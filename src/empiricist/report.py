"""The auditable ledger report (M7 T3, spec §12): `generate(state, cfg)` is a
PURE READ of a run directory's `Ledger` + CAS `Store` -- no model calls, no
domain-verifier re-execution, no mutation. A referee handed the same run
directory can call this function again and get the same Markdown back (up to
the header's own generation-time environment fingerprint), because every
number it prints comes straight out of the ledger tables the campaign itself
wrote (spec §4.2: provenance is total).

**Content contract (spec §12):** header (config hash, environment, total
cost, per-role token/cost); a claims table (every artifact, one row each);
per `VERIFIED_N`/`CERTIFIED`/`FORMALIZED` claim a provenance block (its
evidence rows, the certification stamps currently in force, a CAS link);
`CONJECTURED` (statement + falsification effort) and `REFUTED`
(counterexamples) sections; a gates section (pending/resolved); a search
summary (generations, population size, exact upgrades, stall/f3 events).

**Promotion selection.** "Promoted" (spec: >= VERIFIED_N) uses `Status.rank`,
the one sanctioned numeric comparator (ledger/models.py's own docstring:
never compare `Status` members with `<`/`max()`, StrEnum orders by string
value) -- `artifact.status.rank >= Status.VERIFIED_N.rank` also naturally
excludes REFUTED (rank -1), which is correct: a REFUTED claim is never a
promoted one regardless of any earlier status_n it may have carried.

**Certification stamps.** No evidence row in this codebase names a raw
fusion-verifier ("stab_fusion"/"enum_fusion") as its own `verifier` field --
composite move-level verifiers write "p5_tablebase_dataset_ingest",
"auto_attack", "verify_agreed" instead (see search/loop.py, search/
conjecture.py, domain/p5/dataset.py). So a promoted artifact's trust
boundary is not recoverable by joining `evidence.verifier` against
`certifications.verifier` for that ONE row -- it rests on whichever
verifiers the *ledger's certifications table* currently holds a PASS stamp
for (spec §7: verify() cannot run at all without one). Each provenance block
therefore lists the certifications table's CURRENT full contents ("stamps in
force") rather than attempting a per-evidence-row join the schema does not
support -- an honest report of the trust boundary as it stands, not a
guess at which row depended on which stamp.
"""

from __future__ import annotations

import json
from typing import Any

from empiricist.campaign.state import CampaignState
from empiricist.config import RunConfig, env_fingerprint
from empiricist.ledger.models import Artifact, Status

# search_events triggers that are session/generation bookkeeping, not a
# stall/alarm signal -- everything else observed in search_events is
# reported in the "stall / alarm events" line (spec: "stall/f3 events").
_HOUSEKEEPING_TRIGGERS = frozenset({"created", "resume", "generation", "campaign_end"})


def _short(digest: str | None, n: int = 12) -> str:
    if not digest:
        return "-"
    return digest[:n]


def _fmt_details(details: dict[str, Any]) -> str:
    return json.dumps(details, sort_keys=True, separators=(",", ":"))


def _env_summary() -> tuple[str, str]:
    """(python, platform) parsed from `config.env_fingerprint()` -- the
    environment THIS report-generation process is running in (spec §12's
    "version pins"; for a `run`/`resume` invocation this is also the
    campaign's own execution environment, since the CLI generates the report
    in the same process right after the campaign loop finishes)."""
    fp = json.loads(env_fingerprint())
    return fp.get("python", "?"), fp.get("platform", "?")


def _render_header(state: CampaignState, cfg: RunConfig) -> list[str]:
    python_v, platform_v = _env_summary()
    spent = state.ledger.spent()
    lines = [
        "# Empiricist Campaign Report",
        "",
        f"- Run directory: `{state.run_dir}`",
        f"- Config hash: `{cfg.config_hash()}`",
        f"- Environment: python {python_v}; platform {platform_v}",
        f"- Total spend: ${spent.cost_usd:.4f} "
        f"({spent.tokens_in} input tokens, {spent.tokens_out} output tokens)",
        "",
        "## Per-role spend",
        "",
        "| Role | Runs | Cost (USD) | Tokens in | Tokens out |",
        "|---|---|---|---|---|",
    ]
    aggs = state.ledger.run_aggregates()
    if not aggs:
        lines.append("| _(no runs recorded)_ | | | | |")
    for agg in aggs:
        role = agg.role if agg.role is not None else "_(none)_"
        lines.append(
            f"| {role} | {agg.run_count} | {agg.cost_usd:.4f} | "
            f"{agg.tokens_in} | {agg.tokens_out} |"
        )
    lines.append("")
    return lines


def _render_certifications(state: CampaignState) -> list[str]:
    rows = state.ledger.conn.execute(
        "SELECT * FROM certifications ORDER BY verifier, verifier_version"
    ).fetchall()
    lines = [
        "## Certifications (trust boundary, spec §7)",
        "",
        "| Verifier | Version | Binary hash | Golden suite | Verdict | Stamped at |",
        "|---|---|---|---|---|---|",
    ]
    if not rows:
        lines.append("| _(none stamped)_ | | | | | |")
    for r in rows:
        lines.append(
            f"| {r['verifier']} | {r['verifier_version']} | "
            f"`{_short(r['binary_hash'])}` | `{_short(r['golden_suite_hash'])}` | "
            f"{r['verdict']} | {r['stamped_at']} |"
        )
    lines.append("")
    return lines


def _render_claims_table(artifacts: list[Artifact]) -> list[str]:
    lines = [
        "## Claims",
        "",
        "| ID | Kind | Title | Status | Status N | Coverage |",
        "|---|---|---|---|---|---|",
    ]
    if not artifacts:
        lines.append("| _(no artifacts)_ | | | | | |")
    for art in artifacts:
        lines.append(
            f"| `{_short(art.id)}` | {art.kind} | {art.title} | "
            f"{art.status.value}{f' ({art.substatus})' if art.substatus else ''} | "
            f"{art.status_n if art.status_n is not None else '-'} | "
            f"{art.coverage if art.coverage else '-'} |"
        )
    lines.append("")
    return lines


def _render_provenance_block(state: CampaignState, art: Artifact) -> list[str]:
    lines = [
        f"### {art.kind}: {art.title} (`{_short(art.id)}`)",
        "",
        f"- Status: **{art.status.value}**"
        + (f", n={art.status_n}" if art.status_n is not None else "")
        + (f", coverage={art.coverage}" if art.coverage else "")
        + (f", substatus={art.substatus}" if art.substatus else ""),
        f"- CAS digest: `{art.content_path}` "
        f"(exists in store: {state.store.exists(art.content_path)})",
        "",
        "Evidence:",
        "",
        "| Verifier | Version | Binary hash | Verdict | Wall (s) | Details |",
        "|---|---|---|---|---|---|",
    ]
    evidence = state.ledger.evidence_for(art.id)
    if not evidence:
        lines.append("| _(no evidence rows)_ | | | | | |")
    for ev in evidence:
        lines.append(
            f"| {ev.verifier} | {ev.verifier_version} | `{_short(ev.binary_hash)}` | "
            f"{ev.verdict.value} | {ev.wall_s if ev.wall_s is not None else '-'} | "
            f"`{_fmt_details(ev.details)}` |"
        )
    lines.append("")
    return lines


def _render_provenance_section(state: CampaignState, artifacts: list[Artifact]) -> list[str]:
    promoted = [a for a in artifacts if a.status.rank >= Status.VERIFIED_N.rank]
    lines = ["## Provenance (VERIFIED_N / CERTIFIED / FORMALIZED)", ""]
    if not promoted:
        lines.append("_(no promoted claims yet)_")
        lines.append("")
        return lines
    lines.extend(_render_certifications(state))
    for art in promoted:
        lines.extend(_render_provenance_block(state, art))
    return lines


def _read_json_content(state: CampaignState, art: Artifact) -> dict[str, Any] | None:
    try:
        return json.loads(state.store.get(art.content_path))
    except (KeyError, json.JSONDecodeError):
        return None


def _render_conjectured(state: CampaignState, artifacts: list[Artifact]) -> list[str]:
    lines = ["## CONJECTURED", ""]
    conjectured = [a for a in artifacts if a.status is Status.CONJECTURED]
    if not conjectured:
        lines.append("_(none)_")
        lines.append("")
        return lines
    for art in conjectured:
        lines.append(f"- **{art.title}** (`{_short(art.id)}`)")
        content = _read_json_content(state, art)
        if content is not None:
            lines.append(f"  - Statement: `{_fmt_details(content)}`")
        for ev in state.ledger.evidence_for(art.id):
            checks = ev.details.get("checks")
            lines.append(
                f"  - Falsification effort: {checks} check(s) survived "
                f"(verifier={ev.verifier}, verdict={ev.verdict.value})"
            )
    lines.append("")
    return lines


def _render_refuted(state: CampaignState, artifacts: list[Artifact]) -> list[str]:
    lines = ["## REFUTED", ""]
    refuted = [a for a in artifacts if a.status is Status.REFUTED]
    if not refuted:
        lines.append("_(none)_")
        lines.append("")
        return lines
    for art in refuted:
        lines.append(f"- **{art.title}** (`{_short(art.id)}`)")
        content = _read_json_content(state, art)
        if content is not None:
            lines.append(f"  - Statement: `{_fmt_details(content)}`")
        for ev in state.ledger.evidence_for(art.id):
            counterexample = ev.details.get("counterexample")
            if counterexample:
                lines.append(f"  - Counterexample: {counterexample}")
    lines.append("")
    return lines


def _render_gates(state: CampaignState) -> list[str]:
    gates = state.gates.list()
    lines = ["## Gates", ""]
    pending = [g for g in gates if g.state == "pending"]
    resolved = [g for g in gates if g.state != "pending"]

    lines.append("### Pending")
    lines.append("")
    if not pending:
        lines.append("_(none)_")
    else:
        lines.append("| ID | Kind | Artifact | Opened at | Note |")
        lines.append("|---|---|---|---|---|")
        for g in pending:
            lines.append(
                f"| {g.id} | {g.kind} | `{_short(g.artifact_id)}` | "
                f"{g.opened_at} | {g.note or '-'} |"
            )
    lines.append("")

    lines.append("### Resolved")
    lines.append("")
    if not resolved:
        lines.append("_(none)_")
    else:
        lines.append("| ID | Kind | Artifact | State | Opened at | Resolved at | Note |")
        lines.append("|---|---|---|---|---|---|---|")
        for g in resolved:
            lines.append(
                f"| {g.id} | {g.kind} | `{_short(g.artifact_id)}` | {g.state} | "
                f"{g.opened_at} | {g.resolved_at} | {g.note or '-'} |"
            )
    lines.append("")
    return lines


def _render_search_summary(state: CampaignState) -> list[str]:
    events = state.population.events()
    generation_events = [e for e in events if e.trigger == "generation"]
    exact_upgrades = sum(
        len((e.detail or {}).get("exact_upgrades", ())) for e in generation_events
    )

    stall_counts: dict[str, int] = {}
    for e in events:
        if e.trigger in _HOUSEKEEPING_TRIGGERS:
            continue
        stall_counts[e.trigger] = stall_counts.get(e.trigger, 0) + 1

    lines = [
        "## Search summary",
        "",
        f"- Generations run: {len(generation_events)}",
        f"- Population size: {state.population.count()}",
        f"- Exact upgrades: {exact_upgrades}",
        "- Stall / alarm events:",
    ]
    if not stall_counts:
        lines.append("  - _(none)_")
    else:
        for trigger, n in sorted(stall_counts.items()):
            lines.append(f"  - {trigger}: {n}")
    lines.append("")
    return lines


def generate(state: CampaignState, cfg: RunConfig) -> str:
    """Render the full Markdown report for `state`'s run directory. Pure
    read: no ledger/CAS writes, no model calls, no domain-verifier
    re-execution -- everything printed is already in the ledger/store."""
    artifacts = state.ledger.find_artifacts()
    lines: list[str] = []
    lines.extend(_render_header(state, cfg))
    lines.extend(_render_claims_table(artifacts))
    lines.extend(_render_provenance_section(state, artifacts))
    lines.extend(_render_conjectured(state, artifacts))
    lines.extend(_render_refuted(state, artifacts))
    lines.extend(_render_gates(state))
    lines.extend(_render_search_summary(state))
    return "\n".join(lines) + "\n"

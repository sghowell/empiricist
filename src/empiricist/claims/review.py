"""`review` (charter section 4): write a review receipt for a claim -- a recorded human
review, or the model reviewer (fresh context per sample, bounty framing, two samples
by default for elevated promotions). Each sample is one receipt; any blocking sample
leaves the claim CHALLENGED until a later receipt closes it.

A receipt binds to what was reviewed: the sha256 of the claim's statement and of its
evidence files at review time. `promote` accepts a receipt only for the same statement
and with no blocking finding; `check` flags a receipt whose statement no longer matches.
"""
from __future__ import annotations

import asyncio
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from empiricist.claims.check import check, refresh_repo
from empiricist.claims.lock import committed_file, sha256_file
from empiricist.claims.model import LEVEL_RANK, ClaimFile, load_all
from empiricist.claims.standing import (
    Finding,
    Receipt,
    load_receipts,
    new_receipt_id,
    save_receipt,
    statement_sha256,
)


class ReviewRefused(Exception):
    """The review could not be recorded; the message says why."""


def parse_finding(text: str) -> Finding:
    """`dimension:severity:free text` -> Finding (CLI form)."""
    parts = text.split(":", 2)
    if len(parts) != 3:
        raise ReviewRefused(f"finding {text!r} must be dimension:severity:text")
    dim, sev, body = (x.strip() for x in parts)
    try:
        return Finding(dimension=dim, severity=sev, text=body)  # type: ignore[arg-type]
    except ValueError as exc:
        raise ReviewRefused(f"finding {text!r}: {exc}") from exc


def evidence_hashes(repo: Path, claim) -> list[str]:
    out: list[str] = []
    for path in dict.fromkeys(e.path for e in claim.evidence):
        f = committed_file(repo, path)
        if f is not None:
            out.append(sha256_file(f))
    return sorted(out)


def _now(now: str | None) -> str:
    return now or datetime.now(UTC).isoformat(timespec="seconds")


def _closes_of(claim_id: str, closes: str | list[str] | None, receipts: dict) -> list[str]:
    ids = [closes] if isinstance(closes, str) else list(closes or [])
    for rid in ids:
        target = receipts.get(rid)
        if target is None or target.claim_id != claim_id:
            raise ReviewRefused(f"{rid!r} is not a receipt of {claim_id}")
    return ids


def record_human_review(
    repo: Path | str,
    *,
    claim_id: str,
    reviewer: str,
    verdict: str,
    findings: list[Finding] | None = None,
    closes: str | list[str] | None = None,
    target_level: str | None = None,
    now: str | None = None,
    waivers: list[str] | None = None,
) -> Receipt:
    """Write `receipts/<id>.json` for a human review and refresh the derived standings.
    `waivers` (human reviews only) names rules this receipt explicitly waives for the
    promotion it warrants, e.g. `level_inversion`."""
    repo = Path(repo)
    claims = load_all(repo)
    if claim_id not in claims:
        raise ReviewRefused(f"claim {claim_id!r} does not exist")
    if target_level is not None and target_level not in LEVEL_RANK:
        raise ReviewRefused(f"unknown level {target_level!r}")
    claim = claims[claim_id]
    receipts = load_receipts(repo)
    closes = _closes_of(claim_id, closes, receipts)
    created = _now(now)
    rid = new_receipt_id(claim_id, reviewer, created, set(receipts))
    try:
        receipt = Receipt(
            id=rid, claim_id=claim_id, reviewer=reviewer,
            statement_sha256=statement_sha256(claim.statement),
            evidence_sha256=evidence_hashes(repo, claim),
            findings=list(findings or []), verdict=verdict,  # type: ignore[arg-type]
            closes=closes, created=created, target_level=target_level,  # type: ignore[arg-type]
            waivers=list(waivers or []),  # type: ignore[arg-type]
        )
    except ValueError as exc:
        raise ReviewRefused(str(exc)) from exc
    save_receipt(repo, receipt)
    refresh_repo(repo)
    return receipt


# ---------------------------------------------------------------------------
# Model reviewer
# ---------------------------------------------------------------------------

ELEVATED = frozenset({"CERTIFIED", "FORMALIZED"})
BUNDLE_BYTE_CAP = 240_000
MIN_FILE_SHARE = 24_000


def default_samples(target_level: str | None) -> int:
    return 2 if target_level in ELEVATED else 1


def _evidence_excerpt(repo: Path, path: str, budget: int) -> tuple[str, int]:
    f = committed_file(repo, path)
    if f is None:
        return "(not a committed file)", 0
    data = f.read_bytes()
    digest = sha256_file(f)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return f"(binary, {len(data)} bytes, sha256 {digest})", 0
    if len(text) > budget:
        text = text[:budget] + f"\n... (truncated; {len(data)} bytes total)"
    return f"sha256 {digest}\n{text}", len(text)


def build_review_bundle(
    repo: Path | str,
    claim: ClaimFile,
    *,
    target_level: str | None,
    standings: dict[str, str] | None = None,
    byte_cap: int = BUNDLE_BYTE_CAP,
) -> str:
    """Everything the reviewer sees: statement, target level, evidence with verifier
    identity and (capped) contents, dependencies with their statements and standings."""
    repo = Path(repo)
    claims = load_all(repo)
    standings = standings or {}
    lines = [
        "# Claim under review",
        f"id: {claim.id}",
        f"problem: {claim.problem}",
        f"formulation_version: {claim.formulation_version}",
        f"kind: {claim.kind}",
        f"current level: {claim.level}"
        + (f" (legacy table said {claim.legacy_level})" if claim.legacy_level else ""),
        f"promotion requested: {target_level or '(none; review only)'}",
        "",
        "## Statement (exact; the receipt binds to this text)",
        claim.statement,
        "",
        "## Notes",
        claim.notes or "(none)",
        "",
        "## Dependencies",
    ]
    for d in claim.depends_on:
        dep = claims.get(d)
        if dep is None:
            lines.append(f"- {d} (path dependency)")
        else:
            lines.append(
                f"- {d} [{dep.level}, standing {standings.get(d, dep.standing)}]: {dep.statement}"
            )
    if not claim.depends_on:
        lines.append("(none)")
    lines += ["", "## Evidence entries (verifier identity as recorded)"]
    for e in claim.evidence:
        lines.append(
            f"- {e.path}: {e.verifier} v{e.version} -> {e.verdict} at {e.stamped}"
            + (f" (binary {e.binary_hash[:12]})" if e.binary_hash else "")
            + (f"; note: {e.note}" if e.note else "")
        )
    if not claim.evidence:
        lines.append("(none)")
    lines += ["", "## Evidence files"]
    paths = list(dict.fromkeys(e.path for e in claim.evidence))
    # fair shares: one large certificate must not starve the formulation or proof notes
    share = max(MIN_FILE_SHARE, byte_cap // max(len(paths), 1))
    remaining = byte_cap
    for path in paths:
        excerpt, used = _evidence_excerpt(repo, path, max(min(share, remaining), 0))
        remaining -= used
        lines += [f"### {path}", excerpt, ""]
    lines += [
        "## Task",
        "Find concrete defects along the six dimensions for THIS promotion. Cite the "
        "phrase, file, or field for every finding. List every dimension you examined in "
        "`checked`.",
    ]
    return "\n".join(lines)


def _receipt_from_sample(
    *, claim: ClaimFile, repo: Path, rid: str, created: str, reviewer: str,
    out: dict[str, Any] | None, target_level: str | None, provenance: dict[str, str],
) -> tuple[Receipt, bool]:
    """(receipt, usable): `usable` is False when the sample produced no review."""
    from empiricist.llm.schemas import ReviewOut

    common = dict(
        id=rid, claim_id=claim.id, reviewer=reviewer,
        statement_sha256=statement_sha256(claim.statement),
        evidence_sha256=evidence_hashes(repo, claim), created=created,
        target_level=target_level, provenance=provenance,
    )
    parsed: ReviewOut | None = None
    if out is not None:
        try:
            parsed = ReviewOut.model_validate(out)
        except ValueError:
            parsed = None
    if parsed is None:
        # Spend is never silent: an unusable sample is a REVISE receipt saying so.
        return Receipt(
            **common, verdict="REVISE",
            findings=[Finding(
                dimension="ledger_consistency", severity="warning",
                text="reviewer returned no parseable review; sample discarded, re-run review",
            )],
        ), False
    findings = [Finding(dimension=f.dimension, severity=f.severity, text=f"{f.text} [{f.where}]")
                for f in parsed.findings]
    blocking = any(f.severity == "blocking" for f in findings)
    warning = any(f.severity == "warning" for f in findings)
    # The verdict follows the findings, whatever the model wrote.
    verdict = "BLOCK" if blocking else ("REVISE" if warning or parsed.verdict != "PASS" else "PASS")
    if not blocking and parsed.verdict == "PASS" and len(set(parsed.checked)) < 6:
        verdict = "REVISE"
        findings.append(Finding(
            dimension="decision_soundness", severity="warning",
            text=f"reviewer examined only {sorted(set(parsed.checked))}; PASS needs all six",
        ))
    return Receipt(**common, verdict=verdict, findings=findings), True


async def _review_async(
    repo: Path, claim: ClaimFile, *, client: Any, samples: int, target_level: str | None,
    ledger: Any, standings: dict[str, str], now: str | None, reviewer: str,
    closes: list[str] | None = None,
) -> list[Receipt]:
    from empiricist.llm.roles import ROLES
    from empiricist.llm.schemas import ReviewOut

    prompt = build_review_bundle(repo, claim, target_level=target_level, standings=standings)
    nonce = secrets.token_hex(3)
    existing = set(load_receipts(repo))
    receipts: list[Receipt] = []
    for k in range(1, samples + 1):
        run_id = f"review-{claim.id}-{nonce}-s{k}"
        result = await client.complete(
            ROLES["reviewer"], prompt, schema=ReviewOut, ledger=ledger, run_id=run_id,
        )
        created = _now(now)
        rid = new_receipt_id(claim.id, reviewer, created, existing)
        existing.add(rid)
        provenance = {"run_id": run_id, "transport": type(client).__name__}
        if result is not None:
            provenance["model"] = result.model
            provenance["cost_usd"] = f"{result.cost_usd:.4f}"
        if ledger is not None:
            try:
                run = ledger.get_run(run_id)
                for key in ("request_digest", "response_digest"):
                    if getattr(run, key, None):
                        provenance[key] = getattr(run, key)
            except KeyError:
                pass
        out = result.parsed if result is not None and result.has_artifact else None
        receipt, usable = _receipt_from_sample(
            claim=claim, repo=repo, rid=rid, created=created, reviewer=reviewer, out=out,
            target_level=target_level, provenance=provenance,
        )
        if closes and usable and receipt.verdict != "BLOCK":
            # a fresh, independent review of the corrected claim that raises no blocking
            # finding closes the earlier blocks (its own warnings stay on record as
            # REVISE); a sample that still blocks, or is unusable, closes nothing
            receipt = receipt.model_copy(update={"closes": list(closes)})
        receipts.append(receipt)
    return receipts


def review_with_model(
    repo: Path | str,
    *,
    claim_id: str,
    client: Any,
    samples: int | None = None,
    target_level: str | None = None,
    ledger: Any = None,
    now: str | None = None,
    reviewer: str = "model",
    closes: str | list[str] | None = None,
) -> list[Receipt]:
    """Run `samples` independent reviewer calls (fresh context each) and write one receipt
    per sample. `ledger` (a v0 Ledger under the repo's `.empiricist/`) records the model
    runs; the receipts carry the run ids and receipt digests as provenance. With
    `closes`, a fresh sample that raises no blocking finding (PASS or REVISE) records
    that it closes those earlier blocking receipts (the claim was corrected and
    re-reviewed); a BLOCK sample, or an unusable one, never closes."""
    repo = Path(repo)
    claims = load_all(repo)
    if claim_id not in claims:
        raise ReviewRefused(f"claim {claim_id!r} does not exist")
    if target_level is not None and target_level not in LEVEL_RANK:
        raise ReviewRefused(f"unknown level {target_level!r}")
    closes = _closes_of(claim_id, closes, load_receipts(repo))
    n = samples if samples is not None else default_samples(target_level)
    if n < 1:
        raise ReviewRefused("samples must be >= 1")
    report = check(repo)
    receipts = asyncio.run(_review_async(
        repo, claims[claim_id], client=client, samples=n, target_level=target_level,
        ledger=ledger, standings=dict(report.standings), now=now, reviewer=reviewer,
        closes=closes,
    ))
    for r in receipts:
        save_receipt(repo, r)
    refresh_repo(repo)
    return receipts

"""The `empiricist` CLI (M7 T3, spec §12): `run|resume|status|audit|certify|
gates|report` over a run directory (`<run_dir>/ledger.db` + `<run_dir>/store/`,
`campaign.state.CampaignState`'s two paths).

Thin by design: mutating handlers use `CampaignState.load`; inspection-only
handlers use `CampaignState.open_readonly`.  Each then calls into
`campaign/*` or `report.py`, prints, and closes. No business logic lives here
-- all of it is already tested in `campaign/moves.py`,
`campaign/orchestrator.py`, `campaign/scheduler.py`, and `report.py`.

**--live is the one real-money path** (spec §5.2): either a genuine `claude -p`
subprocess call or an OpenAI Responses API call. Every other command
(including `run`/`resume` WITHOUT `--live`, which only runs the
deterministic ENUMERATE step + writes a report) is fully offline. Tests
reach the `--live` code path too, but through the `_client_factory`
injection seam below (a `FakeLLMClient` stand-in) -- `--live` against a REAL
`claude` subprocess is first exercised in M9's live pilot, per the plan.

Exit codes: `0` success; `1` an expected operational failure (preflight
unhealthy, unknown gate id, an already-resolved gate); `2` a CLI usage/
validation error this module itself catches (an unsupported problem
positional; `--live` without an explicit stop condition; OpenAI without its
required `--max-cost` threshold -- fail-closed). Malformed argv (missing
`--run-dir`, an unknown subcommand, ...) is argparse's own `SystemExit(2)` --
standard argparse behavior, left alone.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from empiricist import report as report_mod
from empiricist.campaign.moves import ensure_certified, ensure_enumerate
from empiricist.campaign.orchestrator import run_campaign
from empiricist.campaign.state import CampaignState
from empiricist.config import RunConfig
from empiricist.ledger.audit import audit_ledger
from empiricist.ledger.db import (
    ORPHANED_EXIT_CODE,
    UNKNOWN_BILLING_EXIT_CODE,
    Ledger,
)
from empiricist.ledger.gates import GateError
from empiricist.llm.client import ClaudeCodeClient, LLMClient
from empiricist.llm.openai_responses import (
    OpenAIPricing,
    OpenAIResponsesClient,
)
from empiricist.llm.preflight import PreflightError, preflight
from empiricist.store import Store
from empiricist.verifiers.enum_fusion import EnumFusionVerifier
from empiricist.verifiers.reverify import reverify_lean_artifacts
from empiricist.verifiers.stab_fusion import StabFusionVerifier

SUPPORTED_PROBLEMS = ("P5",)  # spec: P5 is the only problem in v0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="empiricist")
    sub = parser.add_subparsers(dest="command", required=True)

    def _campaign_flags(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--run-dir", required=True, type=Path)
        sp.add_argument("--live", action="store_true")
        sp.add_argument(
            "--max-cost",
            type=float,
            default=None,
            dest="max_cost",
            help=(
                "stop before the next paid call/wave once recorded spend "
                "reaches this threshold"
            ),
        )
        sp.add_argument(
            "--max-gen",
            type=int,
            default=None,
            dest="max_gen",
            help=(
                "inclusive cumulative successful SEARCH-generation limit "
                "(must be >= 1; not a paid-attempt cap)"
            ),
        )
        sp.add_argument("--tier0-n", type=int, default=None, dest="tier0_n")
        sp.add_argument("--tier1-n", type=int, default=None, dest="tier1_n")
        sp.add_argument("--search-n", type=int, default=None, dest="search_n")
        sp.add_argument(
            "--provider",
            choices=("claude-code", "openai"),
            default="claude-code",
        )
        sp.add_argument(
            "--openai-model",
            choices=("gpt-5.6-sol",),
            default="gpt-5.6-sol",
        )
        sp.add_argument(
            "--openai-reasoning-mode",
            choices=("standard", "pro"),
            default="pro",
        )
        sp.add_argument(
            "--openai-max-output-tokens",
            type=int,
            default=32_768,
        )
        sp.add_argument(
            "--openai-input-usd-per-mtok",
            type=float,
            default=None,
        )
        sp.add_argument(
            "--openai-cached-input-usd-per-mtok",
            type=float,
            default=None,
        )
        sp.add_argument(
            "--openai-output-usd-per-mtok",
            type=float,
            default=None,
        )
        sp.add_argument(
            "--acknowledge-unknown-billing",
            action="store_true",
            help=(
                "resume despite unresolved provider billing; recorded spend "
                "may be understated (acknowledgment applies to this invocation only)"
            ),
        )

    run_p = sub.add_parser("run", help="run (or continue) a campaign")
    run_p.add_argument("problem")
    _campaign_flags(run_p)

    # resume is an alias of run over an existing --run-dir (CampaignState.load
    # is create-or-resume) -- same handler, no positional (P5 is the only
    # supported problem, so there is nothing for the caller to disambiguate).
    resume_p = sub.add_parser("resume", help="alias of run over an existing --run-dir")
    resume_p.set_defaults(problem="P5")
    _campaign_flags(resume_p)

    status_p = sub.add_parser("status", help="artifact counts + spend + population size")
    status_p.add_argument("--run-dir", required=True, type=Path)

    audit_p = sub.add_parser("audit", help="read-only ledger/CAS consistency check")
    audit_p.add_argument("--run-dir", required=True, type=Path)

    reverify_p = sub.add_parser(
        "reverify",
        help=(
            "re-verify FORMALIZED Lean artifacts under the current gate "
            "(opens the ledger for writing: a v0 pilot ledger migrates in place)"
        ),
    )
    reverify_p.add_argument("--run-dir", required=True, type=Path)
    reverify_p.add_argument("--dry-run", action="store_true", help="list targets, write nothing")
    reverify_p.add_argument(
        "--artifact", action="append", default=None,
        help="restrict to this artifact id (repeatable)",
    )
    reverify_p.add_argument("--timeout-s", type=float, default=600.0)

    opt_p = sub.add_parser(
        "p3-optimize",
        help="P3 deterministic tier: optimise a (k, m) Bell scheme for p_min or p_avg (no model)",
    )
    opt_p.add_argument("--run-dir", required=True, type=Path)
    opt_p.add_argument("--k", required=True, type=int, help="ancilla photons")
    opt_p.add_argument("--m", required=True, type=int, help="modes (>= 4)")
    opt_p.add_argument("--target", required=True, choices=("p_min", "p_avg"))
    opt_p.add_argument("--restarts", type=int, default=20)
    opt_p.add_argument("--seed", type=int, default=0)
    opt_p.add_argument("--max-iter", type=int, default=300)
    opt_p.add_argument("--out", required=True, type=Path, help="JSON results file")
    opt_p.add_argument(
        "--ingest", action="store_true",
        help=(
            "ingest the best float scheme (HEURISTIC) and, if lifted, "
            "its exact witness (CERTIFIED)"
        ),
    )

    certify_p = sub.add_parser("certify", help="stamp both P5 fusion verifiers")
    certify_p.add_argument("--run-dir", required=True, type=Path)

    gates_p = sub.add_parser("gates", help="list/resolve the human-gate queue")
    gates_p.add_argument("--run-dir", required=True, type=Path)
    gates_sub = gates_p.add_subparsers(dest="gates_command", required=True)
    gates_sub.add_parser("list")
    resolve_p = gates_sub.add_parser("resolve")
    resolve_p.add_argument("gate_id")
    resolve_group = resolve_p.add_mutually_exclusive_group(required=True)
    resolve_group.add_argument("--approve", action="store_true")
    resolve_group.add_argument("--reject", action="store_true")

    report_p = sub.add_parser("report", help="render the auditable ledger report")
    report_p.add_argument("--run-dir", required=True, type=Path)
    report_p.add_argument("--out", type=Path, default=None)

    return parser


def _cfg_from_args(args: argparse.Namespace) -> RunConfig:
    """RunConfig overrides from the run/resume flags -- unset flags (None)
    leave RunConfig's own defaults untouched."""
    overrides: dict[str, object] = {}
    if args.tier0_n is not None:
        overrides["tier0_n"] = args.tier0_n
    if args.tier1_n is not None:
        overrides["tier1_n"] = args.tier1_n
    if args.search_n is not None:
        overrides["search_target_n"] = args.search_n
    if args.max_cost is not None:
        overrides["max_cost_usd"] = args.max_cost
    if args.max_gen is not None:
        overrides["max_generations"] = args.max_gen
    return replace(RunConfig(), **overrides)


def _open_inspection_state(run_dir: Path) -> CampaignState | None:
    """Open an existing campaign without turning inspection into a resume."""
    try:
        return CampaignState.open_readonly(run_dir)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return None


def _openai_pricing_from_args(args: argparse.Namespace) -> OpenAIPricing | None:
    values = (
        args.openai_input_usd_per_mtok,
        args.openai_cached_input_usd_per_mtok,
        args.openai_output_usd_per_mtok,
    )
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise ValueError(
            "OpenAI pricing is all-or-nothing: pass input, cached-input, "
            "and output USD-per-million-token rates"
        )
    return OpenAIPricing(*values)


def _existing_budget_stop(run_dir: Path, cfg: RunConfig) -> str | None:
    """Return a resume stop reason without mutating an existing campaign.

    Preflight is itself a paid model call. A campaign already at either
    configured stop condition must therefore be detected before constructing a
    client or running preflight.
    """
    if not (run_dir / "ledger.db").exists():
        return None
    state = CampaignState.open_readonly(run_dir)
    try:
        spent = state.ledger.spent()
        if cfg.max_cost_usd is not None and spent.cost_usd >= cfg.max_cost_usd:
            return (
                f"recorded spend ${spent.cost_usd:.4f} already meets "
                f"--max-cost ${cfg.max_cost_usd:.4f}"
            )
        prior_generations = state.population.events(trigger="generation")
        highest_generation = max((event.gen for event in prior_generations), default=0)
        if (
            cfg.max_generations is not None
            and highest_generation >= cfg.max_generations
        ):
            return (
                f"generation {highest_generation} already meets the inclusive "
                f"--max-gen {cfg.max_generations} limit"
            )
        return None
    finally:
        state.close()


def _existing_unknown_billing_runs(run_dir: Path) -> list[str]:
    if not (run_dir / "ledger.db").exists():
        return []
    state = CampaignState.open_readonly(run_dir)
    try:
        return [
            row["run_id"]
            for row in state.ledger.conn.execute(
                "SELECT run_id FROM runs"
                " WHERE provider IS NOT NULL"
                " AND (ended IS NULL OR exit_code IN (?, ?))"
                " ORDER BY rowid",
                (UNKNOWN_BILLING_EXIT_CODE, ORPHANED_EXIT_CODE),
            )
        ]
    finally:
        state.close()


def _build_client(args: argparse.Namespace) -> LLMClient:
    """Construct the selected tool-free transport for one campaign."""
    store = Store(args.run_dir / "store")
    if args.provider == "claude-code":
        return ClaudeCodeClient(store=store)
    return OpenAIResponsesClient(
        model=args.openai_model,
        reasoning_mode=args.openai_reasoning_mode,
        max_output_tokens=args.openai_max_output_tokens,
        store=store,
        pricing=_openai_pricing_from_args(args),
    )


def _cmd_campaign(args: argparse.Namespace, *, client_factory: Callable[[], LLMClient]) -> int:
    if args.problem not in SUPPORTED_PROBLEMS:
        print(
            f"error: unsupported problem {args.problem!r} "
            f"(only {', '.join(SUPPORTED_PROBLEMS)} is supported in v0)",
            file=sys.stderr,
        )
        return 2

    cfg = _cfg_from_args(args)
    run_dir: Path = args.run_dir

    if cfg.max_generations is not None and cfg.max_generations < 1:
        print("error: --max-gen must be at least 1", file=sys.stderr)
        return 2
    if cfg.max_cost_usd is not None and (
        not math.isfinite(cfg.max_cost_usd) or cfg.max_cost_usd <= 0
    ):
        print("error: --max-cost must be a finite number greater than 0", file=sys.stderr)
        return 2

    if not args.live:
        state = CampaignState.load(run_dir)
        try:
            ensure_enumerate(state, cfg)  # the deterministic step; no model moves
            text = report_mod.generate(state, cfg)
            (run_dir / "report.md").write_text(text)
        finally:
            state.close()
        print(
            "dry run complete: ENUMERATE done, report.md written. "
            "No model moves ran -- pass --live to run SEARCH/CONJECTURE."
        )
        return 0

    # Fail-closed budget posture (overnight-safety review I1): an unattended
    # --live campaign bills real money, so it must carry an explicit stop
    # condition. `max_generations` is a strict inclusive generation limit.
    # `max_cost_usd` is checked between paid calls/waves and is therefore a
    # stop threshold, not a reservation-backed hard dollar ceiling.
    if cfg.max_cost_usd is None and cfg.max_generations is None:
        print(
            "error: unattended live campaigns require an explicit budget "
            "stop condition -- pass --max-cost and/or --max-gen (fail-closed).",
            file=sys.stderr,
        )
        return 2

    try:
        pricing = (
            _openai_pricing_from_args(args)
            if args.provider == "openai"
            else None
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.provider == "openai" and pricing is None:
        print(
            "error: live OpenAI campaigns require explicit current pricing "
            "rates so paid calls are never recorded as $0; pass all three "
            "--openai-*-usd-per-mtok flags.",
            file=sys.stderr,
        )
        return 2
    if args.provider == "openai" and cfg.max_cost_usd is None:
        print(
            "error: live OpenAI campaigns require --max-cost; --max-gen "
            "bounds successful SEARCH work, not paid retry/conjecture waves.",
            file=sys.stderr,
        )
        return 2

    try:
        unknown_billing_runs = _existing_unknown_billing_runs(run_dir)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: cannot inspect existing campaign billing: {exc}", file=sys.stderr)
        return 1
    if unknown_billing_runs and not args.acknowledge_unknown_billing:
        joined = ", ".join(unknown_billing_runs)
        print(
            "error: provider billing is unknown for run(s) "
            f"{joined}; compare provider usage before resuming. Pass "
            "--acknowledge-unknown-billing only if you accept that recorded "
            "spend may be understated.",
            file=sys.stderr,
        )
        return 1
    if unknown_billing_runs:
        print(
            "warning: acknowledged unresolved billing for run(s) "
            f"{', '.join(unknown_billing_runs)}; recorded spend may be understated"
        )

    try:
        existing_stop = _existing_budget_stop(run_dir, cfg)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: cannot inspect existing campaign budget: {exc}", file=sys.stderr)
        return 1
    if existing_stop is not None:
        print(f"campaign already at configured stop condition: {existing_stop}")
        print("no client was constructed and no preflight/model call was made")
        return 0

    try:
        client = client_factory()
    except (ValueError, RuntimeError) as exc:
        print(f"error: provider configuration failed: {exc}", file=sys.stderr)
        return 2

    # Preflight is a real model call, so it gets a runs row and request/response
    # receipts just like campaign calls. Opening the bare ledger avoids adding a
    # spurious campaign resume event before run_campaign owns the state.
    run_dir.mkdir(parents=True, exist_ok=True)
    preflight_ledger = Ledger(run_dir / "ledger.db")
    try:
        asyncio.run(preflight(client, ledger=preflight_ledger))
    except (PreflightError, RuntimeError) as exc:
        print(f"error: preflight failed: {exc}", file=sys.stderr)
        return 1
    finally:
        preflight_ledger.close()

    summary = asyncio.run(run_campaign(run_dir, cfg, client))
    print(f"campaign summary: {summary}")

    # run_campaign closes its own mutating handle.  Rendering the completed
    # snapshot must not manufacture another resume boundary.
    state = CampaignState.open_readonly(run_dir)
    try:
        text = report_mod.generate(state, cfg)
        report_path = run_dir / "report.md"
        report_path.write_text(text)
    finally:
        state.close()
    print(f"report written to {report_path}")
    if summary.stop_reason == "billing_unknown":
        print(
            "error: campaign stopped because provider billing is unknown; "
            "reconcile provider usage before resuming",
            file=sys.stderr,
        )
        return 1
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    state = _open_inspection_state(args.run_dir)
    if state is None:
        return 1
    try:
        counts: dict[str, int] = {}
        for art in state.ledger.find_artifacts():
            counts[art.status.value] = counts.get(art.status.value, 0) + 1
        spent = state.ledger.spent()

        print(f"run directory: {args.run_dir}")
        print("artifact counts by status:")
        if not counts:
            print("  (none)")
        for status, n in sorted(counts.items()):
            print(f"  {status}: {n}")
        print(
            f"spend: ${spent.cost_usd:.4f} "
            f"({spent.tokens_in} tokens in, {spent.tokens_out} tokens out)"
        )
        print(f"population size: {state.population.count()}")
        return 0
    finally:
        state.close()


def _cmd_audit(args: argparse.Namespace) -> int:
    state = _open_inspection_state(args.run_dir)
    if state is None:
        return 1
    try:
        report = audit_ledger(state.ledger, state.store)
        print(
            f"audit: {report.artifacts_checked} artifacts, "
            f"{report.evidence_checked} evidence rows"
        )
        if report.ok:
            print("audit OK")
            return 0
        for issue in report.issues:
            artifact = f" artifact={issue.artifact_id}" if issue.artifact_id else ""
            print(f"{issue.code}:{artifact} {issue.message}")
        return 1
    finally:
        state.close()


def _cmd_reverify(args: argparse.Namespace) -> int:
    ledger_path = args.run_dir / "ledger.db"
    if not ledger_path.is_file():
        print(f"error: campaign ledger does not exist: {ledger_path}", file=sys.stderr)
        return 1
    ledger = Ledger(ledger_path)  # write mode: a v0 ledger migrates in place (spec App. A)
    store = Store(args.run_dir / "store")
    try:
        report = reverify_lean_artifacts(
            ledger, store, artifact_ids=args.artifact, dry_run=args.dry_run,
            timeout_s=args.timeout_s,
        )
    finally:
        ledger.close()
    suffix = ""
    if report.dry_run:
        suffix += " [dry run]"
    if report.certified_now:
        suffix += " [certified LeanVerifier in this pass]"
    print(f"reverify: {len(report.outcomes)} lean artifact(s){suffix}")
    for o in report.outcomes:
        print(f"{o.verdict}: {o.decl} artifact={o.artifact_id} {o.detail}")
    return 0 if (report.ok or report.dry_run) else 1


def _cmd_p3_optimize(args: argparse.Namespace) -> int:
    import json

    from empiricist.domain.p3.exact import alg_str, alg_to_json
    from empiricist.domain.p3.optimize import optimize_scheme

    args.run_dir.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(args.run_dir / "ledger.db")
    store = Store(args.run_dir / "store")
    try:
        results = optimize_scheme(
            args.k, args.m, target=args.target, restarts=args.restarts, seed=args.seed,
            max_iter=args.max_iter, ledger=ledger,
            tau_schedule=(0.3, 0.1, 0.03, 0.01, 1e-3, 1e-4, 1e-5),
        )
        rows = []
        for r in results:
            rep = r.report
            rows.append({
                "restart": r.restart, "objective": r.objective,
                "metric": r.metric(args.target),
                "scheme": r.scheme_json,
                "float": {"success_by_state": dict(rep.success_by_state), "p_min": rep.p_min,
                          "p_avg": rep.p_avg, "leakage": rep.leakage},
                "witness": r.witness_json,
                "exact": None if r.exact is None else {
                    "success": {b: alg_to_json(v) for b, v in r.exact.success.items()},
                    "success_str": {b: alg_str(v) for b, v in r.exact.success.items()},
                    "p_min": alg_str(r.exact.p_min), "p_avg": alg_str(r.exact.p_avg),
                    "all_identified": r.exact.all_identified,
                },
            })
        payload = {"k": args.k, "m": args.m, "target": args.target, "restarts": args.restarts,
                   "seed": args.seed, "max_iter": args.max_iter, "results": rows}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=1, sort_keys=True, allow_nan=False))
        if not results:
            print("p3-optimize: no valid result")
            return 1
        best = results[0]
        print(
            f"p3-optimize k={args.k} m={args.m} {args.target}: "
            f"best={best.metric(args.target):.6f} restarts={len(results)} "
            f"exact={'yes' if best.exact is not None else 'no'}"
        )
        for r in results[:5]:
            vec = ", ".join(f"{r.report.success_by_state[b]:.4f}" for b in
                            ("phi+", "phi-", "psi+", "psi-"))
            ex = "" if r.exact is None else " exact=(" + ", ".join(
                alg_str(r.exact.success[b]) for b in ("phi+", "phi-", "psi+", "psi-")) + ")"
            print(f"  restart {r.restart}: ({vec}) leak={r.report.leakage:.1e}{ex}")
        if args.ingest:
            _ingest_optimizer_result(ledger, store, best, args.target)
        return 0
    finally:
        ledger.close()


def _ingest_optimizer_result(ledger: Ledger, store: Store, best, target: str) -> None:
    from empiricist.domain.p3.exact import alg_to_json
    from empiricist.domain.p3.exact_ingest import ingest_exact_witness
    from empiricist.domain.p3.ingest import ingest_scheme_artifact
    from empiricist.verifiers.p3_exact import P3ExactVerifier
    from empiricist.verifiers.p3_exact_goldens import certify_p3_exact, p3_exact_suite_hash
    from empiricist.verifiers.p3_goldens import certify_p3, p3_suite_hash
    from empiricist.verifiers.p3_scheme import P3SchemeVerifier

    k, m = best.scheme_json["n_ancilla_photons"], best.scheme_json["n_modes"]
    v = P3SchemeVerifier()
    cert = ledger.get_certification(v.name, v.version, v.binary_hash)
    if cert is None or cert.golden_suite_hash != p3_suite_hash():
        certify_p3(ledger, v)
    achieved = best.report.p_min if target == "p_min" else best.report.p_avg
    claim = {"claimed_p_min": max(0.0, achieved - 1e-9)} if target == "p_min" else {
        "claimed_p_avg": max(0.0, achieved - 1e-9)}
    # Declare the leakage the engines actually reported (float noise, <= 1e-12 for
    # an unambiguous scheme): an honest budget, recorded in the claim's scope.
    art = ingest_scheme_artifact(
        ledger, store, scheme_json=best.scheme_json,
        title=f"P3 optimizer k={k} m={m} {target} (float, two-engine)",
        claimed_max_leakage=float(best.report.leakage), **claim,
    )
    print(f"  ingested float scheme {art.id[:12]} at {art.status.value}")
    if best.exact is None:
        return
    ve = P3ExactVerifier()
    cert = ledger.get_certification(ve.name, ve.version, ve.binary_hash)
    if cert is None or cert.golden_suite_hash != p3_exact_suite_hash():
        certify_p3_exact(ledger, ve)
    ex = best.exact
    wart = ingest_exact_witness(
        ledger, store, witness_json=best.witness_json,
        claimed_success={b: alg_to_json(val) for b, val in ex.success.items()},
        require_all_identified=ex.all_identified,
        title=f"P3 exact witness k={k} m={m}: {target} optimum",
    )
    print(f"  ingested exact witness {wart.id[:12]} at {wart.status.value}")


def _cmd_certify(args: argparse.Namespace) -> int:
    state = CampaignState.load(args.run_dir)
    try:
        ensure_certified(state)
        for verifier_cls in (StabFusionVerifier, EnumFusionVerifier):
            v = verifier_cls()
            cert = state.ledger.get_certification(v.name, v.version, v.binary_hash)
            verdict = cert.verdict.value if cert is not None else "MISSING"
            print(f"{v.name} v{v.version} [{v.binary_hash[:12]}]: {verdict}")
        return 0
    finally:
        state.close()


def _cmd_gates(args: argparse.Namespace) -> int:
    # Listing is inspection; resolving is an explicit state transition and
    # retains load()'s recovery/session-boundary behavior.
    state = (
        _open_inspection_state(args.run_dir)
        if args.gates_command == "list"
        else CampaignState.load(args.run_dir)
    )
    if state is None:
        return 1
    try:
        if args.gates_command == "list":
            gates = state.gates.list()
            if not gates:
                print("no gates.")
            for g in gates:
                print(
                    f"{g.id}  kind={g.kind}  state={g.state}  "
                    f"artifact={g.artifact_id[:12]}  opened={g.opened_at}"
                )
            return 0

        # gates_command == "resolve"
        try:
            gate = state.gates.resolve(args.gate_id, approve=args.approve)
        except KeyError:
            print(f"error: no such gate {args.gate_id!r}", file=sys.stderr)
            return 1
        except GateError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"gate {gate.id} -> {gate.state}")
        return 0
    finally:
        state.close()


def _cmd_report(args: argparse.Namespace) -> int:
    state = _open_inspection_state(args.run_dir)
    if state is None:
        return 1
    try:
        # Standalone `report` has no config flags -- it reports against
        # RunConfig()'s defaults (documented: `run`/`resume` write a report
        # using the campaign's ACTUAL cfg; this one reflects only what this
        # invocation used, not necessarily what produced the ledger).
        text = report_mod.generate(state, RunConfig())
        if args.out is not None:
            args.out.write_text(text)
            print(f"report written to {args.out}")
        else:
            print(text)
        return 0
    finally:
        state.close()


def main(
    argv: list[str] | None = None,
    *,
    _client_factory: Callable[[], LLMClient] | None = None,
) -> int:
    """Parse `argv` (default: `sys.argv[1:]`) and dispatch. Returns an exit
    code; never calls `sys.exit` itself -- the console-script wrapper
    generated from `[project.scripts]` does that around this function's
    return value.

    `_client_factory` is a test-only seam: the default constructs the provider
    selected by CLI flags, so tests inject a `FakeLLMClient` factory instead
    of touching a real transport.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in ("run", "resume"):
        factory = _client_factory or (lambda: _build_client(args))
        return _cmd_campaign(args, client_factory=factory)
    if args.command == "status":
        return _cmd_status(args)
    if args.command == "audit":
        return _cmd_audit(args)
    if args.command == "reverify":
        return _cmd_reverify(args)
    if args.command == "p3-optimize":
        return _cmd_p3_optimize(args)
    if args.command == "certify":
        return _cmd_certify(args)
    if args.command == "gates":
        return _cmd_gates(args)
    if args.command == "report":
        return _cmd_report(args)

    parser.error(f"unknown command {args.command!r}")  # pragma: no cover -- argparse guards this
    return 2  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

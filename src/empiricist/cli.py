"""The `empiricist` CLI (M7 T3, spec §12): `run|resume|status|certify|gates|
report` over a run directory (`<run_dir>/ledger.db` + `<run_dir>/store/`,
`campaign.state.CampaignState`'s two paths).

Thin by design: every subcommand handler is a few lines of `CampaignState.
load` + a call into `campaign/*` or `report.py` + print + close. No business
logic lives here -- all of it is already tested in `campaign/moves.py`,
`campaign/orchestrator.py`, `campaign/scheduler.py`, and `report.py`.

**--live is the one real-money path** (spec §5.2): a genuine `claude -p`
subprocess call, billed against the subscription. Every other command
(including `run`/`resume` WITHOUT `--live`, which only runs the
deterministic ENUMERATE step + writes a report) is fully offline. Tests
reach the `--live` code path too, but through the `_client_factory`
injection seam below (a `FakeLLMClient` stand-in) -- `--live` against a REAL
`claude` subprocess is first exercised in M9's live pilot, per the plan.

Exit codes: `0` success; `1` an expected operational failure (preflight
unhealthy, unknown gate id, an already-resolved gate); `2` a CLI usage/
validation error this module itself catches (an unsupported problem
positional). Malformed argv (missing `--run-dir`, an unknown subcommand,
...) is argparse's own `SystemExit(2)` -- standard argparse behavior, left
alone.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from empiricist import report as report_mod
from empiricist.campaign.moves import ensure_certified, ensure_enumerate
from empiricist.campaign.orchestrator import run_campaign
from empiricist.campaign.state import CampaignState
from empiricist.config import RunConfig
from empiricist.ledger.gates import GateError
from empiricist.llm.client import ClaudeCodeClient, LLMClient
from empiricist.llm.preflight import PreflightError, preflight
from empiricist.verifiers.enum_fusion import EnumFusionVerifier
from empiricist.verifiers.stab_fusion import StabFusionVerifier

SUPPORTED_PROBLEMS = ("P5",)  # spec: P5 is the only problem in v0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="empiricist")
    sub = parser.add_subparsers(dest="command", required=True)

    def _campaign_flags(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--run-dir", required=True, type=Path)
        sp.add_argument("--live", action="store_true")
        sp.add_argument("--max-cost", type=float, default=None, dest="max_cost")
        sp.add_argument("--max-gen", type=int, default=None, dest="max_gen")
        sp.add_argument("--tier0-n", type=int, default=None, dest="tier0_n")
        sp.add_argument("--tier1-n", type=int, default=None, dest="tier1_n")
        sp.add_argument("--search-n", type=int, default=None, dest="search_n")

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

    client = client_factory()
    try:
        asyncio.run(preflight(client))
    except PreflightError as exc:
        print(f"error: preflight failed: {exc}", file=sys.stderr)
        return 1

    summary = asyncio.run(run_campaign(run_dir, cfg, client))
    print(f"campaign summary: {summary}")

    state = CampaignState.load(run_dir)  # run_campaign closes its own handle
    try:
        text = report_mod.generate(state, cfg)
        report_path = run_dir / "report.md"
        report_path.write_text(text)
    finally:
        state.close()
    print(f"report written to {report_path}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    state = CampaignState.load(args.run_dir)
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
    state = CampaignState.load(args.run_dir)
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
    state = CampaignState.load(args.run_dir)
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

    `_client_factory` is a test-only seam: the default constructs a real
    `ClaudeCodeClient` (a genuine subscription-billed `claude -p` subprocess)
    for `--live`, so tests inject a `FakeLLMClient` factory here instead of
    ever touching the real transport.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in ("run", "resume"):
        factory = _client_factory or ClaudeCodeClient
        return _cmd_campaign(args, client_factory=factory)
    if args.command == "status":
        return _cmd_status(args)
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

"""`python -m empiricist.packs.zx campaign ...`: the P6 completion campaign driver (M25b).

    python -m empiricist.packs.zx campaign --repo . --run-dir runs/p6-completion \
        --max-cost 100 --max-rounds 16 [--k 2] [--classes "2,2,4;2,2,6"] [--fake proposals.json]

`--fake` runs the loop offline against a scripted `FakeLLMClient`: the file holds a JSON
list whose entries are `SystemOut` objects (or null for a call that yields no artifact),
consumed in order, one per proposal slot. Without it the real `ClaudeCodeClient` is used
and every call is a `runs` row in `<run-dir>/ledger.db`, from which the cost cap is read.
Exit status 0 when a candidate passed every check on every class, 1 otherwise.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from empiricist.llm.client import FakeLLMClient, LLMClient
from empiricist.llm.models import LLMResult
from empiricist.packs.zx.campaign import (
    DEFAULT_CLASSES,
    DEFAULT_MAX_DIAGRAMS,
    DEFAULT_MAX_INSTANCES,
    DEFAULT_MAX_NODES,
    DEFAULT_MAX_STEPS,
    DEFAULT_STAR_LEGS,
    CampaignReport,
    Evaluation,
    class_name,
    parse_classes,
    run_campaign,
)


def fake_result(parsed: dict | None) -> LLMResult:
    return LLMResult(
        text="", parsed=parsed, stop_reason="tool_use" if parsed is not None else "end_turn",
        is_error=False, input_tokens=0, output_tokens=0, cache_read_tokens=0,
        cache_creation_tokens=0, cost_usd=0.0, duration_ms=0, session_id="fake", uuid="fake",
        model="fake",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m empiricist.packs.zx")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("campaign", help="the P6 completion campaign loop")
    c.add_argument("--repo", type=Path, default=Path("."), help="the claims repository root")
    c.add_argument("--run-dir", type=Path, required=True, dest="run_dir")
    c.add_argument("--max-cost", type=float, default=100.0, dest="max_cost",
                   help="stop once the run directory's recorded spend (USD) reaches this")
    c.add_argument("--max-rounds", type=int, default=16, dest="max_rounds")
    c.add_argument("--k", type=int, default=2, help="proposals per round")
    c.add_argument("--classes", default=";".join(",".join(map(str, c)) for c in DEFAULT_CLASSES),
                   help='completeness classes w,v,e in order, e.g. "2,2,4;2,2,6"')
    c.add_argument("--star-legs", type=int, default=DEFAULT_STAR_LEGS, dest="star_legs")
    c.add_argument("--max-nodes", type=int, default=DEFAULT_MAX_NODES, dest="max_nodes")
    c.add_argument("--max-instances", type=int, default=DEFAULT_MAX_INSTANCES,
                   dest="max_instances")
    c.add_argument("--max-diagrams", type=int, default=DEFAULT_MAX_DIAGRAMS, dest="max_diagrams")
    c.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS, dest="max_steps")
    c.add_argument("--fake", type=Path, default=None,
                   help="a JSON list of scripted proposals (offline, no model calls)")
    return p


def _client(args: argparse.Namespace) -> LLMClient:
    if args.fake is not None:
        scripted = json.loads(args.fake.read_text("utf-8"))
        if not isinstance(scripted, list):
            raise ValueError("--fake must hold a JSON list of proposals (or nulls)")
        return FakeLLMClient([fake_result(item) for item in scripted])
    from empiricist.llm.client import ClaudeCodeClient
    from empiricist.store import Store

    return ClaudeCodeClient(store=Store(args.run_dir / "store"), timeout_s=1800.0)


def _line(ev: Evaluation) -> str:
    who = f"round {ev.round} slot {ev.slot}" + (f" cand_{ev.cid}" if ev.cid else "")
    if ev.skipped:
        return f"{who}: skipped ({ev.skipped})"
    steps = " ".join(f"{s.name}={s.verdict}" for s in ev.steps)
    return (f"{who}: {'SUCCESS' if ev.success else 'serious' if ev.serious else 'rejected'} "
            f"[{steps}] claims={len(ev.claims)} {ev.seconds:.1f}s")


def _print_report(report: CampaignReport, classes) -> None:
    for ev in report.history:
        print(_line(ev))
    print(f"stop: {report.stop_reason} after {report.rounds} round(s); recorded spend "
          f"${report.spent_usd:.4f}; {len(report.claims)} claim(s) minted; classes "
          + ", ".join(class_name(c) for c in classes))
    if report.success is not None:
        print(f"winner: cand_{report.success.cid} -> " + ", ".join(report.success.claims))


def _cmd_campaign(args: argparse.Namespace) -> int:
    try:
        classes = parse_classes(args.classes)
    except ValueError as exc:
        print(f"campaign: {exc}", file=sys.stderr)
        return 2
    args.run_dir.mkdir(parents=True, exist_ok=True)
    try:
        client = _client(args)
    except (OSError, ValueError) as exc:
        print(f"campaign: {exc}", file=sys.stderr)
        return 2
    report = asyncio.run(run_campaign(
        client, args.repo, args.run_dir, max_rounds=args.max_rounds, max_cost=args.max_cost,
        k=args.k, classes=classes, star_legs=args.star_legs, max_nodes=args.max_nodes,
        max_instances=args.max_instances, max_diagrams=args.max_diagrams,
        max_steps=args.max_steps,
    ))
    _print_report(report, classes)
    return 0 if report.success is not None else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "campaign":
        return _cmd_campaign(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())

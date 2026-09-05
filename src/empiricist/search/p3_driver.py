"""The committed P3 search driver: runs one `P3SearchTask` with every round's
scheme persisted crash-safely to a JSONL file under the run directory.

Why this exists: the M20b wave was driven by an ad-hoc script that kept only the
best scheme, so the k=1 design that identified all four Bell states was lost.
`P3SearchLoop` now exposes `round_sink`; this module is the one place that wires
it, so an operator never has to remember to.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from empiricist.ledger.db import Ledger
from empiricist.llm.client import LLMClient
from empiricist.llm.roles import Role
from empiricist.llm.throttle import DEFAULT_THROTTLE, ThrottlePolicy
from empiricist.search.p3_loop import P3SearchLoop, P3SearchReport, P3SearchTask
from empiricist.store import Store

ROUNDS_DIRNAME = "p3-rounds"


def rounds_path(run_dir: Path, task: P3SearchTask, nonce: str) -> Path:
    return Path(run_dir) / ROUNDS_DIRNAME / f"{task.name}-{nonce}.jsonl"


class JsonlRoundSink:
    """Append one JSON line per round entry; the file is flushed per line."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.count = 0

    def __call__(self, entry: dict) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True, allow_nan=False) + "\n")
            fh.flush()
        self.count += 1


async def run_p3_task(
    run_dir: Path,
    task: P3SearchTask,
    *,
    client: LLMClient,
    ledger: Ledger,
    store: Store,
    role: Role | None = None,
    max_rounds: int = 12,
    throttle: ThrottlePolicy | None = DEFAULT_THROTTLE,
) -> tuple[P3SearchReport, Path]:
    """Run the loop with a JSONL round sink; returns the report and the sink path."""
    nonce = uuid.uuid4().hex[:8]
    path = rounds_path(Path(run_dir), task, nonce)
    sink = JsonlRoundSink(path)
    loop = P3SearchLoop(
        client, ledger, store, max_rounds=max_rounds, role=role, throttle=throttle,
        round_sink=sink,
    )
    report = await loop.run(task)
    summary = {
        "task": task.name, "ok": report.ok, "rounds": report.rounds,
        "artifact_id": report.artifact_id, "throttled": report.throttled,
        "f3_alarm": report.f3_alarm, "best_summary": report.best_summary,
        "best": report.best,
    }
    with path.with_suffix(".summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, sort_keys=True, allow_nan=False)
    return report, path


def read_rounds(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]

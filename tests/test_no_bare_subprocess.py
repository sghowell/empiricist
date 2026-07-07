"""Enforce the 'one audited path' contract: no module outside executor/ may
spawn subprocesses directly — everything goes through executor.runner.execute()."""

import pathlib
import re

BANNED = re.compile(r"\b(import subprocess|from subprocess|os\.system|os\.fork|"
                    r"os\.posix_spawn|multiprocessing|os\.exec)")


def test_no_subprocess_spawning_outside_executor():
    src = pathlib.Path(__file__).resolve().parent.parent / "src" / "empiricist"
    offenders = []
    for py in src.rglob("*.py"):
        if "executor" in py.relative_to(src).parts:
            continue
        for i, line in enumerate(py.read_text().splitlines(), 1):
            if BANNED.search(line):
                offenders.append(f"{py.relative_to(src)}:{i}: {line.strip()}")
    assert not offenders, "subprocess spawning outside executor/:\n" + "\n".join(offenders)

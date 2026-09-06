"""Empiricist command-verifier adapter (template installed by `empiricist claims install-skill`).

    python tools/empiricist_check.py <package> [certificate.json]

Every `<package>.verify` module here exposes the same three names: `REPORT` (the
pinned certificate), `build_report()` (an exact, read-only replay) and
`validate_report(expected, actual)` (raises ValueError on any difference). This
adapter replays the checker and compares it against the certificate named on the
command line, or in `$EMPIRICIST_EVIDENCE`, or (by default) the pinned REPORT. It
exits 0 only when the replay reproduces the certificate exactly; it never writes.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    package = argv[1]
    try:
        mod = importlib.import_module(f"{package}.verify")
    except ImportError as exc:
        print(f"ERROR {package}: cannot import checker: {exc}", file=sys.stderr)
        return 2
    target = argv[2] if len(argv) > 2 else os.environ.get("EMPIRICIST_EVIDENCE") or str(mod.REPORT)
    path = Path(target)
    try:
        expected = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        print(f"FAIL {package}: cannot read certificate {path}: {exc}", file=sys.stderr)
        return 3
    try:
        mod.validate_report(expected, mod.build_report())
    except (ValueError, KeyError, TypeError, AssertionError) as exc:
        print(f"FAIL {package}: {exc}", file=sys.stderr)
        return 3
    print(f"PASS {package}: {path} reproduced by exact replay")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

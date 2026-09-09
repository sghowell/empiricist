"""The complete scoped P8(b) certificate chain: `p8.verify_all.build_reports()`.

One replay (which first re-checks the S0 anchor through `p8.verify.check_certificate`)
rebuilds six certificates -- `s1-derived-action.json`, `a25-regression.json`,
`witness-C.json`, `witness-D.json`, `witness-CD_matter.json` and `classification.json`
(P8-3, which pins the other five by semantic sha256 and the environment: Python, sympy,
python-flint and the research repository's `uv.lock`). A certificate is reproduced iff it
equals one of the six rebuilt reports; that is what `validate_report` checks."""
from __future__ import annotations

import importlib

from empiricist.packs.cosmology.vendored import CHECKERS, vendored_package

vendored_package("p8", CHECKERS / "problems" / "P8" / "src")
_verify_all = importlib.import_module("p8.verify_all")

REPORT = _verify_all.ROOT / "certificates" / "classification.json"


def build_report():
    return _verify_all.build_reports()


def validate_report(expected, actual):
    if any(expected == report for report in actual.values()):
        return
    claim = expected.get("claim") if isinstance(expected, dict) else None
    named = [name for name, report in actual.items()
             if isinstance(report, dict) and claim is not None and report.get("claim") == claim]
    if named:
        raise ValueError(f"{named[0]}: certificate differs from exact replay")
    raise ValueError(
        "certificate is none of the P8(b) chain's replayed reports (" + ", ".join(actual) + ")"
    )

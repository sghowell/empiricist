"""P8-1 (derived covariant action): `p8.verify_all.derivation_report()` against
`s1-derived-action.json`.

`verify_all.build_reports()` replays the whole P8(b) chain; `derivation_report()` is the
part that produces this one certificate, and it is what this adapter compares exactly."""
from __future__ import annotations

import importlib

from empiricist.packs.cosmology.vendored import CHECKERS, vendored_package

vendored_package("p8", CHECKERS / "problems" / "P8" / "src")
_verify_all = importlib.import_module("p8.verify_all")

REPORT = _verify_all.ROOT / "certificates" / "s1-derived-action.json"


def build_report():
    return _verify_all.derivation_report()


def validate_report(expected, actual):
    if expected != actual:
        raise ValueError("P8-1 derived-action certificate differs from exact replay")

"""P8-0 (S0 exact-algebra identities): `p8.verify.report()` against `s0-identities.json`.

`p8.verify` exposes `CERTIFICATE`, `report()` and `check_certificate()` rather than the
`REPORT` / `build_report` / `validate_report` names; this adapter renames them and
compares exactly, as `check_certificate` does."""
from __future__ import annotations

import importlib

from empiricist.packs.cosmology.vendored import CHECKERS, vendored_package

vendored_package("p8", CHECKERS / "problems" / "P8" / "src")
_verify = importlib.import_module("p8.verify")

REPORT = _verify.CERTIFICATE


def build_report():
    return _verify.report()


def validate_report(expected, actual):
    if expected != actual:
        raise ValueError("P8-0 S0 certificate differs from exact replay")

"""SOS_GOLDEN_SUITE: SOSCertificateVerifier's mutation-resistant certification suite
(spec section 7's discipline, the same shape as `verifiers/lean_goldens.py` and
`verifiers/p3_goldens.py`).

Cases (certificate, expected verdict):
1. the pinned k=0 standard-assignment certificate (bound exactly 1/2)  -> PASS
2. a tiny true certificate  (-x0^2 <= 0, Gram [[1]])                   -> PASS
3. the k=0 golden with its bound lowered to 49/100 (identity breaks)   -> FAIL
4. x0^2 <= 0 with Gram [[-1]] (identity holds, Gram not PSD)           -> FAIL
5. a shape-broken certificate (empty Gram for a 1-element basis)       -> FAIL
Cases 3-5 fail through three DIFFERENT checker branches (identity / psd /
shape) -- independent must-fail mechanisms, not repeated cases.
`sos_suite_hash()` pins every stamp to this exact suite content, so editing the
suite invalidates every existing stamp.
"""
from __future__ import annotations

import json
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

from blake3 import blake3

from empiricist.certificates.core import SOSCertificate
from empiricist.certificates.verifier import (
    SOSCertificateVerifier,
    certificate_from_json,
    certificate_to_json,
)
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Certification, Verdict
from empiricist.verifiers.base import VerifierResult
from empiricist.verifiers.registry import certify_with_suite

_K0_GOLDEN_PATH = Path(__file__).resolve().parent / "data" / "p3_k0_standard_assignment.json"


def load_k0_golden() -> SOSCertificate:
    """The pinned exact certificate: standard-assignment p_avg <= 1/2 for all
    U in U(4) (M20c Task 4; constructed from the probability-conservation
    identity and verified by the exact checker)."""
    return certificate_from_json(json.loads(_K0_GOLDEN_PATH.read_text()))


def _tiny_true() -> SOSCertificate:
    return SOSCertificate(
        statement="-x0^2 <= 0",
        variables=("x0",),
        objective={(0, 0): Fraction(-1)},
        bound=Fraction(0),
        constraints=(),
        multipliers=(),
        gram_basis=((0,),),
        gram=((Fraction(1),),),
    )


def _not_psd() -> SOSCertificate:
    return replace(
        _tiny_true(),
        statement="x0^2 <= 0 (bogus)",
        objective={(0, 0): Fraction(1)},
        gram=((Fraction(-1),),),
    )


_K0 = load_k0_golden()

SOS_GOLDEN_SUITE: list[tuple[SOSCertificate, Verdict]] = [
    (_K0, Verdict.PASS),
    (_tiny_true(), Verdict.PASS),
    (replace(_K0, bound=Fraction(49, 100)), Verdict.FAIL),
    (_not_psd(), Verdict.FAIL),
    (replace(_tiny_true(), gram=()), Verdict.FAIL),
]


def sos_suite_hash() -> str:
    """blake3 of a canonical JSON repr of the suite (certificates + verdicts)."""
    payload = json.dumps(
        [[certificate_to_json(c), v.value] for c, v in SOS_GOLDEN_SUITE],
        sort_keys=True,
        separators=(",", ":"),
    )
    return blake3(payload.encode("utf-8")).hexdigest()


def certify_sos(ledger: Ledger, verifier: SOSCertificateVerifier) -> Certification:
    """Run SOS_GOLDEN_SUITE through `verifier.verify(cert)` and stamp PASS iff
    every case matches its exact expected verdict."""

    def run(v: SOSCertificateVerifier, cert: SOSCertificate) -> VerifierResult:
        return v.verify(cert)

    return certify_with_suite(
        ledger, verifier, SOS_GOLDEN_SUITE, run, golden_suite_hash=sos_suite_hash()
    )

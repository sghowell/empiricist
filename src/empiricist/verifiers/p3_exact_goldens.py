"""P3_EXACT_GOLDEN_SUITE: P3ExactVerifier's mutation-resistant certification suite.

Cases (scheme, claim kwargs, expected verdict):
1. standard BSM claiming its exact vector (0, 0, 1, 1)                  -> PASS
2. Grice claiming (1/2, 1/2, 1, 1)                                       -> PASS
3. Grice claiming (1/2, 1/2, 1, 1) with require_all_identified           -> PASS
4. standard BSM claiming (0, 0, 1, 1) with require_all_identified        -> FAIL
   (phi+/phi- are never identified -- the all-four teeth)
5. standard BSM claiming (0, 0, 1/2, 1)                                  -> FAIL (mismatch)
6. Grice claiming (1/4, 1/2, 1, 1)                                       -> FAIL (mismatch)
7. a theta = 0.3 mesh claiming anything                                  -> FAIL (unsupported)
Cases 4-7 exercise three DIFFERENT failure branches (all-identified, exact
mismatch, outside the field). `p3_exact_suite_hash()` pins every stamp to this
exact suite content.
"""
from __future__ import annotations

import json
from fractions import Fraction
from typing import Any

from blake3 import blake3

from empiricist.domain.p3.exact import QR
from empiricist.domain.p3.interferometer import Mesh
from empiricist.domain.p3.known_schemes import grice_boosted_bsm, standard_bsm
from empiricist.domain.p3.scheme import BellScheme
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Certification, Verdict
from empiricist.verifiers.base import VerifierResult
from empiricist.verifiers.p3_exact import P3ExactVerifier, qr_to_json
from empiricist.verifiers.registry import certify_with_suite


def _vec(pp, pm, sp, sm) -> dict[str, QR]:
    return {
        "phi+": QR(Fraction(pp), Fraction(0)),
        "phi-": QR(Fraction(pm), Fraction(0)),
        "psi+": QR(Fraction(sp), Fraction(0)),
        "psi-": QR(Fraction(sm), Fraction(0)),
    }


_NON_OCTANT = BellScheme(
    n_modes=4, n_ancilla_photons=0, ancilla={},
    mesh=Mesh(n_modes=4, elements=(("bs", 0, 2, 0.3, 0.0), ("bs", 1, 3, 0.3, 0.0))),
)

P3_EXACT_GOLDEN_SUITE: list[tuple[BellScheme, dict[str, Any], Verdict]] = [
    (standard_bsm(), {"claimed_success": _vec(0, 0, 1, 1)}, Verdict.PASS),
    (grice_boosted_bsm(), {"claimed_success": _vec("1/2", "1/2", 1, 1)}, Verdict.PASS),
    (
        grice_boosted_bsm(),
        {"claimed_success": _vec("1/2", "1/2", 1, 1), "require_all_identified": True},
        Verdict.PASS,
    ),
    (
        standard_bsm(),
        {"claimed_success": _vec(0, 0, 1, 1), "require_all_identified": True},
        Verdict.FAIL,
    ),
    (standard_bsm(), {"claimed_success": _vec(0, 0, "1/2", 1)}, Verdict.FAIL),
    (grice_boosted_bsm(), {"claimed_success": _vec("1/4", "1/2", 1, 1)}, Verdict.FAIL),
    (_NON_OCTANT, {"claimed_success": _vec(0, 0, 1, 1)}, Verdict.FAIL),
]


def _canon_scheme(scheme: BellScheme) -> dict[str, Any]:
    return {
        "n_modes": scheme.n_modes,
        "n_ancilla_photons": scheme.n_ancilla_photons,
        "ancilla": sorted(
            [list(p), [a.real, a.imag]] for p, a in
            ((tuple(p), complex(a)) for p, a in scheme.ancilla.items())
        ),
        "mesh": [list(el) for el in scheme.mesh.elements],
    }


def _canon_claim(claim: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "claimed_success": {b: qr_to_json(q) for b, q in sorted(claim["claimed_success"].items())}
    }
    if "require_all_identified" in claim:
        out["require_all_identified"] = bool(claim["require_all_identified"])
    return out


def p3_exact_suite_hash() -> str:
    payload = json.dumps(
        [[_canon_scheme(s), _canon_claim(c), v.value] for s, c, v in P3_EXACT_GOLDEN_SUITE],
        sort_keys=True,
        separators=(",", ":"),
    )
    return blake3(payload.encode("utf-8")).hexdigest()


def certify_p3_exact(ledger: Ledger, verifier: P3ExactVerifier) -> Certification:
    def run(v: P3ExactVerifier, case: tuple[BellScheme, dict[str, Any]]) -> VerifierResult:
        scheme, claim = case
        return v.verify(scheme, **claim)

    suite = [((s, c), expected) for s, c, expected in P3_EXACT_GOLDEN_SUITE]
    return certify_with_suite(
        ledger, verifier, suite, run, golden_suite_hash=p3_exact_suite_hash()
    )

"""P3_EXACT_GOLDEN_SUITE: P3ExactVerifier's mutation-resistant certification suite.

Cases (witness JSON, claim kwargs, expected verdict):
1. standard BSM claiming its exact vector (0, 0, 1, 1)                  -> PASS
2. Grice claiming (1/2, 1/2, 1, 1)                                       -> PASS
3. Grice claiming (1/2, 1/2, 1, 1) with require_all_identified           -> PASS
4. standard BSM on 6 modes with a two-photon ancilla |2,0> parked in
   mode 4 (occupation 2: the 1/sqrt(2!) factor is load-bearing), claiming
   its true vector (0, 0, 1, 1)                                          -> PASS
5. standard BSM claiming (0, 0, 1, 1) with require_all_identified        -> FAIL
   (phi+/phi- are never identified -- the all-four teeth)
6. standard BSM claiming (0, 0, 1/2, 1)                                  -> FAIL (mismatch)
7. Grice claiming (1/4, 1/2, 1, 1)                                       -> FAIL (mismatch)
8. Grice with the WHOLE isometry doubled, claiming (128, 128, 256, 256)
   -- exactly what a checker that skipped the isometry test would compute -> FAIL (invalid)
9. Grice with an un-normalised ancilla (both amplitudes 1), claiming
   (1, 1, 2, 2) -- what a checker that skipped the norm test computes   -> FAIL (invalid)
10. a k = 3 witness with three ancilla photons in one mode               -> FAIL (unsupported)
The must-fail claims in 8-9 are deliberately the BROKEN code's own answers, so a
verifier whose witness validation regressed would PASS them and lose its stamp;
case 4 pins the input-factorial factor the same way. `p3_exact_suite_hash()` pins
every stamp to this exact suite content.
"""
from __future__ import annotations

import json
from fractions import Fraction
from math import pi
from typing import Any

from blake3 import blake3

from empiricist.domain.p3.exact import Alg, ExactWitness, alg_to_json, witness_to_json
from empiricist.domain.p3.interferometer import Mesh
from empiricist.domain.p3.known_schemes import grice_boosted_bsm, standard_bsm
from empiricist.domain.p3.scheme import BellScheme
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Certification, Verdict
from empiricist.verifiers.base import VerifierResult
from empiricist.verifiers.p3_exact import P3ExactVerifier
from empiricist.verifiers.registry import certify_with_suite


def _vec(pp, pm, sp, sm) -> dict[str, Alg]:
    return {
        "phi+": Alg.rational(Fraction(pp)),
        "phi-": Alg.rational(Fraction(pm)),
        "psi+": Alg.rational(Fraction(sp)),
        "psi-": Alg.rational(Fraction(sm)),
    }


_STD = witness_to_json(ExactWitness.from_mesh(standard_bsm()))
_GRICE = witness_to_json(ExactWitness.from_mesh(grice_boosted_bsm()))
# Standard BSM on modes 0-3 of a 6-mode device; two ancilla photons sit in mode 4
# and never interfere: the Bell vector is (0, 0, 1, 1) exactly, and the amplitude
# of the |...,2,0> input term carries 1/sqrt(2!).
_STD_K2 = witness_to_json(ExactWitness.from_mesh(BellScheme(
    n_modes=6, n_ancilla_photons=2, ancilla={(2, 0): 1.0 + 0j},
    mesh=Mesh(n_modes=6, elements=(("bs", 0, 2, pi / 4, 0.0), ("bs", 1, 3, pi / 4, 0.0))),
)))
_K3 = witness_to_json(ExactWitness.from_mesh(BellScheme(
    n_modes=5, n_ancilla_photons=3, ancilla={(3,): 1.0 + 0j},
    mesh=Mesh(n_modes=5, elements=(("bs", 0, 2, pi / 4, 0.0), ("bs", 1, 3, pi / 4, 0.0))),
)))


def _doubled(w: dict) -> dict:
    """Every isometry entry doubled: not an isometry; a checker without the
    isometry test would report the vector scaled by 2^(2*photons) = 256 for Grice."""
    out = json.loads(json.dumps(w))
    out["isometry"] = [
        [[[d, str(Fraction(a) * 2), str(Fraction(b) * 2)] for d, a, b in entry] for entry in row]
        for row in out["isometry"]
    ]
    return out


def _bad_ancilla(w: dict) -> dict:
    """Both Grice ancilla amplitudes set to 1 (norm^2 = 2): a checker without the
    normalisation test would report (1, 1, 2, 2)."""
    out = json.loads(json.dumps(w))
    out["ancilla"] = [[p, alg_to_json(Alg.rational(1))] for p, _ in out["ancilla"]]
    return out


P3_EXACT_GOLDEN_SUITE: list[tuple[dict, dict[str, Any], Verdict]] = [
    (_STD, {"claimed_success": _vec(0, 0, 1, 1)}, Verdict.PASS),
    (_GRICE, {"claimed_success": _vec("1/2", "1/2", 1, 1)}, Verdict.PASS),
    (
        _GRICE,
        {"claimed_success": _vec("1/2", "1/2", 1, 1), "require_all_identified": True},
        Verdict.PASS,
    ),
    (_STD_K2, {"claimed_success": _vec(0, 0, 1, 1)}, Verdict.PASS),
    (_STD, {"claimed_success": _vec(0, 0, 1, 1), "require_all_identified": True}, Verdict.FAIL),
    (_STD, {"claimed_success": _vec(0, 0, "1/2", 1)}, Verdict.FAIL),
    (_GRICE, {"claimed_success": _vec("1/4", "1/2", 1, 1)}, Verdict.FAIL),
    (_doubled(_GRICE), {"claimed_success": _vec(128, 128, 256, 256)}, Verdict.FAIL),
    (_bad_ancilla(_GRICE), {"claimed_success": _vec(1, 1, 2, 2)}, Verdict.FAIL),
    (_K3, {"claimed_success": _vec(0, 0, 1, 1)}, Verdict.FAIL),
]


def _canon_claim(claim: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "claimed_success": {b: alg_to_json(q) for b, q in sorted(claim["claimed_success"].items())}
    }
    if "require_all_identified" in claim:
        out["require_all_identified"] = bool(claim["require_all_identified"])
    return out


def p3_exact_suite_hash() -> str:
    payload = json.dumps(
        [[w, _canon_claim(c), v.value] for w, c, v in P3_EXACT_GOLDEN_SUITE],
        sort_keys=True,
        separators=(",", ":"),
    )
    return blake3(payload.encode("utf-8")).hexdigest()


def certify_p3_exact(ledger: Ledger, verifier: P3ExactVerifier) -> Certification:
    def run(v: P3ExactVerifier, case: tuple[dict, dict[str, Any]]) -> VerifierResult:
        witness_json, claim = case
        return v.verify(witness_json, **claim)

    suite = [((w, c), expected) for w, c, expected in P3_EXACT_GOLDEN_SUITE]
    return certify_with_suite(
        ledger, verifier, suite, run, golden_suite_hash=p3_exact_suite_hash()
    )

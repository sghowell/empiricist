"""P3_EXACT_GOLDEN_SUITE: P3ExactVerifier's mutation-resistant certification suite.

Cases (witness JSON, claim kwargs, expected verdict):
1. standard BSM claiming its exact vector (0, 0, 1, 1)                  -> PASS
2. Grice claiming (1/2, 1/2, 1, 1)                                       -> PASS
3. Grice claiming (1/2, 1/2, 1, 1) with require_all_identified           -> PASS
4. standard BSM claiming (0, 0, 1, 1) with require_all_identified        -> FAIL
   (phi+/phi- are never identified -- the all-four teeth)
5. standard BSM claiming (0, 0, 1/2, 1)                                  -> FAIL (mismatch)
6. Grice claiming (1/4, 1/2, 1, 1)                                       -> FAIL (mismatch)
7. Grice with one isometry entry scaled by 2 (not an isometry)           -> FAIL (invalid)
8. a witness whose ancilla is not exactly normalised                     -> FAIL (invalid)
Cases 4-8 exercise three DIFFERENT failure branches (all-identified, exact
mismatch, invalid witness). `p3_exact_suite_hash()` pins every stamp to this
exact suite content.
"""
from __future__ import annotations

import json
from fractions import Fraction
from typing import Any

from blake3 import blake3

from empiricist.domain.p3.exact import Alg, ExactWitness, alg_to_json, witness_to_json
from empiricist.domain.p3.known_schemes import grice_boosted_bsm, standard_bsm
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


def _scaled_entry(w: dict) -> dict:
    """Grice with entry (0, 0) doubled: no longer an isometry."""
    out = json.loads(json.dumps(w))
    out["isometry"][0][0] = [[d, str(Fraction(a) * 2), str(Fraction(b) * 2)]
                             for d, a, b in out["isometry"][0][0]]
    return out


def _bad_ancilla(w: dict) -> dict:
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
    (_STD, {"claimed_success": _vec(0, 0, 1, 1), "require_all_identified": True}, Verdict.FAIL),
    (_STD, {"claimed_success": _vec(0, 0, "1/2", 1)}, Verdict.FAIL),
    (_GRICE, {"claimed_success": _vec("1/4", "1/2", 1, 1)}, Verdict.FAIL),
    (_scaled_entry(_GRICE), {"claimed_success": _vec("1/2", "1/2", 1, 1)}, Verdict.FAIL),
    (_bad_ancilla(_GRICE), {"claimed_success": _vec("1/2", "1/2", 1, 1)}, Verdict.FAIL),
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

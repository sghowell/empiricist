"""P3_GOLDEN_SUITE: P3SchemeVerifier's own mutation-resistant certification suite
(spec §7's discipline, applied to a verifier whose `verify()` shape doesn't fit
`registry.Registry`/`P5_GOLDEN_SUITE` -- see `verifiers/p3_scheme.py`'s docstring,
the same reason `verifiers/lean_goldens.py` exists for `LeanVerifier`). Every case
must produce its exact `expected_verdict` to earn a PASS stamp via `certify_p3`;
ERROR/TIMEOUT never satisfy a must-FAIL case.

Cases (scheme, claim kwargs, expected_verdict):

1. `standard_bsm()` claiming its published p_avg (0.5) -> True. The textbook
   ancilla-free BSM (test_p3_goldens.py's own golden), through the FULL agreed
   contract.
2. `grice_boosted_bsm()` claiming its published p_avg (0.75) -> True.
3. `grice_boosted_bsm()` claiming BOTH p_avg (0.75) and p_min (0.5) -> True --
   pins that a multi-field claim also certifies (not just the single-field case).
4. `standard_bsm()` claiming a p_avg (0.9) it does NOT achieve -> False. The
   must-fail teeth (P5 precedent: a suite that can't fail certifies nothing): an
   honest engine agreement that legitimately FAILs a false claim.
5. A scheme whose claim itself is malformed (`claimed_max_leakage` negative) ->
   False. Exercises the INVALID-claim branch of `verify_scheme_agreed`, mapped by
   `P3SchemeVerifier` to FAIL (`details["detail"]` prefixed `"invalid: "`) -- a
   verifier that always said PASS on a well-formed scheme would still need to
   correctly FAIL this to certify.
6. A scheme whose STRUCTURE itself is malformed (mesh/scheme mode mismatch) ->
   False. Exercises the INVALID-scheme branch (a distinct code path from case 5:
   `scheme.validate()` raising rather than the claim-finiteness guard).
7. A near-degenerate scheme with positive sub-assignment-threshold leakage,
   claiming the standard p_avg under the default zero leakage budget -> False.
   This pins the critical leakage boundary into certification.

Cases 5-7 are deliberately independent must-fail mechanisms (bad claim, bad
scheme, and a physically well-formed but leaky near-threshold scheme), not
repeated cases. Each exercises a different branch of the thing being certified.

`p3_suite_hash()` is a blake3 digest of a canonical (JSON) repr of the suite;
`certify_p3` pins every stamp to this exact hash, so editing the suite invalidates
every existing P3 stamp rather than letting a certification earned against a
DIFFERENT suite silently continue to read as trust (same rule as
`verifiers/goldens.py`/`verifiers/lean_goldens.py`).
"""

from __future__ import annotations

import json
from math import pi
from typing import TYPE_CHECKING, Any

from blake3 import blake3

from empiricist.domain.p3.interferometer import Mesh
from empiricist.domain.p3.known_schemes import grice_boosted_bsm, standard_bsm
from empiricist.domain.p3.scheme import BellScheme
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Certification, Verdict
from empiricist.verifiers.base import VerifierResult
from empiricist.verifiers.registry import certify_with_suite

if TYPE_CHECKING:
    from empiricist.verifiers.p3_scheme import P3SchemeVerifier

# Case 6: mesh/scheme mode mismatch -- BellScheme.validate() raises ValueError
# ("mesh/scheme mode mismatch") before either engine ever runs, so
# verify_scheme_agreed screens it INVALID rather than dispatching to the engines.
_MODE_MISMATCH_SCHEME = BellScheme(
    n_modes=4,
    n_ancilla_photons=0,
    ancilla={},
    mesh=Mesh(n_modes=5, elements=()),
)

# A weak coupling hides 5e-13 of probability per wrong-label pattern below the
# assignment threshold while accumulating about 2e-12 total leakage.
_NEAR_THRESHOLD_LEAKY_SCHEME = BellScheme(
    n_modes=4,
    n_ancilla_photons=0,
    ancilla={},
    mesh=Mesh(
        n_modes=4,
        elements=(
            ("bs", 0, 1, 1e-6, 0.0),
            ("bs", 0, 2, pi / 4, 0.0),
            ("bs", 1, 3, pi / 4, 0.0),
        ),
    ),
)

P3_GOLDEN_SUITE: list[tuple[BellScheme, dict[str, Any], Verdict]] = [
    (standard_bsm(), {"claimed_p_avg": 0.5}, Verdict.PASS),
    (grice_boosted_bsm(), {"claimed_p_avg": 0.75}, Verdict.PASS),
    (
        grice_boosted_bsm(),
        {"claimed_p_avg": 0.75, "claimed_p_min": 0.5},
        Verdict.PASS,
    ),
    (standard_bsm(), {"claimed_p_avg": 0.9}, Verdict.FAIL),
    (standard_bsm(), {"claimed_max_leakage": -1.0}, Verdict.FAIL),
    (_MODE_MISMATCH_SCHEME, {}, Verdict.FAIL),
    (_NEAR_THRESHOLD_LEAKY_SCHEME, {"claimed_p_avg": 0.5}, Verdict.FAIL),
]


def _canon_scheme(scheme: BellScheme) -> dict[str, Any]:
    return {
        "n_modes": scheme.n_modes,
        "n_ancilla_photons": scheme.n_ancilla_photons,
        "ancilla": sorted(
            [list(pattern), [amp.real, amp.imag]]
            for pattern, amp in scheme.ancilla.items()
        ),
        "mesh_n_modes": scheme.mesh.n_modes,
        "mesh_elements": [list(el) for el in scheme.mesh.elements],
    }


def p3_suite_hash() -> str:
    """blake3 hex digest of a canonical JSON repr of P3_GOLDEN_SUITE (each case's
    scheme structure, claim kwargs, and expected verdict)."""
    canon = [
        {
            "scheme": _canon_scheme(scheme),
            "claim": {
                "claimed_p_min": kwargs.get("claimed_p_min"),
                "claimed_p_avg": kwargs.get("claimed_p_avg"),
                "claimed_max_leakage": kwargs.get("claimed_max_leakage", 0.0),
            },
            "expected_verdict": expected.value,
        }
        for scheme, kwargs, expected in P3_GOLDEN_SUITE
    ]
    payload = json.dumps(canon, sort_keys=True, separators=(",", ":"))
    return blake3(payload.encode("utf-8")).hexdigest()


def certify_p3(ledger: Ledger, verifier: P3SchemeVerifier) -> Certification:
    """Run P3_GOLDEN_SUITE through `verifier.verify(scheme, **kwargs)` and stamp a
    Certification (PASS iff every case matches its exact expected verdict) --
    P3SchemeVerifier's own certify path, parallel to but independent of
    `registry.Registry.certify()` (same relationship `certify_lean` has to it)."""

    def run(v: P3SchemeVerifier, case: tuple[BellScheme, dict[str, Any]]) -> VerifierResult:
        scheme, kwargs = case
        return v.verify(scheme, **kwargs)

    suite = [((scheme, kwargs), expected) for scheme, kwargs, expected in P3_GOLDEN_SUITE]
    return certify_with_suite(ledger, verifier, suite, run, golden_suite_hash=p3_suite_hash())

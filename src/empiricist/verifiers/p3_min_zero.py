"""The predicate of the P3 conjecture "k = 0 forces min_B p_B = 0", checked exactly on one
witness (M27b follow-up to the 2026-10-26 referee report).

`check_k0_min_zero(payload)` reads `payload["witness"]` (the exact-witness JSON of
`domain.p3.exact`; other payload keys are ignored, so one evidence file can serve this
verifier and `p3_exact_witness` alike) and returns

- PASS  -- the witness is a valid exact k = 0 scheme (an exact isometry over the four
           dual-rail input modes, any number of vacuum output modes) and its exact success
           vector, under the maximal unambiguous assignment `exact_report` derives, has a
           zero entry: the conjecture's prediction holds on this scheme;
- FAIL  -- a valid exact k = 0 scheme whose four exact successes are all positive: a
           counterexample, so a FAIL may refute the conjecture;
- ERROR -- anything else: malformed JSON, an off-field or non-isometric witness, k != 0.
           Never FAIL, so a defective file can never refute anything.

The maximal assignment is the right one for this predicate: any unambiguous assignment's
success vector is dominated entrywise by it, so "some Bell state has success 0 under every
assignment" holds iff it holds under the maximal one.

`two_branch_witness(w1)` builds the referee's counterexample family: V = [sqrt(w1) H;
sqrt(1 - w1) H X_A] with H the standard 4 x 4 Bell analyser and X_A swapping qubit A's rails;
each branch identifies one Bell pair (Psi+- in the first, Phi+- in the second) when both
photons take it, so the exact success vector is (w2^2, w2^2, w1^2, w1^2) for (phi+, phi-,
psi+, psi-), w2 = 1 - w1 -- (1/4, 1/4, 1/4, 1/4) at w1 = 1/2.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any

from empiricist.domain.p3.exact import (
    Alg,
    ExactUnsupported,
    ExactWitness,
    alg_to_json,
    exact_report,
    witness_from_json,
)
from empiricist.domain.p3.scheme import BELL_LABELS
from empiricist.ledger.models import Verdict
from empiricist.verifiers.base import VerifierResult

_H = ((1, 0, 1, 0), (0, 1, 0, 1), (1, 0, -1, 0), (0, 1, 0, -1))       # sqrt2 * H
_HX = ((0, 1, 1, 0), (1, 0, 0, 1), (0, 1, -1, 0), (1, 0, 0, -1))      # sqrt2 * H X_A


def two_branch_witness(w1: Fraction = Fraction(1, 2)) -> ExactWitness:
    """The eight-mode k = 0 witness [sqrt(w1) H; sqrt(1 - w1) H X_A] (exact, validated)."""
    w1 = Fraction(w1)
    if not 0 < w1 < 1:
        raise ValueError("branch weight must lie strictly between 0 and 1")
    a1 = Alg.sqrt_rational(w1 / 2)          # sqrt(w1) / sqrt2
    a2 = Alg.sqrt_rational((1 - w1) / 2)
    rows = [tuple(a1.scale(x) for x in r) for r in _H]
    rows += [tuple(a2.scale(x) for x in r) for r in _HX]
    w = ExactWitness(n_modes=8, n_ancilla_photons=0, isometry=tuple(rows), ancilla={})
    w.validate()
    return w


def check_k0_min_zero(payload: Any) -> VerifierResult:
    """PASS / FAIL / ERROR as the module docstring states. Total: never raises."""
    try:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a JSON object with a 'witness'")
        witness: ExactWitness = witness_from_json(payload["witness"])
    except Exception as exc:  # noqa: BLE001 - a defective file is an ERROR, never a FAIL
        return VerifierResult(
            verdict=Verdict.ERROR,
            details={"error": f"invalid witness: {type(exc).__name__}: {exc}"},
        )
    if witness.n_ancilla_photons != 0:
        return VerifierResult(
            verdict=Verdict.ERROR,
            details={"error": f"the predicate is about k = 0 schemes; witness has "
                              f"k = {witness.n_ancilla_photons}"},
        )
    try:
        rep = exact_report(witness)
    except ExactUnsupported as exc:
        return VerifierResult(verdict=Verdict.ERROR, details={"error": f"unsupported: {exc}"})
    except Exception as exc:  # noqa: BLE001
        return VerifierResult(verdict=Verdict.ERROR,
                              details={"error": f"{type(exc).__name__}: {exc}"})
    details: dict[str, Any] = {
        "n_modes": witness.n_modes,
        "k": witness.n_ancilla_photons,
        "success": {b: alg_to_json(rep.success[b]) for b in BELL_LABELS},
        "p_min": alg_to_json(rep.p_min),
        "n_identifying_patterns": len(rep.assignment),
    }
    if any(rep.success[b].is_zero() for b in BELL_LABELS):
        details["detail"] = "some Bell state has exact success 0: min_B p_B = 0 holds"
        return VerifierResult(verdict=Verdict.PASS, details=details)
    details["detail"] = (
        "every Bell state has positive exact success: min_B p_B > 0 at k = 0 "
        "(a counterexample to 'k = 0 forces min_B p_B = 0')"
    )
    return VerifierResult(verdict=Verdict.FAIL, details=details)

"""The P3 golden certificate (M20c Task 4): an EXACT SOS certificate of the
assignment-fixed p_avg <= 1/2 bound for all U in U(4), pinned as JSON and
re-verified here by the exact rational checker.

This test uses ONLY the trust-side checker (`certificates.core`) plus the target
definitions (`certificates.p3_targets`) -- no cvxpy, so it runs in the fast
suite and NEVER skips (acceptance criterion 1: the checker never skips). It is
the standing warrant that the pinned certificate is sound: the checker proves,
in exact `Fraction` arithmetic, that `objective <= 1/2` on the stated variety.

Provenance of the golden (see `tests/goldens/p3_k0_standard_assignment.json`'s
`statement` and the M20c Task 4 report): the numeric SDP pipeline
(`solve_sos` + `rationalize`) was exercised but could not land this particular
certificate -- the full U(4) SDP (561-monomial Gram, ~58,905 identity rows)
exceeded the SCS solve budget, and the real-orthogonal restriction converged
numerically (bound ~0.5000) but its TIGHT boundary Gram would not rationalize
(the rounded Gram's residual falls outside the constraint module; margin
~3e-6 < rounding resolution). The pinned certificate was instead constructed
exactly from the probability-conservation identity (`sum_all_S Pr[S|B] = 1` on
the unitary variety, with each `Pr = re^2 + im^2` a manifest sum of squares) --
the actual Calsamiglia-Lutkenhaus content -- and is verified here by the same
trusted checker the SDP pipeline targets. Either route is sound because the
checker, not the finder, is the trust boundary.
"""

import json
from fractions import Fraction
from pathlib import Path

from empiricist.certificates.core import SOSCertificate, check_certificate
from empiricist.certificates.p3_targets import (
    standard_assignment_objective,
    unambiguity_constraints,
    unitarity_constraints,
)

GOLDEN_PATH = Path(__file__).parent / "goldens" / "p3_k0_standard_assignment.json"


def _mono(key: str) -> tuple[int, ...]:
    return tuple(int(x) for x in key.split(",")) if key else ()


def _poly(d: dict[str, str]) -> dict[tuple[int, ...], Fraction]:
    return {_mono(k): Fraction(v) for k, v in d.items()}


def _load_certificate() -> SOSCertificate:
    data = json.loads(GOLDEN_PATH.read_text())
    return SOSCertificate(
        statement=data["statement"],
        variables=tuple(data["variables"]),
        objective=_poly(data["objective"]),
        bound=Fraction(data["bound"]),
        constraints=tuple(_poly(c) for c in data["constraints"]),
        multipliers=tuple(_poly(m) for m in data["multipliers"]),
        gram_basis=tuple(tuple(m) for m in data["gram_basis"]),
        gram=tuple(tuple(Fraction(v) for v in row) for row in data["gram"]),
    )


def test_golden_certificate_passes_exact_checker():
    cert = _load_certificate()
    result = check_certificate(cert)
    assert result.ok, result


def test_golden_bound_is_the_known_tight_value():
    cert = _load_certificate()
    # The task's acceptance: bound <= 1/2 + 1/100. This golden is EXACTLY tight.
    assert cert.bound <= Fraction(1, 2) + Fraction(1, 100)
    assert cert.bound == Fraction(1, 2)


def test_golden_certifies_the_actual_target():
    """Tie the pinned certificate to the LIVE target definitions in
    `p3_targets`: if the objective or constraint polynomials ever drift, this
    catches that the golden certifies a stale problem (it would still pass the
    checker, but no longer bound the intended p_avg)."""
    cert = _load_certificate()
    assert cert.objective == standard_assignment_objective(4)
    unitarity = unitarity_constraints(4)
    unambiguity = unambiguity_constraints(4)
    assert len(cert.constraints) == len(unitarity) + len(unambiguity)
    assert list(cert.constraints[: len(unitarity)]) == unitarity
    assert list(cert.constraints[len(unitarity):]) == unambiguity


def test_golden_gram_is_square_and_matches_basis():
    cert = _load_certificate()
    n = len(cert.gram_basis)
    assert len(cert.gram) == n
    assert all(len(row) == n for row in cert.gram)
    assert len(cert.variables) == 32  # full U(4): 32 real entry variables

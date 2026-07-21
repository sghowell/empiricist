"""Tests for the SDP solve + rationalization pipeline (M20c Task 3, the
SEARCH side). Skips cleanly if `cvxpy` is not installed (`certs` dependency
group; `uv sync --group certs`) -- the checker side (`test_certificates_core.py`)
never skips and must remain importable/runnable without cvxpy at all."""

from fractions import Fraction

import pytest

cvxpy = pytest.importorskip("cvxpy")

from empiricist.certificates.core import check_certificate  # noqa: E402
from empiricist.certificates.solve import (  # noqa: E402
    NumericCertificate,
    rationalize,
    solve_sos,
)

# ---------------------------------------------------------------------------
# Toy 1: bound x <= 1 on {x^2 - 1 = 0} (the same toy hand-verified in
# test_certificates_core.py).
# ---------------------------------------------------------------------------

TOY1_OBJECTIVE = {(0,): Fraction(1)}
TOY1_CONSTRAINTS = ({(0, 0): Fraction(1), (): Fraction(-1)},)
TOY1_VARIABLES = ("x",)


def test_solve_sos_toy_finds_bound_near_one():
    num_cert = solve_sos(TOY1_OBJECTIVE, TOY1_CONSTRAINTS, TOY1_VARIABLES, degree=1)
    assert num_cert is not None
    assert 0.9 < num_cert.bound < 1.2
    assert num_cert.gram_basis == ((), (0,))


def test_rationalize_toy_passes_checker():
    num_cert = solve_sos(TOY1_OBJECTIVE, TOY1_CONSTRAINTS, TOY1_VARIABLES, degree=1)
    assert num_cert is not None
    cert = rationalize(num_cert, TOY1_OBJECTIVE, TOY1_CONSTRAINTS, TOY1_VARIABLES)
    assert cert is not None
    result = check_certificate(cert)
    assert result.ok, result
    assert Fraction(1) <= cert.bound <= Fraction(2)


# ---------------------------------------------------------------------------
# Toy 2: two constraints -- minimize a bound on x + y over
# {x^2 - 1 = 0, y^2 - 1 = 0}. The true minimal bound is exactly 2 (at
# x=y=1, objective = 2, so no valid bound can be smaller).
# ---------------------------------------------------------------------------

TOY2_OBJECTIVE = {(0,): Fraction(1), (1,): Fraction(1)}
TOY2_CONSTRAINTS = (
    {(0, 0): Fraction(1), (): Fraction(-1)},
    {(1, 1): Fraction(1), (): Fraction(-1)},
)
TOY2_VARIABLES = ("x", "y")


def test_solve_sos_two_constraints_finds_bound_near_two():
    num_cert = solve_sos(TOY2_OBJECTIVE, TOY2_CONSTRAINTS, TOY2_VARIABLES, degree=1)
    assert num_cert is not None
    assert 1.8 < num_cert.bound < 2.2


def test_rationalize_two_constraints_passes_checker():
    num_cert = solve_sos(TOY2_OBJECTIVE, TOY2_CONSTRAINTS, TOY2_VARIABLES, degree=1)
    assert num_cert is not None
    cert = rationalize(num_cert, TOY2_OBJECTIVE, TOY2_CONSTRAINTS, TOY2_VARIABLES)
    assert cert is not None
    result = check_certificate(cert)
    assert result.ok, result
    assert cert.bound >= Fraction(2)


# ---------------------------------------------------------------------------
# rationalize must never raise, even on a corrupted NumericCertificate.
# ---------------------------------------------------------------------------


def test_rationalize_returns_none_on_corrupted_multiplier_shapes():
    num_cert = solve_sos(TOY1_OBJECTIVE, TOY1_CONSTRAINTS, TOY1_VARIABLES, degree=1)
    assert num_cert is not None
    # Truncate the multiplier structure so it no longer lines up with
    # TOY1_CONSTRAINTS (one constraint, zero multiplier bases supplied):
    # the identity can no longer possibly be repaired.
    corrupted = NumericCertificate(
        variables=num_cert.variables,
        degree=num_cert.degree,
        bound=num_cert.bound,
        gram_basis=num_cert.gram_basis,
        gram=num_cert.gram,
        multiplier_basis=(),
        multiplier_coeffs=(),
    )
    result = rationalize(corrupted, TOY1_OBJECTIVE, TOY1_CONSTRAINTS, TOY1_VARIABLES)
    assert result is None


def test_rationalize_returns_none_on_wrong_gram_shape():
    num_cert = solve_sos(TOY1_OBJECTIVE, TOY1_CONSTRAINTS, TOY1_VARIABLES, degree=1)
    assert num_cert is not None
    # gram_basis says 2x2, but gram is a mismatched 1x1 -- pure garbage.
    corrupted = NumericCertificate(
        variables=num_cert.variables,
        degree=num_cert.degree,
        bound=num_cert.bound,
        gram_basis=num_cert.gram_basis,
        gram=((1.0,),),
        multiplier_basis=num_cert.multiplier_basis,
        multiplier_coeffs=num_cert.multiplier_coeffs,
    )
    result = rationalize(corrupted, TOY1_OBJECTIVE, TOY1_CONSTRAINTS, TOY1_VARIABLES)
    assert result is None


def test_rationalize_never_raises_on_totally_bogus_input():
    bogus = object()
    try:
        result = rationalize(bogus, TOY1_OBJECTIVE, TOY1_CONSTRAINTS, TOY1_VARIABLES)
    except Exception as exc:  # pragma: no cover - must never happen
        pytest.fail(f"rationalize raised on bogus input: {exc!r}")
    assert result is None

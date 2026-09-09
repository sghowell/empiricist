from math import factorial

import pytest
import sympy as sp
from p8a_remainder import mode_bounds


def test_remainder_all_mode_and_green_identities():
    assert all(sp.simplify(value) == 0 for value in mode_bounds.identities().values())


def test_remainder_zero_potential_gives_zero_error():
    values = mode_bounds.bounds([0]*6, 3, 1)
    assert values["integrated_remainder_derivatives"] == [0]*3
    assert values["IR_exponential_cap"] == values["UV_exponential_cap"] == 1


def test_remainder_rational_cap_is_checked_not_assumed():
    values = mode_bounds.bounds([sp.Rational(1, 1000)]*6, 3, 1, rational_caps=True)
    assert values["IR_exponential_cap"] == values["UV_exponential_cap"] == 2
    with pytest.raises(ValueError, match="exponential caps"):
        mode_bounds.bounds([1]*6, 3, 1, rational_caps=True)


@pytest.mark.parametrize("value", [0.1, sp.oo, sp.nan, -1, sp.Symbol("unknown")])
def test_remainder_unproved_or_inexact_parameter_rejected(value):
    with pytest.raises(ValueError):
        mode_bounds.bounds([value]*6, 1, 1)


@pytest.mark.parametrize("duration,split", [(0, 1), (1, 0), (-1, 1), (1, -1)])
def test_remainder_positive_span_and_split_required(duration, split):
    with pytest.raises(ValueError):
        mode_bounds.bounds([1]*6, duration, split)


def test_remainder_missing_jet_rejected():
    with pytest.raises(ValueError, match="six"):
        mode_bounds.bounds([1]*5, 1, 1)


def test_remainder_no_isolated_linear_fifth_jet_in_nonlinear_error():
    values = mode_bounds.bounds([0, 0, 0, 0, 0, 1], 3, 1)
    assert values["UV_quadratic_residual_coefficient"] == 0
    assert values["integrated_remainder_derivatives"] == [0]*3


def test_remainder_units_and_quadratic_amplitude_scaling():
    delta, length = sp.symbols("delta length", positive=True)
    b = [sp.Integer(j+1) for j in range(6)]
    normalized = mode_bounds.polynomial_bounds([delta*v for v in b], sp.Integer(3),
                                                sp.Integer(1), sp.Integer(2), sp.Integer(2))
    scaled = mode_bounds.polynomial_bounds([delta*v/length**(j+2) for j, v in enumerate(b)],
                                           3*length, 1/length, sp.Integer(2), sp.Integer(2))
    for j, value in enumerate(normalized["integrated_remainder_derivatives"]):
        assert sp.expand(scaled["integrated_remainder_derivatives"][j]*length**(j+2)-value) == 0
        polynomial = sp.Poly(value, delta)
        assert min(power[0] for power, _ in polynomial.terms()) == 2
        assert all(coefficient > 0 for coefficient in polynomial.all_coeffs()[:-2])


def test_remainder_ir_series_factorial_controls():
    # Finite regression controls supplement, rather than replace, the
    # coefficientwise all-n inequalities in the written Volterra proof.
    for n in range(12):
        assert factorial(2*n) >= 2**n*factorial(n)
        assert factorial(2*n+4) >= 24*factorial(2*n)
    partial = sum(sp.Rational(1, 2**n*factorial(n)) for n in range(8))
    # Tail first omitted term and subsequent ratio <=1/18 enclose exp(1/2).
    tail = sp.Rational(1, 2**8*factorial(8))*sp.Rational(18, 17)
    assert partial+tail < 2

"""State-specific A.4 quantitative interval checks."""

from fractions import Fraction

import pytest
import sympy as sp
from p8a_asymptotics import bounds, independent, verify


def example_couplings(**changes):
    params = {"a": 1, "kappa": 1, "b": 1, "ell": 0, "radiation_c": 3, "hbar": 1}
    params.update(changes)
    return bounds.Couplings(**params)


def test_actual_coherent_state_interval_certified():
    result = verify.bounded_example()
    assert result["maximum_error"] == "1/10000"
    assert result["jet_bounds_derived_for_this_state"]
    assert result["oversized_cutoff_1_over_50_rejected"]


def test_coupling_terms_and_nonzero_jet_errors_independently_agree():
    jets = bounds.JetBounds(2, 3, 5, "1/2")
    params = example_couplings(a=2, kappa=3, b=4, ell=-5, radiation_c=6)
    eta = sp.Symbol("eta", positive=True)
    polynomial = bounds.error_polynomial(jets, params, eta)
    assert all(value >= 0 for value in sp.Poly(polynomial, eta).all_coeffs())
    assert sp.diff(polynomial, eta).is_positive
    actual = polynomial.subs(eta, sp.Rational(1, 10))
    expected = independent.error_at("1/10", m0=2, m1=3, m2=5,
                                    a=2, kappa=3, b=4, ell=-5, radiation_c=6)
    assert actual == sp.Rational(expected)


@pytest.mark.parametrize("cutoff", ["0", "-1", "2"])
def test_cutoff_domain_mismatch_rejected(cutoff):
    with pytest.raises(ValueError, match="inside"):
        bounds.certify_interval(bounds.JetBounds(1, 0, 0, 1), example_couplings(), cutoff)


def test_negative_margin_not_certified():
    with pytest.raises(ValueError, match="positivity"):
        bounds.certify_interval(bounds.JetBounds(1, 0, 0, 1), example_couplings(), "1/50")


@pytest.mark.parametrize("values", [(-1, 0, 0, 1), (0, -1, 0, 1), (0, 0, -1, 1), (0, 0, 0, 0)])
def test_invalid_jet_bounds_rejected(values):
    with pytest.raises(ValueError, match="bounds"):
        bounds.JetBounds(*values)


@pytest.mark.parametrize("name", ["a", "kappa", "b", "hbar"])
def test_nonpositive_physical_couplings_rejected(name):
    with pytest.raises(ValueError, match="Positive"):
        example_couplings(**{name: 0})


def test_negative_extra_radiation_not_silently_allowed():
    with pytest.raises(ValueError, match="nonnegative"):
        example_couplings(radiation_c=-1)


@pytest.mark.parametrize("value", [0.1, "nan", "inf", "1/0"])
def test_inexact_or_nonfinite_inputs_rejected(value):
    with pytest.raises((TypeError, ValueError), match="rational"):
        bounds.rational(value)


def test_coupling_sign_absolute_value_and_exact_input():
    assert bounds.rational("1/10") == Fraction(1, 10)
    jets = bounds.JetBounds(0, 0, 0, 1)
    assert bounds.error_polynomial(jets, example_couplings(ell=2), sp.Integer(1)) == 2
    assert bounds.error_polynomial(jets, example_couplings(ell=-2), sp.Integer(1)) == 2

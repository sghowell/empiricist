from fractions import Fraction

import pytest
import sympy as sp
from p8 import signs


def test_sturm_detects_hidden_negative_well():
    assert signs.sturm_positive([1, -1, 1])["roots"] == 0
    with pytest.raises(ValueError):
        signs.sturm_positive([1, -3, 1])


def test_sturm_finite_interval_and_repeated_roots():
    assert signs.sturm_positive([1, -3, 1], upper=Fraction(1, 4))["roots"] == 0
    with pytest.raises(ValueError):
        signs.sturm_positive([1, -2, 1])


def test_zero_and_pole_are_not_silently_removed_at_gamma():
    t = sp.Symbol("t")
    with pytest.raises(ValueError):
        signs.even_rational_positive(1/t**2, t)
    assert signs.even_rational_positive(1/t**2, t, punctured=True)["denominator_zero_order_in_t_squared"] == 1


def test_Bernstein_bounds_are_exact():
    u, v = sp.symbols("u v")
    bounds = signs.bernstein_bounds(2-u+u**2*v, (u, v))
    assert Fraction(bounds["lower"]) == 1
    assert Fraction(bounds["upper"]) == 2


def test_canonical_tail_rate_and_nondecaying_control():
    t, X = sp.symbols("t X")
    result = signs.rational_tail_bound(X/((1+t**2)**2*(2-X)), t, X)
    assert result["order"] == 2
    assert Fraction(result["bound"]) >= Fraction(11, 9)
    with pytest.raises(ValueError):
        signs.rational_tail_bound(1+1/(1+t**2), t, X)

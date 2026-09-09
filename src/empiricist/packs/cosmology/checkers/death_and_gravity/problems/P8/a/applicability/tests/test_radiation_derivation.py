import pytest
import sympy as sp
from p8a_radiation import functional, independent, radiation, validated, verify


def test_exact_mode_geometry_and_QSEI_identities():
    for module in (radiation, functional):
        data = module.identities()
        assert all(sp.simplify(value) == 0 for value in data["residuals"].values())


def test_zero_Ricci_scalar_is_not_flat_spacetime():
    data = radiation.identities()
    t = sp.Symbol("t", positive=True)
    assert data["residuals"]["radiation_Ricci_scalar_zero"] == 0
    assert sp.sympify(data["Kretschmann"], locals={"t": t}) == sp.Rational(3, 2)/t**4
    assert data["matter_era_flat_mode_negative_control"] != "0"


def test_massive_field_cannot_reuse_the_massless_radiation_modes():
    eta, k, mass = sp.symbols("eta k mass", positive=True)
    mode = sp.exp(-sp.I*k*eta)/eta
    residual = sp.simplify(sp.diff(mode, eta, 2)+2/eta*sp.diff(mode, eta)
                           +(k**2+eta**2*mass**2)*mode)
    assert residual == eta*mass**2*sp.exp(-sp.I*eta*k)


def test_wrong_Fourier_cross_sign_disagrees_with_positive_mode_norm():
    k, u = sp.symbols("k u", positive=True)
    # F=1, B=i gives |-ikF-B|^2=(k+1)^2.
    correct = sp.integrate(k*(k+1)**2, (k, 0, u))
    reversed_cross = u**4/4+u**2/2-sp.Rational(2, 3)*u**3
    assert sp.simplify(correct-reversed_cross) == sp.Rational(4, 3)*u**3


def test_independent_proper_and_conformal_integrals_agree():
    result = verify.benchmark()
    assert result["exact_integrals"]["flat_norm"] == ["4/5", "0"]
    assert result["exact_integrals"]["proper_curved_norm"] == ["-75587/1280", "2763/32"]
    assert result["positive_and_strictly_below_flat_norm"]


def test_second_independent_polynomial_and_boundary_conditions():
    result = independent.replay((4, -8, 1, 7, -5, 1))
    assert result["exact_integrals"]["proper_curved_norm"] == result["exact_integrals"]["conformal_positive_norm"]
    with pytest.raises(ValueError, match="endpoint"):
        independent.replay((1, -1))


def test_reduced_pointwise_density_need_not_be_nonnegative():
    t, h = functional.T, functional.H
    density = functional.proper_density().subs({sp.diff(h, t, 2): 0, sp.diff(h, t): 1, h: 0})
    assert density == -sp.Rational(3, 8)/t**2
    # This says nothing about the sign of Q, whose positivity uses the full integral.
    assert validated.positive(-sp.Rational(75587, 1280)+sp.Rational(2763, 32)*sp.log(2))


def test_invalid_interval_claims_and_non_exact_numbers_rejected():
    with pytest.raises(ValueError):
        validated.enclosure(1, 2, 3)
    with pytest.raises(ValueError):
        validated.enclosure(1, 1, 1)
    with pytest.raises(ValueError):
        validated.positive(-1)
    with pytest.raises(ValueError):
        validated.evaluate(0.1)


def test_constant_scale_factor_recovers_proper_time_Minkowski_coefficient():
    eta, scale = sp.symbols("eta a", positive=True)
    h = sp.Function("h")
    f = h(scale*eta)/scale**sp.Rational(3, 2)
    # Convert d_eta integral to dt=scale*d_eta; the field derivative shift is zero.
    density = sp.diff(f, eta, 2)**2/scale
    assert sp.simplify(density-sp.Subs(sp.diff(h(functional.T), functional.T, 2), functional.T, scale*eta)**2) == 0

import pytest
import sympy as sp
from p8a_backreaction import dynamics, independent, verify


@pytest.fixture(scope="module")
def derivation():
    return dynamics.identities()


def test_all_first_order_exact_surrogate_clock_curvature_identities(derivation):
    assert all(sp.simplify(value) == 0 for value in derivation["residuals"].values())


def test_first_order_retarded_mode_uses_full_preparation_history():
    result = dynamics.mode_identities()
    assert all(sp.simplify(value) == 0 for value in result["residuals"].values())
    assert result["preparation_potential_included_in_V1"]
    assert not result["instantaneous_flat_modes_in_nonzero_potential_are_declared_Hadamard"]
    assert not result["uniform_UV_or_actual_RSET_error_bound_derived_from_this_identity"]


def test_wrong_fourth_scale_ODE_factor_is_nonzero():
    a = dynamics.scale()
    wrong = sp.simplify(sp.diff(a**4, dynamics.T)**2
        -16*dynamics.A**2*a**4-64*dynamics.EPS*dynamics.D*dynamics.A**4)
    assert wrong == 192*dynamics.EPS*dynamics.D*dynamics.A**4
    assert independent.replay()["scale_fourth_ODE_epsilon_d_A4_coefficient"] == "256"


def test_wrong_unperturbed_clock_changes_potential_coefficient(derivation):
    assert derivation["incorrect_unperturbed_clock_potential_control"] != derivation["correct_first_order_potential"]
    expected = 48*dynamics.D/(dynamics.A**2*dynamics.ETA**6)
    wrong_a = dynamics.A*dynamics.ETA*(1-dynamics.EPS*dynamics.D/(dynamics.A*dynamics.ETA**2/2)**2)
    assert sp.simplify(dynamics.first(-sp.diff(wrong_a, dynamics.ETA, 2)/wrong_a)-expected) == 0


def test_order_zero_counterterm_is_not_silently_discarded(derivation):
    assert derivation["Itt_order_zero_coupling_linear_control"] == "-126*d/t**6"
    assert derivation["residuals"]["loop_counterterm_no_linear_contribution"] == 0


def test_second_order_completion_is_not_unique(derivation):
    result = derivation["nonunique_all_order_completion"]
    assert not result["first_order_SEE_fixes_all_higher_orders"]
    t = dynamics.T
    f = t**2
    assert sp.simplify(3*sp.diff(f, t)/t+3*f/t**2) == 9
    assert sp.simplify(-2*sp.diff(f, t, 2)-3*sp.diff(f, t)/t+f/t**2) == -9


def test_independent_rational_root_and_defect_certificates():
    result = verify.checked_rational_bounds()
    assert result["frozen_defect_constants"] == {"density": "7/3", "pressure": "35/9", "EED": "7"}
    for name in ("lower_root_polynomial", "upper_root_polynomial"):
        assert all(sp.Rational(value) >= 0 for value in result[name]["Bernstein_coefficients"])


def test_too_small_upper_Taylor_coefficient_rejected():
    bad = independent.root_comparison(sp.Rational(3, 32), lower=True)
    with pytest.raises(ValueError, match="Bernstein"):
        independent.certify_polynomial(bad)


def test_root_enclosure_uses_exact_rational_fourth_powers():
    result = independent.replay()["root_at_z_quarter_enclosure"]
    assert sp.Rational(result["lower"])**4 < sp.Rational(3, 4) < sp.Rational(result["upper"])**4


def test_reference_limit_and_surrogate_are_not_identical_at_second_order():
    coefficient = sp.simplify(dynamics.first(dynamics.surrogate_density()))
    assert coefficient == 3*dynamics.D/(dynamics.KAPPA*dynamics.T**4)
    second = sp.simplify(sp.diff(dynamics.surrogate_density(), dynamics.EPS, 2).subs(dynamics.EPS, 0)/2)
    assert second == 24*dynamics.D**2/(dynamics.KAPPA*dynamics.T**6)


@pytest.mark.parametrize("z", [sp.Rational(1, 16), sp.Rational(1, 8), sp.Rational(1, 4)])
def test_exact_frozen_defects_within_reported_bounds(z):
    result = dynamics.frozen_defects(z, sp.Integer(1))
    for key, coefficient in (("density", sp.Rational(7, 3)), ("pressure", sp.Rational(35, 9)), ("EED", 7)):
        assert 0 < result[key] <= coefficient*z**2

import sympy as sp
from p8a_response import defects, response


def test_all_conservation_anomaly_clock_and_scheme_residuals():
    assert all(value == 0 for value in response.identities().values())
    assert all(value == 0 for value in defects.identities().values())


def test_zero_history_and_zero_perturbation_have_zero_response():
    assert all(value == 0 for value in response.proper_time(sp.Integer(0), sp.Integer(0)).values())


def test_uncut_target_potential_and_finite_curvature_coefficients():
    eta, a = response.ETA, response.A
    d = sp.Symbol("d", positive=True)
    q = -4*d/(a**2*eta**4)
    v = -sp.diff(q, eta, 2)-3*sp.diff(q, eta)/eta
    assert sp.simplify(v-32*d/(a**2*eta**6)) == 0
    finite = response.curvature_response(v)
    t = a*eta**2/2
    assert sp.simplify(finite["density"]+126*d/t**6) == 0
    assert sp.simplify(finite["pressure"]+378*d/t**6) == 0


def test_prepared_constant_cannot_be_selected_by_trace_alone():
    controls = response.controls()
    assert controls["homogeneous_constant_solves_trace_conservation"] == 0
    assert controls["homogeneous_constant_not_fixed_by_trace"] != 0
    assert controls["drop_background_conservation_forcing"] != 0
    assert controls["omit_proper_clock_conversion_density"] != 0
    assert controls["finite_gamma_is_determined_by_A3"] is False
    assert controls["finite_epsilon_remainder_follows_from_first_derivative_bound"] is False


def test_second_defect_coefficient_bound_is_not_a_finite_residual():
    result = defects.coefficient_bounds({"density": 1, "pressure": 2, "EED": 3}, 1, 2, 2)
    assert result == {"density": sp.Rational(19, 8), "pressure": sp.Rational(37, 8), "EED": sp.Rational(57, 8)}

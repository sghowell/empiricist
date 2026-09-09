import pytest
import sympy as sp
from p8a_remainder import geometry, independent, kernel, stress


def test_remainder_exact_covariant_stress_identities_and_history_exclusion():
    values = stress.identities()
    assert values.pop("drop_history_fails_conservation") != 0
    assert all(sp.simplify(value) == 0 for value in values.values())


def test_remainder_generic_stress_bound_matches_calibrated_units():
    delta, length, a, hbar = sp.symbols("delta eta_star A hbar", positive=True)
    data = geometry.calibration()
    cap = sp.Rational(data["delta_bar"])
    b = list(map(sp.Rational, data["potential_bounds"]))
    m = list(map(sp.Rational, independent.replay(geometry.ring_records())["integrated_mode_remainder_constants"]))
    general = stress.bounds([delta**2*v/length**(j+2) for j, v in enumerate(m)],
                            3*length, cap*b[0]/length**2, cap*b[1]/length**3,
                            2/length, 1/(8*a**4*length**4), hbar=hbar)
    normalized = stress.calibration_bounds(m, b, cap)
    for name, value in general.items():
        assert sp.simplify(value*hbar**-1*sp.pi**2*a**4*length**8/delta**2-normalized[name]) == 0


def test_remainder_actual_finite_amplitude_reference_accuracy():
    values = independent.replay(geometry.ring_records())["actual_finite_amplitude_accuracy_example"]
    assert all(sp.Rational(value) < sp.Rational(1, 100)
               for value in values["uniform_reference_scale_error_ratios"].values())
    assert values["all_three_ratios_strictly_below_one_percent"]
    assert "not actual or Born stress" in values["denominator"]
    assert not values["metric_is_claimed_to_solve_SEE"]


def test_remainder_exact_kernel_spatial_constant_and_span_identities():
    assert all(sp.simplify(value) == 0 for value in kernel.identities().values())


def test_remainder_exact_metric_kernel_uses_actual_scale_and_potential():
    eta, start, span, length = sp.symbols("eta start T lambda", positive=True)
    a = sp.Function("a", positive=True)(eta)
    derived = kernel.retarded(a, eta, start, span=span, length=length)
    supplied = kernel.from_potential(a, -sp.diff(a, eta, 2)/a, eta, start,
                                     span=span, length=length)
    assert derived.dummy_eq(supplied)
    assert sp.simplify(kernel.wick(a, 1)*8*sp.pi**2*a**2) == -1
    assert sp.simplify(kernel.wick(a, 1)+1/(8*sp.pi**2*a**2*eta**2)) != 0


def test_remainder_exact_kernel_auxiliary_scale_cancels_for_past_zero_input():
    eta, start, span, length, a = sp.symbols("eta start T lambda a", positive=True)
    # Algebra-only smooth polynomial control, not a physical C-infinity
    # flat-past state. The finite-part scale identity needs U(start)=0.
    potential = (eta-start)**2
    value = kernel.from_potential(a, potential, eta, start, span=span, length=length)
    assert sp.simplify(sp.diff(value, span).doit()) == 0
    with_nonzero_past = kernel.from_potential(a, potential+1, eta, start, span=span, length=length)
    assert sp.simplify(sp.diff(with_nonzero_past, span).doit()) == 1/span


@pytest.mark.parametrize("span,length", [(0, 1), (1, -1), (1.0, 1), (1, sp.oo)])
def test_remainder_kernel_requires_exact_positive_scales(span, length):
    eta = sp.Symbol("eta", positive=True)
    with pytest.raises(ValueError):
        kernel.retarded(eta, eta, 1, span=span, length=length)


def test_remainder_exact_anomaly_retains_pinned_radiation_stress_and_past_constant():
    eta, start = sp.symbols("eta start", positive=True)
    theta = stress.born_trace(eta, 0, eta)
    assert sp.simplify(theta+1/(240*sp.pi**2*eta**8)) == 0
    rho = stress.reconstruct_density(eta, theta, eta, start, 1/(960*sp.pi**2*start**8))
    assert sp.simplify(rho.doit()-1/(960*sp.pi**2*eta**8)) == 0
    wrong = stress.reconstruct_density(eta, theta, eta, start, 0)
    assert sp.simplify(wrong.doit()-rho.doit()) == -1/(960*sp.pi**2*start**4*eta**4)


def test_remainder_lambda_gamma_terms_do_not_disappear_from_absolute_stress():
    eta, ratio, hbar = sp.symbols("eta ratio hbar", positive=True)
    a = sp.Function("a", positive=True)(eta)
    gamma = sp.Symbol("gamma", real=True)
    hc = sp.diff(a, eta)/a
    curvature = 6*sp.diff(a, eta, 2)/a**3
    box_r = (sp.diff(curvature, eta, 2)+2*hc*sp.diff(curvature, eta))/a**2
    baseline = stress.born_trace(a, 0, eta, hbar=hbar)
    changed_gamma = stress.born_trace(a, 0, eta, hbar=hbar, gamma=gamma)
    assert sp.simplify(changed_gamma-baseline+6*gamma*box_r) == 0
    u = -sp.diff(a, eta, 2)/a
    changed_lambda = stress.born_trace(a, -u*sp.log(ratio), eta, hbar=hbar)
    assert sp.simplify(changed_lambda-baseline-hbar*sp.log(ratio)*box_r/(96*sp.pi**2)) == 0
    assert sp.simplify(changed_gamma-baseline) != 0


@pytest.mark.parametrize("values", [[1, 2], [1, -1, 2], [1, 2, 3.0]])
def test_remainder_stress_missing_negative_or_inexact_norm_rejected(values):
    with pytest.raises(ValueError):
        stress.bounds(values, 1, 1, 1, 1, 1)

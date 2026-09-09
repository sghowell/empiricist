"""A.4 two-variable Cauchy extension checks."""

import pytest
import sympy as sp
from p8a_asymptotics import extension, independent


def test_all_three_spatial_dimensional_wave_benchmarks():
    for item in extension.benchmark_wave(extension.ETA, extension.X):
        assert extension.wave(item, extension.ETA, extension.X) == 0


def test_double_cauchy_data_wave_equations_and_order():
    result = extension.identities()
    assert all(sp.simplify(value) == 0 for value in result["residuals"].values())
    assert result["omitted_mixed_data_control_is_nonzero"]
    assert result["noncompact_polynomial_data"]
    assert not result["polynomial_benchmark_proves_general_smooth_PDE_theorem"]


def test_independent_full_coefficient_agreement_through_zero():
    symbolic, rational = extension.identities(), independent.cauchy_replay()
    assert symbolic["independent_monomial_table"] == rational["independent_monomial_table"]
    assert symbolic["through_zero_value"] == rational["through_zero_value"]


def test_missing_mixed_data_rejected():
    data = extension.cauchy_data(extension.benchmark_kernel())
    del data[1, 1]
    with pytest.raises(ValueError, match="four"):
        extension.double_cauchy(data)


@pytest.mark.parametrize("elapsed", [-3, -2, -1, 0, 1, 4])
def test_signed_time_evolution_and_zero_crossing(elapsed):
    x = extension.X[0]
    eta = extension.ETA
    solution = eta**3+3*eta*x**2
    data0 = solution.subs(eta, 2)
    data1 = sp.diff(solution, eta).subs(eta, 2)
    actual = extension.polynomial_cauchy(data0, data1, sp.Integer(elapsed), extension.X)
    assert sp.expand(actual-solution.subs(eta, 2+elapsed)) == 0


def test_nonpolynomial_data_not_silently_truncated():
    with pytest.raises(ValueError, match="polynomial"):
        extension.polynomial_cauchy(sp.sin(extension.X[0]), 0, extension.ETA, extension.X)


def test_elapsed_spatial_dependence_rejected():
    with pytest.raises(ValueError, match="independent"):
        extension.polynomial_cauchy(1, 1, extension.X[0], extension.X)


def test_independent_arithmetic_input_controls():
    with pytest.raises(ValueError, match="nonnegative"):
        independent.power(independent.variable(0), -1)
    with pytest.raises(ValueError, match="eight"):
        independent.evaluate(independent.constant(1), (0,))

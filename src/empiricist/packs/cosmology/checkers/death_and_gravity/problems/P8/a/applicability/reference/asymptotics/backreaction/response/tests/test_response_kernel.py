import pytest
import sympy as sp
from p8a_response import kernel


def test_normalization_spatial_finite_part_and_hadamard_constants():
    assert all(value == 0 for value in kernel.identities().values())


@pytest.mark.parametrize("degree", range(1, 7))
def test_monomial_log_integrals_from_independent_beta_integrals(degree):
    x = sp.Symbol("x", positive=True)
    moment = sp.integrate(degree*x**(degree-1)*sp.log(1-x), (x, 0, 1))
    assert sp.simplify(moment+sp.harmonic(degree)) == 0
    # D=1, A=eta=1, lambda=sqrt(2) removes the geometric logarithm.
    assert kernel.monomial_control(degree, 1, eta=1, a=1, length=sp.sqrt(2)) == sp.Rational(5, 6)+moment


@pytest.mark.parametrize("degree", [0, -1, 1.5, True])
def test_kernel_control_wrong_degrees_rejected(degree):
    with pytest.raises(ValueError):
        kernel.monomial_control(degree, 1)


def test_finite_parts_and_local_scale_are_not_optional():
    controls = kernel.controls()
    for name, value in controls.items():
        if name != "monomial_histories_are_physical_C_infinity_preparations":
            assert value != 0
    assert controls["monomial_histories_are_physical_C_infinity_preparations"] is False


def test_history_retains_past_interval_and_local_factor():
    eta = kernel.ETA
    v = sp.Function("V")(eta)
    result = kernel.history(v, sp.Rational(1, 2))
    integral = next(iter(result.atoms(sp.Integral)))
    assert integral.limits[0][1:] == (sp.Rational(1, 2), eta)
    assert sp.expand(result-integral-v*kernel.local_factor()) == 0

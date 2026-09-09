import pytest
import sympy as sp
from p8a_response import independent, preparation


def test_exact_fraction_switch_and_response_constants():
    symbolic, exact = preparation.normalized_example(), independent.replay()
    for name in ("Q_norm_constants", "V_norm_constants", "K_norm_constants"):
        assert list(map(str, symbolic[name])) == exact[name]
    assert exact["response_constants"] == {
        "density": "1365615131563/125829120",
        "pressure": "1031121912446883/1342177280",
        "EED": "9323796896231963/8053063680"}
    assert exact["finite_epsilon_remainder_bound"] is False


def test_exponential_polynomials_by_direct_chain_rule():
    x = sp.Symbol("x", positive=True)
    result = preparation.switch_derivative_bounds()
    for n, polynomial in enumerate(result["polynomials"]):
        expected = sp.exp(-1/x)*polynomial.subs(result["variable"], 1/x)
        assert sp.simplify(sp.diff(sp.exp(-1/x), x, n)-expected) == 0


def test_denominator_and_logarithm_enclosures_are_strict():
    checks = preparation.elementary_checks()
    assert checks.pop("switch_denominator_monotonic_identity") == 0
    assert all(value > 0 for value in checks.values())


def test_kernel_log_L1_bound_and_derivative_local_terms():
    x = sp.Symbol("x", positive=True)
    assert sp.integrate(-sp.log(x), (x, 0, 1)) == 1
    assert preparation.kernel_bounds([1, 2, 3, 4], 2, 2, 2) == [6, sp.Rational(21, 2), sp.Rational(65, 4)]


def test_finite_counterterm_bound_is_not_silently_zero():
    before = preparation.response_bounds([1, 2, 3, 4], 5, [6, 7, 8], 2)
    after = preparation.response_bounds([1, 2, 3, 4], 5, [6, 7, 8], 2, gamma_abs=1)
    assert all(sp.simplify(after[name]-before[name]) > 0 for name in before)


@pytest.mark.parametrize("bad", [0.1, sp.Float("0.1"), sp.oo, -1, sp.Symbol("unproved")])
def test_noncertified_bound_inputs_rejected(bad):
    with pytest.raises(ValueError):
        preparation.kernel_bounds([1, 2, bad, 4], 2, 2, 2)


@pytest.mark.parametrize("bad", [0, -1, 0.5, sp.oo])
def test_history_domain_rejections(bad):
    with pytest.raises(ValueError):
        preparation.kernel_bounds([1, 2, 3, 4], bad, 2, 2)


@pytest.mark.parametrize("order", [-1, 6, 2.5, True])
def test_unimplemented_switch_orders_rejected(order):
    with pytest.raises(ValueError):
        preparation.switch_derivative_bounds(order)


def test_missing_history_derivative_data_rejected():
    with pytest.raises(ValueError):
        preparation.kernel_bounds([1, 2, 3], 2, 2, 2)
    with pytest.raises(ValueError):
        preparation.response_bounds([1, 2, 3, 4], 1, [1, 2], 2)

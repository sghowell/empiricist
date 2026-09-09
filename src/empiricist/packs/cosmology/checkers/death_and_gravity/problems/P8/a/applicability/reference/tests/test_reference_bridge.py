import pytest
import sympy as sp
from p8a_radiation import validated
from p8a_reference import bridge, independent, verify


def test_absolute_hardy_logarithmic_and_reference_sign_identities():
    verify.verified_residuals(bridge.identities())
    assert bridge.LOCAL_COEFFICIENT == sp.Rational(521, 1280)
    assert bridge.HARDY_CREDIT == sp.Rational(559, 1280)


def test_all_positive_log_coefficients_are_validated():
    for coefficient in bridge.identities()["positive_log_coefficients"]:
        assert validated.positive(sp.Rational(coefficient))


@pytest.mark.parametrize("coefficients", [(4, -12, 13, -6, 1), (4, -8, 1, 7, -5, 1)])
def test_independent_absolute_integral_representations_and_prior_agreement(coefficients):
    result = verify.benchmark(coefficients)
    rows = result["exact_integrals"]
    assert rows["absolute"] == rows["absolute_Hardy"] == rows["absolute_log_positive"]
    assert result["validated_ordering"] == "0 < absolute < difference < flat"


def test_reference_subtraction_has_correct_inequality_direction():
    rows = independent.benchmark()["exact_integrals"]
    difference, reference, absolute = (verify.integral_expression(rows[key])
                                      for key in ("difference", "reference_credit", "absolute"))
    assert sp.simplify(difference-reference-absolute) == 0
    assert validated.positive(difference-absolute)
    assert validated.positive(-absolute-(-difference))


@pytest.mark.parametrize("lower,upper", [(0, 2), (-1, 2), (2, 1), (1, sp.oo)])
def test_invalid_support_window_rejected(lower, upper):
    with pytest.raises(ValueError):
        bridge.endpoint_check((bridge.T-1)**2*(2-bridge.T)**2, lower, upper)


def test_nonzero_endpoint_derivatives_rejected():
    t = bridge.T
    h = (t-1)*(2-t)
    with pytest.raises(ValueError, match="both h and hdot"):
        bridge.endpoint_check(h, 1, 2)
    with pytest.raises(ValueError, match="endpoint jets"):
        independent.benchmark((-2, 3, -1))


def test_logarithmic_boundary_term_really_survives_for_bad_jets():
    t = bridge.T
    h = (t-1)*(2-t)
    u = h/t**sp.Rational(3, 2)
    ux = t*sp.diff(u, t)
    uxx = t*sp.diff(ux, t)
    positive_as_t = (uxx**2+sp.Rational(17, 8)*ux**2+sp.Rational(161, 1280)*u**2)/t
    defect = sp.integrate(sp.expand(bridge.absolute_density(h)-positive_as_t), (t, 1, 2))
    assert sp.simplify(defect) == -1


def test_tampered_positive_enclosure_rejected():
    absolute = verify.integral_expression(independent.benchmark()["exact_integrals"]["absolute"])
    with pytest.raises(ValueError, match="not certified"):
        validated.enclosure(absolute, "0.8", "0.9")

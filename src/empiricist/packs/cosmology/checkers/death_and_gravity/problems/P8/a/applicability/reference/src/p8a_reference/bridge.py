"""Absolute-QSEI functional and its exact Hardy/logarithmic identities."""

import sympy as sp
from p8a_radiation import functional

T = functional.T
H = functional.H
REFERENCE_CREDIT = sp.Rational(1, 320)
HARDY_CREDIT = sp.Rational(559, 1280)
LOCAL_COEFFICIENT = sp.Rational(521, 1280)


def absolute_density(h=H, time=T):
    return (sp.diff(h, time, 2)**2-sp.Rational(3, 8)*sp.diff(h, time)**2/time**2
            +LOCAL_COEFFICIENT*h**2/time**4)


def endpoint_check(h, lower, upper, time=T):
    lower, upper = sp.sympify(lower), sp.sympify(upper)
    if lower.is_positive is not True or (upper-lower).is_positive is not True:
        raise ValueError("Require 0 < lower < upper")
    if lower.is_finite is not True or upper.is_finite is not True:
        raise ValueError("Finite compact interval required")
    jets = [sp.simplify(sp.diff(h, time, order).subs(time, end))
            for end in (lower, upper) for order in (0, 1)]
    if any(value != 0 for value in jets):
        raise ValueError("H2_0 requires both h and hdot to vanish at both endpoints")
    return True


def identities():
    x = sp.Symbol("x", real=True)
    u = sp.Function("u")(x)
    ux, uxx = sp.diff(u, x), sp.diff(u, x, 2)
    log_raw = (uxx+2*ux+sp.Rational(3, 4)*u)**2
    log_raw -= sp.Rational(3, 8)*(ux+sp.Rational(3, 2)*u)**2
    log_raw += LOCAL_COEFFICIENT*u**2
    log_positive = uxx**2+sp.Rational(17, 8)*ux**2+sp.Rational(161, 1280)*u**2
    log_boundary = 2*ux**2+sp.Rational(3, 2)*u*ux+sp.Rational(15, 16)*u**2
    hardy = (sp.diff(H, T)/T-sp.Rational(3, 2)*H/T**2)**2
    hardy_form = sp.diff(H, T, 2)**2-sp.Rational(3, 8)*hardy-HARDY_CREDIT*H**2/T**4
    hardy_boundary = -sp.Rational(3, 2)*H**2/T**3
    time_scale = sp.Symbol("t_star", positive=True)
    pulled_h = T**sp.Rational(3, 2)*sp.Function("u")(sp.log(T/time_scale))
    substitute_log = {sp.log(T/time_scale): x}
    first = sp.diff(pulled_h, T)/sp.sqrt(T)
    second = sp.sqrt(T)*sp.diff(pulled_h, T, 2)
    return {
        "residuals": {
            "difference_to_absolute_reference_sign": sp.simplify(
                functional.proper_density()-REFERENCE_CREDIT*H**2/T**4-absolute_density()),
            "absolute_Hardy_IBP": sp.simplify(absolute_density()-hardy_form
                                              -sp.Rational(3, 8)*sp.diff(hardy_boundary, T)),
            "logarithmic_first_derivative": sp.simplify(first.subs(substitute_log).doit()
                                                        -ux-sp.Rational(3, 2)*u),
            "logarithmic_second_derivative": sp.simplify(second.subs(substitute_log).doit()
                                                         -uxx-2*ux-sp.Rational(3, 4)*u),
            "logarithmic_positive_IBP": sp.simplify(log_raw-log_positive-sp.diff(log_boundary, x)),
            "reference_plus_difference_credit": sp.Rational(111, 256)+REFERENCE_CREDIT-HARDY_CREDIT,
        },
        "reference_credit_in_hbar_over_16pi2_units": str(REFERENCE_CREDIT),
        "absolute_functional_density": str(absolute_density()),
        "absolute_Hardy_form": str(hardy_form),
        "absolute_positive_log_form": str(log_positive),
        "positive_log_coefficients": ["1", "17/8", "161/1280"],
        "logarithmic_clock": "x=log(t/t_star), t_star>0; h=t^(3/2)*u(x)",
        "absolute_bound": "integral h^2*E_omega dt >= -hbar*B[h]/(16*pi^2)",
        "exact_comparison": "0 <= B[h] <= ||hddot||^2",
        "unconditional_absolute_multiplier_for_fixed_prescription": "1",
        "assumed_short_duration": False,
        "sampling_domain": "real C_c^infinity(t>0), or H2_0(t_minus,t_plus) with 0<t_minus<t_plus<infinity",
        "endpoint_jets": "h=hdot=0 at both endpoints",
        "not_optimality": "evaluated source-based bound, not an optimal QEI over states",
    }

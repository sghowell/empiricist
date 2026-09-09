"""Asymptotic coefficients and qualitative correction, not a finite error."""

import sympy as sp

from .preparation import exact_nonnegative


def coefficient_bounds(response_bounds, d, kappa, time_minus):
    """Bounds the epsilon-squared coefficient, not the residual for epsilon>0."""
    if set(response_bounds) != {"density", "pressure", "EED"}:
        raise ValueError("Need all three actual first-response bounds")
    d = exact_nonnegative(d, positive=True)
    kappa = exact_nonnegative(kappa, positive=True)
    t = exact_nonnegative(time_minus, positive=True)
    constants = {"density": 24, "pressure": 40, "EED": 72}
    return {name: constants[name]*d**2/t**6+kappa*exact_nonnegative(value)
            for name, value in response_bounds.items()}


def identities():
    t, d, epsilon = sp.symbols("t d epsilon", positive=True)
    z = 4*epsilon*d/t**2
    frozen_density = 3*z**2*(2-z)/(4*t**2*(1-z)**2)
    frozen_pressure = 5*z**2*(2-z)/(4*t**2*(1-z)**2)
    f, r = sp.Function("F")(t), sp.Function("r")(t)
    lr = 3*sp.diff(r, t)/t+3*r/t**2
    lp = -2*sp.diff(r, t, 2)-3*sp.diff(r, t)/t+r/t**2
    first = -r/t-t*f/3
    second = sp.diff(first, t).subs(sp.diff(r, t), first)
    fp = -f-sp.Rational(2, 3)*t*sp.diff(f, t)
    return {
        "frozen_density_second_coefficient": sp.limit(frozen_density/epsilon**2, epsilon, 0)-24*d**2/t**6,
        "frozen_pressure_second_coefficient": sp.limit(frozen_pressure/epsilon**2, epsilon, 0)-40*d**2/t**6,
        "frozen_EED_second_coefficient": sp.limit((frozen_density+3*frozen_pressure)/(2*epsilon**2), epsilon, 0)-72*d**2/t**6,
        "second_order_geometric_Bianchi_identity": sp.simplify(sp.diff(lr, t)+3*(lr+lp)/(2*t)),
        "second_order_density_cancellation": sp.simplify((f+lr).subs(sp.diff(r, t), first)),
        "second_order_pressure_cancellation": sp.simplify((fp+lp).subs({sp.diff(r, t, 2): second, sp.diff(r, t): first}, simultaneous=True)),
    }

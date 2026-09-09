"""Explicit conditional reference-state and duration bridges; no silent vacuum zero."""

import sympy as sp

CREDIT = sp.Rational(111, 256)


def exact_rational(value):
    value = sp.sympify(value)
    if not value.is_Rational:
        raise ValueError("Supply exact rational inputs, not floating estimates")
    return value


def reference_bridge(beta, duration_fraction):
    """Given E_ref >= -beta*hbar/(16*pi^2*t^4), return a sufficient multiplier.

    The local proper-time window is (t_c-L/2,t_c+L/2), L=lambda*t_c.
    The input reference bound is not derived by this function or checkpoint.
    """
    if beta is None:
        raise ValueError("A reference EED lower bound must be supplied; it is not zero by convention")
    beta, fraction = exact_rational(beta), exact_rational(duration_fraction)
    if beta < 0 or not 0 < fraction < 2:
        raise ValueError("Require beta >= 0 and 0 < L/t_c < 2")
    remainder = max(sp.Integer(0), beta-CREDIT)
    ratio = sp.cancel(fraction/(1-fraction/2))
    multiplier = 1+remainder*ratio**4/sp.pi**4
    return {"assumed_reference_lower_bound": f"E_reference(t) >= -({beta})*hbar/(16*pi^2*t^4)",
            "reference_bound_is_derived_here": False,
            "L_over_t_c": str(fraction), "t_min_over_t_c": str(1-fraction/2),
            "window_over_t_c": [str(1-fraction/2), str(1+fraction/2)],
            "remaining_dimensionless_reference_deficit": str(remainder),
            "absolute_QSEI_multiplier": multiplier,
            "status": "CONDITIONAL_ON_REFERENCE_EED_BOUND; NOT_A_SEE_SOLUTION"}


def geometric_bridge(*, reference_beta, t_min, kappa=1, hbar=1):
    """Q2,Q0 for A.1's shape, conditional also on the correct SEE dictionary."""
    if reference_beta is None:
        raise ValueError("Reference-state stress must not be silently discarded")
    beta, lower, coupling, quantum = map(exact_rational, (reference_beta, t_min, kappa, hbar))
    if beta < 0 or min(lower, coupling, quantum) <= 0:
        raise ValueError("Require nonnegative reference beta and positive t_min, kappa, hbar")
    return {"Q2": coupling*quantum/(16*sp.pi**2),
            "Q0": coupling*quantum*max(sp.Integer(0), beta-CREDIT)/(16*sp.pi**2*lower**4),
            "conditional_on_SEE_and_reference_bound": True}

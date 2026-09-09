"""Exact-metric retarded Born functional in the declared raw Hadamard scheme.

Every argument uses the actual conformal coordinate. In particular a is the
full scale factor, never the radiation normalization A. Flat-zero past U,
the state and geometric hypotheses remain mathematical preconditions.
"""

import sympy as sp

from .mode_bounds import exact_nonnegative


def from_potential(a, potential, eta, eta_start, *, span, length):
    """Exact history integral for an explicitly supplied actual-clock U=-a''/a.

    U and its jets must vanish in the common past. The positive auxiliary
    span cancels under that condition; length is the fixed Hadamard lambda.
    This is a symbolic functional, not a mode solution or state constructor.
    """
    span = exact_nonnegative(span, positive=True)
    length = exact_nonnegative(length, positive=True)
    s = sp.Dummy("s", real=True)
    derivative = sp.diff(potential, eta).subs(eta, s)
    return (sp.Integral(derivative*sp.log((eta-s)/span), (s, eta_start, eta))
            + potential*(sp.log(sp.sqrt(2)*a*span/length)+sp.Rational(5, 6)))


def retarded(a, eta, eta_start, *, span, length):
    """Construct U from the full actual scale factor before forming K[U]."""
    return from_potential(a, -sp.diff(a, eta, 2)/a, eta, eta_start,
                          span=span, length=length)


def wick(a, retarded_kernel, *, hbar=1):
    """Born-on-exact-geometry Wick approximation; not a covariance/state."""
    return -sp.sympify(hbar)*retarded_kernel/(8*sp.pi**2*a**2)


def identities():
    a, u, span, length, radial = sp.symbols("a U T lambda r", positive=True)
    finite_part = sp.Symbol("history_finite_part", real=True)
    born_finite = u*sp.log(radial)-finite_part-u*(sp.log(2*span)+1)
    hadamard_finite = -u/6+u*sp.log(radial*a/(sp.sqrt(2)*length))
    renormalized = -finite_part-u*(sp.log(sp.sqrt(2)*a*span/length)+sp.Rational(5, 6))
    return {"finite_metric_spatial_Hadamard_subtraction": sp.expand_log(
                born_finite-hadamard_finite-renormalized, force=True).expand(),
            "auxiliary_span_cancels_for_flat_past": sp.diff(
                -u*sp.log(span)+u*sp.log(sp.sqrt(2)*a*span/length), span),
            "exact_scale_Wick_normalization": wick(a, u)+u/(8*sp.pi**2*a**2)}

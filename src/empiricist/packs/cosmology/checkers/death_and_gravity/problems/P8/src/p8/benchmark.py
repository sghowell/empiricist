"""A25 v2 benchmark: exact background and removable H=0 limit only.

Not a reconstructed covariant solution or an all-time stability certificate.
All time/field quantities are dimensionless as in A25 (25).
"""

from functools import lru_cache

import sympy as sp

t = sp.Symbol("t", real=True)
tau, epsilon, w = sp.symbols("tau epsilon w", positive=True)
u = sp.Symbol("u", real=True)
PARAMETERS = {tau: sp.Integer(10), epsilon: sp.Integer(5), w: sp.Integer(2),
              u: sp.Rational(1, 10)}


@lru_cache(maxsize=1)
def background():
    s = t/tau
    base = 1+s**2
    sigmoid = 1/(1+sp.exp(-s))
    a = sigmoid*base**sp.Rational(1, 6) + (1-sigmoid)*base**(1/(2*epsilon))
    H = sp.diff(a, t)/a
    g1 = w/(3*sp.cosh(s+u)**2)
    numerator = t**2*sp.tanh(s+u) + tau**2*sp.tanh(s)
    a1_quotient = w/(12*sp.cosh(s+u)**2)*(2*numerator/(H*tau*(t**2+tau**2))-1)
    # Algebraic cancellation in H*(4*a1+g1+1)+g1_dot removes 1/H entirely.
    theta_regular = H + 2*g1*tau/(t**2+tau**2)*(sp.tanh(s)-sp.tanh(s+u))
    return {"a": a, "H": H, "g1": g1, "a1_quotient": a1_quotient,
            "a1_numerator": numerator, "theta_regular": theta_regular}


def bounce_jet():
    """Compute, not hardcode, the finite limits at t=0 by Taylor/l'Hopital."""
    b = background()
    a0 = b["a"].subs(t, 0)
    H0 = sp.simplify(b["H"].subs(t, 0))
    Hdot0 = sp.simplify(sp.diff(b["H"], t).subs(t, 0))
    # Both numerator and H have a simple zero, Hdot0>0 for epsilon,tau>0.
    ratio0 = sp.diff(b["a1_numerator"], t).subs(t, 0) / Hdot0
    a1_0 = sp.simplify(w/(12*sp.cosh(u)**2)*(2*ratio0/tau**3-1))
    return {"a0": a0, "H0": H0, "Hdot0": Hdot0, "a1_0": a1_0,
            "theta0": sp.simplify(b["theta_regular"].subs(t, 0))}

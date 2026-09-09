"""Exact order-two scalar-mode jets, with unrestricted cosmic-time H.

This follows P9's expansion method but shares no symbols or H>0 assumptions.
"""

import sympy as sp

t, x, y, zcoord = sp.symbols("t x y zcoord", real=True)
coords = (t, x, y, zcoord)
k = sp.Symbol("k", positive=True)
eps = sp.Symbol("eps", real=True)
cx, sx = sp.cos(k*x), sp.sin(k*x)
a = sp.Function("a", positive=True)(t)
H = sp.Function("H", real=True)(t)
zeta, lapse, shift = (sp.Function(n)(t) for n in ("zeta", "lapse", "shift"))


def cut(e):
    e = sp.expand(e)
    return sum(e.coeff(eps, n)*eps**n for n in range(3)) if e.has(eps) else e


def mul(*factors):
    out = sp.Integer(1)
    for factor in factors:
        out = cut(out*factor)
    return out


def exp_z(c):
    v = eps*zeta*cx
    return 1+c*v+c**2*v**2/2


def bg(expr):
    # Highest derivatives first. No Friedmann equation is assumed here.
    replacements = {}
    adot = a*H
    for order in range(1, 5):
        replacements[sp.diff(a, t, order)] = adot
        adot = sp.diff(adot, t).subs(sp.diff(a, t), a*H)
    return sp.expand(expr.xreplace(replacements))


def dt(expr):
    return bg(sp.diff(expr, t))


def zero(expr):
    return sp.cancel(bg(expr)) == 0


def average(expr):
    c, s = sp.symbols("_c _s")
    p = sp.Poly(sp.expand(expr).subs({cx: c, sx: s}), c, s)
    moments = {(0, 0): 1, (1, 0): 0, (0, 1): 0, (1, 1): 0,
               (2, 0): sp.Rational(1, 2), (0, 2): sp.Rational(1, 2)}
    return sp.expand(sum(coeff*moments[powers] for powers, coeff in p.terms()))


def taylor_N(coeffs, N):
    """Function of (t,N), supplied as value, N derivative, N² derivative."""
    return cut(coeffs[0]+coeffs[1]*(N-1)+coeffs[2]*(N-1)**2/2)

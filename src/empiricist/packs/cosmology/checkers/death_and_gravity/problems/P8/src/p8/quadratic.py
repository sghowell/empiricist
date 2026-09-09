"""Expand the derived ADM action; obtain background and scalar constraints.

Taylor coefficients are in N at N=1, with phi=t. The lapse time/spatial
derivative coefficients are fixed by the exact Ia degeneracy identities.
No source expression for Theta or Sigma is supplied to the reduction.
"""

from functools import cache

import sympy as sp

from . import covariant
from . import jets as j

F = tuple(sp.Function(n)(j.t) for n in ("F0", "FN", "FNN"))
f = tuple(sp.Function(n)(j.t) for n in ("f0", "fN", "fNN"))
B = tuple(sp.Function(n)(j.t) for n in ("B0", "BN", "BNN"))
C = tuple(sp.Function(n)(j.t) for n in ("C0", "CN", "CNN"))
braid = tuple(sp.Function(n)(j.t) for n in ("K0", "KN", "KNN"))
v = sp.Function("v")(j.t)


def substitute_functions(expr, replacements):
    rules = dict(replacements)
    for fn, value in replacements.items():
        for order in (1, 2, 3, 4):
            rules[sp.diff(fn, j.t, order)] = j.bg(sp.diff(value, j.t, order))
    return expr.xreplace(rules)


@cache
def expand_action():
    d = covariant.geometry()
    N, A, K, V = (d[name] for name in ("N", "invN", "K", "V"))
    delta = C[0]/(4*B[0])
    D = 3*C[0]**2/(8*B[0])
    E = 2*f[0]*delta**2+4*(f[0]+f[1])*delta
    Fjet, fjet, Bjet, Cjet, Kjet = (j.taylor_N(c, N) for c in (F, f, B, C, braid))
    fphi = j.taylor_N(tuple(sp.diff(c, j.t) for c in f), N)
    action = j.mul(d["sqg"], Fjet+j.mul(Kjet, V+j.mul(A, K))
                   - j.mul(fjet, d["R3"])+j.mul(Bjet, K, K)-j.mul(Bjet, d["KK"])
                   + 2*j.mul(A, fphi, K)+j.mul(Cjet, K, V)
                   + j.mul(D, V, V)+j.mul(E, d["acc2"]))
    return j.bg(action)


@cache
def background():
    # k=0 is used ONLY for homogeneous background variation, not propagation.
    linear = expand_action().coeff(j.eps, 1).subs(j.k, 0)
    en = sp.cancel((sp.diff(linear, j.lapse)
                    - j.dt(sp.diff(linear, sp.diff(j.lapse, j.t))))/j.a**3)
    ea = sp.cancel((sp.diff(linear, j.zeta)
                    - j.dt(sp.diff(linear, sp.diff(j.zeta, j.t))))/(3*j.a**3))
    solution = sp.solve((en, ea), (F[0], F[1]), dict=True)[0]
    return {"EN": en, "Ea": ea, "solution": solution}


@cache
def derive():
    raw = 2*j.average(expand_action().coeff(j.eps, 2))
    delta = C[0]/(4*B[0])
    shifted = j.bg(substitute_functions(raw, {j.zeta: v+delta*j.lapse}))
    n, ndot, vdot = j.lapse, sp.diff(j.lapse, j.t), sp.diff(v, j.t)
    L = sp.cancel(shifted)
    degeneracy = {
        "lapse_velocity_squared": sp.cancel(sp.diff(L, ndot, 2)),
        "lapse_scalar_velocity": sp.cancel(sp.diff(L, ndot, vdot)),
        "lapse_velocity_shift": sp.cancel(sp.diff(L, ndot, j.shift)),
    }
    # Explicit time-boundary terms: first n_dot*v, then n_dot*n and v_dot*v.
    boundaries = []
    for qdot, other, primitive in (
        (ndot, v, n*v), (ndot, n, n**2/2), (vdot, v, v**2/2)
    ):
        boundary = sp.cancel(sp.diff(L, qdot, other))*primitive
        boundaries.append(boundary)
        L = sp.cancel(L-j.dt(boundary))
    ibp_residual = sp.cancel(shifted-L-j.dt(sum(boundaries)))
    on_shell = sp.cancel(substitute_functions(L, background()["solution"]))
    GT, FT = -2*B[0], -2*f[0]
    Lambda = -2*f[0]-2*f[1]+FT*delta
    Theta = sp.cancel(sp.diff(on_shell, n, j.shift)/(2*j.a**3*j.k**2))
    Sigma = sp.cancel(sp.diff(on_shell, n, 2)/(2*j.a**3))
    target = j.a**3*(-3*GT*vdot**2+Sigma*n**2+6*Theta*n*vdot
                     + j.k**2*(2*Theta*n*j.shift-2*GT*vdot*j.shift))
    target += j.a*j.k**2*(FT*v**2+2*Lambda*n*v)
    return {"raw": raw, "shifted": shifted, "boundaries": boundaries,
            "on_shell": on_shell, "GT": GT, "FT": FT, "delta": delta,
            "Lambda": Lambda, "Theta": Theta, "Sigma": Sigma,
            "residuals": {**degeneracy, "IBP": ibp_residual,
                          "unreduced_scalar_action": sp.cancel(on_shell-target)}}


def covariant_N_jets(Fexpr, Kexpr, fexpr, A1expr, A3expr, X):
    """Map explicit (t,X) independent functions to the ADM N Taylor jets."""
    N = sp.Symbol("N", positive=True)
    Bexpr = fexpr-X*A1expr
    Cexpr = sp.sqrt(X)*(4*sp.diff(fexpr, X)-2*A1expr+X*A3expr)
    replacements = {}
    for symbols, expr in ((F, Fexpr), (braid, Kexpr), (f, fexpr), (B, Bexpr), (C, Cexpr)):
        nx = expr.subs(X, N**-2)
        for order, symbol in enumerate(symbols):
            replacements[symbol] = sp.simplify(sp.diff(nx, N, order).subs(N, 1))
    return replacements

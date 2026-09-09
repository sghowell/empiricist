"""Independent homogeneous covariant check of the A25 Sigma discrepancy.

Build R and phi_;mu nu directly for ds²=N²dt²-A²dx², with zeta=g1*n
(so the transformed curvature variable is zero). Use the Euler operator
on the unintegrated covariant action, including second derivatives. This
does not use the ADM action, its integration-by-parts algorithm, or q.Sigma.
"""

from functools import cache

import sympy as sp

from . import jets as j
from .matter import ia_completion


@cache
def A25_sigma():
    t, eps, n = j.t, j.eps, j.lapse
    X = sp.Symbol("X", positive=True)
    g, a1, FXX = (sp.Function(name)(t) for name in ("g1", "a1", "FXX"))
    N = 1+eps*n
    invN = 1-eps*n+eps**2*n**2
    z = eps*g*n
    A = j.a*(1+z+z**2/2)
    invA = (1-z+z**2/2)/j.a
    Hcoord = j.mul(sp.diff(A, t), invA)
    Hnormal = j.mul(Hcoord, invN)
    V = -j.mul(sp.diff(N, t), invN, invN, invN)
    R = -6*j.cut(j.mul(sp.diff(A, t, 2), invA, invN, invN)
                 + j.mul(Hcoord, Hcoord, invN, invN)
                 - j.mul(Hcoord, sp.diff(N, t), invN, invN, invN))
    clock_X = j.mul(invN, invN)
    Box = j.cut(V+3*j.mul(invN, Hnormal))
    Li = (j.cut(V**2+3*j.mul(clock_X, Hnormal, Hnormal)), j.mul(Box, Box),
          j.mul(clock_X, V, Box), j.mul(clock_X, V, V), j.mul(clock_X, clock_X, V, V))
    F2 = -sp.Rational(1, 2)+g*(1-X)
    A1 = a1*(X-1)
    A3 = 2*(X*A1-2*F2)*(A1-2*sp.diff(F2, X))/(X*(3*X*A1-4*F2))
    A2, A4, A5 = ia_completion(F2, sp.diff(F2, X), A1, A3, X)
    theta = j.H*(1+4*a1+g)+sp.diff(g, t)
    # Published background equations (55), checked separately against metric variation.
    F0 = -2*sp.diff(j.H, t)-3*j.H**2
    FX = (F0+3*j.H*theta+3*j.H*sp.diff(g, t)-3*g*(2*sp.diff(j.H, t)+3*j.H**2))/2
    F = F0+FX*(X-1)+FXX*(X-1)**2/2
    def expand_X(expr, order=2):
        return j.cut(sum(sp.diff(expr, X, r).subs(X, 1)*(clock_X-1)**r/sp.factorial(r)
                         for r in range(order+1)))
    L = j.cut(expand_X(F)+j.mul(expand_X(F2), R))
    # L3 starts at first order; L4,L5 start at second. Only needed jets are expanded.
    for coeff, invariant, order in zip((A1, A2, A3, A4, A5), Li, (2, 2, 1, 0, 0)):
        L += j.mul(expand_X(coeff, order), invariant)
    volume = j.mul(N, j.a**3*(1+3*z+sp.Rational(9, 2)*z**2))
    quadratic = j.bg(j.mul(volume, L).coeff(eps, 2))
    euler = sp.diff(quadratic, n)-j.dt(sp.diff(quadratic, sp.diff(n, t)))
    euler += j.dt(j.dt(sp.diff(quadratic, sp.diff(n, t, 2))))
    sigma = sp.cancel(sp.diff(euler, n)/(2*j.a**3))
    remainder = sp.cancel(euler-2*j.a**3*sigma*n)
    return {"Sigma": sigma, "auxiliary_remainder": remainder}

"""Metric-derived scalar-mode geometry in P8's (+---) convention.

No field equations or published DHOST perturbation coefficients are inputs.
The expansion covers scalar perturbations of flat FLRW through order two.
"""

from functools import cache

import sympy as sp

from . import jets as j


@cache
def geometry():
    c3 = j.coords[1:]
    N = 1+j.eps*j.lapse*j.cx
    dN = N-1
    invN, invN2 = 1-dN+dN**2, 1-2*dN+3*dN**2
    h = sp.eye(3)*j.a**2*j.exp_z(2)
    hi = sp.eye(3)*j.exp_z(-2)/j.a**2
    sqh = j.a**3*j.exp_z(3)
    shift_up = [sp.diff(j.eps*j.shift*j.cx, c) for c in c3]
    shift_down = [j.cut(sum(h[i, m]*shift_up[m] for m in range(3))) for i in range(3)]
    ch3 = christoffel(h, hi, c3)
    r3 = ricci_scalar(hi, ch3, c3)
    K = sp.Matrix(3, 3, lambda i, m: j.mul(invN, (
        sp.diff(h[i, m], j.t)-sp.diff(shift_down[m], c3[i])
        - sp.diff(shift_down[i], c3[m])
        + 2*sum(ch3[l][i][m]*shift_down[l] for l in range(3)))/2))
    Ku = (hi*K).applyfunc(j.cut)
    trK = j.cut(sp.trace(Ku))
    trKK = j.cut(sp.trace((Ku*Ku).applyfunc(j.cut)))
    g = sp.zeros(4)
    gi = sp.zeros(4)
    g[0, 0] = j.cut(N**2-sum(shift_down[i]*shift_up[i] for i in range(3)))
    gi[0, 0] = invN2
    for i in range(3):
        g[0, i+1] = g[i+1, 0] = -shift_down[i]
        gi[0, i+1] = gi[i+1, 0] = -j.mul(invN2, shift_up[i])
        for m in range(3):
            g[i+1, m+1] = -h[i, m]
            gi[i+1, m+1] = j.cut(-hi[i, m]+j.mul(invN2, shift_up[i], shift_up[m]))
    acc_down = [j.mul(invN, sp.diff(N, c)) for c in c3]
    acc_up = [j.cut(sum(hi[i, m]*acc_down[m] for m in range(3))) for i in range(3)]
    acc2 = j.cut(sum(acc_up[i]*acc_down[i] for i in range(3)))
    V = j.mul(invN, sp.diff(invN, j.t)
              - sum(shift_up[i]*sp.diff(invN, c3[i]) for i in range(3)))
    return {"N": N, "invN": invN, "X": invN2, "sqh": sqh,
            "sqg": j.mul(N, sqh), "h": h, "hi": hi, "g": g, "gi": gi,
            "shift_up": shift_up, "K": trK, "KK": trKK, "R3": r3,
            "acc_up": acc_up, "acc2": acc2, "V": V}


def christoffel(g, gi, coords):
    dim = len(coords)
    return [[[j.cut(sum(gi[l, s]*(sp.diff(g[s, n], coords[m])
                 + sp.diff(g[s, m], coords[n])-sp.diff(g[m, n], coords[s]))
                 for s in range(dim))/2)
             for n in range(dim)] for m in range(dim)] for l in range(dim)]


def ricci_scalar(gi, ch, coords):
    dim = len(coords)
    ric = sp.Matrix(dim, dim, lambda m, n: j.cut(sum(
        sp.diff(ch[l][m][n], coords[l])-sp.diff(ch[l][m][l], coords[n])
        + sum(ch[l][l][s]*ch[s][m][n]-ch[l][n][s]*ch[s][m][l]
              for s in range(dim)) for l in range(dim))))
    return j.cut(sum(gi[m, n]*ric[m, n] for m in range(dim) for n in range(dim)))


@cache
def scalar_invariants():
    d = geometry()
    gi = d["gi"]
    ch4 = christoffel(d["g"], gi, j.coords)
    # phi=t: phi_;mu nu = -Gamma^0_mu nu, phi^mu=g^{mu 0}.
    phi2 = sp.Matrix(4, 4, lambda m, n: -ch4[0][m][n])
    raised = (gi*phi2*gi).applyfunc(j.cut)
    u = gi[:, 0]
    w = (phi2*u).applyfunc(j.cut)
    box = j.cut(sp.trace((gi*phi2).applyfunc(j.cut)))
    contraction = j.cut((u.T*w)[0])
    L1 = j.cut(sum(phi2[m, n]*raised[m, n] for m in range(4) for n in range(4)))
    L2 = j.mul(box, box)
    L3 = j.mul(contraction, box)
    L4 = j.cut((w.T*gi*w)[0])
    L5 = j.mul(contraction, contraction)
    return {"box": box, "L": (L1, L2, L3, L4, L5),
            "R4": ricci_scalar(gi, ch4, j.coords)}


def contraction_residuals():
    d, cov = geometry(), scalar_invariants()
    A, X, V, K, KK, acc2 = (d[n] for n in ("invN", "X", "V", "K", "KK", "acc2"))
    expected = (
        j.cut(V**2+j.mul(X, KK)-2*j.mul(X, acc2)),
        j.mul(V+j.mul(A, K), V+j.mul(A, K)),
        j.cut(j.mul(X, V, V)+j.mul(A, X, K, V)),
        j.cut(j.mul(X, V, V)-j.mul(X, X, acc2)),
        j.mul(X, X, V, V),
    )
    return {**{f"L{i+1}": j.zero(lhs-rhs) for i, (lhs, rhs) in enumerate(zip(cov["L"], expected))},
            "box": j.zero(cov["box"]-V-j.mul(A, K))}


def curvature_ibp_residual():
    """F2 R integration by parts checked against the 4D coordinate curvature."""
    d = geometry()
    f0, f1, f2 = (sp.Function(name)(j.t) for name in ("F20", "F2N", "F2NN"))
    F2 = j.taylor_N((f0, f1, f2), d["N"])
    normal_F = j.mul(d["invN"], sp.diff(F2, j.t)
                    - sum(d["shift_up"][i]*sp.diff(F2, j.coords[i+1]) for i in range(3)))
    spatial_F = j.cut(sum(sp.diff(F2, j.coords[i+1])*d["acc_up"][i] for i in range(3)))
    adm = j.cut(-j.mul(F2, d["R3"])+j.mul(F2, d["K"], d["K"])
                - j.mul(F2, d["KK"])+2*j.mul(d["K"], normal_F)-2*spatial_F)
    boundary = -2*sp.diff(j.mul(d["sqh"], F2, d["K"]), j.t)
    boundary += 2*sum(sp.diff(j.mul(d["sqh"], d["shift_up"][i], F2, d["K"])
                             + j.mul(d["sqg"], F2, d["acc_up"][i]), j.coords[i+1])
                      for i in range(3))
    return j.zero(j.mul(d["sqg"], j.mul(F2, scalar_invariants()["R4"])-adm)-boundary)

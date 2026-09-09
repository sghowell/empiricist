"""Metric-derived free-canonical matter and coupled scalar principal matrices."""

from functools import cache

import sympy as sp

from . import covariant
from . import jets as j
from . import quadratic as q

chi = sp.Function("chi")(j.t)
s = sp.Function("s")(j.t)


@cache
def matter_action():
    d = covariant.geometry()
    field = chi+j.eps*s*j.cx
    gradient = sp.Matrix([sp.diff(field, coord) for coord in j.coords])
    Y = j.cut((gradient.T*d["gi"]*gradient)[0])
    return j.mul(d["sqg"], Y)/2


def matter_bg(expr):
    velocity = sp.diff(chi, j.t)
    acceleration = -3*j.H*velocity
    jerk = j.dt(acceleration).subs(sp.diff(chi, j.t, 2), acceleration)
    return j.bg(expr.xreplace({sp.diff(chi, j.t, 3): jerk,
                              sp.diff(chi, j.t, 2): acceleration}))


@cache
def background():
    linear = matter_action().coeff(j.eps, 1).subs(j.k, 0)
    en = sp.cancel((sp.diff(linear, j.lapse)
                    - j.dt(sp.diff(linear, sp.diff(j.lapse, j.t))))/j.a**3)
    ea = sp.cancel((sp.diff(linear, j.zeta)
                    - j.dt(sp.diff(linear, sp.diff(j.zeta, j.t))))/(3*j.a**3))
    full_en, full_ea = q.background()["EN"]+en, q.background()["Ea"]+ea
    solution = sp.solve((full_en, full_ea), (q.F[0], q.F[1]), dict=True)[0]
    return {"matter_EN": en, "matter_Ea": ea, "EN": full_en, "Ea": full_ea,
            "solution": solution}


@cache
def unreduced():
    raw = 2*j.average((q.expand_action()+matter_action()).coeff(j.eps, 2))
    delta = q.C[0]/(4*q.B[0])
    shifted = q.substitute_functions(raw, {j.zeta: q.v+delta*j.lapse})
    L = sp.cancel(j.bg(shifted))
    n, ndot, vdot, sdot = j.lapse, sp.diff(j.lapse, j.t), sp.diff(q.v, j.t), sp.diff(s, j.t)
    boundaries = []
    for qdot, other, primitive in (
        (ndot, q.v, n*q.v), (ndot, n, n**2/2), (vdot, q.v, q.v**2/2)
    ):
        boundary = sp.cancel(sp.diff(L, qdot, other))*primitive
        boundaries.append(boundary)
        L = sp.cancel(L-j.dt(boundary))
    L = sp.cancel(matter_bg(q.substitute_functions(L, background()["solution"])))
    if L.has(ndot):
        raise RuntimeError("Lapse velocity did not cancel before constraint elimination")
    pure = q.derive()
    velocity = sp.diff(chi, j.t)
    # Verify each principal/constraint block before abbreviating its very
    # large background coefficient. Lower-derivative terms cannot supply k²
    # or a second time derivative after these algebraic constraints.
    checks = {
        "v_velocity": sp.cancel(sp.diff(L, vdot, 2)/(2*j.a**3)+3*pure["GT"]),
        "n_v_velocity": sp.cancel(sp.diff(L, n, vdot)/(j.a**3)-6*pure["Theta"]),
        "matter_velocity": sp.cancel(sp.diff(L, sdot, 2)/j.a**3-1),
        "matter_lapse_velocity": sp.cancel(sp.diff(L, n, sdot)/j.a**3-velocity*(3*delta-1)),
        "shift_constraint": sp.cancel(sp.diff(L, j.shift)/(j.a**3*j.k**2)
                                      -(2*pure["Theta"]*n-2*pure["GT"]*vdot-velocity*s)),
        "gradient_v": sp.cancel(sp.expand(sp.diff(L, q.v, 2)).coeff(j.k, 2)/(2*j.a)-pure["FT"]),
        "gradient_n_v": sp.cancel(sp.expand(sp.diff(L, n, q.v)).coeff(j.k, 2)/(2*j.a)-pure["Lambda"]),
        "gradient_matter": sp.cancel(sp.expand(sp.diff(L, s, 2)).coeff(j.k, 2)/j.a+1),
    }
    sigma_total = sp.cancel(sp.diff(L, n, 2)/(2*j.a**3))
    compact = j.a**3*(-3*pure["GT"]*vdot**2+sigma_total*n**2+6*pure["Theta"]*n*vdot
                        + sdot**2/2+velocity*(3*delta-1)*n*sdot+3*velocity*q.v*sdot
                        + j.k**2*(2*pure["Theta"]*n*j.shift-2*pure["GT"]*vdot*j.shift-velocity*j.shift*s))
    compact += j.a*j.k**2*(pure["FT"]*q.v**2+2*pure["Lambda"]*n*q.v-s**2/2)
    checks["full_unreduced_action"] = sp.cancel(L-compact)
    return {"L": L, "Sigma_total": sigma_total,
            "residuals": checks}


@cache
def derive():
    """Exact small-symbol reduction of the verified principal blocks."""
    full = unreduced()
    if any(value != 0 for value in full["residuals"].values()):
        raise RuntimeError(f"Unreduced matter block mismatch: {full['residuals']}")
    T, FT, th, sig, lam, delta, velocity = sp.symbols("T FT th sig lam delta velocity", real=True)
    n, b, v, vd, ss, sd, k2, a = sp.symbols("n b v vd s sd k2 a", real=True)
    L = a**3*(-3*T*vd**2+sig*n**2+6*th*n*vd+sd**2/2
              + velocity*(3*delta-1)*n*sd+k2*(2*th*n*b-2*T*vd*b-velocity*b*ss))
    L += a*k2*(FT*v**2+2*lam*n*v-ss**2/2)
    equations = [sp.diff(L, field) for field in (n, b)]
    solution = sp.solve(equations, (n, b), dict=True)[0]
    reduced = sp.cancel(L.subs(solution))
    kinetic = (sp.hessian(reduced, (vd, sd))/(2*a**3)).applyfunc(sp.cancel)
    # The sole k² v*vd term has boundary a*k²*T*lam*v²/th. Differentiate
    # coefficient via abstract cosmic-time jets; k is comoving/constant.
    H, Td, ld, thd = sp.symbols("H Td ld thd", real=True)
    boundary = a*k2*T*lam*v**2/th
    d_boundary = sum(sp.diff(boundary, f)*df for f, df in (
        (a, a*H), (T, Td), (lam, ld), (th, thd), (v, vd)))
    canonical = sp.cancel(reduced-d_boundary)
    potential = sp.hessian(canonical, (v, ss))
    gradient = potential.applyfunc(lambda e: sp.cancel(-sp.expand(e).coeff(k2)/(2*a)))
    return {"symbols": (T, FT, th, sig, lam, delta, velocity),
            "derivative_symbols": (H, Td, ld, thd),
            "kinetic": kinetic, "gradient": gradient,
            "constraints_residual": tuple(sp.cancel(eq.subs(solution)) for eq in equations),
            "Sigma_total": full["Sigma_total"], "unreduced_residuals": full["residuals"]}

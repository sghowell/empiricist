"""Reduce the *transcribed* KYY11 (4.24) scalar action on Theta != 0.

This is not yet a covariant-action expansion. All identities use cosmic-time
jets, with no division by H. A Fourier mode has k2 > 0; its common positive
spatial-average normalization is suppressed.
"""

from functools import lru_cache

import sympy as sp

a, H, GT, FT, Theta, Sigma, GTdot, Thetadot, k2, z, zdot, n, b = sp.symbols(
    "a H GT FT Theta Sigma GTdot Thetadot k2 z zdot n b", real=True
)


def dt_boundary(expr):
    """Total derivative for boundary terms depending only on a, GT, Theta, z."""
    allowed = {a, GT, Theta, z, k2}
    if not expr.free_symbols <= allowed:
        raise ValueError("Boundary derivative received an unsupported jet")
    return sum(sp.diff(expr, q) * dq for q, dq in (
        (a, a * H), (GT, GTdot), (Theta, Thetadot), (z, zdot)
    ))


@lru_cache(maxsize=1)
def derive():
    """Derive constraints and IBP coefficients, rather than inserting GS/FS."""
    raw = a**3 * (-3 * GT * zdot**2 + Sigma * n**2 + 6 * Theta * n * zdot)
    raw += a * k2 * (FT * z**2 + 2 * Theta * n * b - 2 * GT * zdot * b
                     + 2 * GT * n * z)
    constraints = [sp.diff(raw, q) for q in (n, b)]
    solution = sp.solve(constraints, (n, b), dict=True)[0]
    reduced = sp.cancel(raw.subs(solution))
    # The mixed z*zdot coefficient is removed by a displayed total derivative.
    boundary = sp.cancel(sp.diff(reduced, z, zdot) / 2) * z**2
    canonical = sp.cancel(reduced - dt_boundary(boundary))
    GS = sp.cancel(sp.diff(canonical, zdot, 2) / (2 * a**3))
    FS = sp.cancel(-sp.diff(canonical, z, 2) / (2 * a * k2))
    xi = a * GT**2 / Theta
    expected_FS = sp.cancel(dt_boundary(xi) / a - FT)
    residuals = {
        "lapse_constraint": sp.cancel(constraints[0].subs(solution)),
        "shift_constraint": sp.cancel(constraints[1].subs(solution)),
        "canonical_action": sp.cancel(canonical - a**3 * GS * zdot**2
                                    + a * k2 * FS * z**2),
        "kinetic_identity": sp.cancel(GS - Sigma * GT**2 / Theta**2 - 3 * GT),
        "gradient_identity": sp.cancel(FS - expected_FS),
    }
    return {"raw": raw, "solution": solution, "reduced": reduced, "boundary": boundary,
            "GS": GS, "FS": FS, "xi": xi, "residuals": residuals}


def independent_polynomial_check():
    """Independent FLINT expansion after clearing Theta²; no SymPy output input.

    Re-transcribe the constrained action and the differentiated boundary.
    This is an identity in Q[a,H,T,F,th,S,Td,thd,k2,z,v,b], not sampling.
    It checks algebra, not the physical validity of KYY11's input action.
    """
    from flint import fmpq_mpoly_ctx

    ctx = fmpq_mpoly_ctx.get(("a", "H", "T", "F", "th", "S", "Td", "thd",
                              "k2", "z", "v", "b"))
    a_, h, t, f, th, s, td, thd, kk, zz, v, bb = ctx.gens()
    # n = T*v/th; multiply the full constrained action by th² first.
    raw_scaled = a_**3 * (-3*t*v**2*th**2 + s*t**2*v**2 + 6*t*th**2*v**2)
    raw_scaled += a_*kk*(f*zz**2*th**2 + 2*th**2*t*v*bb - 2*t*v*bb*th**2
                        + 2*t**2*th*v*zz)
    gs_num = s*t**2 + 3*t*th**2
    fs_num = h*t**2*th + 2*t*td*th - t**2*thd - f*th**2
    boundary_scaled = a_*kk*((h*t**2*th + 2*t*td*th - t**2*thd)*zz**2
                             + 2*t**2*th*zz*v)
    residual = raw_scaled - a_**3*gs_num*v**2 + a_*kk*fs_num*zz**2 - boundary_scaled
    # A sign-error negative control must not disappear under simplification.
    flipped_boundary_residual = residual + 2*boundary_scaled
    return {"ibp_polynomial_zero": residual.is_zero(),
            "wrong_boundary_sign_detected": not flipped_boundary_residual.is_zero()}

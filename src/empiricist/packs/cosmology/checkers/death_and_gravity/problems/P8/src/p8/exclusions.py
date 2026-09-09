"""Exact algebra supporting the analytic all-time exclusion lemmas.

The global calculus/topology argument is in notes/s3-classification.md;
these identities alone are not a computer proof of that analytic theorem.
"""

from itertools import combinations

import sympy as sp

from . import gamma


def algebra():
    X, FT, A, c, d = sp.symbols("X FT A c d", real=True)
    T = FT+2*X*A
    delta = X*(2*A-4*c-X*d)/(2*T)
    lam = FT+4*X*c+FT*delta
    exceptional = sp.factor(lam-T*(1-3*delta))
    d_exceptional = 2*(X*A+FT)*(A-2*c)/(X*(3*X*A+2*FT))
    lam_no_C = sp.factor(lam.subs({c: 0, d: d_exceptional.subs(c, 0)}))
    lam_no_C_expected = 2*FT*(FT+2*X*A)/(2*FT+3*X*A)
    # If D is disabled, the positive prefactor forces A=2*c on shell.
    no_D_factor = 2*X*(FT+X*A)*(A-2*c)/T
    chart = gamma.principal_chart()
    gt, _ft, th, la, w, velocity, J = chart["symbols"]
    _H, _Td, _ld, thd = chart["derivative_symbols"]
    K, G = chart["kinetic"], chart["gradient"]
    return {
        "symbols": (X, FT, A, c, d),
        "exceptional_solution": d_exceptional,
        "positive_Lambda_without_C": lam_no_C,
        "residuals": {
            "exceptional_relation": sp.cancel(exceptional.subs(d, d_exceptional)),
            "no_C_D_Lambda": sp.cancel(lam.subs({c: 0, d: 0})-FT*(1+X*A/T)),
            "no_C_exceptional_Lambda": sp.cancel(lam_no_C-lam_no_C_expected),
            "no_D_exceptional_factor": sp.cancel(exceptional.subs(d, 0)-no_D_factor),
            "no_D_exceptional_Lambda": sp.cancel(lam.subs({d: 0, A: 2*c})-T.subs(A, 2*c)),
            "gamma_gradient": sp.cancel(G[0, 0].subs(th, 0)+gt*thd/la),
            "gamma_detK": sp.cancel(K.det()-gt**2*J/(2*la**2)),
            "matter_mismatch_in_regular_chart": sp.cancel((K-G).det()+(gt*w/la+velocity)**2/4),
        },
    }


def rows():
    """Finite inclusion lattice; witnesses and no-go lemmas supply verdicts."""
    table = []
    for count in range(5):
        for group in combinations("ABCD", count):
            enabled = set(group)
            m0 = "C" if "C" in enabled else "D" if "D" in enabled else None
            m1 = "CD_matter" if {"C", "D"} <= enabled else None
            table.append({"groups": "".join(group) or "baseline",
                          "M0": "E" if m0 else "N", "M0_witness": m0,
                          "M0_exclusion": None if m0 else "positive_Lambda_no_C_D",
                          "M1": "E" if m1 else "N", "M1_witness": m1,
                          "M1_exclusion": None if m1 else "luminal_matter_requires_C_and_D"})
    return table

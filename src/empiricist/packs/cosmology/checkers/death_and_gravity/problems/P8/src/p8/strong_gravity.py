"""An explicit conformal covariant regression of the strong-gravity loophole.

This is not a transcription of Ageeva et al.'s particular model. It checks
the same failed tensor-integral hypothesis with an independently solvable
canonical Einstein-frame cosmology. It is NOT in the frozen GR-tail class.
"""

from functools import cache

import sympy as sp

from . import jets as j
from . import quadratic as q


@cache
def derive():
    t, X = j.t, sp.Symbol("X", positive=True)
    D = 1+t**2
    I = sp.atan(t)+sp.pi/2
    T = I/D**2
    FX = 3/(4*I*D**4)-3*sp.diff(T, t)**2/(4*T)
    F = FX*X
    mapping = q.covariant_N_jets(F, sp.Integer(0), -T/2, sp.Integer(0), sp.Integer(0), X)
    mapping.update({j.H: 2*t/D, j.a: D})
    def specialize(expr):
        return sp.simplify(q.substitute_functions(q.substitute_functions(expr, mapping), mapping))
    d, bg = q.derive(), q.background()
    theta, lam, sigma = (specialize(d[key]) for key in ("Theta", "Lambda", "Sigma"))
    xi = sp.factor(D*T*lam/theta)
    FS = sp.simplify(sp.diff(xi, t)/D-T)
    GS = sp.simplify(sigma*T**2/theta**2+3*T)
    return {"a": D, "GT": T, "FT": T, "F": F, "F2": -T/2,
            "Theta": theta, "Lambda": lam, "FS": FS, "GS": GS,
            "xi": xi, "tensor_integral_primitive": I**2/2,
            "total_tensor_integral": sp.pi**2/2,
            "residuals": {"background_lapse": specialize(bg["EN"]),
                          "background_scale": specialize(bg["Ea"]),
                          "Theta": sp.simplify(theta-1/(2*D**3)),
                          "Lambda": sp.simplify(lam-T), "FS": sp.simplify(FS-3*T),
                          "GS": sp.simplify(GS-3*T), "xi": sp.simplify(xi-2*I**2),
                          "tensor_integrand": sp.simplify(sp.diff(I**2/2, t)-D*T)}}

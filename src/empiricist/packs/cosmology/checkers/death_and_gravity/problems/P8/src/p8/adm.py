"""Ia ADM coefficient identities, derived from covariant contractions/IBP.

Only the Ia completion is a source input. phi=t can be chosen locally and
globally on the frozen monotone-clock trajectories. X=1/N² in this chart.
"""

import sympy as sp

from .matter import ia_completion


def coefficients():
    X, f, fx, A1, A3 = sp.symbols("X F2 F2X A1 A3", real=True)
    A2, A4, A5 = ia_completion(f, fx, A1, A3, X)
    # sqrt(-g) times [F+Klag*(V+sqrtX*K)+(-F2)*R3+B*(K²-Kij²)
    # +2*sqrtX*F2phi*K+C*K*V+D*V²+E*acc²], modulo the displayed curvature boundary.
    B = f-X*A1
    C = sp.sqrt(X)*(4*fx-2*A1+X*A3)
    D = X*(A3+A4+X*A5)
    E = 4*X*fx-2*X*A1-X**2*A4
    GT, FT = -2*B, -2*f
    delta = X*(2*A1-4*fx-X*A3)/(2*GT)
    coupling = -2*f+4*X*fx
    Lambda = coupling+FT*delta
    residuals = {
        "Ia_kinetic_degeneracy": sp.cancel(D+3*C**2/(4*GT)),
        "Ia_lapse_gradient_cancellation": sp.cancel(E+FT*delta**2+2*coupling*delta),
        "Horndeski_locus_D": sp.cancel(D.subs({A1: 2*fx, A3: 0})),
        "Horndeski_locus_E": sp.cancel(E.subs({A1: 2*fx, A3: 0})),
        "corrected_D_dictionary": sp.cancel(coupling-GT-2*X*(2*fx-A1)),
    }
    return {"X": X, "F2": f, "F2X": fx, "A1": A1, "A3": A3,
            "A2": A2, "A4": A4, "A5": A5, "B": B, "C": C, "D": D, "E": E,
            "GT": GT, "FT": FT, "delta": delta, "Lambda": Lambda, "residuals": residuals}

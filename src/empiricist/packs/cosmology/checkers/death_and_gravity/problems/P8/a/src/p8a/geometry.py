"""Independent algebra for the conditional focusing implication and units."""

import sympy as sp


def identities():
    g, gp, expansion, expansion_p, rho, shear_sq = sp.symbols(
        "g gp expansion expansion_p rho shear_sq", real=True)
    # With the FK Ricci convention, Raychaudhuri is theta'=rho-theta^2/3-sigma^2.
    integrand = 3*gp**2+rho*g**2
    derivative = expansion_p*g**2+2*expansion*g*gp
    square = 3*(gp-expansion*g/3)**2
    decomposition = sp.expand((integrand-derivative-square-shear_sq*g**2).subs(
        rho, expansion_p+expansion**2/3+shear_sq))
    kappa, mass, phimax, hbar, inflation = sp.symbols(
        "kappa mass phimax hbar C", positive=True)
    qsei_second = inflation*hbar/(16*sp.pi**2)
    q2 = sp.simplify(kappa*qsei_second)
    q0 = kappa*mass**2*phimax**2/2
    grav = sp.Symbol("G", positive=True)
    return {"residuals": {"Raychaudhuri_completed_square": decomposition,
                          "Q2_four_dimensional_mapping": sp.simplify(
                              q2.subs(kappa, 8*sp.pi*grav)-inflation*grav*hbar/(2*sp.pi)),
                          "Q0_four_dimensional_mapping": sp.simplify(
                              q0.subs(kappa, 8*sp.pi*grav)-4*sp.pi*grav*mass**2*phimax**2)},
            "Q2_if_stated_local_QSEI_and_SEE_hold": str(q2),
            "Q0_if_stated_Wick_square_bound_and_SEE_hold": str(q0),
            "meaning_of_K": "trace of second fundamental form; K=theta(0), K=3H in 4D FLRW",
            "focusing_implication": "J[g] <= -K forces a focal point on a normal geodesic by tau",
            "not_derived": "local QSEI validity duration, Hadamard state bound, or semiclassical applicability"}

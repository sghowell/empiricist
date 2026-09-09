"""Source-level DHOST Ia formulas and exact principal-matrix algebra.

Conventions: A25 = arXiv:2501.09985v2, (+---), X=phi_dot², Y=chi_dot².
Equations (3), (6), (9c), (10c,d,h) are inputs, not derived covariantly here.
D uses MRV20 (8a), not A25's inconsistent (10g); see the source digest.
The exceptional condition is necessary on regular Theta != 0 patches with
rolling luminal matter. It is not a sufficient bounce/stability criterion.
"""

import sympy as sp


def ia_completion(F2, F2X, A1, A3, X):
    """A25 (3a-c), domain F2-X*A1 != 0."""
    den = 8 * (F2 - X * A1)**2
    A4 = (-16*X*A1**3 + 4*(3*F2 + 16*X*F2X)*A1**2 - X**2*F2*A3**2
          - (16*X**2*F2X - 12*X*F2)*A3*A1 - 16*F2X*(3*F2 + 4*X*F2X)*A1
          + 8*F2*(X*F2X - F2)*A3 + 48*F2*F2X**2) / den
    A5 = ((4*F2X - 2*A1 + X*A3)
          * (-2*A1**2 - 3*X*A1*A3 + 4*F2X*A1 + 4*F2*A3)) / den
    return -A1, sp.cancel(A4), sp.cancel(A5)


def source_matrices(GS, FS, GT, Theta, Q, PY, chi_dot, f, g):
    """A25 (9c); return kinetic K and gradient G in the source chart."""
    kinetic = sp.Matrix([[GS + GT**2 * chi_dot**2 * Q / Theta**2, chi_dot*Q*g],
                         [chi_dot*Q*g, Q]])
    gradient = sp.Matrix([[FS, chi_dot*PY*f], [chi_dot*PY*f, PY]])
    return kinetic, gradient


def luminal_identities():
    """At PY=Q>0, det(K-G)=-chi_dot² Q²(f-g)², forcing f=g for K-G PSD."""
    gs, fs, gt, th, q, v, f, g, c = sp.symbols("GS FS GT Theta Q v f g c", real=True)
    kinetic, gradient = source_matrices(gs, fs, gt, th, q, q, v, f, g)
    mismatch = sp.cancel((kinetic - gradient).det() + v**2*q**2*(f-g)**2)
    # On f=g, one exact luminal eigenvalue remains. The other need not be <= 1.
    ks = gs + gt**2*v**2*q/th**2 - v**2*q*g**2
    fs_schur = fs - v**2*q*g**2
    char = (gradient.subs(f, g) - c*kinetic).det()
    factor_residual = sp.cancel(char - q*(1-c)*(fs_schur-c*ks))
    return {"luminal_mismatch": mismatch, "exceptional_factorization": factor_residual}


def exceptional_relation(*, printed_a25_D=False):
    """Derive A25 (17) using MRV20 (8a); retain denominator hypotheses.

    printed_a25_D=True intentionally replays the inconsistent printed (10g).
    Its nonzero residual is retained as a source-transcription regression.
    """
    X, F2, F2X, A1, A3, th = sp.symbols("X F2 F2X A1 A3 Theta", real=True)
    GT, FT = -2*F2 + 2*A1*X, -2*F2
    delta = X*(2*A1 - 4*F2X - A3*X)/(2*GT)
    D_phi_dot = 2*X*((1 if printed_a25_D else 2)*F2X - A1)
    f = -(GT + D_phi_dot + FT*delta)/th
    g = -GT*(1 - 3*delta)/th
    numerator = sp.factor(sp.together(f-g).as_numer_denom()[0])
    solution = sp.solve(numerator, A3)[0]
    expected = 2*(X*A1-2*F2)*(A1-2*F2X)/(X*(3*X*A1-4*F2))
    return {"solution": solution,
            "residual": sp.cancel(solution-expected),
            "luminal_tensor_residual": sp.cancel(solution.subs(A1, 0) + 2*F2X/X)}


def principal_conditions_2x2(kinetic, gradient):
    """Return exact sign polynomials, NOT booleans inferred by sampling.

    Every 'strict' entry must be >0; every 'weak' entry >=0. Matrices must
    refer to a regular, nonsingular chart. Do not use at a constraint pole.
    """
    if kinetic.shape != (2, 2) or gradient.shape != (2, 2):
        raise ValueError("Expected two 2x2 matrices")
    if kinetic != kinetic.T or gradient != gradient.T:
        raise ValueError("Principal matrices must be symmetric")
    difference = kinetic - gradient
    return {
        "strict": (kinetic[0, 0], sp.factor(kinetic.det()),
                   gradient[0, 0], sp.factor(gradient.det())),
        "weak": (difference[0, 0], difference[1, 1], sp.factor(difference.det())),
    }

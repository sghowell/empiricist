"""Published known-answer checks against the independently expanded action."""

from functools import cache

import sympy as sp

from . import jets as j
from . import quadratic as q


@cache
def A25_dictionary():
    """A25 v2 (35),(37)-(40),(47),(55a,b), with its corrected D dictionary.

    The functions g1 and a1 stay arbitrary: this checks source coefficients,
    not selected numerical samples or just the prescribed benchmark curve.
    """
    X = sp.Symbol("X", positive=True)
    g, a1, Fvalue, FX, FXX = (sp.Function(name)(j.t)
                             for name in ("g1", "a1", "Fvalue", "FX", "FXX"))
    f = -sp.Rational(1, 2)+g*(1-X)
    A1 = a1*(X-1)
    A3 = 2*(X*A1-2*f)*(A1-2*sp.diff(f, X))/(X*(3*X*A1-4*f))
    F = Fvalue+FX*(X-1)+FXX*(X-1)**2/2
    mapping = q.covariant_N_jets(F, sp.Integer(0), f, A1, A3, X)
    gravity = {key: value for key, value in mapping.items() if key not in q.F}
    result, bg = q.derive(), q.background()
    Theta = j.H*(1+4*a1+g)+sp.diff(g, j.t)
    EN = Fvalue-2*FX+3*j.H*Theta+3*j.H*sp.diff(g, j.t)-3*g*(2*sp.diff(j.H, j.t)+3*j.H**2)
    Ea = Fvalue+2*sp.diff(j.H, j.t)+3*j.H**2
    FX_on_shell = -q.substitute_functions(bg["solution"][q.F[1]], gravity)/2
    sigma_mapping = {**gravity, q.F[2]: 6*FX_on_shell+4*FXX}
    sigma_derived = q.substitute_functions(result["Sigma"], sigma_mapping)
    sigma_source = FX_on_shell+2*FXX-2*g*sp.diff(g, j.t, 2)+3*sp.diff(g, j.t)**2
    sigma_source += j.H*((15*a1-4*g-15)*sp.diff(g, j.t)-(g-3)*sp.diff(a1, j.t))
    sigma_source -= (a1*(g-3)+(g-11)*g)*sp.diff(j.H, j.t)
    sigma_source -= 3*j.H**2*(a1*(g+15)+(g-1)*g+1)
    return {
        "GT": sp.cancel(q.substitute_functions(result["GT"], gravity)-1),
        "FT": sp.cancel(q.substitute_functions(result["FT"], gravity)-1),
        "Lambda": sp.cancel(q.substitute_functions(result["Lambda"], gravity)-(1-3*g)),
        "Theta": sp.cancel(q.substitute_functions(result["Theta"], gravity)-Theta),
        "background_EN": sp.cancel(q.substitute_functions(bg["EN"], mapping)-EN),
        "background_Ea": sp.cancel(q.substitute_functions(bg["Ea"], mapping)-Ea),
        "Sigma": sp.factor(sigma_derived-sigma_source),
        "Sigma_derived": sp.factor(sigma_derived),
        "Sigma_printed": sp.factor(sigma_source),
    }


@cache
def A25_reconstruction():
    """Actual covariant F jets, with no division by H in their definition.

    g and Theta are the smooth prescribed benchmark functions. The relation
    4H*a1=Theta-H*(1+g)-g_dot makes the apparent a1 quotients removable.
    """
    g, a1, FXX, target = (sp.Function(name)(j.t)
                         for name in ("g1", "a1", "FXX", "Sigma_target"))
    theta = sp.Function("Theta_target")(j.t)
    Ha1 = (theta-j.H*(1+g)-sp.diff(g, j.t))/4
    F0 = -2*sp.diff(j.H, j.t)-3*j.H**2
    FX = (F0+3*j.H*theta+3*j.H*sp.diff(g, j.t)
          -3*g*(2*sp.diff(j.H, j.t)+3*j.H**2))/2
    sigma = A25_dictionary()["Sigma_derived"]
    FXX_solution = sp.solve(sigma-target, FXX)[0]
    # Eliminate a1 and a1_dot together; cancellation is exact and verified.
    regular_FXX = sp.cancel(q.substitute_functions(FXX_solution, {a1: Ha1/j.H}))
    if j.H in sp.denom(regular_FXX).free_symbols or sp.denom(regular_FXX).has(j.H):
        raise ValueError("Unresolved H denominator in reconstructed FXX")
    X = sp.Symbol("X", positive=True)
    F = F0+FX*(X-1)+regular_FXX*(X-1)**2/2
    dictionary_theta = j.H*(1+4*a1+g)+sp.diff(g, j.t)
    residual = q.substitute_functions(regular_FXX, {theta: dictionary_theta})-FXX_solution
    return {"F": F, "F0": F0, "FX": FX, "FXX": regular_FXX,
            "Sigma_target": target,
            "residuals": {"regular_FXX": sp.cancel(residual),
                          "Sigma_target": sp.cancel(sigma.subs(FXX, FXX_solution)-target)}}


def CPS16_dictionary():
    """CPS16 (2.9)-(2.11) after its tensor-frame choice; no frame applied here."""
    T, H, Hdot, m1, m2, m3, a = sp.symbols("T H Hdot m1 m2 m3 a", real=True)
    theta, lam = T*H-m1/2, T-2*m3
    sigma = (m2-2*T*Hdot-6*T*H**2)/2
    source_A = T*(3*(2*T*H-m1)**2+2*T*(m2-2*T*Hdot-6*T*H**2))/(2*T*H-m1)**2
    source_Y = 2*a*T*(T-2*m3)/(2*T*H-m1)
    return {"kinetic": sp.cancel(source_A-(sigma*T**2/theta**2+3*T)),
            "gradient_numerator": sp.cancel(source_Y-a*T*lam/theta),
            "Horndeski_boundary": sp.cancel(lam.subs(m3, 0)-T)}


def luminal_interface():
    """Section-4-style P1(phi)Y+P0 principal interface, not its dynamics.

    Freezing coefficients at a point and normalizing the matter fluctuation
    by sqrt(2P1) leaves precisely the derived free-matter principal blocks.
    Time derivatives of that normalization and potentials are lower-order;
    they are not an authorization to import the free-matter background law.
    """
    from . import coupled, matter
    d = coupled.derive()
    T, _FT, th, S, lam, delta, velocity = d["symbols"]
    Q = sp.Symbol("Q", positive=True)
    l, sigma, FS = sp.symbols("l sigma FS", real=True)
    change = sp.diag(1, sp.sqrt(2*Q))
    K = change.T*d["kinetic"].subs({velocity: sp.sqrt(2*Q)*l, S: sigma+Q*l**2})*change
    G = change.T*d["gradient"].subs(velocity, sp.sqrt(2*Q)*l)*change
    G[0, 0] = FS  # unchanged independently derived metric gradient block
    sourceK, sourceG = matter.source_matrices(sigma*T**2/th**2+3*T, FS, T, th, Q, Q,
                                            l, -lam/th, -T*(1-3*delta)/th)
    return {f"{name}_{i}{m}": sp.cancel(matrix[i, m]-expected[i, m])
            for name, matrix, expected in (("K", K, sourceK), ("G", G, sourceG))
            for i in range(2) for m in range(2)}

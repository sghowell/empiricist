"""Regular Hamiltonian chart at gamma crossing, derived before dividing by Theta.

The canonical scalar coordinates are (v,s); p_v=-2*a^3*T*q*b, p_s=a^3*P.
Here q=k^2/a^2>0, b=a^2*shift, and a^3*chi_dot is constant. The matter-free
case omits (s,P) and sets chi_dot=0. No ghost/gradient conclusion is inferred
solely from multiplying the singular unitary-gauge matrices by Theta².
"""

from functools import cache

import sympy as sp


@cache
def hamiltonian():
    T, FT, th, S, lam, delta, l, q = sp.symbols("T FT th S lam delta l q", real=True)
    n, b, v, s, P = sp.symbols("n b v s P", real=True)
    w = l*(3*delta-1)
    J0 = S+3*th**2/T
    J = J0-w**2/2
    # Momentum constraint and the matter Legendre map, before eliminating n.
    vd, sd = (th*n-l*s/2)/T, P-w*n
    L = -3*T*vd**2+S*n**2+6*th*n*vd+sd**2/2+w*n*sd-3*l*vd*s
    L += q*(FT*v**2+2*lam*n*v-s**2/2+2*th*n*b-2*T*vd*b-l*b*s)
    before_n = sp.expand(-2*T*q*b*vd+P*sd-L)
    R = q*(th*b+lam*v)+w*P/2-3*l*s*th/(2*T)
    constant = P**2/2+q*l*b*s+q*s**2/2-FT*q*v**2-3*l**2*s**2/(4*T)
    lapse = -R/J
    regular = constant+R**2/J
    residuals = {
        "uneliminated_Hamiltonian": sp.cancel(before_n-(constant-J*n**2-2*R*n)),
        "lapse_constraint": sp.cancel(sp.diff(before_n, n).subs(n, lapse)),
        "regular_Hamiltonian": sp.cancel(before_n.subs(n, lapse)-regular),
    }
    return {"symbols": (T, FT, th, S, lam, delta, l, q), "states": (b, v, s, P),
            "w": w, "J0": J0, "J": J, "lapse": lapse, "density": regular,
            "residuals": residuals}


@cache
def principal_chart():
    """Swap the v canonical pair to b and derive its high-q principal action.

    For finite q the momentum Hessian can fail at an isolated q; the regular
    first-order Hamiltonian remains valid. On Lambda != 0 the Hessian is
    invertible for all sufficiently large q, which defines the principal
    kinetic/gradient matrices. Their coefficients are regular at Theta=0.
    """
    T, FT, th, lam, w, l, J, q = sp.symbols("T FT th lam w l J q", real=True)
    b, v, s, P = sp.symbols("b v s P", real=True)
    R = q*(th*b+lam*v)+w*P/2-3*l*s*th/(2*T)
    density = P**2/2+q*l*b*s+q*s**2/2-FT*q*v**2-3*l**2*s**2/(4*T)+R**2/J
    Hess = sp.hessian(density, (v, P))
    M = sp.diag(2*T*q, 1)
    Kexact = (M.T*Hess.inv()*M/2).applyfunc(sp.cancel)
    K = Kexact.applyfunc(lambda expr: sp.limit(expr, q, sp.oo))
    J0 = J+w**2/2
    expected_K = sp.Matrix([[T**2*J0/lam**2, -T*w/(2*lam)], [-T*w/(2*lam), sp.Rational(1, 2)]])
    # Leading spatial action has v=-Theta*b/Lambda. The canonical-pair swap
    # contributes the derivative of 2*a^3*T*q, not just a pointwise swap.
    H, Td, ld, thd = sp.symbols("H Td ld thd", real=True)
    beta = H+Td/T
    before_ibp = -2*T*beta*th/lam+FT*th**2/lam**2
    derivative = Td*th/lam+T*thd/lam-T*th*ld/lam**2
    # Boundary -a*k²*T*Theta*b²/Lambda; d(a*k²)/dt=H*a*k².
    G11 = sp.cancel(-(before_ibp+H*T*th/lam+derivative))
    scaled_FS = (H*T*lam+Td*lam+T*ld)*th-T*lam*thd-FT*th**2
    G = sp.Matrix([[G11, l/2], [l/2, sp.Rational(1, 2)]])
    residuals = {
        "momentum_Hessian": sp.cancel(Hess.det()-(2*q/J)*(q*lam**2-FT*J0)),
        "regular_gradient_IBP": sp.cancel(G11-scaled_FS/lam**2),
        **{f"kinetic_{i}{m}": sp.cancel(K[i, m]-expected_K[i, m])
           for i in range(2) for m in range(2)},
    }
    return {"symbols": (T, FT, th, lam, w, l, J), "derivative_symbols": (H, Td, ld, thd),
            "kinetic": K, "gradient": G, "scaled_FS": scaled_FS,
            "residuals": residuals}


@cache
def auxiliary_chart():
    """Independent b-chart kinetic derivation without any division by J.

    Keep lapse n while swapping the v canonical pair, then eliminate (v,n,P)
    jointly. This proves that J=0 is a principal kinetic degeneration, not
    merely failure of the already-lapse-reduced Hamiltonian chart. It is
    needed for the exclusions, which must not assume J nonzero in advance.
    """
    T, FT, th, lam, w, l, J, q = sp.symbols("T FT th lam w l J q", real=True)
    b, v, n, s, P, bd, sd = sp.symbols("b v n s P bd sd", real=True)
    R = q*(th*b+lam*v)+w*P/2-3*l*s*th/(2*T)
    constant = P**2/2+q*l*b*s+q*s**2/2-FT*q*v**2-3*l**2*s**2/(4*T)
    # Time-dependent canonical boundary affects gradient/lower terms only;
    # principal_chart separately retains and checks that contribution.
    L = 2*T*q*v*bd+P*sd-constant+J*n**2+2*R*n
    aux = (v, n, P)
    Hess = sp.hessian(L, aux)
    solution = sp.solve([sp.diff(L, variable) for variable in aux], aux)
    reduced = sp.cancel(L.subs(solution))
    K = (sp.hessian(reduced, (bd, sd))/2).applyfunc(lambda e: sp.limit(e, q, sp.oo))
    target = principal_chart()["kinetic"]
    return {"auxiliary_determinant": sp.factor(Hess.det()),
            "residuals": {**{f"kinetic_{i}{m}": sp.cancel(K[i, m]-target[i, m])
                              for i in range(2) for m in range(2)},
                          "determinant": sp.cancel(Hess.det()-4*q*(q*lam**2-FT*(J+w**2/2)))}}

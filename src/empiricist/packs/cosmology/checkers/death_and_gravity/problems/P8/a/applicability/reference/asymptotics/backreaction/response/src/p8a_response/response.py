"""Actual first RSET response from the conserved Hadamard trace identity.

FK is +---, R=+6*(Hdot+2H^2), not P8(b)'s convention. gamma multiplies
physical FK I_R2; GS uses the opposite tensor, so gamma=-(c3_GS+c4_GS/3).
No independent cosmological/Newton counterterms are included.
"""

from functools import cache

import sympy as sp

from . import kernel

ETA, A, HBAR = kernel.ETA, kernel.A, kernel.HBAR
GAMMA = sp.Symbol("gamma", real=True)


def curvature_response(potential, *, eta=ETA, a=A):
    """Lower orthonormal components of delta I_R2 at radiation."""
    v, vp, vpp = potential, sp.diff(potential, eta), sp.diff(potential, eta, 2)
    return {"density": 36*(vp/eta**5-v/eta**6)/a**4,
            "pressure": -12*(vpp/eta**4-3*vp/eta**5+3*v/eta**6)/a**4,
            "EED": -18*(vpp/eta**4-4*vp/eta**5+4*v/eta**6)/a**4}


def components(k, potential, clock_derivative, *, eta=ETA, a=A, hbar=HBAR, gamma=GAMMA):
    """Use Q' at fixed proper time, b'-b/eta at fixed conformal time.

    Q(eta)=q(A*eta^2/2), b=Q+integral(Q)/eta, V=-Q''-3Q'/eta.
    The preparation integral in b is essential before the clock conversion.
    """
    kp, kpp = sp.diff(k, eta), sp.diff(k, eta, 2)
    vp, vpp = sp.diff(potential, eta), sp.diff(potential, eta, 2)
    prefactor = hbar/(sp.pi**2*a**4)
    density = prefactor*((kp/eta**5-k/eta**6)/16
                         + (-3*vp/eta**5+3*potential/eta**6+clock_derivative/eta**7)/240)
    pressure = prefactor*((-kpp/eta**4+3*kp/eta**5-3*k/eta**6)/48
                          + (3*vpp/eta**4-9*vp/eta**5+10*potential/eta**6
                             + 5*clock_derivative/eta**7)/720)
    eed = prefactor*((-kpp/eta**4+4*kp/eta**5-4*k/eta**6)/32
                     + (3*vpp/eta**4-12*vp/eta**5+13*potential/eta**6
                        + 6*clock_derivative/eta**7)/480)
    finite = curvature_response(potential, eta=eta, a=a)
    return {name: value+gamma*finite[name]
            for name, value in (("density", density), ("pressure", pressure), ("EED", eed))}


def proper_time(k, q, **kwargs):
    eta = kwargs.get("eta", ETA)
    potential = -sp.diff(q, eta, 2)-3*sp.diff(q, eta)/eta
    return components(k, potential, sp.diff(q, eta), **kwargs)


def conformal_time(k, b, **kwargs):
    eta = kwargs.get("eta", ETA)
    potential = -sp.diff(b, eta, 2)-2*sp.diff(b, eta)/eta
    return components(k, potential, sp.diff(b, eta)-b/eta, **kwargs)


def v1_linear(b, *, eta=ETA, a=A):
    return (-3*eta**4*sp.diff(b, eta, 4)+17*eta**2*sp.diff(b, eta, 2)
            - 34*eta*sp.diff(b, eta)-4*b)/(60*a**4*eta**8)


@cache
def identities():
    b, k = sp.Function("b")(ETA), sp.Function("K")(ETA)
    q, j = sp.Function("Q")(ETA), sp.Function("J")(ETA)
    v = -sp.diff(b, ETA, 2)-2*sp.diff(b, ETA)/ETA
    values = conformal_time(k, b, gamma=0)
    rho0 = HBAR/(960*sp.pi**2*A**4*ETA**8)
    f = kernel.wick(k)
    box_f = (sp.diff(f, ETA, 2)+2*sp.diff(f, ETA)/ETA)/(A*ETA)**2
    theta = -box_f/2-HBAR*v1_linear(b)/(4*sp.pi**2)
    r1 = -6*v/(A*ETA)**2
    box_r1 = (sp.diff(r1, ETA, 2)+2*sp.diff(r1, ETA)/ETA)/(A*ETA)**2
    finite = curvature_response(v)
    local_num = 3*ETA**4*sp.diff(v, ETA, 2)-6*ETA**3*sp.diff(v, ETA)+7*ETA**2*v
    local_num += 4*ETA*sp.diff(b, ETA)-4*b
    results = {
        "FK_trace_from_GS_conserved_Hadamard_stress": values["density"]-3*values["pressure"]-theta,
        "linear_conservation_with_background_forcing": (sp.diff(values["density"], ETA)
            + 4*values["density"]/ETA-theta/ETA+8*rho0*sp.diff(b, ETA)),
        "EED_definition": values["EED"]-values["density"]+theta/2,
        "v1_in_potential_variables": v1_linear(b)-local_num/(60*A**4*ETA**8),
        "finite_tensor_trace": finite["density"]-3*finite["pressure"]+6*box_r1,
        "finite_tensor_conservation": sp.diff(finite["density"], ETA)
            + 3*(finite["density"]+finite["pressure"])/ETA,
    }
    replacements = {sp.diff(j, ETA, n): sp.diff(q, ETA, n-1) for n in range(1, 6)}
    b_from_q = q+j/ETA
    proper = proper_time(k, q, gamma=0)
    factors = {"density": 8, "pressure": sp.Rational(40, 3), "EED": 24}
    for name, value in values.items():
        at_fixed_proper = value.subs(b, b_from_q).doit().subs(replacements, simultaneous=True)
        results["proper_clock_conversion_"+name] = at_fixed_proper+factors[name]*rho0*j/ETA-proper[name]
    results["prepared_potential_from_proper_time_q"] = (
        v.subs(b, b_from_q).doit().subs(replacements, simultaneous=True)
        + sp.diff(q, ETA, 2)+3*sp.diff(q, ETA)/ETA)
    vv = sp.Function("V")(ETA)
    ratio = sp.Symbol("log_length_ratio", real=True)
    before = components(k, vv, sp.diff(q, ETA), gamma=0)
    after = components(k-ratio*vv, vv, sp.diff(q, ETA), gamma=0)
    for name, tensor in curvature_response(vv).items():
        results["subtraction_length_shift_"+name] = after[name]-before[name]+HBAR*ratio*tensor/(576*sp.pi**2)
    return {name: sp.simplify(value) for name, value in results.items()}


def controls():
    c = sp.Symbol("C", real=True)
    rho0 = HBAR/(960*sp.pi**2*A**4*ETA**8)
    b = sp.Function("b")(ETA)
    return {
        "homogeneous_constant_solves_trace_conservation": sp.diff(c/ETA**4, ETA)+4*c/ETA**5,
        "homogeneous_constant_not_fixed_by_trace": c/ETA**4,
        "drop_background_conservation_forcing": 8*rho0*sp.diff(b, ETA),
        "omit_proper_clock_conversion_density": 8*rho0*sp.Function("J")(ETA)/ETA,
        "finite_gamma_is_determined_by_A3": False,
        "finite_epsilon_remainder_follows_from_first_derivative_bound": False,
    }

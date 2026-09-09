"""Exact finite-amplitude Born-functional error, with identical local scheme.

The approximation is defined by its Wick functional, exact anomaly and past
density, then trace and conservation. It is NOT claimed to be a positive
state. R is the convergent integral k*(F-1-F1) dk, not scalar curvature.
"""

import sympy as sp

from .mode_bounds import exact_nonnegative


def born_trace(a, retarded_kernel, eta, *, hbar=1, gamma=0):
    """Exact geometry and local prescription, with only the mode remainder omitted.

    The input kernel is K_{a,lambda}[U] using the exact clock/history.
    This functional is an approximation to RSET, not a covariance/state.
    """
    h = sp.diff(a, eta)/a
    box = lambda value: (sp.diff(value, eta, 2)+2*h*sp.diff(value, eta))/a**2
    curvature = 6*sp.diff(a, eta, 2)/a**3
    v1 = (sp.diff(a, eta)**4/a**8-sp.diff(a, eta, 2)*sp.diff(a, eta)**2/a**7)/60
    v1 += sp.diff(a, eta, 2)**2/(8*a**6)-box(curvature)/120
    wick = -hbar*retarded_kernel/(8*sp.pi**2*a**2)
    return -box(wick)/2-hbar*v1/(4*sp.pi**2)-6*gamma*box(curvature)


def reconstruct_density(a, trace, eta, eta_start, initial_density):
    """State-fixed conserved reconstruction; initial density is explicit data."""
    s = sp.Dummy("s", real=True)
    integrand = (a**3*sp.diff(a, eta)*trace).subs(eta, s)
    return (a.subs(eta, eta_start)**4*initial_density
            + sp.Integral(integrand, (s, eta_start, eta)))/a**4


def bounds(mode_derivatives, duration, b0, b1, hubble_cap, inverse_a_fourth, *, hbar=1):
    """Generic actual-stress error bound with explicitly supplied geometric caps."""
    if len(mode_derivatives) != 3:
        raise ValueError("Need the integrated mode remainder through two derivatives")
    m0, m1, m2 = map(exact_nonnegative, mode_derivatives)
    t, b0, b1, h, ia4, hbar = map(exact_nonnegative,
        (duration, b0, b1, hubble_cap, inverse_a_fourth, hbar))
    pref = hbar*ia4/sp.pi**2
    return {"density": pref*(h*m1+(h**2+b0+t*b1)*m0)/8,
            "pressure": pref*(m2+3*h*m1+(3*h**2+b0+t*b1)*m0)/24,
            "EED": pref*(m2+4*h*m1+(4*h**2+2*t*b1)*m0)/16}


def components(a, remainder, integrated_history, eta):
    """Strip the common hbar/pi²; all quantities use the actual conformal clock."""
    h = sp.diff(a, eta)/a
    u = -sp.diff(a, eta, 2)/a
    r, rp, rpp = remainder, sp.diff(remainder, eta), sp.diff(remainder, eta, 2)
    j = integrated_history  # J'=U'*R, J=0 in the common past.
    return {"density": (-h*rp+(h**2-u)*r+j)/(8*a**4),
            "pressure": (rpp-3*h*rp+(3*h**2+u)*r+j)/(24*a**4),
            "EED": (rpp-4*h*rp+4*h**2*r+2*j)/(16*a**4)}


def calibration_bounds(mode_constants, b, delta_bar):
    """Error constants in hbar*delta²/(pi²*A⁴*eta_star⁸) units."""
    m0, m1, m2 = map(sp.Rational, mode_constants)
    b0, b1 = sp.Rational(b[0]), sp.Rational(b[1])
    cap = sp.Rational(delta_bar)
    return {"density": (2*m1+(4+cap*b0+3*cap*b1)*m0)/64,
            "pressure": (m2+6*m1+(12+cap*b0+3*cap*b1)*m0)/192,
            "EED": (m2+8*m1+(16+6*cap*b1)*m0)/128}


def wick_calibration_bounds(mode_constants, b0, delta_bar):
    """jth derivative units hbar*delta²/(pi²*A²*eta_star^(4+j))."""
    m0, m1, m2 = map(sp.Rational, mode_constants)
    return [m0/8, (m1+4*m0)/8,
            (m2+8*m1+(24+2*sp.Rational(delta_bar)*sp.Rational(b0))*m0)/8]


def identities():
    eta = sp.Symbol("eta", positive=True)
    a, r, j = (sp.Function(name)(eta) for name in ("a", "Rmode", "J"))
    h = sp.diff(a, eta)/a
    u = -sp.diff(a, eta, 2)/a
    values = components(a, r, j, eta)
    wick = r/(4*a**2)
    box = (sp.diff(wick, eta, 2)+2*h*sp.diff(wick, eta))/a**2
    return {"exact_remainder_trace": sp.simplify(values["density"]-3*values["pressure"]+box/2),
            "exact_remainder_conservation": sp.simplify((sp.diff(values["density"], eta)
                + 3*h*(values["density"]+values["pressure"])).subs(sp.diff(j, eta), sp.diff(u, eta)*r)),
            "exact_EED_remainder": sp.simplify(values["EED"]-(values["density"]+3*values["pressure"])/2),
            "history_integration_identity": sp.simplify(sp.diff(a, eta)*sp.diff(a, eta, 2)
                - a*sp.diff(a, eta, 3)-a**2*sp.diff(u, eta)),
            "drop_history_fails_conservation": sp.simplify((sp.diff(values["density"], eta)
                + 3*h*(values["density"]+values["pressure"])).subs({j: 0, sp.diff(j, eta): 0}))}

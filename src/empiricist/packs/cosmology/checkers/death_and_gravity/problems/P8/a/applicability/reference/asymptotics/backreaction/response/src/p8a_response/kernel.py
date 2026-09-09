"""Born normalization and the GS raw-Hadamard retarded Wick-square kernel.

H_lambda is the parametrix of Gottschalk--Siemssen 1809.03812v3 Section 2.5;
the Wick square has no extra alpha*R. hbar is not included in K. Integrals
begin in the flat-zero potential region of the preparation.
"""

from functools import cache

import sympy as sp

ETA = sp.Symbol("eta", positive=True)
A = sp.Symbol("A", positive=True)
HBAR = sp.Symbol("hbar", nonnegative=True)
LAMBDA = sp.Symbol("lambda", positive=True)
SPAN = sp.Symbol("T", positive=True)


def local_factor(eta=ETA, a=A, span=SPAN, length=LAMBDA):
    return sp.log(sp.sqrt(2)*a*eta*span/length)+sp.Rational(5, 6)


def history(potential, eta_start, *, eta=ETA, a=A, span=SPAN, length=LAMBDA):
    """Exact log integral, not a quadrature or a check of state hypotheses."""
    s = sp.Dummy("s", real=True)
    derivative = sp.diff(potential, eta).subs(eta, s)
    return (sp.Integral(derivative*sp.log((eta-s)/span), (s, eta_start, eta))
            + potential*local_factor(eta, a, span, length))


def wick(retarded_kernel, eta=ETA, a=A, hbar=HBAR):
    return -hbar*retarded_kernel/(8*sp.pi**2*a**2*eta**2)


def monomial_control(degree, duration, *, eta=ETA, a=A, length=LAMBDA):
    """V(s)=(s-eta_i)^degree is a kernel-only, NOT a Hadamard-state control.

    Its finite-order past zero is not a C-infinity preparation. The physical
    example uses the C-infinity switch in preparation.py instead.
    """
    if not isinstance(degree, int) or isinstance(degree, bool) or degree < 1:
        raise ValueError("The polynomial kernel control requires integer degree >= 1")
    return duration**degree*(sp.log(sp.sqrt(2)*a*eta*duration/length)
                             + sp.Rational(5, 6)-sp.harmonic(degree))


@cache
def identities():
    k, eta, s, r, duration = sp.symbols("k eta s r D", positive=True)
    u0 = sp.exp(-sp.I*k*eta)/sp.sqrt(2*k)
    du = -sp.sin(k*(eta-s))*sp.exp(-sp.I*k*s)/(k*sp.sqrt(2*k))
    born = sp.expand_complex(sp.conjugate(u0)*du+u0*sp.conjugate(du))
    expected = -sp.sin(2*k*(eta-s))/(2*k**2)
    # Integral_0^D log|(2x+r)/(2x-r)| dx, for D>r/2.
    primitive = (duration*sp.log((2*duration+r)/(2*duration-r))
                 + r*sp.log((4*duration**2-r**2)/r**2)/2)
    constant = sp.limit(primitive/r-sp.log(2*duration/r), r, 0, dir="+")
    v, flat_part = sp.symbols("V Fp")
    born_finite = v*sp.log(r)-flat_part-v*(sp.log(2*SPAN)+1)
    hadamard = -v/6+v*sp.log(r*A*ETA/(sp.sqrt(2)*LAMBDA))
    renormalized = -flat_part-v*local_factor()
    ratio = sp.Symbol("length_ratio", positive=True)
    change_wick = HBAR*v*sp.log(ratio)/(8*sp.pi**2*A**2*ETA**2)
    r1 = -6*v/(A**2*ETA**2)
    return {
        "Born_real_scalar_modulus_normalization": sp.trigsimp(born-expected),
        "spatial_kernel_constant_primitive": sp.simplify(
            sp.diff(primitive, duration)-sp.log((2*duration+r)/(2*duration-r))),
        "spatial_kernel_finite_constant": constant-1,
        "Hadamard_subtraction_includes_five_sixths": sp.expand_log(
            born_finite-hadamard-renormalized, force=True).expand(),
        "Wick_square_length_scale_shift": sp.simplify(
            change_wick+HBAR*sp.log(ratio)*r1/(48*sp.pi**2)),
        "auxiliary_span_cancels": sp.diff(-v*sp.log(SPAN)+v*local_factor(), SPAN),
    }


def controls():
    return {"omit_real_part_factor_two_error": sp.Rational(1, 2),
            "omit_spatial_finite_constant_error": sp.Integer(1),
            "omit_Hadamard_finite_piece_error": sp.Rational(1, 6),
            "omit_local_log_scale_derivative_error": sp.Integer(1),
            "monomial_histories_are_physical_C_infinity_preparations": False}

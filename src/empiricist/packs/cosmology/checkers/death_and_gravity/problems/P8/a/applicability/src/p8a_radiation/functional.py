"""Exact spectral, conformal-time and proper-time difference-QSEI identities."""

import sympy as sp

T = sp.Symbol("t", positive=True)
H = sp.Function("h")(T)


def proper_density(h=H, t=T):
    return (sp.diff(h, t, 2)**2-sp.Rational(3, 8)*sp.diff(h, t)**2/t**2
            +sp.Rational(105, 256)*h**2/t**4)


def identities():
    eta, scale, k, u = sp.symbols("eta A k u", positive=True)
    f = sp.Function("f")(eta)
    b = 1/eta
    bf_prime = sp.diff(b*f, eta)
    fpp = sp.diff(f, eta, 2)
    raw_eta = fpp**2+2*bf_prime**2+sp.Rational(8, 3)*fpp*bf_prime
    sos_eta = (fpp+sp.Rational(4, 3)*bf_prime)**2+sp.Rational(2, 9)*bf_prime**2
    reduced_eta = fpp**2+6*sp.diff(f, eta)**2/eta**2-12*f**2/eta**4
    boundary_eta = (-sp.Rational(8, 3)*f*sp.diff(f, eta)/eta**2
                    +sp.Rational(4, 3)*sp.diff(f, eta)**2/eta
                    -sp.Rational(14, 3)*f**2/eta**3)
    # Positive reference-mode norm before the triangular (alpha,k) integration.
    fr, fi, br, bi = sp.symbols("F_re F_im B_re B_im", real=True)
    fourier_f, fourier_b = fr+sp.I*fi, br+sp.I*bi
    amplitude = -sp.I*k*fourier_f-fourier_b
    squared = sp.expand(amplitude*sp.conjugate(amplitude))
    imaginary_cross = sp.im(fourier_f*sp.conjugate(fourier_b))
    integrated = sp.integrate(k*squared, (k, 0, u))
    target = (u**4*abs(fourier_f)**2/4+u**2*abs(fourier_b)**2/2
              -sp.Rational(2, 3)*u**3*imaginary_cross)

    # Independently change variables using t, rather than inserting eta formulas.
    at = sp.sqrt(2*scale*T)
    ft = H/at**sp.Rational(3, 2)
    eta_t = sp.sqrt(2*T/scale)
    d_eta = lambda expression: at*sp.diff(expression, T)
    transformed = sp.expand((d_eta(d_eta(ft))**2+6/eta_t**2*d_eta(ft)**2
                             -12*ft**2/eta_t**4)/at)
    raw_t = (sp.diff(H, T, 2)**2-2*sp.diff(H, T)*sp.diff(H, T, 2)/T
             +sp.Rational(15, 8)*H*sp.diff(H, T, 2)/T**2
             +sp.Rational(5, 2)*sp.diff(H, T)**2/T**2
             -sp.Rational(33, 8)*H*sp.diff(H, T)/T**3
             +sp.Rational(249, 256)*H**2/T**4)
    boundary_t = (sp.Rational(15, 8)*H*sp.diff(H, T)/T**2
                  -sp.diff(H, T)**2/T-sp.Rational(3, 16)*H**2/T**3)
    hardy_square = (sp.diff(H, T)/T-sp.Rational(3, 2)*H/T**2)**2
    hardy_boundary = -sp.Rational(3, 2)*H**2/T**3
    hardy_reduced = sp.diff(H, T)**2/T**2-sp.Rational(9, 4)*H**2/T**4
    improved = (sp.diff(H, T, 2)**2-sp.Rational(3, 8)*hardy_square
                -sp.Rational(111, 256)*H**2/T**4)

    return {
        "residuals": {
            "positive_spectral_square": sp.expand(squared-(k*k*abs(fourier_f)**2
                                               +abs(fourier_b)**2-2*k*imaginary_cross)),
            "triangular_frequency_integral": sp.simplify(integrated-target),
            "conformal_positive_square": sp.expand(raw_eta-sos_eta),
            "conformal_IBP": sp.simplify(raw_eta-reduced_eta-sp.diff(boundary_eta, eta)),
            "proper_time_pullback": sp.simplify(transformed-raw_t),
            "proper_time_IBP": sp.simplify(raw_t-proper_density()-sp.diff(boundary_t, T)),
            "weighted_Hardy_IBP": sp.simplify(hardy_square-hardy_reduced-sp.diff(hardy_boundary, T)),
            "flat_coefficient_upper_bound_IBP": sp.simplify(
                proper_density()-improved-sp.Rational(3, 8)*sp.diff(hardy_boundary, T)),
        },
        "spectral_prefactor": "hbar/(4*pi^3)",
        "spectral_norm": "integral_0^infty du [u^4*|F|^2/4+u^2*|B|^2/2-(2/3)*u^3*Im(F*conj(B))]",
        "Fourier_convention": "F(u)=integral exp(-i*u*eta)*f(eta) deta; B=Fourier(f/eta)",
        "conformal_positive_form": str(sos_eta),
        "conformal_reduced_density": str(reduced_eta),
        "proper_time_density": str(proper_density()),
        "flat_upper_bound_decomposition": str(improved),
        "overall_proper_time_prefactor": "hbar/(16*pi^2)",
        "sampling_dictionary": "f(eta)=a(eta)^(-3/2)*h(A*eta^2/2)",
        "bound": "integral h^2*(E_omega-E_reference) dt >= -Q[h]",
        "exact_comparison": "0 <= Q[h] <= hbar/(16*pi^2)*||hddot||^2 for every admissible h",
        "curvature_credit": "(3/8)*||hdot/t-3h/(2t^2)||^2+(111/256)*||h/t^2||^2",
        "not_optimality": "Q is the evaluated positive-type construction, not an optimal QEI over states",
    }

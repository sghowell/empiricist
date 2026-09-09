"""Independent normalized-mode, finite-clock and conserved-stress audits."""

import sympy as sp
from p8a_remainder import geometry, stress


def test_remainder_norm_equation_from_two_real_mode_components():
    eta, k = sp.symbols("eta k", positive=True)
    potential = sp.Function("U")(eta)
    real, imag = sp.Function("real")(eta), sp.Function("imag")(eta)
    norm = real**2+imag**2
    substitutions = {}
    for part in (real, imag):
        acceleration = -(k**2+potential)*part
        substitutions[sp.diff(part, eta, 2)] = acceleration
        substitutions[sp.diff(part, eta, 3)] = sp.diff(acceleration, eta)
    equation = sp.diff(norm, eta, 3)+4*(k**2+potential)*sp.diff(norm, eta)
    equation += 2*sp.diff(potential, eta)*norm
    assert sp.simplify(equation.subs(substitutions, simultaneous=True)) == 0


def test_remainder_exact_born_subtraction_cancels_linear_fifth_jet():
    eta, k = sp.symbols("eta k", positive=True)
    u, linear_error = sp.Function("U")(eta), sp.Function("e_linear")(eta)
    free = lambda value: sp.diff(value, eta, 3)+4*k**2*sp.diff(value, eta)
    full = lambda value: free(value)+4*u*sp.diff(value, eta)+2*sp.diff(u, eta)*value
    local_linear = -u/(2*k**2)+sp.diff(u, eta, 2)/(8*k**4)
    assert sp.simplify(free(local_linear)+2*sp.diff(u, eta)
                       - sp.diff(u, eta, 5)/(8*k**4)) == 0
    # e_linear restores the exact retarded Born solution, with zero past
    # jets; it solves L_free e_linear=-U^(5)/(8 k^4).
    approximation = 1+local_linear+linear_error+3*u**2/(8*k**4)
    nonlinear = (10*u*sp.diff(u, eta, 3)+20*sp.diff(u, eta)*sp.diff(u, eta, 2)
                 + 30*u**2*sp.diff(u, eta))/8
    target = nonlinear/k**4+4*u*sp.diff(linear_error, eta)+2*sp.diff(u, eta)*linear_error
    residual = full(approximation)-target
    rule = -4*k**2*sp.diff(linear_error, eta)-sp.diff(u, eta, 5)/(8*k**4)
    assert sp.simplify(residual.subs(sp.diff(linear_error, eta, 3), rule)) == 0
    # Retaining only a local adiabatic subtraction leaves a linear source,
    # and cannot by itself prove the advertised quadratic-amplitude bound.
    local_approximation = 1+local_linear+3*u**2/(8*k**4)
    assert sp.simplify(full(local_approximation)-nonlinear/k**4) == sp.diff(u, eta, 5)/(8*k**4)


def test_remainder_retarded_green_normalization_and_uv_integrals():
    duration, k, split = sp.symbols("duration k split", positive=True)
    green = (1-sp.cos(2*k*duration))/(4*k**2)
    assert green.subs(duration, 0) == 0
    assert sp.diff(green, duration).subs(duration, 0) == 0
    assert sp.diff(green, duration, 2).subs(duration, 0) == 1
    assert sp.simplify(sp.diff(green, duration, 3)+4*k**2*sp.diff(green, duration)) == 0
    for derivative in range(3):
        assert sp.integrate(k/k**(6-derivative), (k, split, sp.oo)) == (
            1/((4-derivative)*split**(4-derivative)))
    assert sp.integrate(k/k**4, (k, split, sp.oo)) == 1/(2*split**2)


def test_remainder_potential_from_exact_proper_to_conformal_clock():
    y = geometry.Y
    delta = geometry.DELTA
    f = sp.Function("f", positive=True)(y)
    scale = y*f**sp.Rational(1, 4)
    derivative = lambda value: f**sp.Rational(1, 4)*sp.diff(value, y)
    direct = sp.simplify(-derivative(derivative(scale))/scale)
    expected = -(sp.diff(f, y, 2)+3*sp.diff(f, y)/y)/(4*sp.sqrt(f))
    expected += sp.diff(f, y)**2/(8*f**sp.Rational(3, 2))
    assert sp.simplify(direct-expected) == 0
    p = sp.Function("p")(y)
    actual = direct.subs(f, 1-delta*p).doit()
    exported = geometry.to_symbolic(geometry.potential_jets()[0])
    assert sp.simplify(actual-exported) == 0
    assert sp.simplify(sp.diff(actual, delta).subs(delta, 0)
                       -(sp.diff(p, y, 2)+3*sp.diff(p, y)/y)/4) == 0


def test_remainder_stress_from_exact_covariant_trace_and_conservation():
    eta = sp.Symbol("eta", positive=True)
    a = sp.Function("a", positive=True)(eta)
    remainder = sp.Function("Rmode")(eta)
    history = sp.Function("J")(eta)
    hc = sp.diff(a, eta)/a
    potential = -sp.diff(a, eta, 2)/a
    # Strip hbar/pi^2. This Wick error is exactly the convergent mode
    # remainder, not a Taylor expansion of the physical clock or anomaly.
    wick_error = remainder/(4*a**2)
    theta = -(sp.diff(wick_error, eta, 2)+2*hc*sp.diff(wick_error, eta))/(2*a**2)
    rho = (-hc*sp.diff(remainder, eta)+(hc**2-potential)*remainder+history)/(8*a**4)
    pressure = (rho-theta)/3
    history_rule = {sp.diff(history, eta): sp.diff(potential, eta)*remainder}
    assert sp.simplify((sp.diff(rho, eta)+3*hc*(rho+pressure)).subs(history_rule)) == 0
    exported = stress.components(a, remainder, history, eta)
    assert sp.simplify(exported["density"]-rho) == 0
    assert sp.simplify(exported["pressure"]-pressure) == 0
    assert sp.simplify(exported["EED"]-rho+theta/2) == 0
    # Removing the history term leaves a definite conservation defect.
    incomplete_rho = rho-history/(8*a**4)
    incomplete_p = (incomplete_rho-theta)/3
    defect = sp.diff(incomplete_rho, eta)+3*hc*(incomplete_rho+incomplete_p)
    assert sp.simplify(defect+sp.diff(potential, eta)*remainder/(8*a**4)) == 0
    assert sp.simplify(defect) != 0

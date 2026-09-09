"""Independent rational Laurent replay, using no SymPy or prior arithmetic."""

from fractions import Fraction as Q


def clean(poly):
    return {int(power): Q(coefficient) for power, coefficient in poly.items() if coefficient}


def add(*polys):
    out = {}
    for poly in polys:
        for power, coefficient in poly.items():
            out[power] = out.get(power, Q(0))+coefficient
    return clean(out)


def scale(poly, value):
    return clean({power: coefficient*Q(value) for power, coefficient in poly.items()})


def shift(poly, power):
    return clean({old+power: coefficient for old, coefficient in poly.items()})


def multiply(left, right):
    out = {}
    for lp, lc in left.items():
        for rp, rc in right.items():
            out[lp+rp] = out.get(lp+rp, Q(0))+lc*rc
    return clean(out)


def derivative(poly):
    return clean({power-1: coefficient*power for power, coefficient in poly.items() if power})


def evaluate(poly, point):
    return sum((coefficient*Q(point)**power for power, coefficient in poly.items()), Q(0))


def integral(poly):
    """Exact basis [1,log(2)] on [1,2]."""
    rational, logarithm = Q(0), Q(0)
    for power, coefficient in poly.items():
        if power == -1:
            logarithm += coefficient
        else:
            rational += coefficient*(Q(2)**(power+1)-1)/(power+1)
    return [rational, logarithm]


def rows_equal(left, right):
    return all(a == b for a, b in zip(left, right, strict=True))


def source_stress():
    """Differentiate conformal K=eta^-1, then use t=A*eta^2/2."""
    k = {-1: Q(1)}
    kp = derivative(k)
    kpp, kppp = derivative(kp), derivative(derivative(kp))
    kk = multiply(k, k)
    k4 = multiply(kk, kk)
    numerator_rho = add(scale(multiply(kpp, k), 2), scale(multiply(kp, kp), -1))
    numerator_pressure = add(scale(kppp, 2), scale(multiply(kpp, k), -2), multiply(kp, kp))
    finite_rho = add(numerator_rho, scale(k4, -3))
    finite_pressure = add(scale(numerator_pressure, -1), scale(multiply(kp, kk), 12), scale(k4, -3))
    if finite_rho or finite_pressure:
        raise ValueError("Independent finite-curvature coefficients do not vanish")
    rho = scale(shift(numerator_rho, -4), Q(1, 2880))
    pressure = scale(shift(numerator_pressure, -4), Q(-1, 8640))
    if set(rho) != {-8} or set(pressure) != {-8}:
        raise ValueError("Radiation stress has the wrong conformal scaling")
    rho_t, pressure_t = rho[-8]/16, pressure[-8]/16
    trace_source = -rho_t+3*pressure_t
    trace_fk = -trace_source
    eed = rho_t-trace_fk/2
    if rho_t <= 0 or pressure_t <= 0 or eed <= 0:
        raise ValueError("Independent physical stress signs failed")
    return {
        "conformal_units": "hbar/(pi^2*A^4*eta^8)",
        "conformal_density_coefficient": str(rho[-8]),
        "conformal_pressure_coefficient": str(pressure[-8]),
        "proper_units": "hbar/(pi^2*t^4)",
        "proper_density_coefficient": str(rho_t),
        "proper_pressure_coefficient": str(pressure_t),
        "source_trace_coefficient": str(trace_source),
        "FK_trace_coefficient": str(trace_fk),
        "FK_EED_coefficient": str(eed),
        "finite_curvature_coefficients": ["0", "0"],
        "reference_credit_in_hbar_over_16pi2_units": str(16*eed),
    }


def benchmark(coefficients=(4, -12, 13, -6, 1)):
    h = clean(dict(enumerate(coefficients)))
    hp, hpp = derivative(h), derivative(derivative(h))
    if any(evaluate(poly, point) for poly in (h, hp) for point in (1, 2)):
        raise ValueError("Independent benchmark requires H2_0 endpoint jets")
    square = lambda poly: multiply(poly, poly)
    flat = square(hpp)
    weighted = shift(square(h), -4)
    difference = add(flat, scale(shift(square(hp), -2), Q(-3, 8)), scale(weighted, Q(105, 256)))
    reference = scale(weighted, Q(1, 320))
    absolute = add(difference, scale(reference, -1))
    hardy_square = square(add(shift(hp, -1), scale(shift(h, -2), Q(-3, 2))))
    hardy = add(flat, scale(hardy_square, Q(-3, 8)), scale(weighted, Q(-559, 1280)))
    # u=t^-3/2*h. Factor t^-3/2 out of every x derivative (d/dx=t*d/dt).
    u0 = h
    u1 = add(shift(derivative(u0), 1), scale(u0, Q(-3, 2)))
    u2 = add(shift(derivative(u1), 1), scale(u1, Q(-3, 2)))
    # u_x^2 dx = t^-4*u1(t)^2 dt, likewise for the other terms.
    log_positive = shift(add(square(u2), scale(square(u1), Q(17, 8)),
                             scale(square(u0), Q(161, 1280))), -4)
    answers = {"flat": integral(flat), "difference": integral(difference),
               "reference_credit": integral(reference), "absolute": integral(absolute),
               "absolute_Hardy": integral(hardy), "absolute_log_positive": integral(log_positive)}
    if any(not rows_equal(answers["absolute"], answers[key])
           for key in ("absolute_Hardy", "absolute_log_positive")):
        raise ValueError("Independent absolute functional representations disagree")
    return {"polynomial_coefficients_ascending": [str(value) for value in coefficients],
            "proper_interval": ["1", "2"], "integral_basis": ["1", "log(2)"],
            "normalized_by": "hbar/(16*pi^2)",
            "exact_integrals": {key: [str(value) for value in row] for key, row in answers.items()}}

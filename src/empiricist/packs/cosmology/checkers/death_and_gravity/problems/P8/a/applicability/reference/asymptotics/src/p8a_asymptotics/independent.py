"""Independent exact rational sparse-polynomial and exponent calculations.

No SymPy or prior symbolic modules are imported. The eight coordinates are
(eta, eta_prime, x1, x2, x3, y1, y2, y3).
"""

from fractions import Fraction
from math import factorial

DIMENSION = 8
ZERO = (0,)*DIMENSION


def add(*polynomials):
    result = {}
    for polynomial in polynomials:
        for powers, value in polynomial.items():
            result[powers] = result.get(powers, Fraction(0))+value
    return {powers: value for powers, value in result.items() if value}


def scale(polynomial, factor):
    factor = Fraction(factor)
    return {powers: value*factor for powers, value in polynomial.items() if value*factor}


def constant(value):
    return {ZERO: Fraction(value)} if value else {}


def variable(axis):
    powers = list(ZERO)
    powers[axis] = 1
    return {tuple(powers): Fraction(1)}


def multiply(left, right):
    result = {}
    for p_left, v_left in left.items():
        for p_right, v_right in right.items():
            powers = tuple(a+b for a, b in zip(p_left, p_right))
            result[powers] = result.get(powers, Fraction(0))+v_left*v_right
    return {powers: value for powers, value in result.items() if value}


def power(polynomial, exponent):
    if not isinstance(exponent, int) or exponent < 0:
        raise ValueError("A nonnegative integer polynomial power is required")
    result = constant(1)
    for _ in range(exponent):
        result = multiply(result, polynomial)
    return result


def derivative(polynomial, axis):
    result = {}
    for powers, value in polynomial.items():
        degree = powers[axis]
        if degree:
            shifted = list(powers)
            shifted[axis] -= 1
            result[tuple(shifted)] = value*degree
    return result


def laplacian(polynomial, axes):
    return add(*(derivative(derivative(polynomial, axis), axis) for axis in axes))


def substitute_constant(polynomial, axis, value):
    value = Fraction(value)
    result = {}
    for powers, coefficient in polynomial.items():
        shifted = list(powers)
        shifted[axis] = 0
        shifted = tuple(shifted)
        result[shifted] = result.get(shifted, Fraction(0))+coefficient*value**powers[axis]
    return {powers: coefficient for powers, coefficient in result.items() if coefficient}


def evaluate(polynomial, coordinates):
    if len(coordinates) != DIMENSION:
        raise ValueError("Exactly eight coordinates are required")
    result = Fraction(0)
    for powers, value in polynomial.items():
        term = value
        for coordinate, degree in zip(coordinates, powers):
            term *= Fraction(coordinate)**degree
        result += term
    return result


def evolve(displacement, velocity, time_axis, spatial_axes, initial_time=2):
    elapsed = add(variable(time_axis), constant(-initial_time))
    answer = {}
    for offset, data in enumerate((displacement, velocity)):
        current, order = data, 0
        while current:
            degree = 2*order+offset
            answer = add(answer, scale(multiply(power(elapsed, degree), current),
                                       Fraction(1, factorial(degree))))
            current = laplacian(current, spatial_axes)
            order += 1
    return answer


def wave_family(time_axis, space):
    time = variable(time_axis)
    x, y, z = (variable(axis) for axis in space)
    return (add(constant(1), time, power(time, 2), power(x, 2), multiply(y, z)),
            add(multiply(time, x), multiply(x, y), z),
            add(power(time, 3), scale(multiply(time, power(x, 2)), 3),
                power(y, 2), scale(power(z, 2), -1)))


def cauchy_replay():
    original = add(*(scale(multiply(left, right), weight) for weight, left, right in zip(
        (Fraction(1), Fraction(2), Fraction(1, 3)),
        wave_family(0, (2, 3, 4)), wave_family(1, (5, 6, 7)))))
    data = {}
    for i in range(2):
        for j in range(2):
            item = original
            if i:
                item = derivative(item, 0)
            if j:
                item = derivative(item, 1)
            data[i, j] = substitute_constant(substitute_constant(item, 0, 2), 1, 2)
    first = evolve(data[0, 0], data[0, 1], 1, (5, 6, 7))
    second = evolve(data[1, 0], data[1, 1], 1, (5, 6, 7))
    extended = evolve(first, second, 0, (2, 3, 4))
    if extended != original:
        raise ValueError("Independent double Cauchy evolution failed")
    for axis, space in ((0, (2, 3, 4)), (1, (5, 6, 7))):
        if add(derivative(derivative(extended, axis), axis), scale(laplacian(extended, space), -1)):
            raise ValueError("Independent extended kernel fails a wave equation")
    return {
        "independent_monomial_table": [[list(powers), str(value)]
                                        for powers, value in sorted(extended.items())],
        "through_zero_value": str(evaluate(extended, (0, -1, 1, 2, -1, 2, 0, 1))),
        "both_wave_equations_exact": True,
        "both_variable_Cauchy_reconstruction_exact": True,
    }


def scaling_replay():
    # Each derivative lowers its exponent by one; the proper-time derivative
    # contributes another eta^-1/A. For F=eta^p eta_prime^q the diagonal
    # coefficient is (p-1)(q-1), with A^-4 eta^(p+q-6).
    def monomial(p, q):
        return Fraction(p-1)*Fraction(q-1), Fraction(p+q-6)

    # Leibniz allocations (i,j) differentiate F or the reciprocal factors.
    allocations = []
    for i in range(2):
        for j in range(2):
            allocations.append({"left_F_derivatives": i, "right_F_derivatives": j,
                                "coefficient": str(Fraction((-1)**(2-i-j))),
                                "diagonal_eta_power": -6+i+j})
    reference = Fraction(1, 320)
    proper_reference = reference/Fraction(2)**4
    zero_c, zero_power = monomial(0, 0)
    linear_c, linear_power = monomial(1, 1)
    restricted_c, restricted_power = monomial(-1, -1)
    return {
        "point_split_Leibniz_allocations": allocations,
        "reference_conformal_coefficient_in_hbar_over_pi2_units": str(reference),
        "reference_proper_coefficient_in_hbar_over_pi2_units": str(proper_reference),
        "proper_state_difference_terms": [
            {"eta_power": exponent, "two_power": str(Fraction(exponent, 2)),
             "A_power": str(-4-Fraction(exponent, 2)), "t_power": str(Fraction(exponent, 2))}
            for exponent in (-6, -5, -4)],
        "constant_mean": {"coefficient": str(zero_c), "eta_power": str(zero_power)},
        "linear_mean": {"coefficient": str(linear_c), "eta_power": str(linear_power)},
        "restricted_domain_mean": {"coefficient": str(restricted_c), "eta_power": str(restricted_power)},
        "normalized_remainder_powers": [8+exponent for exponent in (-6, -5, -4)],
        "normalized_SEE_source_powers": [8+exponent for exponent in (-4, 0)],
    }


def error_at(cutoff, *, m0, m1, m2, a, kappa, b, ell, radiation_c):
    cutoff, m0, m1, m2, a, kappa, b, ell, radiation_c = map(Fraction,
        (cutoff, m0, m1, m2, a, kappa, b, ell, radiation_c))
    return (m0*cutoff**2+m1*cutoff**3
            +(m2+abs(radiation_c-3*b*a**2/kappa))*cutoff**4
            +abs(ell)*a**4*cutoff**8/kappa)

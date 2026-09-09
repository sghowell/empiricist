"""Exact polynomial checks of the written smooth two-variable Cauchy proof.

These finite sums are a polynomial verification interface, not an analytic
series definition for arbitrary smooth Cauchy data. The latter use Kirchhoff
localization in notes/proof.md.
"""

import sympy as sp

ETA, ETAP = sp.symbols("eta eta_prime", real=True)
X = sp.symbols("x1:4", real=True)
Y = sp.symbols("y1:4", real=True)
VARIABLES = (ETA, ETAP, *X, *Y)
INITIAL_TIME = sp.Integer(2)


def laplacian(expression, space):
    return sp.expand(sum(sp.diff(expression, coord, 2) for coord in space))


def wave(expression, time, space):
    return sp.simplify(sp.diff(expression, time, 2)-laplacian(expression, space))


def polynomial_cauchy(displacement_data, velocity_data, elapsed, space):
    """Return C_s f+S_s g exactly, allowing other variables as parameters."""
    if any(sp.sympify(elapsed).has(coord) for coord in space):
        raise ValueError("Elapsed time must be independent of the spatial variables")
    answer = sp.Integer(0)
    for offset, data in enumerate((displacement_data, velocity_data)):
        current = sp.expand(data)
        try:
            sp.Poly(current, *space)
        except sp.PolynomialError as exc:
            raise ValueError("Only polynomial data are admitted by this interface") from exc
        order = 0
        while current != 0:
            degree = 2*order+offset
            answer += elapsed**degree*current/sp.factorial(degree)
            current = laplacian(current, space)
            order += 1
    return sp.expand(answer)


def double_cauchy(data, initial_time=INITIAL_TIME):
    if set(data) != {(0, 0), (1, 0), (0, 1), (1, 1)}:
        raise ValueError("All four bisolution Cauchy data are required")
    first = polynomial_cauchy(data[0, 0], data[0, 1], ETAP-initial_time, Y)
    second = polynomial_cauchy(data[1, 0], data[1, 1], ETAP-initial_time, Y)
    return polynomial_cauchy(first, second, ETA-initial_time, X)


def benchmark_wave(time, space):
    x, y, z = space
    return (1+time+time**2+x**2+y*z,
            time*x+x*y+z,
            time**3+3*time*x**2+y**2-z**2)


def benchmark_kernel():
    return sp.expand(sum(weight*left*right for weight, left, right in zip(
        (1, 2, sp.Rational(1, 3)), benchmark_wave(ETA, X), benchmark_wave(ETAP, Y))))


def cauchy_data(kernel, initial_time=INITIAL_TIME):
    return {(i, j): sp.diff(kernel, ETA, i, ETAP, j).subs(
        {ETA: initial_time, ETAP: initial_time}) for i in range(2) for j in range(2)}


def coefficient_table(expression):
    return [[list(powers), str(coefficient)] for powers, coefficient in sorted(
        sp.Poly(sp.expand(expression), *VARIABLES).terms())]


def identities():
    original = benchmark_kernel()
    data = cauchy_data(original)
    extended = double_cauchy(data)
    reversed_evolution = polynomial_cauchy(
        polynomial_cauchy(data[0, 0], data[1, 0], ETA-INITIAL_TIME, X),
        polynomial_cauchy(data[0, 1], data[1, 1], ETA-INITIAL_TIME, X),
        ETAP-INITIAL_TIME, Y)
    wrong_data = dict(data)
    wrong_data[1, 1] = sp.Integer(0)
    wrong = double_cauchy(wrong_data)
    recovered = cauchy_data(extended)
    return {
        "residuals": {
            "left_wave_equation": wave(extended, ETA, X),
            "right_wave_equation": wave(extended, ETAP, Y),
            "both_variable_evolution_matches_original": sp.expand(extended-original),
            "variable_evolution_order_commutes": sp.expand(extended-reversed_evolution),
            **{f"data_{i}{j}": sp.expand(recovered[i, j]-data[i, j])
               for i in range(2) for j in range(2)},
        },
        "initial_slice_eta": str(INITIAL_TIME),
        "spatial_dimensions_each_variable": 3,
        "independent_monomial_table": coefficient_table(extended),
        "through_zero_value": str(extended.subs(dict(zip(VARIABLES, (0, -1, 1, 2, -1, 2, 0, 1))))),
        "omitted_mixed_data_control_is_nonzero": sp.expand(wrong-original) != 0,
        "noncompact_polynomial_data": True,
        "polynomial_benchmark_proves_general_smooth_PDE_theorem": False,
    }

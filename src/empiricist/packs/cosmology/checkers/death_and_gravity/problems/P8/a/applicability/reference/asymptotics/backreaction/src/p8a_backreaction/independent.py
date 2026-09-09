"""Independent rational polynomial certificates; no SymPy imports."""

from fractions import Fraction
from math import comb


def clean(polynomial):
    values = [Fraction(item) for item in polynomial]
    while values and values[-1] == 0:
        values.pop()
    return values


def add(left, right):
    answer = [Fraction(0)]*max(len(left), len(right))
    for values in (left, right):
        for index, value in enumerate(values):
            answer[index] += value
    return clean(answer)


def scaled(polynomial, coefficient):
    return clean([Fraction(coefficient)*item for item in polynomial])


def multiply(left, right):
    if not left or not right:
        return []
    answer = [Fraction(0)]*(len(left)+len(right)-1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            answer[i+j] += a*b
    return clean(answer)


def fourth_power(polynomial):
    square = multiply(polynomial, polynomial)
    return multiply(square, square)


def bernstein(polynomial, endpoint=Fraction(1, 4)):
    polynomial = clean(polynomial)
    degree = len(polynomial)-1
    return [sum((polynomial[j]*endpoint**j*Fraction(comb(k, j), comb(degree, j))
                 for j in range(k+1)), Fraction(0)) for k in range(degree+1)]


def root_comparison(coefficient, *, lower):
    approximation = [Fraction(1), Fraction(-1, 4), -Fraction(coefficient)]
    fourth = fourth_power(approximation)
    difference = add([Fraction(1), Fraction(-1)], scaled(fourth, -1))
    if not lower:
        difference = scaled(difference, -1)
    if difference[:2] != [0, 0]:
        raise ValueError("Root comparison lacks the required double zero")
    return clean(difference[2:])


def certify_polynomial(polynomial, endpoint=Fraction(1, 4)):
    coefficients = bernstein(polynomial, endpoint)
    if any(item < 0 for item in coefficients):
        raise ValueError("Nonnegative Bernstein certificate failed")
    return {"power_coefficients": [str(item) for item in polynomial],
            "Bernstein_coefficients": [str(item) for item in coefficients],
            "domain": ["0", str(endpoint)], "all_coefficients_nonnegative": True}


def replay():
    lower = root_comparison(Fraction(1, 9), lower=True)
    upper = root_comparison(Fraction(3, 32), lower=False)
    endpoint = Fraction(1, 4)
    lower_minimum = 1-endpoint/4-endpoint**2/9
    upper_minimum = 1-endpoint/4-3*endpoint**2/32
    if min(lower_minimum, upper_minimum) <= 0:
        raise ValueError("Fourth-power comparison is on a nonpositive root branch")
    root_lower, root_upper = Fraction("0.9306048591"), Fraction("0.9306048592")
    if not root_lower**4 < 1-endpoint < root_upper**4:
        raise ValueError("Independent rational fourth-root enclosure failed")
    maximum_ratio = (2-endpoint)/(1-endpoint)**2
    density_coefficient = Fraction(1, 15360)
    d_coefficient = density_coefficient/3
    surrogate_rho_coefficient = 16*density_coefficient/d_coefficient
    y_ode_coefficient = Fraction(16, 3)*surrogate_rho_coefficient
    return {
        "lower_root_polynomial": certify_polynomial(lower),
        "upper_root_polynomial": certify_polynomial(upper),
        "positive_root_comparison_minima": [str(lower_minimum), str(upper_minimum)],
        "root_at_z_quarter_enclosure": {"lower": str(root_lower), "upper": str(root_upper), "strict": True},
        "Taylor_error_coefficients": {"lower": "3/32", "upper": "1/9"},
        "frozen_defect_ratio_maximum": str(maximum_ratio),
        "frozen_defect_constants": {"density": str(3*maximum_ratio/4),
                                    "pressure": str(5*maximum_ratio/4), "EED": str(9*maximum_ratio/4)},
        "d_coefficient_in_kappa_hbar_over_pi2_units": str(d_coefficient),
        "surrogate_density_coefficient_in_epsilon_d_A4_over_kappa_a8_units": str(surrogate_rho_coefficient),
        "scale_fourth_ODE_epsilon_d_A4_coefficient": str(y_ode_coefficient),
        "wrong_scale_fourth_ODE_64_residual_coefficient": str(y_ode_coefficient-64),
    }

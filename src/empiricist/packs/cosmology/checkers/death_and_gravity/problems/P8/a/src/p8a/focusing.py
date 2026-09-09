"""A certified two-parameter improvement of the frozen local-QEI focusing trial."""

from functools import lru_cache

import sympy as sp

from .partition import A, P, R, X, integrate_poly, localized_norm

COEFFICIENTS = sp.symbols("c0 c1", real=True)
ALPHA = sp.Rational(1, 10**6)  # Q2/tau**2; dimensionless illustration, not field calibration
BETA = sp.Rational(1, 100)  # Q0*tau**2
ZETA = sp.Integer(0)  # rho0*tau**2
PSI = X**2*(1-X)**2
BASIS = (PSI, PSI*(2*X-1))


def trial(coefficients=COEFFICIENTS):
    if len(coefficients) != len(BASIS):
        raise ValueError("Frozen trial requires exactly two coefficients")
    return sp.expand(P+sum(coefficient*basis
                           for coefficient, basis in zip(coefficients, BASIS, strict=True)))


def threshold(tail, alpha=ALPHA, beta=BETA, zeta=ZETA):
    """Dimensionless nu*tau; local QEI and initial Ricci assumptions are external."""
    alpha, beta, zeta = map(sp.sympify, (alpha, beta, zeta))
    if not alpha >= 0 or not beta >= 0 or not zeta <= 0:
        raise ValueError("Require Q2 >= 0, Q0 >= 0 and rho0 <= 0")
    endpoints = [tail.subs(X, 0), sp.diff(tail, X).subs(X, 0),
                 tail.subs(X, 1)-1, sp.diff(tail, X).subs(X, 1)]
    if any(sp.simplify(value) != 0 for value in endpoints):
        raise ValueError("Tail violates the frozen endpoint jets")
    return sp.expand(alpha*localized_norm(tail)
                     +beta*(A*integrate_poly(P**2)+R*integrate_poly(tail**2))
                     +3/R*integrate_poly(sp.diff(tail, X)**2)
                     +zeta*A*integrate_poly(1-P**2))


@lru_cache(maxsize=1)
def optimize():
    expression = threshold(trial())
    zero = dict.fromkeys(COEFFICIENTS, 0)
    constant = expression.subs(zero)
    linear = sp.Matrix([sp.diff(expression, value).subs(zero)/2 for value in COEFFICIENTS])
    gram = sp.hessian(expression, COEFFICIENTS)/2
    optimum = (-gram.inv()*linear).applyfunc(sp.cancel)
    improvement = sp.cancel((linear.T*gram.inv()*linear)[0])
    minimum = sp.cancel(constant-improvement)
    cvec = sp.Matrix(COEFFICIENTS)
    residuals = {
        "quadratic_reconstruction": sp.expand(expression-constant-2*(linear.T*cvec)[0]
                                               -(cvec.T*gram*cvec)[0]),
        "stationarity_0": sp.cancel((gram*optimum+linear)[0]),
        "stationarity_1": sp.cancel((gram*optimum+linear)[1]),
        "completed_square_constant": sp.cancel((optimum.T*gram*optimum)[0]-improvement),
    }
    return {"expression": expression, "gram": gram, "linear": linear,
            "cubic_threshold": constant, "optimum": optimum,
            "improvement": improvement, "optimized_threshold": minimum,
            "residuals": residuals}

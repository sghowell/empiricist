"""Small exact sign certificates: FLINT Sturm counts and rational Bernstein bounds."""

from fractions import Fraction
from itertools import pairwise
from math import comb

import sympy as sp
from flint import fmpq, fmpq_poly


def _sign(value):
    return 1 if value > 0 else -1 if value < 0 else 0


def _variations(signs):
    nonzero = [value for value in signs if value]
    return sum(a != b for a, b in pairwise(nonzero))


def sturm_positive(coefficients, lower=Fraction(0), upper=None):
    """Prove a rational polynomial strictly positive on [lower,upper].

    coefficients are ascending. upper=None means +infinity (strictly
    positive at every finite point). No floating arithmetic is used.
    """
    co = [Fraction(value) for value in coefficients]
    p = fmpq_poly([fmpq(v.numerator, v.denominator) for v in co])
    if not p:
        raise ValueError("The zero polynomial is not strictly positive")
    lo = fmpq(lower.numerator, lower.denominator)
    hi = None if upper is None else fmpq(upper.numerator, upper.denominator)
    if p(lo) <= 0 or (hi is not None and p(hi) <= 0):
        raise ValueError("Polynomial is not strictly positive at an endpoint")
    if hi is None and p[p.degree()] <= 0:
        raise ValueError("Polynomial is not positive at the infinite endpoint")
    chain = [p]
    if p.derivative():
        chain.append(p.derivative())
        while True:
            remainder = -(chain[-2] % chain[-1])
            if not remainder:
                break
            # Positive normalization controls rational coefficient growth.
            remainder = remainder/abs(remainder[remainder.degree()])
            chain.append(remainder)
    at_lo = [_sign(f(lo)) for f in chain]
    at_hi = [_sign(f[f.degree()] if hi is None else f(hi)) for f in chain]
    roots = _variations(at_lo)-_variations(at_hi)
    if roots:
        raise ValueError(f"Polynomial has {roots} root(s) in the requested interval")
    return {"coefficients_ascending": [str(v) for v in co],
            "lower": str(lower), "upper": "+infinity" if upper is None else str(upper),
            "sturm_degrees": [f.degree() for f in chain],
            "signs_lower": at_lo, "signs_upper": at_hi,
            "variations_lower": _variations(at_lo), "variations_upper": _variations(at_hi),
            "roots": roots}


def even_polynomial(expr, t):
    polynomial = sp.Poly(expr, t)
    if any(power[0] % 2 for power, value in polynomial.terms() if value):
        raise ValueError("Expected an even polynomial in cosmic time")
    return [Fraction(str(polynomial.nth(2*i))) for i in range(polynomial.degree()//2+1)]


def _strip_zero(coefficients):
    if not any(coefficients):
        raise ValueError("The zero polynomial is not strictly positive")
    order = 0
    while coefficients[order] == 0:
        order += 1
    return order, coefficients[order:]


def even_rational_positive(expr, t, *, punctured=False, upper=None):
    if sp.cancel(expr) == 0:
        raise ValueError("The zero expression is not strictly positive")
    numerator, denominator = sp.fraction(sp.cancel(expr))
    nc, dc = even_polynomial(numerator, t), even_polynomial(denominator, t)
    if dc[-1] < 0:
        nc, dc = [-x for x in nc], [-x for x in dc]
    no, nc = _strip_zero(nc)
    do, dc = _strip_zero(dc)
    if not punctured and (no != 0 or do != 0):
        raise ValueError("A zero/pole at t=0 is not allowed in the regular chart")
    return {"expression": str(sp.factor(expr)), "domain": "t != 0" if punctured else "all t",
            "upper_t_squared": None if upper is None else str(upper),
            "numerator_zero_order_in_t_squared": no, "denominator_zero_order_in_t_squared": do,
            "numerator": sturm_positive(nc, upper=upper),
            "denominator": sturm_positive(dc, upper=upper)}


def denominator_regular(expr, t):
    denominator = sp.fraction(sp.cancel(expr))[1]
    dc = even_polynomial(denominator, t)
    if dc[-1] < 0:
        dc = [-x for x in dc]
    return sturm_positive(dc)


def bernstein_bounds(polynomial, variables):
    """Exact tensor-product Bernstein coefficient bounds on the unit box.

    This conversion uses fractions/integers; SymPy supplies only the input
    power coefficients. The convex-hull bound is recorded with all values.
    """
    poly = sp.Poly(polynomial, *variables)
    degrees = tuple(max(0, poly.degree(var)) for var in variables)
    powers = {index: Fraction(str(value)) for index, value in poly.terms()}
    if len(variables) != 2:
        raise ValueError("This verifier accepts two variables")
    n, m = degrees
    coefficients = []
    for i in range(n+1):
        for j in range(m+1):
            value = sum(v*Fraction(comb(i, k), comb(n, k))*Fraction(comb(j, l), comb(m, l))
                        for (k, l), v in powers.items() if k <= i and l <= j)
            coefficients.append(value)
    return {"degrees": list(degrees), "coefficients": [str(v) for v in coefficients],
            "lower": str(min(coefficients)), "upper": str(max(coefficients))}


def rational_tail_bound(expr, t, X, *, required_order=1):
    """Uniform |expr| <= C/(1+t²)^order on X in [9/10,11/10].

    Compactify with u=1/(1+t²), map X=9/10+r/5, and factor the exact
    vanishing order at u=0. Bernstein bounds certify the remaining quotient
    for every (u,r) in [0,1]², so this also supplies an explicit tail bound.
    """
    u, r, xx = sp.symbols("u r xx", real=True)
    num, den = sp.fraction(sp.cancel(expr))
    def to_x(e):
        poly = sp.Poly(e, t)
        if any(index[0] % 2 for index, value in poly.terms() if value):
            raise ValueError("Tail expression must be even in t")
        return sum(value*xx**(index[0]//2) for index, value in poly.terms())
    compact = sp.cancel((to_x(num)/to_x(den)).subs({xx: (1-u)/u, X: sp.Rational(9, 10)+r/5}))
    if compact == 0:
        return {"expression": "0", "order": "+infinity", "bound": "0"}
    num, den = sp.fraction(compact)
    norder = min(index[0] for index, value in sp.Poly(num, u, r).terms() if value)
    dorder = min(index[0] for index, value in sp.Poly(den, u, r).terms() if value)
    order = norder-dorder
    if order < required_order:
        raise ValueError(f"Insufficient canonical tail decay: order={order}")
    num, den = sp.cancel(num/u**norder), sp.cancel(den/u**dorder)
    nb, db = bernstein_bounds(num, (u, r)), bernstein_bounds(den, (u, r))
    lower, upper = Fraction(db["lower"]), Fraction(db["upper"])
    if lower > 0:
        gap = lower
    elif upper < 0:
        gap = -upper
    else:
        raise ValueError("Bernstein denominator enclosure crosses zero")
    bound = max(abs(Fraction(nb["lower"])), abs(Fraction(nb["upper"])))/gap
    return {"expression": str(sp.factor(expr)), "order": order, "bound": str(bound),
            "X_interval": ["9/10", "11/10"], "u": "1/(1+t^2)",
            "numerator_Bernstein": nb, "denominator_Bernstein": db}

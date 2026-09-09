"""Outward Arb checks for rational functions of pi squared, no float decisions."""

import sympy as sp
from flint import arb, ctx, fmpq

from .partition import Z

PRECISION = 192


def rational(value):
    value = sp.Rational(value)
    return arb(fmpq(int(value.p), int(value.q)))


def polynomial_value(expression, z):
    result = arb(0)
    for coefficient in sp.Poly(expression, Z).all_coeffs():
        result = result*z+rational(coefficient)
    return result


def evaluate(expression):
    """Caller controls precision, normally using ctx.workprec(PRECISION)."""
    numerator, denominator = sp.fraction(sp.cancel(expression))
    z = arb.pi()**2
    divisor = polynomial_value(denominator, z)
    if divisor.contains(0):
        raise ValueError("Interval denominator contains zero")
    return polynomial_value(numerator, z)/divisor


def enclosure(expression, lower, upper):
    lower, upper = sp.Rational(lower), sp.Rational(upper)
    if not lower < upper:
        raise ValueError("Expected strictly ordered rational enclosure endpoints")
    with ctx.workprec(PRECISION):
        value = evaluate(expression)
        if not value > rational(lower) or not value < rational(upper):
            raise ValueError("Claimed rational enclosure is not validated by Arb")
    return {"lower": str(lower), "upper": str(upper), "strict": True}


def positive(expression):
    with ctx.workprec(PRECISION):
        if not evaluate(expression) > 0:
            raise ValueError("Expression is not certified strictly positive")
    return True

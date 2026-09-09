"""Small outward Arb evaluator restricted to the report's exact constants."""

import sympy as sp
from flint import arb, ctx, fmpq

PRECISION = 192


def evaluate(expression):
    expression = sp.sympify(expression)
    if expression.is_Rational:
        return arb(fmpq(int(expression.p), int(expression.q)))
    if expression == sp.pi:
        return arb.pi()
    if expression == sp.log(2):
        return arb(2).log()
    if expression.is_Add:
        return sum((evaluate(item) for item in expression.args), arb(0))
    if expression.is_Mul:
        value = arb(1)
        for item in expression.args:
            value *= evaluate(item)
        return value
    if expression.is_Pow and expression.exp.is_Integer:
        base = evaluate(expression.base)
        if expression.exp < 0 and base.contains(0):
            raise ValueError("Interval denominator contains zero")
        return base**int(expression.exp)
    raise ValueError("Only rational arithmetic, pi and log(2) are admitted")


def enclosure(expression, lower, upper):
    lower, upper = sp.Rational(lower), sp.Rational(upper)
    if not lower < upper:
        raise ValueError("Strictly ordered rational endpoints required")
    with ctx.workprec(PRECISION):
        value = evaluate(expression)
        if not value > evaluate(lower) or not value < evaluate(upper):
            raise ValueError("Claimed enclosure not certified by Arb")
    return {"lower": str(lower), "upper": str(upper), "strict": True}


def positive(expression):
    with ctx.workprec(PRECISION):
        if not evaluate(expression) > 0:
            raise ValueError("Strict positivity not certified")
    return True

"""Exact H2 localization with a geometrically shrinking partition."""

from functools import cache

import sympy as sp

X = sp.Symbol("x", real=True)
Z = sp.Symbol("z", nonnegative=True)  # z = pi**2, not an independent physical input
R = sp.Rational(3, 4)
A = 1-R
P = 3*X**2-2*X**3


def integrate_poly(expression, variable=X):
    """Exact polynomial antiderivative on [0, 1]."""
    poly = sp.Poly(sp.expand(expression), variable)
    return sp.expand(sum(coefficient/sp.Integer(power[0]+1)
                         for power, coefficient in poly.terms()))


def local_bilinear(left, right):
    """Integral of the rotation-invariant pair of localized second derivatives.

    With theta=(pi/2)P, this is integral ((f*cos(theta))'' *
    (g*cos(theta))'' + (f*sin(theta))'' * (g*sin(theta))'').
    Physical cell length h contributes a separate h**(-3).
    """
    first = sp.diff(P, X)/2
    second = sp.diff(P, X, 2)/2
    return integrate_poly(
        sp.diff(left, X, 2)*sp.diff(right, X, 2)
        + Z*(-first**2*(left*sp.diff(right, X, 2)+sp.diff(left, X, 2)*right)
             +(2*first*sp.diff(left, X)+second*left)
             *(2*first*sp.diff(right, X)+second*right))
        + Z**2*first**4*left*right)


@cache
def monomial_tail_pair(left_power, right_power):
    """Infinite geometric tail; both powers must vanish quadratically at t=tau."""
    if not isinstance(left_power, int) or not isinstance(right_power, int):
        raise TypeError("Tail powers must be integers")
    if min(left_power, right_power) < 2:
        raise ValueError("Tail powers below two violate the frozen H2 endpoint domain")
    exponent = left_power+right_power-3
    return sp.expand(local_bilinear((1-A*X)**left_power, (1-A*X)**right_power)
                     / ((A*R)**3*(1-R**exponent)))


def tail_bilinear(left, right):
    """Exact sum over all tail cells, not a finite cutoff approximation."""
    left_terms = sp.Poly(left, X).terms()
    right_terms = sp.Poly(right, X).terms()
    result = 0
    for (k,), coefficient_left in left_terms:
        for (ell,), coefficient_right in right_terms:
            if coefficient_left == 0 or coefficient_right == 0:
                continue
            result += coefficient_left*coefficient_right*monomial_tail_pair(k, ell)
    return sp.expand(result)


def localized_norm(tail):
    return sp.expand(local_bilinear(P, P)/A**3+tail_bilinear(tail, tail))


def tail_remainder(tail, first_omitted_cell):
    """Exact localized energy on cells j >= first_omitted_cell, with j >= 1."""
    if not isinstance(first_omitted_cell, int) or first_omitted_cell < 1:
        raise ValueError("First omitted tail cell must be a positive integer")
    result = 0
    for (k,), ak in sp.Poly(tail, X).terms():
        for (ell,), al in sp.Poly(tail, X).terms():
            result += (ak*al*monomial_tail_pair(k, ell)
                       * R**((k+ell-3)*(first_omitted_cell-1)))
    return sp.expand(result)


def coverage_ratio(ratio=R, t0_over_tau=1):
    """Support length / T at its midpoint for every interior partition member."""
    ratio, t0_over_tau = sp.sympify(ratio), sp.sympify(t0_over_tau)
    if not (0 < ratio < 1) or not t0_over_tau > 0:
        raise ValueError("Require 0 < ratio < 1 and positive T0/tau")
    return sp.cancel(2*(1-ratio**2)/(t0_over_tau*(1+ratio**2)))


def validate_coverage(ratio=R, t0_over_tau=1):
    value = coverage_ratio(ratio, t0_over_tau)
    if not value < 1:
        raise ValueError("Localized supports do not lie strictly inside allowed QEI windows")
    return value


def identities():
    f, fp, fpp, c, s, theta_p, theta_pp = sp.symbols("f fp fpp c s tp tpp")
    radial = fpp-theta_p**2*f
    tangential = 2*theta_p*fp+theta_pp*f
    direct_c = c*fpp-2*s*theta_p*fp-(c*theta_p**2+s*theta_pp)*f
    direct_s = s*fpp+2*c*theta_p*fp+(c*theta_pp-s*theta_p**2)*f
    rotation = sp.expand(direct_c**2+direct_s**2-(c*c+s*s)*(radial**2+tangential**2))
    ratio, exponent, count = sp.symbols("r k N", positive=True)
    geometric = sp.cancel((1-ratio**(exponent*count))/(1-ratio**exponent)
                          +ratio**(exponent*count)/(1-ratio**exponent)
                          -1/(1-ratio**exponent))
    return {"rotation_sum_of_squares": rotation, "geometric_tail_reconstruction": geometric,
            "partition_angle_start": P.subs(X, 0), "partition_angle_end": P.subs(X, 1)-1,
            "partition_first_jet_start": sp.diff(P, X).subs(X, 0),
            "partition_first_jet_end": sp.diff(P, X).subs(X, 1),
            "beta_norm": integrate_poly(P**2)-sp.Rational(13, 35),
            "beta_first_derivative_norm": integrate_poly(sp.diff(P, X)**2)-sp.Rational(6, 5),
            "beta_second_derivative_norm": integrate_poly(sp.diff(P, X, 2)**2)-12}

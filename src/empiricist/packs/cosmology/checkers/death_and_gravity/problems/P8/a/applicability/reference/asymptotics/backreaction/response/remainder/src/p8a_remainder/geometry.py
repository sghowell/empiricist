"""Exact finite preparation and rational fractional-power derivative majorants.

All jets are derivatives in the actual conformal clock, NOT background y.
Ring keys are (delta power, f power, inverse-y power, sorted p-jet indices).
The exact ring is finite and every enclosure is rational on 0<=delta<=1/2.
"""

from fractions import Fraction as F
from functools import cache
from math import ceil, comb

import sympy as sp

from .mode_bounds import exact_nonnegative

Y = sp.Symbol("y", positive=True)
DELTA = sp.Symbol("delta", nonnegative=True)


def add_term(terms, key, coefficient):
    if coefficient:
        terms[key] = terms.get(key, F(0))+coefficient
        if terms[key] == 0:
            del terms[key]


def conformal_derivative(terms):
    """eta_star*d_eta = f^(1/4)*d_y, with f=1-delta*p."""
    result = {}
    for (power_delta, power_f, power_y, jets), c in terms.items():
        shifted_f = power_f+F(1, 4)
        if power_y:
            add_term(result, (power_delta, shifted_f, power_y+1, jets), -power_y*c)
        for index in set(jets):
            changed = list(jets)
            changed.remove(index)
            changed.append(index+1)
            add_term(result, (power_delta, shifted_f, power_y, tuple(sorted(changed))), c*jets.count(index))
        if power_f:
            add_term(result, (power_delta+1, shifted_f-1, power_y, tuple(sorted((*jets, 1)))), -power_f*c)
    return result


@cache
def potential_jets():
    first = {(1, F(-1, 2), 0, (2,)): F(1, 4),
             (1, F(-1, 2), 1, (1,)): F(3, 4),
             (2, F(-3, 2), 0, (1, 1)): F(1, 8)}
    jets = [first]
    for _ in range(5):
        jets.append(conformal_derivative(jets[-1]))
    return jets


def to_symbolic(terms):
    p = sp.Function("p")(Y)
    f = 1-DELTA*p
    result = sp.Integer(0)
    for (nd, nf, ny, jets), c in terms.items():
        value = sp.Rational(c)*DELTA**nd*f**sp.Rational(nf)/Y**ny
        for j in jets:
            value *= sp.diff(p, Y, j)
        result += value
    return result


def smooth_switch_bounds(order=7):
    """New independent extension of A.6's proved recurrence; no A.6 edit."""
    if not isinstance(order, int) or isinstance(order, bool) or not 0 <= order <= 7:
        raise ValueError("This checkpoint needs/certifies switch jets only through order 7")
    y = sp.Symbol("z")
    polynomial = sp.Integer(1)
    r, switch, polynomials = [sp.Rational(3, 8)], [sp.Integer(1)], [polynomial]
    for n in range(1, order+1):
        polynomial = sp.expand(y**2*(polynomial-sp.diff(polynomial, y)))
        polynomials.append(polynomial)
        r.append(sum(abs(c)*(sp.Rational(3, 8)*power[0])**power[0]
                     for power, c in sp.Poly(polynomial, y).terms()))
        switch.append(4*(r[n]+sum(comb(n, j)*2*r[j]*switch[n-j] for j in range(1, n+1))))
    return {"r": r, "switch": switch, "polynomials": polynomials, "variable": y}


@cache
def p_jet_bounds():
    switch = smooth_switch_bounds()["switch"]
    return [F(sum(comb(n, j)*sp.rf(4, n-j)*switch[j] for j in range(n+1))) for n in range(8)]


def majorize(terms, p_bounds=None):
    """|eta_star^(j+2) U^(j)| <= delta*result; full sign is retained upstream."""
    p_bounds = p_jet_bounds() if p_bounds is None else p_bounds
    total = F(0)
    for (nd, nf, ny, jets), c in terms.items():
        if nd < 1 or ny < 0 or max(jets, default=0) >= len(p_bounds):
            raise ValueError("Unsupported term in the proved positive jet majorant")
        value = abs(c)*F(1, 2)**(nd-1)*2**max(0, ceil(-nf))
        for j in jets:
            value *= p_bounds[j]
        total += value
    return total


@cache
def calibration():
    b = [majorize(terms) for terms in potential_jets()]
    p = p_jet_bounds()
    cap = min(F(1, 2), 1/(9*b[0]), 1/(24*b[0]+12*b[1]), 2/p[1])
    return {"potential_bounds": b, "p_bounds": p, "delta_bar": cap,
            "IR_exponent_at_cap": F(9, 2)*cap*b[0],
            "UV_exponent_at_cap": cap*(12*b[0]+6*b[1]),
            "Hubble_extra_at_cap": cap*p[1]/2,
            "jet_term_counts": [len(terms) for terms in potential_jets()]}


def check_amplitude(delta):
    """Reject amplitudes outside the derived finite-family calibration domain."""
    delta = exact_nonnegative(delta)
    if (sp.Rational(calibration()["delta_bar"])-delta).is_nonnegative is not True:
        raise ValueError("Amplitude outside the proved finite-family calibration domain")
    return delta


def identities():
    p = sp.Function("p")(Y)
    f = 1-DELTA*p
    scale = Y*f**sp.Rational(1, 4)  # strip A*eta_star
    derivative = lambda value: f**sp.Rational(1, 4)*sp.diff(value, Y)
    exact_u = -derivative(derivative(scale))/scale
    h = derivative(scale)/scale
    return {"exact_finite_potential": sp.simplify(exact_u-to_symbolic(potential_jets()[0])),
            "exact_conformal_Hubble": sp.simplify(h-f**sp.Rational(1, 4)/Y
                                                      + DELTA*sp.diff(p, Y)*f**sp.Rational(-3, 4)/4),
            "exact_clock_derivative_inverse": f**sp.Rational(1, 4)*f**sp.Rational(-1, 4)-1,
            "proper_time_label": sp.diff(Y**2/2, Y)-Y,
            "wrong_frozen_clock_potential": sp.simplify(-sp.diff(scale, Y, 2)/scale-exact_u)}


def report():
    result = calibration()
    return {"p_derivative_bounds_through_7": list(map(str, result["p_bounds"])),
            "U_derivative_bounds_through_5_per_delta": list(map(str, result["potential_bounds"])),
            "delta_bar": str(result["delta_bar"]),
            "IR_exponent_at_delta_bar": str(result["IR_exponent_at_cap"]),
            "UV_exponent_at_delta_bar": str(result["UV_exponent_at_cap"]),
            "conformal_Hubble_extra_at_delta_bar": str(result["Hubble_extra_at_cap"]),
            "fractional_jet_ring_term_counts": result["jet_term_counts"],
            "clock": "eta_actual/eta_star=1+integral_1^y (1-delta*p(s))^(-1/4) ds",
            "finite_amplitude": "delta=16*epsilon*d/(A^2*eta_star^4); 0<=delta<=delta_bar",
            "calibration_geometry_bounds": "history<=3eta_star; a^-4<=1/(8A^4eta_star^4), |a'/a|<=2/eta_star on y in[2,3]"}


def ring_records():
    return [[{"coefficient": str(c), "delta_power": nd, "f_power": str(nf),
              "inverse_y_power": ny, "p_jets": list(jets)}
             for (nd, nf, ny, jets), c in sorted(terms.items())] for terms in potential_jets()]

"""Exact derivative bounds for a specified C-infinity preparation.

No sampled values stand in for derivative suprema. The inequalities and
denominator proof used by these rational recurrences are in notes/proof.md.
"""

from math import comb, factorial

import sympy as sp


def exact_nonnegative(value, *, positive=False):
    value = sp.sympify(value)
    if value.has(sp.Float) or value.is_finite is not True:
        raise ValueError("Need exact finite parameters, not rounded floats or infinities")
    if (value.is_positive if positive else value.is_nonnegative) is not True:
        raise ValueError("Need a proved positive/nonnegative parameter")
    return value


def switch_derivative_bounds(order=5):
    if not isinstance(order, int) or isinstance(order, bool) or not 0 <= order <= 5:
        raise ValueError("This checkpoint certifies switch derivatives through order 5")
    y = sp.Symbol("y")
    polynomial = sp.Integer(1)
    polynomials, elementary, switch = [polynomial], [sp.Rational(3, 8)], [sp.Integer(1)]
    for n in range(1, order+1):
        polynomial = sp.expand(y**2*(polynomial-sp.diff(polynomial, y)))
        polynomials.append(polynomial)
        rn = sum(abs(c)*(sp.Rational(3, 8)*power[0])**power[0]
                 for power, c in sp.Poly(polynomial, y).terms())
        elementary.append(rn)
        switch.append(4*(rn+sum(comb(n, j)*2*elementary[j]*switch[n-j]
                                for j in range(1, n+1))))
    return {"variable": y, "polynomials": polynomials, "r_derivatives": elementary,
            "switch_derivatives": switch}


def normalized_norms():
    """On history [eta_*,3eta_*], Q_j <= d*q_j/(A² eta_*^(4+j))."""
    switches = switch_derivative_bounds()["switch_derivatives"]
    q = [4*sum(comb(n, j)*sp.rf(4, n-j)*switches[j] for j in range(n+1))
         for n in range(6)]
    v = [q[n+2]+3*sum(comb(n, j)*factorial(j)*q[n-j+1] for j in range(n+1))
         for n in range(4)]
    return {"Q": q, "V": v}


def kernel_bounds(v_norms, span, eta_minus, local_log_abs):
    """Conditional norm inequality; normalized_example supplies proved inputs.

    v_norms[j] bounds |V^(j)| on the entire past-to-observation history.
    local_log_abs bounds |log(sqrt(2)*A*eta*span/lambda)+5/6| on observations.
    This does not estimate a finite-epsilon mode or RSET remainder.
    """
    if len(v_norms) != 4:
        raise ValueError("Need V through its third derivative")
    v0, v1, v2, v3 = map(exact_nonnegative, v_norms)
    span = exact_nonnegative(span, positive=True)
    eta_minus = exact_nonnegative(eta_minus, positive=True)
    c = exact_nonnegative(local_log_abs)
    return [span*v1+c*v0,
            span*v2+c*v1+v0/eta_minus,
            span*v3+c*v2+2*v1/eta_minus+v0/eta_minus**2]


def response_bounds(v_norms, q_prime_norm, k_norms, eta_minus, *, a=1, hbar=1, gamma_abs=0):
    """First derivative at epsilon=0, physical fixed-proper-time comparison."""
    if len(v_norms) != 4 or len(k_norms) != 3:
        raise ValueError("Need four V norms and three retarded K norms")
    v, vp, vpp, _ = map(exact_nonnegative, v_norms)
    k, kp, kpp = map(exact_nonnegative, k_norms)
    qp = exact_nonnegative(q_prime_norm)
    x, a = exact_nonnegative(eta_minus, positive=True), exact_nonnegative(a, positive=True)
    hbar, gamma_abs = exact_nonnegative(hbar), exact_nonnegative(gamma_abs)
    prefactor = hbar/(sp.pi**2*a**4)
    rho = prefactor*((kp/x**5+k/x**6)/16+(3*vp/x**5+3*v/x**6+qp/x**7)/240)
    p = prefactor*((kpp/x**4+3*kp/x**5+3*k/x**6)/48
                   + (3*vpp/x**4+9*vp/x**5+10*v/x**6+5*qp/x**7)/720)
    e = prefactor*((kpp/x**4+4*kp/x**5+4*k/x**6)/32
                   + (3*vpp/x**4+12*vp/x**5+13*v/x**6+6*qp/x**7)/480)
    rho += 36*gamma_abs*(vp/x**5+v/x**6)/a**4
    p += 12*gamma_abs*(vpp/x**4+3*vp/x**5+3*v/x**6)/a**4
    e += 18*gamma_abs*(vpp/x**4+4*vp/x**5+4*v/x**6)/a**4
    return {"density": rho, "pressure": p, "EED": e}


def normalized_example():
    norms = normalized_norms()
    k = kernel_bounds(norms["V"], 2, 2, 2)
    values = response_bounds(norms["V"], norms["Q"][1], k, 2)
    return {"switch": switch_derivative_bounds(), "Q_norm_constants": norms["Q"],
            "V_norm_constants": norms["V"], "K_norm_constants": k,
            "response_constants_in_hbar_d_over_pi2_A6_eta_star12_units": {
                name: sp.simplify(sp.pi**2*value) for name, value in values.items()}}


def elementary_checks():
    partial = sum(sp.Rational(1, factorial(n)) for n in range(5))
    upper = partial+sp.Rational(1, factorial(5))/(1-sp.Rational(1, 6))
    exp_lower = sum(sp.Rational(7, 6)**n/factorial(n) for n in range(5))
    y = sp.Symbol("y", positive=True)
    g = -y+1/y+2*sp.log(y)
    return {"e_lower_margin_over_8_over_3": partial-sp.Rational(8, 3),
            "e_upper_margin_below_11_over_4": sp.Rational(11, 4)-upper,
            "e_squared_upper_below_8": 8-sp.Rational(11, 4)**2,
            "switch_denominator_monotonic_identity": sp.factor(sp.diff(g, y)+(y-1)**2/y**2),
            "exp_seven_sixths_lower_above_3": exp_lower-3,
            "log_kernel_L1_unit_integral": sp.Integer(1)}

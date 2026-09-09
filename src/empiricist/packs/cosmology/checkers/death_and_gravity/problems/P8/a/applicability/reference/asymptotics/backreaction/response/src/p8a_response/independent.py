"""Independent Fraction-only replay of the genuine smooth-preparation bounds."""

from fractions import Fraction as F
from math import comb, factorial


def next_polynomial(polynomial):
    result = [F(0)]*(len(polynomial)+2)
    for n, coefficient in enumerate(polynomial):
        result[n+2] += coefficient
        if n:
            result[n+1] -= n*coefficient
    return result


def replay():
    p = [F(1)]
    polynomials, r, switch = [p], [F(3, 8)], [F(1)]
    for n in range(1, 6):
        p = next_polynomial(p)
        polynomials.append(p)
        r.append(sum((abs(c)*(F(3*j, 8))**j for j, c in enumerate(p) if c), F(0)))
        switch.append(4*(r[n]+sum((comb(n, j)*2*r[j]*switch[n-j]
                                  for j in range(1, n+1)), F(0))))
    q = [4*sum((comb(n, j)*F(factorial(n-j+3), 6)*switch[j]
                for j in range(n+1)), F(0)) for n in range(6)]
    v = [q[n+2]+3*sum((comb(n, j)*factorial(j)*q[n-j+1]
                      for j in range(n+1)), F(0)) for n in range(4)]
    k0, k1, k2 = 2*v[1]+2*v[0], 2*v[2]+2*v[1]+v[0]/2, 2*v[3]+2*v[2]+v[1]+v[0]/4
    rho = (k1/32+k0/64)/16+(3*v[1]/32+3*v[0]/64+q[1]/128)/240
    pressure = (k2/16+3*k1/32+3*k0/64)/48+(3*v[2]/16+9*v[1]/32+10*v[0]/64+5*q[1]/128)/720
    eed = (k2/16+4*k1/32+4*k0/64)/32+(3*v[2]/16+12*v[1]/32+13*v[0]/64+6*q[1]/128)/480
    partial = sum((F(1, factorial(j)) for j in range(5)), F(0))
    upper = partial+F(1, factorial(5))/(1-F(1, 6))
    exp_lower = sum((F(7, 6)**j/factorial(j) for j in range(5)), F(0))
    if not F(8, 3) < partial < upper < F(11, 4) or F(11, 4)**2 >= 8 or exp_lower <= 3:
        raise ValueError("Elementary exponential rational enclosures failed")
    return {"switch_polynomial_coefficients": [[str(c) for c in poly] for poly in polynomials],
            "r_derivative_bounds": list(map(str, r)), "switch_derivative_bounds": list(map(str, switch)),
            "Q_norm_constants": list(map(str, q)), "V_norm_constants": list(map(str, v)),
            "K_norm_constants": list(map(str, (k0, k1, k2))),
            "response_constants": {"density": str(rho), "pressure": str(pressure), "EED": str(eed)},
            "elementary_enclosures": {"e_partial_sum_lower": str(partial), "e_geometric_tail_upper": str(upper),
                                        "exp_seven_sixths_partial_lower": str(exp_lower)},
            "response_units": "hbar*d/(pi^2*A^6*eta_star^12)",
            "amplitude_derivative_order": 1,
            "finite_epsilon_remainder_bound": False}

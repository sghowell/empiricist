"""Fraction-only replay and independent local Taylor-series jet audit.

No SymPy imports. The ring supplied by the main derivation is evaluated
against a separately computed truncated-series solution of its clock
operator; this is an algebraic control, not an alternative physical state.
"""

from fractions import Fraction as F
from math import ceil, comb, factorial


def polynomial_next(values):
    result = [F(0)]*(len(values)+2)
    for n, c in enumerate(values):
        result[n+2] += c
        if n:
            result[n+1] -= n*c
    return result


def p_bounds():
    p, r, switch = [F(1)], [F(3, 8)], [F(1)]
    for n in range(1, 8):
        p = polynomial_next(p)
        r.append(sum((abs(c)*F(3*j, 8)**j for j, c in enumerate(p) if c), F(0)))
        switch.append(4*(r[n]+sum((comb(n, j)*2*r[j]*switch[n-j]
                                  for j in range(1, n+1)), F(0))))
    return [sum((comb(n, j)*F(factorial(n-j+3), 6)*switch[j]
                 for j in range(n+1)), F(0)) for n in range(8)]


def add(*series):
    result = [F(0)]*max(map(len, series))
    for value in series:
        for n, c in enumerate(value):
            result[n] += c
    return result


def scale(series, c):
    return [c*x for x in series]


def multiply(left, right, order):
    result = [F(0)]*(order+1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            if i+j <= order:
                result[i+j] += a*b
    return result


def derivative(series):
    return [n*c for n, c in enumerate(series) if n]


def fractional_power(series, exponent, leading_power, order):
    """Binomial expansion with separately supplied exact leading power."""
    unit = scale(series, 1/series[0])
    unit[0] -= 1
    result, term, coefficient = [F(1)], [F(1)], F(1)
    for n in range(1, order+1):
        term = multiply(term, unit, order)
        coefficient *= (exponent-n+1)/n
        result = add(result, scale(term, coefficient))
    return scale(result[:order+1], leading_power)


def taylor_jet_audit(ring):
    # f(0)=(7/8)^4 ensures that every quarter power is exactly rational.
    root, y0 = F(7, 8), F(3, 2)
    delta = 1-root**4
    jets = [F(1)]+[F((-1)**n, n+1) for n in range(1, 8)]
    p = [jets[n]/factorial(n) for n in range(8)]
    f = scale(p, -delta)
    f[0] += 1
    inv_y = [(-1)**n/y0**(n+1) for n in range(8)]
    f_minus_half = fractional_power(f, F(-1, 2), root**-2, 5)
    f_minus_three_half = fractional_power(f, F(-3, 2), root**-6, 5)
    f_quarter = fractional_power(f, F(1, 4), root, 5)
    pp = derivative(p)
    source = add(derivative(pp), scale(multiply(pp, inv_y, 5), 3))
    potential = add(scale(multiply(f_minus_half, source, 5), delta/4),
                    scale(multiply(f_minus_three_half, multiply(pp, pp, 5), 5), delta**2/8))
    evaluated = []
    for j in range(6):
        direct = potential[0]
        assembled = F(0)
        for row in ring[j]:
            nf = F(row["f_power"])
            if (4*nf).denominator != 1:
                raise ValueError("Quarter-power algebra audit requires quarter exponents")
            value = F(row["coefficient"])*delta**row["delta_power"]*root**int(4*nf)/y0**row["inverse_y_power"]
            for index in row["p_jets"]:
                value *= jets[index]
            assembled += value
        if assembled != direct:
            raise ValueError("Exact fractional jet ring differs from independent Taylor clock calculation")
        evaluated.append(str(direct))
        if j < 5:
            potential = multiply(f_quarter, derivative(potential), 4-j)
    return {"eta_star_and_A": "1 in this algebra-only control", "y0": str(y0),
            "f_quarter_at_y0": str(root), "delta": str(delta),
            "jet_values_from_independent_Taylor_series": evaluated,
            "all_six_exact_jet_comparisons_passed": True,
            "control_is_the_physical_smooth_cutoff": False}


def replay(ring):
    p = p_bounds()
    b = []
    for terms in ring:
        bound = F(0)
        for row in terms:
            value = abs(F(row["coefficient"]))*F(1, 2)**(row["delta_power"]-1)
            value *= 2**max(0, ceil(-F(row["f_power"])))
            for j in row["p_jets"]:
                value *= p[j]
            bound += value
        b.append(bound)
    cap = min(F(1, 2), 1/(9*b[0]), 1/(24*b[0]+12*b[1]), 2/p[1])
    # T=3, K=1, exp caps=2. Divide by delta² before evaluating at cap.
    b0, b1, b2, b3, _, b5 = b
    a0, a1, a2 = 9*b0, 6*b0, 11*b0
    e0, e1 = F(27, 4)*b0**2, 9*b0**2
    e2 = e0+9*b0**2
    low = [e0+a0*a0/2,
           e0+e1+a0*a1,
           e0+2*e1+e2+a1*a1+a0*a2]
    residual = (10*b0*b3+20*b1*b2+30*cap*b0*b0*b1)/8+F(3, 2)*b0*b5+F(3, 4)*b1*b5
    c = 6*residual
    high = [F(3, 16)*b0*b0+c/4,
            F(3, 8)*b0*b1+c/3,
            F(3, 8)*(b1*b1+b0*b2)+c/2]
    m0, m1, m2 = [low[j]+high[j] for j in range(3)]
    stress = {"density": (2*m1+(4+cap*b0+3*cap*b1)*m0)/64,
              "pressure": (m2+6*m1+(12+cap*b0+3*cap*b1)*m0)/192,
              "EED": (m2+8*m1+(16+6*cap*b1)*m0)/128}
    amplitude = F(1, 10**12)
    reference = {"density": 960, "pressure": 576, "EED": 320}
    ratios = {name: reference[name]*3**8*coefficient*amplitude**2 for name, coefficient in stress.items()}
    if not amplitude <= cap or any(value >= F(1, 100) for value in ratios.values()):
        raise ValueError("Concrete finite-amplitude one-percent reference-scale control failed")
    return {"p_jet_bounds": list(map(str, p)), "U_jet_bounds_per_delta": list(map(str, b)),
            "delta_bar": str(cap), "IR_remainder_constants": list(map(str, low)),
            "UV_remainder_constants": list(map(str, high)),
            "integrated_mode_remainder_constants": list(map(str, (m0, m1, m2))),
            "stress_error_constants": {name: str(value) for name, value in stress.items()},
            "actual_finite_amplitude_accuracy_example": {
                "delta": str(amplitude), "uniform_reference_scale_error_ratios": {name: str(value) for name, value in ratios.items()},
                "all_three_ratios_strictly_below_one_percent": True,
                "denominator": "positive pinned A.3 reference components at the same proper time, not actual or Born stress",
                "metric_is_claimed_to_solve_SEE": False},
            "independent_fractional_jet_audit": taylor_jet_audit(ring)}

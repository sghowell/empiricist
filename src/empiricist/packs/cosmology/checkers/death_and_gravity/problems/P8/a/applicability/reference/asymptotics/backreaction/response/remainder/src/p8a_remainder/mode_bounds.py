"""All-frequency, quadratic, C2 remainder estimates with proved exponential caps.

F_k=2k|v_k|², F1[U] is its exact first Born term, and D=F-1-F1.
The bounds control integral k*|partial_eta^j D| dk for j=0,1,2.
No assumption that k²+U stays positive is needed.
"""

import sympy as sp


def exact_nonnegative(value, *, positive=False):
    value = sp.sympify(value)
    if value.has(sp.Float) or value.is_finite is not True:
        raise ValueError("Need exact finite parameters, not rounded floats or infinities")
    if (value.is_positive if positive else value.is_nonnegative) is not True:
        raise ValueError("Need a proved positive/nonnegative parameter")
    return value


def polynomial_bounds(b, duration, split, low_cap, high_cap):
    """Algebraic theorem with already proved exponential upper bounds.

    Internal assembly only: public bounds() checks the exponential caps.
    b[j] bounds U through derivative five; b[4] is retained as jet data even
    though this particular estimate needs only b0,b1,b2,b3,b5.
    """
    b0, b1, b2, b3, _, b5 = b
    t, k, m = duration, split, low_cap
    a0, a1 = b0*t**2*m/2, b0*t*m
    a2 = k**2*a0+b0*m
    e0, e1 = b0**2*t**4*m/24, b0**2*t**3*m/6
    e2 = k**2*e0+b0*a0
    low = [2*e0+a0**2,
           2*(k*e0+e1+a0*a1),
           2*(k**2*e0+2*k*e1+e2+a1**2+a0*a2)]
    r_nonlinear = (10*b0*b3+20*b1*b2+30*b0**2*b1)/8
    residual = r_nonlinear+t*b0*b5/(2*k)+t*b1*b5/(4*k**2)
    c = t*residual*high_cap
    adiabatic = [3*b0**2/8, 3*b0*b1/4, 3*(b1**2+b0*b2)/4]
    high = [adiabatic[j]/(2*k**2)+c/((4-j)*k**(4-j)) for j in range(3)]
    low_integrals = [k**2*value/2 for value in low]
    return {"IR_pointwise_D_derivatives": low,
            "IR_integral_bounds": low_integrals, "UV_integral_bounds": high,
            "integrated_remainder_derivatives": [sp.expand(low_integrals[j]+high[j]) for j in range(3)],
            "UV_quadratic_residual_coefficient": residual,
            "UV_Gronwall_coefficient": c}


def bounds(b, duration, split, *, rational_caps=False):
    """Uniform bounds on actual all-frequency nonlinear mode remainder.

    For rational_caps=True both exact exponent arguments must be <=1/2;
    then exp(1/2)<2 is a proved rational enclosure, not a floating estimate.
    Otherwise the displayed exact exponential factors are retained.
    """
    if len(b) != 6:
        raise ValueError("Need six potential-jet bounds U through U^(5)")
    b = list(map(exact_nonnegative, b))
    duration = exact_nonnegative(duration, positive=True)
    split = exact_nonnegative(split, positive=True)
    low_argument = b[0]*duration**2/2
    high_argument = duration*(4*b[0]/split+2*b[1]/split**2)
    if rational_caps:
        if any((sp.Rational(1, 2)-value).is_nonnegative is not True
               for value in (low_argument, high_argument)):
            raise ValueError("The chosen potential/domain does not prove both exponential caps")
        low_cap = high_cap = sp.Integer(2)
    else:
        low_cap, high_cap = sp.exp(low_argument), sp.exp(high_argument)
    result = polynomial_bounds(b, duration, split, low_cap, high_cap)
    result.update({"IR_exponent_argument": low_argument, "UV_exponent_argument": high_argument,
                   "IR_exponential_cap": low_cap, "UV_exponential_cap": high_cap})
    return result


def identities():
    x, k = sp.symbols("eta k", positive=True)
    u = sp.Function("U")(x)
    q = 3*u**2+sp.diff(u, x, 2)
    approximation = 1-u/(2*k**2)+q/(8*k**4)
    operator = lambda f: sp.diff(f, x, 3)+4*(k**2+u)*sp.diff(f, x)+2*sp.diff(u, x)*f
    residual = (sp.diff(u, x, 5)+10*u*sp.diff(u, x, 3)
                + 20*sp.diff(u, x)*sp.diff(u, x, 2)+30*u**2*sp.diff(u, x))/(8*k**4)
    green = (1-sp.cos(2*k*x))/(4*k**2)
    return {"Gelfand_Dikii_adiabatic_residual": sp.simplify(operator(approximation)-residual),
            "linear_asymptotic_residual": sp.simplify(
                sp.diff(-u/(2*k**2)+sp.diff(u, x, 2)/(8*k**4), x, 3)
                + 4*k**2*sp.diff(-u/(2*k**2)+sp.diff(u, x, 2)/(8*k**4), x)
                + 2*sp.diff(u, x)-sp.diff(u, x, 5)/(8*k**4)),
            "Green_zeroth_initial_value": green.subs(x, 0),
            "Green_first_initial_value": sp.diff(green, x).subs(x, 0),
            "Green_second_initial_value": sp.diff(green, x, 2).subs(x, 0)-1,
            "Green_homogeneous_equation": sp.diff(green, x, 3)+4*k**2*sp.diff(green, x)}

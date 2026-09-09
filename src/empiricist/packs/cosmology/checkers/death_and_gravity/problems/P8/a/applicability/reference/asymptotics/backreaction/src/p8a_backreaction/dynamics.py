"""Symbolic Einstein, conservation, clock, counterterm and mode identities."""

import sympy as sp
from p8a_reference import stress

T, A, D, KAPPA, HBAR, ETA, K, ETA_I = sp.symbols("t A d kappa hbar eta k eta_i", positive=True)
EPS = sp.Symbol("epsilon", nonnegative=True)
Z = sp.Symbol("z", nonnegative=True)


def first(expression):
    return sp.simplify(sp.diff(expression, EPS).subs(EPS, 0))


def scale():
    return (4*A**2*(T**2-4*EPS*D))**sp.Rational(1, 4)


def hubble():
    return T/(2*(T**2-4*EPS*D))


def radiation_density():
    return 3*A**2/(KAPPA*scale()**4)


def surrogate_density():
    return 48*EPS*D*A**4/(KAPPA*scale()**8)


def frozen_defects(z=Z, time=T):
    common = z**2*(2-z)/(4*time**2*(1-z)**2)
    return {"density": 3*common, "pressure": 5*common, "EED": 9*common}


def taylor_polynomials():
    lower = 1-Z/4-Z**2/9
    upper = 1-Z/4-3*Z**2/32
    return {"lower_root_comparison": sp.cancel((1-Z-lower**4)/Z**2),
            "upper_root_comparison": sp.cancel((upper**4-(1-Z))/Z**2)}


def identities():
    a = scale()
    a0 = sp.sqrt(2*A*T)
    h = hubble()
    rho_r, rho_q = radiation_density(), surrogate_density()
    p_r, p_q = rho_r/3, 5*rho_q/3
    ref = stress.reference_stress()
    ref_rho = ref["rho"].subs({stress.T: T, stress.HBAR: HBAR})
    ref_p = ref["pressure"].subs({stress.T: T, stress.HBAR: HBAR})
    d_value = KAPPA*HBAR/(46080*sp.pi**2)
    r = sp.factor(6*(sp.diff(h, T)+2*h**2))
    rtt = 3*(sp.diff(h, T)+h**2)
    i_rho = sp.factor(2*r*rtt-r**2/2-6*h*sp.diff(r, T))
    i_p = sp.factor(-2*r*(sp.diff(h, T)+3*h**2)+r**2/2
                   +2*sp.diff(r, T, 2)+4*h*sp.diff(r, T))
    i_rho_expected = -18*EPS*D*(7*T**2-4*EPS*D)/(T**2-4*EPS*D)**4
    q = sp.Function("q")(T)
    a_linear = a0*(1+EPS*q)
    h_linear = sp.diff(a_linear, T)/a_linear
    linear_density = first(3*h_linear**2-3*A**2/a_linear**4-3*EPS*D/T**4)
    linear_pressure = first(-2*sp.diff(h_linear, T)-3*h_linear**2
                            -A**2/a_linear**4-5*EPS*D/T**4)
    c_time, delta_c = sp.symbols("c_time delta_C", real=True)
    solution_q = c_time/T-D/T**2
    normalized_q = solution_q+delta_c*KAPPA/(12*A**2)
    varied_c_residual = first(3*h_linear**2
        -KAPPA*(3*A**2/KAPPA+EPS*delta_c)/a_linear**4-3*EPS*D/T**4)
    eta_clock = sp.sqrt(2*T/A)*(1-EPS*D/(3*T**2))
    t0_eta = A*ETA**2/2
    inverse_clock = t0_eta+2*EPS*D/(3*t0_eta)
    a_eta = A*ETA-8*EPS*D/(3*A*ETA**3)
    wrong_a_eta = A*ETA*(1-EPS*D/t0_eta**2)
    potential = sp.factor(-a**2*r/6)
    f = sp.Function("f")(T)
    a_changed = a*sp.exp(EPS**2*f)
    h_changed = h+EPS**2*sp.diff(f, T)
    delta_density = (3*h_changed**2-3*A**2/a_changed**4)-(3*h**2-3*A**2/a**4)
    delta_pressure = (-2*sp.diff(h_changed, T)-3*h_changed**2-A**2/a_changed**4
                      -(-2*sp.diff(h, T)-3*h**2-A**2/a**4))
    second_density = sp.simplify(sp.diff(delta_density, EPS, 2).subs(EPS, 0)/2)
    second_pressure = sp.simplify(sp.diff(delta_pressure, EPS, 2).subs(EPS, 0)/2)
    frozen = frozen_defects(4*EPS*D/T**2)
    return {
        "residuals": {
            "pinned_reference_density_normalization": sp.simplify(KAPPA*ref_rho-3*d_value/T**4),
            "pinned_reference_pressure_normalization": sp.simplify(KAPPA*ref_p-5*d_value/T**4),
            "linear_density_ODE": sp.simplify(linear_density-3*(sp.diff(q, T)+q/T-D/T**3)/T),
            "linear_density_solution": sp.simplify(linear_density.subs(q, solution_q).doit()),
            "independent_linear_pressure_solution": sp.simplify(linear_pressure.subs(q, solution_q).doit()),
            "radiation_normalization_mode": sp.simplify(varied_c_residual.subs(q, normalized_q).doit()),
            "exact_surrogate_hubble": sp.simplify(sp.diff(a, T)/a-h),
            "exact_surrogate_00_equation": sp.simplify(3*h**2-KAPPA*(rho_r+rho_q)),
            "exact_surrogate_ii_equation": sp.simplify(-2*sp.diff(h, T)-3*h**2-KAPPA*(p_r+p_q)),
            "classical_radiation_conservation": sp.simplify(sp.diff(rho_r, T)+3*h*(rho_r+p_r)),
            "surrogate_quantum_conservation": sp.simplify(sp.diff(rho_q, T)+3*h*(rho_q+p_q)),
            "surrogate_reduction_coefficient": sp.simplify((rho_q
                -EPS*HBAR*KAPPA**2*rho_r**2/(8640*sp.pi**2)).subs(D, d_value)),
            "scale_fourth_integrated_equation": sp.simplify(sp.diff(a**4, T)**2
                -16*A**2*a**4-256*EPS*D*A**4),
            "surrogate_first_order_scale": sp.simplify(first(a/a0)+D/T**2),
            "surrogate_first_order_hubble": sp.simplify(first(h)-2*D/T**3),
            "surrogate_FK_R": sp.simplify(r+12*EPS*D/(T**2-4*EPS*D)**2),
            "curvature_trace_equation": sp.simplify(r-KAPPA*(rho_r+rho_q-3*(p_r+p_q))),
            "actual_conformal_derivative": sp.simplify(a*sp.diff(a*sp.diff(a, T), T)/a-a**2*r/6),
            "frozen_density_defect": sp.simplify(3*h**2-KAPPA*rho_r-3*EPS*D/T**4-frozen["density"]),
            "frozen_pressure_defect": sp.simplify(-2*sp.diff(h, T)-3*h**2-KAPPA*p_r
                                                  -5*EPS*D/T**4-frozen["pressure"]),
            "frozen_EED_combination": sp.simplify((frozen["density"]+3*frozen["pressure"])/2-frozen["EED"]),
            "clock_derivative_to_first_order": first(sp.diff(eta_clock, T)-1/a),
            "clock_inverse_to_first_order": first(eta_clock.subs(T, inverse_clock)-ETA),
            "conformal_scale_to_first_order": first(a.subs(T, inverse_clock)-a_eta),
            "conformal_potential_to_first_order": sp.simplify(first(-sp.diff(a_eta, ETA, 2)/a_eta)
                                                             -32*D/(A**2*ETA**6)),
            "FK_Itt_from_variation": sp.simplify(i_rho-i_rho_expected),
            "FK_Itt_first_order": sp.simplify(first(i_rho)+126*D/T**6),
            "FK_Ipressure_first_order": sp.simplify(first(i_p)+378*D/T**6),
            "FK_I_trace": sp.simplify(i_rho-3*i_p+6*(sp.diff(r, T, 2)+3*h*sp.diff(r, T))),
            "FK_I_conservation": sp.simplify(sp.diff(i_rho, T)+3*h*(i_rho+i_p)),
            "loop_counterterm_no_linear_contribution": first(EPS*i_rho),
            "nonunique_completion_no_linear_density_change": first(delta_density),
            "nonunique_completion_no_linear_pressure_change": first(delta_pressure),
            "nonunique_completion_second_density": sp.simplify(second_density-(3*sp.diff(f, T)/T+3*f/T**2)),
            "nonunique_completion_second_pressure": sp.simplify(second_pressure
                -(-2*sp.diff(f, T, 2)-3*sp.diff(f, T)/T+f/T**2)),
        },
        "d_definition": str(d_value),
        "scale_fourth": str(sp.expand(a**4)), "H": str(h), "R_FK": str(r),
        "rescaled_minimal_mode_potential": str(potential),
        "first_order_relative_scale": str(solution_q),
        "radiation_normalization_mode": str(delta_c*KAPPA/(12*A**2)),
        "conformal_clock": str(eta_clock), "first_order_conformal_scale": str(a_eta),
        "incorrect_unperturbed_clock_potential_control": str(first(-sp.diff(wrong_a_eta, ETA, 2)/wrong_a_eta)),
        "correct_first_order_potential": str(32*D/(A**2*ETA**6)),
        "Itt_exact": str(i_rho), "Itt_order_zero_coupling_linear_control": str(first(i_rho)),
        "frozen_reference_defects": {name: str(value) for name, value in frozen_defects().items()},
        "nonunique_all_order_completion": {
            "relative_multiplier": "exp(epsilon^2*f(t))",
            "second_order_density_change": str(second_density),
            "second_order_pressure_change": str(second_pressure),
            "first_order_SEE_fixes_all_higher_orders": False,
        },
    }


def mode_identities():
    s = sp.Symbol("s", positive=True)
    potential = sp.Function("V1")
    u0 = sp.exp(-sp.I*K*(ETA-ETA_I))/sp.sqrt(2*K)
    integrand = -sp.sin(K*(ETA-s))*potential(s)*sp.exp(-sp.I*K*(s-ETA_I))/(K*sp.sqrt(2*K))
    u1 = sp.Integral(integrand, (s, ETA_I, ETA))
    return {
        "residuals": {
            "zeroth_mode_wave_equation": sp.simplify(sp.diff(u0, ETA, 2)+K**2*u0),
            "retarded_first_mode_equation": sp.simplify(sp.diff(u1, ETA, 2)+K**2*u1+potential(ETA)*u0),
            "retarded_first_mode_initial_value": u1.subs(ETA, ETA_I).doit(),
            "retarded_first_mode_initial_velocity": sp.diff(u1, ETA).subs(ETA, ETA_I).doit(),
        },
        "retarded_first_mode": str(u1),
        "momentum_domain": "k>0",
        "preparation_potential_included_in_V1": True,
        "instantaneous_flat_modes_in_nonzero_potential_are_declared_Hadamard": False,
        "uniform_UV_or_actual_RSET_error_bound_derived_from_this_identity": False,
    }

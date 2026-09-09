"""Exact stress, convention, state-selection and renormalization checks."""

import sympy as sp

T, ETA, A, HBAR = sp.symbols("t eta A hbar", positive=True)


def positive_time(value):
    value = sp.sympify(value)
    if value.is_positive is not True or value.is_finite is not True:
        raise ValueError("A finite, strictly positive proper time is required")
    return value


def reference_stress(time=T):
    """Fixed matter prescription only; independent gravity terms are separate."""
    time = positive_time(time)
    rho = HBAR/(15360*sp.pi**2*time**4)
    pressure = sp.Rational(5, 3)*rho
    trace_fk = rho-3*pressure
    return {"rho": rho, "pressure": pressure, "trace_FK": trace_fk,
            "EED_FK": sp.simplify(rho-trace_fk/2)}


def added_geometric_eed(*, metric_shift, einstein_shift, time=T):
    """EED of lambda*g_FK+gamma*G_FK, not a default matter renormalization."""
    time = positive_time(time)
    return -sp.sympify(metric_shift)-3*sp.sympify(einstein_shift)/(4*time**2)


def h1_tt(hubble, time=T):
    return sp.simplify(-36*hubble*sp.diff(hubble, time, 2)
                       +18*sp.diff(hubble, time)**2
                       -108*sp.diff(hubble, time)*hubble**2)


def convention_identities():
    scale = sp.Symbol("a", positive=True)
    g_source = sp.diag(-1, scale**2, scale**2, scale**2)
    g_fk = -g_source
    gradient = sp.Matrix(sp.symbols("d0 d1 d2 d3", real=True))
    tensor = gradient*gradient.T

    def minimal(metric):
        norm = (gradient.T*metric.inv()*gradient)[0]
        return tensor-metric*norm/2

    source, fk = minimal(g_source), minimal(g_fk)
    physical_rho = (gradient[0]**2+sum(gradient[i]**2/scale**2 for i in range(1, 4)))/2
    source_trace = sp.trace(g_source.inv()*source)
    fk_trace = sp.trace(g_fk.inv()*fk)
    q_source = sp.Symbol("Q_H_source", real=True)
    rho, pressure = sp.symbols("rho pressure", real=True)
    isotropic = sp.diag(rho, scale**2*pressure, scale**2*pressure, scale**2*pressure)
    physical_trace = sp.trace(g_fk.inv()*isotropic)
    residuals = {f"covariant_minimal_stress_{i}{j}": fk[i, j]-source[i, j]
                 for i in range(4) for j in range(4)}
    residuals.update({
        "same_physical_density": sp.simplify(fk[0, 0]-physical_rho),
        "trace_flips_not_density": sp.simplify(source_trace+fk_trace),
        "FK_isotropic_trace": physical_trace-(rho-3*pressure),
        "FK_EED_from_covariant_stress": rho-physical_trace/2-(rho+3*pressure)/2,
        "central_conservation_correction_invariant":
            sp.trace(g_fk*(-q_source)/3-g_source*q_source/3),
    })
    return {
        "residuals": residuals,
        "source_signature": "-+++", "FK_signature": "+---",
        "covariant_stress_dictionary": "T_ab_FK=T_ab_source; rho=T_tt; p=T_ii/a^2",
        "trace_dictionary": "Tr_FK=rho-3p=-Tr_source",
        "curvature_dictionary": "G_FK=-G_source; Ricci_ab_FK=-Ricci_ab_source; R_FK=R_source",
        "central_term_dictionary": "P_FK=-P_source on R=0; Q_H_FK=-Q_H_source; g*Q_H invariant",
    }


def identities():
    k, occupation_scale = sp.symbols("k s", positive=True)
    a = A*ETA
    hubble = 1/(2*T)
    conformal_hubble = 1/ETA
    mode = sp.exp(-sp.I*k*ETA)/sp.sqrt(2*k)
    mode_dot = sp.diff(mode, ETA)/a
    mode_integrand = sp.simplify(mode_dot*sp.conjugate(mode_dot)
                                +(k/a)**2*mode*sp.conjugate(mode)-k/a**2)
    proper = reference_stress()
    rho_local = HBAR*(-h1_tt(hubble)/6+3*hubble**4)/(2880*sp.pi**2)
    pressure_conservation = sp.simplify(-rho_local-sp.diff(rho_local, T)/(3*hubble))
    kp, kpp, kppp = (sp.diff(conformal_hubble, ETA, order) for order in (1, 2, 3))
    rho_eta = HBAR*(2*kpp*conformal_hubble-kp**2)/(2880*sp.pi**2*a**4)
    pressure_eta = -HBAR*(2*kppp-2*kpp*conformal_hubble+kp**2)/(8640*sp.pi**2*a**4)
    finite_rho = 2*kpp*conformal_hubble-kp**2-3*conformal_hubble**4
    finite_pressure = (-2*kppp+2*kpp*conformal_hubble-kp**2
                       +12*kp*conformal_hubble**2-3*conformal_hubble**4)
    radiation_a = sp.sqrt(2*A*T)
    constant = sp.Symbol("C_radiation", real=True)
    general_rho = proper["rho"]+constant/radiation_a**4
    general_pressure = proper["pressure"]+constant/(3*radiation_a**4)
    ricci_scalar = 6*(sp.diff(hubble, T)+2*hubble**2)
    ricci_squared = 12*(sp.diff(hubble, T)**2+3*sp.diff(hubble, T)*hubble**2+3*hubble**4)
    riemann_squared = 12*((sp.diff(hubble, T)+hubble**2)**2+hubble**4)
    scalar2, ricci2, riemann2 = sp.symbols("R_squared Ricci_squared Riemann_squared")
    weyl2 = riemann2-2*ricci2+scalar2/3
    euler = riemann2-4*ricci2+scalar2
    wick = sp.Function("w")(T)
    # FK improvement expectation divided by xi, in physical density/pressure.
    improvement_rho = 3*hubble*sp.diff(wick, T)+3*hubble**2*wick
    improvement_pressure = -(sp.diff(wick, T, 2)+2*hubble*sp.diff(wick, T)
                             +(2*sp.diff(hubble, T)+3*hubble**2)*wick)
    thermal_wick = HBAR*occupation_scale**2/(2*sp.pi**2*radiation_a**2)
    thermal_rho = 3*HBAR*occupation_scale**4/(sp.pi**2*radiation_a**4)
    thermal_minimal_extra = hubble**2*thermal_wick/2
    metric_shift, einstein_shift = sp.symbols("lambda gamma", real=True)
    shift_rho = metric_shift-3*einstein_shift*hubble**2
    shift_pressure = -metric_shift+einstein_shift*(2*sp.diff(hubble, T)+3*hubble**2)
    return {
        "residuals": {
            "same_minimal_and_conformal_operator": ricci_scalar/6,
            "reference_mode_Wronskian": sp.simplify(mode*sp.diff(sp.conjugate(mode), ETA)
                                                    -sp.conjugate(mode)*sp.diff(mode, ETA)-sp.I),
            "reference_mode_integrand_pointwise_zero": mode_integrand,
            "reference_mode_matches_direct_minimal_source": sp.simplify(
                mode-sp.exp(-sp.I*k/conformal_hubble)/sp.sqrt(2*k)),
            "radiation_H1_tt_zero": h1_tt(hubble),
            "proper_time_density": sp.simplify(rho_local-proper["rho"]),
            "pressure_from_conservation": sp.simplify(pressure_conservation-proper["pressure"]),
            "direct_minimal_density": sp.simplify(rho_eta-proper["rho"].subs(T, A*ETA**2/2)),
            "direct_minimal_pressure": sp.simplify(pressure_eta-proper["pressure"].subs(T, A*ETA**2/2)),
            "finite_curvature_rho_coefficient": sp.simplify(finite_rho),
            "finite_curvature_pressure_coefficient": sp.simplify(finite_pressure),
            "reference_conservation": sp.simplify(sp.diff(proper["rho"], T)
                                                  +3*hubble*(proper["rho"]+proper["pressure"])),
            "FK_trace_from_curvature_invariants": sp.simplify(proper["trace_FK"]
                +HBAR*(riemann_squared-ricci_squared)/(2880*sp.pi**2)),
            "trace_does_not_fix_C": sp.simplify(general_rho-3*general_pressure-proper["trace_FK"]),
            "conservation_does_not_fix_C": sp.simplify(sp.diff(general_rho, T)
                                                       +3*hubble*(general_rho+general_pressure)),
            "actual_mode_integral_fixes_C_zero": sp.simplify(radiation_a**4*(rho_local-proper["rho"])),
            "zero_reference_Wick_improvement_rho": improvement_rho.subs(wick, 0).doit(),
            "zero_reference_Wick_improvement_pressure": improvement_pressure.subs(wick, 0).doit(),
            "Gauss_Bonnet_Weyl_variational_input": sp.expand(ricci2-(weyl2-euler)/2-scalar2/3),
            "nonvacuum_occupation_rho": sp.simplify(HBAR/(2*sp.pi**2*radiation_a**4)
                *sp.integrate(k**3*sp.exp(-k/occupation_scale), (k, 0, sp.oo))-thermal_rho),
            "nonvacuum_occupation_Wick_square": sp.simplify(HBAR/(2*sp.pi**2*radiation_a**2)
                *sp.integrate(k*sp.exp(-k/occupation_scale), (k, 0, sp.oo))-thermal_wick),
            "nonvacuum_minimal_extra_rho": sp.simplify(
                -improvement_rho.subs(wick, thermal_wick).doit()/6-thermal_minimal_extra),
            "nonvacuum_minimal_extra_pressure": sp.simplify(
                -improvement_pressure.subs(wick, thermal_wick).doit()/6-thermal_minimal_extra),
            "explicit_gravity_EED_shift": sp.simplify((shift_rho+3*shift_pressure)/2
                -added_geometric_eed(metric_shift=metric_shift, einstein_shift=einstein_shift)),
        },
        "reference_stress": {key: str(value) for key, value in proper.items()},
        "reference_Wick_square": "0; source conformal transformation with both scalar curvatures zero",
        "state_selection": "specified positive-frequency modes make the subtracted conformal mode integrand zero at every k>0",
        "general_trace_conservation_density": str(general_rho),
        "reference_radiation_integration_constant": "0; fixed by the mode calculation, not by conservation",
        "Ricci_squared": str(sp.simplify(ricci_squared)),
        "Riemann_squared": str(sp.simplify(riemann_squared)),
        "standard_finite_stress_ambiguities": "m^4*g,m^2*G,I,J all vanish; I=0 from R=0, J=0 from C=0 and Gauss-Bonnet",
        "nonvacuum_negative_control": {
            "occupation": "n(k)=exp(-k/s), s>0",
            "conformal_density_excess": str(thermal_rho),
            "Wick_square_excess": str(thermal_wick),
            "minimal_minus_conformal_density_and_pressure": str(thermal_minimal_extra),
        },
        "nonradiation_H1_tt_negative_control": str(h1_tt(sp.Rational(2, 3)/T)),
        "independent_gravity_EED_shift": str(added_geometric_eed(
            metric_shift=metric_shift, einstein_shift=einstein_shift)),
        "reference_SEE_trace_obstruction": str(proper["trace_FK"]),
    }

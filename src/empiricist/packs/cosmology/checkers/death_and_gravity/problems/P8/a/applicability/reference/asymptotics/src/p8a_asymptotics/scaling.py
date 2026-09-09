"""Symbolic state-difference scaling, SEE component and scope controls."""

import sympy as sp
from p8a_reference import stress

ETA, ETAP, A, HBAR, T = sp.symbols("eta eta_prime A hbar t", positive=True)
X = sp.symbols("x1:4", real=True)
Y = sp.symbols("y1:4", real=True)
B, C, ELL = sp.symbols("B C ell", real=True)
KAPPA, EINSTEIN = sp.symbols("kappa b", positive=True)


def point_split_difference(kernel):
    return sp.simplify(sp.diff(kernel/(A**2*ETA*ETAP), ETA, ETAP)/(A**2*ETA*ETAP))


def coincidence(expression):
    return sp.simplify(expression.subs({ETAP: ETA, **dict(zip(Y, X))}, simultaneous=True))


def coherent_difference(mean):
    return sp.simplify((sp.diff(mean/(A*ETA), ETA)/(A*ETA))**2)


def flat_wave(expression):
    return sp.simplify(sp.diff(expression, ETA, 2)-sum(sp.diff(expression, coord, 2) for coord in X))


def jet_difference(f0, f1, f2):
    return (f0/ETA**6-f1/ETA**5+f2/ETA**4)/A**4


def reference_eed():
    return stress.reference_stress()["EED_FK"].subs({stress.T: A*ETA**2/2,
                                                   stress.HBAR: HBAR})


def required_eed():
    return (3*EINSTEIN*A**2/KAPPA-C)/(A**4*ETA**4)+ELL/KAPPA


def identities():
    function = sp.Function("F")(ETA, ETAP)
    split = point_split_difference(function)
    expected = (sp.diff(function, ETA, ETAP)/(ETA**2*ETAP**2)
                -sp.diff(function, ETA)/(ETA**2*ETAP**3)
                -sp.diff(function, ETAP)/(ETA**3*ETAP**2)
                +function/(ETA**3*ETAP**3))/A**4
    f0, f1, f2 = sp.symbols("f0 f1 f2", real=True)
    normalized = sp.expand(A**4*ETA**8*(reference_eed()+jet_difference(f0, f1, f2)))
    proper_difference = (f0/(8*A*T**3)
                         -f1/(2**sp.Rational(5, 2)*A**sp.Rational(3, 2)*T**sp.Rational(5, 2))
                         +f2/(4*A**2*T**2))
    constant = coherent_difference(B)
    linear = coherent_difference(B*ETA)
    restricted_mean = B/(ETA-X[0])
    restricted = coherent_difference(restricted_mean).subs(dict.fromkeys(X, 0))
    bad_kernel = 1/(ETA*ETAP)
    eed_symbol = sp.Symbol("E_omega", real=True)
    geometric = -3*EINSTEIN/(4*(A*ETA**2/2)**2)-ELL
    residual = sp.expand(geometric+KAPPA*(eed_symbol+C/(A*ETA)**4))
    rho = stress.reference_stress()["rho"].subs({stress.T: T, stress.HBAR: HBAR})
    pressure = stress.reference_stress()["pressure"].subs({stress.T: T, stress.HBAR: HBAR})
    extra_rho, extra_pressure = -rho, -pressure
    radiation_rho = C/(4*A**2*T**2)
    cancelling_c = 3*EINSTEIN*A**2/KAPPA
    return {
        "residuals": {
            "actual_point_split_chain_rule": sp.simplify(split-expected),
            "normalized_exact_jet_expression": sp.simplify(normalized-(
                HBAR/(320*sp.pi**2)+ETA**2*f0-ETA**3*f1+ETA**4*f2)),
            "conformal_to_proper_difference": sp.simplify(
                jet_difference(f0, f1, f2).subs(ETA, sp.sqrt(2*T/A))-proper_difference),
            "proper_reference_limit_coefficient": sp.simplify(
                T**4*reference_eed().subs(ETA, sp.sqrt(2*T/A))-HBAR/(5120*sp.pi**2)),
            "clock_normalization_factor": sp.simplify((A*ETA**2/2)**4-A**4*ETA**8/16),
            "constant_coherent_mean_solves_wave": flat_wave(B),
            "constant_coherent_delta": sp.simplify(constant-B**2/(A**4*ETA**6)),
            "constant_coherent_point_split_agrees": sp.simplify(
                coincidence(point_split_difference(B**2))-constant),
            "linear_coherent_mean_solves_wave": flat_wave(B*ETA),
            "linear_coherent_physical_mean_constant": sp.diff(B*ETA/(A*ETA), ETA),
            "linear_coherent_delta_cancels": linear,
            "linear_coherent_point_split_agrees": coincidence(point_split_difference(B**2*ETA*ETAP)),
            "restricted_domain_mean_solves_wave": flat_wave(restricted_mean),
            "restricted_domain_leading_delta": sp.simplify(restricted-4*B**2/(A**4*ETA**8)),
            "necessary_SEE_component_solution": sp.simplify(residual.subs(eed_symbol, required_eed())),
            "required_normalized_limit": sp.limit(A**4*ETA**8*required_eed(), ETA, 0, dir="+"),
            "excluded_negative_fluid_conservation": sp.simplify(
                sp.diff(extra_rho, T)+3*(extra_rho+extra_pressure)/(2*T)),
            "excluded_negative_fluid_density_equation": sp.simplify(
                -3*EINSTEIN/(4*T**2)+KAPPA*(rho+extra_rho+radiation_rho.subs(C, cancelling_c))),
            "excluded_negative_fluid_pressure_equation": sp.simplify(
                -EINSTEIN/(4*T**2)+KAPPA*(pressure+extra_pressure
                    +radiation_rho.subs(C, cancelling_c)/3)),
        },
        "universal_conformal_EED_coefficient": str(HBAR/(320*sp.pi**2)),
        "universal_proper_EED_coefficient": str(HBAR/(5120*sp.pi**2)),
        "state_difference": str(jet_difference(f0, f1, f2)),
        "proper_time_state_difference": str(proper_difference),
        "normalized_remainder": str(ETA**2*f0-ETA**3*f1+ETA**4*f2),
        "required_EED": str(required_eed()),
        "constant_coherent_state_difference": str(constant),
        "linear_coherent_state_difference": str(linear),
        "restricted_domain_control": {
            "domain": "eta>0 and eta-x1>0, not the whole radiation patch",
            "flat_mean": str(restricted_mean),
            "additional_leading_coefficient": str(sp.simplify(A**4*ETA**8*restricted)),
            "smooth_on_full_spatial_Cauchy_slice": False,
        },
        "non_bisolution_control": {
            "kernel": str(bad_kernel),
            "left_wave_residual": str(sp.diff(bad_kernel, ETA, 2)),
            "right_wave_residual": str(sp.diff(bad_kernel, ETAP, 2)),
            "admitted_as_state_difference": False,
        },
        "excluded_extra_source_control": {
            "rho": str(extra_rho), "pressure": str(extra_pressure),
            "trace_FK": str(sp.simplify(extra_rho-3*extra_pressure)),
            "classical_radiation_C": str(cancelling_c), "ell": "0",
            "ordinary_traceless_radiation": False,
            "formal_complete_density_and_pressure_match": True,
        },
    }

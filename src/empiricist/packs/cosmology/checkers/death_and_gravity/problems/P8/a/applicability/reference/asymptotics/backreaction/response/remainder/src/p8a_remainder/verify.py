"""Read-only replay of a finite-amplitude actual RSET remainder certificate."""

import argparse
import hashlib
import json
from pathlib import Path

import sympy as sp
from p8a_response import verify as prior

from . import geometry, independent, kernel, mode_bounds, stress

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT/"certificates"/"radiation-remainder.json"
PRIOR_SHA = "1101c2c2977716ef3bcf452ab02f69abb91ba43c7720df0920384099a1c1e868"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prior_checks():
    if sha(prior.REPORT) != PRIOR_SHA:
        raise ValueError("Pinned A.6 certificate changed")
    prior.validate_report(json.loads(prior.REPORT.read_text()), prior.build_report())
    return PRIOR_SHA


def verified_residuals(values):
    for name, value in values.items():
        if sp.simplify(value) != 0:
            raise ValueError(f"Nonzero finite-remainder derivation residual: {name}")
    return dict.fromkeys(values, "0")


def verified_exclusion(name, value):
    value = sp.simplify(value)
    if value == 0:
        raise ValueError(f"Required exclusion control vanished: {name}")
    return str(value)


def checked_bounds():
    data = geometry.calibration()
    replay = independent.replay(geometry.ring_records())
    if (list(map(str, data["potential_bounds"])) != replay["U_jet_bounds_per_delta"]
            or list(map(str, data["p_bounds"])) != replay["p_jet_bounds"]
            or str(data["delta_bar"]) != replay["delta_bar"]):
        raise ValueError("Independent finite-family potential bounds disagree")
    delta = geometry.DELTA
    b = list(map(sp.Rational, data["potential_bounds"]))
    cap = sp.Rational(data["delta_bar"])
    mode_bounds.bounds([cap*x for x in b], 3, 1, rational_caps=True)
    polynomials = mode_bounds.polynomial_bounds([delta*x for x in b], sp.Integer(3),
                                                sp.Integer(1), sp.Integer(2), sp.Integer(2))
    polynomial_records = []
    constants = []
    for expression in polynomials["integrated_remainder_derivatives"]:
        polynomial = sp.Poly(expression, delta)
        if any(power[0] < 2 or coefficient <= 0 for power, coefficient in polynomial.terms()):
            raise ValueError("Quadratic nonnegative-amplitude majorant condition failed")
        quotient = sp.cancel(expression/delta**2)
        constants.append(quotient.subs(delta, cap))
        polynomial_records.append({"bound_polynomial": str(expression),
                                   "minimum_amplitude_degree": min(power[0] for power, _ in polynomial.terms()),
                                   "nonnegative_coefficients": True,
                                   "normalized_at_delta_bar": str(constants[-1])})
    if list(map(str, constants)) != replay["integrated_mode_remainder_constants"]:
        raise ValueError("Independent all-frequency remainder constants disagree")
    for name, replay_name in (("IR_integral_bounds", "IR_remainder_constants"),
                             ("UV_integral_bounds", "UV_remainder_constants")):
        values = [str(sp.cancel(value/delta**2).subs(delta, cap)) for value in polynomials[name]]
        if values != replay[replay_name]:
            raise ValueError("Independent frequency-region bounds disagree")
    coefficients = stress.calibration_bounds(constants, b, cap)
    if {name: str(value) for name, value in coefficients.items()} != replay["stress_error_constants"]:
        raise ValueError("Independent finite-amplitude stress-error constants disagree")
    rounded = {"density": 8*10**14, "pressure": 9*10**14, "EED": 17*10**14}
    margins = {name: rounded[name]-value for name, value in coefficients.items()}
    if any(value <= 0 for value in margins.values()):
        raise ValueError("Rounded rational stress-error enclosure failed")
    geometry.check_amplitude(sp.Rational(1, 10**12))
    replay["nonnegative_amplitude_polynomial_audit"] = polynomial_records
    replay["rounded_stress_error_upper_bounds"] = {name: str(value) for name, value in rounded.items()}
    replay["strict_rounded_bound_margins"] = {name: str(value) for name, value in margins.items()}
    replay["Wick_C2_remainder_constants"] = list(map(str, stress.wick_calibration_bounds(constants, b[0], cap)))
    replay["Wick_C2_units"] = "j-th actual conformal derivative: hbar*delta^2/(pi^2*A^2*eta_star^(4+j))"
    replay["stress_error_units"] = "hbar*delta^2/(pi^2*A^4*eta_star^8)"
    replay["actual_finite_amplitude_accuracy_example"]["physical_amplitude_interpretation"] = (
        "t_star=A*eta_star^2/2, delta=4*epsilon*d/t_star^2; epsilon=1 and t_star>=2*10^6*sqrt(d) suffice")
    return replay


def build_report():
    prior_hash = prior_checks()
    paths = sorted(ROOT.glob("src/p8a_remainder/*.py"))+sorted(ROOT.glob("tests/*.py"))
    paths += sorted(ROOT.glob("*.md"))+sorted(ROOT.glob("notes/*.md"))
    geometry_checks = geometry.identities()
    clock_exclusion = geometry_checks.pop("wrong_frozen_clock_potential")
    stress_checks = stress.identities()
    history_exclusion = stress_checks.pop("drop_history_fails_conservation")
    eta = sp.Symbol("eta", positive=True)
    a, r, history = (sp.Function(name)(eta) for name in ("a", "Rmode", "J"))
    return {
        "schema": 1, "claim": "P8-A.7", "date": "2026-09-05",
        "status": "FINITE_AMPLITUDE_ACTUAL_RSET_BORN_ON_EXACT_GEOMETRY_ERROR_CERTIFIED; SEE_QSEI_FOCUSING_OPEN",
        "prior_A6_sha256": prior_hash,
        "source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in paths},
        "formulation": "FORMULATION.md", "written_proof": "notes/proof.md", "source_dictionary": "notes/sources.md",
        "scope": {
            "field": "one real free massless minimally coupled scalar",
            "state": "actual positive homogeneous isotropic quasifree Hadamard state transported from the radiation past",
            "initial_Cauchy_slice": "y=1/2, strictly before preparation at y=1; all initial potential jets vanish",
            "FK_conventions": "+---; R=+6*(Hdot+2*H^2); GS Box equals FK Box",
            "prescription": "GS raw H_lambda Wick square and conserved stress; same lambda>0 and physical FK gamma*I_R2 in actual and approximation",
            "gamma_dictionary": "gamma=-(c3_GS+c4_GS/3); no additional alpha*R Wick shift",
            "identical_exact_anomaly_local_terms_and_past_density": True,
            "absolute_RSET_scheme_independence": False,
            "actual_finite_amplitude_RSET_error": True,
            "uniform_derived_nonzero_amplitude_interval": True,
            "nonlinear_Wick_remainder_through_two_actual_conformal_derivatives": True,
            "actual_smooth_preparation_derivative_bounds_derived": True,
            "unconstrained_supplied_jet_bounds_automatically_certified": False,
            "Born_functional_claimed_positive_state": False,
            "A6_epsilon_linear_formula_has_same_error_without_clock_comparison": False,
            "A6_second_order_corrected_metric_jets_certified_here": False,
            "finite_amplitude_SEE_solution_shadowing_or_stability": False,
            "quantitative_perturbed_QSEI_or_all_sampler_bound": False,
            "all_geodesic_focusing_or_P8a_completion": False,
        },
        "mode_and_retarded_Green_identities": verified_residuals(mode_bounds.identities()),
        "exact_finite_geometry_identities": verified_residuals(geometry_checks),
        "exact_stress_reconstruction_identities": verified_residuals(stress_checks),
        "exact_metric_retarded_kernel_identities": verified_residuals(kernel.identities()),
        "finite_Wick_decomposition": "<phi^2>=-hbar*K_{a,lambda}[U]/(8*pi^2*a^2)+hbar*Rmode/(4*pi^2*a^2)",
        "exact_retarded_Born_kernel": "integral_eta_i^eta U'(s)*log((eta-s)/T)ds+U(eta)*(log(sqrt(2)*a(eta)*T/lambda)+5/6)",
        "exact_stress_error_in_hbar_over_pi2_units": {name: str(value) for name, value in stress.components(a, r, history, eta).items()},
        "mode_potential_jet_ring": geometry.ring_records(),
        "derived_finite_geometry": geometry.report(),
        "independently_replayed_uniform_bounds": checked_bounds(),
        "negative_controls": {
            "frozen_background_clock_changes_exact_potential": verified_exclusion("clock", clock_exclusion),
            "omitted_retarded_history_breaks_stress_conservation": verified_exclusion("history", history_exclusion),
            "local_adiabatic_subtraction_alone_leaves_linear_U5": "U^(5)/(8*k^4); independent symbolic audit checks exact-Born cancellation",
            "inputs_rejected": "rounded floats, infinities, unproved signs, negative jets, missing jets, nonpositive split/span, unsupported switch orders, amplitude or exponential caps outside proved domain",
        },
        "verification_boundary": [
            "the full transported state, Hadamard prescription and baseline past density are pinned through A.6 and every earlier dependency",
            "IR Volterra and UV retarded-residual inequalities and coincidence-limit domination are written analytic proofs, not finite sampling claims",
            "the finite-family derivative majorants and all numerical constants are exact rational enclosures, replayed separately using fractions only",
            "a separate exact Taylor-series audit checks all six fractional clock jets; parent-owned tests derive mode, curvature and conservation identities independently",
            "the Born-on-exact-geometry functional retains exact history and local terms; it is neither a positive state construction nor a solved SEE metric",
            "the one-percent example divides by positive radiation-reference components, not actual or Born values and not a cosmological error target",
        ],
    }


def validate_report(expected, actual):
    if expected != actual:
        raise ValueError("Radiation finite-amplitude remainder certificate differs from exact replay")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    actual = build_report()
    if args.check:
        validate_report(json.loads(REPORT.read_text()), actual)
        print("P8(a) A.7: finite-amplitude actual RSET error and all-frequency C2 remainder replay passed; SEE/QSEI/focusing OPEN")
    else:
        print(json.dumps(actual, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

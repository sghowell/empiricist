"""Read-only, source-hash-pinned replay of the actual first-response result."""

import argparse
import hashlib
import json
from pathlib import Path

import sympy as sp
from p8a_backreaction import verify as prior

from . import defects, independent, kernel, preparation, response

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT/"certificates"/"radiation-response.json"
PRIOR_SHA = "a7e1766a16778920c5784b9c52f997497a6e22259c48d956c8ca50ca60770930"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prior_checks():
    if sha(prior.REPORT) != PRIOR_SHA:
        raise ValueError("Pinned A.5 certificate changed")
    prior.validate_report(json.loads(prior.REPORT.read_text()), prior.build_report())
    return PRIOR_SHA


def verified_residuals(values):
    for name, value in values.items():
        if sp.simplify(value) != 0:
            raise ValueError(f"Nonzero first-response derivation residual: {name}")
    return dict.fromkeys(values, "0")


def checked_bounds():
    direct, exact = preparation.normalized_example(), independent.replay()
    for name in ("Q_norm_constants", "V_norm_constants", "K_norm_constants"):
        if list(map(str, direct[name])) != exact[name]:
            raise ValueError("Independent smooth-preparation norm bounds disagree")
    switch = direct["switch"]
    for name, independent_name in (("r_derivatives", "r_derivative_bounds"),
                                   ("switch_derivatives", "switch_derivative_bounds")):
        if list(map(str, switch[name])) != exact[independent_name]:
            raise ValueError("Independent switch bounds disagree")
    for polynomial, coefficients in zip(switch["polynomials"], exact["switch_polynomial_coefficients"], strict=True):
        reconstructed = sum(sp.Rational(c)*switch["variable"]**n for n, c in enumerate(coefficients))
        if sp.expand(polynomial-reconstructed) != 0:
            raise ValueError("Independent exponential derivative polynomials disagree")
    constants = {name: str(value) for name, value in direct[
        "response_constants_in_hbar_d_over_pi2_A6_eta_star12_units"].items()}
    if constants != exact["response_constants"]:
        raise ValueError("Independent actual first-response constants disagree")
    checks = preparation.elementary_checks()
    if checks["switch_denominator_monotonic_identity"] != 0:
        raise ValueError("Switch denominator monotonic identity failed")
    if any(value <= 0 for name, value in checks.items() if name != "switch_denominator_monotonic_identity"):
        raise ValueError("An elementary positive enclosure failed")
    exact["elementary_identity_and_margins"] = {name: str(value) for name, value in checks.items()}
    return exact


def build_report():
    prior_hash = prior_checks()
    paths = sorted(ROOT.glob("src/p8a_response/*.py"))+sorted(ROOT.glob("tests/*.py"))
    paths += sorted(ROOT.glob("*.md"))+sorted(ROOT.glob("notes/*.md"))
    eta = kernel.ETA
    k, q = sp.Function("K")(eta), sp.Function("Q")(eta)
    example = checked_bounds()
    return {
        "schema": 1, "claim": "P8-A.6", "date": "2026-09-05",
        "status": "ACTUAL_PREPARED_STATE_FIRST_RSET_VARIATION_AND_SMOOTH_PREPARATION_DERIVATIVE_BOUNDS; FINITE_AMPLITUDE_SEE_QSEI_OPEN",
        "prior_A5_sha256": prior_hash,
        "source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in paths},
        "formulation": "FORMULATION.md", "written_proof": "notes/proof.md", "source_dictionary": "notes/sources.md",
        "scope": {
            "field": "one real massless minimally coupled scalar",
            "state": "actual past-Cauchy-transported homogeneous isotropic quasifree Hadamard state",
            "initial_Cauchy_slice": "strictly before eta_star, e.g. eta_star/2; log integral can start at eta_star by flatness",
            "FK_curvature": "R=+6*(Hdot+2*H^2); GS Box equals FK Box; do not import P8(b) R sign",
            "prescription": "GS raw H_lambda Wick square, conserved GS(3.4) stress plus physical FK gamma*I_R2",
            "gamma_dictionary": "gamma=-(c3_GS+c4_GS/3); finite massless curvature freedom not fixed by A.3",
            "generic_lambda_gamma_retained": True,
            "named_calibration": "lambda=2*sqrt(2)*A*eta_star^2, gamma=0; a new declared normalization, not scheme independence",
            "proper_time_comparison": True,
            "past_state_fixes_radiation_integration_constant": True,
            "actual_first_RSET_parameter_derivative_computed": True,
            "computed_smooth_preparation_derivative_bounds": True,
            "arbitrary_preparation_norm_tuples_certified_automatically": False,
            "finite_epsilon_RSET_remainder_bound": False,
            "uniform_parameter_interval_response_bound": False,
            "actual_second_Einstein_defect_coefficient_bounded": True,
            "qualitative_corrected_actual_compact_slab_residual_O_epsilon_cubed": True,
            "numerical_cubic_residual_remainder_bound": False,
            "exact_SEE_solution_or_stability_theorem": False,
            "quantitative_perturbed_QSEI_or_all_sampler_bound": False,
            "cosmological_focusing_or_P8a_completion": False,
        },
        "kernel_identities": verified_residuals(kernel.identities()),
        "stress_clock_anomaly_and_scheme_identities": verified_residuals(response.identities()),
        "asymptotic_defect_and_second_correction_identities": verified_residuals(defects.identities()),
        "actual_fixed_proper_time_first_response": {name: str(value) for name, value in response.proper_time(k, q).items()},
        "retarded_kernel": "integral_eta_i^eta V'(s)*log((eta-s)/T) ds + V(eta)*(log(sqrt(2)*A*eta*T/lambda)+5/6)",
        "prepared_potential": "Q=-4*d*chi_tilde/(A^2*eta^4); V=-Q''-3*Q'/eta; full history retained",
        "Wick_square_first_response": "-hbar*K/(8*pi^2*A^2*eta^2)",
        "subtraction_length_stress_shift": "-hbar*log(lambda2/lambda1)*I1/(576*pi^2)",
        "specific_smooth_preparation": {
            "switch": "r(x)=exp(-1/x) for x>0 else0; sigma=r(x)/(r(x)+r(1-x))",
            "cutoff": "chi_tilde=sigma((eta-eta_star)/eta_star)*sigma((4*eta_star-eta)/eta_star)",
            "proper_time_pullback": "chi(t)=chi_tilde(sqrt(2*t/A))",
            "observation_envelope": "[2*eta_star,3*eta_star]; compact interior J for near-target A.5/correction theorem",
            "C_infinity_derivative_norms_derived_not_assumed": True,
            "denominator_bound": "r(x)+r(1-x)>=2*exp(-2)>1/4",
            "auxiliary_span": "2*eta_star", "local_log_absolute_cap": "2",
            "exact_independent_bounds": example,
        },
        "negative_controls": {
            "kernel": {name: value if isinstance(value, bool) else str(value) for name, value in kernel.controls().items()},
            "stress": {name: value if isinstance(value, bool) else str(value) for name, value in response.controls().items()},
            "finite_or_unproved_parameter_inputs_rejected": "tests include rounded floats, infinity, wrong signs and missing derivative data",
        },
        "verification_boundary": [
            "Hadamard propagation, positivity of full transported states and HW joint smoothness are primary written inputs replayed through A.5",
            "the retarded distribution/finite-part limit and first-derivative coincidence exchange are proved in the notes, not by finite arithmetic alone",
            "all switch polynomials, derivative norm recurrences and response constants agree with a separate Fraction-only implementation",
            "independent parent geometry tests derive proper-time curvature, finite tensor, spatial finite limit and second-order correction without the assembly oracle",
            "the numerical bounds apply to the first parameter derivative at zero, not a uniform epsilon neighborhood or the truncated Born covariance as a state",
        ],
    }


def validate_report(expected, actual):
    if expected != actual:
        raise ValueError("Radiation first-response certificate differs from exact replay")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    actual = build_report()
    if args.check:
        validate_report(json.loads(REPORT.read_text()), actual)
        print("P8(a) A.6: actual first RSET response and smooth-preparation derivative bounds replay passed; finite-amplitude SEE/QSEI OPEN")
    else:
        print(json.dumps(actual, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

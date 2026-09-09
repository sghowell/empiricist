"""Read-only pinned replay of the finite-slab backreaction checkpoint."""

import argparse
import hashlib
import json
from pathlib import Path

import sympy as sp
from p8a_asymptotics import verify as prior

from . import bounds, dynamics, independent

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT/"certificates"/"radiation-backreaction.json"
PRIOR_SHA = "05d8484a9f39cc4c47a6a6441d7ab589aea78ca449773bdc3cad72bd42dc5eec"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prior_checks():
    if sha(prior.REPORT) != PRIOR_SHA:
        raise ValueError("Pinned A.4 certificate changed")
    prior.validate_report(json.loads(prior.REPORT.read_text()), prior.build_report())
    return PRIOR_SHA


def verified_residuals(result):
    for name, value in result["residuals"].items():
        if sp.simplify(value) != 0:
            raise ValueError(f"Nonzero backreaction derivation residual: {name}")
    result["residuals"] = dict.fromkeys(result["residuals"], "0")
    return result


def checked_rational_bounds():
    result = independent.replay()
    polynomials = dynamics.taylor_polynomials()
    for symbolic, exact in (("lower_root_comparison", "lower_root_polynomial"),
                            ("upper_root_comparison", "upper_root_polynomial")):
        reconstructed = sum(sp.Rational(value)*dynamics.Z**degree for degree, value in enumerate(
            result[exact]["power_coefficients"]))
        if sp.expand(polynomials[symbolic]-reconstructed) != 0:
            raise ValueError("Independent and symbolic root polynomial disagree")
    for name, expression in dynamics.frozen_defects(time=sp.Integer(1)).items():
        ratio_at_endpoint = sp.simplify((expression/dynamics.Z**2).subs(dynamics.Z, sp.Rational(1, 4)))
        if ratio_at_endpoint != sp.Rational(result["frozen_defect_constants"][name]):
            raise ValueError("Independent and symbolic frozen-defect constants disagree")
    if sp.Rational(result["d_coefficient_in_kappa_hbar_over_pi2_units"]) != sp.Rational(1, 46080):
        raise ValueError("Independent first-order reference coefficient disagrees")
    if result["scale_fourth_ODE_epsilon_d_A4_coefficient"] != "256":
        raise ValueError("Independent scale-fourth equation coefficient disagrees")
    return result


def slab_example():
    slab = bounds.Slab(d=1, epsilon="1/64", t_minus=1, t_plus=2)
    return {
        "clock_units": "normalized so d=1; not a cosmological parameter calibration",
        "epsilon": str(slab.epsilon), "t_interval": [str(slab.t_minus), str(slab.t_plus)],
        "actual_z_max": str(slab.actual_z_max), "certified_z_cap": str(slab.z_max),
        "preparation": slab.preparation_check("1/2"),
        "frozen_reference_defect_bounds": {name: str(value) for name, value in bounds.frozen_bounds(slab).items()},
        "relative_scale_Taylor_error_bound": str(slab.actual_z_max**2/9),
        "synthetic_conditional_response_interface": bounds.response_bridge(
            slab, density_response=1, pressure_response=2),
        "synthetic_response_inputs_are_claimed_actual_quantum_bounds": False,
    }


def build_report():
    prior_hash = prior_checks()
    source_paths = sorted(ROOT.glob("src/p8a_backreaction/*.py"))+sorted(ROOT.glob("tests/*.py"))
    source_paths += sorted(ROOT.glob("*.md"))+sorted(ROOT.glob("notes/*.md"))
    return {
        "schema": 1, "claim": "P8-A.5", "date": "2026-09-05",
        "status": "FIRST_ORDER_BACKREACTION_AND_QUALITATIVE_COMPACT_SLAB_RSET_RESIDUAL_DERIVED; QUANTITATIVE_SEE_QSEI_OPEN",
        "prior_A4_sha256": prior_hash,
        "source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in source_paths},
        "formulation": "FORMULATION.md", "written_proof": "notes/proof.md", "source_dictionary": "notes/sources.md",
        "scope": {
            "field": "free real massless minimally coupled scalar",
            "prescription": "same fixed conserved locally covariant massless A.3 prescription, including its curvature terms on new metrics",
            "FK_dictionary": "g_FK=-g_source; R_ab_FK=-R_ab_source; R_FK=+6*(Hdot+2*H^2)",
            "loop_scaling": "G_FK+kappa*(T_rad+epsilon*RSET)=0; d=kappa*hbar/(46080*pi^2)",
            "classical_radiation": "rho=C_rad/a^4, p=rho/3, C_rad=3*A^2/kappa fixed",
            "cosmological_term": "0",
            "independent_order_zero_curvature_squared_couplings_allowed": False,
            "fixed_finite_loop_order_curvature_squared_couplings_allowed": True,
            "first_order_time_origin_and_normalization_modes": "displayed separately and fixed for the comparison",
            "exact_order_reduced_surrogate_solution_established": True,
            "surrogate_all_order_completion_uniquely_fixed_by_first_order_SEE": False,
            "surrogate_source_identified_with_actual_RSET": False,
            "certified_Taylor_domain": "0<=z=4*epsilon*d/t^2<=1/4",
            "actual_state_family": "reference Hadamard state transported from an unchanged past neighborhood through a smooth temporally prepared FLRW metric",
            "target_metric": "a_OR on the compact target slab; smooth cutoff to a0 in the past and outside the preparation support",
            "actual_RSET_smooth_metric_parameter_dependence_derived": True,
            "actual_SEE_residual_qualitatively_O_epsilon_squared_on_fixed_compact_slab": True,
            "numerical_actual_RSET_response_bound_derived": False,
            "nearby_exact_SEE_solution_or_stability_theorem_established": False,
            "QSEI_on_perturbed_metric_quantitatively_calibrated": False,
            "fixed_h_QSEI_smoothness_promoted_from_diagonal_stress_alone": False,
            "uniform_all_h_H2_QSEI_bound_established": False,
            "physical_singularity_at_surrogate_zero_established": False,
        },
        "Einstein_clock_curvature_and_completion_identities": verified_residuals(dynamics.identities()),
        "first_order_mode_response_identity": verified_residuals(dynamics.mode_identities()),
        "independent_rational_Taylor_and_defect_certificates": checked_rational_bounds(),
        "finite_slab_arithmetic_example": slab_example(),
        "strongest_explicit_bounds": {
            "Taylor": "3*z^2/32 <= 1-z/4-(1-z)^(1/4) <= z^2/9",
            "frozen_density": "0<=D_rho<=7*z^2/(3*t^2)",
            "frozen_pressure": "0<=D_p<=35*z^2/(9*t^2)",
            "frozen_EED": "0<=(D_rho+3*D_p)/2<=7*z^2/t^2",
            "actual_response": "qualitative O(epsilon^2) only; numerical bound conditional on supplied response constants",
        },
        "verification_boundary": [
            "Hadamard propagation, state positivity under Cauchy evolution, and the Hollands-Wald smooth-state lemma are written theorem inputs",
            "the local compact-causal-footprint argument and qualitative actual residual theorem are proved in notes/proof.md, not by finite arithmetic",
            "rational Bernstein/root certificates and symbolic independent checks prove the stated reduced-model inequalities and identities",
            "the reference quantum stress is imported only after unchanged A.4/A.3/A.2/A.1 replay",
        ],
        "not_established": [
            "an exact SEE solution or a quantified distance to one",
            "a numerical RSET derivative/response bound for the actual prepared state",
            "a perturbed-metric QSEI constant, a frequency-uniform mode remainder, or an all-sampler H2 estimate",
            "an order-zero curvature-squared model or an arbitrary family of Hadamard states",
            "a global extrapolation to z=1, physical singularity/bounce, or validity at Planck curvature",
            "a new focusing theorem, realistic-field cosmological calibration, or full P8(a) completion",
        ],
    }


def validate_report(expected, actual):
    if expected != actual:
        raise ValueError("Radiation backreaction certificate differs from exact rational replay")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    actual = build_report()
    if args.check:
        validate_report(json.loads(REPORT.read_text()), actual)
        print("P8(a) A.5: first-order/surrogate bounds and qualitative compact-slab residual replay passed; quantitative SEE/QSEI OPEN")
    else:
        print(json.dumps(actual, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

"""Read-only pinned replay of the whole-patch exact-radiation obstruction."""

import argparse
import hashlib
import json
from pathlib import Path

import sympy as sp
from p8a_radiation import validated
from p8a_reference import verify as prior

from . import bounds, extension, independent, scaling

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT/"certificates"/"radiation-asymptotics.json"
PRIOR_SHA = "dc762112cdd2a5c0330f12d8bf157e27f5bae10d31cafa3b877cbce6eaa92b31"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prior_checks():
    if sha(prior.REPORT) != PRIOR_SHA:
        raise ValueError("Pinned A.3 certificate changed")
    prior.validate_report(json.loads(prior.REPORT.read_text()), prior.build_report())
    return PRIOR_SHA


def verified_residuals(result):
    for name, value in result["residuals"].items():
        if sp.simplify(value) != 0:
            raise ValueError(f"Nonzero asymptotic derivation residual: {name}")
    result["residuals"] = dict.fromkeys(result["residuals"], "0")
    return result


def checked_extension():
    result = verified_residuals(extension.identities())
    other = independent.cauchy_replay()
    for key in ("independent_monomial_table", "through_zero_value"):
        if result[key] != other[key]:
            raise ValueError("Independent and symbolic double Cauchy calculations disagree")
    if not result["omitted_mixed_data_control_is_nonzero"]:
        raise ValueError("Missing mixed Cauchy data control did not fail")
    table = result.pop("independent_monomial_table")
    other.pop("independent_monomial_table")
    result["independent_sparse_rational_checks"] = other
    result["matching_monomial_count"] = len(table)
    result["matching_exact_coefficient_table_sha256"] = hashlib.sha256(
        json.dumps(table, separators=(",", ":")).encode()).hexdigest()
    return result


def checked_scaling():
    result = verified_residuals(scaling.identities())
    other = independent.scaling_replay()
    p, q = sp.symbols("p q", integer=True)
    coefficient = sp.Integer(0)
    for row in other["point_split_Leibniz_allocations"]:
        i, j = row["left_F_derivatives"], row["right_F_derivatives"]
        if row["diagonal_eta_power"]-i-j != -6:
            raise ValueError("Independent point-split exponent disagrees")
        coefficient += sp.Rational(row["coefficient"])*p**i*q**j
    if sp.expand(coefficient-(p-1)*(q-1)) != 0:
        raise ValueError("Independent point-split Leibniz coefficient disagrees")
    for source, target in (
        ("reference_conformal_coefficient_in_hbar_over_pi2_units", "universal_conformal_EED_coefficient"),
        ("reference_proper_coefficient_in_hbar_over_pi2_units", "universal_proper_EED_coefficient"),
    ):
        coefficient = sp.sympify(result[target], locals={"hbar": scaling.HBAR})*sp.pi**2/scaling.HBAR
        if sp.simplify(coefficient-sp.Rational(other[source])) != 0:
            raise ValueError("Independent reference clock conversion disagrees")
    for row in other["proper_state_difference_terms"]:
        left = (scaling.A**-4*scaling.ETA**row["eta_power"]).subs(
            scaling.ETA, sp.sqrt(2*scaling.T/scaling.A))
        right = (2**sp.Rational(row["two_power"])*scaling.A**sp.Rational(row["A_power"])
                 *scaling.T**sp.Rational(row["t_power"]))
        if sp.simplify(left-right) != 0:
            raise ValueError("Independent proper-time remainder exponent disagrees")
    for name, degree in (("constant_mean", 0), ("linear_mean", 1), ("restricted_domain_mean", -1)):
        observed = scaling.coincidence(scaling.point_split_difference((scaling.ETA*scaling.ETAP)**degree))
        expected = sp.Rational(other[name]["coefficient"])*scaling.ETA**sp.Rational(
            other[name]["eta_power"])/scaling.A**4
        if sp.simplify(observed-expected) != 0:
            raise ValueError("Independent coherent scaling control disagrees")
    result["independent_rational_scaling"] = other
    return result


def bounded_example():
    jets = bounds.JetBounds(1, 0, 0, 1)
    couplings = bounds.Couplings(a=1, kappa=1, b=1, ell=0, radiation_c=3, hbar=1)
    result = bounds.certify_interval(jets, couplings, "1/100")
    exact_error = independent.error_at("1/100", m0=1, m1=0, m2=0,
                                      a=1, kappa=1, b=1, ell=0, radiation_c=3)
    if sp.Rational(result["maximum_error"]) != sp.Rational(exact_error):
        raise ValueError("Independent rational residual bound disagrees")
    eta = sp.Symbol("eta", positive=True)
    polynomial = bounds.error_polynomial(jets, couplings, eta)
    if any(coefficient < 0 for coefficient in sp.Poly(polynomial, eta).all_coeffs()):
        raise ValueError("Error polynomial is not coefficientwise nonnegative")
    try:
        bounds.certify_interval(jets, couplings, "1/50")
    except ValueError:
        result["oversized_cutoff_1_over_50_rejected"] = True
    else:
        raise ValueError("Oversized cutoff control unexpectedly passed")
    result["coherent_flat_mean"] = "chi=1; F=1, f0=1, f1=f2=0 at all spatial points"
    result["jet_bounds_derived_for_this_state"] = True
    result["positive_coefficient_error_polynomial"] = str(polynomial)
    result["validated_residual_lower_bound_enclosure"] = validated.enclosure(
        sp.sympify(result["residual_lower_bound"]), "0.00021662869", "0.00021662870")
    result["dimensionless_illustration_not_cosmological_parameter_fit"] = True
    return result


def build_report():
    prior_hash = prior_checks()
    source_paths = sorted(ROOT.glob("src/p8a_asymptotics/*.py"))+sorted(ROOT.glob("tests/*.py"))
    source_paths += sorted(ROOT.glob("*.md"))+sorted(ROOT.glob("notes/*.md"))
    validated.positive(1/(320*sp.pi**2))
    return {
        "schema": 1, "claim": "P8-A.4", "date": "2026-09-05",
        "status": "WHOLE_PATCH_EXACT_RADIATION_SEE_OBSTRUCTION_DERIVED; BACKREACTED_APPLICATION_OPEN",
        "prior_A3_sha256": prior_hash,
        "source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in source_paths},
        "formulation": "FORMULATION.md", "written_proof": "notes/proof.md",
        "source_dictionary": "notes/sources.md",
        "scope": {
            "background": "entire (0,infinity)_eta x R3, a=A*eta, A>0",
            "field": "real free massless minimally coupled scalar",
            "state": "any state with a microlocal Hadamard two-point distribution on the whole patch",
            "all_higher_n_point_or_Weyl_characteristic_regularity_assumed": False,
            "quasifree_homogeneous_isotropic_finite_energy_or_tempered_data_assumed": False,
            "physical_state_or_metric_extension_through_eta_zero_assumed": False,
            "smooth_flat_bisolution_extension_is_derived": True,
            "prescription": "unchanged pinned A.3 massless locally covariant conserved matter prescription",
            "SEE": "b*G_FK+ell*g_FK+alpha*I+beta*J=-kappa*(T_omega+T_rad)",
            "couplings": "finite constants; b,kappa>0; ell,alpha,beta arbitrary; I=J=0 on this patch",
            "additional_sources": "only ordinary homogeneous comoving radiation rho=C/a^4, p=rho/3, finite C>=0",
            "other_traceful_or_quantum_sources_included": False,
            "limit": "pointwise in space and locally spatially uniform for each fixed state",
            "uniform_over_states_rate_or_positive_onset_time_established": False,
            "all_state_pointwise_nonnegative_EED_at_all_times_established": False,
            "whole_patch_exact_SEE_incompatibility_established": True,
            "finite_slab_SEE_incompatibility_established": False,
            "new_incompleteness_theorem_established": False,
        },
        "two_variable_Cauchy_benchmark": checked_extension(),
        "EED_scaling_and_SEE_derivation": checked_scaling(),
        "state_specific_quantitative_residual_example": bounded_example(),
        "precision_bits": validated.PRECISION,
        "verification_boundary": [
            "the general Hadamard smooth-difference and smooth wave Cauchy statements are written primary-source inputs, not finite arithmetic proofs",
            "the noncompact-data, joint-bisolution extension and limit argument are supplied in notes/proof.md",
            "independent exact polynomial and exponent calculations check identities and examples, not arbitrary state's data bounds",
            "the absolute reference EED is imported only after hash-pinned A.3/A.2/A.1 replay",
        ],
        "not_established": [
            "a no-go theorem on a finite slab bounded away from eta=0 or on a smaller spatial domain",
            "a no-go theorem with arbitrary traceful extra sources, time-dependent couplings or additional fields",
            "exclusion of a controlled backreacted radiation-like metric or a general FLRW SEE solution",
            "uniform state-independent pointwise positivity or an actual bound on arbitrary state's Cauchy data",
            "validity of semiclassical gravity at arbitrarily high curvature",
            "a new singularity theorem, realistic-field cosmological QEI calibration, or full P8(a) completion",
        ],
        "next_physical_gate": "an SEE-compatible backreacted testbed with quantitatively controlled QSEI/reference changes and relevant geodesic coverage",
    }


def validate_report(expected, actual):
    if expected != actual:
        raise ValueError("Radiation asymptotics certificate differs from exact and validated replay")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    actual = build_report()
    if args.check:
        validate_report(json.loads(REPORT.read_text()), actual)
        print("P8(a) A.4: whole-patch exact-radiation SEE obstruction replay passed; backreacted application OPEN")
    else:
        print(json.dumps(actual, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

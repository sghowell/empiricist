"""Read-only replay of the radiation-reference stress and absolute QSEI."""

import argparse
import hashlib
import json
from pathlib import Path

import sympy as sp
from p8a_radiation import independent as prior_independent
from p8a_radiation import validated
from p8a_radiation import verify as prior

from . import bridge, independent, stress

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT/"certificates"/"radiation-reference.json"
PRIOR_SHA = "1a7369c03a25787c04fac0bf38189206e5331e43d3e48306a9ebb187763e9ed2"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prior_checks():
    if sha(prior.REPORT) != PRIOR_SHA:
        raise ValueError("Pinned A.2 certificate changed")
    prior.validate_report(json.loads(prior.REPORT.read_text()), prior.build_report())
    return PRIOR_SHA


def verified_residuals(result):
    for name, value in result["residuals"].items():
        if sp.simplify(value) != 0:
            raise ValueError(f"Nonzero reference derivation residual: {name}")
    result["residuals"] = dict.fromkeys(result["residuals"], "0")
    return result


def integral_expression(pair):
    return sp.Rational(pair[0])+sp.Rational(pair[1])*sp.log(2)


def checked_source_stress():
    result = independent.source_stress()
    actual = stress.reference_stress()
    for source_key, target_key in (("proper_density_coefficient", "rho"),
                                   ("proper_pressure_coefficient", "pressure"),
                                   ("FK_trace_coefficient", "trace_FK"),
                                   ("FK_EED_coefficient", "EED_FK")):
        normalized = sp.simplify(actual[target_key]*sp.pi**2*stress.T**4/stress.HBAR)
        if normalized != sp.Rational(result[source_key]):
            raise ValueError("Independent conformal/proper stress routes disagree")
    if sp.Rational(result["reference_credit_in_hbar_over_16pi2_units"]) != bridge.REFERENCE_CREDIT:
        raise ValueError("Independent EED has the wrong QSEI normalization")
    return result


def benchmark(coefficients=(4, -12, 13, -6, 1)):
    result = independent.benchmark(coefficients)
    old = prior_independent.replay(coefficients)
    rows = result["exact_integrals"]
    if rows["difference"] != old["exact_integrals"]["proper_curved_norm"]:
        raise ValueError("Independent new and pinned A.2 difference calculations disagree")
    h = sum(sp.Rational(value)*bridge.T**power for power, value in enumerate(coefficients))
    bridge.endpoint_check(h, 1, 2)
    symbolic = sp.simplify(sp.integrate(bridge.absolute_density(h), (bridge.T, 1, 2)))
    absolute = integral_expression(rows["absolute"])
    difference = integral_expression(rows["difference"])
    flat = integral_expression(rows["flat"])
    if sp.simplify(symbolic-absolute) != 0:
        raise ValueError("SymPy and independent rational absolute integrals disagree")
    for quantity in (absolute, difference-absolute, flat-difference):
        validated.positive(quantity)
    result["validated_ordering"] = "0 < absolute < difference < flat"
    return result


def build_report():
    prior_hash = prior_checks()
    source_paths = sorted(ROOT.glob("src/p8a_reference/*.py"))+sorted(ROOT.glob("tests/*.py"))
    source_paths += sorted(ROOT.glob("*.md"))+sorted(ROOT.glob("notes/*.md"))
    first = benchmark()
    first["validated_absolute_enclosure"] = validated.enclosure(
        integral_expression(first["exact_integrals"]["absolute"]), "0.7965820", "0.7965821")
    first["validated_reference_credit_enclosure"] = validated.enclosure(
        integral_expression(first["exact_integrals"]["reference_credit"]), "0.0000010885", "0.0000010886")
    for coefficient in (bridge.REFERENCE_CREDIT, bridge.HARDY_CREDIT, sp.Rational(17, 8),
                        sp.Rational(161, 1280)):
        validated.positive(coefficient)
    return {
        "schema": 1, "claim": "P8-A.3", "date": "2026-09-05",
        "status": "RADIATION_REFERENCE_EED_AND_ABSOLUTE_QSEI_DERIVED; SEE_APPLICATION_OPEN",
        "prior_A2_sha256": prior_hash,
        "source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in source_paths},
        "formulation": "FORMULATION.md", "written_proof": "notes/derivation.md",
        "source_dictionary": "notes/sources.md",
        "scope": {
            "field": "free real massless minimally coupled scalar",
            "background": "fixed spatially flat 4D radiation FLRW, a=A*eta, eta>0",
            "reference_state": "Minkowski vacuum transported with phi=chi/a; zero occupations in the specified radiation modes",
            "target_state": "any Hadamard state on the fixed patch",
            "prescription": "locally covariant conservation-preserving FK Hadamard prescription; standard massless scaling/analyticity class",
            "usual_finite_stress_ambiguities_vanish_on_this_patch": True,
            "arbitrary_dimensionful_lambda_g_or_gamma_G_included_in_matter_stress": False,
            "independent_gravitational_couplings": "UNSPECIFIED; their displayed EED shift must be retained in a total source or SEE",
            "reference_EED_computed_not_set_to_zero": True,
            "absolute_QSEI_derived_for_this_prescription_and_background": True,
            "small_sampling_duration_assumed": False,
            "reference_state_SEE_solution_established": False,
            "geodesic_coverage": "comoving lines; all normals only to constant-cosmic-time FLRW slices",
        },
        "sign_and_operator_dictionary": verified_residuals(stress.convention_identities()),
        "reference_stress_and_state_derivation": verified_residuals(stress.identities()),
        "independent_rational_conformal_stress": checked_source_stress(),
        "absolute_QSEI_derivation": verified_residuals(bridge.identities()),
        "independent_rational_sample": first,
        "second_independent_rational_sample": benchmark((4, -8, 1, 7, -5, 1)),
        "precision_bits": validated.PRECISION,
        "verification_boundary": [
            "QFT Hadamard, conformal transformation and renormalization theorems are cited written-proof inputs, not proved by arithmetic replay",
            "the spectral difference inequality is imported only after pinned A.2 and A.1 replay",
            "symbolic/independent checks verify source specialization, signs, mode cancellation, constants and integral identities",
        ],
        "not_established": [
            "self-consistency of this metric with the reference field alone or field plus classical traceless radiation",
            "a new SEE solution for any other target state or unspecified additional sources",
            "a Ricci inequality without imposing the correctly matched SEE",
            "general FLRW, tilted observers or all normals of arbitrary Cauchy surfaces",
            "massive, nonminimal, interacting or additional-field absolute bounds",
            "an optimal QEI over states or new cosmological incompleteness theorem",
            "a realistic-field cosmological calibration, exclusion of P8(b) bounces or full P8(a) completion",
        ],
    }


def validate_report(expected, actual):
    if expected != actual:
        raise ValueError("Radiation reference certificate differs from exact and validated replay")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    actual = build_report()
    if args.check:
        validate_report(json.loads(REPORT.read_text()), actual)
        print("P8(a) A.3: positive reference EED and fixed-radiation absolute QSEI replay passed; SEE application OPEN")
    else:
        print(json.dumps(actual, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

"""Read-only exact/validated replay of P8(a)'s conditional focusing checkpoint."""

import argparse
import hashlib
import json
from pathlib import Path

import sympy as sp

from . import focusing, geometry, independent, partition, validated

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT/"certificates"/"focusing.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def polynomial_coefficients(expression):
    poly = sp.Poly(expression, partition.Z)
    return [str(poly.nth(i)) for i in range(3)]


def require_zero(residuals):
    for name, value in residuals.items():
        if sp.simplify(value) != 0:
            raise ValueError(f"Nonzero exact residual: {name}")
    return {name: "0" for name in residuals}


def independent_checks():
    result = independent.replay()
    expected_initial = polynomial_coefficients(
        partition.local_bilinear(partition.P, partition.P)/partition.A**3)
    if result["initial_localized_norm"] != expected_initial:
        raise ValueError("Independent initial localization disagrees")
    basis = (partition.P, *focusing.BASIS)
    expected_gram = [[polynomial_coefficients(partition.tail_bilinear(left, right))
                      for right in basis] for left in basis]
    if result["tail_basis_gram"] != expected_gram:
        raise ValueError("Independent tail Gram integration disagrees")
    return result


def build_report():
    data = focusing.optimize()
    geom = geometry.identities()
    geom["residuals"] = require_zero(geom["residuals"])
    sources = sorted(ROOT.glob("src/p8a/*.py"))+sorted(ROOT.glob("tests/*.py"))
    sources += sorted(ROOT.glob("*.md"))+sorted(ROOT.glob("notes/*.md"))
    gram = data["gram"]
    improvement = data["improvement"]
    minimum = data["optimized_threshold"]
    baseline = data["cubic_threshold"]
    for expression in (gram[0, 0], gram.det(), improvement, sp.Rational(9, 2)-minimum,
                       baseline-sp.Rational(9, 2), partition.tail_remainder(partition.P, 5)):
        validated.positive(expression)
    return {
        "schema": 1,
        "claim": "P8-A.1",
        "date": "2026-09-05",
        "status": "CONDITIONAL_LOCAL_QEI_FOCUSING_OPTIMIZATION; PHYSICAL_APPLICATION_OPEN",
        "source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in sources},
        "hypotheses": "FORMULATION.md; assumed local Ricci/QEI bound plus initial pointwise Ricci bound",
        "written_proof": "notes/focusing.md",
        "parameters": {"dimension": 4, "T0_over_tau": "1", "tau0_over_tau": "1/4",
                       "extended_geodesic_domain_over_tau": ["-1/2", "1"],
                       "partition_ratio": str(partition.R), "Q2_over_tau_squared": str(focusing.ALPHA),
                       "Q0_times_tau_squared": str(focusing.BETA),
                       "rho0_times_tau_squared": str(focusing.ZETA),
                       "z": "pi^2", "units": "all thresholds below are multiplied by tau",
                       "physical_calibration": "NONE; dimensionless conditional demonstration"},
        "support_coverage": {
            "interior_width_over_allowed_window": str(partition.validate_coverage()),
            "first_width_over_allowed_window": str(2*(1-partition.R)/(1+partition.R)),
            "first_window_over_tau": ["-5/16", "9/16"],
            "strict_containment": True,
            "bad_ratio_one_half_width_over_window": str(partition.coverage_ratio(sp.Rational(1, 2))),
        },
        "partition_and_geometric_series_residuals": require_zero(partition.identities()),
        "independent_FLINT_replay": independent_checks(),
        "focusing_and_field_dictionary": geom,
        "finite_family_optimization": {
            "tail": str(focusing.trial()),
            "coefficient_order": [str(value) for value in focusing.COEFFICIENTS],
            "gram": [[str(gram[i, j]) for j in range(2)] for i in range(2)],
            "linear_vector": [str(value) for value in data["linear"]],
            "gram_leading_minor_positive": True, "gram_determinant_positive": True,
            "optimal_coefficients": [str(value) for value in data["optimum"]],
            "cubic_threshold_exact": str(baseline),
            "optimized_threshold_exact": str(minimum),
            "improvement_exact": str(improvement),
            "residuals": require_zero(data["residuals"]),
            "optimality_scope": "unique minimum in the frozen two-coefficient family only",
        },
        "validated_enclosures": {
            "method": "outward Arb rational-function evaluation of pi^2",
            "precision_bits": validated.PRECISION,
            "cubic_threshold": validated.enclosure(baseline, "4.8747718", "4.8747719"),
            "optimized_threshold": validated.enclosure(minimum, "4.4445507", "4.4445508"),
            "improvement_percent": validated.enclosure(100*improvement/baseline, "8.825", "8.826"),
            "coefficient_0": validated.enclosure(data["optimum"][0], "-0.2684398", "-0.2684397"),
            "coefficient_1": validated.enclosure(data["optimum"][1], "-3.9828158", "-3.9828157"),
        },
        "separating_contraction_example": {
            "minus_K_times_tau": "9/2", "optimized_test_certifies_focusing": True,
            "cubic_test_certifies_focusing": False, "initial_SEC_classical_threshold_times_tau": "12",
            "failure_of_a_test_implies_completeness": False,
        },
        "not_established": [
            "a derived local QSEI validity duration in curved spacetime",
            "a realistic quantum-field or state calibration",
            "a cosmological application in a verified semiclassical regime",
            "a singularity theorem assuming only QEIs with no initial pointwise hypothesis",
            "the global optimum over all test functions, cutoffs or partitions",
            "a proof-assistant formalization of global Lorentzian causal geometry",
            "a worldvolume, null or nonminimal-field extension",
            "an exclusion of the P8(b) bounce witnesses",
            "full P8(a) or P8 completion",
        ],
    }


def validate_report(expected, actual):
    if expected != actual:
        raise ValueError("P8(a) focusing certificate differs from exact and validated replay")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    actual = build_report()
    if args.check:
        validate_report(json.loads(REPORT.read_text()), actual)
        print("P8(a) A.1: conditional local-QEI focusing optimization replay passed; physical application OPEN")
    else:
        print(json.dumps(actual, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

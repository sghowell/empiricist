"""Read-only replay of the fixed-radiation difference-QSEI checkpoint."""

import argparse
import hashlib
import json
from pathlib import Path

import sympy as sp
from p8a import verify as prior

from . import functional, independent, radiation, validated, windows

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT/"certificates"/"radiation-qsei.json"
PRIOR_SHA = "f719c98068848003e296260d3ff6b03d32acad40662b9c9980f61c39175f209e"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prior_checks():
    if sha(prior.REPORT) != PRIOR_SHA:
        raise ValueError("Pinned A.1 certificate changed")
    prior.validate_report(json.loads(prior.REPORT.read_text()), prior.build_report())
    return PRIOR_SHA


def verified_residuals(result):
    for name, value in result["residuals"].items():
        if sp.simplify(value) != 0:
            raise ValueError(f"Nonzero derivation residual: {name}")
    result["residuals"] = dict.fromkeys(result["residuals"], "0")
    return result


def integral_expression(row):
    return sp.Rational(row[0])+sp.Rational(row[1])*sp.log(2)


def benchmark():
    replay = independent.replay()
    t = functional.T
    h = (t-1)**2*(2-t)**2
    symbolic = sp.simplify(sp.integrate(functional.proper_density(h), (t, 1, 2)))
    exact = integral_expression(replay["exact_integrals"]["proper_curved_norm"])
    if sp.simplify(symbolic-exact) != 0:
        raise ValueError("Independent FLINT and SymPy integrals disagree")
    validated.positive(exact)
    validated.positive(sp.Rational(4, 5)-exact)
    replay["validated_normalized_curved_norm"] = validated.enclosure(exact, "0.7965831", "0.7965832")
    replay["positive_and_strictly_below_flat_norm"] = True
    return replay


def build_report():
    old = prior_checks()
    source_paths = sorted(ROOT.glob("src/p8a_radiation/*.py"))+sorted(ROOT.glob("tests/*.py"))
    source_paths += sorted(ROOT.glob("*.md"))+sorted(ROOT.glob("notes/*.md"))
    bridge = windows.reference_bridge(1, sp.Rational(1, 2))
    multiplier = bridge["absolute_QSEI_multiplier"]
    bridge["absolute_QSEI_multiplier"] = str(multiplier)
    bridge["validated_multiplier"] = validated.enclosure(multiplier, "1.0011485", "1.0011487")
    conditional_geometry = windows.geometric_bridge(reference_beta=1, t_min=1)
    conditional_geometry = {key: str(value) if isinstance(value, sp.Basic) else value
                            for key, value in conditional_geometry.items()}
    return {
        "schema": 1, "claim": "P8-A.2", "date": "2026-09-05",
        "status": "RADIATION_DIFFERENCE_QSEI_DERIVED; ABSOLUTE_REFERENCE_AND_SEE_APPLICATION_OPEN",
        "prior_A1_sha256": old,
        "source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in source_paths},
        "formulation": "FORMULATION.md", "written_proof": "notes/derivation.md",
        "source_dictionary": "notes/sources.md",
        "fixed_background_and_field_map": verified_residuals(radiation.identities()),
        "difference_QSEI_derivation": verified_residuals(functional.identities()),
        "scope": {
            "field": "free real massless minimally coupled scalar",
            "state_of_interest": "arbitrary Hadamard state on the fixed radiation patch",
            "sampling": "real C_c^infinity(t>0), extended to H2_0 on compact intervals with positive lower endpoint",
            "required_endpoint_jets": "h=hdot=0 at both endpoints",
            "assumed_small_duration_for_difference_bound": False,
            "renormalized_reference_EED": "RETAINED, NOT EVALUATED OR SET TO ZERO",
            "absolute_QSEI_is_unconditionally_derived": False,
            "self_consistent_SEE_solution_is_established": False,
        },
        "independent_FLINT_benchmark": benchmark(),
        "second_independent_FLINT_benchmark": independent.replay((4, -8, 1, 7, -5, 1)),
        "reference_state_conditional_bridge": {
            "dimensionless_reference_credit": str(windows.CREDIT),
            "all_duration_C1_sufficient_if_separately_proved": "E_reference(t) >= -111*hbar/(4096*pi^2*t^4)",
            "general_multiplier": "1+max(0,beta-111/256)*(L/t_min)^4/pi^4",
            "support": "(t_c-L/2,t_c+L/2), 0<L<2*t_c, t_min=t_c-L/2",
            "Poincare_domain": "H2_0 of this proper-time interval; h and hdot have zero traces",
            "example_with_UNESTABLISHED_beta_1": bridge,
            "conditional_geometric_constants_beta_1_tmin_1_kappa_hbar_1": conditional_geometry,
        },
        "precision_bits": validated.PRECISION,
        "not_established": [
            "a value or bound for the actual renormalized reference EED",
            "an unconditional absolute QSEI or general-background T-regularity",
            "self-consistency of the radiation metric with the scalar field SEE",
            "all normal geodesics of arbitrary Cauchy surfaces or other metrics",
            "a new cosmological incompleteness theorem or a realistic-field calibration",
            "an optimal QEI over states or sharp sampling-duration threshold",
            "massive, nonminimal, interacting or additional field extensions",
            "an exclusion of P8(b) bounces or full P8(a) completion",
        ],
    }


def validate_report(expected, actual):
    if expected != actual:
        raise ValueError("Radiation QSEI certificate differs from exact and validated replay")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    actual = build_report()
    if args.check:
        validate_report(json.loads(REPORT.read_text()), actual)
        print("P8(a) A.2: exact radiation difference-QSEI replay passed; reference EED and SEE application OPEN")
    else:
        print(json.dumps(actual, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

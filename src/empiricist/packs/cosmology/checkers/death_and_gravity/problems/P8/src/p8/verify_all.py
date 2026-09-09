"""Replay the complete scoped P8(b) certificate chain, without writes/network.

The analytic lemmas listed in the certificates are written proofs, not
kernel-checked theorems. Exact algebra and outward-rounded inequalities
are recomputed; altered reports or source hashes fail closed.
"""

import argparse
import hashlib
import json
import sys
from functools import cache
from pathlib import Path

import sympy as sp
from flint import __version__ as flint_version

from . import (
    a25_certificate,
    adm,
    candidate_cert,
    coupled,
    covariant,
    exclusions,
    gamma,
    independent_sigma,
    quadratic,
    regressions,
    strong_gravity,
    tensor,
    tilted_hessian,
    verify,
)
from . import jets as j

ROOT = Path(__file__).resolve().parents[2]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


@cache
def derivation_report():
    groups = {"ADM": adm.coefficients()["residuals"],
              "tensor": tensor.derive()["residuals"],
              "scalar": quadratic.derive()["residuals"],
              "coupled": coupled.unreduced()["residuals"],
              "gamma_Hamiltonian": gamma.hamiltonian()["residuals"],
              "gamma_principal": gamma.principal_chart()["residuals"],
              "gamma_without_J_division": gamma.auxiliary_chart()["residuals"],
              "CPS16": regressions.CPS16_dictionary(),
              "luminal_matter_interface": regressions.luminal_interface(),
              "A25_reconstruction": regressions.A25_reconstruction()["residuals"],
              "strong_gravity": strong_gravity.derive()["residuals"]}
    tilted = tilted_hessian.derive()
    groups["tilted_covariant_degeneracy"] = {"determinant": tilted["tilted_scalar_block_determinant"]}
    source = regressions.A25_dictionary()
    groups["A25_dictionary"] = {key: source[key] for key in ("GT", "FT", "Theta", "Lambda", "background_EN", "background_Ea")}
    independently = independent_sigma.A25_sigma()
    g, a1 = (sp.Function(name)(j.t) for name in ("g1", "a1"))
    theta = j.H*(1+4*a1+g)+sp.diff(g, j.t)
    discrepancy = -2*g*(j.dt(theta+sp.diff(g, j.t))+3*j.H*(theta+sp.diff(g, j.t)))
    groups["A25_independent_Sigma"] = {"auxiliary_remainder": independently["auxiliary_remainder"],
                                        "agreement": sp.cancel(independently["Sigma"]-source["Sigma_derived"]),
                                        "discrepancy_formula": sp.cancel(source["Sigma"]-discrepancy)}
    for name, values in groups.items():
        if any(value != 0 for value in values.values()):
            raise ValueError(f"Nonzero exact residual in {name}: {values}")
    if source["Sigma"] == 0:
        raise ValueError("The source-Sigma negative control disappeared")
    coordinate_checks = {**covariant.contraction_residuals(),
                         "F2_R_boundary": covariant.curvature_ibp_residual()}
    if not all(coordinate_checks.values()):
        raise ValueError("Coordinate covariant contraction/boundary failed")
    return {"schema": 1, "claim": "P8-1",
            "scope": "Covariant action through linear background, principal matrices and regular gamma charts; not full nonlinear Dirac formalization",
            "exact_residuals": {name: {key: str(value) for key, value in values.items()}
                                for name, values in groups.items()},
            "coordinate_covariant_checks": coordinate_checks,
            "unitary_metric_Hessian_minor": str(tilted["unitary_K_minor"]),
            "A25_Sigma_derived_minus_printed": str(source["Sigma"]),
            "A25_corrected_F": str(regressions.A25_reconstruction()["F"]),
            "strong_gravity": {key: str(value) for key, value in strong_gravity.derive().items() if key != "residuals"},
            "written_proofs": ["notes/s1-derived-action.md", "notes/s2-benchmarks.md"]}


@cache
def build_reports():
    verify.check_certificate()  # retain and independently replay the original S0 anchor
    reports = {"s1-derived-action.json": derivation_report(),
               "a25-regression.json": a25_certificate.build()}
    for label in ("C", "D", "CD_matter"):
        reports[f"witness-{label}.json"] = candidate_cert.build(label)
    algebra = exclusions.algebra()
    if any(value != 0 for value in algebra["residuals"].values()):
        raise ValueError("An exclusion identity failed")
    sources = sorted((ROOT/"src"/"p8").glob("*.py"))
    sources += sorted((ROOT/"tests").glob("*.py"))
    sources += [ROOT/"FORMULATION.md", ROOT/"README.md"]
    sources += sorted((ROOT/"notes").glob("*.md"))
    reports["classification.json"] = {
        "schema": 1, "claim": "P8-3", "date": "2026-09-04",
        "environment": {"python": sys.version.split()[0], "sympy": sp.__version__,
                        "python_flint": flint_version,
                        "uv_lock_sha256": hashlib.sha256((ROOT.parents[1]/"uv.lock").read_bytes()).hexdigest()},
        "scope": "All 32 M0/M1 sector-row verdicts in the frozen 16-row covariant function-group ladder, with all-time regular linear principal health and conventional tube tails",
        "rows": exclusions.rows(), "minimal_supports": {"M0": ["C", "D"], "M1": ["CD"]},
        "counts": {"M0": {"E": 12, "N": 4}, "M1": {"E": 4, "N": 12}},
        "exclusion_exact_residuals": {key: str(value) for key, value in algebra["residuals"].items()},
        "dependency_semantic_sha256": {name: digest(report) for name, report in reports.items()},
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
        "analytic_obligations": {"positive_numerator_component_no_go": "notes/s3-classification.md sections 1-3",
                                 "regular_ODE_and_principal_charts": "notes/s1-derived-action.md section 3",
                                 "domain_canonical_tails_and_completeness": "notes/s2-rational-witnesses.md sections 3-4",
                                 "benchmark_infinite_tails": "notes/s2-benchmarks.md section 2"},
        "proof_level": "Exact SymPy/FLINT algebra, rational Sturm and Bernstein bounds, Arb core enclosures, plus explicit written analytic lemmas; not FORMALIZED",
        "not_established": ["P8(a)", "nonlinear or BKL stability", "all-wavelength Hamiltonian positivity",
                            "a strong-coupling hierarchy", "UV positivity or completion", "observational viability",
                            "classification outside the frozen ladder/matter/frame/tail contract"],
    }
    return reports


def validate_report(name, expected, current):
    if expected != current:
        raise ValueError(f"{name}: certificate differs from exact replay; inspect the changed evidence or inputs")


def check_reports(directory=ROOT/"certificates"):
    reports = build_reports()
    for name, current in reports.items():
        validate_report(name, json.loads((Path(directory)/name).read_text()), current)
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--report", help="print just one named JSON artifact")
    args = parser.parse_args()
    if args.check:
        reports = check_reports()
        print(f"P8(b): S0 plus {len(reports)} certificate replays passed; 32 scoped sector-row verdicts")
    else:
        reports = build_reports()
        print(json.dumps(reports[args.report] if args.report else reports, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

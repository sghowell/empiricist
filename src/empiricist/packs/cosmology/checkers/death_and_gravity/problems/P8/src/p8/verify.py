"""Replay the S0 exact-algebra certificate. No network, writes, or sampling.

Run with PYTHONPATH=problems/P8/src python -m p8.verify --check.
Without --check, print a fresh JSON report to stdout for review.
"""

import argparse
import hashlib
import json
from pathlib import Path

import sympy as sp

from . import benchmark, horndeski, matter

CERTIFICATE = Path(__file__).resolve().parents[2] / "certificates" / "s0-identities.json"


def report():
    h = horndeski.derive()
    m = matter.luminal_identities()
    relation = matter.exceptional_relation()
    printed = matter.exceptional_relation(printed_a25_D=True)
    independent = horndeski.independent_polynomial_check()
    exact_zeros = {**h["residuals"], **m, "exceptional_relation": relation["residual"],
                   "A1_zero_specialization": relation["luminal_tensor_residual"]}
    if not all(value == 0 for value in exact_zeros.values()):
        raise RuntimeError(f"Exact identity failed: {exact_zeros}")
    if not all(independent.values()) or printed["residual"] == 0:
        raise RuntimeError("Independent check or source-discrepancy negative control failed")
    jet = benchmark.bounce_jet()
    source_hashes = {
        Path(module.__file__).name: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
        for module in (horndeski, matter, benchmark)
    }
    return {
        "schema": 1,
        "claim": "P8-0",
        "scope": "Exact source-action algebra and local benchmark jets only; no covariant or global bounce theorem",
        "domain": ["a > 0", "k2 > 0", "Theta != 0 for quotient chart",
                   "matter implication additionally Q > 0 and chi_dot != 0",
                   "exceptional dictionary additionally X > 0, GT != 0, 3*X*A1-4*F2 != 0"],
        "sources": {"action": "arXiv:1105.5723v4 (4.24)",
                    "matter": "arXiv:2501.09985v2 (9c),(10c,d,h); D from arXiv:2011.14912v1 (8a)",
                    "benchmark": "arXiv:2501.09985v2 (28),(40),(42),(43),(45)"},
        "source_sha256": source_hashes,
        "horndeski": {key: str(h[key]) for key in ("raw", "boundary", "GS", "FS", "xi")},
        "exact_residuals": {key: str(value) for key, value in exact_zeros.items()},
        "independent_flint": independent,
        "exceptional_A3": str(relation["solution"]),
        "printed_A25_D_A3_mismatch": str(sp.factor(printed["residual"])),
        "benchmark_jet": {key: str(value) for key, value in jet.items()},
        "benchmark_Hdot0_pinned": str(jet["Hdot0"].subs(benchmark.PARAMETERS)),
        "not_established": ["covariant action-to-coefficient derivation", "gamma-crossing regularity",
                            "full background reconstruction", "all-time scalar/tensor bounds",
                            "any ladder row verdict", "UV positivity or weak coupling"],
    }


def check_certificate(path=CERTIFICATE):
    expected = json.loads(Path(path).read_text())
    current = report()
    if current != expected:
        raise ValueError("Certificate differs from exact replay; inspect inputs, scope and source hashes")
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="replay and compare the stored certificate")
    args = parser.parse_args()
    if args.check:
        check_certificate()
        print("P8-0: exact certificate replay passed (source-level/local scope only)")
    else:
        print(json.dumps(report(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

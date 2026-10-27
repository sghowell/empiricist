"""The predicate verifier of the conjecture "k = 0 forces min_B p_B = 0" (M27b follow-up).

PASS: a valid exact k = 0 witness whose exact success vector has a zero entry (the
conjecture's prediction holds on it). FAIL: a valid exact k = 0 witness with all four exact
successes positive -- a counterexample, so a FAIL may refute the conjecture. ERROR for
anything else (malformed or off-field witness, k != 0): garbage must never refute.
"""
from __future__ import annotations

import json
from fractions import Fraction

from empiricist.domain.p3.exact import Alg, ExactWitness, witness_to_json
from empiricist.domain.p3.known_schemes import standard_bsm
from empiricist.ledger.models import Verdict
from empiricist.verifiers.p3_min_zero import check_k0_min_zero, two_branch_witness

F = Fraction


def _payload(w) -> dict:
    return {"witness": witness_to_json(w) if isinstance(w, ExactWitness) else w}


def test_standard_bsm_passes_min_zero():
    w = ExactWitness.from_mesh(standard_bsm())
    res = check_k0_min_zero(_payload(w))
    assert res.verdict is Verdict.PASS, res.details
    assert res.details["p_min"] == [] and res.details["k"] == 0


def test_two_branch_counterexample_fails_with_all_four_at_one_quarter():
    res = check_k0_min_zero(_payload(two_branch_witness()))
    assert res.verdict is Verdict.FAIL, res.details
    assert res.details["n_modes"] == 8 and res.details["k"] == 0
    assert all(v == [[1, "1/4", "0"]] for v in res.details["success"].values())


def test_unequal_branches_also_fail():
    res = check_k0_min_zero(_payload(two_branch_witness(F(1, 4))))
    assert res.verdict is Verdict.FAIL, res.details
    succ = res.details["success"]
    assert succ["psi+"] == [[1, "1/16", "0"]] and succ["phi+"] == [[1, "9/16", "0"]]


def test_identity_interferometer_passes():
    rows = [[Alg.rational(int(i == j)) for j in range(4)] for i in range(4)]
    w = ExactWitness(4, 0, tuple(tuple(r) for r in rows), {})
    assert check_k0_min_zero(_payload(w)).verdict is Verdict.PASS


def test_k1_witnesses_are_errors_not_fails():
    """A positive-min k = 1 witness must not refute a k = 0 conjecture."""
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    data = json.loads((repo / "claims/evidence/ffbda7504b80609a.json").read_text())
    res = check_k0_min_zero({"witness": data["witness"]})
    assert res.verdict is Verdict.ERROR and "k = 0" in res.details["error"]


def test_malformed_and_non_isometric_witnesses_are_errors():
    assert check_k0_min_zero(None).verdict is Verdict.ERROR
    assert check_k0_min_zero({"witness": {"n_modes": 4}}).verdict is Verdict.ERROR
    bad = witness_to_json(two_branch_witness())
    bad["isometry"][0][0] = [[1, "1", "0"]]            # breaks orthonormality
    assert check_k0_min_zero({"witness": bad}).verdict is Verdict.ERROR


def test_payload_shared_with_the_exact_witness_verifier():
    """One evidence file serves both verifiers: p3_exact_witness PASSes the certified vector
    (1/4, 1/4, 1/4, 1/4) with every label identified; p3_k0_min_zero FAILs the conjecture."""
    from empiricist.domain.p3.exact import alg_from_json
    from empiricist.verifiers.p3_exact import P3ExactVerifier

    w = witness_to_json(two_branch_witness())
    claimed = {b: alg_from_json([[1, "1/4", "0"]]) for b in ("phi+", "phi-", "psi+", "psi-")}
    assert P3ExactVerifier().verify(w, claimed_success=claimed,
                                    require_all_identified=True).verdict is Verdict.PASS
    assert check_k0_min_zero({"witness": w, "claimed_success": {}}).verdict is Verdict.FAIL

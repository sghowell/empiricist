"""Exact-witness ingestion: an isometry witness with a machine-checked EXACT
success vector enters the ledger at CERTIFIED (spec section 4.1: a general
statement -- a lower bound on p*(k) -- carried by a model-independent,
machine-checkable certificate: the witness itself plus the certified exact
evaluator).

The float path (`domain/p3/ingest.py`) stays HEURISTIC because its engines
certify `leakage == 0` only to 1e-15. This path hands the verifier the witness
JSON itself (no caller-supplied PASS, no separately assembled object), requires
the exact verifier's current stamp before AND inside the transaction, and
records the claim through the same certification-gated `record_claimed_artifact`
the Lean and SOS paths use.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from blake3 import blake3

from empiricist.claims.materialize import materialize_after_ingest
from empiricist.domain.p3.exact import (
    Alg,
    ExactWitness,
    alg_from_json,
    alg_str,
    alg_to_json,
    witness_from_json,
    witness_to_json,
)
from empiricist.domain.p3.scheme import BELL_LABELS
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Artifact, Claim, EvidenceRow, Status, Verdict
from empiricist.search.p3_screen import screen_scheme
from empiricist.store import Store
from empiricist.verifiers.base import VerifierResult
from empiricist.verifiers.p3_exact import P3ExactVerifier
from empiricist.verifiers.p3_exact_goldens import p3_exact_suite_hash

P3_EXACT_WITNESS_PROBLEM_VERSION = "p3-exact-witness-v1"


def witness_json_from_scheme_json(scheme_json: dict, *, max_denom: int = 64) -> dict:
    """Screen a raw mesh scheme and lift it to an exact witness (its angles must
    lie on the pi/12 lattice and its ancilla amplitudes in the field).
    Raises ScreenReject / ExactUnsupported / ValueError accordingly."""
    return witness_to_json(ExactWitness.from_mesh(screen_scheme(scheme_json), max_denom=max_denom))


def _canonical_json(data: dict) -> bytes:
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _parse_claim(claimed_success: dict[str, Any]) -> dict[str, Alg]:
    if set(claimed_success) != set(BELL_LABELS):
        raise ValueError(
            f"claimed_success must name exactly {list(BELL_LABELS)}, "
            f"got {sorted(claimed_success)}"
        )
    return {b: alg_from_json(claimed_success[b]) for b in BELL_LABELS}


def _statement(
    k: int, m: int, n_in: int, success: dict[str, Alg], p_min: Alg, p_avg: Alg,
    all_identified: bool,
) -> str:
    vec = ", ".join(alg_str(success[b]) for b in BELL_LABELS)
    tail = " Every Bell state is identified with positive probability." if all_identified else ""
    return (
        "There is an unambiguous passive linear-optical Bell-measurement scheme with "
        f"k={k} ancilla photon(s) on {m} modes (an isometry over the 4 dual-rail input "
        f"modes and {n_in - 4} ancilla input mode(s)) whose exact per-Bell-state success "
        f"vector is (phi+, phi-, psi+, psi-) = ({vec}); hence the problem's p*({k}) = "
        f"sup min_B p_B is at least {alg_str(p_min)}, and the literature's average-success "
        f"analogue sup mean_B p_B is at least {alg_str(p_avg)} (exact evaluation in "
        f"Q(i)(sqrt d)).{tail}"
    )


def verify_and_ingest_exact_witness(
    ledger: Ledger,
    store: Store,
    *,
    witness_json: dict,
    claimed_success: dict[str, Any],
    require_all_identified: bool = False,
    title: str,
    run_id: str | None = None,
    claims_repo: Path | None = None,
) -> tuple[VerifierResult, Artifact | None]:
    """Check the exact claim against the witness JSON; ingest at CERTIFIED on PASS.

    Raises ValueError for a malformed claim, and PromotionIntegrityError when
    the exact verifier lacks a current stamp (fail closed, before verification).
    A malformed witness is a FAIL result (never raises), like any other miss.
    """
    claim_vec = _parse_claim(claimed_success)
    verifier = P3ExactVerifier()
    suite_hash = p3_exact_suite_hash()
    ledger.require_certification(
        verifier.name, verifier.version, verifier.binary_hash, suite_hash
    )
    result = verifier.verify(
        witness_json, claimed_success=claim_vec, require_all_identified=require_all_identified
    )
    if result.verdict is not Verdict.PASS:
        return result, None
    # Canonicalise through the parser so ignored keys never mint distinct artifacts.
    canonical_witness = witness_to_json(witness_from_json(witness_json))
    payload = {
        "checker": verifier.name,
        "witness": canonical_witness,
        "claimed_success": {b: alg_to_json(claim_vec[b]) for b in BELL_LABELS},
        "require_all_identified": bool(require_all_identified),
    }
    content = _canonical_json(payload)
    digest = store.put(content)
    evidence_run_id = run_id
    if evidence_run_id is not None:
        try:
            ledger.get_run(evidence_run_id)
        except KeyError:
            evidence_run_id = None
    k, m, n_in = result.details["k"], result.details["n_modes"], result.details["n_in"]
    p_min = alg_from_json(result.details["p_min"])
    p_avg = alg_from_json(result.details["p_avg"])
    art = Artifact(
        id=blake3(content).hexdigest(),
        kind="certificate",
        problem="P3",
        problem_version=P3_EXACT_WITNESS_PROBLEM_VERSION,
        title=title,
        content_path=digest,
        status=Status.CERTIFIED,
        run_id=evidence_run_id,
    )
    claim = Claim.create(
        artifact_id=art.id,
        problem=art.problem,
        problem_version=art.problem_version,
        statement=_statement(k, m, n_in, claim_vec, p_min, p_avg, result.details["all_identified"]),
        family=f"k{k}_m{m}_exact_witness",
        metric="exact_success_vector",
        scope={
            "k": k,
            "m": m,
            "n_in": n_in,
            "success": {b: alg_to_json(claim_vec[b]) for b in BELL_LABELS},
            "p_min": alg_to_json(p_min),
            "p_avg": alg_to_json(p_avg),
            "all_identified": bool(result.details["all_identified"]),
            "require_all_identified": bool(require_all_identified),
        },
    )
    evidence = EvidenceRow(
        artifact_id=art.id,
        claim_id=claim.id,
        run_id=evidence_run_id,
        verifier=verifier.name,
        verifier_version=verifier.version,
        binary_hash=verifier.binary_hash,
        golden_suite_hash=suite_hash,
        verdict=Verdict.PASS,
        details=dict(result.details),
    )
    stored = ledger.record_claimed_artifact(
        art, claim, evidence, expected_golden_suite_hash=suite_hash
    )
    materialize_after_ingest(ledger, store, stored.id, claims_repo=claims_repo)
    return result, stored


def ingest_exact_witness(
    ledger: Ledger,
    store: Store,
    *,
    witness_json: dict,
    claimed_success: dict[str, Any],
    require_all_identified: bool = False,
    title: str,
    run_id: str | None = None,
    claims_repo: Path | None = None,
) -> Artifact:
    """`verify_and_ingest_exact_witness` that refuses (ValueError) on non-PASS."""
    result, art = verify_and_ingest_exact_witness(
        ledger,
        store,
        witness_json=witness_json,
        claimed_success=claimed_success,
        require_all_identified=require_all_identified,
        title=title,
        run_id=run_id,
        claims_repo=claims_repo,
    )
    if art is None:
        raise ValueError(
            f"refusing to ingest a non-PASS exact witness: {result.details.get('detail')}"
        )
    return art

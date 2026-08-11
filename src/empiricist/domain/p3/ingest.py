"""Certified, claim-bound ingestion for P3 Bell-measurement schemes.

Raw scheme JSON is screened and independently evaluated inside this module;
callers cannot inject a precomputed PASS. A certified PASS is recorded
atomically with its canonical scoped claim and evidence. Because the two P3
engines are floating-point search evidence, accepted constructions remain
HEURISTIC rather than crossing an exact-certification boundary.
"""

from __future__ import annotations

import json

from blake3 import blake3

from empiricist.domain.p3.verify import AgreedResult, verify_scheme_agreed
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Artifact, Claim, EvidenceRow, Status, Verdict
from empiricist.search.p3_screen import screen_scheme
from empiricist.store import Store
from empiricist.verifiers.p3_goldens import p3_suite_hash
from empiricist.verifiers.p3_scheme import P3SchemeVerifier

P3_SCHEME_PROBLEM_VERSION = "p3-linear-optical-scheme-v1"


def _canonical_scheme_json(scheme_json: dict) -> bytes:
    """Canonical CAS content for `scheme_json` -- sorted-key, separator-tight,
    STRICT JSON (`allow_nan=False`: NaN/Infinity raise rather than silently
    emitting non-standard tokens that other parsers reject), so dict insertion
    order never perturbs the digest (same convention as
    `search.conjecture._canonical_conjecture_json`). Raises `ValueError`
    (never a raw `TypeError`) on anything `json.dumps` cannot serialize
    strictly: a caller error, not a schema violation the screen would have
    caught."""
    try:
        return json.dumps(
            scheme_json, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"scheme_json is not strictly JSON-serializable: {exc}") from exc


def ingest_scheme_artifact(
    ledger: Ledger,
    store: Store,
    *,
    scheme_json: dict,
    title: str,
    run_id: str | None = None,
    claimed_p_min: float | None = None,
    claimed_p_avg: float | None = None,
    claimed_max_leakage: float = 0.0,
) -> Artifact:
    """Verify raw model output and atomically ingest its exact checked claim.

    The caller cannot supply a precomputed PASS. Certification is checked
    before verification and again inside the artifact+claim+evidence
    transaction. Numeric P3 constructions remain HEURISTIC: the floating-point
    engines are strong search evidence, not an exact upper-bound certificate.
    """
    result, artifact = verify_and_ingest_scheme(
        ledger,
        store,
        scheme_json=scheme_json,
        title=title,
        run_id=run_id,
        claimed_p_min=claimed_p_min,
        claimed_p_avg=claimed_p_avg,
        claimed_max_leakage=claimed_max_leakage,
    )
    if result.verdict != "PASS" or artifact is None:
        raise ValueError(
            f"refusing to ingest a non-PASS scheme (verdict={result.verdict!r}): "
            f"{result.detail}"
        )
    return artifact


def verify_and_ingest_scheme(
    ledger: Ledger,
    store: Store,
    *,
    scheme_json: dict,
    title: str,
    run_id: str | None = None,
    claimed_p_min: float | None = None,
    claimed_p_avg: float | None = None,
    claimed_max_leakage: float = 0.0,
) -> tuple[AgreedResult, Artifact | None]:
    """Return the verifier result and ingest only when it is a certified PASS."""

    verifier = P3SchemeVerifier()
    suite_hash = p3_suite_hash()
    ledger.require_certification(
        verifier.name,
        verifier.version,
        verifier.binary_hash,
        suite_hash,
    )

    # Reconstruct the exact object being checked from the raw model output in
    # this function, so a caller cannot pair one scheme's PASS with another
    # scheme's bytes.
    scheme = screen_scheme(scheme_json)
    result = verify_scheme_agreed(
        scheme,
        claimed_p_min=claimed_p_min,
        claimed_p_avg=claimed_p_avg,
        claimed_max_leakage=claimed_max_leakage,
    )
    if result.verdict != "PASS":
        return result, None
    if result.report is None:  # defensive: PASS contract requires a report
        raise RuntimeError("P3 verifier returned PASS without a report")

    content = _canonical_scheme_json(scheme_json)
    art_id = blake3(content).hexdigest()
    content_path = store.put(content)
    evidence_run_id = run_id
    if evidence_run_id is not None:
        try:
            ledger.get_run(evidence_run_id)
        except KeyError:
            # Test/dry clients may not write run receipts. Real transports do.
            evidence_run_id = None
    art = Artifact(
        id=art_id,
        kind="construction",
        problem="P3",
        problem_version=P3_SCHEME_PROBLEM_VERSION,
        title=title,
        content_path=content_path,
        status=Status.HEURISTIC,
        run_id=evidence_run_id,
    )
    metric = ",".join(
        name
        for name, value in (
            ("p_min", claimed_p_min),
            ("p_avg", claimed_p_avg),
        )
        if value is not None
    ) or "leakage"
    claim = Claim.create(
        artifact_id=art.id,
        problem=art.problem,
        problem_version=art.problem_version,
        statement=(
            "This fixed linear-optical Bell-measurement scheme satisfies the "
            "declared success and leakage bounds."
        ),
        metric=metric,
        scope={
            "claimed_p_min": claimed_p_min,
            "claimed_p_avg": claimed_p_avg,
            "claimed_max_leakage": claimed_max_leakage,
        },
    )
    report = result.report
    evidence = EvidenceRow(
        artifact_id=art.id,
        claim_id=claim.id,
        run_id=evidence_run_id,
        verifier=verifier.name,
        verifier_version=verifier.version,
        binary_hash=verifier.binary_hash,
        golden_suite_hash=suite_hash,
        verdict=Verdict.PASS,
        details={
            "success_by_state": dict(report.success_by_state),
            "p_min": report.p_min,
            "p_avg": report.p_avg,
            "leakage": result.leakage,
            "detail": result.detail,
            "claimed_p_min": claimed_p_min,
            "claimed_p_avg": claimed_p_avg,
            "claimed_max_leakage": claimed_max_leakage,
        },
    )
    stored = ledger.record_claimed_artifact(
        art,
        claim,
        evidence,
        expected_golden_suite_hash=suite_hash,
    )
    return result, stored

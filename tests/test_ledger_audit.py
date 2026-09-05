"""Focused consistency checks for the deliberately small ledger/CAS audit."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from empiricist.ledger.audit import audit_ledger
from empiricist.ledger.db import UNKNOWN_BILLING_EXIT_CODE, Ledger
from empiricist.ledger.models import (
    Artifact,
    Certification,
    EvidenceRow,
    Run,
    Status,
    Verdict,
)
from empiricist.store import Store


@pytest.fixture()
def ledger(tmp_path: Path):
    value = Ledger(tmp_path / "ledger.db")
    yield value
    value.close()


@pytest.fixture()
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "store")


def _artifact(
    store: Store,
    content: bytes,
    *,
    status: Status = Status.HEURISTIC,
) -> Artifact:
    digest = store.put(content)
    return Artifact(
        id=digest,
        kind="construction",
        problem="P3",
        problem_version="p3-test-v1",
        title=content.decode(),
        content_path=digest,
        status=status,
    )


def _evidence(
    artifact_id: str,
    *,
    verdict: Verdict = Verdict.PASS,
    claim_id: str | None = None,
    run_id: str | None = None,
    golden_suite_hash: str | None = None,
) -> EvidenceRow:
    return EvidenceRow(
        artifact_id=artifact_id,
        claim_id=claim_id,
        run_id=run_id,
        verifier="p3-scheme",
        verifier_version="1",
        binary_hash="binary",
        golden_suite_hash=golden_suite_hash,
        verdict=verdict,
    )


def _certification(
    *,
    suite: str,
    verdict: Verdict = Verdict.PASS,
) -> Certification:
    return Certification(
        verifier="p3-scheme",
        verifier_version="1",
        binary_hash="binary",
        golden_suite_hash=suite,
        verdict=verdict,
    )


def test_audit_accepts_consistent_cas_evidence_links_and_certification(
    ledger: Ledger,
    store: Store,
) -> None:
    artifact = _artifact(store, b"healthy", status=Status.VERIFIED_N)
    ledger.add_artifact(artifact)
    ledger.start_run(Run(run_id="verify-1", move="VERIFY"))
    ledger.conn.execute(
        "INSERT INTO claims"
        " (id, artifact_id, problem, problem_version, statement, scope_json, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "claim-1",
            artifact.id,
            "P3",
            "p3-test-v1",
            "a fixed construction passes",
            "{}",
            "2026-07-24T00:00:00+00:00",
        ),
    )
    ledger.add_certification(_certification(suite="suite-current"))
    ledger.record_evidence(
        _evidence(
            artifact.id,
            claim_id="claim-1",
            run_id="verify-1",
            golden_suite_hash="suite-current",
        )
    )

    report = audit_ledger(ledger, store)

    assert report.ok
    assert report.issues == ()
    assert report.artifacts_checked == 1
    assert report.evidence_checked == 1


def test_audit_flags_cert_gated_elevated_without_suite_hash(
    ledger: Ledger,
    store: Store,
) -> None:
    """A certification-gated kind (`lean`) at an elevated status whose evidence
    carries no `golden_suite_hash` cannot be cross-checked against a
    certification -> flagged `elevated_missing_certified_evidence`. A
    self-validating kind (`dataset`) is exempt (its warrant is the certified
    engines it re-checks against, recorded in details)."""
    lean_digest = store.put(b"theorem t : True := trivial")
    lean_art = Artifact(
        id=lean_digest, kind="lean", problem="P5", problem_version="p5-test-v1",
        title="Empiricist.t", content_path=lean_digest, status=Status.FORMALIZED,
    )
    ledger.add_artifact(lean_art)
    ledger.record_evidence(_evidence(lean_art.id))  # PASS, no golden_suite_hash

    ds_digest = store.put(b"dataset rows")
    ds_art = Artifact(
        id=ds_digest, kind="dataset", problem="P5", problem_version="p5-test-v1",
        title="tablebase", content_path=ds_digest, status=Status.VERIFIED_N,
    )
    ledger.add_artifact(ds_art)
    ledger.record_evidence(_evidence(ds_art.id))  # PASS, no golden_suite_hash

    flagged = {
        (issue.artifact_id, issue.code)
        for issue in audit_ledger(ledger, store).issues
    }
    assert (lean_art.id, "elevated_missing_certified_evidence") in flagged
    # dataset is self-validating -> exempt from the cert cross-check
    assert (ds_art.id, "elevated_missing_certified_evidence") not in flagged


def test_audit_reports_missing_and_hash_mismatched_cas_blobs(
    ledger: Ledger,
    store: Store,
) -> None:
    missing = _artifact(store, b"missing")
    mismatched = _artifact(store, b"mismatched")
    ledger.add_artifact(missing)
    ledger.add_artifact(mismatched)
    store.path_for(missing.content_path).unlink()
    store.path_for(mismatched.content_path).write_bytes(b"tampered")

    report = audit_ledger(ledger, store)

    assert {issue.code for issue in report.issues} == {
        "artifact_blob_missing",
        "artifact_blob_hash_mismatch",
    }
    assert {issue.artifact_id for issue in report.issues} == {
        missing.id,
        mismatched.id,
    }


@pytest.mark.parametrize(
    "status",
    [Status.VERIFIED_N, Status.CERTIFIED, Status.FORMALIZED],
)
def test_audit_requires_pass_evidence_for_elevated_artifacts(
    ledger: Ledger,
    store: Store,
    status: Status,
) -> None:
    artifact = _artifact(store, status.value.encode(), status=status)
    ledger.add_artifact(artifact)
    ledger.record_evidence(_evidence(artifact.id, verdict=Verdict.FAIL))

    report = audit_ledger(ledger, store)

    issue = next(
        issue
        for issue in report.issues
        if issue.code == "elevated_without_pass_evidence"
    )
    assert issue.artifact_id == artifact.id


def test_audit_reports_dangling_optional_claim_and_run_links(
    ledger: Ledger,
    store: Store,
) -> None:
    artifact = _artifact(store, b"dangling")
    ledger.add_artifact(artifact)
    ledger.conn.execute("PRAGMA foreign_keys=OFF")
    try:
        # Simulate an externally damaged/legacy ledger directly. The normal
        # record_evidence API rejects dangling claim links before insertion.
        ledger.conn.execute(
            "INSERT INTO evidence"
            " (artifact_id, claim_id, run_id, verifier, verifier_version,"
            " binary_hash, verdict, details_json, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                artifact.id,
                "missing-claim",
                "missing-run",
                "p3-scheme",
                "1",
                "binary",
                Verdict.PASS.value,
                "{}",
                "2026-07-24T00:00:00+00:00",
            ),
        )
    finally:
        ledger.conn.execute("PRAGMA foreign_keys=ON")

    report = audit_ledger(ledger, store)

    assert {issue.code for issue in report.issues} == {
        "evidence_claim_missing",
        "evidence_run_missing",
    }


def test_audit_reports_a_dangling_artifact_run_link(
    ledger: Ledger,
    store: Store,
) -> None:
    artifact = replace(
        _artifact(store, b"artifact-run"),
        run_id="missing-artifact-run",
    )
    ledger.add_artifact(artifact)

    report = audit_ledger(ledger, store)

    issue = next(
        issue for issue in report.issues if issue.code == "artifact_run_missing"
    )
    assert issue.artifact_id == artifact.id
    assert issue.run_id == "missing-artifact-run"


def test_audit_accepts_complete_provider_run_with_cas_receipts(
    ledger: Ledger,
    store: Store,
) -> None:
    request_digest = store.put(b'{"request":true}')
    response_digest = store.put(b'{"response":true}')
    config_digest = store.put(b'{"config":true}')
    ledger.start_run(
        Run(
            run_id="provider-ok",
            move="SAMPLE",
            provider="openai",
            request_digest=request_digest,
            response_digest=response_digest,
            config_hash=config_digest,
            exit_code=0,
            ended="2026-07-24T00:00:00+00:00",
        )
    )

    assert audit_ledger(ledger, store).ok


def test_audit_requires_receipts_for_completed_provider_runs(
    ledger: Ledger,
    store: Store,
) -> None:
    ledger.start_run(
        Run(
            run_id="provider-no-receipts",
            move="SAMPLE",
            provider="openai",
            exit_code=1,
            ended="2026-07-24T00:00:00+00:00",
        )
    )

    assert {
        issue.code for issue in audit_ledger(ledger, store).issues
    } == {"run_request_missing", "run_response_missing"}


def test_audit_reports_unresolved_unknown_billing(
    ledger: Ledger,
    store: Store,
) -> None:
    request_digest = store.put(b'{"request":true}')
    response_digest = store.put(b'{"kind":"transport_error"}')
    config_digest = store.put(b'{"config":true}')
    ledger.start_run(
        Run(
            run_id="billing-unknown",
            move="SAMPLE",
            provider="openai",
            request_digest=request_digest,
            response_digest=response_digest,
            config_hash=config_digest,
            exit_code=UNKNOWN_BILLING_EXIT_CODE,
            ended="2026-07-24T00:00:00+00:00",
        )
    )

    issues = audit_ledger(ledger, store).issues
    assert [(issue.code, issue.run_id) for issue in issues] == [
        ("run_billing_unknown", "billing-unknown")
    ]


def test_audit_reports_unreconciled_provider_run_as_unknown_billing(
    ledger: Ledger,
    store: Store,
) -> None:
    ledger.start_run(
        Run(
            run_id="open-provider-run",
            move="SAMPLE",
            provider="openai",
            request_digest=store.put(b'{"request":true}'),
            config_hash=store.put(b'{"config":true}'),
        )
    )

    issues = audit_ledger(ledger, store).issues
    assert any(
        issue.code == "run_billing_unknown"
        and issue.run_id == "open-provider-run"
        for issue in issues
    )


def test_audit_verifies_all_linked_run_receipts_but_ignores_executor_config_hash(
    ledger: Ledger,
    store: Store,
) -> None:
    response_digest = store.put(b"original response")
    store.path_for(response_digest).write_bytes(b"tampered response")
    ledger.start_run(
        Run(
            run_id="provider-bad-receipts",
            move="SAMPLE",
            provider="openai",
            request_digest="f" * 64,
            response_digest=response_digest,
            config_hash="e" * 64,
        )
    )
    ledger.finish_run("provider-bad-receipts", exit_code=0, wall_s=0.1)
    ledger.start_run(
        Run(
            run_id="executor-receipt",
            move="VERIFY",
            request_digest="d" * 64,
            config_hash="ordinary-executor-config-hash",
        )
    )

    issues = audit_ledger(ledger, store).issues

    assert {issue.code for issue in issues} == {
        "run_receipt_missing",
        "run_receipt_hash_mismatch",
    }
    assert len(issues) == 4
    assert any("config_hash" in issue.message for issue in issues)
    assert {
        (issue.run_id, issue.code)
        for issue in issues
    } == {
        ("provider-bad-receipts", "run_receipt_missing"),
        ("provider-bad-receipts", "run_receipt_hash_mismatch"),
        ("executor-receipt", "run_receipt_missing"),
    }


def test_audit_requires_exact_current_pass_certification_for_suite_hash(
    ledger: Ledger,
    store: Store,
) -> None:
    artifact = _artifact(store, b"certification")
    ledger.add_artifact(artifact)
    ledger.record_evidence(
        _evidence(artifact.id, golden_suite_hash="suite-current")
    )

    assert {
        issue.code for issue in audit_ledger(ledger, store).issues
    } == {"evidence_certification_invalid"}

    ledger.add_certification(_certification(suite="suite-old"))
    assert {
        issue.code for issue in audit_ledger(ledger, store).issues
    } == {"evidence_certification_invalid"}

    ledger.add_certification(
        _certification(suite="suite-current", verdict=Verdict.FAIL)
    )
    assert {
        issue.code for issue in audit_ledger(ledger, store).issues
    } == {"evidence_certification_invalid"}

    ledger.add_certification(_certification(suite="suite-current"))
    assert audit_ledger(ledger, store).ok


def test_audit_cross_check_needs_a_pass_row_with_the_suite_hash(
    ledger: Ledger,
    store: Store,
) -> None:
    """A non-PASS row that carries a golden_suite_hash (e.g. a re-verification
    FAIL under the current gate) must NOT clear the flag: the cross-check is
    about certified PASS provenance, not about any row mentioning a suite."""
    digest = store.put(b"theorem t : True := trivial")
    art = Artifact(
        id=digest, kind="lean", problem="P5", problem_version="legacy",
        title="Empiricist.t", content_path=digest, status=Status.FORMALIZED,
    )
    ledger.add_artifact(art)
    ledger.record_evidence(_evidence(art.id))  # legacy PASS, no suite hash
    ledger.record_evidence(
        _evidence(art.id, verdict=Verdict.FAIL, golden_suite_hash="f" * 64)
    )
    codes = {i.code for i in audit_ledger(ledger, store).issues if i.artifact_id == art.id}
    assert "elevated_missing_certified_evidence" in codes

    ledger.record_evidence(_evidence(art.id, golden_suite_hash="f" * 64))  # PASS + hash
    codes = {i.code for i in audit_ledger(ledger, store).issues if i.artifact_id == art.id}
    assert "elevated_missing_certified_evidence" not in codes


def test_audit_treats_certificate_kind_as_certification_gated(
    ledger: Ledger,
    store: Store,
) -> None:
    digest = store.put(b'{"bound": "1/2"}')
    art = Artifact(
        id=digest, kind="certificate", problem="P3", problem_version="p3-sos-certificate-v1",
        title="cert", content_path=digest, status=Status.CERTIFIED,
    )
    ledger.add_artifact(art)
    ledger.record_evidence(_evidence(art.id))  # PASS, no golden_suite_hash
    codes = {i.code for i in audit_ledger(ledger, store).issues if i.artifact_id == art.id}
    assert "elevated_missing_certified_evidence" in codes

"""Small read-only consistency audit for the ledger and its CAS.

This deliberately checks a handful of trust-boundary invariants.  It is not a
historical replay engine and it never repairs state.
"""

from __future__ import annotations

from dataclasses import dataclass

from blake3 import blake3

from empiricist.ledger.db import (
    ORPHANED_EXIT_CODE,
    UNKNOWN_BILLING_EXIT_CODE,
    Ledger,
)
from empiricist.ledger.models import Status, Verdict
from empiricist.store import Store

_ELEVATED_STATUSES = frozenset(
    {Status.VERIFIED_N, Status.CERTIFIED, Status.FORMALIZED}
)

# Kinds whose elevated promotion is CERTIFICATION-gated (its warrant is a
# golden-suite certification), so its evidence MUST carry a cross-checkable
# `golden_suite_hash` column. Other elevated kinds (e.g. `dataset`) are
# self-validating — their warrant is the already-certified verifiers they
# re-check against, recorded in `details` — and are exempt from this cross
# check. Keying on (status, kind) rather than on the suite-hash column being
# populated lets the audit distinguish a self-validating promotion from a
# certification-gated one that is missing its checkable provenance.
# `lean` = kernel-checked Lean modules (LeanVerifier); `certificate` = exact SOS
# certificates checked by certificates.verifier.SOSCertificateVerifier.
_CERT_GATED_KINDS = frozenset({"lean", "certificate"})


@dataclass(frozen=True)
class AuditIssue:
    """One compact, machine-filterable consistency failure."""

    code: str
    message: str
    artifact_id: str | None = None
    run_id: str | None = None


@dataclass(frozen=True)
class AuditReport:
    """Result of one read-only audit pass."""

    issues: tuple[AuditIssue, ...]
    artifacts_checked: int
    evidence_checked: int

    @property
    def ok(self) -> bool:
        return not self.issues


def _audit_run_receipt(
    issues: list[AuditIssue],
    store: Store,
    *,
    run_id: str,
    field: str,
    digest: str,
) -> None:
    """Check one run receipt link without interpreting its payload."""

    try:
        content = store.get(digest)
    except (KeyError, OSError, ValueError):
        issues.append(
            AuditIssue(
                code="run_receipt_missing",
                run_id=run_id,
                message=(
                    f"run {run_id} has no readable {field} CAS receipt at {digest}"
                ),
            )
        )
        return

    actual_digest = blake3(content).hexdigest()
    if actual_digest != digest:
        issues.append(
            AuditIssue(
                code="run_receipt_hash_mismatch",
                run_id=run_id,
                message=(
                    f"run {run_id} {field} CAS content hashes to {actual_digest}, "
                    f"expected {digest}"
                ),
            )
        )


def audit_ledger(ledger: Ledger, store: Store) -> AuditReport:
    """Check current ledger/CAS consistency without changing either surface."""

    issues: list[AuditIssue] = []
    artifacts = ledger.find_artifacts()
    evidence_checked = 0

    for artifact in artifacts:
        if artifact.run_id is not None:
            try:
                ledger.get_run(artifact.run_id)
            except KeyError:
                issues.append(
                    AuditIssue(
                        code="artifact_run_missing",
                        artifact_id=artifact.id,
                        run_id=artifact.run_id,
                        message=(
                            f"artifact {artifact.id} references missing run "
                            f"{artifact.run_id}"
                        ),
                    )
                )

        try:
            content = store.get(artifact.content_path)
        except (KeyError, ValueError):
            issues.append(
                AuditIssue(
                    code="artifact_blob_missing",
                    artifact_id=artifact.id,
                    message=(
                        f"artifact {artifact.id} has no readable CAS blob at "
                        f"{artifact.content_path}"
                    ),
                )
            )
        else:
            actual_digest = blake3(content).hexdigest()
            if actual_digest != artifact.content_path:
                issues.append(
                    AuditIssue(
                        code="artifact_blob_hash_mismatch",
                        artifact_id=artifact.id,
                        message=(
                            f"artifact {artifact.id} CAS content hashes to "
                            f"{actual_digest}, expected {artifact.content_path}"
                        ),
                    )
                )

        evidence = ledger.evidence_for(artifact.id)
        evidence_checked += len(evidence)
        if (
            artifact.status in _ELEVATED_STATUSES
            and artifact.kind in _CERT_GATED_KINDS
            and not any(
                row.verdict is Verdict.PASS
                and getattr(row, "golden_suite_hash", None) is not None
                for row in evidence
            )
        ):
            issues.append(
                AuditIssue(
                    code="elevated_missing_certified_evidence",
                    artifact_id=artifact.id,
                    message=(
                        f"{artifact.status.value} {artifact.kind} artifact "
                        f"{artifact.id} has no PASS evidence carrying a golden_suite_hash "
                        "to cross-check against a certification (certification-gated "
                        "kind); re-verify under the current gate for full provenance"
                    ),
                )
            )
        if (
            artifact.status in _ELEVATED_STATUSES
            and not any(row.verdict is Verdict.PASS for row in evidence)
        ):
            issues.append(
                AuditIssue(
                    code="elevated_without_pass_evidence",
                    artifact_id=artifact.id,
                    message=(
                        f"{artifact.status.value} artifact {artifact.id} has no "
                        "PASS evidence"
                    ),
                )
            )

        for row in evidence:
            claim_id = getattr(row, "claim_id", None)
            if claim_id is not None:
                claim = ledger.conn.execute(
                    "SELECT 1 FROM claims WHERE id = ?", (claim_id,)
                ).fetchone()
                if claim is None:
                    issues.append(
                        AuditIssue(
                            code="evidence_claim_missing",
                            artifact_id=artifact.id,
                            message=(
                                f"evidence for artifact {artifact.id} references "
                                f"missing claim {claim_id}"
                            ),
                        )
                    )

            run_id = getattr(row, "run_id", None)
            if run_id is not None:
                try:
                    ledger.get_run(run_id)
                except KeyError:
                    issues.append(
                        AuditIssue(
                            code="evidence_run_missing",
                            artifact_id=artifact.id,
                            message=(
                                f"evidence for artifact {artifact.id} references "
                                f"missing run {run_id}"
                            ),
                        )
                    )

            suite_hash = getattr(row, "golden_suite_hash", None)
            if suite_hash is not None:
                certification = ledger.get_certification(
                    row.verifier,
                    row.verifier_version,
                    row.binary_hash,
                )
                if (
                    certification is None
                    or certification.verdict is not Verdict.PASS
                    or certification.golden_suite_hash != suite_hash
                ):
                    issues.append(
                        AuditIssue(
                            code="evidence_certification_invalid",
                            artifact_id=artifact.id,
                            message=(
                                f"evidence for artifact {artifact.id} lacks a "
                                "matching current PASS certification"
                            ),
                        )
                    )

    run_ids = [
        row["run_id"]
        for row in ledger.conn.execute("SELECT run_id FROM runs ORDER BY rowid")
    ]
    for run_id in run_ids:
        run = ledger.get_run(run_id)
        provider_backed = run.provider is not None
        billing_unknown = provider_backed and (
            run.ended is None
            or run.exit_code in {
                UNKNOWN_BILLING_EXIT_CODE,
                ORPHANED_EXIT_CODE,  # legacy reconciliation used this sentinel
            }
        )
        if billing_unknown:
            issues.append(
                AuditIssue(
                    code="run_billing_unknown",
                    run_id=run.run_id,
                    message=(
                        f"run {run.run_id} may have incurred provider charges "
                        "that are not represented in recorded spend"
                    ),
                )
            )
        if provider_backed and run.ended is not None:
            if run.request_digest is None:
                issues.append(
                    AuditIssue(
                        code="run_request_missing",
                        run_id=run.run_id,
                        message=(
                            f"completed provider-backed run {run.run_id} has no "
                            "request receipt"
                        ),
                    )
                )
            if run.response_digest is None:
                issues.append(
                    AuditIssue(
                        code="run_response_missing",
                        run_id=run.run_id,
                        message=(
                            f"completed provider-backed run {run.run_id} has no "
                            "response receipt"
                        ),
                    )
                )

        for field, digest in (
            ("request_digest", run.request_digest),
            ("response_digest", run.response_digest),
        ):
            if digest is not None:
                _audit_run_receipt(
                    issues,
                    store,
                    run_id=run.run_id,
                    field=field,
                    digest=digest,
                )

        # Executor config_hash values predate CAS receipts and may be ordinary
        # semantic hashes. Provider adapters use a non-null config_hash only
        # for their stored configuration receipt.
        if provider_backed and run.config_hash is not None:
            _audit_run_receipt(
                issues,
                store,
                run_id=run.run_id,
                field="config_hash",
                digest=run.config_hash,
            )

    return AuditReport(
        issues=tuple(issues),
        artifacts_checked=len(artifacts),
        evidence_checked=evidence_checked,
    )

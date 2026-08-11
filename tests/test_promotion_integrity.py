"""The claim-bound, certified, atomic artifact-ingestion boundary."""

from __future__ import annotations

from dataclasses import replace

import pytest

from empiricist.ledger.db import Ledger, PromotionIntegrityError
from empiricist.ledger.models import (
    Artifact,
    Certification,
    Claim,
    EvidenceRow,
    Status,
    Verdict,
)
from empiricist.store import Store


@pytest.fixture()
def env(tmp_path):
    ledger = Ledger(tmp_path / "ledger.db")
    store = Store(tmp_path / "store")
    yield ledger, store
    ledger.close()


def _artifact(store: Store, *, status: Status = Status.FORMALIZED) -> Artifact:
    digest = store.put(b"the checked artifact")
    return Artifact(
        id=digest,
        kind="lean",
        problem="P3",
        problem_version="p3-bound-v1",
        title="checked theorem",
        content_path=digest,
        status=status,
    )


def _claim(artifact_id: str, threshold: float = 0.5) -> Claim:
    return Claim.create(
        artifact_id=artifact_id,
        problem="P3",
        problem_version="p3-bound-v1",
        statement="the fixed scheme attains the requested threshold",
        metric="p_avg",
        scope={"threshold": threshold, "max_leakage": 0.0},
    )


def _evidence(artifact_id: str, claim_id: str, suite: str) -> EvidenceRow:
    return EvidenceRow(
        artifact_id=artifact_id,
        claim_id=claim_id,
        verifier="trusted-verifier",
        verifier_version="1",
        binary_hash="binary-v1",
        golden_suite_hash=suite,
        verdict=Verdict.PASS,
        details={"checked": True},
    )


def _cert(suite: str, verdict: Verdict = Verdict.PASS) -> Certification:
    return Certification(
        verifier="trusted-verifier",
        verifier_version="1",
        binary_hash="binary-v1",
        golden_suite_hash=suite,
        verdict=verdict,
    )


def test_missing_or_stale_certification_leaves_no_partial_ledger_rows(env):
    ledger, store = env
    artifact = _artifact(store)
    claim = _claim(artifact.id)
    evidence = _evidence(artifact.id, claim.id, "suite-current")

    with pytest.raises(PromotionIntegrityError, match="current PASS certification"):
        ledger.record_claimed_artifact(
            artifact,
            claim,
            evidence,
            expected_golden_suite_hash="suite-current",
        )
    with pytest.raises(KeyError):
        ledger.get_artifact(artifact.id)
    assert ledger.claims_for(artifact.id) == []
    assert ledger.evidence_for(artifact.id) == []

    ledger.add_certification(_cert("suite-old"))
    with pytest.raises(PromotionIntegrityError, match="suite-current"):
        ledger.record_claimed_artifact(
            artifact,
            claim,
            evidence,
            expected_golden_suite_hash="suite-current",
        )
    with pytest.raises(KeyError):
        ledger.get_artifact(artifact.id)


def test_artifact_claim_and_pass_evidence_commit_as_one_unit(env):
    ledger, store = env
    artifact = _artifact(store)
    claim = _claim(artifact.id)
    evidence = _evidence(artifact.id, claim.id, "suite-current")
    ledger.add_certification(_cert("suite-current"))

    stored = ledger.record_claimed_artifact(
        artifact,
        claim,
        evidence,
        expected_golden_suite_hash="suite-current",
    )

    assert stored == artifact
    assert ledger.claims_for(artifact.id) == [claim]
    assert ledger.evidence_for(artifact.id) == [evidence]


def test_same_claim_is_idempotent_but_second_claim_on_same_artifact_is_kept(env):
    ledger, store = env
    artifact = _artifact(store, status=Status.HEURISTIC)
    first = _claim(artifact.id, 0.5)
    second = _claim(artifact.id, 0.75)
    ledger.add_certification(_cert("suite-current"))

    for claim in (first, first, second):
        ledger.record_claimed_artifact(
            artifact,
            claim,
            _evidence(artifact.id, claim.id, "suite-current"),
            expected_golden_suite_hash="suite-current",
        )

    assert {claim.id for claim in ledger.claims_for(artifact.id)} == {
        first.id,
        second.id,
    }
    assert len(ledger.evidence_for(artifact.id)) == 2


def test_legacy_artifact_can_gain_a_versioned_claim_without_reinterpreting_row(env):
    ledger, store = env
    current = _artifact(store)
    legacy = replace(
        current,
        problem_version="legacy",
        status=Status.HEURISTIC,
    )
    ledger.add_artifact(legacy)
    claim = _claim(current.id)
    ledger.add_certification(_cert("suite-current"))

    stored = ledger.record_claimed_artifact(
        current,
        claim,
        _evidence(current.id, claim.id, "suite-current"),
        expected_golden_suite_hash="suite-current",
    )

    # The immutable pilot row remains explicitly legacy; the new canonical
    # claim carries the precise problem version it actually checked.
    assert stored.problem_version == "legacy"
    assert stored.status is Status.FORMALIZED
    assert ledger.claims_for(current.id) == [claim]


def test_non_pass_evidence_cannot_enter_the_claimed_artifact_path(env):
    ledger, store = env
    artifact = _artifact(store)
    claim = _claim(artifact.id)
    evidence = _evidence(artifact.id, claim.id, "suite-current")
    object.__setattr__(evidence, "verdict", Verdict.ERROR)
    ledger.add_certification(_cert("suite-current"))

    with pytest.raises(PromotionIntegrityError, match="requires PASS evidence"):
        ledger.record_claimed_artifact(
            artifact,
            claim,
            evidence,
            expected_golden_suite_hash="suite-current",
        )
    with pytest.raises(KeyError):
        ledger.get_artifact(artifact.id)


def test_forged_claim_id_cannot_enter_the_claimed_artifact_path(env):
    ledger, store = env
    artifact = _artifact(store)
    canonical = _claim(artifact.id)
    forged = replace(canonical, id="forged-claim-id")
    ledger.add_certification(_cert("suite-current"))

    with pytest.raises(PromotionIntegrityError, match="canonical hash"):
        ledger.record_claimed_artifact(
            artifact,
            forged,
            _evidence(artifact.id, forged.id, "suite-current"),
            expected_golden_suite_hash="suite-current",
        )

    with pytest.raises(KeyError):
        ledger.get_artifact(artifact.id)
    assert ledger.claims_for(artifact.id) == []


@pytest.mark.parametrize(
    ("problem", "problem_version", "message"),
    [
        ("P5", "p3-bound-v1", "claim problem does not match"),
        ("P3", "p3-bound-v2", "claim problem version does not match"),
    ],
)
def test_claim_scope_must_match_the_incoming_artifact(
    env,
    problem: str,
    problem_version: str,
    message: str,
):
    ledger, store = env
    artifact = _artifact(store)
    claim = Claim.create(
        artifact_id=artifact.id,
        problem=problem,
        problem_version=problem_version,
        statement="the fixed scheme attains the requested threshold",
        metric="p_avg",
        scope={"threshold": 0.5, "max_leakage": 0.0},
    )
    ledger.add_certification(_cert("suite-current"))

    with pytest.raises(PromotionIntegrityError, match=message):
        ledger.record_claimed_artifact(
            artifact,
            claim,
            _evidence(artifact.id, claim.id, "suite-current"),
            expected_golden_suite_hash="suite-current",
        )

    with pytest.raises(KeyError):
        ledger.get_artifact(artifact.id)

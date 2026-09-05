"""Certificate -> CERTIFIED ingestion (the first real content in that tier)."""
from __future__ import annotations

import pytest

from empiricist.certificates.goldens import certify_sos, load_k0_golden, sos_suite_hash
from empiricist.certificates.ingest import (
    P3_CERTIFICATE_TARGETS,
    ingest_p3_certificate,
    verify_and_ingest_p3_certificate,
)
from empiricist.certificates.verifier import SOSCertificateVerifier, certificate_to_json
from empiricist.ledger.audit import audit_ledger
from empiricist.ledger.db import Ledger, PromotionIntegrityError
from empiricist.ledger.models import Status, Verdict
from empiricist.store import Store

TARGET = "k0_standard_assignment_p_avg"


@pytest.fixture()
def env(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    st = Store(tmp_path / "store")
    certify_sos(lg, SOSCertificateVerifier())
    yield lg, st
    lg.close()


def test_golden_ingests_at_certified_with_claim_and_clean_audit(env):
    lg, st = env
    art = ingest_p3_certificate(
        lg,
        st,
        certificate_json=certificate_to_json(load_k0_golden()),
        target=TARGET,
        title="k=0 standard assignment p_avg <= 1/2",
    )
    assert art.status is Status.CERTIFIED and art.kind == "certificate"
    assert art.problem == "P3"
    claim = lg.claims_for(art.id)[0]
    assert "at most 1/2" in claim.statement and claim.scope["target"] == TARGET
    assert claim.metric == "p_avg_upper_bound"
    rows = lg.evidence_for(art.id)
    assert len(rows) == 1 and rows[0].golden_suite_hash == sos_suite_hash()
    assert rows[0].verdict is Verdict.PASS and rows[0].details["target"] == TARGET
    assert audit_ledger(lg, st).ok


def test_ingest_is_idempotent(env):
    lg, st = env
    kw = dict(certificate_json=certificate_to_json(load_k0_golden()), target=TARGET, title="t")
    a = ingest_p3_certificate(lg, st, **kw)
    b = ingest_p3_certificate(lg, st, **kw)
    assert a.id == b.id and len(lg.evidence_for(a.id)) == 1


def test_wrong_target_is_refused_before_verification(env):
    lg, st = env
    data = certificate_to_json(load_k0_golden())
    with pytest.raises(ValueError, match="does not encode"):
        ingest_p3_certificate(lg, st, certificate_json=data, target="no_such_target", title="t")
    data["objective"] = {"": "0"}
    with pytest.raises(ValueError, match="does not encode"):
        ingest_p3_certificate(lg, st, certificate_json=data, target=TARGET, title="t")
    assert lg.find_artifacts() == []


def test_malformed_json_is_refused(env):
    lg, st = env
    with pytest.raises(ValueError, match="malformed"):
        ingest_p3_certificate(lg, st, certificate_json={"bound": "1"}, target=TARGET, title="t")


def test_mutated_certificate_records_nothing(env):
    lg, st = env
    data = certificate_to_json(load_k0_golden())
    data["bound"] = "49/100"
    result, art = verify_and_ingest_p3_certificate(
        lg, st, certificate_json=data, target=TARGET, title="t"
    )
    assert result.verdict is Verdict.FAIL and art is None
    assert result.details["failure"] == "identity"
    assert lg.find_artifacts() == []
    with pytest.raises(ValueError, match="non-PASS"):
        ingest_p3_certificate(lg, st, certificate_json=data, target=TARGET, title="t")


def test_uncertified_verifier_fails_closed(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    st = Store(tmp_path / "store")
    try:
        with pytest.raises(PromotionIntegrityError):
            ingest_p3_certificate(
                lg,
                st,
                certificate_json=certificate_to_json(load_k0_golden()),
                target=TARGET,
                title="t",
            )
        assert lg.find_artifacts() == []
    finally:
        lg.close()


def test_target_registry_names_the_k0_problem():
    t = P3_CERTIFICATE_TARGETS[TARGET]
    assert t.n_modes == 4 and t.k == 0 and "U(4)" in t.statement

"""Certificate -> CERTIFIED ingestion (the first real content in that tier)."""
from __future__ import annotations

from fractions import Fraction

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
    # The golden's multipliers live entirely on the unitarity block, so the
    # recorded claim may quantify over ALL of U(4).
    assert claim.scope["uses_side_constraints"] is False
    assert "For every passive interferometer U in U(4)" in claim.statement
    assert "AT WHICH" not in claim.statement
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


def test_constraint_half_of_the_meaning_gate_has_teeth(env):
    lg, st = env
    truncated = certificate_to_json(load_k0_golden())
    truncated["constraints"] = truncated["constraints"][:5]
    truncated["multipliers"] = truncated["multipliers"][:5]
    with pytest.raises(ValueError, match="does not encode"):
        ingest_p3_certificate(lg, st, certificate_json=truncated, target=TARGET, title="t")
    extended = certificate_to_json(load_k0_golden())
    extended["constraints"] = extended["constraints"] + [{"0,0": "1"}]
    extended["multipliers"] = extended["multipliers"] + [{"": "0"}]
    with pytest.raises(ValueError, match="does not encode"):
        ingest_p3_certificate(lg, st, certificate_json=extended, target=TARGET, title="t")
    # An attacker-chosen constraint set that makes the identity trivial: refused
    # by the meaning gate even though the checker's algebra would accept it.
    from empiricist.certificates.core import poly_sub

    cert = load_k0_golden()
    bogus = certificate_to_json(cert)
    from empiricist.certificates.verifier import _poly_to_json

    bogus["bound"] = "1/100"
    bogus["constraints"] = [_poly_to_json(poly_sub(cert.objective, {(): Fraction(1, 100)}))]
    bogus["multipliers"] = [{"": "-1"}]
    bogus["gram_basis"] = []
    bogus["gram"] = []
    with pytest.raises(ValueError, match="does not encode"):
        ingest_p3_certificate(lg, st, certificate_json=bogus, target=TARGET, title="t")
    assert lg.find_artifacts() == []


def test_side_constraint_multipliers_yield_the_restricted_claim(env, monkeypatch):
    """A certificate whose identity leans on a SIDE constraint may only claim the
    bound on the side variety: the ingest must record the restricted statement."""
    from empiricist.certificates import ingest as ingest_mod
    from empiricist.certificates.ingest import CertificateTarget, uses_side_constraints

    # objective x0 <= 1/2 on {x0 - 1/2 = 0}: 1/2 - x0 - (-1)(x0 - 1/2) = 0 = empty Gram.
    tiny = CertificateTarget(
        name="tiny_side", n_modes=4, k=0,
        objective=lambda: {(0,): Fraction(1)},
        core_constraints=lambda: [],
        side_constraints=lambda: [{(0,): Fraction(1), (): Fraction(-1, 2)}],
        statement_universal="UNIVERSAL {bound}",
        statement_restricted="RESTRICTED {bound}",
        metric="test",
    )
    monkeypatch.setitem(ingest_mod.P3_CERTIFICATE_TARGETS, "tiny_side", tiny)
    cert_json = {
        "statement": "tiny", "variables": ["x0"], "objective": {"0": "1"},
        "bound": "1/2", "constraints": [{"0": "1", "": "-1/2"}],
        "multipliers": [{"": "-1"}], "gram_basis": [], "gram": [],
    }
    from empiricist.certificates.verifier import certificate_from_json

    assert uses_side_constraints(certificate_from_json(cert_json), tiny) is True
    art = ingest_p3_certificate(lg := env[0], st := env[1], certificate_json=cert_json,
                                target="tiny_side", title="t")
    claim = lg.claims_for(art.id)[0]
    assert claim.statement == "RESTRICTED 1/2" and claim.scope["uses_side_constraints"] is True
    assert art.status is Status.CERTIFIED
    assert st.exists(art.content_path)
    assert uses_side_constraints(load_k0_golden(), P3_CERTIFICATE_TARGETS[TARGET]) is False


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


def test_ignored_keys_do_not_mint_distinct_artifacts(env):
    lg, st = env
    data = certificate_to_json(load_k0_golden())
    a = ingest_p3_certificate(lg, st, certificate_json=data, target=TARGET, title="t")
    b = ingest_p3_certificate(lg, st, certificate_json={**data, "comment": "hi"},
                              target=TARGET, title="t")
    assert a.id == b.id and len(lg.find_artifacts()) == 1


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
    assert t.n_modes == 4 and t.k == 0
    assert "U(4)" in t.statement_universal and "AT WHICH" in t.statement_restricted
    assert len(t.constraints()) == len(t.core_constraints()) + len(t.side_constraints())

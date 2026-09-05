"""Exact witness -> CERTIFIED ingestion."""
from __future__ import annotations

import math

import pytest

from empiricist.domain.p3.exact_ingest import (
    ingest_exact_witness,
    verify_and_ingest_exact_witness,
)
from empiricist.domain.p3.ingest import ingest_scheme_artifact
from empiricist.ledger.audit import audit_ledger
from empiricist.ledger.db import Ledger, PromotionIntegrityError
from empiricist.ledger.models import Status, Verdict
from empiricist.search.schemas import ScreenReject
from empiricist.store import Store
from empiricist.verifiers.p3_exact import P3ExactVerifier
from empiricist.verifiers.p3_exact_goldens import certify_p3_exact, p3_exact_suite_hash
from empiricist.verifiers.p3_goldens import certify_p3
from empiricist.verifiers.p3_scheme import P3SchemeVerifier

_BS = math.pi / 4


def _grice_json() -> dict:
    r = 1 / math.sqrt(2)
    bs = [(0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
    return {
        "n_modes": 8,
        "n_ancilla_photons": 2,
        "ancilla": [
            {"pattern": [1, 0, 1, 0], "re": r, "im": 0.0},
            {"pattern": [0, 1, 0, 1], "re": r, "im": 0.0},
        ],
        "mesh": [{"kind": "bs", "i": i, "j": j, "theta": _BS, "phi": 0.0} for i, j in bs],
    }


def _bsm_json() -> dict:
    return {
        "n_modes": 4,
        "n_ancilla_photons": 0,
        "ancilla": [],
        "mesh": [
            {"kind": "bs", "i": 0, "j": 2, "theta": _BS, "phi": 0.0},
            {"kind": "bs", "i": 1, "j": 3, "theta": _BS, "phi": 0.0},
        ],
    }


GRICE_CLAIM = {"phi+": "1/2", "phi-": "1/2", "psi+": "1", "psi-": "1"}


@pytest.fixture()
def env(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    st = Store(tmp_path / "store")
    certify_p3_exact(lg, P3ExactVerifier())
    certify_p3(lg, P3SchemeVerifier())
    yield lg, st
    lg.close()


def test_grice_witness_ingests_at_certified_with_claim_and_clean_audit(env):
    lg, st = env
    art = ingest_exact_witness(
        lg, st, scheme_json=_grice_json(), claimed_success=GRICE_CLAIM,
        require_all_identified=True, title="Grice k=2 exact witness",
    )
    assert art.status is Status.CERTIFIED and art.kind == "certificate" and art.problem == "P3"
    claim = lg.claims_for(art.id)[0]
    assert "p*_min(2) >= 1/2" in claim.statement and "p*_avg(2) >= 3/4" in claim.statement
    assert "Every Bell state is identified" in claim.statement
    assert claim.family == "k2_m8_exact_witness" and claim.scope["all_identified"] is True
    assert claim.scope["success"]["phi+"] == ["1/2", "0"]
    rows = lg.evidence_for(art.id)
    assert len(rows) == 1 and rows[0].golden_suite_hash == p3_exact_suite_hash()
    assert rows[0].verdict is Verdict.PASS
    assert audit_ledger(lg, st).ok


def test_ingest_is_idempotent_and_distinct_from_the_float_artifact(env):
    lg, st = env
    kw = dict(scheme_json=_grice_json(), claimed_success=GRICE_CLAIM, title="t")
    a = ingest_exact_witness(lg, st, **kw)
    b = ingest_exact_witness(lg, st, **kw)
    assert a.id == b.id and len(lg.evidence_for(a.id)) == 1
    fl = ingest_scheme_artifact(lg, st, scheme_json=_grice_json(), title="float",
                                claimed_p_avg=0.75)
    assert fl.id != a.id and fl.status is Status.HEURISTIC
    assert {x.status for x in lg.find_artifacts()} == {Status.CERTIFIED, Status.HEURISTIC}


def test_wrong_vector_and_missing_all_identified_record_nothing(env):
    lg, st = env
    result, art = verify_and_ingest_exact_witness(
        lg, st, scheme_json=_grice_json(),
        claimed_success={**GRICE_CLAIM, "phi+": "1/4"}, title="t",
    )
    assert result.verdict is Verdict.FAIL and art is None
    result, art = verify_and_ingest_exact_witness(
        lg, st, scheme_json=_bsm_json(),
        claimed_success={"phi+": "0", "phi-": "0", "psi+": "1", "psi-": "1"},
        require_all_identified=True, title="t",
    )
    assert result.verdict is Verdict.FAIL and art is None
    assert lg.find_artifacts() == []
    with pytest.raises(ValueError, match="non-PASS"):
        ingest_exact_witness(lg, st, scheme_json=_bsm_json(),
                             claimed_success={**GRICE_CLAIM}, title="t")


def test_bad_claim_shape_and_bad_scheme_are_refused_before_verification(env):
    lg, st = env
    with pytest.raises(ValueError, match="claimed_success"):
        ingest_exact_witness(lg, st, scheme_json=_grice_json(),
                             claimed_success={"phi+": "1"}, title="t")
    with pytest.raises(ScreenReject):
        ingest_exact_witness(lg, st, scheme_json={"n_modes": 99}, claimed_success=GRICE_CLAIM,
                             title="t")
    assert lg.find_artifacts() == []


def test_uncertified_exact_verifier_fails_closed(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    st = Store(tmp_path / "store")
    try:
        with pytest.raises(PromotionIntegrityError):
            ingest_exact_witness(lg, st, scheme_json=_grice_json(),
                                 claimed_success=GRICE_CLAIM, title="t")
        assert lg.find_artifacts() == []
    finally:
        lg.close()

"""Tests for P3 scheme ingestion into the ledger (M20a Task 2).

Fixture style mirrors `tests/test_search_conjecture.py`'s `env(tmp_path)`
(yields a fresh `(Ledger, Store)` pair, closes the ledger on teardown) and
its duplicate-ingest assertions (`ledger.evidence_for` row count).
"""

from __future__ import annotations

import math

import pytest

from empiricist.domain.p3.ingest import ingest_scheme_artifact
from empiricist.ledger.db import Ledger, PromotionIntegrityError
from empiricist.search.schemas import ScreenReject
from empiricist.store import Store
from empiricist.verifiers.p3_goldens import certify_p3
from empiricist.verifiers.p3_scheme import P3SchemeVerifier


def _bsm_dict(**overrides):
    d = {
        "n_modes": 4,
        "n_ancilla_photons": 0,
        "ancilla": [],
        "mesh": [
            {"kind": "bs", "i": 0, "j": 2, "theta": math.pi / 4, "phi": 0.0},
            {"kind": "bs", "i": 1, "j": 3, "theta": math.pi / 4, "phi": 0.0},
        ],
        "claimed_p_avg": 0.5,
    }
    d.update(overrides)
    return d


@pytest.fixture()
def env(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    st = Store(tmp_path / "store")
    certify_p3(lg, P3SchemeVerifier())
    yield lg, st
    lg.close()


def test_ingest_pass_scheme_lands_as_claim_bound_heuristic(env):
    lg, st = env
    scheme_json = _bsm_dict()

    art = ingest_scheme_artifact(
        lg, st, scheme_json=scheme_json,
        title="k=0 standard BSM at p_avg 1/2",
        claimed_p_avg=0.5,
    )

    stored = lg.get_artifact(art.id)
    assert stored.status.value == "HEURISTIC"
    assert stored.kind == "construction"
    assert stored.problem == "P3"
    assert stored.problem_version == "p3-linear-optical-scheme-v1"

    evs = lg.evidence_for(art.id)
    assert len(evs) == 1
    assert evs[0].verifier == "p3_scheme_agreed"
    assert evs[0].details["p_avg"] == pytest.approx(0.5)
    assert evs[0].details["leakage"] == pytest.approx(0.0)
    assert evs[0].claim_id is not None
    assert evs[0].golden_suite_hash is not None
    assert lg.claims_for(art.id)[0].id == evs[0].claim_id


def test_ingest_records_claims_alongside_achievement(env):
    lg, st = env
    scheme_json = _bsm_dict()

    art = ingest_scheme_artifact(
        lg, st, scheme_json=scheme_json,
        title="k=0 standard BSM at p_avg 1/2", claimed_p_avg=0.5,
    )

    # the evidence row carries the CLAIM the verifier checked, not just the
    # achievement -- the declared leakage budget is THE certificate parameter
    # (verify.py: "unambiguous up to leakage <= <declared budget>")
    details = lg.evidence_for(art.id)[0].details
    assert details["claimed_p_avg"] == 0.5
    assert details["claimed_p_min"] is None
    assert details["claimed_max_leakage"] == 0.0


def test_ingest_refuses_non_pass(env):
    lg, st = env
    scheme_json = _bsm_dict()

    with pytest.raises(ValueError):
        ingest_scheme_artifact(
            lg, st, scheme_json=scheme_json, title="nope", claimed_p_avg=0.99,
        )


def test_ingest_is_idempotent_on_same_scheme(env):
    lg, st = env
    scheme_json = _bsm_dict()

    a1 = ingest_scheme_artifact(
        lg, st, scheme_json=scheme_json, title="first", claimed_p_avg=0.5,
    )
    a2 = ingest_scheme_artifact(
        lg, st, scheme_json=scheme_json, title="second (ignored)", claimed_p_avg=0.5,
    )

    assert a1.id == a2.id
    assert lg.get_artifact(a1.id).title == "first"
    evs = lg.evidence_for(a1.id)
    assert len(evs) == 1  # no second evidence row for the duplicate ingest


def test_ingest_drops_a_dry_run_id_from_artifact_and_evidence(env):
    lg, st = env

    artifact = ingest_scheme_artifact(
        lg,
        st,
        scheme_json=_bsm_dict(),
        title="dry-client result",
        run_id="not-a-ledger-run",
        claimed_p_avg=0.5,
    )

    assert artifact.run_id is None
    assert lg.evidence_for(artifact.id)[0].run_id is None


def test_ingest_rejects_unserializable_scheme_json(env):
    lg, st = env
    bad_scheme_json = {"x": object()}
    with pytest.raises(ScreenReject):
        ingest_scheme_artifact(
            lg, st, scheme_json=bad_scheme_json, title="bad json",
        )


def test_ingest_rejects_nan_in_scheme_json(env):
    lg, st = env
    # allow_nan=False: NaN must raise, never silently emit non-strict JSON
    nan_scheme_json = _bsm_dict(claimed_p_avg=float("nan"))
    with pytest.raises(ValueError):
        ingest_scheme_artifact(
            lg, st, scheme_json=nan_scheme_json, title="nan json",
        )


def test_ingest_requires_current_p3_verifier_certification(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    st = Store(tmp_path / "store")
    try:
        with pytest.raises(PromotionIntegrityError, match="current PASS certification"):
            ingest_scheme_artifact(
                lg,
                st,
                scheme_json=_bsm_dict(),
                title="uncertified",
                claimed_p_avg=0.5,
            )
        assert lg.find_artifacts() == []
    finally:
        lg.close()

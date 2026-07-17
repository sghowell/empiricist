"""Tests for P3 scheme ingestion into the ledger (M20a Task 2).

Fixture style mirrors `tests/test_search_conjecture.py`'s `env(tmp_path)`
(yields a fresh `(Ledger, Store)` pair, closes the ledger on teardown) and
its duplicate-ingest assertions (`ledger.evidence_for` row count).
"""

from __future__ import annotations

import math

import pytest

from empiricist.domain.p3.ingest import ingest_scheme_artifact
from empiricist.domain.p3.verify import verify_scheme_agreed
from empiricist.ledger.db import Ledger
from empiricist.search.p3_screen import screen_scheme
from empiricist.store import Store


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
    yield lg, st
    lg.close()


def test_ingest_pass_scheme_lands_verified_n(env):
    lg, st = env
    scheme_json = _bsm_dict()
    scheme = screen_scheme(scheme_json)
    result = verify_scheme_agreed(scheme, claimed_p_avg=0.5)
    assert result.verdict == "PASS"

    art = ingest_scheme_artifact(
        lg, st, scheme_json=scheme_json, result=result,
        title="k=0 standard BSM at p_avg 1/2",
    )

    stored = lg.get_artifact(art.id)
    assert stored.status.value == "VERIFIED_N"
    assert stored.kind == "construction"
    assert stored.problem == "P3"

    evs = lg.evidence_for(art.id)
    assert len(evs) == 1
    assert evs[0].verifier == "p3_scheme_agreed"
    assert evs[0].details["p_avg"] == pytest.approx(result.report.p_avg)
    assert evs[0].details["leakage"] == pytest.approx(result.leakage)
    assert evs[0].details["success_by_state"] == result.report.success_by_state


def test_ingest_records_claims_alongside_achievement(env):
    lg, st = env
    scheme_json = _bsm_dict()
    scheme = screen_scheme(scheme_json)
    result = verify_scheme_agreed(scheme, claimed_p_avg=0.5)
    assert result.verdict == "PASS"

    art = ingest_scheme_artifact(
        lg, st, scheme_json=scheme_json, result=result,
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
    scheme = screen_scheme(scheme_json)
    result = verify_scheme_agreed(scheme, claimed_p_avg=0.99)
    assert result.verdict == "FAIL"

    with pytest.raises(ValueError):
        ingest_scheme_artifact(
            lg, st, scheme_json=scheme_json, result=result, title="nope",
        )


def test_ingest_is_idempotent_on_same_scheme(env):
    lg, st = env
    scheme_json = _bsm_dict()
    scheme = screen_scheme(scheme_json)
    result = verify_scheme_agreed(scheme, claimed_p_avg=0.5)

    a1 = ingest_scheme_artifact(
        lg, st, scheme_json=scheme_json, result=result, title="first",
    )
    a2 = ingest_scheme_artifact(
        lg, st, scheme_json=scheme_json, result=result, title="second (ignored)",
    )

    assert a1.id == a2.id
    assert lg.get_artifact(a1.id).title == "first"
    evs = lg.evidence_for(a1.id)
    assert len(evs) == 1  # no second evidence row for the duplicate ingest


def test_ingest_rejects_unserializable_scheme_json(env):
    lg, st = env
    scheme_json = _bsm_dict()
    scheme = screen_scheme(scheme_json)
    result = verify_scheme_agreed(scheme, claimed_p_avg=0.5)

    bad_scheme_json = {"x": object()}
    with pytest.raises(ValueError):
        ingest_scheme_artifact(
            lg, st, scheme_json=bad_scheme_json, result=result, title="bad json",
        )


def test_ingest_rejects_nan_in_scheme_json(env):
    lg, st = env
    scheme_json = _bsm_dict()
    scheme = screen_scheme(scheme_json)
    result = verify_scheme_agreed(scheme, claimed_p_avg=0.5)

    # allow_nan=False: NaN must raise, never silently emit non-strict JSON
    nan_scheme_json = _bsm_dict(claimed_p_avg=float("nan"))
    with pytest.raises(ValueError):
        ingest_scheme_artifact(
            lg, st, scheme_json=nan_scheme_json, result=result, title="nan json",
        )

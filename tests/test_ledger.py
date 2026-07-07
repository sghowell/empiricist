"""Tests for the SQLite ledger core: bootstrap, artifacts, evidence, transitions."""

import sqlite3

import pytest

from empiricist.ledger.db import Ledger, TerminalStatusError
from empiricist.ledger.models import Artifact, EvidenceRow, Status, Verdict
from empiricist.store import Store


@pytest.fixture()
def ledger(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    yield lg
    lg.close()


@pytest.fixture()
def store(tmp_path):
    return Store(tmp_path / "store")


def make_artifact(store, content=b"claim: F(path_N) = N-3", **kw):
    digest = store.put(content)
    defaults = dict(
        id=digest, kind="statement", problem="P5", title="a claim",
        content_path=digest, status=Status.HEURISTIC,
    )
    defaults.update(kw)
    return Artifact(**defaults)


def make_evidence(artifact_id, verdict=Verdict.PASS, **kw):
    defaults = dict(
        artifact_id=artifact_id, verifier="stab_fusion", verifier_version="1.0",
        binary_hash="deadbeef", verdict=verdict, details={"n": 8},
    )
    defaults.update(kw)
    return EvidenceRow(**defaults)


def test_bootstrap_applies_wal_and_creates_tables(ledger):
    assert ledger.conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    names = {
        r[0] for r in ledger.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {
        "artifacts", "evidence", "certifications", "edges", "runs",
        "claims", "gates", "population", "evicted", "search_events",
        "pareto_frontier",
    } <= names


def test_add_and_get_artifact_roundtrips(ledger, store):
    art = make_artifact(store)
    ledger.add_artifact(art)
    got = ledger.get_artifact(art.id)
    assert got == art


def test_add_artifact_twice_raises(ledger, store):
    art = make_artifact(store)
    ledger.add_artifact(art)
    with pytest.raises(sqlite3.IntegrityError):
        ledger.add_artifact(art)


def test_record_evidence_without_status_change(ledger, store):
    art = make_artifact(store)
    ledger.add_artifact(art)
    ledger.record_evidence(make_evidence(art.id))
    assert ledger.get_artifact(art.id).status == Status.HEURISTIC
    evs = ledger.evidence_for(art.id)
    assert len(evs) == 1 and evs[0].details == {"n": 8}


def test_promotion_updates_status_atomically_with_evidence(ledger, store):
    art = make_artifact(store, kind="dataset")
    ledger.add_artifact(art)
    ledger.record_evidence(
        make_evidence(art.id),
        new_status=Status.VERIFIED_N, status_n=9, coverage="exhaustive",
    )
    got = ledger.get_artifact(art.id)
    assert got.status == Status.VERIFIED_N
    assert got.status_n == 9 and got.coverage == "exhaustive"


def test_status_change_requires_evidence_api_only(ledger, store):
    """There is no public method to set status without an evidence row."""
    assert not hasattr(ledger, "set_status")


def test_refuted_is_terminal(ledger, store):
    art = make_artifact(store)
    ledger.add_artifact(art)
    ledger.record_evidence(
        make_evidence(art.id, verdict=Verdict.FAIL, details={"counterexample": "C_5"}),
        new_status=Status.REFUTED,
    )
    with pytest.raises(TerminalStatusError):
        ledger.record_evidence(make_evidence(art.id), new_status=Status.CONJECTURED)


def test_record_evidence_for_unknown_artifact_raises(ledger):
    with pytest.raises(KeyError):
        ledger.record_evidence(make_evidence("0" * 64))


def test_edges(ledger, store):
    a = make_artifact(store, content=b"a")
    b = make_artifact(store, content=b"b")
    ledger.add_artifact(a)
    ledger.add_artifact(b)
    ledger.add_edge(a.id, b.id, "depends_on")
    assert ledger.edges_from(a.id) == [(a.id, b.id, "depends_on")]


def test_reopen_preserves_state(tmp_path, store):
    lg = Ledger(tmp_path / "ledger.db")
    art = make_artifact(store)
    lg.add_artifact(art)
    lg.close()
    lg2 = Ledger(tmp_path / "ledger.db")
    assert lg2.get_artifact(art.id) == art
    lg2.close()


def test_record_evidence_rolls_back_atomically_on_midtx_failure(ledger, store):
    """The F1 guarantee: a failure between the status UPDATE and the evidence
    INSERT must leave the artifact unchanged and record nothing."""
    art = make_artifact(store)
    ledger.add_artifact(art)
    bad = make_evidence(art.id)
    # Force the evidence INSERT to violate NOT NULL after the UPDATE ran.
    object.__setattr__(bad, "verifier", None)
    with pytest.raises(sqlite3.IntegrityError):
        ledger.record_evidence(bad, new_status=Status.VERIFIED_N, status_n=9)
    got = ledger.get_artifact(art.id)
    assert got.status == Status.HEURISTIC and got.status_n is None
    assert ledger.evidence_for(art.id) == []


def test_nested_tx_raises_loudly(ledger):
    with pytest.raises(RuntimeError, match="nested _tx"):
        with ledger._tx():
            with ledger._tx():
                pass  # pragma: no cover


def test_substatus_clears_on_status_change_unless_passed(ledger, store):
    art = make_artifact(store)
    ledger.add_artifact(art)
    ledger.record_evidence(
        make_evidence(art.id), new_status=Status.CONJECTURED, substatus="PROVED_DRAFT"
    )
    assert ledger.get_artifact(art.id).substatus == "PROVED_DRAFT"
    # evidence-only record leaves substatus alone
    ledger.record_evidence(make_evidence(art.id))
    assert ledger.get_artifact(art.id).substatus == "PROVED_DRAFT"
    # status change without substatus clears it (no self-contradictory REFUTED+PROVED_DRAFT)
    ledger.record_evidence(
        make_evidence(art.id, verdict=Verdict.FAIL), new_status=Status.REFUTED
    )
    got = ledger.get_artifact(art.id)
    assert got.status == Status.REFUTED and got.substatus is None


def test_status_n_clears_when_leaving_verified_n(ledger, store):
    art = make_artifact(store, kind="dataset")
    ledger.add_artifact(art)
    ledger.record_evidence(
        make_evidence(art.id), new_status=Status.VERIFIED_N,
        status_n=9, coverage="exhaustive",
    )
    ledger.record_evidence(make_evidence(art.id), new_status=Status.CERTIFIED)
    got = ledger.get_artifact(art.id)
    assert got.status == Status.CERTIFIED
    assert got.status_n is None and got.coverage is None

"""Tests for the persisted human-gate queue (spec §4.2, §9; gates parked overnight)."""

import pytest

from empiricist.ledger.db import Ledger
from empiricist.ledger.gates import GateError, Gates


@pytest.fixture()
def gates(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    yield Gates(lg)
    lg.close()


def test_open_gate_is_pending(gates):
    g = gates.open("PROOF_CAMPAIGN", artifact_id="art1", note="prove F(cycle)")
    assert g.state == "pending" and g.kind == "PROOF_CAMPAIGN"
    assert g.opened_at is not None and g.resolved_at is None


def test_list_pending(gates):
    gates.open("PROOF_CAMPAIGN", artifact_id="a")
    gates.open("RELEASE", artifact_id="b")
    pending = gates.list(state="pending")
    assert {g.kind for g in pending} == {"PROOF_CAMPAIGN", "RELEASE"}


def test_approve(gates):
    g = gates.open("PROOF_CAMPAIGN", artifact_id="a")
    resolved = gates.resolve(g.id, approve=True, note="go")
    assert resolved.state == "approved" and resolved.resolved_at is not None
    assert gates.list(state="pending") == []


def test_reject(gates):
    g = gates.open("RELEASE", artifact_id="a")
    assert gates.resolve(g.id, approve=False).state == "rejected"


def test_resolve_twice_raises(gates):
    g = gates.open("RELEASE", artifact_id="a")
    gates.resolve(g.id, approve=True)
    with pytest.raises(GateError):
        gates.resolve(g.id, approve=False)


def test_resolve_unknown_raises(gates):
    with pytest.raises(KeyError):
        gates.resolve("nope", approve=True)


def test_invalid_kind_raises(gates):
    with pytest.raises(GateError):
        gates.open("NOT_A_GATE", artifact_id="a")


def test_gates_survive_reopen(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    g = Gates(lg).open("REDUCE", artifact_id="a", note="reformulate")
    lg.close()
    lg2 = Ledger(tmp_path / "ledger.db")
    gates2 = Gates(lg2)
    persisted = gates2.list(state="pending")
    assert [p.id for p in persisted] == [g.id] and persisted[0].kind == "REDUCE"
    lg2.close()


def test_list_filters_by_kind_and_artifact(gates):
    gates.open("PROOF_CAMPAIGN", artifact_id="a")
    gates.open("ACCEPT_DRAFT", artifact_id="b")
    assert [g.kind for g in gates.list(kind="ACCEPT_DRAFT")] == ["ACCEPT_DRAFT"]
    assert [g.artifact_id for g in gates.list(artifact_id="a")] == ["a"]


def test_has_pending_and_duplicate_open_rejected(gates):
    assert not gates.has_pending(artifact_id="a")
    g = gates.open("PROOF_CAMPAIGN", artifact_id="a")
    assert gates.has_pending(artifact_id="a")
    assert gates.has_pending(artifact_id="a", kind="PROOF_CAMPAIGN")
    with pytest.raises(GateError):
        gates.open("PROOF_CAMPAIGN", artifact_id="a")
    gates.resolve(g.id, approve=True)
    assert not gates.has_pending(artifact_id="a")
    # resolved gate no longer blocks a new one
    gates.open("PROOF_CAMPAIGN", artifact_id="a")


def test_resolve_note_semantics(gates):
    g1 = gates.open("RELEASE", artifact_id="a", note="original")
    assert gates.resolve(g1.id, approve=True).note == "original"  # None preserves
    g2 = gates.open("RELEASE", artifact_id="b", note="original")
    assert gates.resolve(g2.id, approve=False, note="override").note == "override"

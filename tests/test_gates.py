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

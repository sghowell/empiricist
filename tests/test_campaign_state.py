"""Tests for CampaignState (M7 T1): create-or-resume Ledger+Store+Registry+
Population+Gates handles for a run directory (spec §4.4/§9)."""

from __future__ import annotations

import sqlite3

import pytest

from empiricist.campaign.state import CampaignState
from empiricist.ledger.db import ORPHANED_EXIT_CODE, UNKNOWN_BILLING_EXIT_CODE
from empiricist.ledger.migrations import LATEST_SCHEMA_VERSION, SchemaVersionError
from empiricist.ledger.models import Run


def _tree_snapshot(root):
    return {
        path.relative_to(root).as_posix(): (
            "dir" if path.is_dir() else "file",
            None if path.is_dir() else path.read_bytes(),
        )
        for path in sorted(root.rglob("*"))
    }


def test_load_creates_run_dir_ledger_and_store(tmp_path):
    run_dir = tmp_path / "run1"
    state = CampaignState.load(run_dir)
    try:
        assert run_dir.exists()
        assert (run_dir / "ledger.db").exists()
        # Store is lazily materialized (mkdir on first put()), so only its
        # configured root is checked here, not the directory's existence.
        assert state.store.root == run_dir / "store"
        assert state.run_dir == run_dir
    finally:
        state.close()


def test_load_on_empty_dir_logs_created_event(tmp_path):
    run_dir = tmp_path / "run2"
    state = CampaignState.load(run_dir)
    try:
        events = state.population.events()
        assert len(events) == 1
        assert events[0].gen == -1
        assert events[0].trigger == "created"
        assert events[0].detail == {"orphans": 0}
    finally:
        state.close()


def test_second_load_is_a_resume(tmp_path):
    run_dir = tmp_path / "run3"
    state1 = CampaignState.load(run_dir)
    state1.close()

    state2 = CampaignState.load(run_dir)
    try:
        events = state2.population.events()
        assert [e.trigger for e in events] == ["created", "resume"]
        assert events[1].gen == -1
        assert events[1].detail == {"orphans": 0}
    finally:
        state2.close()


def test_resume_reconciles_orphaned_runs(tmp_path):
    run_dir = tmp_path / "run4"
    state1 = CampaignState.load(run_dir)
    # Simulate a crash mid-sample: a run row started but never finished.
    state1.ledger.start_run(Run(run_id="orphan-1", move="SAMPLE"))
    state1.close()

    state2 = CampaignState.load(run_dir)
    try:
        events = state2.population.events()
        assert events[-1].trigger == "resume"
        assert events[-1].detail == {"orphans": 1}

        orphaned_run = state2.ledger.get_run("orphan-1")
        assert orphaned_run.exit_code == ORPHANED_EXIT_CODE
        assert orphaned_run.ended is not None
    finally:
        state2.close()


def test_resume_marks_provider_orphan_as_unknown_billing(tmp_path):
    run_dir = tmp_path / "provider-orphan"
    state1 = CampaignState.load(run_dir)
    state1.ledger.start_run(
        Run(run_id="paid-orphan", move="SAMPLE", provider="openai")
    )
    state1.close()

    state2 = CampaignState.load(run_dir)
    try:
        run = state2.ledger.get_run("paid-orphan")
        assert run.exit_code == UNKNOWN_BILLING_EXIT_CODE
        assert run.ended is not None
    finally:
        state2.close()


def test_resume_detected_via_artifacts_even_with_no_search_events(tmp_path):
    """A prior session that only ran ENUMERATE (no SEARCH/CONJECTURE wave
    yet) leaves artifacts but no non-marker search_events -- resume must
    still be detected from the artifacts table, not just search_events."""
    from empiricist.ledger.ingest import ingest_artifact
    from empiricist.ledger.models import Status

    run_dir = tmp_path / "run5"
    state1 = CampaignState.load(run_dir)
    # Wipe the "created" marker itself to isolate the artifacts-only signal.
    state1.ledger.conn.execute("DELETE FROM search_events")
    ingest_artifact(
        state1.ledger, state1.store, content=b"dataset-bytes", kind="dataset",
        problem="P5", title="t", status=Status.VERIFIED_N,
    )
    state1.close()

    state2 = CampaignState.load(run_dir)
    try:
        events = state2.population.events()
        assert events[-1].trigger == "resume"
    finally:
        state2.close()


def test_close_closes_the_ledger_connection(tmp_path):
    state = CampaignState.load(tmp_path / "run6")
    state.close()
    with pytest.raises(sqlite3.ProgrammingError):
        state.ledger.conn.execute("SELECT 1")


def test_load_tolerates_a_preexisting_empty_directory(tmp_path):
    run_dir = tmp_path / "run7"
    run_dir.mkdir()
    state = CampaignState.load(run_dir)
    state.close()


def test_open_readonly_requires_existing_ledger_without_creating(tmp_path):
    run_dir = tmp_path / "missing"

    with pytest.raises(FileNotFoundError, match="campaign ledger does not exist"):
        CampaignState.open_readonly(run_dir)

    assert not run_dir.exists()


def test_open_readonly_does_not_reconcile_log_or_touch_run_dir(tmp_path):
    run_dir = tmp_path / "run8"
    mutating = CampaignState.load(run_dir)
    mutating.ledger.start_run(Run(run_id="still-running", move="SAMPLE"))
    mutating.close()
    before = _tree_snapshot(run_dir)

    inspecting = CampaignState.open_readonly(run_dir)
    try:
        assert [event.trigger for event in inspecting.population.events()] == ["created"]
        orphan = inspecting.ledger.get_run("still-running")
        assert orphan.ended is None
        assert orphan.exit_code is None

        # The connection itself rejects writes even if a caller accidentally
        # reaches one of the normal mutable facades.
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            inspecting.population.log_event(1, "must-not-write")
    finally:
        inspecting.close()

    assert _tree_snapshot(run_dir) == before


def test_open_readonly_refuses_an_active_wal_instead_of_showing_stale_data(tmp_path):
    mutating = CampaignState.load(tmp_path / "run9")
    try:
        with pytest.raises(RuntimeError, match="active or uncheckpointed WAL"):
            CampaignState.open_readonly(mutating.run_dir)
    finally:
        mutating.close()


def test_open_readonly_refuses_a_future_schema_without_touching_the_run(tmp_path):
    run_dir = tmp_path / "run10"
    state = CampaignState.load(run_dir)
    state.close()
    conn = sqlite3.connect(run_dir / "ledger.db")
    conn.execute(f"PRAGMA user_version={LATEST_SCHEMA_VERSION + 1}")
    conn.close()
    before = _tree_snapshot(run_dir)

    with pytest.raises(SchemaVersionError, match="newer than this build"):
        CampaignState.open_readonly(run_dir)

    assert _tree_snapshot(run_dir) == before

"""Tests for CampaignState (M7 T1): create-or-resume Ledger+Store+Registry+
Population+Gates handles for a run directory (spec §4.4/§9)."""

from __future__ import annotations

import sqlite3

import pytest

from empiricist.campaign.state import CampaignState
from empiricist.ledger.db import ORPHANED_EXIT_CODE
from empiricist.ledger.models import Run


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

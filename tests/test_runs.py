"""Tests for run provenance rows and resume reconciliation (spec §4.4)."""

import pytest

from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Run


@pytest.fixture()
def ledger(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    yield lg
    lg.close()


def test_start_and_finish_run(ledger):
    ledger.start_run(Run(run_id="r1", move="ENUMERATE", role=None, argv="minsearch --n 8"))
    ledger.finish_run(
        "r1", exit_code=0, wall_s=1.5, peak_rss_mb=42.0,
        tokens_in=0, tokens_out=0, cache_read=0, cost_usd=0.0,
    )
    row = ledger.get_run("r1")
    assert row.exit_code == 0 and row.ended is not None and row.wall_s == 1.5


def test_finish_unknown_run_raises(ledger):
    with pytest.raises(KeyError):
        ledger.finish_run("nope", exit_code=0, wall_s=0.0)


def test_reconcile_orphans_marks_unfinished_runs(ledger):
    ledger.start_run(Run(run_id="r1", move="SEARCH"))
    ledger.start_run(Run(run_id="r2", move="SEARCH"))
    ledger.finish_run("r1", exit_code=0, wall_s=1.0)
    n = ledger.reconcile_orphans()
    assert n == 1
    r2 = ledger.get_run("r2")
    assert r2.exit_code == -1 and r2.ended is not None
    # idempotent
    assert ledger.reconcile_orphans() == 0


def test_finish_run_is_exactly_once(ledger):
    from empiricist.ledger.db import RunAlreadyFinishedError
    ledger.start_run(Run(run_id="r1", move="SEARCH"))
    ledger.finish_run("r1", exit_code=0, wall_s=1.0, tokens_out=500, cost_usd=0.25)
    with pytest.raises(RunAlreadyFinishedError):
        ledger.finish_run("r1", exit_code=0, wall_s=0.0)
    # the first finish's numbers stand
    assert ledger.get_run("r1").tokens_out == 500
    assert ledger.spent().cost_usd == pytest.approx(0.25)


def test_reconcile_leaves_finished_runs_untouched(ledger):
    ledger.start_run(Run(run_id="ok", move="SEARCH"))
    ledger.finish_run("ok", exit_code=0, wall_s=1.0)
    ledger.reconcile_orphans()
    assert ledger.get_run("ok").exit_code == 0


def test_spent_is_zero_on_empty_ledger_and_ignores_inflight(ledger):
    assert ledger.spent().cost_usd == 0.0
    ledger.start_run(Run(run_id="inflight", move="SEARCH"))
    s = ledger.spent()
    assert s.cost_usd == 0.0 and s.tokens_in == 0  # documented floor semantics


def test_duplicate_run_id_raises_integrity_error(ledger):
    import sqlite3
    ledger.start_run(Run(run_id="dup", move="SEARCH"))
    with pytest.raises(sqlite3.IntegrityError):
        ledger.start_run(Run(run_id="dup", move="SEARCH"))


def test_spent_sums_cost_and_tokens(ledger):
    ledger.start_run(Run(run_id="r1", move="SEARCH"))
    ledger.finish_run("r1", exit_code=0, wall_s=1.0,
                      tokens_in=1000, tokens_out=500, cost_usd=0.25)
    ledger.start_run(Run(run_id="r2", move="SEARCH"))
    ledger.finish_run("r2", exit_code=0, wall_s=1.0,
                      tokens_in=2000, tokens_out=1500, cost_usd=0.75)
    spent = ledger.spent()
    assert spent.cost_usd == pytest.approx(1.0)
    assert spent.tokens_in == 3000 and spent.tokens_out == 2000

"""Tests for the search Population (M6 T1): per-key elite upsert over the
ledger's `population` table, with a no-silent-truncation `evicted` audit
row on every improvement, plus the `search_events` log (spec §9).
"""

from __future__ import annotations

import pytest

from empiricist.ledger.db import Ledger
from empiricist.search.database import Population


@pytest.fixture()
def ledger(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    yield lg
    lg.close()


@pytest.fixture()
def population(ledger):
    return Population(ledger)


# -- consider(): upsert semantics --------------------------------------------


def test_new_key_inserts_and_reports_improvement(population):
    assert (
        population.consider("k1", island=0, cell="c0", objective_vec=[3], cert_hash="h1")
        is True
    )
    row = population.get("k1")
    assert row is not None
    assert row.lc_orbit_key == "k1"
    assert row.island == 0
    assert row.cell == "c0"
    assert row.objective_vec == [3]
    assert row.cert_hash == "h1"
    assert row.hit_count == 1
    assert population.count() == 1


def test_strictly_better_vec_replaces_row_and_reports_improvement(population):
    population.consider("k1", island=0, cell="c0", objective_vec=[3], cert_hash="h1")
    result = population.consider("k1", island=1, cell="c1", objective_vec=[2], cert_hash="h2")
    assert result is True
    row = population.get("k1")
    assert row.objective_vec == [2]
    assert row.cert_hash == "h2"
    assert row.island == 1
    assert row.cell == "c1"
    assert row.hit_count == 1  # fresh elite, not accumulated
    assert population.count() == 1  # replace, not a new row


def test_worse_vec_bumps_hit_count_and_reports_no_improvement(population):
    population.consider("k1", island=0, cell="c0", objective_vec=[2], cert_hash="h1")
    result = population.consider("k1", island=1, cell="c1", objective_vec=[3], cert_hash="h2")
    assert result is False
    row = population.get("k1")
    assert row.objective_vec == [2]  # unchanged (worse candidate didn't win)
    assert row.cert_hash == "h1"
    assert row.island == 0
    assert row.cell == "c0"
    assert row.hit_count == 2


def test_equal_vec_counts_as_hit_not_improvement(population):
    population.consider("k1", island=0, cell="c0", objective_vec=[2], cert_hash="h1")
    result = population.consider("k1", island=0, cell="c0", objective_vec=[2], cert_hash="h2")
    assert result is False
    row = population.get("k1")
    assert row.cert_hash == "h1"  # incumbent kept
    assert row.hit_count == 2


def test_multivalue_objective_vec_uses_lexicographic_order(population):
    population.consider("k1", 0, "c0", [1, 9], "h1")
    # First component ties at 1, second is strictly smaller -> improvement.
    assert population.consider("k1", 0, "c0", [1, 5], "h2") is True
    assert population.get("k1").objective_vec == [1, 5]
    # First component is worse (2 > 1) even though second is much smaller.
    assert population.consider("k1", 0, "c0", [2, 0], "h3") is False
    assert population.get("k1").objective_vec == [1, 5]


def test_get_missing_key_returns_none(population):
    assert population.get("nope") is None


def test_count_across_multiple_distinct_keys(population):
    population.consider("k1", 0, "c0", [1], "h1")
    population.consider("k2", 0, "c0", [1], "h2")
    population.consider("k1", 0, "c0", [1], "h3")  # equal, no new row
    assert population.count() == 2


def test_objective_vec_json_roundtrips_floats_and_ints(population):
    population.consider("k1", 0, "c0", [3.0, 1.5, 2], "h1")
    row = population.get("k1")
    assert row.objective_vec == [3.0, 1.5, 2]


# -- eviction audit -----------------------------------------------------------


def test_eviction_audit_row_contents_on_improvement(population, ledger):
    population.consider("k1", island=0, cell="c0", objective_vec=[3], cert_hash="h1")
    population.consider("k1", island=1, cell="c1", objective_vec=[2], cert_hash="h2")
    rows = ledger.conn.execute(
        "SELECT lc_orbit_key, reason, dominated_by, ts FROM evicted WHERE lc_orbit_key = ?",
        ("k1",),
    ).fetchall()
    assert len(rows) == 1
    r = rows[0]
    assert r["reason"] == "improved"
    assert r["dominated_by"] == "h2"  # the NEW cert that dominated the old row
    assert r["ts"]  # non-empty timestamp


def test_no_eviction_row_on_worse_or_equal(population, ledger):
    population.consider("k1", 0, "c0", [2], "h1")
    population.consider("k1", 0, "c0", [3], "h2")  # worse
    population.consider("k1", 0, "c0", [2], "h3")  # equal
    rows = ledger.conn.execute(
        "SELECT * FROM evicted WHERE lc_orbit_key = ?", ("k1",)
    ).fetchall()
    assert rows == []


def test_multiple_improvements_each_log_an_eviction_row(population, ledger):
    population.consider("k1", 0, "c0", [5], "h1")
    population.consider("k1", 0, "c0", [3], "h2")
    population.consider("k1", 0, "c0", [1], "h3")
    rows = ledger.conn.execute(
        "SELECT dominated_by FROM evicted WHERE lc_orbit_key = ? ORDER BY rowid", ("k1",)
    ).fetchall()
    assert [r["dominated_by"] for r in rows] == ["h2", "h3"]


# -- events -------------------------------------------------------------------


def test_log_event_and_events_roundtrip_detail(population):
    population.log_event(gen=1, trigger="improvement", detail={"key": "k1", "n": 3})
    population.log_event(gen=1, trigger="stall", detail=None)
    events = population.events()
    assert len(events) == 2
    imp = next(e for e in events if e.trigger == "improvement")
    assert imp.gen == 1
    assert imp.detail == {"key": "k1", "n": 3}
    assert imp.ts
    stall = next(e for e in events if e.trigger == "stall")
    assert stall.detail is None


def test_events_filter_by_trigger(population):
    population.log_event(gen=1, trigger="improvement", detail=None)
    population.log_event(gen=2, trigger="stall", detail=None)
    population.log_event(gen=3, trigger="improvement", detail=None)
    improvements = population.events(trigger="improvement")
    assert len(improvements) == 2
    assert all(e.trigger == "improvement" for e in improvements)
    assert [e.gen for e in improvements] == [1, 3]


def test_events_empty_by_default(population):
    assert population.events() == []
    assert population.events(trigger="improvement") == []


# -- persistence across reopen -------------------------------------------------


def test_persistence_across_ledger_reopen(tmp_path):
    path = tmp_path / "ledger.db"
    lg1 = Ledger(path)
    pop1 = Population(lg1)
    pop1.consider("k1", 0, "c0", [3], "h1")
    pop1.consider("k1", 1, "c1", [2], "h2")  # improvement -> eviction row too
    pop1.log_event(gen=1, trigger="improvement", detail={"k": "k1"})
    lg1.close()

    lg2 = Ledger(path)
    try:
        pop2 = Population(lg2)
        row = pop2.get("k1")
        assert row is not None
        assert row.objective_vec == [2]
        assert row.cert_hash == "h2"
        assert pop2.count() == 1
        events = pop2.events()
        assert len(events) == 1
        assert events[0].detail == {"k": "k1"}
        evicted = lg2.conn.execute(
            "SELECT * FROM evicted WHERE lc_orbit_key = 'k1'"
        ).fetchall()
        assert len(evicted) == 1
    finally:
        lg2.close()

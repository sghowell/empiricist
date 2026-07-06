"""Tests for ledger model types."""

import pytest

from empiricist.ledger.models import (
    Budget,
    Status,
    Verdict,
    dominates,
    now_iso,
)


def test_status_members():
    assert {s.value for s in Status} == {
        "REFUTED", "HEURISTIC", "CONJECTURED", "VERIFIED_N", "CERTIFIED", "FORMALIZED",
    }


def test_verdict_members():
    assert {v.value for v in Verdict} == {"PASS", "FAIL", "ERROR", "TIMEOUT"}


def test_budget_is_frozen_with_optional_fields():
    b = Budget(wall_s=10.0)
    assert b.wall_s == 10.0 and b.tokens is None and b.rss_mb is None
    with pytest.raises(AttributeError):
        b.wall_s = 5.0  # type: ignore[misc]


def test_now_iso_is_utc_isoformat():
    ts = now_iso()
    assert ts.endswith("+00:00") and "T" in ts


class TestDominates:
    """Pareto dominance, minimizing every component."""

    def test_strictly_better_dominates(self):
        assert dominates([1, 1], [2, 2])

    def test_equal_does_not_dominate(self):
        assert not dominates([1, 1], [1, 1])

    def test_better_in_one_equal_in_other_dominates(self):
        assert dominates([1, 2], [1, 3])

    def test_incomparable_does_not_dominate(self):
        assert not dominates([1, 3], [2, 1])
        assert not dominates([2, 1], [1, 3])

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            dominates([1], [1, 2])

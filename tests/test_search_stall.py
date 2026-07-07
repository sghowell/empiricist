"""Tests for two-signal stall detection (M6 T4, spec §9): no-improvement
window + diversity floor over a sliding tail of `GenerationReport`s. See
`search.stall.StallDetector`'s docstring for the exact proxy-metric
semantics this suite pins down -- notably that `"island_reset"` is reached
only when `diversity_floor <= 0.0` (see that module's "documented quirk"
section for why).
"""

from __future__ import annotations

import pytest

from empiricist.search.loop import GenerationReport
from empiricist.search.stall import StallDetector


def make_report(gen: int, *, sampled: int, inserted: int) -> GenerationReport:
    return GenerationReport(
        gen=gen, sampled=sampled, no_artifact=0, screened_out=0, verify_fail=0,
        verify_error=0, inserted=inserted, duplicates=0, exact_upgrades=(),
        screen_reasons=(),
    )


def test_fewer_than_window_reports_is_healthy():
    d = StallDetector(window=3, diversity_floor=0.3)
    d.feed(make_report(1, sampled=10, inserted=0))
    d.feed(make_report(2, sampled=10, inserted=0))
    assert d.assess() == "healthy"


def test_zero_reports_is_healthy():
    d = StallDetector(window=3, diversity_floor=0.3)
    assert d.assess() == "healthy"


def test_any_improvement_anywhere_in_window_is_healthy():
    d = StallDetector(window=3, diversity_floor=0.9)  # high floor, still healthy
    d.feed(make_report(1, sampled=10, inserted=0))
    d.feed(make_report(2, sampled=10, inserted=1))
    d.feed(make_report(3, sampled=10, inserted=0))
    assert d.assess() == "healthy"


def test_no_improvements_with_positive_floor_is_hard_restart():
    """total_inserted==0 over the window -> diversity is trivially 0.0, so
    any diversity_floor > 0 always escalates to hard_restart."""
    d = StallDetector(window=3, diversity_floor=0.3)
    for gen in (1, 2, 3):
        d.feed(make_report(gen, sampled=10, inserted=0))
    assert d.assess() == "hard_restart"


def test_no_improvements_with_zero_floor_is_island_reset():
    """diversity_floor=0.0 disables the hard-restart escalation (0.0 is
    never < 0.0), so a totally-stalled window recommends the softer
    island_reset instead."""
    d = StallDetector(window=3, diversity_floor=0.0)
    for gen in (1, 2, 3):
        d.feed(make_report(gen, sampled=10, inserted=0))
    assert d.assess() == "island_reset"


def test_no_improvements_with_negative_floor_is_island_reset():
    d = StallDetector(window=3, diversity_floor=-0.1)
    for gen in (1, 2, 3):
        d.feed(make_report(gen, sampled=10, inserted=0))
    assert d.assess() == "island_reset"


def test_window_is_a_sliding_tail_not_cumulative_history():
    """The improving gen=1 report ages out of a window=2 detector once two
    more reports arrive -- only the LAST 2 are considered."""
    d = StallDetector(window=2, diversity_floor=0.3)
    d.feed(make_report(1, sampled=10, inserted=5))
    assert d.assess() == "healthy"  # fewer than window reports so far
    d.feed(make_report(2, sampled=10, inserted=0))
    assert d.assess() == "healthy"  # window=[1,2]: gen 1's insert still counts
    d.feed(make_report(3, sampled=10, inserted=0))
    assert d.assess() == "hard_restart"  # window=[2,3]: gen 1 aged out, no improvement


def test_window_validates_minimum():
    with pytest.raises(ValueError):
        StallDetector(window=0, diversity_floor=0.3)


def test_feed_returns_none_and_assess_is_repeatable():
    d = StallDetector(window=2, diversity_floor=0.3)
    assert d.feed(make_report(1, sampled=10, inserted=0)) is None
    d.feed(make_report(2, sampled=10, inserted=0))
    assert d.assess() == "hard_restart"
    assert d.assess() == "hard_restart"  # assess() does not mutate state

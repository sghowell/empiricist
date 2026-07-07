"""Tests for two-signal stall detection (M6 T4/T5, spec §9): no-improvement
window + a verified-activity floor over a sliding tail of `GenerationReport`s.
See `search.stall.StallDetector`'s docstring for the exact semantics this
suite pins down -- notably that `"island_reset"` is genuinely reachable for
any positive `diversity_floor` (the fixed formulation), unlike the earlier
`inserted / sampled` proxy that collapsed every stalled window to
`"hard_restart"`.
"""

from __future__ import annotations

import pytest

from empiricist.search.loop import GenerationReport
from empiricist.search.stall import StallDetector


def make_report(
    gen: int, *, sampled: int, inserted: int, duplicates: int = 0
) -> GenerationReport:
    return GenerationReport(
        gen=gen, sampled=sampled, no_artifact=0, screened_out=0, verify_fail=0,
        verify_error=0, inserted=inserted, duplicates=duplicates, exact_upgrades=(),
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


def test_no_improvements_but_still_verifying_above_floor_is_island_reset():
    """total_inserted==0 over the window (no NEW key anywhere), but every
    sampled candidate is still reaching PASS -- they just keep landing on
    already-known keys (duplicates). That is CONVERGENCE, not collapse:
    verified_activity = (0+9)/10 = 0.9 >= 0.3, so the recommendation is the
    softer island_reset (shift the island/targets), genuinely reachable
    here with a positive floor -- the bug the old proxy had."""
    d = StallDetector(window=1, diversity_floor=0.3)
    d.feed(make_report(1, sampled=10, inserted=0, duplicates=9))
    assert d.assess() == "island_reset"


def test_no_improvements_and_verified_activity_below_floor_is_hard_restart():
    """No new keys AND barely anything even verifies (1 duplicate out of 10
    sampled, the rest failed screen/verify): verified_activity = 0.1 < 0.3
    -- the search is degenerate, not merely converged, so hard_restart."""
    d = StallDetector(window=1, diversity_floor=0.3)
    d.feed(make_report(1, sampled=10, inserted=0, duplicates=1))
    assert d.assess() == "hard_restart"


def test_nothing_verifies_at_all_is_hard_restart():
    """The degenerate floor: zero inserts, zero duplicates -- every sample
    failed screen/verify. verified_activity is trivially 0.0, so any
    positive floor recommends hard_restart."""
    d = StallDetector(window=3, diversity_floor=0.3)
    for gen in (1, 2, 3):
        d.feed(make_report(gen, sampled=10, inserted=0, duplicates=0))
    assert d.assess() == "hard_restart"


def test_verified_activity_aggregates_across_the_whole_window():
    """No single report clears the floor on its own, but the window-summed
    ratio does: total inserted=0, total duplicates=4, total sampled=10 ->
    0.4 >= 0.3 -> island_reset. Pins down that the ratio is computed over
    summed window totals, not per-report."""
    d = StallDetector(window=2, diversity_floor=0.3)
    d.feed(make_report(1, sampled=5, inserted=0, duplicates=1))  # 0.2 alone
    d.feed(make_report(2, sampled=5, inserted=0, duplicates=3))  # 0.6 alone
    assert d.assess() == "island_reset"


def test_verified_activity_exactly_at_floor_is_island_reset():
    """The comparison is >=, not >: a ratio exactly equal to the floor
    still counts as still-alive."""
    d = StallDetector(window=1, diversity_floor=0.3)
    d.feed(make_report(1, sampled=10, inserted=0, duplicates=3))
    assert d.assess() == "island_reset"


def test_no_improvements_with_zero_floor_is_island_reset():
    """diversity_floor=0.0: verified_activity (even 0.0) is never < 0.0, so
    a totally dead window still recommends the softer island_reset."""
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
    more reports arrive -- only the LAST 2 are considered, and the tail's
    low verified_activity drops it all the way to hard_restart."""
    d = StallDetector(window=2, diversity_floor=0.3)
    d.feed(make_report(1, sampled=10, inserted=5))
    assert d.assess() == "healthy"  # fewer than window reports so far
    d.feed(make_report(2, sampled=10, inserted=0))
    assert d.assess() == "healthy"  # window=[1,2]: gen 1's insert still counts
    d.feed(make_report(3, sampled=10, inserted=0))
    assert d.assess() == "hard_restart"  # window=[2,3]: gen 1 aged out, nothing verifies


def test_window_validates_minimum():
    with pytest.raises(ValueError):
        StallDetector(window=0, diversity_floor=0.3)


def test_feed_returns_none_and_assess_is_repeatable():
    d = StallDetector(window=2, diversity_floor=0.3)
    assert d.feed(make_report(1, sampled=10, inserted=0)) is None
    d.feed(make_report(2, sampled=10, inserted=0))
    assert d.assess() == "hard_restart"
    assert d.assess() == "hard_restart"  # assess() does not mutate state

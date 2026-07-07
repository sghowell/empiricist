"""Stall detection (M6 T4, spec §9): a two-signal, offline recommendation
over a sliding window of `search.loop.GenerationReport`s -- no-improvement
window + a diversity floor. `StallDetector` only RECOMMENDS a state; it
writes nothing and emits nothing itself (the M7 scheduler is the one that
acts on `assess()`'s return value -- e.g. by logging a `search_events` row
and actually resetting/restarting).

**Exact semantics** (read this before changing the thresholds):

- Fewer than `window` reports fed so far -> `"healthy"` (not enough history
  to judge a wave; refuses to call a stall on a cold start).
- Otherwise, look at the LAST `window` reports fed (a sliding tail, not the
  cumulative history -- `feed` keeps only the most recent `window`):
  - `total_inserted = sum(r.inserted for r in window)`. If `total_inserted >
    0` (the population gained at least one new key somewhere in the window)
    -> `"healthy"`, regardless of diversity.
  - Otherwise (`total_inserted == 0`, i.e. a fully stalled window: every
    sample in it either failed some earlier stage or hit an
    already-known key): compute `diversity = total_inserted /
    total_sampled` (0.0, since the numerator is 0) and compare to
    `diversity_floor`.
    - `diversity < diversity_floor` -> `"hard_restart"`.
    - otherwise -> `"island_reset"`.

**Documented quirk:** `diversity` is `sum(inserted) / sum(sampled)` over the
window -- the plan's own proxy for "distinct new keys / window", since
`GenerationReport` (M6 T3) does not carry the set of individual achieved
keys, only aggregate counts, and `population.consider` returning `True` is
exactly "this candidate was a new key" per `search.database.Population`'s
own contract. A direct consequence: whenever `total_inserted == 0` (the only
way to reach the diversity comparison at all), `diversity` is trivially
`0.0`, so for any `diversity_floor > 0` the comparison ALWAYS resolves to
`"hard_restart"` -- `"island_reset"` is reached only when `diversity_floor
<= 0.0` (i.e. a config that disables the harder escalation and always
prefers the softer recommendation for a stalled window). This is accepted
as a known limitation of the proxy, not a bug: a real distinct-key diversity
signal would require widening `GenerationReport` to carry per-candidate
keys, deferred to M7 alongside the rest of the scheduler wiring.
"""

from __future__ import annotations

from collections import deque
from typing import Literal

from empiricist.search.loop import GenerationReport

Assessment = Literal["healthy", "island_reset", "hard_restart"]


class StallDetector:
    def __init__(self, window: int, diversity_floor: float) -> None:
        if window < 1:
            raise ValueError(f"window must be >= 1, got {window}")
        self._window = window
        self._diversity_floor = diversity_floor
        self._reports: deque[GenerationReport] = deque(maxlen=window)

    def feed(self, report: GenerationReport) -> None:
        self._reports.append(report)

    def assess(self) -> Assessment:
        if len(self._reports) < self._window:
            return "healthy"

        total_inserted = sum(r.inserted for r in self._reports)
        if total_inserted > 0:
            return "healthy"

        total_sampled = sum(r.sampled for r in self._reports)
        diversity = total_inserted / total_sampled if total_sampled else 0.0
        if diversity < self._diversity_floor:
            return "hard_restart"
        return "island_reset"

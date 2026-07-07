"""Stall detection (M6 T4, spec §9): a two-signal, offline recommendation
over a sliding window of `search.loop.GenerationReport`s -- no-improvement
window + a verified-activity floor. `StallDetector` only RECOMMENDS a state;
it writes nothing and emits nothing itself (the M7 scheduler is the one that
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
  - Otherwise (`total_inserted == 0`, i.e. no NEW key was found anywhere in
    the window) the two remaining states are distinguished by whether the
    search is still ALIVE: are candidates still passing the certified
    verifier at all, even if every one of them lands on an already-known
    key? That is `verified_activity = sum(inserted + duplicates) /
    sum(sampled)` over the window (both `inserted` and `duplicates` come
    from a `population.consider` call, i.e. a candidate that reached PASS
    under `verify_agreed` -- the difference between them is only whether the
    achieved key was new). Compare `verified_activity` to `diversity_floor`:
    - `verified_activity >= diversity_floor` -> `"island_reset"`: the search
      is CONVERGED, not broken -- samples keep verifying, they just keep
      landing on orbits already in the population (e.g. one island has been
      fully mined out). The recommended remedy is to shift the island/target
      set, not to blow away search state.
    - `verified_activity < diversity_floor` -> `"hard_restart"`: the search
      is DEGENERATE -- samples aren't even verifying (screen rejects,
      verify FAILs/ERRORs dominate), so there is no live signal left to
      redirect. The recommended remedy is a harder reset.

**Why the earlier "diversity = inserted / sampled" formulation was wrong:**
that proxy only credits NEW keys in its numerator, but by construction the
diversity branch is only ever reached when `total_inserted == 0` (that's
the `if total_inserted > 0: return "healthy"` guard above) -- so the old
`diversity` was trivially `0.0` on every path that reached it, and any
`diversity_floor > 0` collapsed the whole branch to `"hard_restart"`,
making `"island_reset"` unreachable for any realistic (positive) floor. The
fix widens the numerator to `inserted + duplicates` -- i.e. it asks "is
verification still succeeding?" rather than "did verification succeed on
something NEW?" (the latter is already fully covered by the `total_inserted
> 0` branch above) -- which is what actually distinguishes "converged onto
known territory" (island_reset) from "nothing verifies any more"
(hard_restart), and makes both branches genuinely reachable for any
`diversity_floor` in `[0, 1]`.
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
        total_verified = sum(r.inserted + r.duplicates for r in self._reports)
        verified_activity = total_verified / total_sampled if total_sampled else 0.0
        if verified_activity >= self._diversity_floor:
            return "island_reset"
        return "hard_restart"

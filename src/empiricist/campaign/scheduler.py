"""Scheduler (M7 T2, spec §9): deterministic weighted round-robin over the
two live moves (SEARCH, CONJECTURE -- ENUMERATE is a precondition, not
scheduled) plus a small, fully-enumerable stop/park state machine.

**Rotation.** Each move carries an integer weight >= 1. `next_move()` walks
a materialized cycle list (`[move] * weight` per active move, concatenated
in `("search", "conjecture")` order) round-robin -- e.g. weights
`{search: 3, conjecture: 1}` (the default: `search = cfg.conjecture_every`,
`conjecture = 1`) yields `search, search, search, conjecture, search, ...`.
The cycle is rebuilt (position reset to 0) whenever a weight changes or a
move is dropped from rotation -- deterministic and side-effect-free to
inspect (`next_move()` never mutates weights, only its own cursor).

**Progress bookkeeping (`record`).** Every call reports whether the move's
most recent wave made forward progress (SEARCH: `report.inserted > 0`, a
genuinely new population key; CONJECTURE: at least one artifact landed
`CONJECTURED` this wave). Progress resets that move's consecutive
no-progress streak to 0; no progress increments it. The streak has two
uses, one per move:

- CONJECTURE: this streak is ALSO the halving trigger -- once it reaches
  `cfg.scheduler_patience` consecutive no-progress waves AND the weight is
  still above the floor (1), halve the weight (`max(1, weight // 2)`) and
  reset the streak to start counting toward the next halving (or, once the
  floor is reached, toward `should_stop`'s exhaustion check below).
- SEARCH: the streak is tracked the same way but is NEVER the halving
  trigger -- SEARCH's richer two-signal `StallDetector` assessment is a
  strictly better halving signal than a bare progress bit, so halving is
  driven exclusively by `note_stall` (below). The streak still feeds
  `should_stop`'s exhaustion check, on equal footing with CONJECTURE's.

**Stall halving (`note_stall`).** The caller owns the `StallDetector`
instance (this class receives it in `__init__` purely for callers/tests to
reach via `.stall`; the scheduler itself never calls `.feed()`/`.assess()`
-- staying pure means it only ever reacts to values callers hand it). Feed a
generation's report to `stall`, compute `stall.assess()`, and pass the
result here as `level`. Any level other than `"healthy"` halves SEARCH's
weight (floored at 1), same halving primitive CONJECTURE's streak uses.

**Targets exhausted (`note_targets_exhausted`).** SEARCH has no open targets
left at `cfg.search_target_n` (an empty `open_targets(...)` -- distinct
from a stall: there is nothing to sample, not merely nothing new found).
This drops `"search"` from the rotation entirely (not merely floors its
weight) and rebuilds the cycle so `next_move()` only ever returns
`"conjecture"` from then on. It does NOT by itself stop the campaign --
CONJECTURE can still be making genuine progress mining the same dataset.

**Stopping (`should_stop`).** Checked BEFORE `next_move()` each iteration,
in this fixed order:

1. `cfg.max_cost_usd` set and `spent.cost_usd >= max_cost_usd` -> `"budget_cost"`.
   This is a between-wave stop threshold, not a reservation-backed hard cap.
2. `cfg.max_generations` set and `gen > max_generations` -> `"budget_generations"`.
   `gen` is the next SEARCH generation number, so the configured value is
   inclusive: `max_generations=1` permits generation 1 and then stops.
3. Both moves "exhausted" -> `"stalled_out"`. A move is exhausted iff either
   (a) it has been dropped from rotation (SEARCH via `note_targets_
   exhausted`), or (b) its weight has bottomed out at 1 AND its
   no-progress streak has reached `cfg.scheduler_patience` again post-floor
   (i.e. `cfg.scheduler_patience` consecutive no-progress waves with
   nothing left to halve). This is deliberately symmetric across both
   moves -- SEARCH's "dropped" case is just the degenerate instance where
   there is no weight left to floor at all.
4. Otherwise `None` -- keep going.

`should_stop` never mutates state; it is a pure read of the streak/weight/
active bookkeeping `record`/`note_stall`/`note_targets_exhausted` maintain.
`f3_alarm`/`KeyboardInterrupt` are NOT scheduler concerns -- the orchestrator
handles those directly (a scheduler stop reason is never raised as an
exception, and an alarm is never a scheduler decision).

**PROVE park (`maybe_open_proof_gate`).** Spec §9: v0 never acts on a
CONJECTURED claim -- it only parks a human gate once. If >=1 CONJECTURED
artifact exists, take the FIRST (oldest, `find_artifacts`' order) and open a
`PROOF_CAMPAIGN` gate for it UNLESS one is already pending for that exact
artifact (`Gates.has_pending`, the documented scheduler seam) -- so calling
this every iteration (as the orchestrator does, after every move) is safe
and idempotent: the first call opens the gate, every later call is a no-op
until that gate is resolved.
"""

from __future__ import annotations

import logging

from empiricist.config import RunConfig
from empiricist.ledger.db import Ledger, Spent
from empiricist.ledger.gates import Gates
from empiricist.ledger.models import Status
from empiricist.search.stall import Assessment, StallDetector

logger = logging.getLogger(__name__)

MOVES: tuple[str, ...] = ("search", "conjecture")


class Scheduler:
    def __init__(self, cfg: RunConfig, stall: StallDetector) -> None:
        self._cfg = cfg
        self.stall = stall  # held for callers/tests only -- see module docstring.
        self._patience = max(1, cfg.scheduler_patience)
        self._weights: dict[str, int] = {
            "search": max(1, cfg.conjecture_every),
            "conjecture": 1,
        }
        self._active: list[str] = ["search", "conjecture"]
        self._streak: dict[str, int] = {"search": 0, "conjecture": 0}
        self._cycle: list[str] = []
        self._pos = 0
        self._rebuild_cycle()

    # -- rotation -------------------------------------------------------------

    def _rebuild_cycle(self) -> None:
        self._cycle = [m for m in self._active for _ in range(self._weights[m])]
        self._pos = 0

    def next_move(self) -> str:
        if not self._cycle:
            raise RuntimeError("Scheduler.next_move: no active moves left in rotation")
        move = self._cycle[self._pos % len(self._cycle)]
        self._pos += 1
        return move

    # -- progress bookkeeping --------------------------------------------------

    def record(self, move: str, progressed: bool) -> None:
        self._require_move(move)
        if progressed:
            self._streak[move] = 0
            return
        self._streak[move] += 1
        if (
            move == "conjecture"
            and self._weights[move] > 1
            and self._streak[move] >= self._patience
        ):
            self._halve(move)
            self._streak[move] = 0

    def note_stall(self, move: str, level: Assessment) -> None:
        self._require_move(move)
        if level != "healthy":
            self._halve(move)

    def note_targets_exhausted(self) -> None:
        if "search" in self._active:
            self._active.remove("search")
            self._rebuild_cycle()
            logger.info("scheduler: SEARCH has no open targets -- dropped from rotation")

    def _halve(self, move: str) -> None:
        old = self._weights[move]
        new = max(1, old // 2)
        if new != old:
            self._weights[move] = new
            self._rebuild_cycle()
            logger.info("scheduler: halved %s weight %d -> %d", move, old, new)

    def _require_move(self, move: str) -> None:
        if move not in MOVES:
            raise ValueError(f"unknown move {move!r} (expected one of {MOVES})")

    # -- stopping ---------------------------------------------------------------

    def should_stop(self, spent: Spent, gen: int) -> str | None:
        if self._cfg.max_cost_usd is not None and spent.cost_usd >= self._cfg.max_cost_usd:
            return "budget_cost"
        if self._cfg.max_generations is not None and gen > self._cfg.max_generations:
            return "budget_generations"
        if self._is_exhausted("search") and self._is_exhausted("conjecture"):
            return "stalled_out"
        return None

    def _is_exhausted(self, move: str) -> bool:
        if move not in self._active:
            return True
        return self._weights[move] == 1 and self._streak[move] >= self._patience

    # -- PROVE park ---------------------------------------------------------------

    def maybe_open_proof_gate(self, gates: Gates, ledger: Ledger) -> str | None:
        conjectured = ledger.find_artifacts(status=Status.CONJECTURED)
        if not conjectured:
            return None
        first = conjectured[0]  # find_artifacts orders oldest -> newest
        if gates.has_pending(artifact_id=first.id, kind="PROOF_CAMPAIGN"):
            return None
        gate = gates.open(
            "PROOF_CAMPAIGN",
            artifact_id=first.id,
            note="parked: >=1 CONJECTURED artifact awaiting a human-approved PROVE campaign",
        )
        logger.info(
            "scheduler: opened PROOF_CAMPAIGN gate %s for artifact %s", gate.id, first.id
        )
        return gate.id

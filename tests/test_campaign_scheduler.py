"""Tests for the M7 T2 Scheduler (campaign/scheduler.py): weighted
round-robin rotation, weight halving (note_stall for SEARCH, record's
internal streak for CONJECTURE), should_stop's budget/stalled_out matrix,
note_targets_exhausted dropping SEARCH from rotation, and the idempotent
PROOF_CAMPAIGN park. See scheduler.py's module docstring for the exact
semantics these tests pin down.
"""

from __future__ import annotations

import pytest

from empiricist.campaign.scheduler import Scheduler
from empiricist.campaign.state import CampaignState
from empiricist.config import RunConfig
from empiricist.ledger.db import Spent
from empiricist.ledger.ingest import ingest_artifact
from empiricist.ledger.models import Status
from empiricist.search.stall import StallDetector

ZERO_SPENT = Spent(cost_usd=0.0, tokens_in=0, tokens_out=0)


def make_scheduler(**cfg_kwargs) -> Scheduler:
    cfg = RunConfig(**cfg_kwargs)
    stall = StallDetector(window=cfg.stall_window_generations, diversity_floor=cfg.diversity_floor)
    return Scheduler(cfg, stall)


@pytest.fixture()
def state(tmp_path):
    st = CampaignState.load(tmp_path / "run")
    yield st
    st.close()


# -- rotation -----------------------------------------------------------------


def test_default_cycle_is_conjecture_every_to_one():
    sched = make_scheduler(conjecture_every=3)
    moves = [sched.next_move() for _ in range(8)]
    assert moves == [
        "search", "search", "search", "conjecture",
        "search", "search", "search", "conjecture",
    ]


def test_conjecture_every_one_is_even_alternation():
    sched = make_scheduler(conjecture_every=1)
    moves = [sched.next_move() for _ in range(4)]
    assert moves == ["search", "conjecture", "search", "conjecture"]


def test_next_move_cursor_repeats_the_same_cycle():
    sched = make_scheduler(conjecture_every=2)
    first_round = [sched.next_move() for _ in range(3)]
    second_round = [sched.next_move() for _ in range(3)]
    assert first_round == second_round == ["search", "search", "conjecture"]


def test_stall_object_is_reachable_but_not_touched_by_the_scheduler():
    """Scheduler's __init__ takes a StallDetector for callers/tests to reach
    (`.stall`), but stays pure -- it never calls .feed()/.assess() on it
    itself; halving only ever reacts to values passed into note_stall.
    Proof by observation: even with a wildly over-weighted SEARCH move that
    would trip a real stall many times over if fed real reports, an UNFED
    detector still reports "healthy" (fewer than `window` reports seen) --
    so nothing inside the scheduler is calling .feed()/.assess() on it."""
    cfg = RunConfig(conjecture_every=8)
    stall = StallDetector(window=cfg.stall_window_generations, diversity_floor=cfg.diversity_floor)
    sched = Scheduler(cfg, stall)
    assert sched.stall is stall
    for _ in range(20):
        sched.next_move()
    assert stall.assess() == "healthy"


# -- weight halving: note_stall (SEARCH) ---------------------------------------


def test_note_stall_healthy_does_not_halve():
    sched = make_scheduler(conjecture_every=4)
    sched.note_stall("search", "healthy")
    moves = [sched.next_move() for _ in range(5)]
    assert moves.count("search") == 4
    assert moves.count("conjecture") == 1


def test_note_stall_hard_restart_halves_search_weight():
    sched = make_scheduler(conjecture_every=4)
    sched.note_stall("search", "hard_restart")
    moves = [sched.next_move() for _ in range(3)]
    assert moves.count("search") == 2
    assert moves.count("conjecture") == 1


def test_note_stall_island_reset_also_halves():
    sched = make_scheduler(conjecture_every=4)
    sched.note_stall("search", "island_reset")
    moves = [sched.next_move() for _ in range(3)]
    assert moves.count("search") == 2


def test_note_stall_halving_floors_at_one():
    sched = make_scheduler(conjecture_every=1)  # search weight already 1
    sched.note_stall("search", "hard_restart")
    moves = [sched.next_move() for _ in range(4)]
    assert moves == ["search", "conjecture", "search", "conjecture"]


def test_note_stall_repeated_halves_down_to_floor():
    sched = make_scheduler(conjecture_every=8)
    sched.note_stall("search", "hard_restart")  # 8 -> 4
    sched.note_stall("search", "hard_restart")  # 4 -> 2
    sched.note_stall("search", "hard_restart")  # 2 -> 1
    moves = [sched.next_move() for _ in range(2)]
    assert moves == ["search", "conjecture"]


def test_note_stall_unknown_move_raises():
    sched = make_scheduler()
    with pytest.raises(ValueError):
        sched.note_stall("bogus", "healthy")


# -- progress bookkeeping (record) ---------------------------------------------


def test_record_progress_resets_streak():
    sched = make_scheduler(conjecture_every=1, scheduler_patience=2)
    sched.record("search", False)
    sched.record("search", True)  # resets the streak
    sched.record("search", False)
    # One post-reset miss is not enough to exhaust a patience=2 move.
    assert sched.should_stop(ZERO_SPENT, gen=1) is None
    sched.note_targets_exhausted()  # make search's exhaustion the deciding factor
    assert sched.should_stop(ZERO_SPENT, gen=1) is None  # conjecture still fresh (streak=0)


def test_record_conjecture_never_halves_below_its_floor_of_one():
    """conjecture's weight always starts at (and never exceeds) 1, so
    reaching patience never triggers an actual halving for it -- but the
    streak still accumulates past patience (record's `weight > 1` guard is
    what makes that possible: only an ACTUAL halving resets the streak).
    The rotation proportions must stay untouched throughout."""
    sched = make_scheduler(conjecture_every=3, scheduler_patience=2)
    sched.record("conjecture", False)
    sched.record("conjecture", False)  # streak reaches patience=2, weight stays 1
    sched.record("conjecture", False)  # streak keeps growing past patience
    moves = [sched.next_move() for _ in range(4)]
    assert moves == ["search", "search", "search", "conjecture"]


def test_record_unknown_move_raises():
    sched = make_scheduler()
    with pytest.raises(ValueError):
        sched.record("bogus", True)


# -- note_targets_exhausted ------------------------------------------------------


def test_note_targets_exhausted_drops_search_from_rotation():
    sched = make_scheduler(conjecture_every=3)
    sched.note_targets_exhausted()
    moves = [sched.next_move() for _ in range(4)]
    assert moves == ["conjecture", "conjecture", "conjecture", "conjecture"]


def test_note_targets_exhausted_is_idempotent():
    sched = make_scheduler(conjecture_every=3)
    sched.note_targets_exhausted()
    sched.note_targets_exhausted()  # must not raise or double-remove
    assert sched.next_move() == "conjecture"


# -- should_stop: budget matrix --------------------------------------------------


def test_should_stop_none_when_unbounded():
    sched = make_scheduler()
    assert sched.should_stop(ZERO_SPENT, gen=1000) is None


def test_should_stop_budget_cost():
    sched = make_scheduler(max_cost_usd=1.0)
    assert sched.should_stop(Spent(cost_usd=0.99, tokens_in=0, tokens_out=0), gen=1) is None
    assert sched.should_stop(Spent(cost_usd=1.0, tokens_in=0, tokens_out=0), gen=1) == "budget_cost"
    assert sched.should_stop(Spent(cost_usd=5.0, tokens_in=0, tokens_out=0), gen=1) == "budget_cost"


def test_should_stop_budget_generations():
    sched = make_scheduler(max_generations=5)
    assert sched.should_stop(ZERO_SPENT, gen=4) is None
    assert sched.should_stop(ZERO_SPENT, gen=5) is None
    assert sched.should_stop(ZERO_SPENT, gen=6) == "budget_generations"


def test_should_stop_cost_checked_before_generations():
    sched = make_scheduler(max_cost_usd=1.0, max_generations=5)
    spent = Spent(cost_usd=1.0, tokens_in=0, tokens_out=0)
    assert sched.should_stop(spent, gen=6) == "budget_cost"


# -- should_stop: stalled_out ------------------------------------------------------


def test_should_stop_stalled_out_requires_both_moves_exhausted():
    sched = make_scheduler(conjecture_every=3, scheduler_patience=2)
    sched.note_targets_exhausted()  # SEARCH exhausted (dropped)
    assert sched.should_stop(ZERO_SPENT, gen=1) is None  # conjecture still fresh
    sched.record("conjecture", False)
    assert sched.should_stop(ZERO_SPENT, gen=1) is None  # streak=1 < patience=2
    sched.record("conjecture", False)  # streak=2 >= patience -> conjecture exhausted too
    assert sched.should_stop(ZERO_SPENT, gen=1) == "stalled_out"


def test_should_stop_stalled_out_via_symmetric_halving_and_streaks():
    """The pure path, without note_targets_exhausted: SEARCH halved down to
    its floor via repeated note_stall, then both moves' streaks reach
    patience via record() -- stalled_out fires without ever dropping a move
    from the rotation."""
    sched = make_scheduler(conjecture_every=2, scheduler_patience=2)
    sched.note_stall("search", "hard_restart")  # 2 -> 1 (floor)
    sched.record("search", False)
    sched.record("search", False)  # search streak=2 >= patience, weight already floor
    sched.record("conjecture", False)
    sched.record("conjecture", False)  # conjecture streak=2 >= patience, weight already floor
    assert sched.should_stop(ZERO_SPENT, gen=1) == "stalled_out"
    # both moves are still IN rotation (exhausted != removed, for conjecture)
    moves = [sched.next_move() for _ in range(2)]
    assert set(moves) == {"search", "conjecture"}


def test_should_stop_not_stalled_out_when_only_one_move_exhausted():
    sched = make_scheduler(conjecture_every=2, scheduler_patience=1)
    sched.record("conjecture", False)  # conjecture exhausted (streak=1 >= patience=1)
    assert sched.should_stop(ZERO_SPENT, gen=1) is None  # search untouched, not exhausted


# -- maybe_open_proof_gate -------------------------------------------------------


def test_maybe_open_proof_gate_none_when_no_conjectured(state):
    sched = make_scheduler()
    assert sched.maybe_open_proof_gate(state.gates, state.ledger) is None


def test_maybe_open_proof_gate_opens_for_the_conjectured_artifact(state):
    sched = make_scheduler()
    art = ingest_artifact(
        state.ledger, state.store, content=b"claim-1", kind="statement",
        problem="P5", title="t1", status=Status.CONJECTURED,
    )
    gate_id = sched.maybe_open_proof_gate(state.gates, state.ledger)
    assert gate_id is not None

    gates = state.gates.list(kind="PROOF_CAMPAIGN", artifact_id=art.id)
    assert len(gates) == 1
    assert gates[0].id == gate_id
    assert gates[0].state == "pending"


def test_maybe_open_proof_gate_idempotent_across_calls(state):
    sched = make_scheduler()
    ingest_artifact(
        state.ledger, state.store, content=b"claim-1", kind="statement",
        problem="P5", title="t1", status=Status.CONJECTURED,
    )
    first = sched.maybe_open_proof_gate(state.gates, state.ledger)
    second = sched.maybe_open_proof_gate(state.gates, state.ledger)
    assert first is not None
    assert second is None  # already pending -- no duplicate gate

    assert len(state.gates.list(kind="PROOF_CAMPAIGN")) == 1


def test_maybe_open_proof_gate_targets_only_the_first_conjectured_artifact(state):
    sched = make_scheduler()
    first_art = ingest_artifact(
        state.ledger, state.store, content=b"claim-1", kind="statement",
        problem="P5", title="t1", status=Status.CONJECTURED,
    )
    ingest_artifact(
        state.ledger, state.store, content=b"claim-2", kind="statement",
        problem="P5", title="t2", status=Status.CONJECTURED,
    )
    sched.maybe_open_proof_gate(state.gates, state.ledger)
    gates = state.gates.list(kind="PROOF_CAMPAIGN")
    assert len(gates) == 1
    assert gates[0].artifact_id == first_art.id


def test_maybe_open_proof_gate_respects_an_externally_opened_pending_gate(state):
    """has_pending guard: a gate opened by something ELSE for this artifact
    (not maybe_open_proof_gate itself) must still be respected."""
    sched = make_scheduler()
    art = ingest_artifact(
        state.ledger, state.store, content=b"claim-1", kind="statement",
        problem="P5", title="t1", status=Status.CONJECTURED,
    )
    state.gates.open("PROOF_CAMPAIGN", artifact_id=art.id, note="manual")
    assert sched.maybe_open_proof_gate(state.gates, state.ledger) is None
    assert len(state.gates.list(kind="PROOF_CAMPAIGN")) == 1

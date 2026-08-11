"""Tests for the M7 T2 orchestrator (`campaign/orchestrator.py`):
`run_campaign`'s end-to-end loop over a scripted `FakeLLMClient`, generation
numbering resume, budget stop, and the F3Alarm abort path. Offline, fast
configs (tier0_n=5, tier1_n=4 -- see test_campaign_moves.py's FAST_CFG for
the empirically-checked shape: exactly one open orbit, at n=5).
"""

from __future__ import annotations

import asyncio

import pytest

import empiricist.campaign.orchestrator as orchestrator_mod
from empiricist.campaign.moves import dataset_rows, ensure_enumerate, open_targets
from empiricist.campaign.orchestrator import CampaignSummary, run_campaign
from empiricist.campaign.state import CampaignState
from empiricist.config import RunConfig
from empiricist.ledger.models import Status
from empiricist.llm.client import FakeLLMClient
from empiricist.llm.models import BillingUnknownError, LLMResult
from empiricist.llm.roles import ROLES
from empiricist.search.loop import F3Alarm, GenerationReport

FAST_KW = dict(tier0_n=5, tier1_n=4, search_target_n=5, targets_per_gen=8)


def run(coro):
    return asyncio.run(coro)


def make_result(parsed: dict | None) -> LLMResult:
    return LLMResult(
        text="", parsed=parsed, stop_reason="tool_use" if parsed else "end_turn",
        is_error=False, input_tokens=1, output_tokens=1, cache_read_tokens=0,
        cache_creation_tokens=0, cost_usd=0.0, duration_ms=1,
        session_id="s", uuid="u", model="claude-fable-5",
    )


TRUE_CONJECTURE = {
    "family": "path", "closed_form": "N-3",
    "predicted_values": {"3": 0, "4": 1, "5": 2}, "confidence": 0.9,
}


def scripted_client() -> FakeLLMClient:
    """32 refusals (fills exactly one SEARCH generation's k=32 samples),
    then ONE grounded true conjecture (the first of CONJECTURE's k=8
    samples) -- everything after is exhausted-list None (more refusals for
    the rest of that wave, and for a second SEARCH generation)."""
    assert ROLES["searcher"].k == 32
    assert ROLES["conjecturer"].k == 8
    scripted = [make_result(None)] * 32 + [make_result(TRUE_CONJECTURE)]
    return FakeLLMClient(scripted)


# -- end-to-end -----------------------------------------------------------------


def test_run_campaign_two_search_gens_and_one_conjecture_wave(tmp_path):
    run_dir = tmp_path / "run"
    # conjecture_every=1 -> cycle [search, conjecture]; max_generations=2 lets
    # exactly search(gen=1), conjecture(wave), search(gen=2) run before the
    # top-of-loop budget check stops it (see module docstring / plan notes).
    cfg = RunConfig(**FAST_KW, conjecture_every=1, max_generations=2)
    client = scripted_client()

    summary = run(run_campaign(run_dir, cfg, client))

    assert isinstance(summary, CampaignSummary)
    assert summary.generations == 2
    assert summary.conjecture_waves == 1
    assert summary.conjectured == 1
    assert summary.refuted == 0
    assert summary.exact_upgrades == 0
    assert summary.spent_cost_usd == 0.0  # FakeLLMClient never records a runs row
    assert summary.stop_reason == "budget_generations"
    assert summary.f3_alarm is False

    state = CampaignState.load(run_dir)
    try:
        gen_events = state.population.events(trigger="generation")
        assert [e.gen for e in gen_events] == [1, 2]

        end_events = state.population.events(trigger="campaign_end")
        assert len(end_events) == 1
        assert end_events[0].detail["stop_reason"] == "budget_generations"
        assert end_events[0].detail["conjectured"] == 1

        conjectured_artifacts = state.ledger.find_artifacts(status=Status.CONJECTURED)
        assert len(conjectured_artifacts) == 1

        # the scheduler parked a PROOF_CAMPAIGN gate for the sole CONJECTURED
        # artifact along the way (maybe_open_proof_gate, called after every move).
        gates = state.gates.list(kind="PROOF_CAMPAIGN")
        assert len(gates) == 1
        assert gates[0].artifact_id == conjectured_artifacts[0].id
        assert gates[0].state == "pending"
    finally:
        state.close()


def test_run_campaign_resumes_generation_numbering(tmp_path):
    run_dir = tmp_path / "run"
    cfg = RunConfig(**FAST_KW, conjecture_every=1, max_generations=2)
    run(run_campaign(run_dir, cfg, scripted_client()))  # logs generation events [1, 2]

    cfg2 = RunConfig(**FAST_KW, conjecture_every=1, max_generations=3)
    second_client = FakeLLMClient([make_result(None)] * 32)  # one more search gen, all refusals
    summary2 = run(run_campaign(run_dir, cfg2, second_client))

    assert summary2.generations == 1
    assert summary2.stop_reason == "budget_generations"

    state = CampaignState.load(run_dir)
    try:
        gen_events = state.population.events(trigger="generation")
        assert [e.gen for e in gen_events] == [1, 2, 3]  # continues, never repeats/collides
    finally:
        state.close()


# -- budget stop ------------------------------------------------------------------


def test_run_campaign_max_generations_one_runs_generation_one(tmp_path):
    run_dir = tmp_path / "run"
    cfg = RunConfig(**FAST_KW, max_generations=1)
    client = FakeLLMClient([make_result(None)] * 32)

    summary = run(run_campaign(run_dir, cfg, client))

    assert summary.stop_reason == "budget_generations"
    assert summary.generations == 1
    assert summary.conjecture_waves == 0
    assert len(client.calls) == 32

    state = CampaignState.load(run_dir)
    try:
        end_events = state.population.events(trigger="campaign_end")
        assert len(end_events) == 1
        assert end_events[0].detail["stop_reason"] == "budget_generations"
    finally:
        state.close()


# -- F3Alarm ------------------------------------------------------------------------


def test_run_campaign_f3_alarm_aborts_and_is_recorded(tmp_path, monkeypatch):
    run_dir = tmp_path / "run"
    cfg = RunConfig(**FAST_KW)  # default conjecture_every -> SEARCH goes first

    async def boom(*_args, **_kwargs):
        raise F3Alarm({"disagreement": True})

    monkeypatch.setattr(orchestrator_mod, "search_move", boom)

    summary = run(run_campaign(run_dir, cfg, FakeLLMClient([])))

    assert summary.f3_alarm is True
    assert summary.stop_reason == "f3_alarm"
    assert summary.generations == 0

    state = CampaignState.load(run_dir)
    try:
        end_events = state.population.events(trigger="campaign_end")
        assert len(end_events) == 1
        assert end_events[0].detail["f3_alarm"] is True
        assert end_events[0].detail["stop_reason"] == "f3_alarm"
    finally:
        state.close()


# -- KeyboardInterrupt / arbitrary exception still logs campaign_end -----------------


def test_run_campaign_unexpected_exception_still_logs_campaign_end_and_reraises(
    tmp_path, monkeypatch
):
    """An exception OUTSIDE the per-move isolation guard (here: ENUMERATE
    itself, before the loop starts) still propagates -- and the finally
    block still logs campaign_end. (Per-move exceptions are isolated, see
    the move-error tests below.)"""
    run_dir = tmp_path / "run"
    cfg = RunConfig(**FAST_KW)

    def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(orchestrator_mod, "ensure_enumerate", boom)

    with pytest.raises(RuntimeError, match="boom"):
        run(run_campaign(run_dir, cfg, FakeLLMClient([])))

    state = CampaignState.load(run_dir)
    try:
        end_events = state.population.events(trigger="campaign_end")
        assert len(end_events) == 1  # the finally block ran even though we raised
    finally:
        state.close()


def test_run_campaign_failing_campaign_end_log_does_not_mask_original_error(
    tmp_path, monkeypatch, capsys
):
    """Review M3: if the campaign_end log_event itself fails (e.g. the
    ledger connection is what broke), the ORIGINAL exception must still be
    the one that propagates; the log failure goes to stderr."""
    run_dir = tmp_path / "run"
    cfg = RunConfig(**FAST_KW)

    def boom(*_args, **_kwargs):
        raise RuntimeError("original error")

    monkeypatch.setattr(orchestrator_mod, "ensure_enumerate", boom)

    real_load = CampaignState.load

    def load_with_broken_logger(run_dir_arg):
        state = real_load(run_dir_arg)
        original_log = state.population.log_event

        def flaky_log(gen, trigger, detail=None):
            if trigger == "campaign_end":
                raise RuntimeError("ledger connection lost")
            return original_log(gen, trigger, detail)

        state.population.log_event = flaky_log
        return state

    monkeypatch.setattr(orchestrator_mod.CampaignState, "load", load_with_broken_logger)

    with pytest.raises(RuntimeError, match="original error"):
        run(run_campaign(run_dir, cfg, FakeLLMClient([])))

    assert "failed to log campaign_end" in capsys.readouterr().err


# -- move-error isolation + circuit breaker (overnight-safety review I2) --------------


def _empty_report(gen: int) -> GenerationReport:
    return GenerationReport(
        gen=gen, sampled=1, no_artifact=1, screened_out=0, verify_fail=0,
        verify_error=0, inserted=0, duplicates=0, exact_upgrades=(), screen_reasons=(),
    )


def test_run_campaign_move_errors_are_isolated_and_campaign_continues(tmp_path, monkeypatch):
    """A search_move that raises twice then succeeds: the two failures are
    logged as durable move_error events and counted as no-progress, then
    the campaign carries on to the budget stop."""
    run_dir = tmp_path / "run"
    cfg = RunConfig(**FAST_KW, max_generations=1)  # default breaker threshold = 3

    calls = {"n": 0}

    async def flaky(_state, _cfg, _client, gen):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise RuntimeError(f"transport blip {calls['n']}")
        return _empty_report(gen)

    monkeypatch.setattr(orchestrator_mod, "search_move", flaky)

    summary = run(run_campaign(run_dir, cfg, FakeLLMClient([])))

    assert summary.stop_reason == "budget_generations"
    assert summary.move_errors == 2
    assert summary.generations == 1  # only the third (successful) wave counted
    assert calls["n"] == 3

    state = CampaignState.load(run_dir)
    try:
        errs = state.population.events(trigger="move_error")
        assert len(errs) == 2
        assert all(e.detail["move"] == "search" for e in errs)
        assert "transport blip 1" in errs[0].detail["error"]
        assert "transport blip 2" in errs[1].detail["error"]
    finally:
        state.close()


def test_run_campaign_consecutive_move_errors_trip_the_circuit_breaker(tmp_path, monkeypatch):
    """A persistently-broken transport must not spin forever on an uncapped
    campaign: max_consecutive_move_errors consecutive failures stop it with
    stop_reason='move_errors'."""
    run_dir = tmp_path / "run"
    cfg = RunConfig(**FAST_KW)  # NO budget caps -- only the breaker can stop this

    async def dead(*_args, **_kwargs):
        raise RuntimeError("dead transport")

    monkeypatch.setattr(orchestrator_mod, "search_move", dead)

    summary = run(run_campaign(run_dir, cfg, FakeLLMClient([])))

    assert summary.stop_reason == "move_errors"
    assert summary.move_errors == cfg.max_consecutive_move_errors
    assert summary.generations == 0

    state = CampaignState.load(run_dir)
    try:
        errs = state.population.events(trigger="move_error")
        assert len(errs) == cfg.max_consecutive_move_errors

        end_events = state.population.events(trigger="campaign_end")
        assert len(end_events) == 1
        assert end_events[0].detail["stop_reason"] == "move_errors"
    finally:
        state.close()


def test_run_campaign_unknown_billing_stops_immediately(tmp_path, monkeypatch):
    run_dir = tmp_path / "run"
    cfg = RunConfig(**FAST_KW)
    calls = {"n": 0}

    async def ambiguous(*_args, **_kwargs):
        calls["n"] += 1
        raise BillingUnknownError("provider accepted a call with no usage receipt")

    monkeypatch.setattr(orchestrator_mod, "search_move", ambiguous)

    summary = run(run_campaign(run_dir, cfg, FakeLLMClient([])))

    assert calls["n"] == 1
    assert summary.stop_reason == "billing_unknown"
    assert summary.move_errors == 0
    state = CampaignState.load(run_dir)
    try:
        events = state.population.events(trigger="billing_unknown")
        assert len(events) == 1
        assert events[0].detail["move"] == "search"
    finally:
        state.close()


def test_run_campaign_f3_alarm_still_stops_the_world_not_isolated(tmp_path, monkeypatch):
    """F3Alarm is an Exception subclass -- it must keep its dedicated
    stop-the-world handling, never be swallowed by move-error isolation."""
    run_dir = tmp_path / "run"
    cfg = RunConfig(**FAST_KW)

    async def alarm(*_args, **_kwargs):
        raise F3Alarm({"disagreement": True})

    monkeypatch.setattr(orchestrator_mod, "search_move", alarm)

    summary = run(run_campaign(run_dir, cfg, FakeLLMClient([])))

    assert summary.f3_alarm is True
    assert summary.stop_reason == "f3_alarm"
    assert summary.move_errors == 0  # never entered the isolation path


# -- duplicate-conjecture resume (overnight-safety review C1: the wedge reproducer) ----


def test_run_campaign_resume_re_mines_same_conjecture_without_wedging(tmp_path):
    """The C1 reproducer: session 1 lands a CONJECTURED artifact; session 2
    re-mines the byte-identical conjecture (the model rediscovering
    yesterday's closed form after resume). Before the dedupe fix this
    crashed with sqlite3.IntegrityError on the artifact PRIMARY KEY on
    EVERY resume -- a permanent wedge. Now: the duplicate is skipped, the
    wave counts as no progress, and the campaign completes."""
    run_dir = tmp_path / "run"
    cfg = RunConfig(**FAST_KW, conjecture_every=1, max_generations=2)
    run(run_campaign(run_dir, cfg, scripted_client()))  # session 1: conjecture lands

    cfg2 = RunConfig(**FAST_KW, conjecture_every=1, max_generations=4)
    # session 2: one search wave of refusals, then the SAME conjecture again.
    client2 = FakeLLMClient([make_result(None)] * 32 + [make_result(TRUE_CONJECTURE)])
    summary2 = run(run_campaign(run_dir, cfg2, client2))  # must NOT raise

    assert summary2.stop_reason == "budget_generations"
    assert summary2.conjectured == 0   # duplicate: skipped, no progress
    assert summary2.move_errors == 0   # dedupe handled it -- NOT error isolation

    state = CampaignState.load(run_dir)
    try:
        conjectured = state.ledger.find_artifacts(status=Status.CONJECTURED)
        assert len(conjectured) == 1  # still exactly one artifact
        assert len(state.ledger.evidence_for(conjectured[0].id)) == 1  # one attack, ever
    finally:
        state.close()


# -- solved-target filtering (overnight-safety review I3) -------------------------------


def test_run_campaign_all_targets_solved_drops_search_and_stalls_out(tmp_path):
    """When every open orbit at search_target_n already has a population
    elite at/below target_f, SEARCH genuinely runs out of targets: the
    scheduler drops it from rotation (note_targets_exhausted fires for
    real) and the campaign winds down via conjecture patience to
    'stalled_out' -- instead of re-targeting solved orbits forever."""
    run_dir = tmp_path / "run"
    cfg = RunConfig(**FAST_KW, conjecture_every=1)

    state = CampaignState.load(run_dir)
    art = ensure_enumerate(state, cfg)
    rows = dataset_rows(state, art)
    [target] = open_targets(rows, cfg.search_target_n, cfg.targets_per_gen)
    # A certified witness at exactly target_f: the orbit is solved.
    state.population.consider(target.lc_orbit_key, 0, "n5", [float(target.target_f)], "c" * 64)
    state.close()

    summary = run(run_campaign(run_dir, cfg, FakeLLMClient([])))  # all-refusal client

    assert summary.stop_reason == "stalled_out"
    assert summary.generations == 0        # search never ran -- no targets left
    assert summary.conjecture_waves == 3   # scheduler_patience no-progress waves

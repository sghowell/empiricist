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
from empiricist.campaign.orchestrator import CampaignSummary, run_campaign
from empiricist.campaign.state import CampaignState
from empiricist.config import RunConfig
from empiricist.ledger.models import Status
from empiricist.llm.client import FakeLLMClient
from empiricist.llm.models import LLMResult
from empiricist.llm.roles import ROLES
from empiricist.search.loop import F3Alarm

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
    # conjecture_every=1 -> cycle [search, conjecture]; max_generations=3 lets
    # exactly search(gen=1), conjecture(wave), search(gen=2) run before the
    # top-of-loop budget check stops it (see module docstring / plan notes).
    cfg = RunConfig(**FAST_KW, conjecture_every=1, max_generations=3)
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
    cfg = RunConfig(**FAST_KW, conjecture_every=1, max_generations=3)
    run(run_campaign(run_dir, cfg, scripted_client()))  # logs generation events [1, 2]

    cfg2 = RunConfig(**FAST_KW, conjecture_every=1, max_generations=4)
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


def test_run_campaign_max_generations_one_stops_before_any_move(tmp_path):
    run_dir = tmp_path / "run"
    cfg = RunConfig(**FAST_KW, max_generations=1)
    client = FakeLLMClient([])

    summary = run(run_campaign(run_dir, cfg, client))

    assert summary.stop_reason == "budget_generations"
    assert summary.generations == 0
    assert summary.conjecture_waves == 0
    assert client.calls == []  # should_stop fired before next_move() ever ran

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
    run_dir = tmp_path / "run"
    cfg = RunConfig(**FAST_KW)

    async def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(orchestrator_mod, "search_move", boom)

    with pytest.raises(RuntimeError, match="boom"):
        run(run_campaign(run_dir, cfg, FakeLLMClient([])))

    state = CampaignState.load(run_dir)
    try:
        end_events = state.population.events(trigger="campaign_end")
        assert len(end_events) == 1  # the finally block ran even though we raised
    finally:
        state.close()

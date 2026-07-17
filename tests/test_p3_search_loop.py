"""Tests for `search/p3_loop.py`'s `P3SearchLoop` (M20a Task 3): propose ->
screen -> verify -> ingest/feedback. Fully offline -- a `FakeLLMClient`
(scripted `BellSchemeOut`-shaped results) exercises the LOOP LOGIC without a
real model call or the (not-yet-existing, Task 4) `ROLES["p3_searcher"]`; a
stub `Role`-shaped object is injected instead (mirrors
`test_formalize_loop.py`'s `FakeVerifier` stand-in pattern).
"""

from __future__ import annotations

import asyncio
import math
import sqlite3

import pytest

from empiricist.domain.p3.verify import AgreedResult
from empiricist.executor.runner import DuplicateRunError
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Run
from empiricist.llm.client import FakeLLMClient
from empiricist.llm.models import Effort, LLMResult
from empiricist.llm.roles import Role
from empiricist.search.p3_loop import P3SearchLoop, P3SearchReport, P3SearchTask
from empiricist.store import Store

_STUB_ROLE = Role(
    name="p3_searcher_stub", system_prompt="stub", effort=Effort.LOW, k=1, active=True,
)


def _bsm_dict(**overrides):
    d = {
        "n_modes": 4,
        "n_ancilla_photons": 0,
        "ancilla": [],
        "mesh": [
            {"kind": "bs", "i": 0, "j": 2, "theta": math.pi / 4, "phi": 0.0},
            {"kind": "bs", "i": 1, "j": 3, "theta": math.pi / 4, "phi": 0.0},
        ],
    }
    d.update(overrides)
    return d


class RunRecordingFakeClient(FakeLLMClient):
    """FakeLLMClient that ALSO opens a runs row per call with the caller's
    run_id, exactly the way the real `ClaudeCodeClient.complete` does
    (`ledger.start_run` -> `DuplicateRunError` on collision) -- so a reused
    run_id surfaces as the same failure it would produce in a live campaign."""

    async def complete(self, role, prompt, *, session_id=None, system_prompt=None,
                       schema=None, run_id=None, ledger=None):
        if ledger is not None and run_id is not None:
            try:
                ledger.start_run(Run(
                    run_id=run_id, move="SAMPLE", role=role.name, model=role.model,
                ))
            except sqlite3.IntegrityError as e:
                raise DuplicateRunError(run_id) from e
        return await super().complete(
            role, prompt, session_id=session_id, system_prompt=system_prompt,
            schema=schema, run_id=run_id, ledger=ledger,
        )


def make_result(parsed: dict | None) -> LLMResult:
    return LLMResult(
        text="", parsed=parsed, stop_reason="tool_use" if parsed else "end_turn",
        is_error=False, input_tokens=1, output_tokens=1, cache_read_tokens=0,
        cache_creation_tokens=0, cost_usd=0.0, duration_ms=1,
        session_id="s", uuid="u", model="claude-fable-5",
    )


def run(coro):
    return asyncio.run(coro)


def make_env(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    st = Store(tmp_path / "store")
    return lg, st


# -- (a) good scheme, round 1 -----------------------------------------------


def test_good_scheme_round_one_ingests_at_verified_n(tmp_path):
    lg, st = make_env(tmp_path)
    client = FakeLLMClient([make_result(_bsm_dict())])
    loop = P3SearchLoop(client, lg, st, max_rounds=6, role=_STUB_ROLE)
    task = P3SearchTask(
        name="t1", goal="find a k=0 scheme with p_avg >= 1/2", context="ctx",
        target_p_avg=0.5,
    )

    report = run(loop.run(task))

    assert isinstance(report, P3SearchReport)
    assert report.ok is True
    assert report.rounds == 1
    assert report.f3_alarm is False
    assert report.artifact_id is not None
    assert len(report.history) == 1
    assert report.history[0][0] == "PASS"
    assert report.best_summary["p_avg"] == pytest.approx(0.5)

    art = lg.get_artifact(report.artifact_id)
    assert art.status.value == "VERIFIED_N"
    assert art.kind == "construction"
    assert art.problem == "P3"

    evs = lg.evidence_for(report.artifact_id)
    assert len(evs) == 1
    assert evs[0].verifier == "p3_scheme_agreed"
    # the CHECKED claim (the task targets, not the scheme dict's own claimed_*
    # fields) is recorded with the evidence -- the certificate is claim +
    # achievement
    assert evs[0].details["claimed_p_avg"] == 0.5
    assert evs[0].details["claimed_p_min"] is None
    assert evs[0].details["claimed_max_leakage"] == 0.0
    lg.close()


# -- run-id freshness: two run() calls with the SAME task never collide ------


def test_two_runs_same_task_same_ledger_do_not_collide_on_run_id(tmp_path):
    """P3 campaigns are overnight/killable: a re-launched run() with the same
    task name must mint fresh run_ids (per-run() nonce), not collide with the
    previous invocation's runs rows (the documented formalize-loop incident)."""
    lg, st = make_env(tmp_path)
    client = RunRecordingFakeClient(
        [make_result(_bsm_dict()), make_result(_bsm_dict())],
    )
    loop = P3SearchLoop(client, lg, st, max_rounds=2, role=_STUB_ROLE)
    task = P3SearchTask(name="same-name", goal="g", context="c", target_p_avg=0.5)

    r1 = run(loop.run(task))
    r2 = run(loop.run(task))  # must NOT raise DuplicateRunError

    assert r1.ok is True
    assert r2.ok is True
    # the duplicate scheme short-circuits to the SAME artifact (idempotent
    # ingest), but both model calls got their own fresh runs rows
    assert r1.artifact_id == r2.artifact_id
    lg.close()


# -- (b) overclaimed target FAILs twice, tracks best, feeds back concretely --


def test_overclaimed_target_fails_twice_tracks_best_and_feeds_back(tmp_path):
    lg, st = make_env(tmp_path)
    client = FakeLLMClient([make_result(_bsm_dict()), make_result(_bsm_dict())])
    loop = P3SearchLoop(client, lg, st, max_rounds=2, role=_STUB_ROLE)
    # The standard BSM only achieves p_avg 0.5; target 0.75 is out of reach for it.
    task = P3SearchTask(
        name="t2", goal="find a scheme with p_avg >= 3/4", context="ctx",
        target_p_avg=0.75,
    )

    report = run(loop.run(task))

    assert report.ok is False
    assert report.rounds == 2
    assert report.artifact_id is None
    assert report.f3_alarm is False
    assert [h[0] for h in report.history] == ["FAIL", "FAIL"]
    assert "FAIL" in report.history[0][1]

    assert report.best is not None
    assert report.best_summary["p_avg"] == pytest.approx(0.5)

    # the feedback's ACHIEVED summary carries the exact raw p_avg -- the same
    # float the verifier's own detail string uses, so the two never contradict
    # (a rounded "p_avg=0.75" next to a detail saying "0.7499999... < 0.75"
    # would read as a self-contradiction to the model)
    exact_p_avg = str(report.best_summary["p_avg"])
    assert f"p_avg={exact_p_avg}" in report.history[0][1]

    # round-2 PROMPT (what the model actually sees) carries round-1's outcome
    # and the achieved p_avg -- concrete, not vague, feedback.
    assert len(client.calls) == 2
    round2_prompt = client.calls[1][1]
    assert "FAIL" in round2_prompt
    assert exact_p_avg in round2_prompt
    lg.close()


# -- (c) screened garbage, then good scheme ----------------------------------


def test_screened_garbage_then_good_scheme(tmp_path):
    lg, st = make_env(tmp_path)
    garbage = _bsm_dict(n_modes=99)  # over the MAX_MODES cap -> ScreenReject
    client = FakeLLMClient([make_result(garbage), make_result(_bsm_dict())])
    loop = P3SearchLoop(client, lg, st, max_rounds=6, role=_STUB_ROLE)
    task = P3SearchTask(name="t3", goal="g", context="c", target_p_avg=0.5)

    report = run(loop.run(task))

    assert report.ok is True
    assert [h[0] for h in report.history] == ["SCREENED", "PASS"]
    assert "n_modes" in report.history[0][1]
    assert report.artifact_id is not None

    round2_prompt = client.calls[1][1]
    assert "SCREENED" in round2_prompt
    lg.close()


# -- (d) verifier ERROR aborts immediately -----------------------------------


def test_verifier_error_aborts_immediately(tmp_path, monkeypatch):
    import empiricist.search.p3_loop as p3_loop_mod

    def fake_verify_scheme_agreed(scheme, **kwargs):
        return AgreedResult(
            "ERROR", None, "engines disagree on 3 pattern(s): [...]", -1.0,
        )

    monkeypatch.setattr(p3_loop_mod, "verify_scheme_agreed", fake_verify_scheme_agreed)

    lg, st = make_env(tmp_path)
    client = FakeLLMClient([make_result(_bsm_dict()), make_result(_bsm_dict())])
    loop = P3SearchLoop(client, lg, st, max_rounds=6, role=_STUB_ROLE)
    task = P3SearchTask(name="t4", goal="g", context="c", target_p_avg=0.5)

    report = run(loop.run(task))

    assert report.ok is False
    assert report.f3_alarm is True
    assert report.rounds == 1
    assert report.artifact_id is None
    assert report.history == [("ERROR", "engines disagree on 3 pattern(s): [...]")]
    # never retried -- only one client call
    assert len(client.calls) == 1
    lg.close()


# -- (e) NO_ARTIFACT rounds exhaust the budget -------------------------------


def test_no_artifact_rounds_exhaust_budget(tmp_path):
    lg, st = make_env(tmp_path)
    client = FakeLLMClient([])  # script exhausted immediately -> None every round
    loop = P3SearchLoop(client, lg, st, max_rounds=2, role=_STUB_ROLE)
    task = P3SearchTask(name="t5", goal="g", context="c")

    report = run(loop.run(task))

    assert report.ok is False
    assert report.rounds == 2
    assert report.artifact_id is None
    assert report.f3_alarm is False
    assert [h[0] for h in report.history] == ["NO_ARTIFACT", "NO_ARTIFACT"]
    lg.close()


# -- INVALID is screen-class, not an alarm -----------------------------------


def test_invalid_claim_treated_as_screen_class_not_alarm(tmp_path):
    lg, st = make_env(tmp_path)
    client = FakeLLMClient([make_result(_bsm_dict()), make_result(_bsm_dict())])
    loop = P3SearchLoop(client, lg, st, max_rounds=2, role=_STUB_ROLE)
    # A non-finite leakage budget makes every round's claim INVALID
    # (domain/p3/verify.py's own pre-check), never an ERROR/alarm.
    task = P3SearchTask(
        name="t6", goal="g", context="c", target_p_avg=0.5,
        max_leakage=float("nan"),
    )

    report = run(loop.run(task))

    assert report.ok is False
    assert report.f3_alarm is False
    assert [h[0] for h in report.history] == ["INVALID", "INVALID"]
    assert report.artifact_id is None
    lg.close()


# -- role resolution: lazy, and documents the Task 4 dependency -------------


def test_default_role_none_resolves_lazily_and_fails_loudly_until_task4(tmp_path):
    """ROLES["p3_searcher"] does not exist until M20a Task 4 adds it. Until
    then, running without an injected `role=` fails loudly (KeyError) at the
    point of use inside `run()`, rather than at import/construction time and
    rather than silently substituting some other role."""
    lg, st = make_env(tmp_path)
    client = FakeLLMClient([])
    loop = P3SearchLoop(client, lg, st, max_rounds=1)  # no role= injected

    with pytest.raises(KeyError):
        run(loop.run(P3SearchTask(name="t7", goal="g", context="c")))
    lg.close()


def test_default_max_rounds_is_twelve(tmp_path):
    lg, st = make_env(tmp_path)
    loop = P3SearchLoop(FakeLLMClient([]), lg, st, role=_STUB_ROLE)
    assert loop._max_rounds == 12
    lg.close()


def test_max_rounds_must_be_positive(tmp_path):
    lg, st = make_env(tmp_path)
    with pytest.raises(ValueError):
        P3SearchLoop(FakeLLMClient([]), lg, st, max_rounds=0, role=_STUB_ROLE)
    lg.close()


# -- build_prompt -------------------------------------------------------


def test_build_prompt_round_one_has_no_prior_attempt(tmp_path):
    lg, st = make_env(tmp_path)
    loop = P3SearchLoop(FakeLLMClient([]), lg, st, role=_STUB_ROLE)
    prompt = loop.build_prompt(
        P3SearchTask(name="t", goal="find X", context="ctx Y"), [], None,
    )
    assert "find X" in prompt
    assert "ctx Y" in prompt
    assert "previous round" not in prompt
    lg.close()

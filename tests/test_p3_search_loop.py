"""Tests for `search/p3_loop.py`'s `P3SearchLoop` (M20a Task 3): propose ->
screen -> verify -> ingest/feedback. Fully offline -- a `FakeLLMClient`
(scripted `BellSchemeOut`-shaped results) exercises the LOOP LOGIC without a
real model call; most tests inject a stub `Role`-shaped object instead of
`ROLES["p3_searcher"]` (mirrors `test_formalize_loop.py`'s `FakeVerifier`
stand-in pattern). A dedicated test below exercises the real lazy resolution
of `ROLES["p3_searcher"]` (M20a Task 4, `llm/roles.py`).
"""

from __future__ import annotations

import asyncio
import math
import sqlite3

import pytest

from empiricist.domain.p3.verify import AgreedResult
from empiricist.executor.runner import DuplicateRunError
from empiricist.ledger.db import Ledger, PromotionIntegrityError
from empiricist.ledger.models import Certification, Run, Verdict
from empiricist.llm.client import FakeLLMClient
from empiricist.llm.models import Effort, LLMResult
from empiricist.llm.roles import ROLES, Role
from empiricist.search.p3_loop import P3SearchLoop, P3SearchReport, P3SearchTask
from empiricist.store import Store
from empiricist.verifiers.p3_goldens import certify_p3
from empiricist.verifiers.p3_scheme import P3SchemeVerifier

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
    certify_p3(lg, P3SchemeVerifier())
    return lg, st


@pytest.mark.parametrize("suite", [None, "stale-suite"])
def test_missing_or_stale_certification_fails_before_model_call(tmp_path, suite):
    lg = Ledger(tmp_path / "ledger.db")
    st = Store(tmp_path / "store")
    verifier = P3SchemeVerifier()
    if suite is not None:
        lg.add_certification(Certification(
            verifier=verifier.name,
            verifier_version=verifier.version,
            binary_hash=verifier.binary_hash,
            golden_suite_hash=suite,
            verdict=Verdict.PASS,
        ))
    client = FakeLLMClient([make_result(_bsm_dict())])
    loop = P3SearchLoop(client, lg, st, max_rounds=1, role=_STUB_ROLE)

    with pytest.raises(PromotionIntegrityError):
        run(loop.run(P3SearchTask(name="uncertified", goal="g", context="c")))

    assert client.calls == []
    lg.close()


# -- (a) good scheme, round 1 -----------------------------------------------


def test_good_scheme_round_one_ingests_claim_bound_heuristic(tmp_path):
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
    assert art.status.value == "HEURISTIC"
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
    assert evs[0].claim_id == lg.claims_for(art.id)[0].id
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
    import empiricist.domain.p3.ingest as p3_ingest_mod

    def fake_verify_scheme_agreed(scheme, **kwargs):
        return AgreedResult(
            "ERROR", None, "engines disagree on 3 pattern(s): [...]", -1.0,
        )

    monkeypatch.setattr(
        p3_ingest_mod, "verify_scheme_agreed", fake_verify_scheme_agreed
    )

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


# -- role resolution: ROLES["p3_searcher"] now exists (M20a Task 4) ---------


def test_p3_searcher_role_exists_active_k1_high_effort():
    """M20a Task 4 added `ROLES["p3_searcher"]` to `llm/roles.py`: active,
    k == 1 (one scheme per round, no wave fan-out), effort HIGH."""
    role = ROLES["p3_searcher"]
    assert role.active is True
    assert role.k == 1
    assert role.effort is Effort.HIGH


def test_default_role_none_resolves_lazily_to_p3_searcher(tmp_path):
    """Now that `ROLES["p3_searcher"]` exists, running without an injected
    `role=` no longer raises KeyError: `run()` resolves it lazily and reaches
    the first `client.complete` call with it. `FakeLLMClient.calls` records
    the role each call actually received, so this pins that the LOOP -- not a
    test stub -- is the one resolving the real registered role."""
    lg, st = make_env(tmp_path)
    client = FakeLLMClient([])  # empty script: NO_ARTIFACT every round, no real scheme needed
    loop = P3SearchLoop(client, lg, st, max_rounds=1)  # no role= injected

    report = run(loop.run(P3SearchTask(name="t7", goal="g", context="c")))

    assert report.ok is False
    assert [h[0] for h in report.history] == ["NO_ARTIFACT"]
    assert len(client.calls) == 1
    assert client.calls[0][0] == "p3_searcher"
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


# -- M21a: throttle backoff + per-round persistence ------------------------------


from empiricist.llm.throttle import ThrottlePolicy  # noqa: E402


class ThrottlingFakeClient(FakeLLMClient):
    """First `n_throttled` calls: open+close a runs row with the rate-limit
    signature (exit 1, 0 output tokens, sub-second wall) and return None. Later
    calls write a healthy receipt and hand out the scripted results."""

    def __init__(self, scripted, *, n_throttled):
        super().__init__(scripted)
        self.n_throttled = n_throttled
        self.run_ids: list[str] = []

    async def complete(self, role, prompt, *, session_id=None, system_prompt=None,
                       schema=None, run_id=None, ledger=None):
        self.run_ids.append(run_id)
        ledger.start_run(Run(run_id=run_id, move="SAMPLE", role=role.name))
        if self.n_throttled > 0:
            self.n_throttled -= 1
            ledger.finish_run(run_id, exit_code=1, wall_s=0.3, tokens_out=0)
            return None
        ledger.finish_run(run_id, exit_code=0, wall_s=5.0, tokens_out=100)
        return await super().complete(role, prompt, schema=schema, run_id=run_id, ledger=ledger)


def _certified_env(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    st = Store(tmp_path / "store")
    certify_p3(lg, P3SchemeVerifier())
    return lg, st


def test_throttled_call_backs_off_then_retries_same_round(tmp_path):
    lg, st = _certified_env(tmp_path)
    slept: list[float] = []

    async def fake_sleep(s):
        slept.append(s)

    client = ThrottlingFakeClient([make_result(_bsm_dict(claimed_p_avg=0.5))], n_throttled=2)
    loop = P3SearchLoop(
        client, lg, st, max_rounds=3, role=_STUB_ROLE,
        throttle=ThrottlePolicy(base_s=1.0, max_s=4.0, max_attempts=4), sleep=fake_sleep,
    )
    rep = run(loop.run(P3SearchTask(name="t", goal="g", context="c", target_p_avg=0.5)))
    assert rep.ok and rep.rounds == 1 and not rep.throttled
    assert slept == [1.0, 2.0]
    assert [r.split("-")[-1] for r in client.run_ids] == ["r1", "r1a2", "r1a3"]
    assert [e["outcome"] for e in rep.rounds_log] == ["THROTTLED", "THROTTLED", "PASS"]
    assert [e["attempt"] for e in rep.rounds_log] == [1, 2, 3]
    assert [h[0] for h in rep.history] == ["PASS"]  # throttled attempts never churn rounds
    lg.close()


def test_throttle_exhaustion_aborts_task_without_alarm(tmp_path):
    lg, st = _certified_env(tmp_path)

    async def fake_sleep(s):
        pass

    client = ThrottlingFakeClient([], n_throttled=99)
    loop = P3SearchLoop(
        client, lg, st, max_rounds=5, role=_STUB_ROLE,
        throttle=ThrottlePolicy(base_s=1.0, max_s=1.0, max_attempts=3), sleep=fake_sleep,
    )
    rep = run(loop.run(P3SearchTask(name="t", goal="g", context="c", target_p_avg=0.5)))
    assert not rep.ok and rep.throttled and not rep.f3_alarm
    assert rep.rounds == 1 and len(client.run_ids) == 3
    assert rep.history[-1][0] == "THROTTLED"
    assert [e["outcome"] for e in rep.rounds_log] == ["THROTTLED"] * 3
    lg.close()


def test_round_sink_receives_every_round_including_failed_schemes(tmp_path):
    lg, st = _certified_env(tmp_path)
    seen: list[dict] = []
    # Round 1: an empty mesh (every Bell state ambiguous, p_avg = 0) misses the
    # task's 0.5 target -> FAIL; round 2: the standard BSM hits it -> PASS.
    client = FakeLLMClient([
        make_result(_bsm_dict(mesh=[])),
        make_result(_bsm_dict()),
    ])
    loop = P3SearchLoop(client, lg, st, max_rounds=2, role=_STUB_ROLE, round_sink=seen.append)
    rep = run(loop.run(P3SearchTask(name="t", goal="g", context="c", target_p_avg=0.5)))
    assert rep.ok
    assert [e["outcome"] for e in seen] == ["FAIL", "PASS"]
    assert seen[0]["scheme"]["mesh"] == []  # the FAILED scheme itself survives
    assert seen[0]["summary"]["p_avg"] == pytest.approx(0.0)
    assert seen[1]["scheme"]["mesh"] == _bsm_dict()["mesh"]
    assert seen[1]["summary"]["p_avg"] == pytest.approx(0.5)
    assert seen[0]["run_id"].endswith("-r1") and seen[1]["run_id"].endswith("-r2")
    assert rep.rounds_log == seen


def test_no_throttle_policy_keeps_legacy_no_artifact_behaviour(tmp_path):
    lg, st = _certified_env(tmp_path)
    client = ThrottlingFakeClient([], n_throttled=99)
    loop = P3SearchLoop(client, lg, st, max_rounds=2, role=_STUB_ROLE, throttle=None)
    rep = run(loop.run(P3SearchTask(name="t", goal="g", context="c", target_p_avg=0.5)))
    assert [h[0] for h in rep.history] == ["NO_ARTIFACT", "NO_ARTIFACT"] and not rep.throttled
    assert [e["outcome"] for e in rep.rounds_log] == ["NO_ARTIFACT", "NO_ARTIFACT"]
    lg.close()


def test_offline_fake_without_receipts_is_never_throttled(tmp_path):
    lg, st = _certified_env(tmp_path)
    client = FakeLLMClient([])  # writes no runs rows -> NO_ARTIFACT, not THROTTLED
    loop = P3SearchLoop(client, lg, st, max_rounds=1, role=_STUB_ROLE)
    rep = run(loop.run(P3SearchTask(name="t", goal="g", context="c", target_p_avg=0.5)))
    assert [h[0] for h in rep.history] == ["NO_ARTIFACT"] and not rep.throttled
    lg.close()

"""Tests for `formalize/loop.py`'s `FormalizeLoop` (M18): propose -> gate ->
revise, the model never gets a shell. Fully offline -- a `FakeLLMClient`
(scripted `LeanModuleOut` results) AND a fake verifier stub (`.verify()`
returning scripted `VerifierResult`s) exercise the LOOP LOGIC without the real
Lean toolchain or a real model call.
"""

from __future__ import annotations

import asyncio
import sqlite3

import pytest
from blake3 import blake3

from empiricist.executor.runner import DuplicateRunError
from empiricist.formalize.loop import FormalizeLoop, FormalizeReport, FormalizeTask
from empiricist.ledger.db import Ledger, PromotionIntegrityError
from empiricist.ledger.models import Certification, Run, Status, Verdict
from empiricist.llm.client import FakeLLMClient
from empiricist.llm.models import LLMResult
from empiricist.llm.throttle import ThrottlePolicy
from empiricist.store import Store
from empiricist.verifiers.base import VerifierResult
from empiricist.verifiers.lean_goldens import lean_suite_hash

_MODULE_V1 = (
    "import Mathlib\n"
    "namespace Empiricist\n"
    "theorem foo : 1 = 2 := by sorry\n"
    "end Empiricist\n"
)
_MODULE_V2 = (
    "import Mathlib\n"
    "namespace Empiricist\n"
    "theorem foo : (1 : Nat) = 1 := rfl\n"
    "end Empiricist\n"
)


class FakeVerifier:
    """Duck-typed stand-in for LeanVerifier: `.verify(module_source, *, decl,
    timeout_s=...)` returning scripted VerifierResults in order, plus the
    identity fields `ingest_lean_artifact` needs off a real verifier."""

    name = "fake_lean"
    version = "0.1"
    binary_hash = "fakehash0123456789"

    def __init__(self, scripted: list[VerifierResult]) -> None:
        self._scripted = list(scripted)
        self.calls: list[tuple[str, str]] = []  # (module_source, decl)

    def verify(self, module_source: str, *, decl: str, timeout_s: float = 600.0) -> VerifierResult:
        self.calls.append((module_source, decl))
        return self._scripted[len(self.calls) - 1]


class RunRecordingFakeClient(FakeLLMClient):
    """Fake transport that enforces the real runs.run_id uniqueness boundary."""

    async def complete(
        self,
        role,
        prompt,
        *,
        session_id=None,
        system_prompt=None,
        schema=None,
        run_id=None,
        ledger=None,
    ):
        if ledger is not None and run_id is not None:
            try:
                ledger.start_run(
                    Run(
                        run_id=run_id,
                        move="SAMPLE",
                        role=role.name,
                        model=role.model,
                    )
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateRunError(run_id) from exc
        result = await super().complete(
            role,
            prompt,
            session_id=session_id,
            system_prompt=system_prompt,
            schema=schema,
            run_id=run_id,
            ledger=ledger,
        )
        if ledger is not None and run_id is not None:
            ledger.finish_run(run_id, exit_code=0, wall_s=0.0)
        return result


def make_result(parsed: dict | None) -> LLMResult:
    return LLMResult(
        text="", parsed=parsed, stop_reason="tool_use" if parsed else "end_turn",
        is_error=False, input_tokens=1, output_tokens=1, cache_read_tokens=0,
        cache_creation_tokens=0, cost_usd=0.0, duration_ms=1,
        session_id="s", uuid="u", model="claude-fable-5",
    )


def out_dict(module_source: str, decl: str = "Empiricist.foo", notes: str = "") -> dict:
    return {"module_source": module_source, "decl": decl, "notes": notes}


def run(coro):
    return asyncio.run(coro)


def make_env(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    lg.add_certification(Certification(
        verifier=FakeVerifier.name,
        verifier_version=FakeVerifier.version,
        binary_hash=FakeVerifier.binary_hash,
        golden_suite_hash=lean_suite_hash(),
        verdict=Verdict.PASS,
    ))
    st = Store(tmp_path / "store")
    return lg, st


@pytest.mark.parametrize("suite", [None, "stale-suite"])
def test_missing_or_stale_certification_fails_before_model_call(tmp_path, suite):
    lg = Ledger(tmp_path / "ledger.db")
    st = Store(tmp_path / "store")
    verifier = FakeVerifier([])
    if suite is not None:
        lg.add_certification(Certification(
            verifier=verifier.name,
            verifier_version=verifier.version,
            binary_hash=verifier.binary_hash,
            golden_suite_hash=suite,
            verdict=Verdict.PASS,
        ))
    client = FakeLLMClient([make_result(out_dict(_MODULE_V2))])
    loop = FormalizeLoop(client, lg, st, verifier, max_rounds=1)

    with pytest.raises(PromotionIntegrityError):
        run(loop.run(FormalizeTask(name="uncertified", goal="g", context="c")))

    assert client.calls == []
    assert verifier.calls == []
    lg.close()


def pass_result(statement="1 = 1", axioms=()):
    return VerifierResult(
        verdict=Verdict.PASS,
        details={
            "decl": "Empiricist.foo", "axioms": list(axioms),
            "statement": statement,
            "statement_hash": blake3(statement.encode("utf-8")).hexdigest(),
        },
    )


def fail_result(gate="diagnostics", **extra):
    details = {"gate": gate}
    details.update(extra)
    return VerifierResult(verdict=Verdict.FAIL, details=details)


# -- (a) PASS on round 1 --------------------------------------------------


def test_rerun_same_task_mints_fresh_run_ids_and_links_evidence(tmp_path):
    """A stopped/exhausted invocation can resume under the same task name.

    Each ``run()`` invocation must own a fresh provenance namespace while the
    successful round's evidence still links to that exact provider receipt.
    """
    lg, st = make_env(tmp_path)
    client = RunRecordingFakeClient([
        make_result(None),
        make_result(out_dict(_MODULE_V2)),
    ])
    verifier = FakeVerifier([pass_result()])
    loop = FormalizeLoop(client, lg, st, verifier, max_rounds=1)
    task = FormalizeTask(name="restartable", goal="prove 1=1", context="none")

    first = run(loop.run(task))
    second = run(loop.run(task))  # must not raise DuplicateRunError

    assert first.ok is False
    assert second.ok is True
    run_ids = [
        row["run_id"]
        for row in lg.conn.execute("SELECT run_id FROM runs ORDER BY rowid")
    ]
    assert len(run_ids) == 2
    assert run_ids[0] != run_ids[1]
    assert all(
        run_id.startswith("formalize-restartable-") and run_id.endswith("-r1")
        for run_id in run_ids
    )
    assert lg.get_artifact(second.artifact_id).run_id == run_ids[1]
    assert lg.evidence_for(second.artifact_id)[0].run_id == run_ids[1]
    lg.close()


def test_pass_round_one_ingests_formalized_artifact(tmp_path):
    lg, st = make_env(tmp_path)
    client = FakeLLMClient([make_result(out_dict(_MODULE_V2))])
    verifier = FakeVerifier([pass_result(statement="1 = 1", axioms=["propext"])])
    loop = FormalizeLoop(client, lg, st, verifier, max_rounds=6)

    report = run(loop.run(FormalizeTask(name="t1", goal="prove 1=1", context="none")))

    assert isinstance(report, FormalizeReport)
    assert report.ok is True
    assert report.rounds == 1
    assert report.final_verdict == "PASS"
    assert report.final_gate is None
    assert report.recorded_statement == "1 = 1"
    assert report.recorded_axioms == ("propext",)
    assert report.decl == "Empiricist.foo"
    assert report.module_source == _MODULE_V2
    assert report.artifact_id is not None
    assert len(report.history) == 1
    assert report.history[0][0] == "PASS"

    # -- the FORMALIZED artifact + its evidence row really exist --
    art = lg.get_artifact(report.artifact_id)
    assert art.kind == "lean"
    assert art.status == Status.FORMALIZED
    assert art.title == "Empiricist.foo"
    assert st.get(art.content_path) == _MODULE_V2.encode("utf-8")

    evidence = lg.evidence_for(report.artifact_id)
    assert len(evidence) == 1
    assert evidence[0].verdict == Verdict.PASS
    assert evidence[0].verifier == "fake_lean"
    assert evidence[0].claim_id is not None
    assert evidence[0].golden_suite_hash == lean_suite_hash()
    claims = lg.claims_for(report.artifact_id)
    assert len(claims) == 1
    assert claims[0].statement == "1 = 1"
    assert claims[0].problem_version == "p5-ghz3-v1"

    # the verifier was called with the exact (module_source, decl) pair
    assert verifier.calls == [(_MODULE_V2, "Empiricist.foo")]
    lg.close()


# -- (b) FAIL(diagnostics) round 1, PASS round 2 --------------------------


def test_fail_then_pass_feeds_back_round_one_feedback_into_round_two_prompt(tmp_path):
    lg, st = make_env(tmp_path)
    client = FakeLLMClient([
        make_result(out_dict(_MODULE_V1)),
        make_result(out_dict(_MODULE_V2)),
    ])
    verifier = FakeVerifier([
        fail_result(gate="diagnostics", errors=["type mismatch: expected Nat, got ..."]),
        pass_result(),
    ])
    loop = FormalizeLoop(client, lg, st, verifier, max_rounds=6)

    report = run(loop.run(FormalizeTask(name="t2", goal="prove foo", context="ctx")))

    assert report.ok is True
    assert report.rounds == 2
    assert len(report.history) == 2
    assert report.history[0][0] == "FAIL"
    assert report.history[0][1] == "diagnostics"
    assert "type mismatch" in report.history[0][2]
    assert report.history[1][0] == "PASS"

    # round-2 prompt actually carried round-1's feedback + prior module
    assert len(client.calls) == 2
    round1_prompt = client.calls[0][1]
    round2_prompt = client.calls[1][1]
    assert "prove foo" in round1_prompt
    assert "type mismatch" not in round1_prompt
    assert _MODULE_V1 in round2_prompt
    assert "type mismatch: expected Nat, got ..." in round2_prompt
    assert "Compilation failed" in round2_prompt
    lg.close()


# -- (c) all rounds FAIL ---------------------------------------------------


def test_all_rounds_fail_exhausts_budget_without_ingesting(tmp_path):
    lg, st = make_env(tmp_path)
    max_rounds = 3
    client = FakeLLMClient([make_result(out_dict(_MODULE_V1)) for _ in range(max_rounds)])
    verifier = FakeVerifier([fail_result(gate="sorry") for _ in range(max_rounds)])
    loop = FormalizeLoop(client, lg, st, verifier, max_rounds=max_rounds)

    report = run(loop.run(FormalizeTask(name="t3", goal="g", context="c")))

    assert report.ok is False
    assert report.rounds == max_rounds
    assert report.artifact_id is None
    assert report.final_verdict == "FAIL"
    assert report.final_gate == "sorry"
    assert len(report.history) == max_rounds
    assert all(v == "FAIL" and g == "sorry" for v, g, _ in report.history)

    # -- (f) FAIL never ingests --
    assert lg.conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 0
    lg.close()


# -- (d) no-artifact round handled -----------------------------------------


def test_no_artifact_round_handled_then_pass(tmp_path):
    lg, st = make_env(tmp_path)
    client = FakeLLMClient([
        make_result(None),               # explicit refusal: has_artifact False
        make_result(out_dict(_MODULE_V2)),
    ])
    verifier = FakeVerifier([pass_result()])
    loop = FormalizeLoop(client, lg, st, verifier, max_rounds=6)

    report = run(loop.run(FormalizeTask(name="t4", goal="g", context="c")))

    assert report.ok is True
    assert report.rounds == 2
    assert report.history[0][0] == "NO_ARTIFACT"
    assert report.history[0][1] is None
    assert "LeanModuleOut schema" in report.history[0][2]
    # the verifier is never even called for the no-artifact round
    assert len(verifier.calls) == 1
    lg.close()


def test_no_artifact_via_script_exhaustion_is_handled(tmp_path):
    """FakeLLMClient returns None once its script is exhausted (mirrors
    SearchLoop's no_artifact accounting) -- same code path as an explicit
    refusal."""
    lg, st = make_env(tmp_path)
    client = FakeLLMClient([])  # script exhausted immediately
    verifier = FakeVerifier([])
    loop = FormalizeLoop(client, lg, st, verifier, max_rounds=2)

    report = run(loop.run(FormalizeTask(name="t5", goal="g", context="c")))

    assert report.ok is False
    assert report.rounds == 2
    assert all(v == "NO_ARTIFACT" for v, _, _ in report.history)
    assert verifier.calls == []
    lg.close()


# -- (e) ERROR verdict handled without crashing -----------------------------


def test_error_verdict_fed_back_not_crashed_then_pass(tmp_path):
    lg, st = make_env(tmp_path)
    client = FakeLLMClient([
        make_result(out_dict(_MODULE_V1)),
        make_result(out_dict(_MODULE_V2)),
    ])
    verifier = FakeVerifier([
        VerifierResult(
            verdict=Verdict.ERROR,
            details={"error": "lean --json compile subprocess timed out"},
        ),
        pass_result(),
    ])
    loop = FormalizeLoop(client, lg, st, verifier, max_rounds=6)

    report = run(loop.run(FormalizeTask(name="t6", goal="g", context="c")))

    assert report.ok is True
    assert report.rounds == 2
    assert report.history[0][0] == "ERROR"
    assert report.history[0][1] is None
    assert "Verification errored" in report.history[0][2]
    assert "timed out" in report.history[0][2]
    lg.close()


# -- invalid JSON (schema-mismatched structured_output) ---------------------


def test_invalid_json_round_handled_then_pass(tmp_path):
    lg, st = make_env(tmp_path)
    bad = {"module_source": _MODULE_V1, "decl": "Empiricist.foo", "extra_bogus_field": True}
    client = FakeLLMClient([make_result(bad), make_result(out_dict(_MODULE_V2))])
    verifier = FakeVerifier([pass_result()])
    loop = FormalizeLoop(client, lg, st, verifier, max_rounds=6)

    report = run(loop.run(FormalizeTask(name="t7", goal="g", context="c")))

    assert report.ok is True
    assert report.rounds == 2
    assert report.history[0][0] == "INVALID_JSON"
    assert "LeanModuleOut schema" in report.history[0][2]
    # the invalid round never reached verify() at all
    assert verifier.calls == [(_MODULE_V2, "Empiricist.foo")]
    lg.close()


# -- (g) goal-state feedback (M18 hole-driven development) ----------------


_MODULE_HOLE = (
    "import Mathlib\n"
    "namespace Empiricist\n"
    "theorem foo (n : Nat) : n + 0 = n ∧ n = n := by\n"
    "  refine ⟨?_, ?_⟩\n"
    "end Empiricist\n"
)
_MODULE_FILLED = (
    "import Mathlib\n"
    "namespace Empiricist\n"
    "theorem foo (n : Nat) : n + 0 = n ∧ n = n := by\n"
    "  exact ⟨by simp, rfl⟩\n"
    "end Empiricist\n"
)
_GOAL_STATE_ERROR = (
    "unsolved goals\ncase refine_1\nn : Nat\n⊢ n + 0 = n\n\n"
    "case refine_2\nn : Nat\n⊢ n = n"
)


def test_hole_proof_then_filled_proof_carries_full_goal_state_into_round_two(tmp_path):
    """A `?_`-hole module FAILs at gate=diagnostics with the real Lean goal
    state in `details["errors"]`; round 2's prompt must carry that goal state
    forward VERBATIM (not truncated, not summarized) so the model can fill the
    holes -- the whole point of M18 goal-state feedback."""
    lg, st = make_env(tmp_path)
    client = FakeLLMClient([
        make_result(out_dict(_MODULE_HOLE)),
        make_result(out_dict(_MODULE_FILLED)),
    ])
    verifier = FakeVerifier([
        fail_result(gate="diagnostics", errors=[_GOAL_STATE_ERROR]),
        pass_result(),
    ])
    loop = FormalizeLoop(client, lg, st, verifier, max_rounds=6)

    report = run(loop.run(FormalizeTask(name="t8", goal="prove foo", context="ctx")))

    assert report.ok is True
    assert report.rounds == 2
    assert report.history[0][0] == "FAIL"
    assert report.history[0][1] == "diagnostics"
    # the round-1 feedback itself carries the goal state, in full
    assert _GOAL_STATE_ERROR in report.history[0][2]
    assert "⊢" in report.history[0][2]
    assert "REMAINING GOAL" in report.history[0][2]

    # round-2 PROMPT (what the model actually sees) carries the prior module
    # AND the untruncated goal state forward
    assert len(client.calls) == 2
    round2_prompt = client.calls[1][1]
    assert _MODULE_HOLE in round2_prompt
    assert _GOAL_STATE_ERROR in round2_prompt
    assert "case refine_1" in round2_prompt
    assert "case refine_2" in round2_prompt

    # round 2 PASSes and ingests
    assert report.history[1][0] == "PASS"
    assert report.artifact_id is not None
    art = lg.get_artifact(report.artifact_id)
    assert art.status == Status.FORMALIZED
    lg.close()


def test_default_max_rounds_is_twelve(tmp_path):
    lg, st = make_env(tmp_path)
    loop = FormalizeLoop(FakeLLMClient([]), lg, st, FakeVerifier([]))
    assert loop._max_rounds == 12
    lg.close()


# -- build_prompt -------------------------------------------------------


def test_build_prompt_round_one_has_no_prior_attempt(tmp_path):
    lg, st = make_env(tmp_path)
    loop = FormalizeLoop(FakeLLMClient([]), lg, st, FakeVerifier([]))
    prompt = loop.build_prompt(FormalizeTask(name="t", goal="prove X", context="ctx Y"), [])
    assert "prove X" in prompt
    assert "ctx Y" in prompt
    assert "FAITHFULLY" in prompt
    assert "previous attempt" not in prompt
    lg.close()


def test_build_prompt_round_one_carries_hole_development_guidance(tmp_path):
    lg, st = make_env(tmp_path)
    loop = FormalizeLoop(FakeLLMClient([]), lg, st, FakeVerifier([]))
    prompt = loop.build_prompt(FormalizeTask(name="t", goal="prove X", context="ctx Y"), [])
    assert "?_" in prompt
    assert "hole" in prompt.lower()
    assert "goal state" in prompt.lower()
    lg.close()


def test_formalizer_role_prompt_carries_hole_development_guidance():
    from empiricist.llm.roles import ROLES

    prompt = ROLES["formalizer"].system_prompt
    assert "?_" in prompt
    assert "hole" in prompt.lower()
    assert "goal state" in prompt.lower()
    assert "sorry" in prompt.lower()
    assert "native_decide" in prompt.lower()


def test_max_rounds_must_be_positive(tmp_path):
    lg, st = make_env(tmp_path)
    try:
        FormalizeLoop(FakeLLMClient([]), lg, st, FakeVerifier([]), max_rounds=0)
        raised = False
    except ValueError:
        raised = True
    assert raised
    lg.close()


# -- M21a: throttle backoff --------------------------------------------------------


class ThrottlingFakeClient(FakeLLMClient):
    """First `n_throttled` calls write the rate-limit receipt and return None."""

    def __init__(self, scripted, *, n_throttled):
        super().__init__(scripted)
        self.n_throttled = n_throttled
        self.run_ids: list[str] = []

    async def complete(self, role, prompt, *, session_id=None, system_prompt=None,
                       schema=None, run_id=None, ledger=None):
        self.run_ids.append(run_id)
        ledger.start_run(Run(run_id=run_id, move="SAMPLE", role=role.name, model=role.model))
        if self.n_throttled > 0:
            self.n_throttled -= 1
            ledger.finish_run(run_id, exit_code=1, wall_s=0.2, tokens_out=0)
            return None
        ledger.finish_run(run_id, exit_code=0, wall_s=9.0, tokens_out=500)
        return await super().complete(role, prompt, schema=schema, run_id=run_id, ledger=ledger)


def test_formalize_throttled_attempts_back_off_then_pass(tmp_path):
    lg, st = make_env(tmp_path)
    slept: list[float] = []

    async def fake_sleep(s):
        slept.append(s)

    client = ThrottlingFakeClient([make_result(out_dict(_MODULE_V2))], n_throttled=2)
    verifier = FakeVerifier([pass_result()])
    loop = FormalizeLoop(
        client, lg, st, verifier, max_rounds=2,
        throttle=ThrottlePolicy(base_s=1.0, max_s=8.0, max_attempts=4), sleep=fake_sleep,
    )
    report = run(loop.run(FormalizeTask(name="th", goal="g", context="c")))
    assert report.ok and report.rounds == 1 and not report.throttled
    assert report.throttled_attempts == 2
    assert slept == [1.0, 2.0]
    assert [r.split("-")[-1] for r in client.run_ids] == ["r1", "r1a2", "r1a3"]
    assert [h[0] for h in report.history] == ["PASS"]
    lg.close()


def test_formalize_throttle_exhaustion_aborts(tmp_path):
    lg, st = make_env(tmp_path)

    async def fake_sleep(s):
        pass

    client = ThrottlingFakeClient([], n_throttled=99)
    verifier = FakeVerifier([])
    loop = FormalizeLoop(
        client, lg, st, verifier, max_rounds=4,
        throttle=ThrottlePolicy(base_s=1.0, max_s=1.0, max_attempts=2), sleep=fake_sleep,
    )
    report = run(loop.run(FormalizeTask(name="th", goal="g", context="c")))
    assert not report.ok and report.throttled
    assert report.final_verdict == "THROTTLED" and report.rounds == 1
    assert len(client.run_ids) == 2 and verifier.calls == []
    assert report.throttled_attempts == 2
    lg.close()


def test_formalize_default_throttle_policy_is_on(tmp_path):
    lg, st = make_env(tmp_path)
    slept: list[float] = []

    async def fake_sleep(s):
        slept.append(s)

    client = ThrottlingFakeClient([make_result(out_dict(_MODULE_V2))], n_throttled=1)
    loop = FormalizeLoop(client, lg, st, FakeVerifier([pass_result()]), max_rounds=2,
                         sleep=fake_sleep)
    report = run(loop.run(FormalizeTask(name="th", goal="g", context="c")))
    assert report.ok and slept == [60.0] and report.throttled_attempts == 1
    lg.close()

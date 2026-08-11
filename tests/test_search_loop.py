"""Tests for the SEARCH loop (M6 T3): k nonce-diverse Searcher prompts ->
`complete_many` -> parse/screen (never trusted) -> `verify_agreed` (the
certified A/B pair) -> population insert + evidence, with the F3 alarm on
engine disagreement and exact-upgrade detection (spec §9).

Fully scripted via FakeLLMClient -- deterministic, no real model call.
"""

from __future__ import annotations

import asyncio

import pytest

from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.construction import Construction, FusionOp
from empiricist.domain.p5.graphstate import GraphState
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Status, Verdict
from empiricist.llm.client import FakeLLMClient
from empiricist.llm.models import LLMResult
from empiricist.llm.roles import ROLES
from empiricist.search.database import Population
from empiricist.search.loop import F3Alarm, SearchLoop, TargetSpec
from empiricist.store import Store
from empiricist.verifiers.base import VerifierResult
from empiricist.verifiers.enum_fusion import EnumFusionVerifier
from empiricist.verifiers.registry import Registry
from empiricist.verifiers.stab_fusion import StabFusionVerifier

# The P4 construction (matches tests/test_verifiers.py's fixture): resources=2
# GHZ3 stars (qubits 0,1,2 and 3,4,5), fuse leaf 2 with leaf 4 -> a 4-path on
# the surviving qubits {0,1,3,5}.
P4_DICT = {
    "resources": 2,
    "steps": [{"op": "fuse", "args": [2, 4]}],
    "target_n": 4,
    "target_edges": [[0, 1], [1, 2], [2, 3]],
}
P4_CONSTRUCTION = Construction(
    resources=2, steps=(FusionOp(a=2, b=4),),
    target=GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)]),
)
P4_KEY = lc_orbit_key(P4_CONSTRUCTION.target)

# Same shape/size as P4, but the claimed target is a star instead of a path --
# a schema- and screen-valid Construction whose steps genuinely do not reach
# its claimed target (verify_agreed FAILs honestly, no engine disagreement).
WRONG_TARGET_DICT = {
    "resources": 2,
    "steps": [{"op": "fuse", "args": [2, 4]}],
    "target_n": 4,
    "target_edges": [[0, 1], [0, 2], [0, 3]],
}

# Schema-invalid: ConstructionOut forbids extra fields.
SCHEMA_INVALID_DICT = {
    "resources": 1,
    "steps": [],
    "target_n": 3,
    "target_edges": [[0, 1], [0, 2]],
    "bogus_extra_field": True,
}

# Screen-invalid but schema-valid: a self-fusion (a == b) -- ScreenReject,
# not a pydantic ValidationError.
SELF_FUSE_DICT = {
    "resources": 2,
    "steps": [{"op": "fuse", "args": [2, 2]}],
    "target_n": 4,
    "target_edges": [[0, 1]],
}

# Screen-valid (the screen only checks per-step shape + the global size
# identity, not liveness of referenced qubits across steps) but references an
# already-fused qubit in its second step -- both engines raise internally, so
# verify_agreed reports a genuine (non-disagreement) ERROR.
DOUBLE_FUSE_DICT = {
    "resources": 2,
    "steps": [{"op": "fuse", "args": [2, 4]}, {"op": "fuse", "args": [2, 5]}],
    "target_n": 2,
    "target_edges": [[0, 1]],
}


def make_result(parsed: dict | None, *, is_error: bool = False) -> LLMResult:
    return LLMResult(
        text="", parsed=parsed, stop_reason="tool_use" if parsed else "end_turn",
        is_error=is_error, input_tokens=1, output_tokens=1, cache_read_tokens=0,
        cache_creation_tokens=0, cost_usd=0.0, duration_ms=1,
        session_id="s", uuid="u", model="claude-fable-5",
    )


def run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def env(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    st = Store(tmp_path / "store")
    reg = Registry(lg)
    reg.certify(StabFusionVerifier())
    reg.certify(EnumFusionVerifier())
    pop = Population(lg)
    yield lg, st, reg, pop
    lg.close()


def make_loop(client, env, *, island=0):
    lg, st, reg, pop = env
    return SearchLoop(client, lg, st, reg, pop, island=island)


def p4_target(target_f=1, known_bound="F >= 4 (Tier-0 unreachable)"):
    return TargetSpec(
        n=4, lc_orbit_key=P4_KEY, representative_edges=((0, 1), (1, 2), (2, 3)),
        known_bound=known_bound, target_f=target_f,
    )


# -- build_prompt ---------------------------------------------------------


def test_build_prompt_contains_target_details_nonce_and_mod3_hint(env):
    loop = make_loop(FakeLLMClient([]), env)
    target = TargetSpec(
        n=4, lc_orbit_key="deadbeef", representative_edges=((0, 1), (1, 2), (2, 3)),
        known_bound="F >= 8 (Tier-0 unreachable)", target_f=4,
    )
    nonce = "nonce-xyz-123"
    prompt = loop.build_prompt(target, nonce)
    assert prompt.count(nonce) >= 1
    assert target.known_bound in prompt
    assert "mod 3" in prompt
    for a, b in target.representative_edges:
        assert f"({a},{b})" in prompt
    assert "3*i" in prompt  # workspace layout hint (resource i = qubits 3i,3i+1,3i+2)
    # lc hint for hard targets (from n=6 some minimal schedules REQUIRE an lc)
    assert '"op": "lc"' in prompt
    assert "local" in prompt and "does not count toward F" in prompt


# -- run_generation: the full wave ------------------------------------------


def test_run_generation_full_wave_counts_population_events_and_upgrade(env):
    lg, st, reg, pop = env
    scripted = [
        make_result(dict(P4_DICT)),               # 1: valid, improving, exact upgrade
        make_result(dict(P4_DICT)),                # 2: same again -> duplicate
        make_result(dict(SCHEMA_INVALID_DICT)),    # 3: schema-invalid -> screened
        make_result(None),                         # 4: refusal -> no_artifact
        make_result(dict(WRONG_TARGET_DICT)),       # 5: valid shape, verify FAIL
    ]
    client = FakeLLMClient(scripted)
    loop = make_loop(client, env)
    target = p4_target()

    report = run(loop.run_generation(1, [target], k=6))  # 6th prompt: script exhausted

    assert report.gen == 1
    assert report.sampled == 6
    assert report.no_artifact == 2       # 1 script-exhausted + 1 explicit refusal
    assert report.screened_out == 1
    assert report.verify_fail == 1
    assert report.verify_error == 0
    assert report.inserted == 1
    assert report.duplicates == 1
    assert report.exact_upgrades == ((P4_KEY, 1),)
    assert len(report.screen_reasons) == 1

    # -- population state --
    row = pop.get(P4_KEY)
    assert row is not None
    assert row.objective_vec == [1]
    assert row.hit_count == 2  # 1 insert + 1 duplicate hit
    assert pop.count() == 1

    # no eviction rows: an insert followed by a tie, never a replacement
    evicted = lg.conn.execute(
        "SELECT * FROM evicted WHERE lc_orbit_key = ?", (P4_KEY,)
    ).fetchall()
    assert evicted == []

    # -- generation event --
    events = pop.events(trigger="generation")
    assert len(events) == 1
    assert events[0].gen == 1
    assert events[0].detail["inserted"] == 1
    assert events[0].detail["duplicates"] == 1
    assert events[0].detail["exact_upgrades"] == [[P4_KEY, 1]]

    # -- CAS artifact + evidence row for the exact upgrade --
    cert_hash = row.cert_hash
    assert cert_hash is not None
    assert st.get(cert_hash)  # content retrievable
    art = lg.get_artifact(cert_hash)
    assert art.kind == "construction"
    assert art.problem_version == "p5-ghz3-v1"
    assert art.status == Status.HEURISTIC

    evidence = lg.evidence_for(cert_hash)
    assert len(evidence) == 1
    ev = evidence[0]
    assert ev.verifier == "verify_agreed"
    assert ev.verdict == Verdict.PASS
    assert ev.details["achieved_key"] == P4_KEY
    assert ev.details["f"] == 1
    assert ev.details["upgrade"] is True
    assert ev.details["target"]["lc_orbit_key"] == P4_KEY
    # both certified engines' identities ride along (name@version:hash12)
    assert ev.details["stab_fusion_id"].startswith("stab_fusion@1.0:")
    assert ev.details["enum_fusion_id"].startswith("enum_fusion@1.0:")
    assert len(ev.details["stab_fusion_id"].rsplit(":", 1)[1]) == 12


def test_duplicate_exact_upgrade_resubmission_does_not_crash(env):
    """A byte-identical re-submission of an already-known witness must not
    re-ingest the CAS artifact (its id IS the content digest -- a second
    add_artifact with the same id raises sqlite3.IntegrityError, spec
    §4.2) -- the loop must gate on population.consider's `improved` flag,
    not attempt-and-catch."""
    lg, st, reg, pop = env
    scripted = [make_result(dict(P4_DICT)), make_result(dict(P4_DICT))]
    client = FakeLLMClient(scripted)
    loop = make_loop(client, env)
    report = run(loop.run_generation(1, [p4_target()], k=2))
    assert report.inserted == 1
    assert report.duplicates == 1
    assert report.exact_upgrades == ((P4_KEY, 1),)  # only the FIRST hit counts
    assert len(lg.evidence_for(pop.get(P4_KEY).cert_hash)) == 1


# -- no_artifact accounting ---------------------------------------------------


def test_no_artifact_counts_both_script_exhaustion_and_has_artifact_false(env):
    scripted = [make_result(None)]  # 1 explicit refusal (has_artifact False)
    client = FakeLLMClient(scripted)
    loop = make_loop(client, env)
    report = run(loop.run_generation(1, [p4_target()], k=3))  # 2 more: script exhausted
    assert report.sampled == 3
    assert report.no_artifact == 3
    assert report.screened_out == 0
    assert report.inserted == 0


# -- screening: schema vs. semantic reject ------------------------------------


def test_screen_reasons_deduped_but_screened_out_counts_each_candidate(env):
    scripted = [make_result(dict(SELF_FUSE_DICT)), make_result(dict(SELF_FUSE_DICT))]
    client = FakeLLMClient(scripted)
    loop = make_loop(client, env)
    report = run(loop.run_generation(1, [p4_target()], k=2))
    assert report.screened_out == 2
    assert len(report.screen_reasons) == 1  # same reason both times -> deduped
    assert "distinct" in report.screen_reasons[0]


# -- verify_error: a real (non-disagreement) engine ERROR --------------------


def test_verify_error_counted_without_crashing_or_raising_f3(env):
    scripted = [make_result(dict(DOUBLE_FUSE_DICT))]
    client = FakeLLMClient(scripted)
    loop = make_loop(client, env)
    report = run(loop.run_generation(1, [p4_target()], k=1))
    assert report.verify_error == 1
    assert report.verify_fail == 0
    assert report.inserted == 0
    assert report.duplicates == 0


# -- F3 alarm: engine disagreement stops the world ----------------------------


def test_f3_alarm_on_verifier_disagreement(env, monkeypatch):
    lg, st, reg, pop = env
    scripted = [make_result(dict(P4_DICT))]
    client = FakeLLMClient(scripted)
    loop = make_loop(client, env)

    import empiricist.search.loop as loop_mod

    def fake_verify_agreed(registry, construction):
        return VerifierResult(
            verdict=Verdict.ERROR,
            details={"disagreement": True, "stab_fusion_key": "a", "enum_fusion_key": "b"},
        )

    monkeypatch.setattr(loop_mod, "verify_agreed", fake_verify_agreed)

    with pytest.raises(F3Alarm) as excinfo:
        run(loop.run_generation(1, [p4_target()], k=1))
    assert excinfo.value.args[0]["disagreement"] is True
    assert pop.count() == 0  # no candidate entered the population before the alarm
    assert pop.events(trigger="generation") == []  # the wave never finished...
    alarms = pop.events(trigger="f3_alarm")  # ...but the alarm itself is durable
    assert len(alarms) == 1
    assert alarms[0].gen == 1
    assert alarms[0].detail["candidate"] == 0
    assert alarms[0].detail["disagreement"] is True
    assert alarms[0].detail["stab_fusion_key"] == "a"
    assert alarms[0].detail["enum_fusion_key"] == "b"
    assert alarms[0].detail["counts_so_far"]["inserted"] == 0


def test_f3_alarm_partial_wave_preserves_earlier_verified_writes(env, monkeypatch):
    """Partial-wave semantics: a wave of [genuine PASS, disagreement] aborts
    on the SECOND candidate -- but the first candidate's writes (population
    row, CAS artifact, upgrade evidence) persist, because that candidate
    individually earned a real two-engine agreement; the later machinery
    fault says nothing about it. The f3_alarm event marks the abort."""
    lg, st, reg, pop = env
    scripted = [make_result(dict(P4_DICT)), make_result(dict(P4_DICT))]
    client = FakeLLMClient(scripted)
    loop = make_loop(client, env)

    import empiricist.search.loop as loop_mod

    real_verify_agreed = loop_mod.verify_agreed
    calls = {"n": 0}

    def flaky_verify_agreed(registry, construction):
        calls["n"] += 1
        if calls["n"] >= 2:  # candidate 1 (0-indexed): the machinery fault
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={"disagreement": True, "stab_fusion_key": "a",
                         "enum_fusion_key": "b"},
            )
        return real_verify_agreed(registry, construction)

    monkeypatch.setattr(loop_mod, "verify_agreed", flaky_verify_agreed)

    with pytest.raises(F3Alarm):
        run(loop.run_generation(1, [p4_target()], k=2))

    # candidate 0's genuinely-agreed writes persist
    row = pop.get(P4_KEY)
    assert row is not None
    assert row.objective_vec == [1]
    assert st.get(row.cert_hash)  # CAS artifact retrievable
    assert len(lg.evidence_for(row.cert_hash)) == 1  # the upgrade evidence row

    # the alarm is durable and names the aborting candidate + counts so far
    alarms = pop.events(trigger="f3_alarm")
    assert len(alarms) == 1
    assert alarms[0].detail["candidate"] == 1
    assert alarms[0].detail["disagreement"] is True
    assert alarms[0].detail["counts_so_far"]["inserted"] == 1

    # but the wave never finished: no generation event
    assert pop.events(trigger="generation") == []


# -- round-robin + default k --------------------------------------------------


def test_prompts_round_robin_over_targets(env):
    client = FakeLLMClient([])
    loop = make_loop(client, env)
    t1 = TargetSpec(n=4, lc_orbit_key="k1", representative_edges=((0, 1),),
                     known_bound="BOUND_ONE", target_f=1)
    t2 = TargetSpec(n=5, lc_orbit_key="k2", representative_edges=((0, 1),),
                     known_bound="BOUND_TWO", target_f=2)
    run(loop.run_generation(1, [t1, t2], k=4))
    prompts = [p for _, p in client.calls]
    assert len(prompts) == 4
    assert "BOUND_ONE" in prompts[0] and "BOUND_TWO" not in prompts[0]
    assert "BOUND_TWO" in prompts[1] and "BOUND_ONE" not in prompts[1]
    assert "BOUND_ONE" in prompts[2]
    assert "BOUND_TWO" in prompts[3]


def test_default_k_uses_searcher_role_k(env):
    client = FakeLLMClient([])
    loop = make_loop(client, env)
    run(loop.run_generation(1, [p4_target()]))
    assert len(client.calls) == ROLES["searcher"].k


def test_run_generation_rejects_empty_targets(env):
    loop = make_loop(FakeLLMClient([]), env)
    with pytest.raises(ValueError):
        run(loop.run_generation(1, []))

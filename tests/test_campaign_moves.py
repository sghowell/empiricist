"""Tests for the M7 T1 campaign moves (`campaign/moves.py`): ensure_certified,
ensure_enumerate (idempotent ENUMERATE), dataset_rows, open_targets,
search_move, conjecture_move. Small/fast configs (tier0_n=5, tier1_n=4) so
the fast suite stays fast; fully offline (FakeLLMClient).
"""

from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from empiricist.campaign.moves import (
    conjecture_move,
    dataset_rows,
    ensure_certified,
    ensure_enumerate,
    open_targets,
    search_move,
)
from empiricist.campaign.state import CampaignState
from empiricist.config import RunConfig
from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.localcomp import OrbitTooLarge
from empiricist.ledger.models import Status
from empiricist.llm.client import FakeLLMClient
from empiricist.llm.models import LLMResult
from empiricist.llm.roles import ROLES
from empiricist.verifiers.enum_fusion import EnumFusionVerifier
from empiricist.verifiers.stab_fusion import StabFusionVerifier

# Deliberately tiny relative to the campaign defaults (tier0_n=9, tier1_n=7):
# tier0_search(5) + tier1_search(4) run in well under a second, and (per
# empirical check) leave exactly ONE open orbit, at n=5 (tier1 never
# examined n=5, since 5 > tier1_n=4, so the one orbit Tier-0 didn't reach at
# n=5 stays "open" with lower_bound=5 rather than being resolved to tier1).
FAST_CFG = RunConfig(tier0_n=5, tier1_n=4, search_target_n=5, targets_per_gen=8)


def run(coro):
    return asyncio.run(coro)


def make_result(parsed: dict | None) -> LLMResult:
    return LLMResult(
        text="", parsed=parsed, stop_reason="tool_use" if parsed else "end_turn",
        is_error=False, input_tokens=1, output_tokens=1, cache_read_tokens=0,
        cache_creation_tokens=0, cost_usd=0.0, duration_ms=1,
        session_id="s", uuid="u", model="claude-fable-5",
    )


@pytest.fixture()
def campaign(tmp_path):
    state = CampaignState.load(tmp_path / "run")
    yield state, FAST_CFG
    state.close()


# -- ensure_certified ---------------------------------------------------------


def test_ensure_certified_stamps_both_fusion_verifiers(campaign):
    state, _cfg = campaign
    stab, enum_v = StabFusionVerifier(), EnumFusionVerifier()
    assert not state.ledger.is_certified(stab.name, stab.version, stab.binary_hash)
    assert not state.ledger.is_certified(enum_v.name, enum_v.version, enum_v.binary_hash)

    ensure_certified(state)

    assert state.ledger.is_certified(stab.name, stab.version, stab.binary_hash)
    assert state.ledger.is_certified(enum_v.name, enum_v.version, enum_v.binary_hash)


def test_ensure_certified_second_call_skips_already_stamped_verifiers(campaign, monkeypatch):
    state, _cfg = campaign
    ensure_certified(state)

    calls: list[str] = []
    original_certify = state.registry.certify

    def spy_certify(verifier):
        calls.append(verifier.name)
        return original_certify(verifier)

    monkeypatch.setattr(state.registry, "certify", spy_certify)
    ensure_certified(state)
    assert calls == []  # idempotent: nothing re-certified


# -- ensure_enumerate ----------------------------------------------------------


def test_ensure_enumerate_produces_verified_n_dataset(campaign):
    state, cfg = campaign
    art = ensure_enumerate(state, cfg)
    assert art.status == Status.VERIFIED_N
    assert art.kind == "dataset"
    assert art.problem == "P5"
    assert art.status_n == cfg.tier0_n
    assert art.coverage == "exhaustive"

    # also certified both verifiers as a side effect of the first ENUMERATE
    stab, enum_v = StabFusionVerifier(), EnumFusionVerifier()
    assert state.ledger.is_certified(stab.name, stab.version, stab.binary_hash)
    assert state.ledger.is_certified(enum_v.name, enum_v.version, enum_v.binary_hash)


def test_ensure_enumerate_second_call_is_idempotent_and_skips_recompute(campaign, monkeypatch):
    state, cfg = campaign
    first = ensure_enumerate(state, cfg)

    import empiricist.campaign.moves as moves_mod

    def boom(*_a, **_kw):
        raise AssertionError("tier0_search must not run on an idempotent second call")

    monkeypatch.setattr(moves_mod, "tier0_search", boom)

    second = ensure_enumerate(state, cfg)
    assert second.id == first.id

    n_artifacts = state.ledger.conn.execute(
        "SELECT COUNT(*) FROM artifacts WHERE kind='dataset'"
    ).fetchone()[0]
    assert n_artifacts == 1  # no duplicate ingest


def test_ensure_enumerate_recovers_from_reingest_identity_collision(campaign, monkeypatch):
    """Documented recovery path: if the idempotency short-circuit (find_
    artifacts) somehow misses an already-ingested dataset, re-deriving and
    re-ingesting identical content collides on the artifact's PRIMARY KEY
    (its id IS the content digest) -- ensure_enumerate must catch that
    sqlite3.IntegrityError and load the existing artifact rather than crash.
    Forced here by monkeypatching find_artifacts to always report "nothing
    found" so the second call falls all the way through to re-ingest."""
    state, cfg = campaign
    first = ensure_enumerate(state, cfg)

    monkeypatch.setattr(state.ledger, "find_artifacts", lambda **_kw: [])

    second = ensure_enumerate(state, cfg)
    assert second.id == first.id
    assert second.status == Status.VERIFIED_N

    n_artifacts = state.ledger.conn.execute(
        "SELECT COUNT(*) FROM artifacts WHERE kind='dataset'"
    ).fetchone()[0]
    assert n_artifacts == 1  # the collision recovered to the SAME row, not a duplicate


# -- dataset_rows ---------------------------------------------------------------


def test_dataset_rows_shape(campaign):
    state, cfg = campaign
    art = ensure_enumerate(state, cfg)
    rows = dataset_rows(state, art)

    assert isinstance(rows, list) and rows
    assert {r["n"] for r in rows} == {3, 4, 5}
    for row in rows:
        assert set(row) == {
            "n", "orbit_id", "representative_edges", "F", "lower_bound",
            "exact", "tier", "witness",
        }


# -- open_targets ---------------------------------------------------------------


def test_open_targets_maps_the_real_open_row_at_n5(campaign):
    state, cfg = campaign
    art = ensure_enumerate(state, cfg)
    rows = dataset_rows(state, art)

    targets = open_targets(rows, 5, 8)
    assert len(targets) == 1
    t = targets[0]
    assert t.n == 5
    assert t.target_f == 5
    assert t.known_bound == "F >= 5"

    [open_row] = [r for r in rows if r["n"] == 5 and not r["exact"]]
    expected_key = lc_orbit_key(
        GraphState(n=5, edges=[tuple(e) for e in open_row["representative_edges"]])
    )
    assert t.lc_orbit_key == expected_key
    # open_targets computes the TRUE lc_orbit_key (canonical.py), never the
    # tablebase's own orbit_id namespace (the M6 carryover finding, see
    # search/conjecture.py's module docstring) -- this particular row's two
    # ids happen to coincide (documented there as a one-off coincidence, not
    # a general fact), so it is not asserted here; test_open_targets_caps_
    # and_sorts_by_orbit_id below uses a row where they visibly differ.
    assert t.representative_edges == tuple(tuple(e) for e in open_row["representative_edges"])


def test_open_targets_no_open_rows_at_a_fully_resolved_n(campaign):
    state, cfg = campaign
    art = ensure_enumerate(state, cfg)
    rows = dataset_rows(state, art)
    assert open_targets(rows, 3, 8) == []  # n=3 has no open orbit (Adcock: 1, all tier0)


def test_open_targets_caps_and_sorts_by_orbit_id():
    rows = [
        {"n": 4, "orbit_id": "zzz-path", "representative_edges": [[0, 1], [1, 2], [2, 3]],
         "F": None, "lower_bound": 4, "exact": False, "tier": "open"},
        {"n": 4, "orbit_id": "aaa-star", "representative_edges": [[0, 1], [0, 2], [0, 3]],
         "F": None, "lower_bound": 4, "exact": False, "tier": "open"},
        {"n": 5, "orbit_id": "mmm", "representative_edges": [[0, 1], [1, 2], [2, 3], [3, 4]],
         "F": None, "lower_bound": 5, "exact": False, "tier": "open"},
    ]
    targets = open_targets(rows, 4, cap=1)
    assert len(targets) == 1
    assert targets[0].known_bound == "F >= 4"
    assert targets[0].target_f == 4
    # sorted by orbit_id -> "aaa-star" precedes "zzz-path"
    star_key = lc_orbit_key(GraphState(n=4, edges=[(0, 1), (0, 2), (0, 3)]))
    assert targets[0].lc_orbit_key == star_key


def test_open_targets_target_f_is_the_achievable_rung_not_n():
    """Beyond-frontier: for an open orbit whose lower bound is N+3 (n=6/7
    F>=N+3 opens no deterministic tier reached), target_f must be the
    achievable rung (lower_bound=N+3), NOT N -- else the exact-upgrade
    detector could never score an F=N+3 witness. For n=8/9 opens
    (lower_bound=N) target_f stays N, so this is backward-compatible."""
    rows = [
        # a beyond-frontier n=6 open orbit at F>=9 (=N+3)
        {"n": 6, "orbit_id": "hard6", "representative_edges": [[0, 1], [1, 2], [2, 3],
         [3, 4], [4, 5], [5, 0], [0, 3], [1, 4], [2, 5]],
         "F": None, "lower_bound": 9, "exact": False, "tier": "open"},
    ]
    [t] = open_targets(rows, 6, cap=8)
    assert t.target_f == 9  # the achievable rung, not n=6
    assert t.known_bound == "F >= 9"


def test_open_targets_skips_orbit_too_large(monkeypatch):
    import empiricist.campaign.moves as moves_mod

    rows = [
        {"n": 5, "orbit_id": "a", "representative_edges": [[0, 1], [1, 2], [2, 3], [3, 4]],
         "F": None, "lower_bound": 5, "exact": False, "tier": "open"},
    ]

    def boom(_g):
        raise OrbitTooLarge("orbit exceeded cap")

    monkeypatch.setattr(moves_mod, "lc_orbit_key", boom)
    assert moves_mod.open_targets(rows, 5, 8) == []


# -- search_move ------------------------------------------------------------


def test_search_move_raises_when_no_open_targets(campaign):
    state, cfg = campaign
    fully_resolved_cfg = replace(cfg, search_target_n=3)
    client = FakeLLMClient([])
    with pytest.raises(ValueError):
        run(search_move(state, fully_resolved_cfg, client, gen=1))


def test_search_move_scripted_refusal_and_screen_reject(campaign):
    """No real hits required to prove the plumbing works end to end -- a
    refusal (no_artifact) and a self-fuse (screen-reject) are enough to
    exercise ensure_enumerate -> open_targets -> SearchLoop.run_generation
    -> GenerationReport + a durable search_events "generation" row."""
    state, cfg = campaign
    self_fuse = {
        "resources": 2,
        "steps": [{"op": "fuse", "args": [2, 2]}],
        "target_n": 4,
        "target_edges": [[0, 1]],
    }
    scripted = [make_result(None), make_result(self_fuse)]
    client = FakeLLMClient(scripted)

    report = run(search_move(state, cfg, client, gen=1))

    assert report.gen == 1
    assert report.sampled == ROLES["searcher"].k
    assert report.screened_out == 1
    assert report.no_artifact == report.sampled - 1
    assert report.verify_fail == 0
    assert report.verify_error == 0
    assert report.inserted == 0
    assert report.duplicates == 0
    assert report.exact_upgrades == ()

    events = state.population.events(trigger="generation")
    assert len(events) == 1
    assert events[0].gen == 1


# -- conjecture_move ----------------------------------------------------------


def test_conjecture_move_true_conjecture_lands_conjectured(campaign):
    state, cfg = campaign
    conj_dict = {
        "family": "path", "closed_form": "N-3",
        "predicted_values": {"3": 0, "4": 1, "5": 2}, "confidence": 0.9,
    }
    client = FakeLLMClient([make_result(conj_dict)])

    artifacts = run(conjecture_move(state, cfg, client))

    assert len(artifacts) == 1
    art = artifacts[0]
    assert art.status == Status.HEURISTIC  # submit's pre-evidence snapshot
    fetched = state.ledger.get_artifact(art.id)
    assert fetched.status == Status.CONJECTURED

    evidence = state.ledger.evidence_for(art.id)
    assert len(evidence) == 1
    assert evidence[0].verifier == "auto_attack"


def test_conjecture_move_false_conjecture_lands_refuted(campaign):
    state, cfg = campaign
    conj_dict = {
        "family": "path", "closed_form": "N-2",
        "predicted_values": {"5": 4}, "confidence": 0.5,
    }
    client = FakeLLMClient([make_result(conj_dict)])

    artifacts = run(conjecture_move(state, cfg, client))

    assert len(artifacts) == 1
    fetched = state.ledger.get_artifact(artifacts[0].id)
    assert fetched.status == Status.REFUTED


def test_conjecture_move_duplicates_yield_one_artifact_one_evidence_row(campaign):
    """C1: byte-identical conjectures -- twice in the SAME wave, then again
    in a SECOND wave -- must produce exactly one artifact with exactly one
    evidence row, no sqlite3.IntegrityError, and the duplicates excluded
    from the returned (progress-counted) list."""
    state, cfg = campaign
    conj_dict = {
        "family": "path", "closed_form": "N-3",
        "predicted_values": {"3": 0, "4": 1, "5": 2}, "confidence": 0.9,
    }

    # Wave 1: the same conjecture mined twice in one wave.
    client1 = FakeLLMClient([make_result(conj_dict), make_result(conj_dict)])
    artifacts1 = run(conjecture_move(state, cfg, client1))
    assert len(artifacts1) == 1

    # Wave 2 (the resume case): the same conjecture re-mined -- must not crash.
    client2 = FakeLLMClient([make_result(conj_dict)])
    artifacts2 = run(conjecture_move(state, cfg, client2))
    assert artifacts2 == []  # duplicate skipped -> reads as no progress

    n_statements = state.ledger.conn.execute(
        "SELECT COUNT(*) FROM artifacts WHERE kind='statement'"
    ).fetchone()[0]
    assert n_statements == 1
    assert state.ledger.get_artifact(artifacts1[0].id).status == Status.CONJECTURED
    assert len(state.ledger.evidence_for(artifacts1[0].id)) == 1  # one attack, ever


def test_conjecture_move_reworded_duplicates_yield_one_artifact(campaign):
    """M9 live-campaign fix: the SAME (family, predicted_values) mined
    twice with DIFFERENT closed_form prose -- the exact shape of the live
    finding (10 CONJECTURED artifacts, all one conjecture reworded) -- must
    collapse to one CONJECTURED artifact, not two."""
    state, cfg = campaign
    same_values = {"3": 0, "4": 1, "5": 2}
    conj_dict_a = {
        "family": "path", "closed_form": "N-3",
        "predicted_values": same_values, "confidence": 0.9,
    }
    conj_dict_b = {
        "family": "path", "closed_form": "the fusion count equals N minus 3",
        "predicted_values": same_values, "confidence": 0.4,
    }
    client = FakeLLMClient([make_result(conj_dict_a), make_result(conj_dict_b)])

    artifacts = run(conjecture_move(state, cfg, client))

    assert len(artifacts) == 1  # the reworded restatement was skipped
    n_statements = state.ledger.conn.execute(
        "SELECT COUNT(*) FROM artifacts WHERE kind='statement'"
    ).fetchone()[0]
    assert n_statements == 1
    assert state.ledger.get_artifact(artifacts[0].id).status == Status.CONJECTURED
    assert len(state.ledger.evidence_for(artifacts[0].id)) == 1


def test_conjecture_move_passes_state_ledger_to_mine(campaign, monkeypatch):
    """M9 live-campaign fix: Conjecturer calls were previously untracked
    (no `ledger` forwarded to `client.complete_many`, so no `runs` row, no
    cost/provenance). `conjecture_move` must pass `state.ledger` into
    `mine`."""
    state, cfg = campaign
    import empiricist.campaign.moves as moves_mod

    calls: list[dict] = []
    original_mine = moves_mod.mine

    async def spy_mine(client, rows, *, k=None, ledger=None):
        calls.append({"ledger": ledger})
        return await original_mine(client, rows, k=k, ledger=ledger)

    monkeypatch.setattr(moves_mod, "mine", spy_mine)

    client = FakeLLMClient([])
    run(conjecture_move(state, cfg, client))

    assert len(calls) == 1
    assert calls[0]["ledger"] is state.ledger


# -- open_targets: solved-orbit filtering (I3) ---------------------------------


def test_open_targets_drops_orbit_solved_in_population(campaign):
    state, cfg = campaign
    art = ensure_enumerate(state, cfg)
    rows = dataset_rows(state, art)
    [target] = open_targets(rows, 5, 8)

    # A certified witness at exactly target_f (F=5): solved.
    state.population.consider(target.lc_orbit_key, 0, "n5", [5.0], "c" * 64)

    assert open_targets(rows, 5, 8, population=state.population) == []
    # Without the population handle, behavior is unchanged (dataset-only view).
    assert len(open_targets(rows, 5, 8)) == 1


def test_open_targets_keeps_orbit_whose_witness_is_above_target_f(campaign):
    """A population elite ABOVE target_f (e.g. an F=8 construction for an
    orbit whose F=5 question is still open, mod-3 ladder) does NOT drop the
    target -- the bound the campaign is after has not been reached."""
    state, cfg = campaign
    art = ensure_enumerate(state, cfg)
    rows = dataset_rows(state, art)
    [target] = open_targets(rows, 5, 8)

    state.population.consider(target.lc_orbit_key, 0, "n5", [8.0], "c" * 64)

    filtered = open_targets(rows, 5, 8, population=state.population)
    assert len(filtered) == 1
    assert filtered[0].lc_orbit_key == target.lc_orbit_key

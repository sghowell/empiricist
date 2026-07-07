"""Tests for conjecture mining + deterministic auto-ATTACK (M6 T4, spec §9).

`family_table`/`attack`'s table-lookup branches run against a REAL small
VERIFIED_N dataset (`tier0_search(6)` + `tier1_search(6)` -> `build_dataset`,
module-scoped fixture -- a few seconds, matching `test_p5_dataset.py`'s own
`small_dataset` fixture). The open-row lower-bound ATTACK branch (checks
step 4 in the plan) is the one exception: none of the four named families
(path/cycle/star/complete) leave an OPEN row anywhere in n<=6 -- the dataset's
sole open row at n=6 is a 3-regular graph not LC-equivalent to any of them
(`test_p5_dataset.py::test_build_dataset_tier_labels` pins n=6 at 8 tier0 + 2
tier1 + 1 open). That branch is exercised against a SYNTHETIC row instead
(documented at the test itself) -- real data everywhere it exists, a
fabricated-but-representative row only where the real dataset has no
example to offer.
"""

from __future__ import annotations

import asyncio

import pytest

from empiricist.domain.p5.dataset import build_dataset
from empiricist.domain.p5.tablebase import tier0_search, tier1_search
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Status, Verdict
from empiricist.llm.client import FakeLLMClient
from empiricist.llm.models import LLMResult
from empiricist.llm.roles import ROLES
from empiricist.llm.schemas import ConjectureOut
from empiricist.search.conjecture import (
    attack,
    dataset_summary,
    family_graph,
    family_table,
    mine,
    submit,
)
from empiricist.store import Store


def run(coro):
    return asyncio.run(coro)


def make_result(parsed: dict | None) -> LLMResult:
    return LLMResult(
        text="", parsed=parsed, stop_reason="tool_use" if parsed else "end_turn",
        is_error=False, input_tokens=1, output_tokens=1, cache_read_tokens=0,
        cache_creation_tokens=0, cost_usd=0.0, duration_ms=1,
        session_id="s", uuid="u", model="claude-fable-5",
    )


@pytest.fixture(scope="module")
def small_dataset_rows():
    tier0 = tier0_search(6)
    tier1 = tier1_search(6)
    return build_dataset(tier0, tier1)["rows"]


@pytest.fixture()
def env(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    st = Store(tmp_path / "store")
    yield lg, st
    lg.close()


# -- family_graph -------------------------------------------------------------


def test_family_graph_path_p4_edges():
    g = family_graph("path", 4)
    assert g.n == 4
    assert set(g.edges) == {(0, 1), (1, 2), (2, 3)}


def test_family_graph_cycle_c5_edges():
    g = family_graph("cycle", 5)
    assert g.n == 5
    assert set(g.edges) == {(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)}


def test_family_graph_star6_edges():
    g = family_graph("star", 6)
    assert g.n == 6
    assert set(g.edges) == {(0, 1), (0, 2), (0, 3), (0, 4), (0, 5)}


def test_family_graph_complete_k4_edges():
    g = family_graph("complete", 4)
    assert g.n == 4
    assert set(g.edges) == {(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)}


def test_family_graph_cycle_rejects_n_below_3():
    assert family_graph("cycle", 2) is None
    assert family_graph("cycle", 0) is None
    assert family_graph("cycle", -1) is None


def test_family_graph_unknown_family_returns_none():
    assert family_graph("wheel", 5) is None
    assert family_graph("tree", 4) is None


# -- family_table: matched against the REAL small dataset -----------------


def test_family_table_paths_exact_n_minus_3(small_dataset_rows):
    table = family_table(small_dataset_rows, ["path"])
    for n in range(3, 7):
        assert table["path"][n] == n - 3


def test_family_table_cycle_c6_is_tier1_not_n_minus_3(small_dataset_rows):
    """C6 is NOT all-merge reachable at n=6 -- it resolves via Tier-1's one
    intra fusion, so F=6 (== N), not the Tier-0 floor N-3=3. This is one of
    n=6's two tier1 rows (test_p5_dataset.py pins 8 tier0 + 2 tier1 + 1 open
    at n=6)."""
    table = family_table(small_dataset_rows, ["cycle"])
    assert table["cycle"][6] == 6
    assert table["cycle"][5] == 5  # same story at n=5 (1 tier1 row there)
    assert table["cycle"][3] == 0
    assert table["cycle"][4] == 1


def test_family_table_n3_all_families_collapse_to_ghz_orbit(small_dataset_rows):
    """n=3 has exactly one connected orbit (Adcock: 1) -- K3 == C3 == star3,
    so every family reports the same F=0 at n=3."""
    table = family_table(small_dataset_rows, ["path", "cycle", "star", "complete"])
    for family in ("path", "cycle", "star", "complete"):
        assert table[family][3] == 0


def test_family_table_star_and_complete_exact_up_to_n6(small_dataset_rows):
    table = family_table(small_dataset_rows, ["star", "complete"])
    for n in range(3, 7):
        assert table["star"][n] == n - 3
        assert table["complete"][n] == n - 3


def test_family_table_unknown_family_yields_empty(small_dataset_rows):
    table = family_table(small_dataset_rows, ["not-a-family"])
    assert table["not-a-family"] == {}


# -- dataset_summary ------------------------------------------------------


def test_dataset_summary_contains_families_values_and_invariants(small_dataset_rows):
    text = dataset_summary(small_dataset_rows)
    assert "path:" in text
    assert "n=3: F=0" in text
    assert "n=6: F=6" in text  # cycle's tier1 value
    assert "N-3 (mod 3)" in text
    assert "N-3" in text


# -- attack: (a) TRUE conjecture survives ----------------------------------


def test_attack_true_path_conjecture_survives(small_dataset_rows):
    conj = ConjectureOut(
        family="path", closed_form="N-3",
        predicted_values={"3": 0, "4": 1, "5": 2, "6": 3},
        confidence=0.95,
    )
    report = attack(conj, small_dataset_rows)
    assert report.survived is True
    assert report.counterexample is None
    assert report.checks >= 4


# -- attack: (b) off-by-THREE -> the EXACT-ROW check fires -----------------


def test_attack_off_by_three_refuted_by_exact_row_not_mod3(small_dataset_rows):
    """N instead of N-3 for path at n=6: mod-3-clean (6 === 3 (mod 3), same
    residue as N-3=3) and clears the floor (6 >= 3), so it survives checks
    1-2 and is refuted only by the table's exact-F comparison (check 3)."""
    conj = ConjectureOut(
        family="path", closed_form="N", predicted_values={"6": 6}, confidence=0.5,
    )
    report = attack(conj, small_dataset_rows)
    assert report.survived is False
    assert report.checks == 3  # mod3 (pass) + floor (pass) + table (fail)
    assert "n=6" in report.counterexample
    assert "predicted F=6" in report.counterexample
    assert "actual (exact) F=3" in report.counterexample


# -- attack: (c) mod-3 violation --------------------------------------------


def test_attack_mod3_violation_refuted_at_first_check(small_dataset_rows):
    """Off-by-one always breaks the mod-3 ladder (adding/subtracting 1
    always changes the residue mod 3): predicted=4 at n=6 vs N-3=3 -- 4%3=1
    != 3%3=0."""
    conj = ConjectureOut(
        family="path", closed_form="N-2", predicted_values={"6": 4}, confidence=0.5,
    )
    report = attack(conj, small_dataset_rows)
    assert report.survived is False
    assert report.checks == 1
    assert "mod 3" in report.counterexample
    assert "n=6" in report.counterexample


# -- attack: (d) floor violation --------------------------------------------


def test_attack_floor_violation_refuted_at_second_check(small_dataset_rows):
    """Off-by-THREE downward (n-6, mod-3-clean relative to N-3) undercuts
    the floor N-3 before ever reaching the table check: predicted=0 at n=6
    passes mod3 (0%3==3%3==0) but 0 < N-3=3."""
    conj = ConjectureOut(
        family="path", closed_form="N-6", predicted_values={"6": 0}, confidence=0.5,
    )
    report = attack(conj, small_dataset_rows)
    assert report.survived is False
    assert report.checks == 2
    assert "floor" in report.counterexample
    assert "n=6" in report.counterexample


# -- attack: (e) open-row lower-bound violation (SYNTHETIC row) -------------


def test_attack_open_row_lower_bound_violation_synthetic_row(small_dataset_rows):
    """None of path/cycle/star/complete leave an open row within n<=6 (see
    module docstring), so this fabricates ONE synthetic open row for the
    star family at n=7 (representative_edges = the real star-7 edge set, so
    `attack`'s lc_orbit_key lookup genuinely matches it) claiming a proven
    lower bound of F>=10 -- well above the floor N-3=4 -- and predicts
    F=7: mod-3-clean (7%3=1 == (7-3)%3=1) and clears the floor (7>=4), so it
    is refuted ONLY by undercutting the synthetic bound."""
    star7_edges = [[0, i] for i in range(1, 7)]
    synthetic_row = {
        "n": 7,
        "orbit_id": "synthetic-star7",
        "representative_edges": star7_edges,
        "F": None,
        "lower_bound": 10,
        "exact": False,
        "tier": "open",
        "witness": None,
    }
    rows = [*small_dataset_rows, synthetic_row]

    conj = ConjectureOut(
        family="star", closed_form="N-3", predicted_values={"7": 7}, confidence=0.5,
    )
    report = attack(conj, rows)
    assert report.survived is False
    assert report.checks == 3  # mod3 (pass) + floor (pass) + table/bound (fail)
    assert "n=7" in report.counterexample
    assert "predicted F=7" in report.counterexample
    assert "lower bound 10" in report.counterexample


def test_attack_open_row_prediction_meeting_bound_survives_when_grounded(small_dataset_rows):
    """The mirror case: a prediction AT/ABOVE the synthetic bound survives
    that check (no claim of exactness is made for an open row). The
    conjecture must ALSO carry exact-row grounding (n=3..6, all exact star
    rows) -- an open-row match alone does not ground promotion (see the
    ungrounded tests below)."""
    star7_edges = [[0, i] for i in range(1, 7)]
    synthetic_row = {
        "n": 7,
        "orbit_id": "synthetic-star7",
        "representative_edges": star7_edges,
        "F": None,
        "lower_bound": 10,
        "exact": False,
        "tier": "open",
        "witness": None,
    }
    rows = [*small_dataset_rows, synthetic_row]

    conj = ConjectureOut(
        family="star", closed_form="N-3 (except the open n=7 row)",
        predicted_values={"3": 0, "4": 1, "5": 2, "6": 3, "7": 10}, confidence=0.5,
    )
    report = attack(conj, rows)
    assert report.survived is True
    assert report.counterexample is None


# -- attack: gate 0 + grounding (M6 T5 review I1/I2) --------------------------


def test_attack_malformed_word_key_is_refuted_not_a_crash(small_dataset_rows):
    """Reproducer for the I1 crash: a model-supplied non-integer key must
    refute, never let int() raise out of attack()."""
    conj = ConjectureOut(
        family="path", closed_form="N-3", predicted_values={"eight": 8}, confidence=0.5,
    )
    report = attack(conj, small_dataset_rows)
    assert report.survived is False
    assert report.checks == 0
    assert report.counterexample == "malformed prediction key 'eight'"


def test_attack_malformed_empty_key_is_refuted_not_a_crash(small_dataset_rows):
    """Second I1 reproducer: the empty-string key."""
    conj = ConjectureOut(
        family="path", closed_form="N-3", predicted_values={"": 5}, confidence=0.5,
    )
    report = attack(conj, small_dataset_rows)
    assert report.survived is False
    assert report.checks == 0
    assert report.counterexample == "malformed prediction key ''"


def test_attack_empty_predictions_refuted_as_vacuous(small_dataset_rows):
    """A conjecture that predicts nothing can never be falsified -- and so
    can never be promoted: checks=0 must NOT read as survival."""
    conj = ConjectureOut(
        family="path", closed_form="N-3", predicted_values={}, confidence=0.9,
    )
    report = attack(conj, small_dataset_rows)
    assert report.survived is False
    assert report.checks == 0
    assert report.counterexample == "no predictions offered"


def test_attack_unknown_family_refuted(small_dataset_rows):
    """A family attack() has no generator for admits zero table lookups --
    invariants-only survival would be ungrounded by construction, so it is
    refuted up front."""
    conj = ConjectureOut(
        family="wheel", closed_form="N", predicted_values={"6": 6}, confidence=0.5,
    )
    report = attack(conj, small_dataset_rows)
    assert report.survived is False
    assert report.checks == 0
    assert report.counterexample == "unknown family 'wheel'"


def test_attack_entirely_out_of_range_is_ungrounded_not_promoted(small_dataset_rows):
    """No row exists for n=100 -- the table check (3) is skipped, so only
    the 2 invariant checks run and pass. Under the corrected semantics that
    is NOT survival: nothing overlapped the exact table, so the conjecture
    is unpromotable (ungrounded), reported as survived=False with the
    documented non-contradiction counterexample."""
    conj = ConjectureOut(
        family="path", closed_form="N-3", predicted_values={"100": 97}, confidence=0.5,
    )
    report = attack(conj, small_dataset_rows)
    assert report.survived is False
    assert report.checks == 2  # mod3 + floor both ran (and passed)
    assert report.counterexample == "no prediction overlaps the exact table (ungrounded)"


def test_attack_open_row_overlap_alone_is_ungrounded(small_dataset_rows):
    """Grounding means an EXACT-row comparison passed: overlapping only an
    open row (bound met, nothing contradicted) proves consistency with
    nothing that is actually known, so it is unpromotable too."""
    star7_edges = [[0, i] for i in range(1, 7)]
    synthetic_row = {
        "n": 7,
        "orbit_id": "synthetic-star7",
        "representative_edges": star7_edges,
        "F": None,
        "lower_bound": 10,
        "exact": False,
        "tier": "open",
        "witness": None,
    }
    rows = [*small_dataset_rows, synthetic_row]

    conj = ConjectureOut(
        family="star", closed_form="N+3", predicted_values={"7": 10}, confidence=0.5,
    )
    report = attack(conj, rows)
    assert report.survived is False
    assert report.checks == 3  # mod3 + floor + open-row bound, all ran (and passed)
    assert report.counterexample == "no prediction overlaps the exact table (ungrounded)"


def test_attack_mixed_range_with_exact_grounding_survives(small_dataset_rows):
    """SOME in-range exact matches + some out-of-range predictions: the
    exact rows ground the conjecture, the out-of-range n=100 prediction is
    invariant-checked only, and the whole thing survives."""
    conj = ConjectureOut(
        family="path", closed_form="N-3",
        predicted_values={"3": 0, "4": 1, "5": 2, "6": 3, "100": 97}, confidence=0.9,
    )
    report = attack(conj, small_dataset_rows)
    assert report.survived is True
    assert report.counterexample is None
    assert report.checks == 4 * 3 + 2  # 3 checks per in-range n, 2 for n=100


# -- submit -----------------------------------------------------------------


def test_submit_survivor_lands_conjectured_with_pass_evidence(env, small_dataset_rows):
    lg, st = env
    conj = ConjectureOut(
        family="path", closed_form="N-3",
        predicted_values={"3": 0, "4": 1, "5": 2, "6": 3}, confidence=0.9,
    )
    report = attack(conj, small_dataset_rows)
    assert report.survived is True

    art = submit(lg, st, conj, report)
    assert art.status == Status.HEURISTIC  # pre-evidence snapshot

    fetched = lg.get_artifact(art.id)
    assert fetched.status == Status.CONJECTURED

    evidence = lg.evidence_for(art.id)
    assert len(evidence) == 1
    assert evidence[0].verifier == "auto_attack"
    assert evidence[0].verdict == Verdict.PASS
    assert evidence[0].details["checks"] == report.checks
    assert evidence[0].details["counterexample"] is None


def test_submit_refuted_lands_refuted_with_fail_evidence_and_counterexample(
    env, small_dataset_rows
):
    lg, st = env
    conj = ConjectureOut(
        family="path", closed_form="N-2", predicted_values={"6": 4}, confidence=0.5,
    )
    report = attack(conj, small_dataset_rows)
    assert report.survived is False

    art = submit(lg, st, conj, report)
    fetched = lg.get_artifact(art.id)
    assert fetched.status == Status.REFUTED

    evidence = lg.evidence_for(art.id)
    assert len(evidence) == 1
    assert evidence[0].verdict == Verdict.FAIL
    assert evidence[0].details["counterexample"] == report.counterexample
    assert evidence[0].details["counterexample"] is not None


def test_submit_refuted_artifact_is_terminal(env, small_dataset_rows):
    """REFUTED is terminal (spec §4.1) -- a further record_evidence attempt
    to change its status must raise, same discipline as every other REFUTED
    artifact in the ledger."""
    from empiricist.ledger.db import TerminalStatusError
    from empiricist.ledger.models import EvidenceRow

    lg, st = env
    conj = ConjectureOut(
        family="path", closed_form="N-2", predicted_values={"6": 4}, confidence=0.5,
    )
    report = attack(conj, small_dataset_rows)
    art = submit(lg, st, conj, report)

    with pytest.raises(TerminalStatusError):
        lg.record_evidence(
            EvidenceRow(
                artifact_id=art.id, verifier="x", verifier_version="1.0",
                binary_hash="x", verdict=Verdict.PASS,
            ),
            new_status=Status.CONJECTURED,
        )


# -- mine: FakeLLMClient round trip ------------------------------------------


def test_mine_returns_scripted_conjectures_round_trip(small_dataset_rows):
    conj_dict = {
        "family": "path", "closed_form": "N-3",
        "predicted_values": {"3": 0, "4": 1, "5": 2, "6": 3}, "confidence": 0.9,
    }
    client = FakeLLMClient([make_result(conj_dict)])
    conjs = run(mine(client, small_dataset_rows, k=1))
    assert len(conjs) == 1
    assert isinstance(conjs[0], ConjectureOut)
    assert conjs[0].family == "path"
    assert conjs[0].predicted_values["4"] == 1

    role_name, prompt = client.calls[0]
    assert role_name == "conjecturer"
    assert "path:" in prompt
    assert "N-3 (mod 3)" in prompt


def test_mine_skips_no_artifact_and_schema_invalid(small_dataset_rows):
    invalid = {"family": "path"}  # missing required fields
    client = FakeLLMClient([make_result(None), make_result(invalid)])
    conjs = run(mine(client, small_dataset_rows, k=2))
    assert conjs == []


def test_mine_default_k_uses_conjecturer_role_k(small_dataset_rows):
    client = FakeLLMClient([])
    run(mine(client, small_dataset_rows))
    assert len(client.calls) == ROLES["conjecturer"].k


def test_mine_prompts_are_nonce_diversified(small_dataset_rows):
    client = FakeLLMClient([])
    run(mine(client, small_dataset_rows, k=3))
    prompts = [p for _, p in client.calls]
    assert len(set(prompts)) == 3  # every prompt carries a distinct nonce

"""`empiricist.packs.zx.campaign` (M25b): the completion move -- `SystemOut`, the playbook
prompt, `evaluate` with claim minting -- and the campaign loop with its driver, all offline
against a temporary claims repository and a scripted `FakeLLMClient`.

Measured facts these tests rest on (M25a groundwork plus the M25b probes): the seed
(R0core + the six scalar eliminations) is sound at arity 2, terminates under (vertices,
edges), is locally confluent within depth 4 at arity 2 and is incomplete for C(2, 1, 2)
(Z(0) and X(0) with a Hadamard self-loop both become a zero scalar); the seed plus
colour_change and the two Hadamard-on-a-state rules of R1 passes all four checks on
C(1, 1, 1) at depth 2 and has a non-joinable pair at depth 1 (colour_change against
fusion_x)."""
from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from empiricist.claims.check import check
from empiricist.claims.model import load_all
from empiricist.llm.roles import ROLES
from empiricist.llm.schemas import json_schema_for
from empiricist.packs import certify_pack_verifier
from empiricist.packs.zx import MANIFEST, termination
from empiricist.packs.zx import campaign as cp
from empiricist.packs.zx.rules import RULES

VERIFIERS = ("zx_rule_sound", "zx_termination", "zx_critical_pairs", "zx_completeness")
PROJECT = Path(__file__).resolve().parents[1]

STATE_H_Z_1_2 = {
    "name": "state_h_z_1_2",
    "lhs": {"vertices": [[0, "B", "0"], [1, "Z", "1/2"]], "edges": [[0, 1, True]],
            "inputs": [], "outputs": [0]},
    "rhs": {"vertices": [[0, "B", "0"], [2, "Z", "3/2"]], "edges": [[0, 2, False]],
            "inputs": [], "outputs": [0]},
    "residual": [],
    "reference": "a Hadamard on the single-leg state Z(1/2 pi) is the state Z(3/2 pi) up to "
                 "scalar",
}
STATE_H_Z_3_2 = {
    "name": "state_h_z_3_2",
    "lhs": {"vertices": [[0, "B", "0"], [1, "Z", "3/2"]], "edges": [[0, 1, True]],
            "inputs": [], "outputs": [0]},
    "rhs": {"vertices": [[0, "B", "0"], [2, "Z", "1/2"]], "edges": [[0, 2, False]],
            "inputs": [], "outputs": [0]},
    "residual": [],
    "reference": "a Hadamard on the single-leg state Z(3/2 pi) is the state Z(1/2 pi) up to "
                 "scalar",
}
COLOUR_CHANGE_NO_FLIP = {
    "name": "colour_change_no_flip",
    "lhs": {"vertices": [[0, "X", "a"]], "edges": [], "inputs": [], "outputs": []},
    "rhs": {"vertices": [[0, "Z", "a"]], "edges": [], "inputs": [], "outputs": []},
    "residual": [[0, [[0, False]]]],
    "reference": "test: (H) without the leg flip -- unsound with a leg",
}
MEASURE_A = ["vertices", "x_vertices", "edges", "hadamard_edges"]


def system_a(depth: int = 2) -> cp.SystemOut:
    return cp.SystemOut(
        rules=[*cp.R0CORE, "colour_change", *cp.SEED_INLINE_RULES, STATE_H_Z_1_2, STATE_H_Z_3_2],
        measure=MEASURE_A, depth=depth,
        rationale="the seed plus colour change and the Hadamard-on-a-state rules",
    )


def unsound_system() -> cp.SystemOut:
    return cp.SystemOut(rules=[*cp.R0CORE, COLOUR_CHANGE_NO_FLIP, *cp.SEED_INLINE_RULES],
                        measure=MEASURE_A, depth=2, rationale="colour change without the flip")


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(scope="module")
def template_repo(tmp_path_factory) -> Path:
    repo = tmp_path_factory.mktemp("template")
    for name in VERIFIERS:
        stamp, problems = certify_pack_verifier(repo, name)
        assert stamp is not None, problems
    return repo


@pytest.fixture()
def repo(tmp_path, template_repo) -> Path:
    target = tmp_path / "repo"
    shutil.copytree(template_repo, target)
    return target


def claim_files(repo: Path) -> dict[str, dict]:
    return {c.id: c.model_dump() for c in load_all(repo).values()}


# ----------------------------------------------------------------------------- the schema


def test_system_out_is_closed_and_bounded_in_code_not_schema():
    s = cp.SystemOut(rules=["fusion"], measure=["vertices"], depth=3, rationale="r")
    assert s.depth == 3
    with pytest.raises(ValidationError):
        cp.SystemOut(rules=["fusion"], measure=["vertices"], depth=3, rationale="r", extra=1)
    for bad in (0, cp.MAX_PROPOSED_DEPTH + 1):
        with pytest.raises(ValidationError):
            cp.SystemOut(rules=["fusion"], measure=["vertices"], depth=bad, rationale="r")
    with pytest.raises(ValidationError):
        cp.SystemOut(rules=[], measure=["vertices"], depth=1, rationale="r")
    with pytest.raises(ValidationError):
        cp.SystemOut(rules=["fusion"], measure=[], depth=1, rationale="r")
    schema = json_schema_for(cp.SystemOut)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"rules", "measure", "depth", "rationale"}
    assert "minimum" not in json.dumps(schema) and "maximum" not in json.dumps(schema)


def test_proposer_role_is_generic_and_active():
    role = ROLES[cp.ROLE]
    assert role.active and role.k == 2
    assert "ONE candidate object" in role.system_prompt
    for word in ("ZX", "rewrite", "spider", "P6"):
        assert word not in role.system_prompt


def test_seed_is_r0core_plus_r1s_scalar_rules():
    committed = json.loads((PROJECT / "claims/evidence/p6/r1_completeness_c212.json").read_text())
    scalars = [r for r in committed["rules"] if isinstance(r, dict)
               and r["name"].startswith("scalar_")]
    assert list(cp.SEED_INLINE_RULES) == scalars
    assert cp.SEED.rules[:12] == list(cp.R0CORE)
    assert cp.FORMULATION == MANIFEST.problems["P6"]


# ----------------------------------------------------------------------------- rules and ids


def test_resolve_rules_library_reverse_inline_and_known():
    s = cp.SystemOut(rules=["fusion", {"reverse": "colour_change"}, STATE_H_Z_1_2, "extra"],
                     measure=["vertices"], depth=1, rationale="")
    with pytest.raises(cp.InvalidSystem, match="unknown rule name 'extra'"):
        cp.resolve_rules(s)
    known = {"extra": RULES["hopf"]}
    rules = cp.resolve_rules(s, known)
    assert [r.name for r in rules] == ["fusion", "colour_change_rev", "state_h_z_1_2", "hopf"]
    rev = rules[1]
    assert rev.lhs == RULES["colour_change"].rhs and rev.rhs == RULES["colour_change"].lhs
    assert rev.residual == RULES["colour_change"].reversed().residual
    assert cp.is_library(rules[0]) and not cp.is_library(rev)
    for bad, msg in (
        (["fusion", "fusion"], "listed twice"),
        ([{"reverse": "nope"}], "cannot reverse"),
        ([{"name": "x"}], "bad inline rule"),
        ([{**STATE_H_Z_1_2, "name": "fusion"}], "shadows a library rule"),
    ):
        with pytest.raises(cp.InvalidSystem, match=msg):
            cp.resolve_rules(cp.SystemOut(rules=bad, measure=["vertices"], depth=1,
                                          rationale=""))
    with pytest.raises(ValidationError):            # the schema rejects anything else first
        cp.SystemOut(rules=[3], measure=["vertices"], depth=1, rationale="")
    # a library rule given inline by its exact JSON is the library rule
    inline_fusion = cp.SystemOut(rules=[RULES["fusion"].to_json()], measure=["vertices"],
                                 depth=1, rationale="")
    assert cp.is_library(cp.resolve_rules(inline_fusion)[0])
    assert cp.rules_payload(cp.resolve_rules(inline_fusion)) == ["fusion"]


def test_candidate_id_is_stable_under_reordering_and_sensitive_to_the_set():
    a = system_a()
    b = cp.SystemOut(rules=list(reversed(a.rules)), measure=["edges"], depth=5,
                     rationale="other")
    assert cp.candidate_id(a) == cp.candidate_id(b)
    assert len(cp.candidate_id(a)) == 10 and int(cp.candidate_id(a), 16) >= 0
    assert cp.candidate_id(a) != cp.candidate_id(cp.SEED)
    # the reverse shorthand and the explicit reversed JSON are the same rule
    via_short = cp.SystemOut(rules=["fusion", {"reverse": "colour_change"}], measure=["vertices"],
                             depth=1, rationale="")
    via_json = cp.SystemOut(rules=[cp.reversed_rule("colour_change").to_json(), "fusion"],
                            measure=["vertices"], depth=1, rationale="")
    assert cp.candidate_id(via_short) == cp.candidate_id(via_json)
    # the reference text is documentation, not identity
    renamed_ref = cp.SystemOut(rules=["fusion", {**STATE_H_Z_1_2, "reference": "other words"}],
                               measure=["vertices"], depth=1, rationale="")
    same = cp.SystemOut(rules=["fusion", STATE_H_Z_1_2], measure=["vertices"], depth=1,
                        rationale="")
    assert cp.candidate_id(renamed_ref) == cp.candidate_id(same)


def test_register_keeps_first_name_and_disambiguates_conflicts():
    registry: dict = {}
    keys: dict = {}
    names = cp.register(registry, keys, cp.resolve_rules(cp.SEED))
    assert names[:2] == ["fusion", "fusion_x"] and "scalar_z_0" in names
    other = {**STATE_H_Z_1_2, "name": "scalar_z_0"}     # a different rule, same name
    other_rules = cp.resolve_rules(cp.SystemOut(rules=[other], measure=["vertices"], depth=1,
                                                rationale=""))
    names2 = cp.register(registry, keys, other_rules)
    assert len(names2) == 1 and names2[0].startswith("scalar_z_0~") and names2[0] in registry
    assert registry["scalar_z_0"].rhs.vertices == ()            # the seed's rule kept its name
    assert registry[names2[0]] == other_rules[0]
    # registering the same rule again yields the same key
    assert cp.register(registry, keys, other_rules) == names2
    # and the key resolves in a later proposal
    later = cp.SystemOut(rules=["fusion", names2[0]], measure=["vertices"], depth=1,
                         rationale="")
    assert cp.resolve_rules(later, registry)[1] == other_rules[0]


def test_parse_classes():
    assert cp.parse_classes("2,2,4;2,2,6") == [(2, 2, 4), (2, 2, 6)]
    assert cp.parse_classes(" 1,1,1 ") == [(1, 1, 1)]
    for bad in ("", "2,2", "9,2,4", "2,2,99"):
        with pytest.raises(ValueError):
            cp.parse_classes(bad)
    assert cp.class_tag((2, 1, 2)) == "c212" and cp.class_name((2, 1, 2)) == "C(2, 1, 2)"


# ----------------------------------------------------------------------------- payloads


def test_write_payloads_shapes_and_canonical_order(repo):
    cid = cp.candidate_id(system_a())
    paths = cp.write_payloads(repo, cid, system_a(), [(1, 1, 1), (2, 1, 2)])
    assert set(paths) == {"sound", "terminates", "locally_confluent_d2_k2", "complete_c111",
                          "complete_c212"}
    assert all(p.startswith(f"claims/evidence/p6/cand_{cid}/") for p in paths.values())
    sound = json.loads((repo / paths["sound"]).read_text())
    assert sound["fragment"] == "clifford" and sound["star_legs"] == 2
    assert sound["max_instances"] == cp.DEFAULT_MAX_INSTANCES
    names = [r if isinstance(r, str) else r["name"] for r in sound["rules"]]
    lib = [n for n in names if n in RULES]
    assert lib == [n for n in RULES if n in lib]            # library order
    inline = [n for n in names if n not in RULES]
    assert inline == sorted(inline) and names == lib + inline
    assert all(isinstance(r, dict) for r in sound["rules"] if not isinstance(r, str))
    term = json.loads((repo / paths["terminates"]).read_text())
    assert term["measure"] == MEASURE_A and term["rules"] == sound["rules"]
    cps = json.loads((repo / paths["locally_confluent_d2_k2"]).read_text())
    assert cps["depth"] == 2 and cps["star_legs"] == 2 and cps["max_nodes"] == 20000
    comp = json.loads((repo / paths["complete_c212"]).read_text())
    assert (comp["max_wires"], comp["max_vertices"], comp["max_edges"]) == (2, 1, 2)
    assert comp["max_steps"] == cp.DEFAULT_MAX_STEPS and comp["max_diagrams"] == 1_000_000
    # the same candidate again reuses the files a claim may lock
    before = (repo / paths["sound"]).read_bytes()
    cp.write_payloads(repo, cid, system_a(), [(1, 1, 1), (2, 1, 2)], max_instances=7)
    assert (repo / paths["sound"]).read_bytes() == before


# ----------------------------------------------------------------------------- evaluate


def test_unsound_candidate_is_not_serious_and_mints_nothing(repo):
    ev = cp.evaluate(repo, unsound_system(), classes=[(1, 1, 1)])
    assert not ev.serious and not ev.success and ev.claims == []
    assert [s.name for s in ev.steps] == ["sound"]
    step = ev.steps[0]
    assert step.verdict == "FAIL" and step.verifier == "zx_rule_sound"
    assert step.witness["rule"] == "colour_change_no_flip" and step.witness["instance"]
    assert "colour_change_no_flip" in step.detail
    assert claim_files(repo) == {} and check(repo).ok
    # the model's error leaves no evidence files behind: the witness is the record
    assert not (repo / step.evidence).exists()
    assert not (repo / step.evidence).parent.exists()


def test_unorientable_measure_is_fed_back_not_claimed(repo):
    s = cp.SystemOut(rules=list(cp.SEED.rules), measure=["hadamard_edges"], depth=2,
                     rationale="ties on fusion")
    ev = cp.evaluate(repo, s, classes=[(1, 1, 1)])
    assert not ev.serious and ev.claims == []
    assert [s.name for s in ev.steps] == ["sound", "terminates"]
    assert ev.steps[0].verdict == "PASS" and ev.steps[1].verdict == "FAIL"
    w = ev.steps[1].witness
    assert w["rule"] == "fusion" and w["component"] is None and "ties" in w["reason"]
    assert "fusion" in ev.steps[1].detail
    assert claim_files(repo) == {} and check(repo).ok


def test_invalid_rule_name_is_skipped(repo):
    s = cp.SystemOut(rules=["fusion", "not_a_rule"], measure=["vertices"], depth=1,
                     rationale="")
    ev = cp.evaluate(repo, s, classes=[(1, 1, 1)])
    assert ev.cid is None and "not_a_rule" in ev.skipped and ev.steps == []
    assert claim_files(repo) == {}


def test_non_joinable_pair_mints_two_verified_and_one_refuted(repo):
    ev = cp.evaluate(repo, system_a(depth=1), classes=[(1, 1, 1)], now="2026-09-09")
    cid = ev.cid
    assert ev.serious and not ev.success
    assert [s.name for s in ev.steps] == ["sound", "terminates", "locally_confluent_d1_k2"]
    assert [s.verdict for s in ev.steps] == ["PASS", "PASS", "FAIL"]
    # only the payloads of the checks that ran exist
    assert sorted(p.name for p in (repo / f"claims/evidence/p6/cand_{cid}").iterdir()) == [
        "cp_depth1_arity2.json", "rules_sound_k2.json",
        "termination_vertices_x_vertices_edges_hadamard_edges.json",
    ]
    assert ev.claims == [f"P6.cand_{cid}_sound", f"P6.cand_{cid}_terminates",
                         f"P6.cand_{cid}_locally_confluent_d1_k2"]
    claims = claim_files(repo)
    assert set(claims) == set(ev.claims)
    sound = claims[f"P6.cand_{cid}_sound"]
    assert sound["level"] == "VERIFIED_N" and sound["coverage"] == "exhaustive"
    assert sound["n"] == ev.steps[0].n > 1000 and sound["updated"] == "2026-09-09"
    assert sound["problem"] == "P6" and sound["formulation_version"] == "p6-zx-v1"
    assert "up to 2 residual legs" in sound["statement"]
    assert "state_h_z_1_2" in sound["statement"] and "colour_change" in sound["statement"]
    assert sound["evidence"][0]["verifier"] == "zx_rule_sound"
    assert sound["evidence"][0]["verdict"] == "PASS"
    term = claims[f"P6.cand_{cid}_terminates"]
    assert term["level"] == "VERIFIED_N" and term["n"] == 21
    assert "(vertices, x_vertices, edges, hadamard_edges)" in term["statement"]
    refuted = claims[f"P6.cand_{cid}_locally_confluent_d1_k2"]
    assert refuted["level"] == "REFUTED" and refuted["n"] is None
    assert "within depth 1 at residual arity <= 2" in refuted["statement"]
    assert "max_nodes = 20000" in refuted["statement"]
    assert refuted["evidence"][0]["verdict"] == "FAIL"
    assert "Witness:" in refuted["notes"]
    w = ev.steps[2].witness
    assert {w["rule1"], w["rule2"]} == {"colour_change", "fusion_x"}
    assert w["host"]["vertices"] and w["result1"] and w["result2"]
    assert check(repo).ok
    # evaluating the same system again re-runs the verifiers but mints nothing new
    again = cp.evaluate(repo, system_a(depth=1), classes=[(1, 1, 1)], now="2026-09-09")
    assert again.claims == ev.claims
    assert all(s.problem == "already minted" for s in again.steps)
    assert claim_files(repo) == claims and check(repo).ok


def test_seed_on_c212_mints_a_completeness_claim(repo):
    ev = cp.evaluate(repo, cp.SEED, classes=[(2, 1, 2)])
    cid = ev.cid
    assert ev.serious and not ev.success
    assert [(s.name, s.verdict) for s in ev.steps] == [
        ("sound", "PASS"), ("terminates", "PASS"), ("locally_confluent_d4_k2", "PASS"),
        ("complete_c212", "FAIL"),
    ]
    claims = claim_files(repo)
    assert set(claims) == set(ev.claims) == {
        f"P6.cand_{cid}_sound", f"P6.cand_{cid}_terminates",
        f"P6.cand_{cid}_locally_confluent_d4_k2", f"P6.cand_{cid}_complete_c212",
    }
    lc = claims[f"P6.cand_{cid}_locally_confluent_d4_k2"]
    assert lc["level"] == "VERIFIED_N" and lc["n"] == 2388
    assert "2388 critical pairs" in lc["statement"]
    comp = claims[f"P6.cand_{cid}_complete_c212"]
    assert comp["level"] == "REFUTED"
    assert "complete for the class C(2, 1, 2)" in comp["statement"]
    assert "max_steps = 200" in comp["statement"]
    w = ev.steps[3].witness
    assert (w["inputs"], w["outputs"]) == (0, 0)
    assert w["a"]["vertices"] == [[0, "Z", "0"]] and w["b"]["vertices"] == [[0, "X", "0"]]
    assert check(repo).ok


def test_success_on_c111_mints_four_verified_claims(repo):
    ev = cp.evaluate(repo, system_a(), classes=[(1, 1, 1)])
    assert ev.serious and ev.success
    assert [s.verdict for s in ev.steps] == ["PASS"] * 4
    claims = claim_files(repo)
    assert len(claims) == 4 and all(c["level"] == "VERIFIED_N" for c in claims.values())
    comp = claims[f"P6.cand_{ev.cid}_complete_c111"]
    assert comp["n"] == 57 and "57 diagrams" in comp["statement"]
    assert "applied first-applicable in the listed order" in comp["statement"]
    assert check(repo).ok
    # round trip through JSON, as the campaign log stores it
    back = cp.Evaluation.from_json(json.loads(json.dumps(ev.to_json())))
    assert back == ev


# ----------------------------------------------------------------------------- the prompt


def test_build_prompt_is_the_playbook(monkeypatch):
    seed_eval = cp.Evaluation(
        cid=cp.candidate_id(cp.SEED), system=cp.SEED.model_dump(), rules=["fusion"],
        steps=[cp.Step("sound", "zx_rule_sound", "PASS", "all good", "e", n=1260),
               cp.Step("terminates", "zx_termination", "PASS", "decreases", "e", n=18),
               cp.Step("locally_confluent_d4_k2", "zx_critical_pairs", "PASS", "2388 pairs",
                       "e", n=2388),
               cp.Step("complete_c224", "zx_completeness", "FAIL", "two normal forms", "e",
                       witness={"a": {"vertices": [[0, "Z", "0"]]}, "b": {"vertices": []}})],
        serious=True, round=0)
    failed = cp.Evaluation(
        cid="deadbeef00", system=unsound_system().model_dump(),
        rules=["fusion", "colour_change_no_flip"],
        steps=[cp.Step("sound", "zx_rule_sound", "FAIL", "rule colour_change_no_flip is not an "
                       "equation", "e", witness={"rule": "colour_change_no_flip",
                                                 "instance": {"vertices": [[0, "X", "1/2"]]}})],
        round=1, slot=0)
    invalid = cp.Evaluation(cid=None, system=None, skipped="invalid schema: depth", round=1,
                            slot=1)
    monkeypatch.setattr(termination, "COMPONENTS", (*termination.COMPONENTS, "phase_vertices"))
    text = cp.build_prompt([seed_eval, failed, invalid], cp.SEED, [(2, 2, 4), (2, 2, 6)],
                           "n0nce", round_no=2)
    assert text.startswith("[nonce n0nce]") and text.rstrip().endswith("nonce: n0nce")
    assert "Problem 6 (ii)(a)" in text and "C(2, 2, 4), C(2, 2, 6)" in text
    assert "deleted spider" in text and "residual" in text          # the matching semantics
    for name in ("fusion", "bialgebra", "hopf_h", "loop_x_h"):        # the library, as JSON
        assert f"\n{name}: {{" in text
    assert json.dumps(RULES["euler"].to_json(), separators=(",", ":"), sort_keys=True) in text
    assert '{"reverse": "<name>"}' in text
    assert "- phase_vertices:" in text and "- hadamard_edges:" in text   # components, live
    for v in ("zx_rule_sound", "zx_termination", "zx_critical_pairs", "zx_completeness"):
        assert v in text
    assert "max_nodes = 20000" in text and "max_instances = 40000" in text
    assert "## The seed" in text and "scalar_z_0: {" in text
    assert "measured outcome" in text and "complete_c224: FAIL" in text
    assert "### round 1 slot 0 -- cand_deadbeef00" in text
    assert "REJECTED (not serious) at sound" in text
    assert 'witness: {"instance":{"vertices":[[0,"X","1/2"]]},"rule":"colour_change_no_flip"}' \
        in text
    assert "### round 1 slot 1" in text and "not evaluated: invalid schema: depth" in text
    assert "## Your task" in text and "SystemOut" in text
    assert "round 2" in text
    assert len(text.encode()) < cp.PROMPT_BUDGET
    assert "transcript" not in text.lower()


def test_prompt_stays_under_budget_with_a_long_history():
    big_witness = {"host": {"vertices": [[i, "Z", "1/2"] for i in range(12)],
                            "edges": [[i, i + 1, True] for i in range(11)]},
                   "result1": {"vertices": [[i, "Z", "0"] for i in range(12)]},
                   "result2": {"vertices": [[i, "X", "0"] for i in range(12)]},
                   "rule1": "a", "rule2": "b", "reason": "no common diagram"}
    history = []
    for r in range(1, 17):
        for slot in range(2):
            rule = {**STATE_H_Z_1_2, "name": f"rule_{r}_{slot}"}
            sysd = cp.SystemOut(rules=[*cp.SEED.rules, rule], measure=["vertices"], depth=3,
                                rationale="x" * 400).model_dump()
            history.append(cp.Evaluation(
                cid=f"{r:04x}{slot:06x}", system=sysd, rules=[*cp.R0CORE, f"rule_{r}_{slot}"],
                steps=[cp.Step("sound", "zx_rule_sound", "PASS", "ok", "e", n=1),
                       cp.Step("terminates", "zx_termination", "PASS", "ok", "e", n=1),
                       cp.Step("locally_confluent_d3_k2", "zx_critical_pairs", "FAIL",
                               "a critical pair of a and b is not joinable", "e",
                               witness=big_witness, claim="P6.cand_x", level="REFUTED")],
                serious=True, round=r, slot=slot))
    text = cp.build_prompt(history, cp.SEED, [(2, 2, 4)], "n")
    assert len(text.encode()) <= cp.PROMPT_BUDGET
    assert "### round 16 slot 1" in text and "### round 1 slot 0" in text
    assert "rule_16_1: {" in text                    # recent inline rules stay usable by name

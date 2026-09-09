"""`empiricist.packs.zx` P6 groundwork (M25a): rule soundness, bounded completeness
against the semantic oracle, and critical pairs per residual arity."""
from __future__ import annotations

import json
from fractions import Fraction

import numpy as np
import pytest

from empiricist.ledger.models import Verdict
from empiricist.packs.zx import MANIFEST
from empiricist.packs.zx import diagram as dg
from empiricist.packs.zx import rewrite as rw
from empiricist.packs.zx import semantics as sem
from empiricist.packs.zx import soundness as sd
from empiricist.packs.zx.diagram import Diagram
from empiricist.packs.zx.rules import (
    CLIFFORD_RULES,
    PHASES_CLIFFORD,
    PHASES_CLIFFORD_T,
    RULES,
    Rule,
)

F = Fraction


def payload(obj) -> bytes:
    return json.dumps(obj).encode()


def subset(*names: str) -> dict[str, Rule]:
    return {n: RULES[n] for n in names}


def pattern(vertices, edges) -> Diagram:
    outs = sorted(v for v, (k, _) in vertices.items() if k == "B")
    return Diagram.build(vertices, edges, inputs=(), outputs=outs)


def colour_change_without_flip() -> Rule:
    """Colour change that forgets to toggle the residual legs: sound on a bare spider,
    unsound as soon as it has a leg."""
    return Rule("colour_change_no_flip", pattern({0: ("X", "a")}, []), pattern({0: ("Z", "a")}, []),
                residual=((0, ((0, False),)),), reference="test: (H) without the leg flip")


def pi_commute_wrong_sign() -> Rule:
    base = RULES["pi_commute"]
    rhs = base.rhs.with_phase(5, "a")
    return Rule("pi_commute_wrong_sign", base.lhs, rhs, (), "test: (K) with the sign dropped")


def identity_z_h_without_hadamard() -> Rule:
    base = RULES["identity_z_h"]
    rhs = pattern({0: ("B", 0), 2: ("B", 0)}, [(0, 2, False)])
    return Rule("identity_z_h_no_h", base.lhs, rhs, (), "test: (S2) with the H flag dropped")


# ----------------------------------------------------------------------------- Task 1: soundness


def test_instances_of_grounds_variables_and_enumerates_leg_multisets_per_star():
    fusion = RULES["fusion"]
    inst = list(sd.instances_of(fusion, PHASES_CLIFFORD, 1))
    # 4^2 bindings x (no leg, one plain, one Hadamard)^2 stars
    assert len(inst) == 16 * 9 == sd.instance_count(fusion, PHASES_CLIFFORD, 1)
    bindings, legs, host = inst[0]
    assert set(bindings) == {"a", "b"} and set(legs) == set(fusion.stars)
    assert all(h.is_well_formed() and h.is_ground() for _, _, h in inst)
    # the class is "all combinations": fusion's symmetry makes some instances isomorphic
    distinct = {h.relabel_canonical().canonical_json() for _, _, h in inst}
    assert 78 <= len(distinct) < len(inst)
    # legs are multisets: (plain, H) and (H, plain) are one configuration
    two = list(sd.instances_of(RULES["colour_change"], (F(0),), 2))
    assert [legs[0] for _, legs, _ in two] == [(), (False,), (True,), (False, False),
                                               (False, True), (True, True)]
    assert sd.instance_count(RULES["bialgebra"], PHASES_CLIFFORD_T, 2) == 1   # no vars, no stars
    assert sd.instance_count(RULES["commute_controls"], PHASES_CLIFFORD_T, 0) == 8 ** 3
    # the identity matching applies the rule to its own instance
    for b, _, h in inst[:5]:
        out = rw.apply(h, fusion, sd.identity_matching(fusion, b))
        assert sem.equal_up_to_scalar(sem.matrix(h), sem.matrix(out))


def test_check_passes_sound_rules_and_names_the_first_unsound_instance():
    rep = sd.check(subset("fusion", "colour_change", "hopf"), phases=PHASES_CLIFFORD, star_legs=1)
    assert rep.ok and rep.failure is None
    assert rep.instances == 144 + 12 + 144 and rep.skipped == 0
    assert rep.per_rule["colour_change"] == {"instances": 12, "skipped": 0}
    assert rep.rules == ["colour_change", "fusion", "hopf"]
    bad = colour_change_without_flip()
    rep2 = sd.check({"fusion": RULES["fusion"], bad.name: bad}, phases=PHASES_CLIFFORD, star_legs=1)
    assert not rep2.ok
    f = rep2.failure
    assert f.rule == bad.name and f.legs == {0: (False,)} and f.bindings == {"a": F(0)}
    assert f.entry == (1, 0)                        # X(0) state [1, 0] against Z(0) state [1, 1]
    assert sem.boundary_wires(f.host) == 1 and f.reason
    # the failure stops the check; fusion (sorted after colour_change_no_flip) is not judged
    assert "fusion" not in rep2.per_rule and rep2.instances == 2   # a=0: no leg (equal), one leg
    # with no legs the flipless colour change is an equation
    assert sd.check({bad.name: bad}, phases=PHASES_CLIFFORD, star_legs=0).ok


def test_check_judges_the_two_other_near_misses_and_every_library_rule():
    for rule in (pi_commute_wrong_sign(), identity_z_h_without_hadamard()):
        rep = sd.check({rule.name: rule}, phases=PHASES_CLIFFORD, star_legs=1)
        assert not rep.ok and rep.failure.rule == rule.name
    wrong = pi_commute_wrong_sign()
    rep = sd.check({wrong.name: wrong}, phases=(F(0), F(1)), star_legs=0)
    assert rep.ok                                   # a in {0, pi}: Z(a) commutes with X
    rep = sd.check(dict(RULES), phases=PHASES_CLIFFORD, star_legs=0, max_instances=10 ** 5)
    assert rep.ok and set(rep.per_rule) == set(RULES) and rep.skipped == 0


def test_soundness_budgets_and_unjudgeable_rules_are_errors():
    with pytest.raises(sd.SoundnessError, match="budget"):
        sd.check(subset("fusion"), phases=PHASES_CLIFFORD_T, star_legs=2, max_instances=100)
    # a rule on seven interface wires is over the semantic budget on every instance
    ids = list(range(7))
    lhs = pattern({**{i: ("B", 0) for i in ids}, 7: ("Z", 0)}, [(i, 7, False) for i in ids])
    rhs = pattern({**{i: ("B", 0) for i in ids}, 8: ("Z", 0)}, [(i, 8, False) for i in ids])
    wide = Rule("wide", lhs, rhs, (), "test")
    with pytest.raises(sd.SoundnessError, match="unjudgeable"):
        sd.check({"wide": wide}, phases=PHASES_CLIFFORD, star_legs=0)
    # skipped instances are counted and the judged ones decide: a star on five interface
    # wires is judged with no leg and with one, skipped with two (seven wires)
    ids = list(range(5))
    five = Rule("five", pattern({**{i: ("B", 0) for i in ids}, 5: ("Z", "a")},
                                [(i, 5, False) for i in ids]),
                pattern({**{i: ("B", 0) for i in ids}, 6: ("Z", "a")},
                        [(i, 6, False) for i in ids]),
                ((5, ((6, False),)),), "test")
    rep = sd.check({"five": five}, phases=(F(0),), star_legs=2)
    assert rep.ok and rep.instances == 3 and rep.skipped == 3
    assert rep.per_rule["five"] == {"instances": 3, "skipped": 3}
    # a failing rule is a verdict even when another rule is unjudgeable
    bad = colour_change_without_flip()
    rep = sd.check({"wide": wide, bad.name: bad}, phases=PHASES_CLIFFORD, star_legs=1)
    assert not rep.ok and rep.failure.rule == bad.name


def test_first_difference_reports_the_entry_after_scalar_alignment():
    a = np.array([[1, 2], [3, 4]], dtype=complex)
    assert sd.first_difference(a, 2j * a) is None
    entry, va, vb = sd.first_difference(a, np.array([[1, 2], [3, 5]], dtype=complex))
    assert entry == (1, 1) and abs(va - 4) < 1e-9 and abs(vb - 5) < 1e-9
    entry, va, vb = sd.first_difference(a, 3 * np.array([[1, 2], [3, 5]], dtype=complex))
    assert entry == (1, 1) and abs(va - 4) < 1e-9 and abs(vb - 5) < 1e-9   # aligned on (0, 0)
    entry, va, vb = sd.first_difference(np.zeros((2, 2)), a)
    assert entry == (0, 0) and va == 0 and vb == 1


def test_zx_rule_sound_verifier_verdicts_and_details(tmp_path):
    v = MANIFEST.verifiers["zx_rule_sound"](tmp_path)
    r = v.verify_bytes(payload({"rules": ["fusion", "identity_z"], "fragment": "clifford"}))
    assert r.verdict is Verdict.PASS, r.details
    assert r.details["instances"] == 145 and r.details["skipped"] == 0
    assert r.details["star_legs"] == 1 and r.details["fragment"] == "clifford"
    assert r.details["per_rule"]["fusion"] == {"instances": 144, "skipped": 0}
    assert r.details["rules"] == ["fusion", "identity_z"]
    bad = colour_change_without_flip().to_json()
    r = v.verify_bytes(payload({"rules": ["fusion", bad], "star_legs": 1}))
    assert r.verdict is Verdict.FAIL
    assert r.details["rule"] == "colour_change_no_flip" and r.details["legs"] == {"0": [False]}
    assert r.details["bindings"] == {"a": "0"} and r.details["entry"] == [1, 0]
    assert "colour_change_no_flip" in r.details["detail"] and r.details["instances"] >= 1
    assert Diagram.from_json(r.details["instance"]).is_well_formed()
    assert Diagram.from_json(r.details["result"]).is_well_formed()
    r = v.verify_bytes(payload({"rules": ["fusion", bad], "star_legs": 0}))
    assert r.verdict is Verdict.PASS
    # defaults: clifford+t, star_legs 1, max_instances 4096
    r = v.verify_bytes(payload({"rules": ["colour_change"]}))
    assert r.verdict is Verdict.PASS and r.details["instances"] == 24
    # errors: budget, unjudgeable, bad fragment, bad star_legs, unknown rule
    r = v.verify_bytes(payload({"rules": ["fusion"], "star_legs": 2, "max_instances": 10}))
    assert r.verdict is Verdict.ERROR and "budget" in r.details["error"]
    ids = list(range(7))
    lhs = pattern({**{i: ("B", 0) for i in ids}, 7: ("Z", 0)}, [(i, 7, False) for i in ids])
    wide = Rule("wide", lhs, lhs, (), "test").to_json()
    r = v.verify_bytes(payload({"rules": [wide]}))
    assert r.verdict is Verdict.ERROR and "unjudgeable" in r.details["error"]
    for bad_payload in ({"rules": ["fusion"], "fragment": "stabilizer"},
                        {"rules": ["fusion"], "star_legs": 3},
                        {"rules": ["nope"]}, {"rules": []}, {"rules": ["fusion", "fusion"]}):
        r = v.verify_bytes(payload(bad_payload))
        assert r.verdict is Verdict.ERROR and r.details["error"], bad_payload


def test_zx_rule_sound_golden_payloads_are_the_stated_classes(tmp_path):
    v = MANIFEST.verifiers["zx_rule_sound"](tmp_path)
    cases = {c.label: c for c in v.golden_suite()}
    clifford = json.loads(cases["zx_rule_sound__clifford_rules_star_legs_1"].payload)
    assert set(clifford["rules"]) == set(CLIFFORD_RULES)
    assert clifford["fragment"] == "clifford" and clifford["star_legs"] == 1
    r = v.verify_bytes(cases["zx_rule_sound__clifford_rules_star_legs_1"].payload)
    assert r.verdict is Verdict.PASS and r.details["instances"] > 600 and r.details["skipped"] == 0
    t = json.loads(cases["zx_rule_sound__clifford_t_rules_star_legs_0"].payload)
    assert set(t["rules"]) == {"supp", "supp_x", "e_scalar", "commute_controls", "bw"}
    assert t["star_legs"] == 0
    fails = [label for label, c in cases.items() if c.expected is Verdict.FAIL]
    assert len(fails) == 3
    for label in fails:
        r = v.verify_bytes(cases[label].payload)
        assert r.verdict is Verdict.FAIL and r.details["rule"] in label, (label, r.details)


# ----------------------------------------------------------------------------- manifest

def test_manifest_hashes_cover_the_new_engines(tmp_path):
    sound = MANIFEST.verifiers["zx_rule_sound"](tmp_path)
    assert sound.name == "zx_rule_sound" and sound.version == "1"
    assert len(sound.binary_hash) == 64
    assert dg.Diagram is Diagram   # the diagram module is in every trust boundary

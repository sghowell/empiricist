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
    complete = MANIFEST.verifiers["zx_completeness"](tmp_path)
    assert sound.name == "zx_rule_sound" and complete.name == "zx_completeness"
    assert sound.version == complete.version == "1"
    assert len(sound.binary_hash) == 64 and sound.binary_hash != complete.binary_hash
    assert dg.Diagram is Diagram   # the diagram module is in every trust boundary


# ----------------------------------------------------------------------------- Task 2: completeness

from empiricist.packs.zx import completeness as cm  # noqa: E402
from empiricist.packs.zx.rules import swap_colours  # noqa: E402

LOOP_RULES = ("loop_z", "loop_x", "loop_z_h", "loop_x_h")
WIRE_RULES = ("identity_z", "identity_x", "identity_z_h", "identity_x_h", "identity_z_hh",
              "identity_x_hh") + LOOP_RULES


def scalar_rule(kind: str, phase: Fraction) -> Rule:
    """A non-zero 0-leg spider is the empty diagram (up to scalar)."""
    tag = str(phase).replace("/", "_")
    return Rule(f"scalar_{kind.lower()}_{tag}", pattern({0: (kind, phase)}, []),
                pattern({}, []), (), "test: a non-zero scalar is 1 up to scalar")


def scalar_rules() -> dict[str, Rule]:
    out = {}
    for kind in ("Z", "X"):
        for phase in (F(0), F(1, 2), F(3, 2)):
            r = scalar_rule(kind, phase)
            out[r.name] = r
    return out


def test_enumerate_diagrams_counts_small_classes_exactly_and_canonically():
    wires_only = cm.enumerate_diagrams(PHASES_CLIFFORD, 2, 0, 2, 1000)
    assert len(wires_only) == 7            # empty; cap, wire, cup, each plain or Hadamard
    scalars = cm.enumerate_diagrams(PHASES_CLIFFORD, 0, 1, 2, 1000)
    assert len(scalars) == 49              # empty; 8 spiders x (no loop, 1 loop x2, 2 loops x3)
    one_wire = cm.enumerate_diagrams(PHASES_CLIFFORD, 1, 1, 1, 1000)
    assert len(one_wire) == 57             # 25 scalars (<= 1 loop) + 8 x 2 flags x {input, output}
    for cls in (wires_only, scalars, one_wire):
        assert all(d.is_well_formed() and d.is_ground() for d in cls)
        assert all(d == d.relabel_canonical() for d in cls)
        assert len({d.canonical_json() for d in cls}) == len(cls)
    ins_outs = {(len(d.inputs), len(d.outputs)) for d in one_wire}
    assert ins_outs == {(0, 0), (1, 0), (0, 1)}
    assert cm.enumerate_diagrams(PHASES_CLIFFORD, 0, 0, 0, 1) == [Diagram((), ())]
    with pytest.raises(cm.CompletenessError, match="max_diagrams"):
        cm.enumerate_diagrams(PHASES_CLIFFORD, 2, 1, 2, 10)
    # a bigger class: every enumerated diagram respects the bounds
    cls = cm.enumerate_diagrams(PHASES_CLIFFORD, 2, 2, 3, 100000)
    assert all(len(d.inputs) + len(d.outputs) <= 2 and len(d.interior) <= 2
               and len(d.edges) <= 3 for d in cls)
    assert len(cls) > len(one_wire)


def test_normal_form_applies_the_first_rule_in_payload_order_until_none_applies():
    x_wire = Diagram.build({0: ("B", 0), 1: ("X", 0), 2: ("B", 0)},
                           [(0, 1, False), (1, 2, False)], inputs=[0], outputs=[2])
    wire = Diagram.build({0: ("B", 0), 1: ("B", 0)}, [(0, 1, False)], inputs=[0], outputs=[1])
    nf, steps = cm.reduce(x_wire, subset("colour_change", "identity_z_hh"), 10)
    assert nf == wire.relabel_canonical() and steps == 2
    nf2, steps2 = cm.reduce(x_wire, subset("identity_x", "colour_change"), 10)
    assert nf2 == nf and steps2 == 1
    assert cm.normal_form(x_wire, subset("identity_x"), 10) == nf
    assert cm.normal_form(x_wire, subset("identity_z"), 10) == x_wire.relabel_canonical()
    with pytest.raises(cm.CompletenessError, match="terminate"):
        cm.reduce(x_wire, subset("colour_change", "identity_z_hh"), 1)
    ping_pong = {"colour_change": RULES["colour_change"],
                 "colour_change_x": swap_colours(RULES["colour_change"], "colour_change_x")}
    with pytest.raises(cm.CompletenessError, match="terminate"):
        cm.normal_form(x_wire, ping_pong, 50)


def test_semantic_key_groups_matrices_up_to_scalar_and_zero_together():
    a = np.array([[1, 1j], [0.5, -0.25]], dtype=complex)
    assert cm.semantic_key(a) == cm.semantic_key((0.3 - 2j) * a)
    assert cm.semantic_key(a) != cm.semantic_key(a.conj())
    assert cm.semantic_key(np.zeros((2, 2))) == cm.semantic_key(1e-12 * a) == ("zero",)
    # noise does not move the pivot between tied maxima
    b = np.array([[1, 1]], dtype=complex)
    assert cm.semantic_key(b) == cm.semantic_key(np.array([[1, 1 + 1e-13]], dtype=complex))


def test_check_finds_a_witness_pair_and_passes_once_the_class_is_complete():
    rep = cm.check(subset(*LOOP_RULES), phases=PHASES_CLIFFORD, max_wires=0, max_vertices=1,
                   max_edges=1, max_steps=20, max_diagrams=1000)
    assert not rep.ok and rep.diagrams == 25 and rep.classes == 2       # zero and non-zero
    w = rep.failure
    assert sem.equal_up_to_scalar(sem.matrix(w.a), sem.matrix(w.b))
    assert w.normal_form_a != w.normal_form_b
    assert w.normal_form_a == cm.normal_form(w.a, subset(*LOOP_RULES), 20)
    # the check stops at the witness: the empty diagram and Z(0), both normal forms
    assert rep.reduced == 2 and rep.normal_forms == 2 and rep.steps_max == 0
    assert rep.skipped == 0 and len(w.a.vertices) == 0 and len(w.b.vertices) == 1
    complete = subset(*LOOP_RULES, "colour_change") | scalar_rules()
    rep2 = cm.check(complete, phases=PHASES_CLIFFORD, max_wires=0, max_vertices=1, max_edges=1,
                    max_steps=20, max_diagrams=1000)
    assert rep2.ok and rep2.classes == 2 and rep2.normal_forms == 2 and rep2.diagrams == 25
    assert rep2.steps_max == 3                  # X(a)+H loop -> X(a+1) -> Z(a+1) -> empty
    # without colour change the X scalars are stranded next to the Z ones
    rep3 = cm.check(subset(*LOOP_RULES) | scalar_rules(), phases=PHASES_CLIFFORD, max_wires=0,
                    max_vertices=1, max_edges=1, max_steps=20, max_diagrams=1000)
    assert not rep3.ok
    # budgets are errors
    with pytest.raises(cm.CompletenessError):
        cm.check(subset(*LOOP_RULES), phases=PHASES_CLIFFORD, max_wires=0, max_vertices=1,
                 max_edges=1, max_steps=20, max_diagrams=3)


def test_zx_completeness_verifier_verdicts_and_details(tmp_path):
    v = MANIFEST.verifiers["zx_completeness"](tmp_path)
    r = v.verify_bytes(payload({"rules": ["identity_z"], "max_vertices": 0}))
    assert r.verdict is Verdict.PASS, r.details
    assert r.details["diagrams"] == r.details["classes"] == r.details["normal_forms"] == 7
    assert r.details["steps_max"] == 0 and r.details["skipped"] == 0
    assert r.details["max_wires"] == 2 and r.details["max_edges"] == 6
    assert r.details["fragment"] == "clifford" and r.details["max_steps"] == 200
    r = v.verify_bytes(payload({"rules": list(LOOP_RULES), "max_wires": 0, "max_vertices": 1,
                                "max_edges": 1}))
    assert r.verdict is Verdict.FAIL
    for key in ("a", "b", "normal_form_a", "normal_form_b"):
        assert Diagram.from_json(r.details[key]).is_well_formed()
    assert r.details["inputs"] == 0 and r.details["outputs"] == 0
    assert r.details["diagrams"] == 25 and r.details["classes"] == 2
    assert "different normal forms" in r.details["detail"]
    inline = [r_.to_json() for r_ in scalar_rules().values()]
    r = v.verify_bytes(payload({"rules": list(LOOP_RULES) + ["colour_change"] + inline,
                                "max_wires": 0, "max_vertices": 1, "max_edges": 1}))
    assert r.verdict is Verdict.PASS and r.details["normal_forms"] == 2
    # errors: the fragment, the budgets, the bounds
    r = v.verify_bytes(payload({"rules": ["identity_z"], "fragment": "clifford+t"}))
    assert r.verdict is Verdict.ERROR and "fragment" in r.details["error"]
    r = v.verify_bytes(payload({"rules": ["identity_z"], "max_diagrams": 2}))
    assert r.verdict is Verdict.ERROR and "max_diagrams" in r.details["error"]
    ping_pong = swap_colours(RULES["colour_change"], "colour_change_x").to_json()
    r = v.verify_bytes(payload({"rules": ["colour_change", ping_pong], "max_wires": 0,
                                "max_vertices": 1, "max_edges": 0, "max_steps": 5}))
    assert r.verdict is Verdict.ERROR and "terminate" in r.details["error"]
    for bad in ({"rules": ["identity_z"], "max_wires": 4},
                {"rules": ["identity_z"], "max_vertices": 5},
                {"rules": ["identity_z"], "max_edges": -1},
                {"rules": ["identity_z"], "max_steps": 0},
                {"rules": ["nope"]}, {"rules": []}):
        r = v.verify_bytes(payload(bad))
        assert r.verdict is Verdict.ERROR and r.details["error"], bad


def test_zx_completeness_goldens_are_the_stated_classes(tmp_path):
    v = MANIFEST.verifiers["zx_completeness"](tmp_path)
    cases = {c.label: c for c in v.golden_suite()}
    verdicts = {label: v.verify_bytes(c.payload) for label, c in cases.items()}
    assert {c.expected for c in cases.values()} == {Verdict.PASS, Verdict.FAIL}
    for label, r in verdicts.items():
        assert r.verdict is cases[label].expected, (label, r.details)
    wires = json.loads(cases["zx_completeness__wires_only"].payload)
    assert wires["max_vertices"] == 0
    assert verdicts["zx_completeness__wires_only"].details["diagrams"] == 7
    for label, c in cases.items():
        if c.expected is Verdict.FAIL:
            d = verdicts[label].details
            assert sem.equal_up_to_scalar(sem.matrix(Diagram.from_json(d["a"])),
                                          sem.matrix(Diagram.from_json(d["b"])))

"""Phase-aware termination components with conservative symbolic evaluation (M25b Task 1)."""
from __future__ import annotations

from empiricist.packs.zx import termination as term
from empiricist.packs.zx.diagram import Diagram
from empiricist.packs.zx.rules import RULES, Rule


def _pat(vertices, edges):
    outs = sorted(v for v, (k, _) in vertices.items() if k == "B")
    return Diagram.build(vertices, edges, inputs=(), outputs=outs)


def test_phase_components_are_known_and_counted_on_ground_diagrams():
    assert "phase_vertices" in term.COMPONENTS and "pi_vertices" in term.COMPONENTS
    d = _pat({0: ("Z", "1/2"), 1: ("X", 1), 2: ("Z", 0), 3: ("B", 0)},
             [(0, 1, False), (1, 3, True)])
    assert term.measure(d, ["phase_vertices", "pi_vertices", "vertices"]) == (2, 1, 3)
    lo, hi = term.measure_bounds(d, ["phase_vertices"])
    assert lo == hi == (2,)


def test_symbolic_phase_contributes_an_interval():
    d = _pat({0: ("Z", "a"), 1: ("B", 0)}, [(0, 1, False)])
    assert term.measure_bounds(d, ["phase_vertices", "vertices"]) == ((0, 1), (1, 1))


def test_a_ground_rule_can_decrease_phase_vertices():
    # Z(pi/2) state with a Hadamard leg -> Z(3pi/2) state with a plain leg: phase_vertices ties,
    # hadamard_edges strictly decreases; the reverse orientation increases it.
    lhs = _pat({0: ("Z", "1/2"), 1: ("B", 0)}, [(0, 1, True)])
    rhs = _pat({0: ("Z", "3/2"), 1: ("B", 0)}, [(0, 1, False)])
    r = Rule("state_h", lhs, rhs)
    dec = term.check_rule(r, ["phase_vertices", "hadamard_edges"])
    assert dec.decreases and dec.component == "hadamard_edges"
    # a rule that removes a phase-pi spider decreases pi_vertices
    lhs2 = _pat({0: ("Z", 1), 1: ("B", 0), 2: ("B", 0)}, [(0, 1, False), (0, 2, False)])
    rhs2 = _pat({1: ("B", 0), 2: ("B", 0)}, [(1, 2, False)])
    dec2 = term.check_rule(Rule("drop_pi", lhs2, rhs2), ["pi_vertices"])
    assert dec2.decreases and dec2.component == "pi_vertices"


def test_symbolic_rules_never_show_a_phase_decrease():
    # fusion Z(a)-Z(b) -> Z(a+b): structurally 2 -> 1 spiders, but phase_vertices is unknown
    # on every symbolic side (lo(LHS) = 0, hi(RHS) = 1), so the component cannot decrease
    # and must not be claimed to weakly decrease either.
    dec = term.check_rule(RULES["fusion"], ["phase_vertices", "vertices"])
    assert not dec.decreases and dec.component == "phase_vertices"
    assert "symbolic" in dec.detail or "increase" in dec.detail
    # with vertices first the structural decrease is found and the phase component never matters
    dec_v = term.check_rule(RULES["fusion"], ["vertices", "phase_vertices"])
    assert dec_v.decreases and dec_v.component == "vertices"


def test_existing_structural_checks_are_unchanged():
    rules = {n: RULES[n] for n in ("fusion", "identity_z", "loop_z")}
    rep = term.check(rules, ["vertices", "edges"])
    assert rep.ok

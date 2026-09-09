"""`empiricist.packs.zx`: ZX diagrams, semantics, rules, rewriting, derivations,
critical pairs, termination certificates and the four pack verifiers (M24c)."""
from __future__ import annotations

import json
from fractions import Fraction

import numpy as np
import pytest

from empiricist.packs.zx import diagram as dg
from empiricist.packs.zx import semantics as sem
from empiricist.packs.zx.diagram import Diagram, PhaseExpr

F = Fraction

# ----------------------------------------------------------------------------- helpers


def wire(*, hadamard: bool = False) -> Diagram:
    """One input wired straight to one output."""
    return Diagram.build({0: ("B", 0), 1: ("B", 0)}, [(0, 1, hadamard)], inputs=[0], outputs=[1])


def spider_1_1(kind: str, phase) -> Diagram:
    return Diagram.build(
        {0: ("B", 0), 1: (kind, phase), 2: ("B", 0)},
        [(0, 1, False), (1, 2, False)], inputs=[0], outputs=[2],
    )


def bell() -> Diagram:
    """Z(0) with two outputs and no inputs: |00> + |11>."""
    return Diagram.build(
        {0: ("Z", 0), 1: ("B", 0), 2: ("B", 0)}, [(0, 1, False), (0, 2, False)],
        inputs=[], outputs=[1, 2],
    )


def cnot() -> Diagram:
    """Control Z(0) on wire 0, target X(0) on wire 1, joined by a plain edge."""
    return Diagram.build(
        {0: ("B", 0), 1: ("B", 0), 2: ("Z", 0), 3: ("X", 0), 4: ("B", 0), 5: ("B", 0)},
        [(0, 2, False), (1, 3, False), (2, 3, False), (2, 4, False), (3, 5, False)],
        inputs=[0, 1], outputs=[4, 5],
    )


H = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
CNOT = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=complex)


# ----------------------------------------------------------------------------- Task 1: diagrams


def test_build_normalises_phases_edges_and_ordering():
    d = Diagram.build({2: ("Z", F(9, 4)), 0: ("B", 0), 1: ("X", "-1/4")},
                      [(2, 0, False), (2, 1, True), (1, 2, True)], inputs=[0], outputs=[])
    assert d.vertices == ((0, "B", F(0)), (1, "X", F(7, 4)), (2, "Z", F(1, 4)))
    assert d.edges == ((0, 2, False), (1, 2, True), (1, 2, True))   # sorted, u <= v, multiset
    assert d.kind(1) == "X" and d.phase(2) == F(1, 4)
    assert d.degree(2) == 3 and d.degree(1) == 2 and sorted(d.neighbours(2)) == [0, 1, 1]
    assert d.interior == (1, 2) and d.boundary == (0,)
    assert d.is_ground()


def test_build_rejects_bad_kinds_ids_and_dangling_edges():
    with pytest.raises(ValueError):
        Diagram.build({0: ("Q", 0)}, [])
    with pytest.raises(ValueError):
        Diagram.build({0: ("Z", 0)}, [(0, 1, False)])
    with pytest.raises(ValueError):
        Diagram.build({"a": ("Z", 0)}, [])
    with pytest.raises(ValueError):
        Diagram.build({0: ("Z", "1/3+")}, [])


def test_well_formedness_problems_are_named():
    ok = spider_1_1("Z", F(1, 4))
    assert ok.is_well_formed() and ok.well_formedness_problems() == []
    # a boundary vertex of degree 2, an output that is not a boundary vertex, a phase
    # outside the pi/4 fragment, and a boundary vertex listed nowhere
    bad = Diagram.build({0: ("B", 0), 1: ("Z", F(1, 3)), 2: ("B", 0), 3: ("B", 0)},
                        [(0, 1, False), (0, 2, False), (1, 3, False)], inputs=[0], outputs=[1])
    problems = bad.well_formedness_problems()
    assert any("degree" in p for p in problems)
    assert any("output" in p for p in problems)
    assert any("pi/4" in p for p in problems)
    assert any("boundary vertex 2" in p or "boundary vertex 3" in p for p in problems)
    assert not bad.is_well_formed()


def test_json_round_trip_is_canonical_and_reduced():
    d = Diagram.build({5: ("Z", F(2, 4)), 3: ("B", 0), 7: ("X", F(7, 4))},
                      [(5, 3, False), (7, 5, True)], inputs=[3], outputs=[])
    obj = d.to_json()
    assert obj == {
        "vertices": [[3, "B", "0"], [5, "Z", "1/2"], [7, "X", "7/4"]],
        "edges": [[3, 5, False], [5, 7, True]],
        "inputs": [3], "outputs": [],
    }
    assert Diagram.from_json(obj) == d
    assert Diagram.from_json(json.loads(d.canonical_json())) == d
    # canonical text is sorted, compact, deterministic
    assert d.canonical_json() == json.dumps(obj, sort_keys=True, separators=(",", ":"))
    with pytest.raises(ValueError):
        Diagram.from_json({"vertices": [[0, "Z", "0"]], "edges": [[0, 9, False]]})
    with pytest.raises(ValueError):
        Diagram.from_json("nope")


def test_phase_expressions_parse_print_and_substitute():
    e = PhaseExpr.parse("a+b-1/4")
    assert str(e) == "7/4+a+b"                     # constant first, then variables sorted
    assert e.variables() == frozenset({"a", "b"})
    assert e.substitute({"a": F(1, 4), "b": F(1, 2)}) == F(1, 2)   # 7/4+1/4+1/2 = 5/2 = 1/2 mod 2
    assert PhaseExpr.parse("-a").substitute({"a": F(1, 4)}) == F(7, 4)
    assert PhaseExpr.parse("2a+1").substitute({"a": F(3, 4)}) == F(1, 2)
    assert PhaseExpr.parse("1/4") == F(1, 4)        # a constant expression is a plain Fraction
    partial = PhaseExpr.parse("a+b").substitute({"a": F(1)})
    assert isinstance(partial, PhaseExpr) and str(partial) == "1+b"
    with pytest.raises(ValueError):
        PhaseExpr.parse("a*b")
    d = Diagram.build({0: ("Z", "a+1/2")}, [])
    assert not d.is_ground() and d.variables() == frozenset({"a"})
    assert d.to_json()["vertices"] == [[0, "Z", "1/2+a"]]
    assert d.substitute({"a": F(1, 2)}).phase(0) == F(1)


def test_relabel_canonical_identifies_isomorphic_diagrams_and_separates_others():
    a = Diagram.build({0: ("B", 0), 1: ("B", 0), 2: ("Z", F(1, 4)), 3: ("X", 0), 4: ("Z", 0)},
                      [(0, 2, False), (2, 3, True), (3, 4, False), (4, 1, False), (2, 4, True)],
                      inputs=[0], outputs=[1])
    b = Diagram.build({10: ("B", 0), 20: ("B", 0), 30: ("Z", F(1, 4)), 40: ("X", 0), 50: ("Z", 0)},
                      [(10, 30, False), (30, 40, True), (40, 50, False), (50, 20, False),
                       (30, 50, True)], inputs=[10], outputs=[20])
    assert a != b and a.relabel_canonical() == b.relabel_canonical()
    assert dg.isomorphic(a, b)
    # one phase differs: not isomorphic
    c = b.with_phase(30, F(3, 4))
    assert not dg.isomorphic(a, c)
    # swapping input and output roles matters
    swapped = Diagram(b.vertices, b.edges, inputs=(20,), outputs=(10,))
    assert not dg.isomorphic(a, swapped)
    # a Hadamard edge is not a plain edge
    e = Diagram.build({10: ("B", 0), 20: ("B", 0), 30: ("Z", F(1, 4)), 40: ("X", 0), 50: ("Z", 0)},
                      [(10, 30, False), (30, 40, False), (40, 50, False), (50, 20, False),
                       (30, 50, True)], inputs=[10], outputs=[20])
    assert not dg.isomorphic(a, e)
    # canonical form is idempotent and labels boundary vertices first, in order
    can = a.relabel_canonical()
    assert can.relabel_canonical() == can and can.inputs == (0,) and can.outputs == (1,)


def test_relabel_canonical_breaks_symmetric_ties_deterministically():
    # a 4-cycle of Z(0) spiders with alternating Hadamard edges, no boundary: every
    # vertex looks alike to refinement; the canonical form must still be unique
    def cycle(ids, h):
        v = {i: ("Z", 0) for i in ids}
        e = [(ids[k], ids[(k + 1) % 4], h[k]) for k in range(4)]
        return Diagram.build(v, e)
    a = cycle([0, 1, 2, 3], [True, False, True, False])
    b = cycle([7, 5, 3, 1], [False, True, False, True])
    assert a.relabel_canonical() == b.relabel_canonical()
    c = cycle([0, 1, 2, 3], [True, True, False, False])
    assert a.relabel_canonical() != c.relabel_canonical()


# ----------------------------------------------------------------------------- Task 1: semantics


def assert_equal_up_to_scalar(m, ref):
    assert m.shape == ref.shape
    assert sem.equal_up_to_scalar(m, ref), f"\n{m}\n!=\n{ref}"


def test_matrix_of_the_wire_identity_and_hadamard():
    assert_equal_up_to_scalar(sem.matrix(wire()), np.eye(2))
    assert_equal_up_to_scalar(sem.matrix(wire(hadamard=True)), H)


def test_matrix_of_bell_state_cnot_and_phase_gate():
    assert_equal_up_to_scalar(sem.matrix(bell()), np.array([[1], [0], [0], [1]], dtype=complex))
    assert_equal_up_to_scalar(sem.matrix(cnot()), CNOT)
    t = sem.matrix(spider_1_1("Z", F(1, 4)))
    assert_equal_up_to_scalar(t, np.diag([1, np.exp(1j * np.pi / 4)]))
    # exact scalar convention: Z(alpha) 1->1 is diag(1, e^{i pi alpha}) with no extra factor
    assert np.allclose(t, np.diag([1, np.exp(1j * np.pi / 4)]))
    x = sem.matrix(spider_1_1("X", F(1, 2)))
    assert_equal_up_to_scalar(x, H @ np.diag([1, 1j]) @ H)


def test_hadamard_squared_is_identity_and_colour_change_is_invariant():
    hh = Diagram.build({0: ("B", 0), 1: ("Z", 0), 2: ("B", 0)},
                       [(0, 1, True), (1, 2, True)], inputs=[0], outputs=[2])
    assert_equal_up_to_scalar(sem.matrix(hh), np.eye(2))
    # X(alpha) with plain legs == Z(alpha) with every leg toggled to Hadamard
    for legs in [(1, 1), (2, 1), (1, 2), (0, 3)]:
        n_in, n_out = legs
        ids_in = list(range(n_in))
        ids_out = list(range(n_in, n_in + n_out))
        c = n_in + n_out
        x = Diagram.build({**{i: ("B", 0) for i in ids_in + ids_out}, c: ("X", F(1, 4))},
                          [(i, c, False) for i in ids_in + ids_out], inputs=ids_in, outputs=ids_out)
        z = Diagram.build({**{i: ("B", 0) for i in ids_in + ids_out}, c: ("Z", F(1, 4))},
                          [(i, c, True) for i in ids_in + ids_out], inputs=ids_in, outputs=ids_out)
        assert_equal_up_to_scalar(sem.matrix(x), sem.matrix(z))


def test_self_loops_and_parallel_edges_and_scalar_spiders():
    # a plain self-loop on a spider is the spider (scalar 1); a Hadamard self-loop adds pi
    base = spider_1_1("Z", F(1, 4))
    loop = Diagram.build({0: ("B", 0), 1: ("Z", F(1, 4)), 2: ("B", 0)},
                         [(0, 1, False), (1, 2, False), (1, 1, False)], inputs=[0], outputs=[2])
    assert np.allclose(sem.matrix(loop), sem.matrix(base))
    hloop = Diagram.build({0: ("B", 0), 1: ("Z", F(1, 4)), 2: ("B", 0)},
                          [(0, 1, False), (1, 2, False), (1, 1, True)], inputs=[0], outputs=[2])
    assert_equal_up_to_scalar(sem.matrix(hloop), sem.matrix(spider_1_1("Z", F(5, 4))))
    # Hopf: Z and X joined by two parallel plain edges are disconnected (up to scalar)
    hopf = Diagram.build({0: ("B", 0), 1: ("Z", 0), 2: ("X", 0), 3: ("B", 0)},
                         [(0, 1, False), (1, 2, False), (1, 2, False), (2, 3, False)],
                         inputs=[0], outputs=[3])
    apart = Diagram.build({0: ("B", 0), 1: ("Z", 0), 2: ("X", 0), 3: ("B", 0)},
                          [(0, 1, False), (2, 3, False)], inputs=[0], outputs=[3])
    assert_equal_up_to_scalar(sem.matrix(hopf), sem.matrix(apart))
    # a 0-leg spider is the scalar 1 + e^{i pi alpha}; Z(pi) alone is the zero scalar
    assert np.allclose(sem.matrix(Diagram.build({0: ("Z", F(1, 2))}, [])), [[1 + 1j]])
    assert np.allclose(sem.matrix(Diagram.build({0: ("Z", F(1))}, [])), [[0]])
    # a diagram wiring an input straight to an output next to a scalar spider
    d = Diagram.build({0: ("B", 0), 1: ("B", 0), 2: ("X", F(1, 2))}, [(0, 1, False)],
                      inputs=[0], outputs=[1])
    assert np.allclose(sem.matrix(d), (1 + 1j) * np.eye(2))


def test_equal_up_to_scalar_tolerance_and_zero_handling():
    a = np.array([[1, 2], [3, 4]], dtype=complex)
    assert sem.equal_up_to_scalar(a, (0.3 - 0.7j) * a)
    assert sem.equal_up_to_scalar(a, a + 1e-12)
    assert not sem.equal_up_to_scalar(a, a + 1e-6)
    assert not sem.equal_up_to_scalar(a, np.zeros((2, 2)))
    assert sem.equal_up_to_scalar(np.zeros((2, 2)), np.zeros((2, 2)))
    assert not sem.equal_up_to_scalar(a, np.eye(3))


def test_semantics_rejects_non_ground_ill_formed_and_over_budget_diagrams():
    with pytest.raises(sem.SemanticsError):
        sem.matrix(Diagram.build({0: ("Z", "a")}, []))
    # a cup (two inputs wired together) is well-formed; a degree-2 boundary vertex is not
    assert_equal_up_to_scalar(
        sem.matrix(Diagram.build({0: ("B", 0), 1: ("B", 0)}, [(0, 1, False)], inputs=[0, 1])),
        np.array([[1, 0, 0, 1]], dtype=complex),
    )
    with pytest.raises(sem.SemanticsError):
        sem.matrix(Diagram.build({0: ("B", 0), 1: ("B", 0), 2: ("Z", 0)},
                                 [(0, 1, False), (0, 2, False)], inputs=[0], outputs=[1]))
    big_ids = list(range(7))
    big = Diagram.build({**{i: ("B", 0) for i in big_ids}, 7: ("Z", 0)},
                        [(i, 7, False) for i in big_ids], inputs=big_ids, outputs=[])
    with pytest.raises(sem.SemanticsError):
        sem.matrix(big)
    assert sem.boundary_wires(big) == 7 > sem.MAX_BOUNDARY_WIRES


# ----------------------------------------------------------------------------- Task 2: rules

from empiricist.packs.zx import derivation as dv  # noqa: E402
from empiricist.packs.zx import rewrite as rw  # noqa: E402
from empiricist.packs.zx import rules as rl  # noqa: E402
from empiricist.packs.zx.rewrite import Matching  # noqa: E402
from empiricist.packs.zx.rules import RULES, Rule  # noqa: E402

PHASES = [F(k, 4) for k in range(8)]


def instance(rule: Rule, bindings: dict, star_legs: dict[int, list[bool]] | None = None):
    """The LHS pattern as a concrete host: variables bound, every star vertex given the
    extra boundary legs in `star_legs` (a list of Hadamard flags per star vertex)."""
    lhs = rule.lhs.substitute(bindings)
    verts = {v: lhs.vertex_data(v) for v in lhs.vertex_ids}
    edges = list(lhs.edges)
    nxt = lhs.max_id + 1
    for star, flags in (star_legs or {}).items():
        for h in flags:
            verts[nxt] = ("B", 0)
            edges.append((star, nxt, h))
            nxt += 1
    outs = sorted(v for v, (k, _) in verts.items() if k == "B")
    return Diagram.build(verts, edges, inputs=[], outputs=outs)


def identity_matching(rule: Rule, bindings: dict) -> Matching:
    return Matching(vertices={v: v for v in rule.lhs.vertex_ids},
                    phases={k: str(v) for k, v in bindings.items()})


def bindings_for(rule: Rule, seed: int) -> list[dict[str, Fraction]]:
    """A deterministic spread of phase bindings for the rule's variables."""
    names = sorted(rule.lhs.variables() | rule.rhs.variables())
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(12 if names else 1):
        out.append({n: PHASES[int(rng.integers(8))] for n in names})
    return out


@pytest.mark.parametrize("name", sorted(RULES))
def test_every_library_rule_is_sound_on_concrete_instances(name):
    rule = RULES[name]
    star_configs: list[dict[int, list[bool]]] = [{}]
    if rule.stars:
        star_configs += [
            {s: [False] for s in rule.stars},
            {s: [True, False] for s in rule.stars},
            {s: [True] for s in rule.stars},
        ]
    checked = 0
    for b in bindings_for(rule, seed=7):
        for legs in star_configs:
            host = instance(rule, b, legs)
            if sem.boundary_wires(host) > sem.MAX_BOUNDARY_WIRES:
                continue
            result = rw.apply(host, rule, identity_matching(rule, b))
            assert result.is_well_formed(), result.well_formedness_problems()
            assert sem.equal_up_to_scalar(sem.matrix(host), sem.matrix(result)), (name, b, legs)
            checked += 1
    assert checked > 0


@pytest.mark.parametrize("name", sorted(RULES))
def test_every_library_rule_round_trips_through_json_and_reverses(name):
    rule = RULES[name]
    assert Rule.from_json(rule.to_json()) == rule
    rev = rule.reversed()
    assert rev.lhs == rule.rhs and rev.rhs == rule.lhs
    assert rev.reversed() == rule
    assert rule.reference


def test_rule_table_lists_every_rule_with_its_reference():
    table = rl.rule_table()
    assert set(r["name"] for r in table) == set(RULES)
    assert all(r["reference"] for r in table)
    assert "S1" in RULES["fusion"].reference and "JPV" in RULES["fusion"].reference
    assert set(rl.CLIFFORD_RULES) <= set(RULES) and set(rl.CLIFFORD_T_RULES) <= set(RULES)
    assert "supp" in rl.CLIFFORD_T_RULES and "supp" not in rl.CLIFFORD_RULES


def test_rule_validation_rejects_bad_interfaces_and_targets():
    z = Diagram.build({0: ("B", 0), 1: ("Z", 0)}, [(0, 1, False)], outputs=[0])
    other = Diagram.build({5: ("B", 0), 1: ("Z", 0)}, [(5, 1, False)], outputs=[5])
    with pytest.raises(ValueError):
        Rule("bad", z, other, residual=())
    with pytest.raises(ValueError):            # star must be an LHS interior vertex
        Rule("bad", z, z, residual=((0, ((1, False),)),))
    with pytest.raises(ValueError):            # target must be an RHS interior vertex
        Rule("bad", z, z, residual=((1, ((7, False),)),))
    # a variable that occurs only on the RHS (legal: the reverse of a phase-dropping rule)
    # must be bound by the matching at apply time
    free_rhs = Diagram.build({0: ("B", 0), 1: ("Z", "a")}, [(0, 1, False)], outputs=[0])
    free = Rule("free", z, free_rhs, residual=())
    host = Diagram.build({0: ("B", 0), 1: ("Z", 0)}, [(0, 1, False)], inputs=[0])
    with pytest.raises(rw.RewriteError, match="unbound"):
        rw.apply(host, free, Matching(vertices={0: 0, 1: 1}))
    out = rw.apply(host, free, Matching(vertices={0: 0, 1: 1}, phases={"a": "1/4"}))
    assert [out.phase(v) for v in out.interior] == [F(1, 4)]


# ----------------------------------------------------------------------------- Task 2: rewriting


def two_spiders(p1, p2, *, mid_hadamard=False) -> Diagram:
    return Diagram.build(
        {0: ("B", 0), 1: ("Z", p1), 2: ("Z", p2), 3: ("B", 0)},
        [(0, 1, False), (1, 2, mid_hadamard), (2, 3, False)], inputs=[0], outputs=[3],
    )


def test_fusion_matches_binds_phases_and_carries_residual_legs():
    host = two_spiders(F(1, 4), F(3, 4))
    ms = rw.find_matchings(host, RULES["fusion"])
    assert len(ms) == 2                      # the two spiders in either role
    m = next(m for m in ms if m.vertices[0] == 1)
    info = rw.check_matching(host, RULES["fusion"], m)
    assert info.bindings == {"a": F(1, 4), "b": F(3, 4)}
    assert set(info.residual[0]) == {0} and set(info.residual[1]) == {2}
    out = rw.apply(host, RULES["fusion"], m)
    assert dg.isomorphic(out, spider_1_1("Z", F(1)))
    # a Hadamard edge between the spiders is not a fusion
    h_between = two_spiders(F(1, 4), F(3, 4), mid_hadamard=True)
    assert rw.find_matchings(h_between, RULES["fusion"]) == []
    # explicit phases that contradict the host are rejected
    with pytest.raises(rw.RewriteError):
        rw.check_matching(host, RULES["fusion"], Matching(vertices=m.vertices, phases={"a": "1/2"}))


def test_matching_conditions_are_enforced():
    host = two_spiders(F(1, 4), F(3, 4))
    fusion = RULES["fusion"]
    with pytest.raises(rw.RewriteError, match="injective"):
        rw.check_matching(host, fusion, Matching(vertices={0: 1, 1: 1}))
    with pytest.raises(rw.RewriteError, match="kind"):
        rw.check_matching(host, RULES["fusion_x"], Matching(vertices={0: 1, 1: 2}))
    with pytest.raises(rw.RewriteError, match="missing"):
        rw.check_matching(host, fusion, Matching(vertices={0: 1}))
    with pytest.raises(rw.RewriteError, match="no host vertex"):
        rw.check_matching(host, fusion, Matching(vertices={0: 1, 1: 42}))
    # identity needs a degree-2 zero spider: a spider with a third leg is not one
    ident = RULES["identity_z"]
    three = Diagram.build({0: ("B", 0), 1: ("Z", 0), 2: ("B", 0), 3: ("B", 0)},
                          [(0, 1, False), (1, 2, False), (1, 3, False)], inputs=[0], outputs=[2, 3])
    with pytest.raises(rw.RewriteError, match="extra"):
        rw.check_matching(three, ident, Matching(vertices={0: 0, 1: 1, 2: 2}))
    assert rw.find_matchings(three, ident) == []
    # a boundary pattern vertex may not land on a matched interior vertex
    zx_host = Diagram.build({0: ("B", 0), 1: ("Z", F(1, 4)), 2: ("X", 1), 3: ("B", 0)},
                            [(0, 1, False), (1, 2, False), (2, 3, False)], inputs=[0], outputs=[3])
    with pytest.raises(rw.RewriteError, match="identification"):
        rw.check_matching(zx_host, RULES["pi_commute"], Matching(vertices={0: 1, 1: 1, 2: 2, 3: 3}))
    assert len(rw.find_matchings(zx_host, RULES["pi_commute"])) == 1


def test_identity_removal_and_hadamard_cancellation():
    d = Diagram.build({0: ("B", 0), 1: ("Z", 0), 2: ("B", 0)}, [(0, 1, True), (1, 2, True)],
                      inputs=[0], outputs=[2])
    assert rw.find_matchings(d, RULES["identity_z"]) == []
    ms = rw.find_matchings(d, RULES["identity_z_hh"])
    assert len(ms) == 2
    assert dg.isomorphic(rw.apply(d, RULES["identity_z_hh"], ms[0]), wire())
    # boundary images may coincide: Z(0) with both legs on one spider leaves a self-loop
    loopy = Diagram.build({0: ("B", 0), 1: ("Z", F(1, 4)), 2: ("Z", 0)},
                          [(0, 1, False), (1, 2, False), (1, 2, False)], inputs=[0], outputs=[])
    ms = rw.find_matchings(loopy, RULES["identity_z"])
    assert len(ms) == 1 and ms[0].vertices == {0: 1, 1: 2, 2: 1}
    out = rw.apply(loopy, RULES["identity_z"], ms[0])
    assert out.edges == ((0, 1, False), (1, 1, False))


def test_colour_change_flips_residual_legs_but_not_self_loops():
    host = Diagram.build({0: ("B", 0), 1: ("X", F(1, 4)), 2: ("B", 0), 3: ("Z", 0)},
                         [(0, 1, False), (1, 2, True), (1, 3, False), (1, 1, True), (3, 3, False)],
                         inputs=[0], outputs=[2])
    (m,) = rw.find_matchings(host, RULES["colour_change"])
    out = rw.apply(host, RULES["colour_change"], m)
    new = next(v for v in out.interior if out.kind(v) == "Z" and out.phase(v) == F(1, 4))
    flags = sorted((out.other_end(e, new), out.edges[e][2]) for e in set(out.incident(new)))
    assert flags == [(0, True), (2, False), (3, True), (new, True)]
    assert sem.equal_up_to_scalar(sem.matrix(host), sem.matrix(out))


def test_reverse_direction_and_explicit_splits():
    fused = spider_1_1("Z", F(1, 2))
    unfuse = RULES["fusion"].reversed()
    # unfusing needs the phase split given explicitly; legs default to the first target
    m = Matching(vertices={0: 1}, phases={"a": "1/4"})
    out = rw.apply(fused, unfuse, m)
    assert dg.isomorphic(out, Diagram.build(
        {0: ("B", 0), 1: ("Z", F(1, 4)), 2: ("Z", F(1, 4)), 3: ("B", 0)},
        [(0, 1, False), (1, 2, False), (1, 3, False)], inputs=[0], outputs=[3]))
    with pytest.raises(rw.RewriteError, match="unbound"):
        rw.apply(fused, unfuse, Matching(vertices={0: 1}))
    # a split sends the output leg (host edge 1) to the second spider
    m2 = Matching(vertices={0: 1}, phases={"a": "1/4"}, split={(1, 0): 1})
    out2 = rw.apply(fused, unfuse, m2)
    assert dg.isomorphic(out2, two_spiders(F(1, 4), F(1, 4)))
    with pytest.raises(rw.RewriteError, match="split"):
        rw.apply(fused, unfuse, Matching(vertices={0: 1}, phases={"a": "1/4"}, split={(1, 0): 9}))


def test_euler_matches_a_hadamard_edge_between_any_two_vertices():
    ms = rw.find_matchings(wire(hadamard=True), RULES["euler"])
    assert len(ms) == 2
    out = rw.apply(wire(hadamard=True), RULES["euler"], ms[0])
    assert len(out.interior) == 3 and sem.equal_up_to_scalar(sem.matrix(out), H)
    back = rw.find_matchings(out, RULES["euler"].reversed())
    assert len(back) == 2                    # the Z-X-Z chain is symmetric
    for m in back:
        assert dg.isomorphic(rw.apply(out, RULES["euler"].reversed(), m), wire(hadamard=True))


def test_symbolic_hosts_match_syntactically():
    host = Diagram.build({0: ("B", 0), 1: ("Z", "a"), 2: ("Z", "b+1/2"), 3: ("B", 0)},
                         [(0, 1, False), (1, 2, False), (2, 3, False)], inputs=[0], outputs=[3])
    (m,) = [m for m in rw.find_matchings(host, RULES["fusion"]) if m.vertices[0] == 1]
    out = rw.apply(host, RULES["fusion"], m)
    assert str(out.phase(out.interior[0])) == "1/2+a+b"
    assert rw.find_matchings(host, RULES["identity_z"]) == []     # `a` is not syntactically 0


# ----------------------------------------------------------------------------- Task 2: derivations


def test_replay_reports_the_reached_diagram_and_the_first_bad_step():
    start = two_spiders(F(1, 4), F(7, 4))
    steps = [
        dv.Step("fusion", Matching(vertices={0: 1, 1: 2}), "->"),
        dv.Step("identity_z", Matching(vertices={0: 0, 1: 4, 2: 3}), "->"),
    ]
    good = dv.Derivation(start, tuple(steps), wire())
    r = dv.replay(good, RULES)
    assert r.ok and r.failed_step is None and r.steps_applied == 2
    assert dg.isomorphic(r.reached, wire())
    # the claimed end is not what the steps reach
    r2 = dv.replay(dv.Derivation(start, tuple(steps), wire(hadamard=True)), RULES)
    assert not r2.ok and r2.failed_step is None and not r2.end_matches
    # a step whose matching does not fit
    misfit = dv.Step("identity_z", Matching(vertices={0: 0, 1: 1, 2: 2}), "->")
    r3 = dv.replay(dv.Derivation(start, (misfit,), wire()), RULES)
    assert not r3.ok and r3.failed_step == 0 and "phase" in r3.reason
    # an unknown rule, a bad direction
    unknown = dv.Step("nope", Matching(vertices={}), "->")
    r4 = dv.replay(dv.Derivation(start, (unknown,), wire()), RULES)
    assert r4.failed_step == 0 and "unknown rule" in r4.reason
    sideways = dv.Step("fusion", steps[0].matching, "up")
    r5 = dv.replay(dv.Derivation(start, (sideways,), wire()), RULES)
    assert r5.failed_step == 0 and "direction" in r5.reason


def test_derivation_json_round_trip_and_reverse_steps():
    start = wire(hadamard=True)
    step = dv.Step("euler", Matching(vertices={0: 0, 1: 1}), "->")
    d = dv.Derivation(start, (step,), start)
    obj = d.to_json()
    assert obj["steps"][0] == {
        "rule": "euler", "direction": "->",
        "matching": {"vertices": {"0": 0, "1": 1}, "phases": {}, "split": []},
    }
    assert dv.Derivation.from_json(obj) == d
    r = dv.replay(d, RULES)
    assert r.failed_step is None and not r.end_matches
    # go there and back with a reverse step
    mid = r.reached
    back = dv.Step("euler", rw.find_matchings(mid, RULES["euler"].reversed())[0], "<-")
    assert dv.replay(dv.Derivation(start, (step, back), start), RULES).ok
    with pytest.raises(ValueError):
        dv.Derivation.from_json({"start": start.to_json()})
    with pytest.raises(ValueError):
        dv.Step.from_json({"rule": "euler", "direction": "->", "matching": {"vertices": {"x": 0}}})


# ----------------------------------------------------------------------------- Task 3a: overlaps

from empiricist.packs.zx import critical_pairs as cp  # noqa: E402


def subset(*names: str) -> dict[str, Rule]:
    return {n: RULES[n] for n in names}


def erase(d: Diagram) -> Diagram:
    """Symbolic phases set to 0: the shape of a symbolic diagram."""
    return d.substitute({v: 0 for v in d.variables()})


def test_fusion_overlaps_itself_on_chains_and_parallel_edges_and_joins_in_one_step():
    ovs = cp.overlaps(RULES["fusion"], RULES["fusion"], star_legs=0)
    shapes = [erase(o.host) for o in ovs]
    chain = Diagram.build({0: ("Z", 0), 1: ("Z", 0), 2: ("Z", 0)}, [(0, 1, False), (1, 2, False)])
    parallel = Diagram.build({0: ("Z", 0), 1: ("Z", 0)}, [(0, 1, False), (0, 1, False)])
    assert any(dg.isomorphic(s, chain) for s in shapes)
    assert any(dg.isomorphic(s, parallel) for s in shapes)
    assert all(o.host.variables() for o in ovs)          # phases stay symbolic
    for o in ovs:
        assert o.rule1 == o.rule2 == "fusion"
        assert cp.joinable(o.result1, o.result2, subset("fusion"), depth=1).joinable
    # with context legs on the stars there are more overlaps, all still joinable
    more = cp.overlaps(RULES["fusion"], RULES["fusion"], star_legs=1)
    assert len(more) > len(ovs)
    assert all(cp.joinable(o.result1, o.result2, subset("fusion"), depth=1).joinable for o in more)


def test_fusion_and_identity_overlap_by_binding_the_phase_to_zero():
    ovs = cp.overlaps(RULES["fusion"], RULES["identity_z"], star_legs=0)
    assert ovs
    for o in ovs:
        z0 = [v for v in o.host.interior if o.host.phase(v) == 0]
        assert z0, o.host.to_json()
        assert cp.joinable(o.result1, o.result2, subset("fusion", "identity_z"), depth=1).joinable


def test_check_reports_the_first_non_joinable_pair_and_a_fix_makes_it_pass():
    broken = cp.check(subset("fusion_x", "colour_change"), depth=2)
    assert not broken.ok and broken.failure is not None
    o, j = broken.failure
    assert {o.rule1, o.rule2} == {"fusion_x", "colour_change"} and not j.joinable
    fixed = cp.check(subset("fusion", "fusion_x", "colour_change"), depth=2)
    assert fixed.ok and fixed.overlaps >= broken.overlaps and fixed.failure is None
    assert cp.check(subset("fusion", "fusion_x", "colour_change"), depth=1).ok is False


def absorb(k: int) -> Rule:
    """X(0) state through a Z(k/4) wire is the X(0) state (Z(phi)|0> = |0>)."""
    lhs = Diagram.build({0: ("X", 0), 1: ("Z", F(k, 4)), 2: ("B", 0)},
                        [(0, 1, False), (1, 2, False)], outputs=[2])
    rhs = Diagram.build({3: ("X", 0), 2: ("B", 0)}, [(3, 2, False)], outputs=[2])
    return Rule(f"absorb_{k}", lhs, rhs, (), "test: <0| Z(k/4)")


def scalar(k: int) -> Rule:
    """The scalar X(0)-Z(k/4) is 1 for every k: removable."""
    lhs = Diagram.build({0: ("X", 0), 1: ("Z", F(k, 4))}, [(0, 1, False)])
    return Rule(f"scalar_{k}", lhs, Diagram.build({}, []), (), "test: <0|Z(k/4)> = 1")


def test_symbolic_failure_falls_back_to_a_ground_case_split():
    for k in range(8):
        for r in (absorb(k), scalar(k)):
            host = instance(r, {})
            assert sem.equal_up_to_scalar(sem.matrix(host),
                                          sem.matrix(rw.apply(host, r, identity_matching(r, {}))))
    # fusion/absorb_k overlap: X(0)-Z(k/4)-Z(b) rewrites to X(0)-Z(b+k/4) or X(0)-Z(b);
    # no constant-phase rule matches the symbolic b, every ground instance joins
    rules = subset("fusion") | {f"absorb_{k}": absorb(k) for k in range(8)}
    rules |= {f"scalar_{k}": scalar(k) for k in range(8)}
    rep = cp.check(rules, depth=1, star_legs=0)
    assert rep.ok, rep.failure
    assert rep.case_splits > 0 and rep.overlaps > 0
    # with a single scalar rule the pair fails at a concrete instance
    rep2 = cp.check({"fusion": RULES["fusion"], "absorb_1": absorb(1), "scalar_1": scalar(1)},
                    depth=1, star_legs=0)
    assert not rep2.ok
    _, j = rep2.failure
    assert not j.joinable and j.instances > 0 and "instance" in j.reason


def test_joinability_budget_is_an_error_not_a_verdict():
    with pytest.raises(cp.CriticalPairError):
        cp.joinable(two_spiders(F(1, 4), F(1, 4)), wire(), subset("fusion", "euler"), depth=3,
                    max_nodes=1)


# ----------------------------------------------------------------------------- Task 3b: termination

from empiricist.packs.zx import termination as tm  # noqa: E402


def test_measure_counts_interior_vertices_and_edges():
    d = Diagram.build({0: ("B", 0), 1: ("Z", F(1, 4)), 2: ("X", 0), 3: ("B", 0)},
                      [(0, 1, False), (1, 2, True), (1, 2, True), (2, 3, False), (2, 2, False)],
                      inputs=[0], outputs=[3])
    comps = ["vertices", "z_vertices", "x_vertices", "edges", "hadamard_edges", "plain_edges",
             "self_loops"]
    assert tm.measure(d, comps) == (2, 1, 1, 5, 2, 3, 1)
    with pytest.raises(tm.TerminationError):
        tm.measure(d, ["phase_sum"])


def test_symbolic_decrease_per_rule():
    ok = tm.check_rule(RULES["fusion"], ["vertices", "edges"])
    assert ok.decreases and ok.component == "vertices"
    tie = tm.check_rule(RULES["colour_change"], ["vertices", "edges", "hadamard_edges"])
    assert not tie.decreases and tie.component == "hadamard_edges" and "leg" in tie.detail
    assert tm.check_rule(RULES["colour_change"], ["x_vertices"]).decreases
    assert not tm.check_rule(RULES["hopf"], ["vertices"]).decreases
    assert tm.check_rule(RULES["hopf"], ["vertices", "edges"]).component == "edges"
    assert tm.check_rule(RULES["euler"], ["hadamard_edges"]).decreases
    assert not tm.check_rule(RULES["euler"].reversed(), ["hadamard_edges"]).decreases
    assert not tm.check_rule(RULES["fusion"].reversed(), ["vertices", "edges"]).decreases
    assert tm.check_rule(RULES["loop_z"], ["self_loops"]).decreases
    assert tm.check_rule(RULES["loop_z_h"], ["edges"]).decreases
    # fusion under edges-first: the pattern edge goes, star-star residual edges become
    # self-loops (still edges), so edges strictly decrease
    assert tm.check_rule(RULES["fusion"], ["edges"]).decreases


def test_symbolic_decrease_implies_decrease_on_every_instance():
    comps = ["vertices", "edges", "hadamard_edges"]
    for name in ("fusion", "identity_z_hh", "hopf", "euler", "bialgebra", "copy", "loop_x_h",
                 "supp", "bw", "commute_controls"):
        rule = RULES[name]
        verdict = tm.check_rule(rule, comps)
        if not verdict.decreases:
            continue
        for b in bindings_for(rule, seed=3)[:4]:
            for legs in ({}, {s: [True, False, True] for s in rule.stars}):
                host = instance(rule, b, legs)
                out = rw.apply(host, rule, identity_matching(rule, b))
                assert tm.measure(host, comps) > tm.measure(out, comps), (name, b, legs)


def test_check_names_the_first_rule_that_does_not_decrease():
    rules = subset("fusion", "identity_z", "hopf", "euler")
    rep = tm.check(rules, ["hadamard_edges", "vertices", "edges"])
    assert rep.ok and [(r.rule, r.component) for r in rep.rules] == [
        ("euler", "hadamard_edges"), ("fusion", "vertices"), ("hopf", "edges"),
        ("identity_z", "vertices")]
    rep2 = tm.check(rules | subset("colour_change"), ["hadamard_edges", "vertices", "edges"])
    assert not rep2.ok and rep2.failure.rule == "colour_change"
    with pytest.raises(tm.TerminationError):
        tm.check(rules, ["vertices", "nope"])
    with pytest.raises(tm.TerminationError):
        tm.check(rules, [])


def test_rename_apart_and_overlap_dedup_are_deterministic():
    r = cp.rename_apart(RULES["fusion"], "_1")
    assert r.variables() == {"a_1", "b_1"} and r.name == "fusion"
    a = cp.overlaps(RULES["fusion"], RULES["hopf"], star_legs=1)
    b = cp.overlaps(RULES["fusion"], RULES["hopf"], star_legs=1)
    assert [o.host for o in a] == [o.host for o in b]
    keys = [o.key for o in a]
    assert len(keys) == len(set(keys))


# ----------------------------------------------------------------------------- Task 3c: verifiers

from empiricist.ledger.models import Verdict  # noqa: E402
from empiricist.packs import certify_pack_verifier, load_pack  # noqa: E402
from empiricist.packs.zx import MANIFEST  # noqa: E402
from empiricist.packs.zx import verifiers as vf  # noqa: E402

VERIFIER_NAMES = ("zx_derivation", "zx_semantic_equal", "zx_critical_pairs", "zx_termination",
                  "zx_rule_sound", "zx_completeness")


def payload(obj) -> bytes:
    return json.dumps(obj).encode()


def test_manifest_declares_the_verifiers_for_p6(tmp_path):
    assert load_pack("zx") is MANIFEST
    assert MANIFEST.name == "zx" and set(MANIFEST.verifiers) == set(VERIFIER_NAMES)
    assert MANIFEST.problems == {"P6": "p6-zx-v2"} and MANIFEST.version == "0.2"
    hashes = set()
    for name, factory in MANIFEST.verifiers.items():
        v = factory(tmp_path)
        assert v.name == name and v.version
        assert len(v.binary_hash) == 64 and int(v.binary_hash, 16) >= 0
        hashes.add(v.binary_hash)
    assert len(hashes) == len(VERIFIER_NAMES)      # each hash covers its own engines


@pytest.mark.parametrize("name", VERIFIER_NAMES)
def test_golden_suites_have_near_miss_fails_and_exact_verdicts(name, tmp_path):
    v = MANIFEST.verifiers[name](tmp_path)
    suite = v.golden_suite()
    verdicts = {c.expected for c in suite}
    assert verdicts == {Verdict.PASS, Verdict.FAIL}
    for c in suite:
        r = v.verify_bytes(c.payload)
        assert r.verdict is c.expected, (c.label, r.details)
        assert r.details.get("detail")


@pytest.mark.parametrize("name", VERIFIER_NAMES)
def test_certify_in_a_temporary_repository(name, tmp_path):
    stamp, problems = certify_pack_verifier(tmp_path, name)
    assert problems == [] and stamp is not None
    assert stamp.name == name and stamp.pack == "zx"


def test_verifiers_are_total_and_report_errors_not_verdicts(tmp_path):
    for name in VERIFIER_NAMES:
        v = MANIFEST.verifiers[name](tmp_path)
        for bad in (b"", b"not json", b"[1, 2]", b"{}", b'{"rules": 5}', b"\xff\xfe"):
            r = v.verify_bytes(bad)
            assert r.verdict is Verdict.ERROR and r.details["error"], (name, bad)
    d = MANIFEST.verifiers["zx_derivation"](tmp_path)
    r = d.verify_bytes(payload({"start": wire().to_json(), "end": wire().to_json(),
                                "steps": [{"rule": "nope", "matching": {"vertices": {}}}]}))
    assert r.verdict is Verdict.ERROR and "nope" in r.details["error"]
    r = d.verify_bytes(payload({"start": wire().to_json(), "end": wire().to_json(), "steps": [],
                                "rules": [RULES["fusion"].to_json()]}))
    assert r.verdict is Verdict.ERROR and "fusion" in r.details["error"]   # shadows the library
    ill = Diagram.build({0: ("B", 0), 1: ("Z", F(1, 3)), 2: ("B", 0)},
                        [(0, 1, False), (1, 2, False)], inputs=[0], outputs=[2])
    r = d.verify_bytes(payload({"start": ill.to_json(), "end": ill.to_json(), "steps": []}))
    assert r.verdict is Verdict.ERROR and "well-formed" in r.details["error"]
    s = MANIFEST.verifiers["zx_semantic_equal"](tmp_path)
    ids = list(range(7))
    big = Diagram.build({**{i: ("B", 0) for i in ids}, 7: ("Z", 0)}, [(i, 7, False) for i in ids],
                        inputs=ids)
    r = s.verify_bytes(payload({"a": big.to_json(), "b": big.to_json()}))
    assert r.verdict is Verdict.ERROR and "budget" in r.details["error"]
    c = MANIFEST.verifiers["zx_critical_pairs"](tmp_path)
    r = c.verify_bytes(payload({"rules": ["fusion", "euler"], "depth": 3, "max_nodes": 1}))
    assert r.verdict is Verdict.ERROR and "exceeded" in r.details["error"]
    r = c.verify_bytes(payload({"rules": ["fusion"], "depth": -1}))
    assert r.verdict is Verdict.ERROR
    t = MANIFEST.verifiers["zx_termination"](tmp_path)
    r = t.verify_bytes(payload({"rules": ["fusion"], "measure": ["phase_sum"]}))
    assert r.verdict is Verdict.ERROR and "phase_sum" in r.details["error"]


def test_verdict_details_name_the_failure(tmp_path):
    d = MANIFEST.verifiers["zx_derivation"](tmp_path)
    start = two_spiders(F(1, 4), F(7, 4))
    steps = [{"rule": "fusion", "matching": {"vertices": {"0": 1, "1": 2}}, "direction": "->"},
             {"rule": "identity_z", "matching": {"vertices": {"0": 0, "1": 4, "2": 3}}}]
    ok = d.verify_bytes(payload({"start": start.to_json(), "end": wire().to_json(),
                                 "steps": steps}))
    assert ok.verdict is Verdict.PASS and ok.details["steps"] == 2
    bad = d.verify_bytes(payload({"start": start.to_json(), "end": wire().to_json(),
                                  "steps": steps[:1]}))
    assert bad.verdict is Verdict.FAIL and bad.details["failed_step"] is None
    bad2 = d.verify_bytes(payload({"start": start.to_json(), "end": wire().to_json(),
                                   "steps": [steps[1]]}))
    assert bad2.verdict is Verdict.FAIL and bad2.details["failed_step"] == 0
    # inline rules extend the library
    inline = absorb(1).to_json()
    host = instance(absorb(1), {})
    out = rw.apply(host, absorb(1), identity_matching(absorb(1), {}))
    r = d.verify_bytes(payload({
        "start": host.to_json(), "end": out.to_json(), "rules": [inline],
        "steps": [{"rule": "absorb_1", "matching": identity_matching(absorb(1), {}).to_json()}]}))
    assert r.verdict is Verdict.PASS
    s = MANIFEST.verifiers["zx_semantic_equal"](tmp_path)
    r = s.verify_bytes(payload({"a": wire().to_json(), "b": bell().to_json()}))
    assert r.verdict is Verdict.FAIL and "wire" in r.details["detail"]
    c = MANIFEST.verifiers["zx_critical_pairs"](tmp_path)
    r = c.verify_bytes(payload({"rules": ["fusion_x", "colour_change"], "depth": 2}))
    assert r.verdict is Verdict.FAIL and {r.details["rule1"], r.details["rule2"]} == {
        "fusion_x", "colour_change"}
    r = c.verify_bytes(payload({"rules": ["fusion", "identity_z"], "depth": 1,
                                "fragment": "clifford", "star_legs": 0}))
    assert r.verdict is Verdict.PASS and r.details["overlaps"] > 0
    t = MANIFEST.verifiers["zx_termination"](tmp_path)
    r = t.verify_bytes(payload({"rules": ["fusion", "colour_change"], "measure": ["vertices"]}))
    assert r.verdict is Verdict.FAIL and r.details["rule"] == "colour_change"


def test_run_reads_the_evidence_file_from_the_repository(tmp_path):
    v = MANIFEST.verifiers["zx_semantic_equal"](tmp_path)
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / "hh.json").write_bytes(
        payload({"a": wire().to_json(), "b": wire().to_json()}))
    assert v.run("evidence/hh.json").verdict is Verdict.PASS
    assert v.run("evidence/missing.json").verdict is Verdict.ERROR
    assert set(vf.GOLDEN_DIR.glob("*.json")) >= {
        vf.GOLDEN_DIR / f"{c.label}.json" for c in v.golden_suite()}

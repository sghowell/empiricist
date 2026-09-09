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

"""Tests for the GraphState representation and its three equivalent views."""

from dataclasses import FrozenInstanceError

import numpy as np
import pytest
import stim

from empiricist.domain.p5.graphstate import GraphState


def test_from_edges_roundtrips_to_adjacency():
    gs = GraphState(n=3, edges=[(0, 1), (1, 2)])
    A = gs.adjacency()
    assert A.shape == (3, 3)
    # symmetric, zero diagonal, edges present
    assert np.array_equal(A, A.T) and np.trace(A) == 0
    assert A[0, 1] == 1 and A[1, 2] == 1 and A[0, 2] == 0


def test_adjacency_is_gf2_valued():
    gs = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3), (3, 0)])  # C_4
    A = gs.adjacency()
    assert A.dtype == np.uint8
    assert set(np.unique(A).tolist()) <= {0, 1}


def test_from_adjacency_roundtrips():
    gs = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3), (3, 0)])
    gs2 = GraphState.from_adjacency(gs.adjacency())
    assert gs == gs2


def test_neighbors():
    gs = GraphState(n=4, edges=[(0, 1), (0, 2), (0, 3)])  # star centred at 0
    assert gs.neighbors(0) == frozenset({1, 2, 3})
    assert gs.neighbors(1) == frozenset({0})


def test_stabilizers_have_correct_form():
    """Star K_{1,2} (path 1-0-2): center 0 stabilizer = X0 Z1 Z2; leaf 1 = Z0 X1.

    Robust structural check (per stim 1.16, verified empirically): a PauliString's
    per-qubit Pauli type is read back as an int via ps[q] (0=I, 1=X, 2=Y, 3=Z), and
    `ps.pauli_indices("X"/"Z")` lists the qubits carrying that type. We use these
    rather than brittle string-form equality.
    """
    gs = GraphState(n=3, edges=[(0, 1), (0, 2)])
    stabs = gs.stabilizers()
    assert len(stabs) == 3

    PAULI_INT = {"_": 0, "X": 1, "Y": 2, "Z": 3}
    for v in range(3):
        p = stabs[v]
        assert len(p) == 3
        for q in range(3):
            if q == v:
                expected = "X"
            elif q in gs.neighbors(v):
                expected = "Z"
            else:
                expected = "_"
            assert p[q] == PAULI_INT[expected], (
                f"vertex {v}, qubit {q}: expected {expected}, got pauli index {p[q]}"
            )
        # cross-check via pauli_indices too
        assert p.pauli_indices("X") == [v]
        assert set(p.pauli_indices("Z")) == set(gs.neighbors(v))
        assert p.pauli_indices("Y") == []


def test_stim_state_matches_stabilizers():
    """The stim circuit for |G> must yield exactly the graph-state stabilizer group.

    Rigorous mechanism (two independent state-prep routes, compared via stim's own
    state-equality oracle):

    Route A: apply_state_prep (H on every qubit, then CZ per edge) on a fresh
    TableauSimulator.

    Route B: stim.TableauSimulator.set_state_from_stabilizers(declared), with
    allow_redundant=False and allow_underconstrained=False (the defaults). This
    call *itself* raises ValueError unless the declared generators are mutually
    commuting, non-contradictory, AND form a complete independent generating set
    for an n-qubit state -- so a successful call already certifies the declared
    generators are a valid, complete stabilizer generating set.

    Per stim's own documented guarantee: "Two simulators have the same canonical
    stabilizers if and only if their current quantum state is equal." So if
    canonical_stabilizers() from Route A and Route B match, the state prepared by
    H^n + CZ/edge is *exactly* the state stabilized by the declared generators --
    i.e. state == stabilizer-group, not merely a shape/count check.
    """
    gs = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])  # path P_4
    declared = gs.stabilizers()

    sim_a = stim.TableauSimulator()
    gs.apply_state_prep(sim_a)
    canon_a = sim_a.canonical_stabilizers()

    sim_b = stim.TableauSimulator()
    # Raises ValueError if declared is not independent/complete/consistent.
    sim_b.set_state_from_stabilizers(declared)
    canon_b = sim_b.canonical_stabilizers()

    assert len(canon_a) == gs.n
    assert len(canon_b) == gs.n
    assert [str(s) for s in canon_a] == [str(s) for s in canon_b]

    # Belt-and-braces: each declared generator individually has +1 expectation on
    # the H^n+CZ-prepared state (i.e. each declared generator does stabilize it).
    for p in declared:
        assert sim_a.peek_observable_expectation(p) == 1


def test_stim_state_matches_stabilizers_disconnected_and_isolated_vertex():
    """Same cross-check on a graph with an isolated vertex and a disjoint edge."""
    gs = GraphState(n=3, edges=[(0, 1)])  # vertex 2 isolated
    declared = gs.stabilizers()

    sim_a = stim.TableauSimulator()
    gs.apply_state_prep(sim_a)
    canon_a = sim_a.canonical_stabilizers()

    sim_b = stim.TableauSimulator()
    sim_b.set_state_from_stabilizers(declared)
    canon_b = sim_b.canonical_stabilizers()

    assert [str(s) for s in canon_a] == [str(s) for s in canon_b]


def test_equal_graphstates_compare_equal():
    a = GraphState(n=3, edges=[(0, 1), (1, 2)])
    b = GraphState(n=3, edges=[(1, 2), (0, 1)])  # same edges, different order
    assert a == b and hash(a) == hash(b)


def test_unequal_graphstates_compare_unequal():
    a = GraphState(n=3, edges=[(0, 1), (1, 2)])
    b = GraphState(n=3, edges=[(0, 1), (0, 2)])
    assert a != b


def test_frozen_and_immutable():
    gs = GraphState(n=3, edges=[(0, 1)])
    with pytest.raises(FrozenInstanceError):
        gs.n = 5  # type: ignore[misc]


def test_rejects_self_loops_and_out_of_range():
    with pytest.raises(ValueError):
        GraphState(n=3, edges=[(0, 0)])
    with pytest.raises(ValueError):
        GraphState(n=3, edges=[(0, 3)])

"""Engine A (stim) fusion goldens. A wrong fusion rule MUST fail these."""

import pytest

from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.fusion_stim import StimEngine
from empiricist.domain.p5.graphstate import GraphState


@pytest.fixture()
def eng():
    return StimEngine()


def star(center, leaves, n):
    return GraphState(n=n, edges=[(center, leaf) for leaf in leaves])


def test_roundtrip_no_fusion(eng):
    """state_from_graph then to_graphstate must return the same LC orbit."""
    for gs in [
        GraphState(n=3, edges=[(0, 1), (0, 2)]),
        GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)]),
        GraphState(n=5, edges=[(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)]),  # C_5
    ]:
        st = eng.state_from_graph(gs)
        out = eng.to_graphstate(st)
        assert lc_orbit_key(out) == lc_orbit_key(gs)


def test_ghz3_pair_fusion_gives_p4(eng):
    """THE core golden: star3 x star3 fused leaf-leaf -> P4 (F(P4)=1 witness)."""
    # qubits 0,1,2 = star(0;1,2); qubits 3,4,5 = star(3;4,5)
    two = GraphState(n=6, edges=[(0, 1), (0, 2), (3, 4), (3, 5)])
    st = eng.state_from_graph(two)
    st = eng.fuse(st, 2, 4)     # fuse leaf 2 with leaf 4
    out = eng.to_graphstate(st)
    p4 = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    assert lc_orbit_key(out) == lc_orbit_key(p4)


def test_disjoint_leaf_fusion_matches_complete_bipartite_rule(eng):
    """For disjoint components, {XX,ZZ} fusion = connect N(a) x N(b), delete a,b."""
    # star(0;1,2,3) + star(4;5,6): fuse leaf 3 with leaf 5
    g = GraphState(n=7, edges=[(0, 1), (0, 2), (0, 3), (4, 5), (4, 6)])
    st = eng.state_from_graph(g)
    st = eng.fuse(st, 3, 5)
    out = eng.to_graphstate(st)
    # expected: N(3)={0}, N(5)={4} -> edge 0-4; remaining qubits 0,1,2,4,6 -> relabel
    expected = GraphState(n=5, edges=[(0, 1), (0, 2), (0, 3), (3, 4)])
    assert lc_orbit_key(out) == lc_orbit_key(expected)


@pytest.mark.parametrize("g", [3, 4, 5, 6])
def test_ghz3_chain_gives_path(eng, g):
    """Chaining g GHZ3 stars with g-1 leaf fusions yields P_{g+2}: the
    F(path_N)=N-3 achievability witness."""
    n = 3 * g
    edges = []
    for i in range(g):
        c = 3 * i
        edges += [(c, c + 1), (c, c + 2)]
    st = eng.state_from_graph(GraphState(n=n, edges=edges))
    for i in range(g - 1):
        st = eng.fuse(st, 3 * i + 2, 3 * (i + 1) + 1)   # leaf of i with leaf of i+1
    out = eng.to_graphstate(st)
    path = GraphState(n=g + 2, edges=[(i, i + 1) for i in range(g + 1)])
    assert lc_orbit_key(out) == lc_orbit_key(path)


def test_intra_component_fusion_works(eng):
    """Fusing two qubits of the SAME component must not crash (needed for cycles)."""
    # P_6, fuse the two endpoint qubits: the Bell measurement splices the chain's
    # ends together, folding the path into a cycle over the 4 interior qubits -> C_4.
    # Pinning the orbit: the engine extracts exactly C_4, and C_4 is LC-equivalent
    # to P_4 (n=4 has two connected LC orbits -- star/GHZ vs path -- and C_4's
    # lc_orbit membership list contains 3-edge paths, verified empirically), so
    # this pin is a real discriminator: the star/GHZ orbit would fail it.
    p6 = GraphState(n=6, edges=[(i, i + 1) for i in range(5)])
    st = eng.state_from_graph(p6)
    st = eng.fuse(st, 0, 5)
    out = eng.to_graphstate(st)
    assert out.n == 4   # 6 - 2
    c4 = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3), (0, 3)])
    assert lc_orbit_key(out) == lc_orbit_key(c4)


def test_fuse_is_functional_input_state_reusable(eng):
    """Branching consumers (the M5c BFS) fan out multiple fusions from ONE state:
    fuse must not corrupt its input.

    The center-center branch is the real discriminator: an in-place-mutating
    fuse survives the leaf-leaf branches by accidental orbit collision (checked
    against a deliberately-broken engine), but its fourth branch here yields a
    single stray edge instead of K_{2,2}."""
    two = GraphState(n=6, edges=[(0, 1), (0, 2), (3, 4), (3, 5)])
    st0 = eng.state_from_graph(two)
    out_a = eng.to_graphstate(eng.fuse(st0, 2, 4))
    out_b = eng.to_graphstate(eng.fuse(st0, 2, 5))   # branch from the SAME st0
    out_a2 = eng.to_graphstate(eng.fuse(st0, 2, 4))  # repeat the first branch
    assert lc_orbit_key(out_a) == lc_orbit_key(out_a2)  # deterministic, uncorrupted
    p4 = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    assert lc_orbit_key(out_a) == lc_orbit_key(p4)      # still the golden result
    assert lc_orbit_key(out_b) == lc_orbit_key(p4)      # the sibling branch too
    # center-center branch: N(0)={1,2}, N(3)={4,5} disjoint -> complete bipartite
    # {1,2}x{4,5} = K_{2,2} = C_4 (LC-equivalent to P_4, same n=4 path orbit)
    out_cc = eng.to_graphstate(eng.fuse(st0, 0, 3))
    c4 = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3), (0, 3)])
    assert lc_orbit_key(out_cc) == lc_orbit_key(c4)


def test_extraction_gf2_fallback_path(eng, monkeypatch):
    """Force the fallback splitter and confirm a golden still holds."""
    import empiricist.domain.p5.fusion_stim as fs

    monkeypatch.setattr(fs, "_fast_split", lambda *a, **k: None)
    two = GraphState(n=6, edges=[(0, 1), (0, 2), (3, 4), (3, 5)])
    st = eng.fuse(eng.state_from_graph(two), 2, 4)
    out = eng.to_graphstate(st)
    p4 = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    assert lc_orbit_key(out) == lc_orbit_key(p4)


def test_fuse_rejects_bad_qubits(eng):
    gs = GraphState(n=4, edges=[(0, 1), (2, 3)])
    st = eng.state_from_graph(gs)
    with pytest.raises(ValueError):
        eng.fuse(st, 0, 0)          # same qubit
    st2 = eng.fuse(st, 1, 2)
    with pytest.raises(ValueError):
        eng.fuse(st2, 1, 3)         # 1 is no longer active


def test_fusion_reduces_qubits_by_two(eng):
    gs = GraphState(n=6, edges=[(0, 1), (0, 2), (3, 4), (3, 5)])
    st = eng.state_from_graph(gs)
    assert len(st.active) == 6
    st = eng.fuse(st, 2, 4)
    assert len(st.active) == 4

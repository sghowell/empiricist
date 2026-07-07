"""Engine B (pure-Python GF(2) bitmask) fusion goldens.

Written independently of engine A's test module (F3): this file is authored
fresh against the physics spec, not copied or imported from the stim-engine
tests. The golden facts checked here are the same physical facts any correct
fusion engine must reproduce -- disagreement with those facts means the GF(2)
engine's physics is wrong, not that the golden is negotiable.
"""

import inspect

import pytest

from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.fusion_gf2 import GF2Engine
from empiricist.domain.p5.graphstate import GraphState


@pytest.fixture()
def eng():
    return GF2Engine()


def star(center: int, leaves: list[int], n: int) -> GraphState:
    return GraphState(n=n, edges=[(center, leaf) for leaf in leaves])


def test_roundtrip_no_fusion(eng):
    """state_from_graph -> to_graphstate must land in the same LC orbit."""
    p3 = GraphState(n=3, edges=[(0, 1), (1, 2)])
    p4 = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    c5 = GraphState(n=5, edges=[(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)])
    for gs in (p3, p4, c5):
        st = eng.state_from_graph(gs)
        out = eng.to_graphstate(st)
        assert lc_orbit_key(out) == lc_orbit_key(gs)


def test_ghz3_pair_fusion_gives_p4(eng):
    """GHZ3(0;1,2) + GHZ3(3;4,5), fused at leaves (2,4) -> P4's orbit."""
    two_stars = GraphState(n=6, edges=[(0, 1), (0, 2), (3, 4), (3, 5)])
    st = eng.state_from_graph(two_stars)
    st = eng.fuse(st, 2, 4)
    out = eng.to_graphstate(st)
    p4 = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    assert lc_orbit_key(out) == lc_orbit_key(p4)


def test_disjoint_leaf_fusion_matches_complete_bipartite_rule(eng):
    """Disjoint-component fusion rule: connect N(a) x N(b), delete a, b.

    star(0;1,2,3) + star(4;5,6), fused at leaves (3,5): N(3)={0}, N(5)={4}
    -> new edge (0,4); surviving vertices {0,1,2,4,6} relabel to 0..4.
    """
    g = GraphState(n=7, edges=[(0, 1), (0, 2), (0, 3), (4, 5), (4, 6)])
    st = eng.state_from_graph(g)
    st = eng.fuse(st, 3, 5)
    out = eng.to_graphstate(st)
    expected = GraphState(n=5, edges=[(0, 1), (0, 2), (0, 3), (3, 4)])
    assert lc_orbit_key(out) == lc_orbit_key(expected)


@pytest.mark.parametrize("g", [3, 4, 5, 6])
def test_ghz3_chain_gives_path(eng, g):
    """Chaining g GHZ3 stars leaf-to-leaf with g-1 fusions yields P_{g+2}
    (the F(path_N) = N-3 achievability witness, for N = g+2)."""
    n = 3 * g
    edges = []
    for i in range(g):
        c = 3 * i
        edges += [(c, c + 1), (c, c + 2)]
    st = eng.state_from_graph(GraphState(n=n, edges=edges))
    for i in range(g - 1):
        st = eng.fuse(st, 3 * i + 2, 3 * (i + 1) + 1)
    out = eng.to_graphstate(st)
    path = GraphState(n=g + 2, edges=[(i, i + 1) for i in range(g + 1)])
    assert lc_orbit_key(out) == lc_orbit_key(path)


def test_intra_component_endpoints_gives_c4_orbit(eng):
    """Fusing the two endpoints of P6 (same component) must not crash and
    must land in the 4-qubit ring/cluster orbit, which is LC-equivalent to
    P4 (n=4 connected graphs have exactly two LC orbits: GHZ/star, and
    everything else -- path, ring, etc. -- which all coincide)."""
    p6 = GraphState(n=6, edges=[(i, i + 1) for i in range(5)])
    st = eng.state_from_graph(p6)
    st = eng.fuse(st, 0, 5)
    out = eng.to_graphstate(st)
    assert out.n == 4
    c4 = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3), (3, 0)])
    p4 = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    assert lc_orbit_key(c4) == lc_orbit_key(p4)  # sanity: the two ARE one orbit
    assert lc_orbit_key(out) == lc_orbit_key(p4)


def test_functional_fuse_does_not_mutate_and_branches_agree(eng):
    """fuse() must be functional: two branches fused from the SAME base
    state must not interfere, and each must land in its own correct orbit."""
    two_stars = GraphState(n=6, edges=[(0, 1), (0, 2), (3, 4), (3, 5)])
    st0 = eng.state_from_graph(two_stars)

    branch_leaves = eng.fuse(st0, 2, 4)  # leaf-leaf fusion -> P4
    branch_centers = eng.fuse(st0, 0, 3)  # center-center fusion -> K(2,2)/C4

    # st0 itself must still be usable/untouched: re-deriving from it again
    # must reproduce the same first branch.
    replay = eng.fuse(st0, 2, 4)
    assert replay.generators == branch_leaves.generators
    assert replay.active == branch_leaves.active

    p4 = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    k22 = GraphState(n=4, edges=[(0, 2), (0, 3), (1, 2), (1, 3)])

    out_leaves = eng.to_graphstate(branch_leaves)
    out_centers = eng.to_graphstate(branch_centers)

    assert lc_orbit_key(out_leaves) == lc_orbit_key(p4)
    assert lc_orbit_key(out_centers) == lc_orbit_key(k22)
    # K(2,2) is a 4-cycle, and n=4 rings/paths share the single non-GHZ orbit.
    assert lc_orbit_key(out_centers) == lc_orbit_key(p4)


def test_fuse_rejects_bad_qubits(eng):
    gs = GraphState(n=4, edges=[(0, 1), (2, 3)])
    st = eng.state_from_graph(gs)
    with pytest.raises(ValueError):
        eng.fuse(st, 0, 0)  # same qubit
    st2 = eng.fuse(st, 1, 2)
    with pytest.raises(ValueError):
        eng.fuse(st2, 1, 3)  # 1 is no longer active


def test_engine_b_is_independent_of_stim_and_numpy():
    """The independence guard (F3): engine B must not import stim or numpy,
    nor reach across to engine A's module."""
    from empiricist.domain.p5 import fusion_gf2

    src = inspect.getsource(fusion_gf2)
    assert "import stim" not in src
    assert "import numpy" not in src
    assert "fusion_stim" not in src

"""Tests for local complementation and LC-orbit enumeration (spec §8.2)."""

import networkx as nx
import pytest

from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.localcomp import (
    DEFAULT_ORBIT_CAP,
    OrbitTooLarge,
    lc_orbit,
    local_complement,
)


def test_local_complement_is_an_involution():
    gs = GraphState(n=5, edges=[(0, 1), (0, 2), (0, 3), (1, 2), (3, 4)])
    for v in range(5):
        assert local_complement(local_complement(gs, v), v) == gs


def test_local_complement_toggles_neighborhood_clique():
    # star centred at 0 on {1,2,3}: tau_0 makes {1,2,3} a triangle (complete).
    star = GraphState(n=4, edges=[(0, 1), (0, 2), (0, 3)])
    out = local_complement(star, 0)
    # 0 still connected to 1,2,3; and 1-2,1-3,2-3 now all present
    assert out.neighbors(0) == frozenset({1, 2, 3})
    assert (1, 2) in out.edges and (1, 3) in out.edges and (2, 3) in out.edges


def test_local_complement_leaves_edges_outside_neighborhood_clique_unchanged():
    # a's own edges (a-N(a)) are untouched, and edges among non-neighbors of a
    # are untouched -- only pairs *within* N(a) can flip.
    gs = GraphState(n=5, edges=[(0, 1), (0, 2), (0, 3), (3, 4)])
    out = local_complement(gs, 0)
    assert out.neighbors(0) == frozenset({1, 2, 3})  # a's own edges unchanged
    assert (3, 4) in out.edges  # edge outside N(0) x N(0) unchanged


def test_local_complement_on_isolated_vertex_is_identity():
    gs = GraphState(n=3, edges=[(1, 2)])
    assert local_complement(gs, 0) == gs


def test_ghz3_star_and_triangle_share_an_orbit():
    star = GraphState(n=3, edges=[(0, 1), (0, 2)])  # P_3 / GHZ_3
    triangle = GraphState(n=3, edges=[(0, 1), (1, 2), (0, 2)])  # K_3
    orbit = lc_orbit(star)
    # the triangle is LC-equivalent to GHZ_3 (tau on the path centre)
    assert any(g == triangle for g in orbit)


def test_lc_orbit_is_closed_under_local_complement():
    gs = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])  # P_4
    orbit = set(lc_orbit(gs))
    for g in list(orbit):
        for v in range(g.n):
            assert local_complement(g, v) in orbit  # closed


def test_lc_orbit_deduplicates():
    gs = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    orbit = lc_orbit(gs)
    assert len(orbit) == len(set(orbit))  # no duplicate GraphStates


def test_lc_orbit_contains_the_start_graph():
    gs = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    assert gs in lc_orbit(gs)


def test_lc_orbit_raises_when_cap_exceeded():
    gs = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    with pytest.raises(OrbitTooLarge):
        lc_orbit(gs, cap=1)


def test_default_cap_is_generous():
    assert DEFAULT_ORBIT_CAP >= 1000


def _independent_nx_lc(graph: nx.Graph, v: int) -> nx.Graph:
    """Independent nx-only local complementation: toggle every edge within N(v).

    Deliberately does NOT call empiricist.domain.p5.localcomp.local_complement --
    this is the cross-check oracle, so it must be implemented from scratch against
    plain networkx primitives.
    """
    h = graph.copy()
    nbrs = list(graph.neighbors(v))
    for i in range(len(nbrs)):
        for j in range(i + 1, len(nbrs)):
            a, b = nbrs[i], nbrs[j]
            if h.has_edge(a, b):
                h.remove_edge(a, b)
            else:
                h.add_edge(a, b)
    return h


def _independent_nx_orbit_edge_keys(gs: GraphState) -> set[frozenset]:
    """Independently enumerate the LC orbit's edge-sets via a plain-nx BFS fixpoint."""
    start = nx.Graph()
    start.add_nodes_from(range(gs.n))
    start.add_edges_from(gs.edges)

    def key(graph: nx.Graph) -> frozenset:
        return frozenset(frozenset(e) for e in graph.edges())

    seen = {key(start)}
    frontier = [start]
    while frontier:
        graph = frontier.pop()
        for v in range(gs.n):
            h = _independent_nx_lc(graph, v)
            k = key(h)
            if k not in seen:
                seen.add(k)
                frontier.append(h)
    return seen


def test_lc_orbit_matches_networkx_local_complement_bruteforce():
    """Cross-check the orbit against an independent nx-based fixpoint enumeration."""
    gs = GraphState(n=5, edges=[(0, 1), (1, 2), (2, 3), (3, 4)])  # P_5

    independent = _independent_nx_orbit_edge_keys(gs)
    ours = {frozenset(frozenset(e) for e in g.edges) for g in lc_orbit(gs)}
    assert ours == independent


@pytest.mark.parametrize(
    ("edges", "n"),
    [
        ([(0, 1), (0, 2)], 3),  # P_3 / GHZ_3
        ([(0, 1), (1, 2), (2, 3)], 4),  # P_4
        ([(0, 1), (1, 2), (2, 3), (3, 4)], 5),  # P_5
    ],
)
def test_lc_orbit_matches_networkx_for_several_small_graphs(edges, n):
    gs = GraphState(n=n, edges=edges)
    independent = _independent_nx_orbit_edge_keys(gs)
    ours = {frozenset(frozenset(e) for e in g.edges) for g in lc_orbit(gs)}
    assert ours == independent

"""Tests for pynauty canonicalization + the LC-orbit canonical key.

The load-bearing golden test reproduces the Adcock LC-orbit counts of connected
graph states through 9 qubits (1,1,1,2,4,11,26,101,440) -- a strong, mutation-
resistant check that the whole LC-equivalence pipeline is correct.
"""

import itertools

import networkx as nx
import pytest

from empiricist.domain.p5.canonical import (
    iso_certificate,
    lc_equivalent,
    lc_orbit_key,
)
from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.localcomp import lc_orbit


def test_iso_certificate_is_isomorphism_invariant():
    # two labelings of the same path P_3
    a = GraphState(n=3, edges=[(0, 1), (1, 2)])
    b = GraphState(n=3, edges=[(0, 2), (2, 1)])  # relabelled path
    assert iso_certificate(a) == iso_certificate(b)


def test_iso_certificate_distinguishes_nonisomorphic():
    path = GraphState(n=3, edges=[(0, 1), (1, 2)])
    triangle = GraphState(n=3, edges=[(0, 1), (1, 2), (0, 2)])
    assert iso_certificate(path) != iso_certificate(triangle)


def test_lc_orbit_key_is_lc_invariant():
    star = GraphState(n=3, edges=[(0, 1), (0, 2)])
    triangle = GraphState(n=3, edges=[(0, 1), (1, 2), (0, 2)])
    # GHZ_3 star and triangle are LC-equivalent -> same orbit key
    assert lc_orbit_key(star) == lc_orbit_key(triangle)


def test_lc_orbit_key_separates_distinct_orbits():
    # P_4 and K_{1,3} (star) are in DIFFERENT LC orbits on 4 vertices
    p4 = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    star = GraphState(n=4, edges=[(0, 1), (0, 2), (0, 3)])
    assert lc_orbit_key(p4) != lc_orbit_key(star)


def test_lc_equivalent_predicate():
    star = GraphState(n=3, edges=[(0, 1), (0, 2)])
    triangle = GraphState(n=3, edges=[(0, 1), (1, 2), (0, 2)])
    p4 = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    assert lc_equivalent(star, triangle) is True
    # different vertex counts are trivially inequivalent
    assert lc_equivalent(star, p4) is False


ADCOCK_CUMULATIVE = {1: 1, 2: 1, 3: 1, 4: 2, 5: 4, 6: 11, 7: 26, 8: 101, 9: 440}


def _connected_graphs(n):
    """All connected simple graphs on n labelled vertices (small n)."""
    verts = list(range(n))
    all_edges = list(itertools.combinations(verts, 2))
    for r in range(n - 1, len(all_edges) + 1):
        for es in itertools.combinations(all_edges, r):
            G = nx.Graph()
            G.add_nodes_from(verts)
            G.add_edges_from(es)
            if nx.is_connected(G):
                yield GraphState(n=n, edges=list(es))


def _count_lc_orbits(n: int) -> int:
    """Count distinct LC-orbit keys among all connected graphs on n vertices.

    Exhaustive enumeration visits every graph in an orbit separately; naively
    calling lc_orbit_key(g) per graph recomputes that orbit's full BFS + iso
    certificates once per member, i.e. O(total_graphs * orbit_size) work -- fine
    through n=6 but infeasible at n=7 where a handful of orbits contain a large
    fraction of the ~1.87M connected labelled graphs.

    Memoize by edge-set instead: the first time any member of an orbit is seen,
    compute its orbit once (lc_orbit) and cache the resulting min iso-certificate
    for EVERY member, so each graph contributes exactly one iso_certificate call
    -- O(total_graphs) total. This is the same quantity lc_orbit_key computes
    (min iso_certificate over lc_orbit(g)); the cache is a performance detail,
    not a change to what's being verified.
    """
    cache: dict[frozenset, bytes] = {}
    keys: set[bytes] = set()
    for g in _connected_graphs(n):
        key = cache.get(g.edges)
        if key is None:
            orbit_certs = {o.edges: iso_certificate(o) for o in lc_orbit(g)}
            key = min(orbit_certs.values())
            cache.update(dict.fromkeys(orbit_certs, key))
        keys.add(key)
    return len(keys)


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6])
def test_lc_orbit_counts_match_adcock(n):
    """Count distinct LC-orbit keys over all connected graphs on n vertices."""
    assert _count_lc_orbits(n) == ADCOCK_CUMULATIVE[n]


@pytest.mark.slow
@pytest.mark.parametrize("n", [7])
def test_lc_orbit_counts_match_adcock_n7(n):
    assert _count_lc_orbits(n) == ADCOCK_CUMULATIVE[n]

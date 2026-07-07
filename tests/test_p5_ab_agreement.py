"""A/B agreement fuzz: the two independent engines must produce the SAME
LC-orbit key for the same fusion sequence. Disagreement = one engine is wrong.

Per the plan's discipline: if any seed makes A and B disagree, or makes
either engine raise, that is the F3 mechanism firing (or a genuine physics
bug to report) -- the test itself is never adjusted to suppress a finding.
"""

import random

import pytest

from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.fusion_gf2 import GF2Engine
from empiricist.domain.p5.fusion_stim import StimEngine
from empiricist.domain.p5.graphstate import GraphState


def random_connected_graph(rng, n):
    while True:
        edges = [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < 0.5]
        gs = GraphState(n=n, edges=edges)
        import networkx as nx

        if nx.is_connected(gs.to_networkx()):
            return gs


@pytest.mark.parametrize("seed", range(20))
def test_ab_agree_on_random_single_fusions(seed):
    rng = random.Random(seed)
    n = rng.randint(4, 7)
    gs = random_connected_graph(rng, n)
    a, b = rng.sample(range(n), 2)
    ea, eb = StimEngine(), GF2Engine()
    out_a = ea.to_graphstate(ea.fuse(ea.state_from_graph(gs), a, b))
    out_b = eb.to_graphstate(eb.fuse(eb.state_from_graph(gs), a, b))
    assert lc_orbit_key(out_a) == lc_orbit_key(out_b), (
        f"A/B DISAGREE on seed={seed} gs={sorted(gs.edges)} fuse=({a},{b})"
    )


@pytest.mark.parametrize("seed", range(10))
def test_ab_agree_on_multi_fusion_sequences(seed):
    rng = random.Random(1000 + seed)
    # two disjoint stars + extra edges, then 2 sequential fusions on random actives
    gs = GraphState(n=8, edges=[(0, 1), (0, 2), (0, 3), (4, 5), (4, 6), (4, 7)])
    ea, eb = StimEngine(), GF2Engine()
    sa, sb = ea.state_from_graph(gs), eb.state_from_graph(gs)
    active = list(range(8))
    for _ in range(2):
        a, b = rng.sample(active, 2)
        sa, sb = ea.fuse(sa, a, b), eb.fuse(sb, a, b)
        active.remove(a)
        active.remove(b)
    assert lc_orbit_key(ea.to_graphstate(sa)) == lc_orbit_key(eb.to_graphstate(sb))

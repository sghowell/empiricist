"""The move kernel (M5c Task 1): merge_fresh_ghz3, intra_fuse,
local_complements. The closed form is trusted ONLY because of the fuzz
below -- per the plan's discipline, a disagreement means the closed form is
wrong (fix it, never weaken the fuzz).
"""

import random

import networkx as nx
import pytest

from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.fusion_gf2 import GF2Engine
from empiricist.domain.p5.fusion_stim import StimEngine
from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.moves import intra_fuse, local_complements, merge_fresh_ghz3


def random_connected_graph(rng, n):
    while True:
        edges = [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < 0.5]
        gs = GraphState(n=n, edges=edges)
        if nx.is_connected(gs.to_networkx()):
            return gs


@pytest.mark.parametrize("seed", range(25))
def test_merge_rule_matches_both_engines_fuzz(seed):
    """The closed form's ONLY warrant: for a random blob and a random fusion
    qubit/role, merge_fresh_ghz3 must match what BOTH engines produce for
    the same fusion applied to blob (x) fresh-GHZ3-star."""
    rng = random.Random(seed)
    n = rng.randint(4, 7)
    blob = random_connected_graph(rng, n)
    a = rng.randrange(n)
    role = rng.choice(["center", "leaf"])
    closed_form = merge_fresh_ghz3(blob, a, role)

    # fresh GHZ3 star: center n, leaves n+1, n+2 (disjoint from the blob)
    combined = GraphState(n=n + 3, edges=set(blob.edges) | {(n, n + 1), (n, n + 2)})
    b = n if role == "center" else n + 1

    for eng in (StimEngine(), GF2Engine()):
        state = eng.fuse(eng.state_from_graph(combined), a, b)
        out = eng.to_graphstate(state)
        assert lc_orbit_key(out) == lc_orbit_key(closed_form), (
            f"seed={seed} n={n} a={a} role={role} engine={type(eng).__name__} "
            f"blob={sorted(blob.edges)}: closed form disagrees with the engine"
        )


@pytest.mark.parametrize("seed", range(15))
def test_commutation_L1(seed):
    """L1 (single-blob WLOG): two disjoint fusion pairs (qubit-disjoint, so
    their measurements commute) applied in EITHER order, on EITHER engine,
    must land in the same LC orbit."""
    rng = random.Random(2000 + seed)
    n1 = rng.randint(3, 4)
    n2 = rng.randint(3, 4)
    blob1 = random_connected_graph(rng, n1)
    blob2 = random_connected_graph(rng, n2)
    edges2 = {(u + n1, v + n1) for u, v in blob2.edges}
    combined = GraphState(n=n1 + n2, edges=set(blob1.edges) | edges2)

    pool1 = list(range(n1))
    pool2 = list(range(n1, n1 + n2))
    rng.shuffle(pool1)
    rng.shuffle(pool2)
    pair1 = (pool1[0], pool2[0])
    pair2 = (pool1[1], pool2[1])

    for eng_cls in (StimEngine, GF2Engine):
        forward = eng_cls()
        s_fwd = forward.fuse(forward.fuse(forward.state_from_graph(combined), *pair1), *pair2)
        backward = eng_cls()
        s_bwd = backward.fuse(
            backward.fuse(backward.state_from_graph(combined), *pair2), *pair1
        )
        key_fwd = lc_orbit_key(forward.to_graphstate(s_fwd))
        key_bwd = lc_orbit_key(backward.to_graphstate(s_bwd))
        assert key_fwd == key_bwd, (
            f"seed={seed} engine={eng_cls.__name__} pair1={pair1} pair2={pair2}: "
            "fusion order changed the orbit"
        )


@pytest.mark.parametrize("seed", range(10))
def test_intra_fuse_agrees_with_stim(seed):
    rng = random.Random(3000 + seed)
    n = rng.randint(4, 7)
    gs = random_connected_graph(rng, n)
    a, b = rng.sample(range(n), 2)

    out_intra = intra_fuse(gs, a, b)

    eng = StimEngine()
    out_stim = eng.to_graphstate(eng.fuse(eng.state_from_graph(gs), a, b))

    assert lc_orbit_key(out_intra) == lc_orbit_key(out_stim)


def test_merge_golden_p4():
    """star3 blob (center 0, leaves 1,2), fuse a leaf with a fresh star's
    leaf -> P4 (the M5b golden, through the closed form)."""
    blob = GraphState(n=3, edges=[(0, 1), (0, 2)])
    out = merge_fresh_ghz3(blob, a=1, role="leaf")
    target = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    assert lc_orbit_key(out) == lc_orbit_key(target)


@pytest.mark.parametrize("k", range(1, 6))
def test_mod3_invariant_smoke(k):
    """L3 shape: a chain of k merges from GHZ3 always lands at size 3+k,
    having used exactly k fusions (= N-3)."""
    blob = GraphState(n=3, edges=[(0, 1), (0, 2)])
    for _ in range(k):
        blob = merge_fresh_ghz3(blob, a=blob.n - 1, role="leaf")
    assert blob.n == 3 + k


def test_local_complements_yields_tau_at_every_vertex():
    gs = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    from empiricist.domain.p5.localcomp import local_complement

    expected = [local_complement(gs, v) for v in range(gs.n)]
    assert list(local_complements(gs)) == expected

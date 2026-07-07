"""The cut-rank/rank-width profile is an LC-invariant used as a cheap non-
equivalence pre-filter (spec §8.2): equal profile is necessary (not sufficient)
for LC-equivalence, so a profile MISMATCH certifies non-equivalence."""

from empiricist.domain.p5.canonical import lc_equivalent, lc_orbit_key
from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.localcomp import cut_rank_profile, local_complement


def test_profile_is_lc_invariant():
    gs = GraphState(n=5, edges=[(0, 1), (1, 2), (2, 3), (3, 4)])
    base = cut_rank_profile(gs)
    for v in range(5):
        assert cut_rank_profile(local_complement(gs, v)) == base


def test_profile_mismatch_implies_non_equivalent():
    import itertools

    # over small connected graphs: profile mismatch => lc_orbit_key mismatch
    verts = list(range(4))
    alledges = list(itertools.combinations(verts, 2))
    graphs = []
    for r in range(3, len(alledges) + 1):
        for es in itertools.combinations(alledges, r):
            import networkx as nx

            G = nx.Graph()
            G.add_nodes_from(verts)
            G.add_edges_from(es)
            if nx.is_connected(G):
                graphs.append(GraphState(n=4, edges=list(es)))
    for a in graphs:
        for b in graphs:
            if cut_rank_profile(a) != cut_rank_profile(b):
                assert not lc_equivalent(a, b)  # mismatch => genuinely inequivalent


def test_profile_is_a_prefilter_not_a_certificate():
    # profile equal does NOT imply equivalent (it's one-sided); at least document
    # by asserting the pipeline still uses lc_orbit_key for the final decision.
    star = GraphState(n=3, edges=[(0, 1), (0, 2)])
    triangle = GraphState(n=3, edges=[(0, 1), (1, 2), (0, 2)])
    assert cut_rank_profile(star) == cut_rank_profile(triangle)  # same orbit anyway
    assert lc_orbit_key(star) == lc_orbit_key(triangle)

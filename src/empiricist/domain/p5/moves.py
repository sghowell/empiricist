"""The move kernel (M5c Task 1): pure graph-level rewrites for the Tier-0/
Tier-1 tablebase search (plan lemmas L1/L3), fast because they never invoke a
stabilizer tableau in the hot loop.

`merge_fresh_ghz3` is the closed-form disjoint-fusion graph rewrite (the
complete-bipartite rule M5b's goldens already proved for the P4/chain cases);
it is trusted ONLY because `tests/test_p5_moves.py::test_merge_rule_matches_
both_engines_fuzz` validates it against BOTH independent fusion engines on
randomized cases -- if that fuzz ever disagrees, the closed form is wrong
(the engines, not this module, are the certified authority; see the plan's
Task 1 Step 4).

`intra_fuse` (same-component fusion) has no trusted closed form -- unlike a
disjoint merge, folding two qubits of the SAME component depends on the
detailed stabilizer structure connecting them, not just their neighbor sets
-- so it delegates to GF2Engine (certified in M5b) and extracts. Not the hot
path: Tier-1 allows at most a handful of intra fusions per schedule (plan
L4).

`local_complements` is the 0-cost move iterator consumed by the tablebase's
0-1 BFS (plan's "Search-space consequence": LC orbits fall out as the 0-edge
connected components of the search graph, so `lc_orbit_key` never needs to
run in the hot loop).
"""

from __future__ import annotations

from collections.abc import Iterator

from empiricist.domain.p5.fusion_gf2 import GF2Engine
from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.localcomp import local_complement


def merge_fresh_ghz3(gs: GraphState, a: int, role: str) -> GraphState:
    """Fuse blob qubit `a` with a FRESH GHZ3 star (center + 2 leaves) at
    `role` ("center" fuses `a` to the fresh star's center; "leaf" fuses `a`
    to one of the fresh star's leaves).

    Closed form (disjoint fusion, M5b-proven complete-bipartite rewrite):
    new vertex set = (blob \\ {a}) union the 2 surviving fresh qubits; new
    edges = (blob edges not touching `a`) union the fresh star's surviving
    internal edge (only when role == "leaf": the center-to-other-leaf edge;
    when role == "center" both leaves survive but were never adjacent to
    each other, so there is no surviving internal edge) union the complete
    bipartite N_blob(a) x N_fresh(b), where N_fresh(b) is "both leaves" for
    role == "center" (b, the fused fresh qubit, is the center) or "the
    center" for role == "leaf" (b is a leaf, whose only fresh-neighbor is
    the center).

    Deterministic relabeling: blob qubits keep their id, compacted to close
    the gap left by removing `a` (q -> q if q < a else q - 1); the 2
    surviving fresh qubits get the next two ids, gs.n - 1 and gs.n (in that
    fixed order) -- so the result has gs.n + 1 qubits (remove 1, add 2, net
    +1, matching L3's "component size grows by 1 per merge").

    ONLY TRUSTED because of `test_merge_rule_matches_both_engines_fuzz` in
    tests/test_p5_moves.py -- if the fuzz disagrees with the engines, THE
    CLOSED FORM IS WRONG (fix it, never the fuzz).
    """
    if not (0 <= a < gs.n):
        raise ValueError(f"a={a} out of range for gs.n={gs.n}")
    if role not in ("center", "leaf"):
        raise ValueError(f"role must be 'center' or 'leaf', got {role!r}")

    blob_nbrs = gs.neighbors(a)
    compact = {q: (q if q < a else q - 1) for q in range(gs.n) if q != a}
    survivor1, survivor2 = gs.n - 1, gs.n  # the 2 surviving fresh qubits' new ids

    if role == "center":
        # b (fused) is the fresh center: its fresh-neighbors are BOTH leaves;
        # the two leaves were never adjacent to each other -- no surviving
        # internal edge.
        fresh_nbrs_of_b = {survivor1, survivor2}
        internal_edges: set[tuple[int, int]] = set()
    else:
        # b (fused) is a fresh leaf: its only fresh-neighbor is the center
        # (-> survivor1); the OTHER leaf (survivor2) keeps its center-leaf edge.
        fresh_nbrs_of_b = {survivor1}
        internal_edges = {(survivor1, survivor2)}

    kept_edges = {(compact[u], compact[v]) for u, v in gs.edges if a not in (u, v)}
    bipartite_edges = {(u, v) for u in (compact[x] for x in blob_nbrs) for v in fresh_nbrs_of_b}
    new_edges = kept_edges | bipartite_edges | internal_edges
    return GraphState(n=gs.n + 1, edges=new_edges)


def intra_fuse(gs: GraphState, a: int, b: int) -> GraphState:
    """Fuse two qubits `a`, `b` of the SAME connected component.

    No trusted closed form exists for the general same-component case
    (unlike `merge_fresh_ghz3`'s disjoint case) -- delegate to GF2Engine
    (certified in M5b via EnumFusionVerifier) and extract. Not the hot path:
    Tier-1 allows at most a handful of these per schedule (plan L4)."""
    engine = GF2Engine()
    state = engine.state_from_graph(gs)
    state = engine.fuse(state, a, b)
    return engine.to_graphstate(state)


def local_complements(gs: GraphState) -> Iterator[GraphState]:
    """The 0-cost search edges from `gs`: tau_v(gs) for every vertex v
    (Bouchet local complementation, spec Sec 8.2) -- the moves the tablebase
    BFS walks for free."""
    for v in range(gs.n):
        yield local_complement(gs, v)

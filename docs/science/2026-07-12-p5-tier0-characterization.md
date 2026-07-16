# P5: a structural characterization of the minimum-fusion extremal class

> **CORRECTION / SPEC NOTE (2026-07-15):** this note's hypothesis was Opus-authored
> (out of spec). Fable-5 has since independently re-generated it from the data — see
> `2026-07-15-p5-dh-characterization-fable.md`. Also: the exact/open split below is
> **175/410**, not 185/400 (arithmetic error; the characterization is unaffected).


**Date:** 2026-07-12 · **Problem:** P5(ii)/(iii), structure · **Method:** data-mining
the VERIFIED_N tablebase (585 LC-orbits, n≤9) for an LC-invariant characterizing
`F(G)=N−3`.

The universal lower bound is `F(G) ≥ N−3` (formalized: `fusion_cost_lower_bound`).
Which graph states *attain* it? This note gives a clean, fully-grounded answer via a
deep, well-studied graph-state complexity invariant.

## Main result (conjecture, grounded on all 585 orbits n≤9)

> **`F(G) = N − 3` ⟺ G is distance-hereditary (equivalently, rank-width 1).**

Checked on the entire tablebase: **175/175 exact rows** satisfy `F=N−3 ⟺ DH`, and
**0/410 open rows** (all proven `F > N−3`) are distance-hereditary. No exceptions.

Distance-hereditary graphs — those reducible to a point by repeatedly deleting
pendant vertices and twins, equivalently the graphs of **rank-width 1** — are a
classical vertex-minor-closed class. Rank-width (Oum–Seymour) is a local-
complementation invariant, exactly the right kind of quantity for an LC-orbit
property like `F`. The characterization says: **a graph state reaches the universal
minimum fusion count iff its entanglement structure is rank-width 1.**

### It unifies the formalized families

Every family we proved `F=N−3` for is distance-hereditary, which is *why* they attain
the bound: **paths, stars, complete graphs `K_N`, all trees, and all complete
bipartite `K_{m,n}`** are rank-width 1. The `tree_min_fusions` /
`completeBipartite_min_fusions` theorems are instances of this one structural law.
It also explains the earlier girth observation (short girth was a necessary-not-
sufficient shadow: distance-hereditary graphs forbid induced cycles ≥5, but the
converse fails).

## What is NOT true — rank-width does not determine F beyond the extremal class

The tempting generalization `F(G) = N − 3 + 3·(rank-width(G) − 1)` (making the mod-3
ladder tier equal `rw−1`) **is false.** It holds on all 175 exact rows (rank-width
pinned to 1 for Tier-0 via DH, to 2 for Tier-1 via not-DH + linear-rank-width 2), and
it correctly predicted two live results (the 2×4 cluster has `rw=2`→`F=N`, verified;
the n=6 beyond-frontier orbit has `rw=3`→`F=N+3`, verified). **But** there is an n=7
orbit that is **rank-width 2** (not distance-hereditary, linear-rank-width 2) yet has
proven `F ≥ N+3` — so `rw=2` does not force `F=N`. Rank-width sharply captures the
`F=N−3` boundary but *undercounts* the fusion tier above it; the higher tiers need a
finer invariant than rank-width. Honest negative result.

## Why the boundary is believable (a proof sketch, not yet a proof)

- **DH ⟹ F=N−3.** A distance-hereditary graph is built from a point by pendant and
  twin additions. Pendant additions are exactly the leaf-merges we formalized
  (`ghz3LeafMerge`); twin additions correspond to fusion moves that add a vertex
  without an intra-fusion. So a DH graph state admits an all-merge (Tier-0)
  construction of `N−3` fusions — the upper bound — matching the universal lower
  bound. (Formalizing this general direction would subsume all the family theorems
  into one; the pendant half is done, the twin half is the new work.)
- **F=N−3 ⟹ DH.** An all-merge (Tier-0) construction builds the graph by a tree of
  cross-component merges with no intra-fusion; the resulting cut-rank structure
  never exceeds 1, i.e. rank-width 1. A rank-2 obstruction would force an intra-
  fusion (`F ≥ N`). Making this rigorous is the rank-width lower-bound argument.

## Provenance & status

Grounded on the VERIFIED_N dataset (185 exact + 400 open orbits, all two-engine
certified) plus three live beyond-frontier closures. Computations: distance-
hereditary via pendant/twin pruning; rank-width bounds via the exact
distance-hereditary test (rw=1) and a linear-rank-width subset-DP upper bound
(`rw ≤ lrw`), both LC-invariant (verified across orbit members). This is a
**conjecture with a proof sketch**, not a theorem — the natural next steps are to
prove `DH ⟺ F=N−3` (and formalize it, generalizing the family theorems) and to find
the finer invariant governing the higher tiers.

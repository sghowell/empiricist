# P5: why DH ⟹ F=N−3 is unprovable in the current production model (a precise limit)

**Date:** 2026-07-16 · **Problem:** P5 formalization scope · **Method:** Fable strategist
(free-form) + deterministic LC-orbit checks on the 585-orbit tablebase.

## The question

Having formalized `F(G)=N−3` for five distance-hereditary (DH) families (paths, stars,
all trees, K_N, K_{m,n}) and shown deterministically that `F(G)=N−3 ⟺ G is DH` (rank-width 1)
on all 585 orbits, the natural capstone is the general **forward** direction
`DH ⟹ F=N−3` as one Lean theorem. This note reports why that theorem is **not reachable in
the current Lean production model** — and what would fix it.

## The airtight chain

1. **`ProducibleBy` graphs are exactly trees.** The base is `GHZ3graph = P₃` (a tree); the
   only growth constructor is `merge = ghz3LeafMerge ≃g addPendant` (attach a pendant —
   preserves tree-ness); `iso` only relabels. So every `ProducibleBy k` graph is a tree on
   `k+3` vertices.
2. Hence **`ProducibleUpToLC (N−3) G ⟺ G's local-complementation orbit contains a tree`**
   (`ProducibleUpToLC f H := ∃ G, ProducibleBy f G ∧ LCEquiv G H`, with `LCEquiv` = pure LC).
3. **Deterministic check** (uncapped LC-orbit enumeration, cap 200 000, 0 orbits truncated):
   of the 175 extremal (DH) orbits at n≤9, only **93 have a tree in their LC-orbit; 82 do
   not** (2 at n=6, 4 at n=7, 19 at n=8, 57 at n=9; orbit sizes 40–80).

**Therefore those 82 DH orbits are extremal (physical `F=N−3`, two-engine verified) yet are
NOT `ProducibleUpToLC(N−3)` in the Lean model. The general `DH ⟹ F=N−3` is false as stated
there — 82 explicit counterexamples.**

## Why the stepwise proof provably loops

Fable's strategist reduced `pendant_step : ProducibleUpToLC k G → ProducibleUpToLC (k+1)
(addPendant G u)` to a clean, formalizable **transport table**: for a fresh vertex ℓ and the
three attachments P (pendant), T₀ (false twin, ℓ~N(u)), T₁ (true twin, ℓ~N[u]),
`LC_v(attach c G u) = attach c'(LC_v G) u` with `c'=c` off `N[u]`, `T₀↔T₁` for `v∈N(u)`,
`P↔T₁` for `v=u`. Transporting a pendant across an `LC_u` step turns it into a **twin** —
this is exactly why the naive witness fails (star = P·P₃, but P₃~K₃ and paw = P·K₃ needs P₄).
The residual obligation collapses to "connected DH ⟹ LC-equivalent to a tree" — which the
82-orbit check **refutes** — and chasing the recursion, no size/degree measure decreases: the
lemma-by-lemma induction genuinely loops. No purely stepwise witness construction exists.

## Nothing is broken

- The five family theorems are correct: those families **are** LC-orbits of trees (K_N ~ star,
  K_{m,n} ~ double-star, etc.), which is *why* the pendant model reaches them.
- The universal lower bound `F ≥ N−3` is general (independent of `ProducibleBy`).
- The DH characterization `F=N−3 ⟺ DH` stands — it is about the **physical** `F` (engine-
  verified on 585 orbits), which the Lean `ProducibleUpToLC` under-approximates.

The precise statement: **Lean `ProducibleUpToLC` is a sound sub-model of physical `F` that
reaches exactly the LC-orbits of trees — a strict subset of the distance-hereditary graphs.**

## The principled fix (a new milestone)

Extend `ProducibleBy` with **true-twin-merge and false-twin-merge** constructors. By
Bandelt–Mulder, {pendant, true-twin, false-twin} closure of a point = exactly the DH graphs,
so the extended model would reach all of DH and `DH ⟹ F=N−3` would become a **direct
induction on the build** (each step = one constructor — no LC-witness gymnastics). Two
prerequisites, in the project's discipline:

1. **Engine justification** that a twin-merge is a genuine 1-fusion primitive up to LC, cross-
   checked on both fusion engines exactly as the D6 leaf-merge was (McKay 0/200, GF(2)≡stim).
   Open sub-question: for the non-tree-reducible cases the twin fusion is genuinely non-tree
   (C₄'s twin was realizable as leaf-merge+LC only because C₄~P₄).
2. **Re-establishing `F ≥ N−3`** for the extended constructor set (each merge is still +1
   vertex/+1 fusion, so the component-merge counting should carry over).

Until then, the concrete twin mechanism is proven for the smallest essential case
(`c4_producibleUpToLC`), and the general theorem awaits the model extension.

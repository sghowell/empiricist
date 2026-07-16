# P5: the DH forward direction, formalized — DH ⟹ F=N−3

**Date:** 2026-07-16 · **Problem:** P5(ii)/(iii), formalization · **Method:** Fable-authored
Lean 4 via the propose→gate→revise loop, on an engine-justified model extension.

## Result

`dh_min_fusions` (Fable-authored, gate-certified, axioms {propext, Classical.choice, Quot.sound}):

> For every distance-hereditary graph `G` on `N` vertices,
> `ProducibleByExt (N−3) G  ∧  (∀ schedule, N−3 ≤ f)` — i.e. **F(G) = N−3.**

Here `PendantTwinBuildable` is the Bandelt–Mulder distance-hereditary class (a connected
3-vertex core — `P₃` or `K₃` — closed under pendant, false-twin, and true-twin additions and
isomorphism), and `ProducibleByExt` is the extended fusion-production model. This is the
**forward direction** of the characterization `F(G)=N−3 ⟺ G distance-hereditary`.

## Why the current model couldn't do it, and the honest fix

An earlier note (`2026-07-16-p5-dh-forward-model-scope.md`) showed the general theorem is
*false* in the leaf-merge-only model: `ProducibleBy` graphs are exactly trees, so
`ProducibleUpToLC(N−3)` reaches only LC-orbits of trees, and 82 of the 175 distance-hereditary
orbits (n≤9) have no tree in their orbit. The obstruction was not a hard proof — it was a
**missing primitive**.

The fix was to add the primitive that was already engine-verified but never formalized: the
**center-role GHZ₃ fusion**, which produces a **false twin** (`ghz3CenterMerge`, proven iso to
`addFalseTwin`). Both fusion engines agree with it (400/400), and all 175 extremal orbits are
reachable by {leaf, center} merges + local complementation. The extended model is:

```
inductive ProducibleByExt : Nat → SimpleGraph V → Prop
  | base       : ProducibleByExt 0 GHZ3graph
  | leafMerge  : ProducibleByExt m G → ProducibleByExt (m+1) (ghz3LeafMerge G a)   -- pendant
  | centerMerge: ProducibleByExt m G → ProducibleByExt (m+1) (ghz3CenterMerge G a) -- false twin
  | lc         : ProducibleByExt m G → ProducibleByExt m (localComplement G v)      -- free Clifford
  | iso        : ProducibleByExt m G → G ≃g H → ProducibleByExt m H                 -- relabel
```

Every constructor is physically justified: a base resource, two two-engine-verified 1-fusion
primitives, free local Cliffords, and relabelling. `F ≥ N−3` is untouched (it is the abstract
`fusion_cost_lower_bound`, independent of which constructors exist).

## The architectural move: exact tracking beats the lifting obstruction

The naive induction is provably impossible: `P₃ ~_LC K₃` yet `addPendant(P₃,c)=star` is not
LC-equivalent to `addPendant(K₃,c)=paw`, so the `(k+1)`-witness cannot be "add a vertex to
`G`'s witness." The resolution is to **track the exact graph** through `ProducibleByExt`, with
`lc` as an *internal* constructor (local Cliffords are free), so the DH build maps to production
by **direct constructors, with no existential-witness lifting**:

- pendant `addPendant H a` → `leafMerge` then `iso` (`ghz3LeafMerge_iso_addPendant`);
- false twin `addFalseTwin H a` → `centerMerge` then `iso` (`ghz3CenterMerge_iso_addFalseTwin`);
- true twin `addTrueTwin H a` → `lc ∘ leafMerge ∘ lc`, closed by the identity
  `localComplement (addPendant G u) (some u) = addTrueTwin (localComplement G u) u`
  and `localComplement_involutive`;
- core → `base` (+ `lc` for `K₃`) then `iso`.

The true-twin identity is the crux that lets a clique-building step be realized without any LC
lifting. All of it is Fable-authored Lean, developed hole-by-hole through the gated loop.

## Modules

| module | content | status |
|---|---|---|
| `CenterMerge` | `ghz3CenterMerge` + iso to `addFalseTwin` | promoted (PR#32) |
| `TrueTwin` | `addTrueTwin` + the pendant↔true-twin LC identity | promoted (PR#33) |
| `ProducibleExt` | `ProducibleByExt` + `producibleByExt_c4` | promoted (PR#34) |
| `DHForward` | `PendantTwinBuildable` + `dh_forward` + `dh_min_fusions` | capstone |

## What remains open

The **reverse** direction, `F=N−3 ⟹ distance-hereditary`, needs rank-width / vertex-minor
machinery that mathlib does not have, and stays open. The characterization as a whole is a
Fable-generated CONJECTURED artifact grounded on all 585 orbits; its forward half is now a
theorem.

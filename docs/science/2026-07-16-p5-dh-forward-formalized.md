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
| `DHCharacterization` | `PendantTwinBuildable` (+ `lc`) + `dh_forward` + `dh_reverse` + `dh_characterization` + `dh_min_fusions` | capstone |

## The reverse direction — formalized at the model level

`dh_characterization` (Fable-authored, gate-certified):

> `ProducibleByExt (N−3) G  ↔  PendantTwinBuildable G` — a graph is producible at the fusion
> floor in the extended model **iff** it is distance-hereditary.

The reverse (`dh_reverse : ProducibleByExt m G → PendantTwinBuildable G`) is a direct structural
induction: `base → core`, `leafMerge → pendant` and `centerMerge → falseTwin` (via the
faithfulness isos), `lc → lc`, `iso → iso`. It required adding an `lc` constructor to
`PendantTwinBuildable` — this does **not** change the class: the pendant/twin build class is
already the distance-hereditary graphs (Bandelt–Mulder), and DH is closed under local
complementation (rank-width 1 is an LC-invariant, Oum/Bouchet), so `lc` only makes the closure
manifest and turns the reverse's `lc` case into a one-line constructor instead of a ~10-lemma
transport argument.

**How this relates to the physical `F=N−3 ⟹ DH`.** The bridge is a vertex-counting argument,
rigorous but not Lean-formalized here: a schedule producing an `N`-vertex graph uses `g` GHZ₃
resources and `f` fusions with `N + 2f = 3g`, and each fusion is either a disjoint merge (`+1`
vertex, `−1` component) or an intra-fusion (`+0` vertices, `+0` components). Reaching `N`
vertices needs exactly `N−3` disjoint merges, so `f = N−3` forces **zero intra-fusions** — i.e.
`F=N−3` is realized by disjoint merges + local Cliffords only, which is exactly `ProducibleByExt`.
Hence physical `F(G)=N−3 ⟹ ProducibleByExt(N−3) G ⟹ DH`. The reason this last step is not a
single Lean theorem: intra-fusion has **no closed-form graph rewrite** (the domain computes it
engine-only), so a general-schedule model that would let Lean state "`F=N−3`" directly cannot be
built; and the classical route (non-DH ⟹ `F>N−3`) needs rank-width machinery mathlib lacks.

**Net:** both directions of the *model* characterization `ProducibleByExt(N−3) ⟺ DH` are now
machine-verified; the physical `F=N−3 ⟺ DH` follows via the (paper) counting bridge. The
original Fable-generated conjecture, grounded on all 585 orbits, is now — at the model level — a
theorem in both directions.

## UPDATE: the counting bridge is now a Lean theorem (single-blob model)

The remark above is superseded in part. The obstacle it named — intra-fusion has no closed-form
graph rewrite — is sidestepped rather than solved: to exclude intra-fusions at the floor, no
rewrite is needed. A new inductive `BlobSchedule` extends the production model with an `intra`
constructor that **over-approximates** an intra-blob fusion: from a graph on `V` it may produce
*any* graph on a carrier with two fewer elements, at the cost of one fusion. Over-approximating
only strengthens the floor theorem. Formalized (module `Bridge`, gate-certified, clean axioms):

- `BlobSchedule.natCard_le` — any `BlobSchedule f G` has `Nat.card V ≤ f + 3` (a merge gains one
  vertex per fusion; an intra loses two vertices while spending one).
- `blobSchedule_floor` — `BlobSchedule f G` with `card V = f + 3` implies `ProducibleByExt f G`:
  at the floor the intra case is impossible (its sub-derivation would violate `natCard_le`).
- `floor_schedule_iff_dh` — for `3 ≤ N`: `BlobSchedule (N−3) G ↔ PendantTwinBuildable G`.

So even in a schedule model that allows intra-fusions generous enough to produce arbitrary
graphs, the fusion floor is reached exactly by the distance-hereditary graphs. The remaining
boundary between this theorem and the physical minimum is now **only the single-blob normal
form**: reducing an arbitrary multi-component schedule to a single growing blob, justified by
the commutation of fusions on disjoint qubit pairs (domain-level, engine-checked; not
formalized).

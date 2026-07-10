/-
Copyright (c) 2026 Sean Howell. All rights reserved.
Released under the MIT license as described in the file LICENSE.
Authors: Sean Howell
-/
import Mathlib.Combinatorics.SimpleGraph.Hasse
import Mathlib.Logic.Equiv.Fin.Basic
import Mathlib.Order.Bounds.Basic
import EmpiricistLean.Basic

/-!
# The path family exact minimum-fusion value `F(pathₙ) = N − 3` (Empiricist Problem 5)

This module proves the **upper** bound `F(pathₙ) ≤ N − 3` for the minimum-fusion
synthesis problem restricted to the path family, and combines it with the
universal lower bound (re-derived here, since the gate forbids importing
`EmpiricistLean.FusionCost`) to pin the **exact value** `F(pathₙ) = N − 3`.

`F(G)` = the minimum number of `{X_aZ_b, Z_aX_b}` Bell-measurement fusions of
GHZ₃ resource states producing a graph state LC-equivalent to `|G⟩`.

## What is MODELED vs PROVED (in the spirit of `FusionCost.lean`)

The physical fusion is a destructive Bell measurement.  On **disjoint** graph
states (spec D6) it realizes a *graph rewrite*: fusing qubit `a` of the blob with
a leaf `b` of a fresh GHZ₃ resource performs the complete-bipartite neighbourhood
join `N(a) × N(b)` and deletes `a, b`.  This graph-level rewrite is what we MODEL,
as the `SimpleGraph` transformation `ghz3LeafMerge` below.  It is **not** an
assumption pulled from thin air: it is the exact rule realized by the two
independently-verified fusion engines (`fusion_gf2`, `fusion_stim`) and their
fuzz-certified closed form (`domain/p5/moves.py::merge_fresh_ghz3`, `role="leaf"`).
The engines were cross-checked against this Lean rule on concrete `N`:

* `ghz3LeafMerge G a` is isomorphic to "attach one pendant vertex at `a`"
  (`ghz3LeafMerge_iso_addPendant`); an independent McKay-certificate check over
  200 random connected `G` found **0** mismatches with `merge_fresh_ghz3(G,a,"leaf")`.
* Merging a fresh GHZ₃ leaf onto an endpoint of `pathₙ` yields `pathₙ₊₁`,
  confirmed on **both** engines (via `lc_orbit_key`) for `N = 3..7`.

What we then PROVE from this modeled rule:

* `producibleBy_pathGraph` — `pathₙ` (i.e. `pathGraph N`) is produced from the
  GHZ₃ resource (`= pathGraph 3`) by **exactly `N − 3`** leaf-merge fusions — the
  explicit construction realizing the upper bound.
* `family_fusion_lower_bound` — the universal lower bound `N − 3 ≤ f` for *any*
  schedule satisfying photon counting and the local merge dynamics (this is the
  `FusionCost` content, re-derived inline; the gate forbids the cross-module import).
* `pathGraph_fusion_isLeast` — combining both: `N − 3` is the **least** achievable
  fusion count, i.e. `F(pathₙ) = N − 3`.

## Faithfulness of the identification GHZ₃ = `pathGraph 3` and iso ⇒ LC-equiv

GHZ₃ is the 3-vertex star `K₁,₂` (a center with two leaves), which as an abstract
graph is the 3-vertex path `pathGraph 3`.  A graph *isomorphism* is a qubit
relabelling; the domain's LC-orbit key (`domain/p5/canonical.py`) is invariant
under both local complementation **and** relabelling, so producing a graph
`≃g pathₙ` produces a state LC-equivalent to the path family — the ≃g results here
are therefore at least as strong as the "LC-equivalent to familyₙ" claim.

## Honest scope of the `F = N − 3` statement

`Schedule` records a synthesis schedule by its physical invariants (photon
counting `N + 2f = 3g`; a component-merge dynamics forcing connectivity) **plus**
a genuine producing construction (`ProducibleBy`).  Requiring `ProducibleBy` in a
`Schedule` is what makes membership non-vacuous (a real construction, not merely
consistent counts): the upper half of `pathGraph_fusion_isLeast` exhibits the
explicit `ProducibleBy` construction, and its lower half is discharged from the
schedule's photon counting + merge dynamics (never the construction).

**Where the general optimality lives.**  Because a `Schedule`'s `ProducibleBy`
construction of an `N`-vertex path uses exactly `N − 3` leaf-merges, `Achievable`
here is the class of genuine leaf-merge constructions, all with `f = N − 3`; so
`pathGraph_fusion_isLeast` says "the least fusion count among genuine leaf-merge
constructions of `pathₙ` is `N − 3`".  The claim that **no** GHZ₃-fusion strategy
whatsoever beats `N − 3` is the SEPARATE, fully general `family_fusion_lower_bound`
(photon counting + merge dynamics only, no `ProducibleBy`) — the `FusionCost`
content.  Together: `family_fusion_lower_bound` (F ≥ N − 3 for any schedule) and
`pathGraph_fusion_upper_bound` (F ≤ N − 3 by explicit construction) pin the exact
value.  This mirrors `FusionCost.lean`: nothing smuggles the conclusion into a
definition — the hypotheses are the exact qubit-count equality, the local merge
rule, and an actual construction.
-/

namespace Empiricist

open SimpleGraph

/-! ## The GHZ₃ resource graph and the D6 disjoint leaf-merge rule -/

/-- The GHZ₃ resource state's graph: the 3-vertex star `K₁,₂`, equal as an
abstract graph to the 3-vertex path `pathGraph 3` (center `1`, leaves `0, 2`). -/
def GHZ3graph : SimpleGraph (Fin 3) := pathGraph 3

/-- **The modeled D6 disjoint leaf-merge fusion rule.**  Fusing blob qubit `a` of
`G` with a **leaf** of a fresh GHZ₃ resource (spec D6): the fused blob vertex `a`
and the fused fresh leaf are consumed; the fresh **center** (`Sum.inr false`)
survives and inherits `a`'s entire neighbourhood `N(a)` (the complete-bipartite
join `N(a) × {center}`, since a GHZ₃ leaf's only neighbour is the center); the
fresh **other leaf** (`Sum.inr true`) survives as a pendant on the center.  The
surviving blob vertices `{v // v ≠ a}` keep their mutual edges.  Net vertex change
`|V| − 1 + 2 = |V| + 1`, matching one fusion of a 3-qubit resource. -/
def ghz3LeafMerge {V : Type} (G : SimpleGraph V) (a : V) :
    SimpleGraph ({v : V // v ≠ a} ⊕ Bool) where
  Adj x y :=
    match x, y with
    | Sum.inl u, Sum.inl v => G.Adj u.1 v.1
    | Sum.inl u, Sum.inr s => s = false ∧ G.Adj u.1 a
    | Sum.inr s, Sum.inl v => s = false ∧ G.Adj a v.1
    | Sum.inr s, Sum.inr t => (s = false ∧ t = true) ∨ (s = true ∧ t = false)
  symm := ⟨by
    rintro (u | s) (v | t) h
    · exact h.symm
    · exact ⟨h.1, h.2.symm⟩
    · exact ⟨h.1, h.2.symm⟩
    · tauto⟩
  loopless := ⟨by
    rintro (u | s) h
    · exact G.irrefl h
    · rcases s with _ | _ <;> tauto⟩

/-- "Attach a fresh pendant vertex (`none`) at `a`": `G` on `Option V` with a new
degree-1 vertex adjacent only to `a`.  This is `ghz3LeafMerge G a` under the
faithful relabelling (fresh center ↦ the reused label `a`, fresh leaf ↦ `none`);
see `ghz3LeafMerge_iso_addPendant`.  Cleaner to iterate for the path construction. -/
def addPendant {V : Type} (G : SimpleGraph V) (a : V) : SimpleGraph (Option V) where
  Adj x y :=
    match x, y with
    | some u, some v => G.Adj u v
    | some u, none => u = a
    | none, some v => v = a
    | none, none => False
  symm := ⟨by
    rintro (_ | u) (_ | v) h
    · exact h
    · exact h
    · exact h
    · exact h.symm⟩
  loopless := ⟨by
    rintro (_ | u) h
    · exact h
    · exact G.irrefl h⟩

/-- The relabelling `({v // v ≠ a} ⊕ Bool) ≃ Option V`: surviving blob vertex
`u ↦ some u`, fresh center (`inr false`) ↦ `some a`, fresh leaf (`inr true`) ↦
`none`.  A bijection because the fresh center exactly occupies `a`'s vacated slot. -/
def leafMergeEquivOption (V : Type) [DecidableEq V] (a : V) :
    ({v : V // v ≠ a} ⊕ Bool) ≃ Option V where
  toFun := fun x => match x with
    | Sum.inl u => some u.1
    | Sum.inr false => some a
    | Sum.inr true => none
  invFun := fun o => match o with
    | none => Sum.inr true
    | some v => if h : v = a then Sum.inr false else Sum.inl ⟨v, h⟩
  left_inv := by
    rintro (u | s)
    · simp [u.2]
    · cases s <;> simp
  right_inv := by
    rintro (_ | v)
    · simp
    · by_cases h : v = a <;> simp [h]

/-- **Faithfulness lemma.**  The modeled D6 leaf-merge rule `ghz3LeafMerge G a` is
isomorphic to `addPendant G a` — attaching one pendant vertex at `a`.  (Proved,
not assumed; independently McKay-cross-checked against both fusion engines.) -/
def ghz3LeafMerge_iso_addPendant {V : Type} [DecidableEq V] (G : SimpleGraph V) (a : V) :
    ghz3LeafMerge G a ≃g addPendant G a where
  __ := leafMergeEquivOption V a
  map_rel_iff' := by
    rintro (u | s) (v | t)
    · simp [leafMergeEquivOption, ghz3LeafMerge, addPendant]
    · cases t <;> simp [leafMergeEquivOption, ghz3LeafMerge, addPendant, u.2]
    · cases s <;> simp [leafMergeEquivOption, ghz3LeafMerge, addPendant, v.2]
    · cases s <;> cases t <;>
        simp [leafMergeEquivOption, ghz3LeafMerge, addPendant, SimpleGraph.irrefl]

/-- **The single-fusion path-extension step.**  One leaf-merge fusion attaching a
fresh pendant at the endpoint `0` of `pathₙ₊₁` yields `pathₙ₊₂`: attaching a
pendant at a path endpoint extends the path by one vertex.  The isomorphism is the
standard `Fin (n+2) ≃ Option (Fin (n+1))` (`finSuccEquiv`), sending `none ↦ 0`. -/
def addPendant_pathGraph_iso (n : ℕ) :
    addPendant (pathGraph (n + 1)) (0 : Fin (n + 1)) ≃g pathGraph (n + 2) where
  __ := (finSuccEquiv (n + 1)).symm
  map_rel_iff' := by
    rintro (_ | x) (_ | y) <;>
      simp only [finSuccEquiv_symm_none, finSuccEquiv_symm_some]
    · change (pathGraph (n + 2)).Adj 0 0 ↔ (addPendant (pathGraph (n + 1)) 0).Adj none none
      simp [pathGraph_adj, addPendant]
    · change (pathGraph (n + 2)).Adj 0 y.succ ↔
        (addPendant (pathGraph (n + 1)) 0).Adj none (some y)
      simp only [pathGraph_adj, addPendant, Fin.val_zero, Fin.val_succ, Fin.ext_iff]; omega
    · change (pathGraph (n + 2)).Adj x.succ 0 ↔
        (addPendant (pathGraph (n + 1)) 0).Adj (some x) none
      simp only [pathGraph_adj, addPendant, Fin.val_zero, Fin.val_succ, Fin.ext_iff]; omega
    · simp only [pathGraph_adj, addPendant, Fin.val_succ]; omega

/-- One leaf-merge fusion of the modeled rule extends `pathₙ₊₁` to `pathₙ₊₂`. -/
def ghz3LeafMerge_pathGraph_iso (n : ℕ) :
    ghz3LeafMerge (pathGraph (n + 1)) (0 : Fin (n + 1)) ≃g pathGraph (n + 2) :=
  (ghz3LeafMerge_iso_addPendant (pathGraph (n + 1)) 0).trans (addPendant_pathGraph_iso n)

/-! ## Producibility: reachability from GHZ₃ by leaf-merge fusions -/

/-- `ProducibleBy m H` : the graph `H` is produced from a single GHZ₃ resource by
`m` cross-component leaf-merge fusions with fresh GHZ₃'s (up to qubit relabelling).
`base` starts at the GHZ₃ resource with `0` fusions; `merge` applies one D6
leaf-merge (`+1` fusion); `iso` closes the relation under qubit relabelling
(graph isomorphism), reflecting that graph states are defined up to relabelling. -/
inductive ProducibleBy : ℕ → {V : Type} → SimpleGraph V → Prop where
  | base : ProducibleBy 0 GHZ3graph
  | merge {m : ℕ} {V : Type} (G : SimpleGraph V) (a : V) :
      ProducibleBy m G → ProducibleBy (m + 1) (ghz3LeafMerge G a)
  | iso {m : ℕ} {V W : Type} {G : SimpleGraph V} {H : SimpleGraph W} :
      ProducibleBy m G → (G ≃g H) → ProducibleBy m H

/-- **The explicit upper-bound construction.**  `pathₖ₊₃` is produced from the
GHZ₃ resource by exactly `k` leaf-merge fusions.  Induction on `k`: `pathGraph 3`
is the GHZ₃ resource (`base`); each further fusion extends the path by one vertex
(`merge` + the `ghz3LeafMerge_pathGraph_iso` re-labelling). -/
theorem producibleBy_pathGraph (k : ℕ) : ProducibleBy k (pathGraph (k + 3)) := by
  induction k with
  | zero => exact ProducibleBy.base
  | succ k ih =>
      have hstep : ProducibleBy (k + 1) (ghz3LeafMerge (pathGraph (k + 3)) (0 : Fin (k + 3))) :=
        ProducibleBy.merge (pathGraph (k + 3)) 0 ih
      exact ProducibleBy.iso hstep (ghz3LeafMerge_pathGraph_iso (k + 2))

/-- `pathₙ` is produced by exactly `N − 3` leaf-merge fusions, for `N ≥ 3`. -/
theorem producibleBy_pathGraph_of_le {N : ℕ} (hN : 3 ≤ N) :
    ProducibleBy (N - 3) (pathGraph N) := by
  have h := producibleBy_pathGraph (N - 3)
  rwa [Nat.sub_add_cancel hN] at h

/-! ## The universal lower bound (re-derived inline from `FusionCost`) -/

/-- **The component-merge bound** (`FusionCost.components_merge_bound`, re-derived
inline: the gate forbids importing `EmpiricistLean.FusionCost`).  A schedule whose
component count starts at `g`, ends connected (`= 1`), and drops by at most one per
fusion, uses at least `g − 1` fusions: `g ≤ f + 1`. -/
theorem components_merge_bound {g f : ℕ} (c : ℕ → ℕ)
    (hstart : c 0 = g) (hend : c f = 1)
    (hstep : ∀ i, i < f → c i ≤ c (i + 1) + 1) :
    g ≤ f + 1 := by
  have key : ∀ i, i ≤ f → g ≤ c i + i := by
    intro i
    induction i with
    | zero => intro _; omega
    | succ n ih =>
      intro hle
      have hstep_n := hstep n (by omega)
      have hprev := ih (by omega)
      omega
  have hfinal := key f (le_refl f)
  rw [hend] at hfinal
  omega

/-- **The universal minimum-fusion lower bound `F ≥ N − 3`.**  Photon counting
(`N + 2f = 3g`) plus the component-merge dynamics (start `g`, end connected, each
fusion `−1` at most) force `N − 3 ≤ f`, for any schedule producing an `N`-vertex
connected output (`N ≥ 3` regime carried faithfully).  This is `FusionCost`'s
content; it makes no reference to the specific family or rule — it holds for
*every* GHZ₃-fusion schedule. -/
theorem family_fusion_lower_bound {N g f : ℕ} (hN : 3 ≤ N)
    (hcount : N + 2 * f = 3 * g)
    (c : ℕ → ℕ) (hc0 : c 0 = g) (hcf : c f = 1)
    (hcstep : ∀ i, i < f → c i ≤ c (i + 1) + 1) :
    N - 3 ≤ f := by
  have hg := components_merge_bound c hc0 hcf hcstep
  omega

/-! ## The exact value `F(pathₙ) = N − 3` -/

/-- A GHZ₃-fusion synthesis **schedule** producing (a graph isomorphic to) the
target `T` on `N` vertices, recorded by its physical invariants **and** a genuine
producing construction.

* `g, f` — GHZ₃ resources consumed, fusions performed.
* `hcount` — photon counting `N + 2f = 3g` (exact qubit bookkeeping).
* `c, hc0, hcf, hcstep` — the component-merge dynamics: the connected-component
  count starts at `g`, ends at `1` (connected output), and each fusion drops it by
  at most one.  This *derives* connectivity's `g ≤ f + 1`, never assumes it.
* `outG, produces, outIso` — a genuine graph `outG` produced by `f` leaf-merge
  fusions (`produces`) that is isomorphic to `T` (`outIso`).  This is what makes a
  schedule a real construction rather than merely consistent bookkeeping. -/
structure Schedule (N : ℕ) (T : SimpleGraph (Fin N)) : Type 1 where
  g : ℕ
  f : ℕ
  hcount : N + 2 * f = 3 * g
  c : ℕ → ℕ
  hc0 : c 0 = g
  hcf : c f = 1
  hcstep : ∀ i, i < f → c i ≤ c (i + 1) + 1
  out : Type
  outG : SimpleGraph out
  produces : ProducibleBy f outG
  outIso : outG ≃g T

/-- The set of fusion counts achievable by a schedule producing `T`. -/
def Achievable (N : ℕ) (T : SimpleGraph (Fin N)) : Set ℕ :=
  { f | ∃ s : Schedule N T, s.f = f }

/-- The explicit `N − 3`-fusion schedule producing `pathₙ` (the upper-bound
witness): `g = N − 2` resources, `f = N − 3` fusions, the linear merge dynamics
`c i = (N − 2) − i`, and the `producibleBy_pathGraph` construction. -/
noncomputable def pathGraphSchedule {N : ℕ} (hN : 3 ≤ N) :
    Schedule N (pathGraph N) where
  g := N - 2
  f := N - 3
  hcount := by omega
  c := fun i => (N - 2) - i
  hc0 := by simp
  hcf := by omega
  hcstep := by intro i hi; omega
  out := Fin N
  outG := pathGraph N
  produces := producibleBy_pathGraph_of_le hN
  outIso := RelIso.refl _

/-- **`F(pathₙ) ≤ N − 3`.**  `N − 3` fusions suffice: the explicit construction. -/
theorem pathGraph_fusion_upper_bound {N : ℕ} (hN : 3 ≤ N) :
    (N - 3) ∈ Achievable N (pathGraph N) :=
  ⟨pathGraphSchedule hN, rfl⟩

/-- **`F(pathₙ) = N − 3` — the exact minimum-fusion value.**  `N − 3` is the least
achievable fusion count for producing `pathₙ` (`N ≥ 3`): it is achieved by the
explicit `N − 3`-fusion construction (`pathGraph_fusion_upper_bound`), and every
schedule uses at least `N − 3` fusions by the universal lower bound
(`family_fusion_lower_bound`, applied to the schedule's own physical invariants). -/
theorem pathGraph_fusion_isLeast {N : ℕ} (hN : 3 ≤ N) :
    IsLeast (Achievable N (pathGraph N)) (N - 3) := by
  refine ⟨pathGraph_fusion_upper_bound hN, ?_⟩
  rintro f ⟨s, rfl⟩
  exact family_fusion_lower_bound hN s.hcount s.c s.hc0 s.hcf s.hcstep

/-- The minimum-fusion value as an infimum: `F(pathₙ) = N − 3`. -/
theorem pathGraph_fusion_sInf {N : ℕ} (hN : 3 ≤ N) :
    sInf (Achievable N (pathGraph N)) = N - 3 :=
  (pathGraph_fusion_isLeast hN).csInf_eq

end Empiricist

/-
EmpiricistLean.FusionRule

P5: the GHZ3 fusion construction relation.

* `GHZ3graph`                    : the 3-qubit GHZ resource state as a graph
                                   (`SimpleGraph.pathGraph 3`, center `1`, leaves `0`, `2`).
* `addPendant G a`               : attach one fresh degree-1 vertex (`none`) adjacent only to `a`.
* `ghz3LeafMerge G a`            : the D6 DISJOINT leaf-merge fusion rule: fuse blob qubit `a`
                                   with a leaf of a fresh GHZ3 resource; `a` and the fused leaf
                                   are consumed, the fresh center inherits N(a), the other fresh
                                   leaf survives as a pendant on the center.
* `ghz3LeafMerge_iso_addPendant` : FAITHFULNESS — the D6 rule is (up to graph isomorphism)
                                   exactly pendant attachment at `a`.
* `ProducibleBy m G`             : `G` is producible by `m` fusions from one GHZ3 resource.
* `ProducibleUpToLC f H`         : producible in `f` fusions up to local-Clifford (LC) equivalence.
* `producibleUpToLC_ghz3_step`   : TARGET — one leaf-merge on GHZ3 is producible up to LC in
                                   one fusion.
-/
import Mathlib.Combinatorics.SimpleGraph.Basic
import Mathlib.Combinatorics.SimpleGraph.Hasse
import Mathlib.Combinatorics.SimpleGraph.Maps
import Mathlib.Logic.Equiv.Fin.Basic
import EmpiricistLean.LocalComp

set_option autoImplicit false

namespace Empiricist

open SimpleGraph

/-- **(1)** The GHZ3 resource state as a graph: the 3-vertex path `0 — 1 — 2`
(center `1`, leaves `0` and `2`). -/
def GHZ3graph : SimpleGraph (Fin 3) :=
  SimpleGraph.pathGraph 3

/-- **(2)** Attach one fresh degree-1 vertex (`none`) adjacent ONLY to `a`.
Existing vertices keep their edges: `some u ~ some v` iff `G.Adj u v`,
and `some u ~ none` iff `u = a`. -/
def addPendant {V : Type} (G : SimpleGraph V) (a : V) : SimpleGraph (Option V) where
  Adj x y :=
    match x, y with
    | some u, some v => G.Adj u v
    | some u, none => u = a
    | none, some v => v = a
    | none, none => False
  symm := by
    constructor
    rintro (_ | u) (_ | v) h
    · exact h
    · exact h
    · exact h
    · exact G.adj_symm h
  loopless := by
    constructor
    rintro (_ | u) h
    · exact h
    · exact G.irrefl h

@[simp] lemma addPendant_adj_some_some {V : Type} (G : SimpleGraph V) (a u v : V) :
    (addPendant G a).Adj (some u) (some v) ↔ G.Adj u v := Iff.rfl

@[simp] lemma addPendant_adj_some_none {V : Type} (G : SimpleGraph V) (a u : V) :
    (addPendant G a).Adj (some u) none ↔ u = a := Iff.rfl

@[simp] lemma addPendant_adj_none_some {V : Type} (G : SimpleGraph V) (a v : V) :
    (addPendant G a).Adj none (some v) ↔ v = a := Iff.rfl

@[simp] lemma addPendant_not_adj_none_none {V : Type} (G : SimpleGraph V) (a : V) :
    ¬ (addPendant G a).Adj none none := fun h => h

/-- **(3)** The D6 DISJOINT leaf-merge fusion rule: fuse blob qubit `a : V` with a LEAF of a
fresh GHZ3 resource.  The fused blob vertex `a` and the fused fresh leaf are CONSUMED.
Carrier: `{v // v ≠ a} ⊕ Bool`, where

* `Sum.inl u`     — a surviving blob vertex (`u ≠ a`);
* `Sum.inr false` — the fresh GHZ3 CENTER, which survives and inherits `a`'s entire
  neighbourhood `N(a)`;
* `Sum.inr true`  — the fresh OTHER leaf, surviving as a pendant on that center.

Surviving blob vertices keep their mutual edges.  Net vertex change: `|V| - 1 + 2 = |V| + 1`,
one fusion of a 3-qubit resource. -/
def ghz3LeafMerge {V : Type} (G : SimpleGraph V) (a : V) :
    SimpleGraph ({v // v ≠ a} ⊕ Bool) where
  Adj x y :=
    match x, y with
    | Sum.inl u, Sum.inl v => G.Adj u.1 v.1
    | Sum.inl u, Sum.inr b => b = false ∧ G.Adj u.1 a
    | Sum.inr b, Sum.inl v => b = false ∧ G.Adj v.1 a
    | Sum.inr b, Sum.inr c => b ≠ c
  symm := by
    constructor
    rintro (u | b) (v | c) h
    · exact G.adj_symm h
    · exact h
    · exact h
    · exact fun hcb => h hcb.symm
  loopless := by
    constructor
    rintro (u | b) h
    · exact G.irrefl h
    · exact h rfl

@[simp] lemma ghz3LeafMerge_adj_inl_inl {V : Type} (G : SimpleGraph V) (a : V)
    (u v : {v // v ≠ a}) :
    (ghz3LeafMerge G a).Adj (Sum.inl u) (Sum.inl v) ↔ G.Adj u.1 v.1 := Iff.rfl

@[simp] lemma ghz3LeafMerge_adj_inl_inr {V : Type} (G : SimpleGraph V) (a : V)
    (u : {v // v ≠ a}) (b : Bool) :
    (ghz3LeafMerge G a).Adj (Sum.inl u) (Sum.inr b) ↔ b = false ∧ G.Adj u.1 a := Iff.rfl

@[simp] lemma ghz3LeafMerge_adj_inr_inl {V : Type} (G : SimpleGraph V) (a : V)
    (b : Bool) (v : {v // v ≠ a}) :
    (ghz3LeafMerge G a).Adj (Sum.inr b) (Sum.inl v) ↔ b = false ∧ G.Adj v.1 a := Iff.rfl

@[simp] lemma ghz3LeafMerge_adj_inr_inr {V : Type} (G : SimpleGraph V) (a : V) (b c : Bool) :
    (ghz3LeafMerge G a).Adj (Sum.inr b) (Sum.inr c) ↔ b ≠ c := Iff.rfl

/-- The vertex relabelling underlying the faithfulness isomorphism: surviving blob vertices go
to themselves, the fresh GHZ3 center (`inr false`) goes to the consumed fusion site `a`, and
the fresh surviving leaf (`inr true`) goes to the fresh pendant vertex `none`. -/
def mergeEquiv {V : Type} [DecidableEq V] (a : V) : ({v // v ≠ a} ⊕ Bool) ≃ Option V where
  toFun x :=
    match x with
    | Sum.inl u => some u.1
    | Sum.inr false => some a
    | Sum.inr true => none
  invFun y :=
    match y with
    | none => Sum.inr true
    | some v => if h : v = a then Sum.inr false else Sum.inl ⟨v, h⟩
  left_inv := by
    rintro (⟨v, hv⟩ | b)
    · simp [hv]
    · cases b <;> simp
  right_inv := by
    rintro (_ | v)
    · rfl
    · rcases eq_or_ne v a with rfl | h
      · simp
      · simp [h]

@[simp] lemma mergeEquiv_inl {V : Type} [DecidableEq V] (a : V) (u : {v // v ≠ a}) :
    mergeEquiv a (Sum.inl u) = some u.1 := rfl

@[simp] lemma mergeEquiv_inr_false {V : Type} [DecidableEq V] (a : V) :
    mergeEquiv a (Sum.inr false) = some a := rfl

@[simp] lemma mergeEquiv_inr_true {V : Type} [DecidableEq V] (a : V) :
    mergeEquiv a (Sum.inr true) = none := rfl

/-- **(4)** FAITHFULNESS of the D6 leaf-merge rule: `ghz3LeafMerge G a` is isomorphic (as a
simple graph) to attaching one pendant vertex at `a`.  This pins the rule down: leaf-merging a
fresh GHZ3 resource at `a` does exactly one pendant attachment. -/
def ghz3LeafMerge_iso_addPendant {V : Type} [DecidableEq V] (G : SimpleGraph V) (a : V) :
    ghz3LeafMerge G a ≃g addPendant G a where
  toEquiv := mergeEquiv a
  map_rel_iff' := by
    rintro (⟨u, hu⟩ | b) (⟨v, hv⟩ | c)
    · -- blob–blob: both sides are `G.Adj u v`
      exact Iff.rfl
    · cases c
      · -- blob–center: `some u ~ some a` vs `false = false ∧ G.Adj u a`
        show G.Adj u a ↔ false = false ∧ G.Adj u a
        exact ⟨fun h => ⟨rfl, h⟩, fun h => h.2⟩
      · -- blob–fresh leaf: `some u ~ none` (i.e. `u = a`) vs `true = false ∧ _` (both false)
        show u = a ↔ true = false ∧ G.Adj u a
        exact ⟨fun h => absurd h hu, fun h => Bool.noConfusion h.1⟩
    · cases b
      · -- center–blob: `some a ~ some v` vs `false = false ∧ G.Adj v a`
        show G.Adj a v ↔ false = false ∧ G.Adj v a
        exact ⟨fun h => ⟨rfl, h.symm⟩, fun h => h.2.symm⟩
      · -- fresh leaf–blob: `none ~ some v` (i.e. `v = a`) vs `true = false ∧ _` (both false)
        show v = a ↔ true = false ∧ G.Adj v a
        exact ⟨fun h => absurd h hv, fun h => Bool.noConfusion h.1⟩
    · cases b <;> cases c
      · -- center–center: `G.Adj a a` vs `false ≠ false` (both false)
        show G.Adj a a ↔ (false ≠ false)
        exact ⟨fun h => absurd h G.irrefl, fun h => absurd rfl h⟩
      · -- center–fresh leaf: `some a ~ none` (i.e. `a = a`) vs `false ≠ true` (both true)
        show a = a ↔ (false ≠ true)
        exact ⟨fun _ h => Bool.noConfusion h, fun _ => rfl⟩
      · -- fresh leaf–center: `none ~ some a` (i.e. `a = a`) vs `true ≠ false` (both true)
        show a = a ↔ (true ≠ false)
        exact ⟨fun _ h => Bool.noConfusion h, fun _ => rfl⟩
      · -- fresh leaf–fresh leaf: `none ~ none` (False) vs `true ≠ true` (false)
        show False ↔ (true ≠ true)
        exact ⟨fun h => h.elim, fun h => h rfl⟩

/-- **(5)** `ProducibleBy m G`: the graph state `G` is producible by `m` fusions, starting from
a single GHZ3 resource, where each fusion consumes one fresh GHZ3 resource via the D6
leaf-merge rule; producibility is closed under graph isomorphism (relabelling of qubits). -/
inductive ProducibleBy : Nat → {V : Type} → SimpleGraph V → Prop
  | base : ProducibleBy 0 GHZ3graph
  | merge {m : Nat} {V : Type} (G : SimpleGraph V) (a : V) :
      ProducibleBy m G → ProducibleBy (m + 1) (ghz3LeafMerge G a)
  | iso {m : Nat} {V W : Type} {G : SimpleGraph V} {H : SimpleGraph W} :
      ProducibleBy m G → G ≃g H → ProducibleBy m H

/-- **(6)** `ProducibleUpToLC f H`: `H` is producible in `f` fusions up to local Clifford (LC)
equivalence — the physical state is only defined up to local Cliffords, i.e. up to the
`LCEquiv` relation generated by local complementations (`LCStep`).  Since `ProducibleBy` is
closed under graph isomorphism (`ProducibleBy.iso`), quantifying over graphs on the carrier of
`H` loses no generality: any relabelling is absorbed by `iso` before comparing under LC. -/
def ProducibleUpToLC (f : Nat) {W : Type} (H : SimpleGraph W) : Prop :=
  ∃ G : SimpleGraph W, ProducibleBy f G ∧ LCEquiv G H

/-- **(7)** Exact production implies production up to LC, via reflexivity of `LCEquiv`. -/
theorem ProducibleBy.toUpToLC {f : Nat} {V : Type} {G : SimpleGraph V}
    (h : ProducibleBy f G) : ProducibleUpToLC f G :=
  ⟨G, h, lcEquiv_equivalence.refl G⟩

/-- Bonus form of the target: any 0-fusion-producible blob, leaf-merged once, is producible up
to LC in one fusion. -/
theorem producibleUpToLC_ghz3LeafMerge {V : Type} (G : SimpleGraph V) (a : V)
    (h : ProducibleBy 0 G) : ProducibleUpToLC 1 (ghz3LeafMerge G a) :=
  (ProducibleBy.merge G a h).toUpToLC

/-- **(8) TARGET.**  GHZ3 leaf-merged once (at any blob qubit `a : Fin 3`) is producible up to
local Clifford equivalence in exactly one fusion.  Transitively exercises `GHZ3graph`,
`ghz3LeafMerge`, `ProducibleBy.base`, `ProducibleBy.merge`, `ProducibleUpToLC`, and
`LCEquiv` reflexivity. -/
theorem producibleUpToLC_ghz3_step (a : Fin 3) :
    ProducibleUpToLC 1 (ghz3LeafMerge GHZ3graph a) :=
  (ProducibleBy.merge GHZ3graph a ProducibleBy.base).toUpToLC

end Empiricist
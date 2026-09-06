import Mathlib.Combinatorics.SimpleGraph.Acyclic
import EmpiricistLean.Basic
import EmpiricistLean.LocalComp
import EmpiricistLean.FusionRule

/-!
# The 4-cycle (smallest non-tree distance-hereditary graph) needs only one fusion, up to LC

`addFalseTwin GHZ3graph 1` is the 4-cycle `C₄` on `Option (Fin 3)`: the new vertex `none`
is a false twin of the centre `1` of the path `P₃`, so `none ~ some 0`, `none ~ some 2`,
plus the path edges `some 0 ~ some 1`, `some 1 ~ some 2`.

We show `ProducibleUpToLC 1` for it.  The witness is a labeled path `P₄`
(`some 1 — none — some 0 — some 2`), producible by one GHZ₃ leaf merge (up to iso),
and LC-equivalent to `C₄` by an explicit three-step local-complementation chain
(at `none`, then `some 0`, then `none`).
-/

set_option maxHeartbeats 1000000

namespace Empiricist

open SimpleGraph

/-- Add a *false twin* of `u` to `G`: the new vertex `none` is adjacent to exactly the
`G`-neighbours of `u` (in particular not to `u` itself). -/
def addFalseTwin {V : Type*} (G : SimpleGraph V) (u : V) : SimpleGraph (Option V) where
  Adj x y :=
    match x, y with
    | some a, some b => G.Adj a b
    | none, some a => G.Adj u a
    | some a, none => G.Adj u a
    | none, none => False
  symm := by
    try constructor
    rintro (_ | a) (_ | b) h
    · exact h
    · exact h
    · exact h
    · first
        | exact h.symm
        | exact G.adj_symm h
        | exact G.symm h
        | exact SimpleGraph.Adj.symm h
  loopless := by
    try constructor
    rintro (_ | a) h
    · exact h
    · first
        | exact G.irrefl h
        | exact G.loopless a h
        | exact h.ne rfl
        | exact SimpleGraph.irrefl G h

/-- The path `some 1 — none — some 0 — some 2` on `Option (Fin 3)`. -/
def pathW : SimpleGraph (Option (Fin 3)) :=
  SimpleGraph.fromRel (fun x y =>
    (x = none ∧ y = some 1) ∨ (x = none ∧ y = some 0) ∨ (x = some 0 ∧ y = some 2))

/-- The relabelling `none ↦ some 1`, `some 0 ↦ none`, `some 1 ↦ some 0`, `some 2 ↦ some 2`. -/
def phi : Option (Fin 3) ≃ Option (Fin 3) :=
  (Equiv.swap (none : Option (Fin 3)) (some 1)).trans
    (Equiv.swap (none : Option (Fin 3)) (some 0))

/-- `pathW` is a relabelling of the pendant extension of `P₃` at the leaf `0`
(the path `none — some 0 — some 1 — some 2`). -/
def isoWP : addPendant GHZ3graph 0 ≃g pathW :=
  ⟨phi, by
    intro a b
    rcases a with _ | i <;> rcases b with _ | j <;>
      (try fin_cases i) <;> (try fin_cases j) <;>
      (first
        | (simp [phi, pathW, addPendant, GHZ3graph, SimpleGraph.fromRel_adj,
            SimpleGraph.pathGraph_adj, Equiv.trans_apply, Equiv.swap_apply_def]
           ; done)
        | (simp [phi, pathW, addPendant, GHZ3graph, SimpleGraph.fromRel_adj,
            SimpleGraph.pathGraph_adj, Equiv.trans_apply, Equiv.swap_apply_def]
           ; decide)
        | decide)⟩

private lemma lc_step {V : Type} [DecidableEq V] (G : SimpleGraph V) (v : V) :
    LCEquiv G (localComplement G v) := by
  apply lcEquiv_localComplement

private lemma lc_trans {V : Type} [DecidableEq V] {A B C : SimpleGraph V}
    (h1 : LCEquiv A B) (h2 : LCEquiv B C) : LCEquiv A C := by
  first
    | exact lcEquiv_equivalence.trans h1 h2
    | exact (lcEquiv_equivalence _).trans h1 h2
    | exact Equivalence.trans lcEquiv_equivalence h1 h2
    | exact Equivalence.trans (lcEquiv_equivalence _) h1 h2
    | exact Relation.EqvGen.trans _ _ _ h1 h2
    | exact EqvGen.trans _ _ _ h1 h2

private lemma lc_symm {V : Type} [DecidableEq V] {A B : SimpleGraph V}
    (h : LCEquiv A B) : LCEquiv B A := by
  first
    | exact lcEquiv_equivalence.symm h
    | exact (lcEquiv_equivalence _).symm h
    | exact Equivalence.symm lcEquiv_equivalence h
    | exact Equivalence.symm (lcEquiv_equivalence _) h
    | exact Relation.EqvGen.symm _ _ h
    | exact EqvGen.symm _ _ h

/-- The explicit three-step local complementation chain, evaluated:
starting from the path `1 — none — 0 — 2`, complementing at `none`, `some 0`, `none`
yields exactly the 4-cycle `addFalseTwin GHZ3graph 1`. -/
private lemma lc3_eq :
    localComplement (localComplement (localComplement pathW none) (some 0)) none
      = addFalseTwin GHZ3graph 1 := by
  ext x y
  rcases x with _ | i <;> rcases y with _ | j <;>
    (try fin_cases i) <;> (try fin_cases j) <;>
    (first
      | (simp [localComplement, Xor', pathW, addFalseTwin, GHZ3graph,
          SimpleGraph.fromRel_adj, SimpleGraph.pathGraph_adj] ; done)
      | (simp [localComplement, Xor', pathW, addFalseTwin, GHZ3graph,
          SimpleGraph.fromRel_adj, SimpleGraph.pathGraph_adj] ; decide)
      | decide)

/-- The 4-cycle obtained by adding a false twin of the centre of `P₃` is producible,
up to local complementation, with a single fusion. -/
theorem c4_producibleUpToLC : ProducibleUpToLC 1 (addFalseTwin GHZ3graph 1) := by
  have hP4 : ProducibleBy 1 (addPendant GHZ3graph 0) := by
    first
      | exact (ProducibleBy.merge GHZ3graph 0 ProducibleBy.base).iso
          (ghz3LeafMerge_iso_addPendant GHZ3graph 0)
      | exact ProducibleBy.iso (ProducibleBy.merge GHZ3graph 0 ProducibleBy.base)
          (ghz3LeafMerge_iso_addPendant GHZ3graph 0)
      | exact ProducibleBy.iso (ghz3LeafMerge_iso_addPendant GHZ3graph 0)
          (ProducibleBy.merge GHZ3graph 0 ProducibleBy.base)
      | exact (ProducibleBy.merge 0 ProducibleBy.base).iso
          (ghz3LeafMerge_iso_addPendant GHZ3graph 0)
      | exact (ProducibleBy.base.merge GHZ3graph 0).iso
          (ghz3LeafMerge_iso_addPendant GHZ3graph 0)
      | exact ((ProducibleBy.base).merge 0).iso
          (ghz3LeafMerge_iso_addPendant GHZ3graph 0)
  have hW : ProducibleBy 1 pathW := by
    first
      | exact hP4.iso isoWP
      | exact ProducibleBy.iso hP4 isoWP
      | exact ProducibleBy.iso isoWP hP4
  have hchain : LCEquiv pathW (addFalseTwin GHZ3graph 1) := by
    have h := lc_trans (lc_trans (lc_step pathW none)
        (lc_step (localComplement pathW none) (some 0)))
      (lc_step (localComplement (localComplement pathW none) (some 0)) none)
    rwa [lc3_eq] at h
  first
    | exact ⟨pathW, hW, hchain⟩
    | exact ⟨pathW, hchain, hW⟩
    | exact ⟨pathW, hW, lc_symm hchain⟩
    | exact ⟨_, pathW, hW, hchain⟩
    | exact ⟨_, pathW, hW, lc_symm hchain⟩

end Empiricist
import Mathlib.Combinatorics.SimpleGraph.Basic
import EmpiricistLean.Basic
import EmpiricistLean.FusionRule

namespace Empiricist

/-- Add a false twin of `a`: the new vertex `none` is adjacent exactly to the
neighbours of `a` (and NOT to `a` itself, nor to itself). -/
def addFalseTwin {V : Type} (G : SimpleGraph V) (a : V) : SimpleGraph (Option V) where
  Adj x y := match x, y with
    | some u, some v => G.Adj u v
    | none, some v => G.Adj a v
    | some u, none => G.Adj a u
    | none, none => False
  symm := by
    constructor
    rintro (_ | u) (_ | v) h
    · exact h.elim
    · exact h
    · exact h
    · exact h.symm
  loopless := by
    constructor
    rintro (_ | u) h
    · exact h
    · exact G.irrefl h

/-- CENTER-role GHZ3 fusion rewrite: delete the merged center `a`, introduce two
fresh survivor vertices (`inr false`, `inr true`) each attached to `N(a)`,
with the two survivors non-adjacent (false twins). -/
def ghz3CenterMerge {V : Type} (G : SimpleGraph V) (a : V) :
    SimpleGraph ({v // v ≠ a} ⊕ Bool) where
  Adj x y := match x, y with
    | Sum.inl u, Sum.inl v => G.Adj u.1 v.1
    | Sum.inl u, Sum.inr _ => G.Adj u.1 a
    | Sum.inr _, Sum.inl v => G.Adj v.1 a
    | Sum.inr _, Sum.inr _ => False
  symm := by
    constructor
    rintro (u | b) (v | c) h
    · exact h.symm
    · exact h
    · exact h
    · exact h.elim
  loopless := by
    constructor
    rintro (u | b) h
    · exact G.irrefl h
    · exact h

/-- The center-role GHZ3 merge graph is isomorphic to adding a false twin of `a`:
the engine-verified false-twin primitive. -/
def ghz3CenterMerge_iso_addFalseTwin {V : Type} [DecidableEq V] (G : SimpleGraph V) (a : V) :
    ghz3CenterMerge G a ≃g addFalseTwin G a where
  toEquiv := mergeEquiv a
  map_rel_iff' := by
    rintro (⟨u, hu⟩ | b) (⟨v, hv⟩ | c)
    · exact Iff.rfl
    · cases c
      · -- mergeEquiv (inr false) = some a : some u ~ some a is G.Adj u a
        show G.Adj u a ↔ G.Adj u a
        exact Iff.rfl
      · -- mergeEquiv (inr true) = none : some u ~ none is G.Adj a u
        show G.Adj a u ↔ G.Adj u a
        exact G.adj_comm a u
    · cases b
      · -- some a ~ some v is G.Adj a v
        show G.Adj a v ↔ G.Adj v a
        exact G.adj_comm a v
      · -- none ~ some v is G.Adj a v
        show G.Adj a v ↔ G.Adj v a
        exact G.adj_comm a v
    · cases b <;> cases c
      · -- some a ~ some a is G.Adj a a, merge side is False
        show G.Adj a a ↔ False
        exact ⟨fun h => G.irrefl h, False.elim⟩
      · -- some a ~ none is G.Adj a a
        show G.Adj a a ↔ False
        exact ⟨fun h => G.irrefl h, False.elim⟩
      · -- none ~ some a is G.Adj a a
        show G.Adj a a ↔ False
        exact ⟨fun h => G.irrefl h, False.elim⟩
      · -- none ~ none is False
        show False ↔ False
        exact Iff.rfl

end Empiricist

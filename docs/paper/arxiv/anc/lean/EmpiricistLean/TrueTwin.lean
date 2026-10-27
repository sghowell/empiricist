import Mathlib.Combinatorics.SimpleGraph.Basic
import EmpiricistLean.Basic
import EmpiricistLean.LocalComp
import EmpiricistLean.FusionRule

/-!
# EmpiricistLean.TrueTwin

Adding a *true twin* of a vertex, and the key identity: locally complementing
the attachment vertex `some u` of `addPendant G u` turns the pendant `none`
into a true twin of `u` over the locally complemented base graph.
-/

namespace Empiricist

/-- `addTrueTwin G a` adjoins a new vertex `none` to `G` which is a *true twin*
of `a`: the new vertex is adjacent to `a` itself and to every neighbour of `a`;
the old part of the graph is unchanged. -/
def addTrueTwin {V : Type*} (G : SimpleGraph V) (a : V) : SimpleGraph (Option V) where
  Adj p q :=
    match p, q with
    | some x, some y => G.Adj x y
    | some x, none => x = a ∨ G.Adj a x
    | none, some y => y = a ∨ G.Adj a y
    | none, none => False
  symm := by
    constructor
    rintro (_ | x) (_ | y) h
    · exact h
    · exact h
    · exact h
    · exact SimpleGraph.Adj.symm h
  loopless := by
    constructor
    rintro (_ | x) h
    · exact h
    · exact SimpleGraph.Adj.ne h rfl

@[simp] lemma addTrueTwin_adj_some_some {V : Type*} (G : SimpleGraph V) (a x y : V) :
    (addTrueTwin G a).Adj (some x) (some y) ↔ G.Adj x y := Iff.rfl

@[simp] lemma addTrueTwin_adj_some_none {V : Type*} (G : SimpleGraph V) (a x : V) :
    (addTrueTwin G a).Adj (some x) none ↔ x = a ∨ G.Adj a x := Iff.rfl

@[simp] lemma addTrueTwin_adj_none_some {V : Type*} (G : SimpleGraph V) (a x : V) :
    (addTrueTwin G a).Adj none (some x) ↔ x = a ∨ G.Adj a x := Iff.rfl

@[simp] lemma addTrueTwin_adj_none_none {V : Type*} (G : SimpleGraph V) (a : V) :
    (addTrueTwin G a).Adj none none ↔ False := Iff.rfl

private lemma lc_adj {V : Type*} [DecidableEq V] (G : SimpleGraph V) (v x y : V) :
    (localComplement G v).Adj x y ↔
      Xor' (G.Adj x y) (x ≠ y ∧ G.Adj x v ∧ G.Adj y v) := Iff.rfl

private lemma pend_some_some {V : Type} [DecidableEq V] (G : SimpleGraph V) (a x y : V) :
    (addPendant G a).Adj (some x) (some y) ↔ G.Adj x y := Iff.rfl

private lemma pend_some_none {V : Type} [DecidableEq V] (G : SimpleGraph V) (a x : V) :
    (addPendant G a).Adj (some x) none ↔ x = a := Iff.rfl

private lemma pend_none_some {V : Type} [DecidableEq V] (G : SimpleGraph V) (a x : V) :
    (addPendant G a).Adj none (some x) ↔ x = a := Iff.rfl

private lemma pend_none_none {V : Type} [DecidableEq V] (G : SimpleGraph V) (a : V) :
    (addPendant G a).Adj none none ↔ False := Iff.rfl

/-- Locally complementing the attachment vertex `some u` in `addPendant G u`
turns the pendant vertex `none` into a **true twin** of `u`, over the locally
complemented base graph `localComplement G u`. -/
theorem addPendant_localComplement_center {V : Type} [DecidableEq V]
    (G : SimpleGraph V) (u : V) :
    localComplement (addPendant G u) (some u) = addTrueTwin (localComplement G u) u := by
  ext p q
  rcases p with _ | x <;> rcases q with _ | y
  · -- `none — none`: stays non-adjacent.
    simp [lc_adj, pend_none_none, pend_none_some, Xor']
  · -- `none — some y`: the pendant edge toggles to `y = u ∨ G.Adj u y`.
    rcases eq_or_ne y u with rfl | h
    · simp [lc_adj, pend_none_some, pend_some_some, SimpleGraph.irrefl, Xor']
    · simp [lc_adj, pend_none_some, pend_some_some, SimpleGraph.irrefl, Xor', h,
        G.adj_comm y u]
      -- Residual: `G.Adj u y ↔ Xor (G.Adj u y) False`; close by unfolding the
      -- xor definitionally with an explicit term.
      exact ⟨fun hadj => Or.inl ⟨hadj, fun f => f⟩,
             fun hx => hx.elim And.left fun hx' => hx'.1.elim⟩
  · -- `some x — none`: symmetric to the previous case.
    rcases eq_or_ne x u with rfl | h
    · simp [lc_adj, pend_some_none, pend_none_some, pend_some_some,
        SimpleGraph.irrefl, Xor']
    · simp [lc_adj, pend_some_none, pend_none_some, pend_some_some,
        SimpleGraph.irrefl, Xor', h, G.adj_comm x u]
      exact ⟨fun hadj => Or.inl ⟨hadj, fun f => f⟩,
             fun hx => hx.elim And.left fun hx' => hx'.1.elim⟩
  · -- `some x — some y`: this block is exactly `localComplement G u`.
    simp [lc_adj, pend_some_some, pend_some_none, pend_none_some, Xor']

end Empiricist

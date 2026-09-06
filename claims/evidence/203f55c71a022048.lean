import Mathlib.Combinatorics.SimpleGraph.Basic
import EmpiricistLean.Basic

namespace Empiricist

/-- Add a "false twin" of `u` to `G`: a new vertex `none` adjacent exactly to the
neighbors of `u`; old vertices `some x`, `some y` retain the adjacency of `G`. -/
def addFalseTwin {V : Type*} (G : SimpleGraph V) (u : V) : SimpleGraph (Option V) where
  Adj a b :=
    match a, b with
    | some x, some y => G.Adj x y
    | none, some x => G.Adj u x
    | some x, none => G.Adj u x
    | none, none => False
  symm := by
    constructor
    rintro (_ | x) (_ | y) h
    · exact h.elim
    · exact h
    · exact h
    · exact G.adj_symm h
  loopless := by
    constructor
    rintro (_ | x) h
    · exact h
    · exact G.irrefl h

/-- The new vertex `none` is adjacent to `some x` iff `u` is adjacent to `x` in `G`. -/
theorem addFalseTwin_none_some {V : Type*} (G : SimpleGraph V) (u x : V) :
    (addFalseTwin G u).Adj none (some x) ↔ G.Adj u x :=
  Iff.rfl

end Empiricist

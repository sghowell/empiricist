/-
Copyright (c) 2026 Sean Howell. All rights reserved.
Released under the MIT license as described in the file LICENSE.
Authors: Sean Howell
-/
import Mathlib.Combinatorics.SimpleGraph.Acyclic

/-!
# Empiricist scaffold lemma

This is the Empiricist project's first **FORMALIZED** artifact: a genuine, sorry-free
graph-theory fact proved against a pinned mathlib. It exercises the M8 Lean verifier
pipeline (`lake env lean --json` diagnostics + `#print axioms` audit). It is explicitly
a scaffold, not an instance of the project's own `F(G)` conjecture machinery.

The statement: a connected simple graph on a finite vertex set `V` has at least
`|V| - 1` edges. Every connected graph contains a spanning tree (`Connected.exists_isTree_le`),
and a tree on `n` vertices has exactly `n - 1` edges (`IsTree.card_edgeFinset`); the spanning
tree's edges are a subset of `G`'s, giving the bound. Mathlib already packages this chain as
`SimpleGraph.Connected.card_vert_le_card_edgeSet_add_one`, so the proof here is a short
bridge from that `Nat.card`/`+1` form to the `Fintype.card`/truncated-subtraction form.
-/

namespace Empiricist

open SimpleGraph

/-- A connected simple graph on a finite vertex set has at least `|V| - 1` edges. -/
theorem connected_edge_bound {V : Type*} (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj]
    (hG : G.Connected) : Fintype.card V - 1 ≤ G.edgeFinset.card := by
  have h := hG.card_vert_le_card_edgeSet_add_one
  rw [Nat.card_eq_fintype_card, Nat.card_eq_fintype_card, ← edgeFinset_card] at h
  omega

end Empiricist

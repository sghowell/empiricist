/-
  Empiricist: minimal fusion count for the PATH family in the P5 GHZ3 fusion model.

  TARGET: `Empiricist.pathGraph_min_fusions`
    For N ≥ 3:
      (upper) ProducibleBy (N - 3) (SimpleGraph.pathGraph N), and
      (lower) any admissible fusion cost schedule c with N + 2f = 3g, c 0 = g,
              c f = 1, c i ≤ c (i+1) + 1 forces N - 3 ≤ f.

  Lower conjunct: immediate from the trusted `Empiricist.fusion_cost_lower_bound`.
  Upper conjunct: induction.  Base: pathGraph 3 = GHZ3graph.  Step: one
  `ghz3LeafMerge` at endpoint 0 of pathGraph (k+3), transported first along
  `ghz3LeafMerge_iso_addPendant` and then along the `finSuccEquiv`-based
  isomorphism "pendant at a path endpoint = the longer path".
-/
import EmpiricistLean.Foundation
import EmpiricistLean.LocalComp
import EmpiricistLean.FusionRule
import Mathlib.Combinatorics.SimpleGraph.Hasse
import Mathlib.Logic.Equiv.Fin.Basic

set_option maxRecDepth 8000
set_option maxHeartbeats 1000000

namespace Empiricist

/-- The GHZ3 graph is (equal to) the path graph on 3 vertices. -/
lemma GHZ3graph_eq_pathGraph3 : GHZ3graph = SimpleGraph.pathGraph 3 := by
  first
  | rfl
  | (ext a b
     fin_cases a <;> fin_cases b <;>
       simp [GHZ3graph, SimpleGraph.pathGraph_adj] <;>
       first
       | rfl
       | omega
       | decide
       | simp_all
       | tauto
       | trivial)
  | (ext a b
     fin_cases a <;> fin_cases b <;>
       simp [GHZ3graph, SimpleGraph.pathGraph_adj, SimpleGraph.fromEdgeSet_adj,
         Set.mem_insert_iff, Set.mem_singleton_iff, Sym2.eq_iff] <;>
       first
       | rfl
       | omega
       | decide
       | simp_all
       | tauto
       | trivial)
  | (ext a b
     constructor <;> intro h <;> fin_cases a <;> fin_cases b <;>
       simp_all [GHZ3graph, SimpleGraph.pathGraph_adj] <;>
       first
       | rfl
       | omega
       | decide
       | tauto
       | trivial)
  | (ext a b; revert a b; decide)

/-- The 3-vertex path is producible with zero fusions (it is the GHZ3 resource). -/
lemma pathGraph3_producible : ProducibleBy 0 (SimpleGraph.pathGraph 3) := by
  have h0 : ProducibleBy 0 GHZ3graph := by
    first
    | exact ProducibleBy.ghz3
    | exact ProducibleBy.base
    | exact ProducibleBy.ghz3graph
    | exact ProducibleBy.GHZ3graph
    | exact ProducibleBy.GHZ3
    | exact ProducibleBy.basic
    | exact ProducibleBy.init
    | constructor
  exact GHZ3graph_eq_pathGraph3 ▸ h0

/-- Attaching a pendant vertex at endpoint `0` of `pathGraph (n+1)` yields a graph
isomorphic to `pathGraph (n+2)`; the isomorphism is `(finSuccEquiv (n+1)).symm`,
sending the new pendant vertex `none` to `0` and `some i` to `i.succ`. -/
def pathPendantIso (n : ℕ) :
    addPendant (SimpleGraph.pathGraph (n + 1)) 0 ≃g SimpleGraph.pathGraph (n + 2) where
  toEquiv := (finSuccEquiv (n + 1)).symm
  map_rel_iff' := by
    intro a b
    cases a <;> cases b <;>
      first
      | exact iff_of_false (SimpleGraph.irrefl _) (SimpleGraph.irrefl _)
      | (simp [addPendant, SimpleGraph.pathGraph_adj, finSuccEquiv_symm_none,
           finSuccEquiv_symm_some, Fin.val_succ, Fin.val_zero] <;>
         first
         | omega
         | (simp only [Fin.ext_iff, Fin.val_zero, Fin.val_succ]
            omega)
         | (constructor <;> intro h <;> omega)
         | rfl
         | decide
         | tauto
         | simp_all
         | aesop)
      | (simp [addPendant_adj, SimpleGraph.pathGraph_adj, finSuccEquiv_symm_none,
           finSuccEquiv_symm_some, Fin.val_succ, Fin.val_zero] <;>
         first
         | omega
         | (simp only [Fin.ext_iff, Fin.val_zero, Fin.val_succ]
            omega)
         | rfl
         | decide
         | tauto
         | simp_all
         | aesop)
      | (simp only [finSuccEquiv_symm_none, finSuccEquiv_symm_some,
           SimpleGraph.pathGraph_adj, Fin.val_succ, Fin.val_zero, addPendant] <;>
         first
         | omega
         | (simp only [Fin.ext_iff, Fin.val_zero, Fin.val_succ]
            omega)
         | tauto
         | simp_all
         | aesop)
      | (simp_all [addPendant, SimpleGraph.pathGraph_adj, finSuccEquiv_symm_none,
           finSuccEquiv_symm_some, Fin.val_succ, Fin.val_zero] <;>
         first
         | omega
         | (simp only [Fin.ext_iff, Fin.val_zero, Fin.val_succ]
            omega)
         | tauto
         | aesop)

/-- Upper bound, uniform form: the path on `k + 3` vertices is producible with `k` fusions. -/
lemma pathGraph_producible : ∀ k : ℕ, ProducibleBy k (SimpleGraph.pathGraph (k + 3)) := by
  intro k
  induction k with
  | zero =>
    first
    | exact pathGraph3_producible
    | (show ProducibleBy 0 (SimpleGraph.pathGraph 3)
       exact pathGraph3_producible)
    | simpa using pathGraph3_producible
  | succ k ih =>
    -- one leaf-merge at endpoint 0
    have hMerge : ProducibleBy (k + 1) (ghz3LeafMerge (SimpleGraph.pathGraph (k + 3)) 0) := by
      first
      | exact ProducibleBy.merge ih 0
      | exact ProducibleBy.merge 0 ih
      | exact ProducibleBy.merge ih
      | exact ih.merge 0
      | exact ih.merge
      | exact ProducibleBy.merge (v := 0) ih
      | exact ProducibleBy.merge ih (v := 0)
      | (apply ProducibleBy.merge <;> first | exact ih | exact 0)
    -- transport along ghz3LeafMerge ≃g addPendant
    have e1 : ghz3LeafMerge (SimpleGraph.pathGraph (k + 3)) 0 ≃g
        addPendant (SimpleGraph.pathGraph (k + 3)) 0 := by
      first
      | exact ghz3LeafMerge_iso_addPendant (SimpleGraph.pathGraph (k + 3)) 0
      | exact ghz3LeafMerge_iso_addPendant _ _
      | exact ghz3LeafMerge_iso_addPendant _
      | exact ghz3LeafMerge_iso_addPendant
      | exact (ghz3LeafMerge_iso_addPendant (SimpleGraph.pathGraph (k + 3)) 0).symm
      | exact (ghz3LeafMerge_iso_addPendant _ _).symm
      | apply ghz3LeafMerge_iso_addPendant
    have hPend : ProducibleBy (k + 1) (addPendant (SimpleGraph.pathGraph (k + 3)) 0) := by
      first
      | exact ProducibleBy.iso hMerge e1
      | exact ProducibleBy.iso e1 hMerge
      | exact hMerge.iso e1
      | exact ProducibleBy.iso hMerge e1.symm
      | exact ProducibleBy.iso e1.symm hMerge
      | exact hMerge.iso e1.symm
    -- transport along addPendant (pathGraph (k+3)) 0 ≃g pathGraph (k+4)
    have e2 : addPendant (SimpleGraph.pathGraph (k + 3)) 0 ≃g
        SimpleGraph.pathGraph (k + 4) := pathPendantIso (k + 2)
    have hgoal : ProducibleBy (k + 1) (SimpleGraph.pathGraph (k + 4)) := by
      first
      | exact ProducibleBy.iso hPend e2
      | exact ProducibleBy.iso e2 hPend
      | exact hPend.iso e2
      | exact ProducibleBy.iso hPend e2.symm
      | exact ProducibleBy.iso e2.symm hPend
      | exact hPend.iso e2.symm
    have harith : k + 1 + 3 = k + 4 := by omega
    rw [harith]
    exact hgoal

/-- TARGET. For every `N ≥ 3`:
(1) the path graph on `N` vertices is producible with `N - 3` fusions, and
(2) `N - 3` is a lower bound for any admissible fusion cost schedule. -/
theorem pathGraph_min_fusions (N : ℕ) (hN : 3 ≤ N) :
    ProducibleBy (N - 3) (SimpleGraph.pathGraph N) ∧
      (∀ (g f : ℕ) (c : ℕ → ℕ),
        N + 2 * f = 3 * g → c 0 = g → c f = 1 →
        (∀ i, i < f → c i ≤ c (i + 1) + 1) → N - 3 ≤ f) := by
  constructor
  · have h := pathGraph_producible (N - 3)
    have hEq : N - 3 + 3 = N := by omega
    rw [hEq] at h
    exact h
  · intro g f c h1 h2 h3 h4
    first
    | exact fusion_cost_lower_bound N g f c h1 h2 h3 h4
    | exact fusion_cost_lower_bound h1 h2 h3 h4
    | exact fusion_cost_lower_bound g f c h1 h2 h3 h4
    | exact fusion_cost_lower_bound f c h1 h2 h3 h4
    | exact fusion_cost_lower_bound c h1 h2 h3 h4
    | exact fusion_cost_lower_bound N h1 h2 h3 h4
    | exact fusion_cost_lower_bound N c h1 h2 h3 h4
    | exact fusion_cost_lower_bound _ _ _ _ h1 h2 h3 h4
    | (apply fusion_cost_lower_bound <;> assumption)

end Empiricist

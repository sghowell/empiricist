/-
  STAR family K_{1,N-1}: exact fusion cost F(star_N) = N - 3.

  Statement `Empiricist.star_min_fusions`:
    for 3 ≤ N,
      (upper) ProducibleBy (N - 3) (starGraph N), and
      (lower) any monotone-by-≤1 fusion cost schedule c with resource balance
              N + 2*f = 3*g, c 0 = g, c f = 1 forces N - 3 ≤ f.

  Upper bound: induction — starGraph 3 ≅ GHZ3graph (swap 0 ↔ 1); each step is one
  `ghz3LeafMerge` at the center 0, which (via `ghz3LeafMerge_iso_addPendant` and the
  key sub-lemma `addPendantCenterIso`: pendant-at-center = bigger star) grows the star.
  Lower bound: from the trusted `Empiricist.fusion_cost_lower_bound` (with a
  self-contained arithmetic fallback proving the identical inequality).

  NOTE: runtime exceptions (maxRecDepth) escape `first`-combinators, so every branch
  below is loop-safe: `Fin.ext_iff` only ever occurs inside `simp only` with a fixed
  finite lemma list, never inside a full `simp` call.
-/
import EmpiricistLean.Foundation
import EmpiricistLean.LocalComp
import EmpiricistLean.FusionRule
import Mathlib.Combinatorics.SimpleGraph.Basic
import Mathlib.Combinatorics.SimpleGraph.Hasse
import Mathlib.Logic.Equiv.Fin.Basic
import Mathlib.Tactic.FinCases

set_option maxRecDepth 8000
set_option maxHeartbeats 800000

namespace Empiricist

/-- The star graph `K_{1,N-1}` on `Fin N` with center `0`: vertex `0` is adjacent to
every other vertex and there are no leaf–leaf edges. Uses `.val = 0` (total over `Nat`,
no `NeZero` needed). -/
def starGraph (N : Nat) : SimpleGraph (Fin N) where
  Adj i j := i ≠ j ∧ (i.val = 0 ∨ j.val = 0)
  symm := by
    first
    | -- `Std.Symm`-class shape with implicit vertex arguments.
      exact ⟨fun h => ⟨Ne.symm h.1, Or.symm h.2⟩⟩
    | -- `Std.Symm`-class shape with explicit vertex arguments.
      exact ⟨fun _ _ h => ⟨Ne.symm h.1, Or.symm h.2⟩⟩
    | (constructor
       intro i j h
       exact ⟨Ne.symm h.1, Or.symm h.2⟩)
    | -- Legacy `Symmetric Adj` shape.
      (intro i j h
       exact ⟨Ne.symm h.1, Or.symm h.2⟩)
    | exact fun i j h => ⟨Ne.symm h.1, Or.symm h.2⟩
  loopless := by
    first
    | -- `Std.Irrefl`-class shape: field `irrefl : ∀ a, ¬ r a a`.
      exact ⟨fun i h => h.1 rfl⟩
    | (constructor
       intro i h
       exact h.1 rfl)
    | -- Legacy `Irreflexive Adj` shape.
      (intro i h
       exact h.1 rfl)
    | exact fun i h => h.1 rfl

@[simp] theorem starGraph_adj {N : Nat} {i j : Fin N} :
    (starGraph N).Adj i j ↔ i ≠ j ∧ (i.val = 0 ∨ j.val = 0) :=
  Iff.rfl

/-- `GHZ3graph` (the 3-vertex path = 3-vertex star with center `1`) is isomorphic to
`starGraph 3` via swapping `0 ↔ 1`; the swap moves the center to `0`. -/
def ghz3IsoStar3 : GHZ3graph ≃g starGraph 3 where
  toEquiv := Equiv.swap 0 1
  map_rel_iff' := by
    intro a b
    first
    | -- Preferred route: register decidability for both adjacency relations, then
      -- settle each of the 9 cases by kernel computation.
      (haveI : DecidableRel (starGraph 3).Adj := fun i j =>
         inferInstanceAs (Decidable (i ≠ j ∧ (i.val = 0 ∨ j.val = 0)))
       haveI : DecidableRel GHZ3graph.Adj := fun u v =>
         decidable_of_iff (u.val + 1 = v.val ∨ v.val + 1 = u.val)
           SimpleGraph.pathGraph_adj.symm
       fin_cases a <;> fin_cases b <;> decide)
    | -- Full simp, but WITHOUT `Fin.ext_iff` (loop-safe).
      (fin_cases a <;> fin_cases b <;>
         simp [GHZ3graph, starGraph_adj, SimpleGraph.pathGraph_adj,
           Equiv.swap_apply_def])
    | -- Full simp with decide-postprocessing (loop-safe: no `Fin.ext_iff`).
      (fin_cases a <;> fin_cases b <;>
         simp +decide [GHZ3graph, starGraph_adj, SimpleGraph.pathGraph_adj,
           Equiv.swap_apply_def])
    | -- `simp only` with an explicit finite lemma list, then omega (loop-safe).
      (fin_cases a <;> fin_cases b <;>
         (simp only [GHZ3graph, starGraph_adj, SimpleGraph.pathGraph_adj,
            Equiv.swap_apply_def, Fin.ext_iff, ne_eq]
          omega))
    | -- Diagnostic tail: on failure this reveals the unfolded definition of GHZ3graph.
      (fin_cases a <;> fin_cases b <;> (unfold GHZ3graph; rfl))

/-- `addPendant` adjacency, old–old vertices: exactly the old edges. -/
theorem pendant_adj_some_some (k : Nat) (x y : Fin (k + 3)) :
    (addPendant (starGraph (k + 3)) (0 : Fin (k + 3))).Adj (some x) (some y) ↔
      (starGraph (k + 3)).Adj x y := by
  first
  | exact Iff.rfl
  | simp only [addPendant_adj]
  | simp [addPendant_adj]
  | simp [addPendant]
  | (unfold addPendant; simp)
  | -- Diagnostic tail: `exact trivial` fails printing the (unfolded) goal.
    ((try unfold addPendant); exact trivial)

/-- `addPendant` adjacency, new pendant vertex to old vertex: only the attachment
point (the star center `0`). -/
theorem pendant_adj_none_some (k : Nat) (y : Fin (k + 3)) :
    (addPendant (starGraph (k + 3)) (0 : Fin (k + 3))).Adj none (some y) ↔
      y = (0 : Fin (k + 3)) := by
  first
  | exact Iff.rfl
  | simp only [addPendant_adj]
  | simp [addPendant_adj]
  | simp [addPendant_adj, eq_comm]
  | simp [addPendant]
  | simp [addPendant, eq_comm]
  | (unfold addPendant; simp)
  | (unfold addPendant; simp [eq_comm])
  | ((try unfold addPendant); exact trivial)

/-- `addPendant` adjacency, old vertex to new pendant vertex: only the attachment
point (the star center `0`). -/
theorem pendant_adj_some_none (k : Nat) (x : Fin (k + 3)) :
    (addPendant (starGraph (k + 3)) (0 : Fin (k + 3))).Adj (some x) none ↔
      x = (0 : Fin (k + 3)) := by
  first
  | exact Iff.rfl
  | simp only [addPendant_adj]
  | simp [addPendant_adj]
  | simp [addPendant_adj, eq_comm]
  | simp [addPendant]
  | simp [addPendant, eq_comm]
  | (unfold addPendant; simp)
  | (unfold addPendant; simp [eq_comm])
  | ((try unfold addPendant); exact trivial)

/-- KEY SUB-LEMMA: attaching a pendant at the center `0` of `starGraph (k+3)` yields
exactly `starGraph (k+4)` — via `finSuccEquivLast.symm : Option (Fin (k+3)) ≃ Fin (k+4)`,
which embeds the old vertices by `castSucc` and sends the new pendant vertex (`none`)
to `Fin.last`, the new leaf of the bigger star. -/
def addPendantCenterIso (k : Nat) :
    addPendant (starGraph (k + 3)) (0 : Fin (k + 3)) ≃g starGraph (k + 4) where
  toEquiv := finSuccEquivLast.symm
  map_rel_iff' := by
    intro a b
    have hnone : (finSuccEquivLast.symm none : Fin (k + 4)) = Fin.last (k + 3) := by
      first
      | exact finSuccEquivLast_symm_none
      | simp
      | rfl
    have hsome : ∀ z : Fin (k + 3),
        (finSuccEquivLast.symm (some z) : Fin (k + 4)) = Fin.castSucc z := by
      intro z
      first
      | exact finSuccEquivLast_symm_some z
      | simp
      | rfl
    rcases a with _ | x <;> rcases b with _ | y
    · -- none / none: both sides are non-edges (irreflexivity).
      first
      | exact iff_of_false (fun h => (starGraph_adj.mp h).1 rfl)
          ((addPendant (starGraph (k + 3)) (0 : Fin (k + 3))).irrefl)
      | exact iff_of_false (fun h => (starGraph_adj.mp h).1 rfl)
          ((addPendant (starGraph (k + 3)) (0 : Fin (k + 3))).loopless none)
    · -- none / some y: pendant (= Fin.last, a leaf) touches exactly the center 0.
      rw [hnone, hsome y, pendant_adj_none_some k y]
      have hy := y.isLt
      first
      | (simp only [starGraph_adj, ne_eq, Fin.ext_iff, Fin.val_last, Fin.coe_castSucc,
           Fin.val_zero]
         omega)
      | (simp only [starGraph_adj, ne_eq, ← Fin.val_inj, Fin.val_last, Fin.coe_castSucc,
           Fin.val_zero]
         omega)
    · -- some x / none: symmetric to the previous case.
      rw [hsome x, hnone, pendant_adj_some_none k x]
      have hx := x.isLt
      first
      | (simp only [starGraph_adj, ne_eq, Fin.ext_iff, Fin.val_last, Fin.coe_castSucc,
           Fin.val_zero]
         omega)
      | (simp only [starGraph_adj, ne_eq, ← Fin.val_inj, Fin.val_last, Fin.coe_castSucc,
           Fin.val_zero]
         omega)
    · -- some x / some y: castSucc preserves values, so both sides coincide.
      rw [hsome x, hsome y, pendant_adj_some_some k x y]
      first
      | (simp only [starGraph_adj, ne_eq, Fin.ext_iff, Fin.coe_castSucc, Fin.val_zero]
         try omega)
      | (simp only [starGraph_adj, ne_eq, ← Fin.val_inj, Fin.coe_castSucc, Fin.val_zero]
         try omega)

/-- Upper bound, in induction-friendly form: the star on `k + 3` vertices is producible
with `k` fusions. Base: `starGraph 3 ≅ GHZ3graph`. Step: one `ghz3LeafMerge` at the
center `0`, then transport along `ghz3LeafMerge ≅ addPendant ≅ bigger star`. -/
theorem star_producible (k : Nat) : ProducibleBy k (starGraph (k + 3)) := by
  induction k with
  | zero =>
    show ProducibleBy 0 (starGraph 3)
    have hbase : ProducibleBy 0 GHZ3graph := by
      first
      | exact ghz3_producible
      | exact GHZ3_producible
      | exact GHZ3graph_producible
      | exact ghz3Producible
      | exact producible_ghz3
      | exact producibleBy_ghz3
      | exact ghz3_producibleBy
      | exact producibleBy_zero_ghz3
      | exact ProducibleBy.ghz3
      | exact ProducibleBy.ghz3 _
      | exact ProducibleBy.ghz3 _ _
      | exact ProducibleBy.GHZ3
      | exact ProducibleBy.base
      | exact ProducibleBy.base _
      | exact ProducibleBy.zero
      | exact ProducibleBy.zero _
      | exact ProducibleBy.refl
      | exact ProducibleBy.self
      | (constructor; done)
      | (constructor <;> first | exact SimpleGraph.Iso.refl _ | rfl | trivial)
      | -- Diagnostic tail: on failure this prints the full signature of the
        -- foundation's `ProducibleBy.iso`, revealing the API shape.
        exact @ProducibleBy.iso
    first
    | exact hbase.iso ghz3IsoStar3
    | exact hbase.iso ghz3IsoStar3.symm
    | exact ProducibleBy.iso ghz3IsoStar3 hbase
    | exact ProducibleBy.iso ghz3IsoStar3.symm hbase
    | exact ProducibleBy.iso _ _ ghz3IsoStar3 hbase
    | exact ProducibleBy.iso _ _ hbase ghz3IsoStar3
  | succ k ih =>
    show ProducibleBy (k + 1) (starGraph (k + 4))
    have step :
        ghz3LeafMerge (starGraph (k + 3)) (0 : Fin (k + 3)) ≃g starGraph (k + 4) := by
      first
      | exact (ghz3LeafMerge_iso_addPendant (starGraph (k + 3)) (0 : Fin (k + 3))).trans
          (addPendantCenterIso k)
      | exact (ghz3LeafMerge_iso_addPendant _ _).trans (addPendantCenterIso k)
      | exact RelIso.trans ghz3LeafMerge_iso_addPendant (addPendantCenterIso k)
      | exact ((ghz3LeafMerge_iso_addPendant (starGraph (k + 3)) (0 : Fin (k + 3))).symm).trans
          (addPendantCenterIso k)
      | exact ((ghz3LeafMerge_iso_addPendant _ _).symm).trans (addPendantCenterIso k)
    have hmerge :
        ProducibleBy (k + 1) (ghz3LeafMerge (starGraph (k + 3)) (0 : Fin (k + 3))) := by
      first
      | exact ih.merge (0 : Fin (k + 3))
      | exact ih.merge _
      | exact ih.merge
      | exact ProducibleBy.merge _ _ ih
      | exact ProducibleBy.merge _ ih _
      | exact ProducibleBy.merge _ ih
      | exact ProducibleBy.merge _ _ _ ih
      | exact ProducibleBy.merge _ _ ih _
      | exact ProducibleBy.merge ih _
      | exact ProducibleBy.merge ih
      | exact ProducibleBy.merge (0 : Fin (k + 3)) ih
      | exact ProducibleBy.merge (starGraph (k + 3)) (0 : Fin (k + 3)) ih
      | exact ProducibleBy.merge (starGraph (k + 3)) ih (0 : Fin (k + 3))
      | (apply ProducibleBy.merge <;>
           first
           | exact ih
           | exact (0 : Fin (k + 3))
           | exact starGraph (k + 3)
           | infer_instance)
      | -- Diagnostic tail: on failure this prints the full signature of
        -- `ProducibleBy.merge`, revealing the exact argument order.
        exact @ProducibleBy.merge
    first
    | exact hmerge.iso step
    | exact hmerge.iso step.symm
    | exact ProducibleBy.iso step hmerge
    | exact ProducibleBy.iso step.symm hmerge
    | exact ProducibleBy.iso _ _ step hmerge
    | exact ProducibleBy.iso _ _ hmerge step

/-- MAIN THEOREM: `F(star_N) = N - 3` for the star family `K_{1,N-1}`, `3 ≤ N`.
Upper conjunct: `starGraph N` is producible with `N - 3` fusions.
Lower conjunct (general lower bound, visible in the type): any fusion schedule with
resource balance `N + 2*f = 3*g`, initial count `g`, final count `1`, and per-step
decrease at most `1`, needs at least `N - 3` fusions. -/
theorem star_min_fusions (N : Nat) (hN : 3 ≤ N) :
    ProducibleBy (N - 3) (starGraph N) ∧
      ∀ (g f : Nat) (c : Nat → Nat),
        N + 2 * f = 3 * g → c 0 = g → c f = 1 →
        (∀ i, i < f → c i ≤ c (i + 1) + 1) → N - 3 ≤ f := by
  refine ⟨?_, ?_⟩
  · -- Upper bound: specialize the induction with N = k + 3.
    obtain ⟨k, rfl⟩ : ∃ k, N = k + 3 := ⟨N - 3, by omega⟩
    have hk : k + 3 - 3 = k := by omega
    rw [hk]
    exact star_producible k
  · -- Lower bound: immediate from the trusted foundation lemma
    -- `Empiricist.fusion_cost_lower_bound` (with a self-contained arithmetic fallback).
    intro g f c hbal h0 hf hstep
    first
    | exact fusion_cost_lower_bound N g f c hbal h0 hf hstep
    | exact fusion_cost_lower_bound hbal h0 hf hstep
    | exact fusion_cost_lower_bound _ _ _ _ hbal h0 hf hstep
    | exact fusion_cost_lower_bound N f g c hbal h0 hf hstep
    | (-- Self-contained proof of the same inequality:
       -- each step drops the count by at most 1, so c 0 ≤ c f + f, i.e. g ≤ 1 + f;
       -- then N + 2f = 3g ≤ 3f + 3 gives N - 3 ≤ f.
       have key : ∀ m, m ≤ f → c (f - m) ≤ c f + m := by
         intro m
         induction m with
         | zero =>
           intro _
           have hz : f - 0 = f := Nat.sub_zero f
           rw [hz]
           omega
         | succ m ihm =>
           intro hm
           have h1 : f - (m + 1) < f := by omega
           have h2 := hstep (f - (m + 1)) h1
           have h3 : f - (m + 1) + 1 = f - m := by omega
           rw [h3] at h2
           have h4 := ihm (by omega)
           omega
       have h5 := key f (Nat.le_refl f)
       rw [Nat.sub_self] at h5
       omega)

end Empiricist

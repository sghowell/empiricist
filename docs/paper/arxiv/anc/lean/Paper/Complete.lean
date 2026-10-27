import Mathlib.Combinatorics.SimpleGraph.Acyclic
import EmpiricistLean.Basic
import EmpiricistLean.Foundation
import EmpiricistLean.LocalComp
import EmpiricistLean.FusionRule
import EmpiricistLean.TreeThm

namespace Empiricist

/-- The star graph on `Fin N` with center the vertex of value `0`:
`i` and `j` are adjacent iff they are distinct and one of them is the center. -/
def starGraph (N : ℕ) : SimpleGraph (Fin N) where
  Adj i j := i ≠ j ∧ (i.val = 0 ∨ j.val = 0)
  symm := by
    first
      | exact fun i j h => ⟨h.1.symm, h.2.symm⟩
      | exact ⟨fun i j h => ⟨h.1.symm, h.2.symm⟩⟩
      | exact ⟨fun h => ⟨h.1.symm, h.2.symm⟩⟩
      | (constructor; intro i j h; exact ⟨h.1.symm, h.2.symm⟩)
      | (intro i j h; exact ⟨h.1.symm, h.2.symm⟩)
      | aesop_graph
  loopless := by
    first
      | exact fun i h => h.1 rfl
      | exact ⟨fun i h => h.1 rfl⟩
      | exact ⟨fun h => h.1 rfl⟩
      | (constructor; intro i h; exact h.1 rfl)
      | (intro i h; exact h.1 rfl)
      | aesop_graph

@[simp] lemma starGraph_adj {N : ℕ} (a b : Fin N) :
    (starGraph N).Adj a b ↔ a ≠ b ∧ (a.val = 0 ∨ b.val = 0) := Iff.rfl

instance (N : ℕ) : DecidableRel (starGraph N).Adj := fun a b =>
  decidable_of_iff _ (starGraph_adj a b).symm

/-- The star graph is a tree (for nonempty vertex set): connected through the
center, and acyclic since every edge contains the center. -/
lemma starGraph_isTree (N : ℕ) (hN : 1 ≤ N) : (starGraph N).IsTree := by
  have hpos : 0 < N := hN
  constructor
  · -- connected: every vertex reaches the center
    have hreach : ∀ w : Fin N, (starGraph N).Reachable w ⟨0, hpos⟩ := by
      intro w
      by_cases hw : w = ⟨0, hpos⟩
      · subst hw; exact SimpleGraph.Reachable.refl _
      · exact SimpleGraph.Adj.reachable ((starGraph_adj w ⟨0, hpos⟩).mpr ⟨hw, Or.inr rfl⟩)
    have hne : Nonempty (Fin N) := ⟨⟨0, hpos⟩⟩
    have hpre : (starGraph N).Preconnected := fun u v => (hreach u).trans (hreach v).symm
    first
      | exact SimpleGraph.Connected.mk hpre
      | exact SimpleGraph.Connected.mk hpre hne
      | exact ⟨hpre, hne⟩
      | exact ⟨hpre⟩
      | (constructor; exact hpre)
  · -- acyclic: a cycle has ≥ 3 edges, but every edge contains the center,
    -- which forces a repetition in the (nodup) cycle support.
    intro v p hp
    have hlen := hp.three_le_length
    have hnodup := hp.support_nodup
    cases p with
    | nil =>
      simp only [SimpleGraph.Walk.length_nil] at hlen
      omega
    | cons h q =>
      rename_i a
      cases q with
      | nil =>
        simp only [SimpleGraph.Walk.length_cons, SimpleGraph.Walk.length_nil] at hlen
        omega
      | cons h₂ r =>
        rename_i b
        simp only [SimpleGraph.Walk.support_cons, List.tail_cons, List.nodup_cons] at hnodup
        obtain ⟨hans, hrnd⟩ := hnodup
        rw [starGraph_adj] at h h₂
        obtain ⟨hva, hv0⟩ := h
        obtain ⟨hab, hab0⟩ := h₂
        by_cases hA : a.val = 0
        · -- second vertex is the center; the third vertex is a leaf whose next
          -- neighbour must be the center again: support repetition.
          have hb0 : b.val ≠ 0 := fun hb => hab (Fin.ext (by omega))
          cases r with
          | nil =>
            simp only [SimpleGraph.Walk.length_cons, SimpleGraph.Walk.length_nil] at hlen
            omega
          | cons h₃ s =>
            rename_i c
            rw [starGraph_adj] at h₃
            obtain ⟨hbc, hbc0⟩ := h₃
            have hc0 : c.val = 0 := hbc0.resolve_left hb0
            have hca : c = a := Fin.ext (by omega)
            apply hans
            rw [SimpleGraph.Walk.support_cons]
            exact List.mem_cons_of_mem _ (by rw [← hca]; exact s.start_mem_support)
        · -- first vertex is the center and the third vertex is the center again:
          -- the start vertex reappears inside the tail support.
          have hb0 : b.val = 0 := hab0.resolve_left hA
          have hv0' : v.val = 0 := hv0.resolve_right hA
          have hbv : b = v := Fin.ext (by omega)
          cases r with
          | nil =>
            simp only [SimpleGraph.Walk.length_cons, SimpleGraph.Walk.length_nil] at hlen
            omega
          | cons h₃ s =>
            simp only [SimpleGraph.Walk.support_cons, List.nodup_cons] at hrnd
            exact hrnd.1 (by rw [hbv]; exact s.end_mem_support)

/-- If a cost function drops by at most 1 per step, then over `f` steps it drops
by at most `f`. -/
lemma cost_descent (c : ℕ → ℕ) :
    ∀ f : ℕ, (∀ i, i < f → c i ≤ c (i + 1) + 1) → c 0 ≤ c f + f := by
  intro f
  induction f with
  | zero => intro _; omega
  | succ n ih =>
    intro h
    have h1 : c 0 ≤ c n + n := ih (fun i hi => h i (Nat.lt_succ_of_lt hi))
    have h2 : c n ≤ c (n + 1) + 1 := h n (Nat.lt_succ_self n)
    omega

/-- Local complementation of the star at its center yields the complete graph:
the center's neighbourhood is all leaves, pairwise non-adjacent, and toggling
makes them pairwise adjacent. -/
lemma localComplement_star {N : ℕ} (c : Fin N) (hc : c.val = 0) :
    localComplement (starGraph N) c = SimpleGraph.completeGraph (Fin N) := by
  ext a b
  rw [localComplement_adj]
  have hK : (SimpleGraph.completeGraph (Fin N)).Adj a b ↔ a ≠ b := by
    first
      | exact SimpleGraph.top_adj
      | exact Iff.rfl
      | simp [SimpleGraph.completeGraph]
      | (rw [SimpleGraph.completeGraph_eq_top]; exact SimpleGraph.top_adj)
  rw [hK]
  unfold Xor'
  constructor
  · -- either star-adjacent (hence distinct) or toggled (hence distinct)
    rintro (⟨h1, -⟩ | ⟨h1, -⟩)
    · exact ((starGraph_adj a b).mp h1).1
    · exact h1.1
  · intro hab
    by_cases h0 : a.val = 0 ∨ b.val = 0
    · -- an edge touching the center: star-adjacent, and NOT toggled
      -- (since a center endpoint cannot also be a leaf-neighbour of the center)
      left
      refine ⟨(starGraph_adj a b).mpr ⟨hab, h0⟩, ?_⟩
      rintro ⟨-, hac, hbc⟩
      rcases h0 with h | h
      · exact ((starGraph_adj a c).mp hac).1 (Fin.ext (h.trans hc.symm))
      · exact ((starGraph_adj b c).mp hbc).1 (Fin.ext (h.trans hc.symm))
    · -- two leaves: not star-adjacent, but both adjacent to the center,
      -- so the toggle makes them adjacent
      push_neg at h0
      right
      refine ⟨⟨hab, (starGraph_adj a c).mpr ⟨?_, Or.inr hc⟩,
          (starGraph_adj b c).mpr ⟨?_, Or.inr hc⟩⟩, ?_⟩
      · intro h
        exact h0.1 (by rw [h]; exact hc)
      · intro h
        exact h0.2 (by rw [h]; exact hc)
      · intro h
        rcases ((starGraph_adj a b).mp h).2 with h' | h'
        · exact h0.1 h'
        · exact h0.2 h'

/-- **F(K_N) = N - 3.** The complete graph on `N ≥ 3` qubits is producible up to
local complementation with `N - 3` fusions (witness: the star graph, one local
complementation away from `K_N`), and `N - 3` is a lower bound for any fusion
schedule (counted by any admissible cost function). -/
theorem complete_min_fusions (N : ℕ) (hN : 3 ≤ N) :
    ProducibleUpToLC (N - 3) (SimpleGraph.completeGraph (Fin N)) ∧
      ∀ (g f : ℕ) (c : ℕ → ℕ),
        N + 2 * f = 3 * g → c 0 = g → c f = 1 →
          (∀ i, i < f → c i ≤ c (i + 1) + 1) → N - 3 ≤ f := by
  have hpos : 0 < N := by omega
  constructor
  · -- upper bound: the star tree construction, then one local complementation
    have hTree : (starGraph N).IsTree := starGraph_isTree N (by omega)
    have hprod : ProducibleBy (N - 3) (starGraph N) := by
      first
        | exact producibleBy_tree hTree hN
        | exact producibleBy_tree hTree
        | exact producibleBy_tree hN hTree
        | exact producibleBy_tree (starGraph N) hTree hN
        | exact producibleBy_tree N (starGraph N) hTree hN
        | exact producibleBy_tree N hN (starGraph N) hTree
        | exact producibleBy_tree _ hTree hN
        | (have h := producibleBy_tree hTree (by simpa using hN); simpa using h)
        | (have h := producibleBy_tree hTree; simpa using h (by simpa using hN))
        | (apply producibleBy_tree <;>
            first
              | exact hTree
              | exact hN
              | simpa using hN
              | exact hpos
              | assumption
              | infer_instance)
        | exact (tree_min_fusions N hN (starGraph N) hTree).1
        | exact (tree_min_fusions hTree hN).1
        | exact (tree_min_fusions hN hTree).1
        | exact (tree_min_fusions (starGraph N) hTree hN).1
        | exact (tree_min_fusions N (starGraph N) hTree hN).1
    have hEq : localComplement (starGraph N) ⟨0, hpos⟩ = SimpleGraph.completeGraph (Fin N) :=
      localComplement_star ⟨0, hpos⟩ rfl
    refine ⟨starGraph N, hprod, ?_⟩
    rw [← hEq]
    first
      | exact lcEquiv_localComplement _ _
      | exact lcEquiv_localComplement (starGraph N) ⟨0, hpos⟩
      | exact lcEquiv_localComplement _
      | exact lcEquiv_localComplement ⟨0, hpos⟩ (starGraph N)
      | exact lcEquiv_equivalence.symm (lcEquiv_localComplement _ _)
      | exact (lcEquiv_equivalence _).symm (lcEquiv_localComplement _ _)
      | exact (lcEquiv_equivalence _ _).symm (lcEquiv_localComplement _ _)
      | exact lcEquiv_equivalence.symm (lcEquiv_localComplement _)
      | exact (lcEquiv_equivalence _).symm (lcEquiv_localComplement _)
  · -- lower bound: from the trusted foundation (with a self-contained fallback)
    intro g f c hc1 hc2 hc3 hc4
    have hle : c 0 ≤ c f + f := cost_descent c f hc4
    first
      | exact fusion_cost_lower_bound N g f c hc1 hc2 hc3 hc4
      | exact fusion_cost_lower_bound hc1 hc2 hc3 hc4
      | exact fusion_cost_lower_bound g f c hc1 hc2 hc3 hc4
      | exact fusion_cost_lower_bound N f g c hc1 hc2 hc3 hc4
      | omega

end Empiricist

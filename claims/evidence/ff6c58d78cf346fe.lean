/-
  EmpiricistLean.BipartiteThm

  F(K_{m,n}) = N - 3 for the complete bipartite graph, N = m + n.

  Upper bound: K_{m,n} is LC-equivalent (via the verified sequence
  τ₀, τ_m, τ₀ of local complementations) to the double-star caterpillar
  tree `doubleStar m n`, which is producible with N - 3 fusions by the
  general tree theorem.  Lower bound: the counting argument
  `fusion_cost_lower_bound` from the foundation.

  This module REUSES the shared foundation: localComplement / LCStep /
  LCEquiv / lcEquiv_equivalence / lcEquiv_localComplement / doubleStar /
  doubleStar_isTree / ProducibleBy / ProducibleUpToLC / producibleBy_tree /
  fusion_cost_lower_bound all come from the imports.  Only
  `completeBipartite` and the intermediate LC stage graphs are defined here.
-/
import Mathlib.Combinatorics.SimpleGraph.Acyclic
import EmpiricistLean.Basic
import EmpiricistLean.Foundation
import EmpiricistLean.LocalComp
import EmpiricistLean.FusionRule
import EmpiricistLean.DoubleStar
import EmpiricistLean.TreeThm

namespace Empiricist

/-- The complete bipartite graph `K_{m,n}` on `Fin (m + n)`, with parts
`A = {0, …, m-1}` and `B = {m, …, m+n-1}`. -/
def completeBipartite (m n : ℕ) : SimpleGraph (Fin (m + n)) where
  Adj i j := decide ((i : ℕ) < m) ≠ decide ((j : ℕ) < m)
  symm := by
    constructor
    intro i j h
    exact Ne.symm h
  loopless := by
    constructor
    intro i h
    exact h rfl

@[simp] theorem completeBipartite_adj (m n : ℕ) (i j : Fin (m + n)) :
    (completeBipartite m n).Adj i j ↔
      decide ((i : ℕ) < m) ≠ decide ((j : ℕ) < m) :=
  Iff.rfl

/-- Unfolding lemma for the imported `localComplement` (definitional). -/
theorem localComplement_adj' {V : Type*} (G : SimpleGraph V) (v x y : V) :
    (localComplement G v).Adj x y ↔
      Xor' (G.Adj x y) (x ≠ y ∧ G.Adj x v ∧ G.Adj y v) :=
  Iff.rfl

/-- Unfolding lemma for `Xor'` (definitional). -/
theorem xorIff (a b : Prop) : Xor' a b ↔ (a ∧ ¬ b) ∨ (b ∧ ¬ a) :=
  Iff.rfl

/-- Unfolding lemma for the imported `doubleStar` (definitional): centres `0`
and `m` are adjacent, `0` is adjacent to everything `≤ m`, and `m` is adjacent
to everything `≥ m`. -/
theorem doubleStar_adj' (m n : ℕ) (i j : Fin (m + n)) :
    (doubleStar m n).Adj i j ↔
      i ≠ j ∧ (((i : ℕ) = 0 ∧ (j : ℕ) ≤ m) ∨ ((j : ℕ) = 0 ∧ (i : ℕ) ≤ m) ∨
        ((i : ℕ) = m ∧ m ≤ (j : ℕ)) ∨ ((j : ℕ) = m ∧ m ≤ (i : ℕ))) :=
  Iff.rfl

instance instDecidableRelDoubleStarAdj (m n : ℕ) :
    DecidableRel (doubleStar m n).Adj := fun i j =>
  decidable_of_iff _ (doubleStar_adj' m n i j).symm

/-- The graph obtained from `K_{m,n}` by local complementation at `0`:
the complete bipartite graph together with a clique on the bottom part `B`. -/
def bipStage1 (m n : ℕ) : SimpleGraph (Fin (m + n)) where
  Adj i j := i ≠ j ∧ (m ≤ (i : ℕ) ∨ m ≤ (j : ℕ))
  symm := by
    constructor
    intro i j h
    exact ⟨h.1.symm, h.2.symm⟩
  loopless := by
    constructor
    intro i h
    exact h.1 rfl

@[simp] theorem bipStage1_adj (m n : ℕ) (i j : Fin (m + n)) :
    (bipStage1 m n).Adj i j ↔ i ≠ j ∧ (m ≤ (i : ℕ) ∨ m ≤ (j : ℕ)) :=
  Iff.rfl

/-- The graph obtained from `bipStage1` by local complementation at `m`:
a clique on `A ∪ {m}` together with `m` joined to every other vertex. -/
def bipStage2 (m n : ℕ) : SimpleGraph (Fin (m + n)) where
  Adj i j := i ≠ j ∧ ((i : ℕ) = m ∨ (j : ℕ) = m ∨ ((i : ℕ) < m ∧ (j : ℕ) < m))
  symm := by
    constructor
    intro i j h
    obtain ⟨h1, h2 | h2 | ⟨h2, h3⟩⟩ := h
    · exact ⟨h1.symm, Or.inr (Or.inl h2)⟩
    · exact ⟨h1.symm, Or.inl h2⟩
    · exact ⟨h1.symm, Or.inr (Or.inr ⟨h3, h2⟩)⟩
  loopless := by
    constructor
    intro i h
    exact h.1 rfl

@[simp] theorem bipStage2_adj (m n : ℕ) (i j : Fin (m + n)) :
    (bipStage2 m n).Adj i j ↔
      i ≠ j ∧ ((i : ℕ) = m ∨ (j : ℕ) = m ∨ ((i : ℕ) < m ∧ (j : ℕ) < m)) :=
  Iff.rfl

set_option maxHeartbeats 800000 in
/-- First LC step: local complementation of `K_{m,n}` at vertex `0`. -/
theorem lc_completeBipartite (m n : ℕ) (hm : 1 ≤ m)
    (v0 : Fin (m + n)) (h0 : (v0 : ℕ) = 0) :
    localComplement (completeBipartite m n) v0 = bipStage1 m n := by
  ext x y
  simp only [localComplement_adj', xorIff, completeBipartite_adj, bipStage1_adj,
    ne_eq, decide_eq_decide, Fin.ext_iff, h0]
  omega

set_option maxHeartbeats 800000 in
/-- Second LC step: local complementation of `bipStage1` at vertex `m`. -/
theorem lc_bipStage1 (m n : ℕ) (vm : Fin (m + n)) (hmv : (vm : ℕ) = m) :
    localComplement (bipStage1 m n) vm = bipStage2 m n := by
  ext x y
  simp only [localComplement_adj', xorIff, bipStage1_adj, bipStage2_adj, ne_eq,
    Fin.ext_iff, hmv]
  omega

set_option maxHeartbeats 800000 in
/-- Third LC step: local complementation of `bipStage2` at vertex `0` yields
the imported double star. -/
theorem lc_bipStage2 (m n : ℕ) (hm : 1 ≤ m)
    (v0 : Fin (m + n)) (h0 : (v0 : ℕ) = 0) :
    localComplement (bipStage2 m n) v0 = doubleStar m n := by
  ext x y
  simp only [localComplement_adj', xorIff, bipStage2_adj, doubleStar_adj', ne_eq,
    Fin.ext_iff, h0]
  omega

/-- The complete bipartite graph `K_{m,n}` (with `m, n ≥ 1`) is
local-complementation-equivalent to the double-star caterpillar, via the
verified LC sequence τ₀, τ_m, τ₀. -/
theorem bipartite_lcEquiv_doubleStar (m n : ℕ) (hm : 1 ≤ m) (hn : 1 ≤ n) :
    LCEquiv (completeBipartite m n) (doubleStar m n) := by
  have h0mn : 0 < m + n := by omega
  have hmmn : m < m + n := by omega
  have e1 : localComplement (completeBipartite m n) ⟨0, h0mn⟩ = bipStage1 m n :=
    lc_completeBipartite m n hm ⟨0, h0mn⟩ rfl
  have e2 : localComplement (bipStage1 m n) ⟨m, hmmn⟩ = bipStage2 m n :=
    lc_bipStage1 m n ⟨m, hmmn⟩ rfl
  have e3 : localComplement (bipStage2 m n) ⟨0, h0mn⟩ = doubleStar m n :=
    lc_bipStage2 m n hm ⟨0, h0mn⟩ rfl
  have h1 : LCEquiv (completeBipartite m n) (bipStage1 m n) := by
    rw [← e1]; apply lcEquiv_localComplement
  have h2 : LCEquiv (bipStage1 m n) (bipStage2 m n) := by
    rw [← e2]; apply lcEquiv_localComplement
  have h3 : LCEquiv (bipStage2 m n) (doubleStar m n) := by
    rw [← e3]; apply lcEquiv_localComplement
  exact lcEquiv_equivalence.trans (lcEquiv_equivalence.trans h1 h2) h3

/-- **Main theorem.**  `F(K_{m,n}) = (m+n) - 3`:  the complete bipartite
graph on `N = m + n ≥ 3` vertices (with `m, n ≥ 1`) is producible up to local
complementation with `N - 3` fusions, and no schedule with fewer fusions is
possible (counting lower bound). -/
theorem completeBipartite_min_fusions (m n : ℕ) (hm : 1 ≤ m) (hn : 1 ≤ n) (hN : 3 ≤ m + n) :
    ProducibleUpToLC ((m + n) - 3) (completeBipartite m n) ∧
      ∀ (g f : ℕ) (c : ℕ → ℕ), (m + n) + 2 * f = 3 * g → c 0 = g → c f = 1 →
        (∀ i, i < f → c i ≤ c (i + 1) + 1) → (m + n) - 3 ≤ f := by
  constructor
  · -- Upper bound: produce the double star (a tree) with N - 3 fusions,
    -- then transport across the LC equivalence.
    have hTree : (doubleStar m n).IsTree := doubleStar_isTree m n hm hn
    have hcard : Fintype.card (Fin (m + n)) = m + n := by simp
    have hprod : ProducibleBy ((m + n) - 3) (doubleStar m n) :=
      producibleBy_tree (m + n) (doubleStar m n) hcard hTree hN
    exact ⟨doubleStar m n, hprod,
      lcEquiv_equivalence.symm (bipartite_lcEquiv_doubleStar m n hm hn)⟩
  · -- Lower bound: the counting argument.
    intro g f c hq h0 hf hstep
    exact fusion_cost_lower_bound (m + n) g f c hN hq h0 hf hstep

end Empiricist
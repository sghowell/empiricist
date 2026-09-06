import Mathlib.Data.Matrix.Basic
import Mathlib.LinearAlgebra.UnitaryGroup
import Mathlib.Data.Finset.Card
import Mathlib.Tactic.FinCases
import EmpiricistLean.Basic
import EmpiricistLean.P3Amplitudes
import EmpiricistLean.P3Pauli
import EmpiricistLean.P3L1
import EmpiricistLean.P3L2
import EmpiricistLean.P3Counting
import EmpiricistLean.P3Bridge

namespace Empiricist

/-- CASE a (DoubledEdges): the four detectors split into two pairs sharing the
same 2-element label set, and the two label sets are disjoint. By the bridge
(`identifies_rowDecouples`), each identified label lies in `Mset U i` for the
identifying pattern's detectors; but a single coincidence pattern's `Q` is
proportional to at most one Pauli, so a pattern identifies at most one label,
and with only two distinct label-sets available at most two labels can be
identified — contradicting that all four are identified. -/
theorem case_doubled (U : Matrix (Fin 4) (Fin 4) ℂ)
    (hU : U ∈ Matrix.unitaryGroup (Fin 4) ℂ) (e : BellLabel ≃ Fin 4)
    (hall : ∀ μ : BellLabel, ∃ i j : Fin 4, Identifies U i j μ)
    (hd : DoubledEdges (fun i => (Mset U i).image e)) : False := by
  classical
  obtain ⟨i, j, k, l, huniv, hij, hkl, hci, hck, hdisj, hun⟩ := hd
  -- beta-reduced restatements of the doubled-edges data
  have hkl' : (Mset U k).image e = (Mset U l).image e := hkl
  have hci' : ((Mset U i).image e).card = 2 := hci
  have hdisj2 : Disjoint ((Mset U i).image e) ((Mset U k).image e) := hdisj
  -- an ordered coincidence pattern identifies at most one label:
  -- its Q matrix is proportional to at most one Pauli (trace test).
  have huniq : ∀ (a b : Fin 4) (μ ν : BellLabel),
      Identifies U a b μ → Identifies U a b ν → μ = ν := by
    intro a b μ ν h1 h2
    by_contra hne
    have hp1 := (identifies_iff_prop U a b μ).mp h1
    have hp2 := (identifies_iff_prop U a b ν).mp h2
    have hz := ((prop_iff_traces_vanish (Q U a b) ν).mp hp2).2 μ hne
    exact ((prop_iff_traces_vanish (Q U a b) μ).mp hp1).1 hz
  -- swapping the detector pair changes Q by at most a sign
  have hQpm : ∀ a b : Fin 4, Q U b a = Q U a b ∨ Q U b a = -(Q U a b) := by
    intro a b
    first
      | (refine Or.inl ?_
         unfold Q Xblk Yblk sigmaX
         ext r c
         fin_cases r <;> fin_cases c <;>
           simp [Matrix.mul_apply, Matrix.transpose_apply, Fin.sum_univ_succ,
             Matrix.submatrix_apply, Matrix.neg_apply] <;>
           ring)
      | (refine Or.inr ?_
         unfold Q Xblk Yblk sigmaX
         ext r c
         fin_cases r <;> fin_cases c <;>
           simp [Matrix.mul_apply, Matrix.transpose_apply, Fin.sum_univ_succ,
             Matrix.submatrix_apply, Matrix.neg_apply] <;>
           ring)
      | (refine Or.inl ?_
         unfold Q Xblk Yblk sigmaX
         ext r c
         simp [Matrix.mul_apply, Matrix.transpose_apply, Fin.sum_univ_two,
           Matrix.submatrix_apply, Matrix.neg_apply, Matrix.cons_val_zero,
           Matrix.cons_val_one, Matrix.head_cons] <;>
           ring)
      | (refine Or.inr ?_
         unfold Q Xblk Yblk sigmaX
         ext r c
         simp [Matrix.mul_apply, Matrix.transpose_apply, Fin.sum_univ_two,
           Matrix.submatrix_apply, Matrix.neg_apply, Matrix.cons_val_zero,
           Matrix.cons_val_one, Matrix.head_cons] <;>
           ring)
      | (refine Or.inl ?_
         unfold Q
         ext r c
         fin_cases r <;> fin_cases c <;>
           simp [Xblk, Yblk, sigmaX, Matrix.mul_apply, Matrix.transpose_apply,
             Fin.sum_univ_succ, Matrix.submatrix_apply, Matrix.neg_apply] <;>
           ring)
      | (refine Or.inr ?_
         unfold Q
         ext r c
         fin_cases r <;> fin_cases c <;>
           simp [Xblk, Yblk, sigmaX, Matrix.mul_apply, Matrix.transpose_apply,
             Fin.sum_univ_succ, Matrix.submatrix_apply, Matrix.neg_apply] <;>
           ring)
      | exact ?_
  -- hence identification is insensitive to the order of the pattern
  have hflip : ∀ (a b : Fin 4) (μ : BellLabel),
      Identifies U a b μ → Identifies U b a μ := by
    intro a b μ h1
    obtain ⟨t, ht, hQ⟩ := (identifies_iff_prop U a b μ).mp h1
    rcases hQpm a b with h | h
    · exact (identifies_iff_prop U b a μ).mpr ⟨t, ht, h.trans hQ⟩
    · refine (identifies_iff_prop U b a μ).mpr ⟨-t, neg_ne_zero.mpr ht, ?_⟩
      rw [h, hQ, neg_smul]
  -- so the reversed pattern also identifies at most the same label
  have huniq' : ∀ (a b : Fin 4) (μ ν : BellLabel),
      Identifies U a b μ → Identifies U b a ν → μ = ν := by
    intro a b μ ν h1 h2
    exact huniq b a μ ν (hflip a b μ h1) h2
  -- pull the doubled structure back through the equivalence e
  have hSkl : Mset U k = Mset U l := Finset.image_injective e.injective hkl'
  have hdisj' : ∀ μ : BellLabel, μ ∈ Mset U i → μ ∈ Mset U k → False := by
    intro μ h1 h2
    exact Finset.disjoint_left.mp hdisj2 (Finset.mem_image_of_mem _ h1)
      (Finset.mem_image_of_mem _ h2)
  -- a detector whose Mset contains a label of the i-half must be i or j
  have hloc : ∀ (a : Fin 4) (μ : BellLabel),
      μ ∈ Mset U i → μ ∈ Mset U a → a = i ∨ a = j := by
    intro a μ hS hMa
    have ha : a ∈ ({i, j, k, l} : Finset (Fin 4)) := by
      rw [huniv]; exact Finset.mem_univ a
    simp only [Finset.mem_insert, Finset.mem_singleton] at ha
    rcases ha with ha | ha | ha | ha
    · exact Or.inl ha
    · exact Or.inr ha
    · subst ha; exact (hdisj' μ hS hMa).elim
    · subst ha; rw [← hSkl] at hMa; exact (hdisj' μ hS hMa).elim
  -- every label of the i-half is identified by the pattern {i, j} (some order)
  have key : ∀ μ : BellLabel, μ ∈ Mset U i →
      Identifies U i j μ ∨ Identifies U j i μ := by
    intro μ hμ
    obtain ⟨a, b, hab⟩ := hall μ
    have hr := identifies_rowDecouples U hU a b μ hab
    have hma : μ ∈ Mset U a := mem_Mset.mpr hr.1
    have hmb : μ ∈ Mset U b := mem_Mset.mpr hr.2
    have hne' : a ≠ b := by
      intro h; subst h; exact no_diag_identify U hU a μ hab
    have ha := hloc a μ hμ hma
    have hb := hloc b μ hμ hmb
    rcases ha with ha | ha <;> rcases hb with hb | hb
    · exact (hne' (ha.trans hb.symm)).elim
    · subst ha; subst hb; exact Or.inl hab
    · subst ha; subst hb; exact Or.inr hab
    · exact (hne' (ha.trans hb.symm)).elim
  -- the i-half contains two distinct labels
  have hScard : (Mset U i).card = 2 := by
    have h := hci'
    rwa [Finset.card_image_of_injective _ e.injective] at h
  obtain ⟨μ₁, hμ₁, μ₂, hμ₂, hne⟩ := Finset.one_lt_card.mp
    (by omega : 1 < (Mset U i).card)
  -- both labels ride on the single pattern {i, j}: contradiction
  rcases key μ₁ hμ₁ with h1 | h1 <;> rcases key μ₂ hμ₂ with h2 | h2
  · exact hne (huniq i j μ₁ μ₂ h1 h2)
  · exact hne (huniq' i j μ₁ μ₂ h1 h2)
  · exact hne (huniq' j i μ₁ μ₂ h1 h2)
  · exact hne (huniq j i μ₁ μ₂ h1 h2)

end Empiricist

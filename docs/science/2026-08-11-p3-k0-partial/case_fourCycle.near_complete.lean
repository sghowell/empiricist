import EmpiricistLean.Basic
import EmpiricistLean.P3Amplitudes
import EmpiricistLean.P3Pauli
import EmpiricistLean.P3L1
import EmpiricistLean.P3L2
import EmpiricistLean.P3Counting
import EmpiricistLean.P3Bridge
import EmpiricistLean.P3Sesq
import EmpiricistLean.P3TwoByTwo
import EmpiricistLean.P3Eigvec
import Mathlib.Data.Matrix.Basic
import Mathlib.LinearAlgebra.UnitaryGroup

namespace Empiricist

theorem case_fourCycle (U : Matrix (Fin 4) (Fin 4) ℂ)
    (hU : U ∈ Matrix.unitaryGroup (Fin 4) ℂ) (e : BellLabel ≃ Fin 4)
    (hall : ∀ μ : BellLabel, ∃ i j : Fin 4, Identifies U i j μ)
    (hc : FourCycle (fun i => (Mset U i).image e)) : False := by
  unfold FourCycle at hc
  obtain ⟨i₀, i₁, i₂, i₃, hI, a, b, c, d, hL, h0, h1, h2, h3⟩ := hc
  replace h0 : Finset.image e (Mset U i₀) = {a, b} := h0
  replace h2 : Finset.image e (Mset U i₂) = {c, d} := h2
  have key : ∀ x y z w : Fin 4, ({x, y, z, w} : Finset (Fin 4)) = Finset.univ →
      x ≠ y ∧ x ≠ z ∧ x ≠ w ∧ y ≠ z ∧ y ≠ w ∧ z ≠ w := by decide
  obtain ⟨hab, hac, had, hbc, hbd, hcd⟩ := key a b c d hL
  obtain ⟨hi01, hi02, hi03, hi12, hi13, hi23⟩ := key i₀ i₁ i₂ i₃ hI
  have getMem : ∀ (i : Fin 4) (S : Finset (Fin 4)) (x : Fin 4),
      Finset.image e (Mset U i) = S → x ∈ S → RowDecouples U i (e.symm x) := by
    intro i S x hS hx
    have hx' : x ∈ Finset.image e (Mset U i) := by rw [hS]; exact hx
    rcases Finset.mem_image.mp hx' with ⟨μ, hμ, hEq⟩
    have hμx : e.symm x = μ := by rw [← hEq]; exact Equiv.symm_apply_apply e μ
    rw [hμx]
    exact mem_Mset.mp hμ
  have h0a : RowDecouples U i₀ (e.symm a) := getMem i₀ {a, b} a h0 (by simp)
  have h0b : RowDecouples U i₀ (e.symm b) := getMem i₀ {a, b} b h0 (by simp)
  have h2c : RowDecouples U i₂ (e.symm c) := getMem i₂ {c, d} c h2 (by simp)
  have h2d : RowDecouples U i₂ (e.symm d) := getMem i₂ {c, d} d h2 (by simp)
  have hlabAB : e.symm a ≠ e.symm b := fun h => hab (by simpa using congrArg e h)
  have hlabAC : e.symm a ≠ e.symm c := fun h => hac (by simpa using congrArg e h)
  have hlabAD : e.symm a ≠ e.symm d := fun h => had (by simpa using congrArg e h)
  have hlabBC : e.symm b ≠ e.symm c := fun h => hbc (by simpa using congrArg e h)
  have hlabBD : e.symm b ≠ e.symm d := fun h => hbd (by simpa using congrArg e h)
  have hlabCD : e.symm c ≠ e.symm d := fun h => hcd (by simpa using congrArg e h)
  obtain ⟨A, hA⟩ : ∃ A, e.symm a = A := ⟨_, rfl⟩
  obtain ⟨B, hB⟩ : ∃ B, e.symm b = B := ⟨_, rfl⟩
  obtain ⟨C, hC⟩ : ∃ C, e.symm c = C := ⟨_, rfl⟩
  obtain ⟨D, hD⟩ : ∃ D, e.symm d = D := ⟨_, rfl⟩
  rw [hA] at h0a hlabAB hlabAC hlabAD
  rw [hB] at h0b hlabAB hlabBC hlabBD
  rw [hC] at h2c hlabAC hlabBC hlabCD
  rw [hD] at h2d hlabAD hlabBD hlabCD
  clear hA hB hC hD
  have hmulEq : mulLabel A B = mulLabel C D := by
    clear h0a h0b h2c h2d
    cases A <;> cases B <;> cases C <;> cases D <;>
      first
      | exact (hlabAB rfl).elim
      | exact (hlabAC rfl).elim
      | exact (hlabAD rfl).elim
      | exact (hlabBC rfl).elim
      | exact (hlabBD rfl).elim
      | exact (hlabCD rfl).elim
      | decide
      | rfl
      | simp [mulLabel]
  have hUU : U * star U = 1 := Matrix.mem_unitaryGroup_iff.mp hU
  have hor02 : (U * star U) i₀ i₂ = 0 := by rw [hUU]; exact Matrix.one_apply_ne hi02
  try rw [Matrix.mul_apply] at hor02
  try simp only [Matrix.star_apply, Fin.sum_univ_four] at hor02
  try clear hall
  try clear h0
  try clear h1
  try clear h2
  try clear h3
  try clear hI
  try clear hL
  try clear key
  try clear getMem
  try clear hab
  try clear hac
  try clear had
  try clear hbc
  try clear hbd
  try clear hcd
  try clear hi01
  try clear hi03
  try clear hi12
  try clear hi13
  try clear hi23
  try clear a
  try clear b
  try clear c
  try clear d
  try clear e
  try clear i₁
  try clear i₃
  try clear hUU
  -- Eigen-structure of the two twisted x-rows for the common Pauli
  obtain ⟨e0, he0, heq0⟩ := decouple_pair h0a h0b
  obtain ⟨c₀, hc₀⟩ := left_eigen_of_pair heq0
  obtain ⟨e2, he2, heq2⟩ := decouple_pair h2c h2d
  obtain ⟨c₂, hc₂⟩ := left_eigen_of_pair heq2
  rw [hmulEq] at hc₀
  obtain ⟨εP, hεP, hTP⟩ := pauli_transpose (mulLabel C D)
  have he₀ := mulVec_eigen hεP hTP hc₀
  have he₂ := mulVec_eigen hεP hTP hc₂
  have hx0 : xRow U i₀ ≠ 0 := by
    rcases row_ne_zero_of_unitary hU i₀ with h | h
    · exact h
    · intro hx0'; apply h; obtain ⟨cc, hcc, hyy⟩ := h0a
      rw [hyy, hx0']; simp [Matrix.zero_vecMul]
  have hw₀ := w_ne_zero hx0
  have hx2 : xRow U i₂ ≠ 0 := by
    rcases row_ne_zero_of_unitary hU i₂ with h | h
    · exact h
    · intro hx2'; apply h; obtain ⟨cc, hcc, hyy⟩ := h2c
      rw [hyy, hx2']; simp [Matrix.zero_vecMul]
  have hw₂ := w_ne_zero hx2
  have hnI : mulLabel C D ≠ BellLabel.phiP := mulLabel_ne_phiP hlabCD
  have hpair := pauli_eigvec_sesq_pairing hnI he₀ he₂ hw₀ hw₂
  revert hor02 hpair he₀ he₂ hw₀ hw₂ hc₀ hc₂
  obtain ⟨k₀, hk₀, hx₀⟩ := h0a
  obtain ⟨k₂, hk₂, hx₂⟩ := h2c
  obtain ⟨l₀, hl₀, hy₀⟩ := h0b
  obtain ⟨l₂, hl₂, hy₂⟩ := h2d
  fin_cases A <;> fin_cases B <;> fin_cases C <;> fin_cases D <;>
    first
    | exact (hlabAB rfl).elim
    | exact (hlabAC rfl).elim
    | exact (hlabAD rfl).elim
    | exact (hlabBC rfl).elim
    | exact (hlabBD rfl).elim
    | exact (hlabCD rfl).elim
    | (intro hc₀ hc₂ hw₀ hw₂ he₀ he₂ hpair hor02
       apply hpair
       simp only [sesq, pauliOf, mulLabel, sigma0, sigmaX, sigmaY, sigmaZ, Kmat,
         Matrix.vecMul, Matrix.mulVec, Matrix.dotProduct, Fin.sum_univ_two,
         Matrix.cons_val_zero, Matrix.cons_val_one, Matrix.head_cons,
         Matrix.smul_apply, Pi.smul_apply, smul_eq_mul] at hx₀ hx₂ hy₀ hy₂ hor02 ⊢
       constructor <;> linear_combination hor02)

end Empiricist

import EmpiricistLean.Basic
import EmpiricistLean.P3Amplitudes
import EmpiricistLean.P3Pauli
import EmpiricistLean.P3L1
import EmpiricistLean.P3L2
import EmpiricistLean.P3Counting
import EmpiricistLean.P3Bridge
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
  -- distinctness of the four labels and the four rows
  have key : ∀ x y z w : Fin 4, ({x, y, z, w} : Finset (Fin 4)) = Finset.univ →
      x ≠ y ∧ x ≠ z ∧ x ≠ w ∧ y ≠ z ∧ y ≠ w ∧ z ≠ w := by decide
  obtain ⟨hab, hac, had, hbc, hbd, hcd⟩ := key a b c d hL
  obtain ⟨hi01, hi02, hi03, hi12, hi13, hi23⟩ := key i₀ i₁ i₂ i₃ hI
  -- extraction of RowDecouples facts from the Mset images (rows i₀ and i₂ only:
  -- their label pairs {a,b} and {c,d} are complementary and cover all 4 labels)
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
  -- distinctness of the four Bell labels
  have hlabAB : e.symm a ≠ e.symm b := fun h => hab (by simpa using congrArg e h)
  have hlabAC : e.symm a ≠ e.symm c := fun h => hac (by simpa using congrArg e h)
  have hlabAD : e.symm a ≠ e.symm d := fun h => had (by simpa using congrArg e h)
  have hlabBC : e.symm b ≠ e.symm c := fun h => hbc (by simpa using congrArg e h)
  have hlabBD : e.symm b ≠ e.symm d := fun h => hbd (by simpa using congrArg e h)
  have hlabCD : e.symm c ≠ e.symm d := fun h => hcd (by simpa using congrArg e h)
  -- give the four Bell labels opaque names A B C D (so we can case on them later)
  obtain ⟨A, hA⟩ : ∃ A, e.symm a = A := ⟨_, rfl⟩
  obtain ⟨B, hB⟩ : ∃ B, e.symm b = B := ⟨_, rfl⟩
  obtain ⟨C, hC⟩ : ∃ C, e.symm c = C := ⟨_, rfl⟩
  obtain ⟨D, hD⟩ : ∃ D, e.symm d = D := ⟨_, rfl⟩
  rw [hA] at h0a hlabAB hlabAC hlabAD
  rw [hB] at h0b hlabAB hlabBC hlabBD
  rw [hC] at h2c hlabAC hlabBC hlabCD
  rw [hD] at h2d hlabAD hlabBD hlabCD
  -- unfold RowDecouples and extract the nonzero scalars
  unfold RowDecouples at h0a h0b h2c h2d
  obtain ⟨k₁, hk₁, hy₁⟩ := h0a
  obtain ⟨k₂, hk₂, hy₂⟩ := h0b
  obtain ⟨k₃, hk₃, hy₃⟩ := h2c
  obtain ⟨k₄, hk₄, hy₄⟩ := h2d
  -- unitarity: expanded row inner products (both orientations + diagonals)
  have hUU : U * star U = 1 := Matrix.mem_unitaryGroup_iff.mp hU
  have hor02 : (U * star U) i₀ i₂ = 0 := by rw [hUU]; exact Matrix.one_apply_ne hi02
  have hor20 : (U * star U) i₂ i₀ = 0 := by
    rw [hUU]; exact Matrix.one_apply_ne (Ne.symm hi02)
  have hd0 : (U * star U) i₀ i₀ = 1 := by rw [hUU]; exact Matrix.one_apply_eq i₀
  have hd2 : (U * star U) i₂ i₂ = 1 := by rw [hUU]; exact Matrix.one_apply_eq i₂
  try rw [Matrix.mul_apply] at hor02
  try rw [Matrix.mul_apply] at hor20
  try rw [Matrix.mul_apply] at hd0
  try rw [Matrix.mul_apply] at hd2
  try simp only [Matrix.star_apply, Fin.sum_univ_four] at hor02 hor20 hd0 hd2
  -- componentwise form of the decoupling equations (probe the exact shape)
  have E10 := congrFun hy₁ 0
  have E11 := congrFun hy₁ 1
  have E30 := congrFun hy₃ 0
  have E31 := congrFun hy₃ 1
  try simp only [Pi.smul_apply, smul_eq_mul] at E10 E11 E30 E31
  try simp only [Matrix.vecMul, Matrix.dotProduct, Fin.sum_univ_two] at E10 E11 E30 E31
  try simp only [Matrix.vecMul, dotProduct, Fin.sum_univ_two] at E10 E11 E30 E31
  -- definitional probes (each guarded; unfold keeps the body visible)
  have d5 : xRow U i₀ = xRow U i₀ := rfl
  try unfold xRow at d5
  have d6 : yRow U i₀ = yRow U i₀ := rfl
  try unfold yRow at d6
  have d7 : Kmat A = Kmat A := rfl
  try unfold Kmat at d7
  have d8y : sigmaY = sigmaY := rfl
  try unfold sigmaY at d8y
  have d8x : sigmaX = sigmaX := rfl
  try unfold sigmaX at d8x
  have d8z : sigmaZ = sigmaZ := rfl
  try unfold sigmaZ at d8z
  have d80 : sigma0 = sigma0 := rfl
  try unfold sigma0 at d80
  -- type signatures in case unfold failed
  have dxr := @xRow
  have dyr := @yRow
  have dkm := @Kmat
  -- decidability probe for BellLabel (for the upcoming 24-way case split)
  try have dec1 : BellLabel.phiP ≠ BellLabel.psiP := by decide
  -- probe for possibly-existing helper lemmas in the foundation
  try have p1 := @xRow_ne_zero
  try have p2 := @row_split
  try have p3 := @orth_split
  try have p4 := @sigmaY_mul_self
  exact ?_

end Empiricist
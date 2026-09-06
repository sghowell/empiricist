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
import EmpiricistLean.P3SesqSum
import Mathlib.Data.Matrix.Basic
import Mathlib.LinearAlgebra.UnitaryGroup
import Mathlib.Tactic

set_option maxRecDepth 100000

namespace Empiricist

private lemma star_I_eq : star Complex.I = -Complex.I := by
  rw [← starRingEnd_apply]; exact Complex.conj_I

private lemma I_sq' : Complex.I ^ 2 = -1 := Complex.I_sq

private lemma I_cube' : Complex.I ^ 3 = -Complex.I := by
  rw [show (3 : ℕ) = 2 + 1 from rfl, pow_add, Complex.I_sq, pow_one]; ring

private lemma I_four' : Complex.I ^ 4 = 1 := by
  rw [show (4 : ℕ) = 2 + 2 from rfl, pow_add, Complex.I_sq]; ring

set_option hygiene false in
/-- Coordinate normalization of the goal. -/
macro "bell_simp_goal" : tactic =>
  `(tactic| simp only [sesq, Kmat, pauliOf, sigma0, sigmaX, sigmaY, sigmaZ, Matrix.vecMul,
      Matrix.mulVec, Matrix.mul_apply, dotProduct, Fin.sum_univ_two, Matrix.of_apply,
      Matrix.cons_val_zero, Matrix.cons_val_one, Matrix.head_cons, Matrix.cons_val_fin_one,
      Pi.smul_apply, smul_eq_mul, Matrix.smul_apply, Matrix.one_fin_two,
      Pi.star_apply, Matrix.star_apply, Matrix.transpose_apply, Matrix.neg_apply, Pi.neg_apply,
      starRingEnd_apply, star_add, star_sub, star_mul', star_neg, star_one, star_zero,
      star_star, star_I_eq, Complex.conj_I, mul_zero, zero_mul, mul_one, one_mul, add_zero,
      zero_add, sub_zero, zero_sub, mul_neg, neg_mul, neg_neg, neg_zero])

set_option hygiene false in
/-- Coordinate normalization of `hor02`. -/
macro "bell_simp_hor02" : tactic =>
  `(tactic| simp only [sesq, Kmat, pauliOf, sigma0, sigmaX, sigmaY, sigmaZ, Matrix.vecMul,
      Matrix.mulVec, Matrix.mul_apply, dotProduct, Fin.sum_univ_two, Matrix.of_apply,
      Matrix.cons_val_zero, Matrix.cons_val_one, Matrix.head_cons, Matrix.cons_val_fin_one,
      Pi.smul_apply, smul_eq_mul, Matrix.smul_apply, Matrix.one_fin_two,
      Pi.star_apply, Matrix.star_apply, Matrix.transpose_apply, Matrix.neg_apply, Pi.neg_apply,
      starRingEnd_apply, star_add, star_sub, star_mul', star_neg, star_one, star_zero,
      star_star, star_I_eq, Complex.conj_I, mul_zero, zero_mul, mul_one, one_mul, add_zero,
      zero_add, sub_zero, zero_sub, mul_neg, neg_mul, neg_neg, neg_zero] at hor02)

set_option hygiene false in
/-- Apply the sesq-sum lemma with a given (μ, ν, c) and normalize the resulting goal. -/
macro "bell_refine " μ:term:max ", " ν:term:max ", " c:term : tactic =>
  `(tactic| (
    refine pauli_eigvec_sesq_sum_ne $μ $ν
        (by first
          | decide
          | (intro h; cases h)
          | simp [pauliOf, sigma0, sigmaX, sigmaY, sigmaZ, Matrix.ext_iff, Fin.forall_fin_two]
          | (intro h
             have h00 := congrFun (congrFun h 0) 0
             have h01 := congrFun (congrFun h 0) 1
             have h11 := congrFun (congrFun h 1) 1
             simp [pauliOf, sigma0, sigmaX, sigmaY, sigmaZ] at h00 h01 h11))
        (by first
          | decide
          | (constructor <;> decide)
          | (refine ⟨?_, ?_, ?_⟩ <;> decide)
          | (ext i j <;> fin_cases i <;> fin_cases j <;>
              simp [pauliOf, sigma0, sigmaX, sigmaY, sigmaZ, Matrix.mul_apply, Matrix.neg_apply,
                Fin.sum_univ_two, Matrix.of_apply, Matrix.cons_val_zero, Matrix.cons_val_one,
                Matrix.head_cons] <;> ring))
        _ _ hw₀ hw₂ _ _ he₀ he₂ $c
        (by
          refine mul_ne_zero (mul_ne_zero ?_ ?_) ?_ <;>
            first
              | exact hk₀
              | exact hk₂
              | exact star_ne_zero.mpr hk₀
              | exact star_ne_zero.mpr hk₂
              | exact Complex.I_ne_zero
              | exact neg_ne_zero.mpr Complex.I_ne_zero
              | exact one_ne_zero
              | exact neg_ne_zero.mpr one_ne_zero
              | norm_num [Complex.ext_iff])
        ?_
    bell_simp_goal))

set_option hygiene false in
/-- Close the normalized goal from `hor02` / `hor02c`. -/
macro "bell_close" : tactic =>
  `(tactic| (
    try ring_nf at hor02
    try ring_nf at hor02c
    try ring_nf
    try simp only [I_sq', I_cube', I_four', neg_neg, neg_mul, mul_neg, one_mul,
      mul_one, neg_one_mul, mul_neg_one, neg_zero] at hor02
    try simp only [I_sq', I_cube', I_four', neg_neg, neg_mul, mul_neg, one_mul,
      mul_one, neg_one_mul, mul_neg_one, neg_zero] at hor02c
    try simp only [I_sq', I_cube', I_four', neg_neg, neg_mul, mul_neg, one_mul,
      mul_one, neg_one_mul, mul_neg_one, neg_zero]
    first
      | linear_combination hor02
      | linear_combination (-1 : ℂ) * hor02
      | linear_combination hor02c
      | linear_combination (-1 : ℂ) * hor02c
      | linear_combination Complex.I * hor02
      | linear_combination (-Complex.I) * hor02
      | linear_combination Complex.I * hor02c
      | linear_combination (-Complex.I) * hor02c))

set_option hygiene false in
macro "bell_combo " μ:term:max ", " ν:term:max ", " c:term : tactic =>
  `(tactic| (bell_refine $μ, $ν, $c
             bell_close))

set_option hygiene false in
/-- Try all scalar choices for a fixed (μ, ν). -/
macro "bell_try " μ:term:max ", " ν:term:max : tactic =>
  `(tactic| first
      | bell_combo $μ, $ν, (k₀ * star k₂ * Complex.I)
      | bell_combo $μ, $ν, (k₀ * star k₂ * (-Complex.I))
      | bell_combo $μ, $ν, (star k₀ * k₂ * Complex.I)
      | bell_combo $μ, $ν, (star k₀ * k₂ * (-Complex.I))
      | bell_combo $μ, $ν, (k₀ * star k₂ * (1 : ℂ))
      | bell_combo $μ, $ν, (k₀ * star k₂ * (-1 : ℂ))
      | bell_combo $μ, $ν, (star k₀ * k₂ * (1 : ℂ))
      | bell_combo $μ, $ν, (star k₀ * k₂ * (-1 : ℂ)))

set_option hygiene false in
/-- Pin P and N to concrete labels, then try all combos. -/
macro "bell_pn " μ:term:max ", " ν:term:max : tactic =>
  `(tactic| (
    have hPv : P = $μ := by rw [← hP] <;> decide
    have hNv : N = $ν := by rw [← hN] <;> decide
    subst hPv
    subst hNv
    bell_try $μ, $ν))

set_option hygiene false in
/-- Debug fallback: pin P and N, apply the lemma with the expected scalar, leave goal open. -/
macro "bell_pn_dbg " μ:term:max ", " ν:term:max : tactic =>
  `(tactic| (
    have hPv : P = $μ := by rw [← hP] <;> decide
    have hNv : N = $ν := by rw [← hN] <;> decide
    subst hPv
    subst hNv
    bell_refine $μ, $ν, (k₀ * star k₂ * Complex.I)
    try clear * - hor02 hor02c))

set_option hygiene false in
/-- Per-branch finisher: substitute the y-row scaling into `hor02`, pin the common Pauli,
then try the combos. -/
macro "bell_finish" : tactic =>
  `(tactic| (
    have hor02 : xRow U i₀ 0 * star (xRow U i₂ 0) + xRow U i₀ 1 * star (xRow U i₂ 1)
        + yRow U i₀ 0 * star (yRow U i₂ 0) + yRow U i₀ 1 * star (yRow U i₂ 1) = 0 := by
      first
        | exact hor02
        | (have h2 : (U * star U) i₀ i₂ = 0 := by
             rw [Matrix.mem_unitaryGroup_iff.mp hU]; exact Matrix.one_apply_ne hi02
           rw [Matrix.mul_apply, Fin.sum_univ_four] at h2
           simp only [Matrix.star_apply] at h2
           exact h2)
        | (simp only [Matrix.mul_apply, Fin.sum_univ_four, Matrix.star_apply] at hor02
           exact hor02)
    rw [hy₀, hy₂] at hor02
    bell_simp_hor02
    have hor02c := congrArg (star : ℂ → ℂ) hor02
    simp only [star_add, star_sub, star_mul', star_neg, star_one, star_zero, star_star,
      star_I_eq, starRingEnd_apply, Complex.conj_I, mul_neg, neg_mul, neg_neg, mul_one,
      one_mul] at hor02c
    first
      | bell_pn BellLabel.phiM, BellLabel.psiP
      | bell_pn BellLabel.phiM, BellLabel.psiM
      | bell_pn BellLabel.psiP, BellLabel.phiM
      | bell_pn BellLabel.psiP, BellLabel.psiM
      | bell_pn BellLabel.psiM, BellLabel.phiM
      | bell_pn BellLabel.psiM, BellLabel.psiP
      | bell_pn_dbg BellLabel.phiM, BellLabel.psiP
      | bell_pn_dbg BellLabel.phiM, BellLabel.psiM
      | bell_pn_dbg BellLabel.psiP, BellLabel.phiM
      | bell_pn_dbg BellLabel.psiP, BellLabel.psiM
      | bell_pn_dbg BellLabel.psiM, BellLabel.phiM
      | bell_pn_dbg BellLabel.psiM, BellLabel.psiP))

set_option maxRecDepth 100000 in
set_option maxHeartbeats 100000000 in
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
  -- Pin the common Pauli label as an opaque `P` so it survives the case split on C, D.
  obtain ⟨P, hP⟩ : ∃ P, mulLabel C D = P := ⟨_, rfl⟩
  try rw [hP] at he₀ he₂
  -- Pin the twist partner `N := mulLabel A C` (the Pauli of pauliOf A * pauliOf C).
  obtain ⟨N, hN⟩ : ∃ N, mulLabel A C = N := ⟨_, rfl⟩
  -- FINAL BLOCK: w₀ := xRow U i₀ ᵥ* sigmaY, w₂ := xRow U i₂ ᵥ* sigmaY are nonzero
  -- eigenvectors of pauliOf P; hor02 decomposes as sesq w₀ w₂ + c * sesq w₀ ((pauliOf N).mulVec w₂)
  -- and pauli_eigvec_sesq_sum_ne forbids this being 0.
  obtain ⟨k₀, hk₀, hy₀⟩ := h0a
  obtain ⟨k₂, hk₂, hy₂⟩ := h2c
  cases A <;> cases B <;> cases C <;> cases D <;>
    first
    | exact (hlabAB rfl).elim
    | exact (hlabAC rfl).elim
    | exact (hlabAD rfl).elim
    | exact (hlabBC rfl).elim
    | exact (hlabBD rfl).elim
    | exact (hlabCD rfl).elim
    | bell_finish

end Empiricist

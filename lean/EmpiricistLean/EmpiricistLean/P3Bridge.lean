import EmpiricistLean.Basic
import EmpiricistLean.P3Amplitudes
import EmpiricistLean.P3Pauli
import EmpiricistLean.P3L1
import EmpiricistLean.P3L2
import Mathlib.Data.Matrix.Basic
import Mathlib.LinearAlgebra.Matrix.NonsingularInverse
import Mathlib.Tactic.LinearCombination
import Mathlib.Tactic.FinCases

set_option maxHeartbeats 1000000

namespace Empiricist

/-- Entrywise form of the pattern matrix: `Q U i j` is the symmetrized outer
product of the x-rows against the y-rows of the two detectors. -/
private theorem Q_entry (U : Matrix (Fin 4) (Fin 4) ℂ) (i j : Fin 4) (a b : Fin 2) :
    Q U i j a b = xRow U i a * yRow U j b + xRow U j a * yRow U i b := by
  try unfold Q
  try unfold Xblk
  try unfold Yblk
  try unfold xRow
  try unfold yRow
  try unfold sigmaX
  try simp [Matrix.mul_apply, Matrix.transpose_apply, Fin.sum_univ_two]
  try ring
  try simp [Matrix.mul_apply, Matrix.transpose_apply, Fin.sum_univ_succ]
  try ring
  try (fin_cases a <;> fin_cases b <;>
    simp [Matrix.mul_apply, Matrix.transpose_apply, Fin.sum_univ_succ] <;> ring)
  all_goals exact ?_

/-- Row-vector action of `Kmat μ = σY * pauliOf μ` in components. -/
private theorem vecMul_Kmat (μ : BellLabel) (v : Fin 2 → ℂ) (b : Fin 2) :
    Matrix.vecMul v (Kmat μ) b
      = Complex.I * v 1 * pauliOf μ 0 b - Complex.I * v 0 * pauliOf μ 1 b := by
  try unfold Kmat
  try unfold sigmaY
  try simp [Matrix.vecMul, dotProduct, Matrix.mul_apply, Fin.sum_univ_two]
  try ring
  try simp [Matrix.vecMul, Matrix.dotProduct, Matrix.mul_apply, Fin.sum_univ_two]
  try ring
  try (fin_cases b <;>
    simp [Matrix.vecMul, dotProduct, Matrix.mul_apply, Fin.sum_univ_succ] <;> ring)
  try (cases μ <;>
    simp [Kmat, pauliOf, sigma0, sigmaX, sigmaY, sigmaZ, Matrix.vecMul, dotProduct,
      Matrix.mul_apply, Fin.sum_univ_two] <;> ring)
  all_goals exact ?_

/-- The Pauli matrices have nonzero 2x2 determinant (in entry form). -/
private theorem pauli_det_ne (μ : BellLabel) :
    pauliOf μ 0 0 * pauliOf μ 1 1 - pauliOf μ 0 1 * pauliOf μ 1 0 ≠ 0 := by
  have h1 : IsUnit (pauliOf μ).det :=
    (Matrix.isUnit_iff_isUnit_det _).mp (pauli_invertible μ)
  have h2 := h1.ne_zero
  rwa [Matrix.det_fin_two] at h2

/-- Core of the bridge: from the entrywise identity
`xᵢ a * yⱼ b + xⱼ a * yᵢ b = t * (pauliOf μ) a b` (with `t ≠ 0`), detector `i`
row-decouples. The ε-pairing `w := xᵢ σY` annihilates `xᵢ`, so pairing the
identity with `w` isolates `yᵢ` up to the nonzero scalar
`s = I (xᵢ₁ xⱼ₀ − xᵢ₀ xⱼ₁)`, whose nonvanishing follows from the determinant
identity `detX' · detY' = t² · det (pauliOf μ) ≠ 0`. -/
private theorem bridge_core (U : Matrix (Fin 4) (Fin 4) ℂ) (i j : Fin 4) (μ : BellLabel)
    (t : ℂ) (ht : t ≠ 0)
    (hE : ∀ a b : Fin 2, xRow U i a * yRow U j b + xRow U j a * yRow U i b
        = t * pauliOf μ a b) :
    RowDecouples U i μ := by
  unfold RowDecouples
  have hdetP := pauli_det_ne μ
  -- determinant identity: det Q = detX' * detY' = t^2 * det P
  have hdetQ : (xRow U i 0 * xRow U j 1 - xRow U i 1 * xRow U j 0) *
      (yRow U j 0 * yRow U i 1 - yRow U j 1 * yRow U i 0)
      = t ^ 2 * (pauliOf μ 0 0 * pauliOf μ 1 1 - pauliOf μ 0 1 * pauliOf μ 1 0) := by
    linear_combination
      (xRow U i 1 * yRow U j 1 + xRow U j 1 * yRow U i 1) * hE 0 0
        + t * pauliOf μ 0 0 * hE 1 1
        - (xRow U i 1 * yRow U j 0 + xRow U j 1 * yRow U i 0) * hE 0 1
        - t * pauliOf μ 0 1 * hE 1 0
  -- nondegeneracy of the x-block
  have hdX : xRow U i 0 * xRow U j 1 - xRow U i 1 * xRow U j 0 ≠ 0 := by
    intro h0
    have h2 : t ^ 2 * (pauliOf μ 0 0 * pauliOf μ 1 1 - pauliOf μ 0 1 * pauliOf μ 1 0)
        = 0 := by
      rw [← hdetQ, h0, zero_mul]
    rcases mul_eq_zero.mp h2 with h3 | h3
    · refine ht ?_
      have h4 : t * t = 0 := by linear_combination h3
      exact mul_self_eq_zero.mp h4
    · exact hdetP h3
  have hS : Complex.I * (xRow U i 1 * xRow U j 0 - xRow U i 0 * xRow U j 1) ≠ 0 := by
    refine mul_ne_zero Complex.I_ne_zero fun h0 => hdX ?_
    linear_combination -h0
  refine ⟨t / (Complex.I * (xRow U i 1 * xRow U j 0 - xRow U i 0 * xRow U j 1)),
    div_ne_zero ht hS, funext fun b => ?_⟩
  have key : Complex.I * (xRow U i 1 * xRow U j 0 - xRow U i 0 * xRow U j 1) * yRow U i b
      = t * Matrix.vecMul (xRow U i) (Kmat μ) b := by
    rw [vecMul_Kmat]
    linear_combination Complex.I * xRow U i 1 * hE 0 b - Complex.I * xRow U i 0 * hE 1 b
  rw [Pi.smul_apply, smul_eq_mul, div_mul_eq_mul_div, eq_div_iff hS]
  linear_combination key

/-- BRIDGE, left half: Q(i,j) = t • pauliOf μ (t ≠ 0) row-decouples detector i. -/
theorem bridge_left (U : Matrix (Fin 4) (Fin 4) ℂ)
    (hU : U ∈ Matrix.unitaryGroup (Fin 4) ℂ) (i j : Fin 4) (μ : BellLabel)
    (t : ℂ) (ht : t ≠ 0) (hQ : Q U i j = t • pauliOf μ) :
    RowDecouples U i μ := by
  refine bridge_core U i j μ t ht fun a b => ?_
  have h : Q U i j a b = (t • pauliOf μ) a b := by rw [hQ]
  rw [Q_entry] at h
  simpa using h

/-- BRIDGE, right half: Q(i,j) = t • pauliOf μ (t ≠ 0) row-decouples detector j. -/
theorem bridge_right (U : Matrix (Fin 4) (Fin 4) ℂ)
    (hU : U ∈ Matrix.unitaryGroup (Fin 4) ℂ) (i j : Fin 4) (μ : BellLabel)
    (t : ℂ) (ht : t ≠ 0) (hQ : Q U i j = t • pauliOf μ) :
    RowDecouples U j μ := by
  refine bridge_core U j i μ t ht fun a b => ?_
  have h : Q U i j a b = (t • pauliOf μ) a b := by rw [hQ]
  rw [Q_entry] at h
  have h' : xRow U i a * yRow U j b + xRow U j a * yRow U i b = t * pauliOf μ a b := by
    simpa using h
  linear_combination h'

/-- Diagonal patterns identify nothing: Q U i i is singular while
t • pauliOf μ with t ≠ 0 is invertible. -/
theorem no_diag_identify (U : Matrix (Fin 4) (Fin 4) ℂ)
    (hU : U ∈ Matrix.unitaryGroup (Fin 4) ℂ) (i : Fin 4) (μ : BellLabel)
    (h : Identifies U i i μ) : False := by
  obtain ⟨t, ht, hQ⟩ := (identifies_iff_prop U i i μ).mp h
  have hE : ∀ a b : Fin 2,
      xRow U i a * yRow U i b + xRow U i a * yRow U i b = t * pauliOf μ a b := by
    intro a b
    have h2 : Q U i i a b = (t • pauliOf μ) a b := by rw [hQ]
    rw [Q_entry] at h2
    simpa using h2
  have hdetP := pauli_det_ne μ
  -- det (Q U i i) = 0 since Q U i i has rank ≤ 1, so t^2 * det P = 0
  have h2 : t ^ 2 * (pauliOf μ 0 0 * pauliOf μ 1 1 - pauliOf μ 0 1 * pauliOf μ 1 0)
      = 0 := by
    linear_combination
      (-(xRow U i 1 * yRow U i 1 + xRow U i 1 * yRow U i 1)) * hE 0 0
        - t * pauliOf μ 0 0 * hE 1 1
        + (xRow U i 1 * yRow U i 0 + xRow U i 1 * yRow U i 0) * hE 0 1
        + t * pauliOf μ 0 1 * hE 1 0
  rcases mul_eq_zero.mp h2 with h3 | h3
  · refine ht ?_
    have h4 : t * t = 0 := by linear_combination h3
    exact mul_self_eq_zero.mp h4
  · exact hdetP h3

/-- BRIDGE (assembled): a pattern (i,j) identifying μ row-decouples BOTH detectors. -/
theorem identifies_rowDecouples
    (U : Matrix (Fin 4) (Fin 4) ℂ) (hU : U ∈ Matrix.unitaryGroup (Fin 4) ℂ)
    (i j : Fin 4) (μ : BellLabel) (h : Identifies U i j μ) :
    RowDecouples U i μ ∧ RowDecouples U j μ := by
  obtain ⟨t, ht, hQ⟩ := (identifies_iff_prop U i j μ).mp h
  exact ⟨bridge_left U hU i j μ t ht hQ, bridge_right U hU i j μ t ht hQ⟩

end Empiricist

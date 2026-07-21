import EmpiricistLean.P3Amplitudes
import Mathlib.LinearAlgebra.Matrix.Trace
import Mathlib.LinearAlgebra.Matrix.NonsingularInverse
import Mathlib.Tactic.FinCases
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.LinearCombination
import Mathlib.Tactic.NormNum

/-!
# `EmpiricistLean.P3Pauli`

The 2×2 Pauli toolbox for the P3 "at most 3 of 4" theorem: the label→Pauli map,
the Pauli trace expansion, trace orthogonality/normalization, invertibility, and
the target theorem that distinct non-identity Paulis share no common eigenvector.
-/

set_option maxHeartbeats 1000000

namespace Empiricist

/-- The Pauli matrix associated to each Bell label (matching the correspondence
of `rawAmp_eq_traceForm`). -/
def pauliOf : BellLabel → Matrix (Fin 2) (Fin 2) ℂ
  | .phiP => sigma0
  | .psiP => sigmaX
  | .psiM => sigmaY
  | .phiM => sigmaZ

/-- Every 2×2 complex matrix has the Pauli expansion with coefficients
`(σ_μ * M).trace / 2`. -/
theorem pauli_expansion (M : Matrix (Fin 2) (Fin 2) ℂ) :
    M = ((M.trace) / 2) • sigma0 + (((sigmaX * M).trace) / 2) • sigmaX
      + (((sigmaY * M).trace) / 2) • sigmaY + (((sigmaZ * M).trace) / 2) • sigmaZ := by
  ext i j
  fin_cases i <;> fin_cases j <;>
    simp [sigma0, sigmaX, sigmaY, sigmaZ, Matrix.trace_fin_two, Matrix.mul_apply,
      Matrix.vecMul, dotProduct, Fin.sum_univ_two, Matrix.add_apply, Matrix.smul_apply,
      smul_eq_mul] <;>
    first
      | ring1
      | linear_combination ((M 0 1 - M 1 0) / 2) * Complex.I_mul_I
      | linear_combination ((M 1 0 - M 0 1) / 2) * Complex.I_mul_I

theorem trace_sigma0_mul (M : Matrix (Fin 2) (Fin 2) ℂ) :
    (sigma0 * M).trace = M.trace := by
  simp [sigma0, Matrix.trace_fin_two, Matrix.mul_apply, Matrix.vecMul, dotProduct,
    Fin.sum_univ_two]

/-- The Pauli expansion, phrased uniformly through `pauliOf`. -/
theorem pauli_expansion_pauliOf (M : Matrix (Fin 2) (Fin 2) ℂ) :
    M = (((pauliOf .phiP * M).trace) / 2) • pauliOf .phiP
      + (((pauliOf .psiP * M).trace) / 2) • pauliOf .psiP
      + (((pauliOf .psiM * M).trace) / 2) • pauliOf .psiM
      + (((pauliOf .phiM * M).trace) / 2) • pauliOf .phiM := by
  simpa [pauliOf, trace_sigma0_mul] using pauli_expansion M

/-- Distinct Paulis are trace-orthogonal. -/
theorem pauli_orthogonal : ∀ mu nu : BellLabel, mu ≠ nu →
    (pauliOf mu * pauliOf nu).trace = 0 := by
  intro mu nu h
  cases mu <;> cases nu <;>
    first
    | exact absurd rfl h
    | norm_num [pauliOf, sigma0, sigmaX, sigmaY, sigmaZ, Matrix.trace_fin_two,
        Matrix.mul_apply, Fin.sum_univ_two, Complex.I_mul_I]

/-- Each Pauli has trace pairing `2` with itself. -/
theorem pauli_norm : ∀ mu : BellLabel, (pauliOf mu * pauliOf mu).trace = 2 := by
  intro mu
  cases mu <;>
    norm_num [pauliOf, sigma0, sigmaX, sigmaY, sigmaZ, Matrix.trace_fin_two,
      Matrix.mul_apply, Fin.sum_univ_two, Complex.I_mul_I]

/-- `M` is a nonzero multiple of the Pauli `pauliOf mu` iff its `mu` trace pairing is
nonzero and all other trace pairings vanish. -/
theorem prop_iff_traces_vanish (M : Matrix (Fin 2) (Fin 2) ℂ) (mu : BellLabel) :
    (∃ t : ℂ, t ≠ 0 ∧ M = t • pauliOf mu) ↔
      ((pauliOf mu * M).trace ≠ 0 ∧ ∀ nu ≠ mu, (pauliOf nu * M).trace = 0) := by
  constructor
  · rintro ⟨t, ht, rfl⟩
    refine ⟨?_, ?_⟩
    · rw [Matrix.mul_smul, Matrix.trace_smul, pauli_norm mu, smul_eq_mul]
      exact mul_ne_zero ht (by norm_num)
    · intro nu hnu
      rw [Matrix.mul_smul, Matrix.trace_smul, pauli_orthogonal nu mu hnu, smul_zero]
  · rintro ⟨hne, hz⟩
    refine ⟨(pauliOf mu * M).trace / 2, div_ne_zero hne (by norm_num), ?_⟩
    have hexp := pauli_expansion_pauliOf M
    cases mu with
    | phiP =>
      rw [hz BellLabel.psiP (fun h => BellLabel.noConfusion h),
          hz BellLabel.psiM (fun h => BellLabel.noConfusion h),
          hz BellLabel.phiM (fun h => BellLabel.noConfusion h)] at hexp
      simpa using hexp
    | psiP =>
      rw [hz BellLabel.phiP (fun h => BellLabel.noConfusion h),
          hz BellLabel.psiM (fun h => BellLabel.noConfusion h),
          hz BellLabel.phiM (fun h => BellLabel.noConfusion h)] at hexp
      simpa using hexp
    | psiM =>
      rw [hz BellLabel.phiP (fun h => BellLabel.noConfusion h),
          hz BellLabel.psiP (fun h => BellLabel.noConfusion h),
          hz BellLabel.phiM (fun h => BellLabel.noConfusion h)] at hexp
      simpa using hexp
    | phiM =>
      rw [hz BellLabel.phiP (fun h => BellLabel.noConfusion h),
          hz BellLabel.psiP (fun h => BellLabel.noConfusion h),
          hz BellLabel.psiM (fun h => BellLabel.noConfusion h)] at hexp
      simpa using hexp

/-- Every Pauli matrix is invertible (its determinant is `1` or `-1`). -/
theorem pauli_invertible : ∀ mu : BellLabel, IsUnit (pauliOf mu) := by
  intro mu
  rw [Matrix.isUnit_iff_isUnit_det, isUnit_iff_ne_zero]
  cases mu <;>
    norm_num [pauliOf, sigma0, sigmaX, sigmaY, sigmaZ, Matrix.det_fin_two,
      Complex.I_mul_I]

private lemma both_zero {v : Fin 2 → ℂ} (h0 : v 0 = 0) (h1 : v 1 = 0) : v = 0 := by
  funext i
  fin_cases i
  · simpa using h0
  · simpa using h1

private lemma no_common_XY (v : Fin 2 → ℂ) (a b : ℂ) (hv : v ≠ 0)
    (hX : sigmaX.mulVec v = a • v) (hY : sigmaY.mulVec v = b • v) : False := by
  have e1 : v 1 = a * v 0 := by
    simpa [Matrix.mulVec, dotProduct, Fin.sum_univ_two, sigmaX] using congrFun hX 0
  have e2 : v 0 = a * v 1 := by
    simpa [Matrix.mulVec, dotProduct, Fin.sum_univ_two, sigmaX] using congrFun hX 1
  have e3 : -(Complex.I * v 1) = b * v 0 := by
    simpa [Matrix.mulVec, dotProduct, Fin.sum_univ_two, sigmaY] using congrFun hY 0
  have e4 : Complex.I * v 0 = b * v 1 := by
    simpa [Matrix.mulVec, dotProduct, Fin.sum_univ_two, sigmaY] using congrFun hY 1
  have h2 : (2 * Complex.I) * (v 0 * v 1) = 0 := by
    linear_combination v 1 * e4 - v 0 * e3 + b * v 1 * e1 - b * v 0 * e2
  have key : v 0 * v 1 = 0 :=
    (mul_eq_zero.mp h2).resolve_left (by norm_num [Complex.I_ne_zero])
  rcases mul_eq_zero.mp key with h | h
  · exact hv (both_zero h (by rw [e1, h, mul_zero]))
  · exact hv (both_zero (by rw [e2, h, mul_zero]) h)

private lemma no_common_XZ (v : Fin 2 → ℂ) (a b : ℂ) (hv : v ≠ 0)
    (hX : sigmaX.mulVec v = a • v) (hZ : sigmaZ.mulVec v = b • v) : False := by
  have e1 : v 1 = a * v 0 := by
    simpa [Matrix.mulVec, dotProduct, Fin.sum_univ_two, sigmaX] using congrFun hX 0
  have e2 : v 0 = a * v 1 := by
    simpa [Matrix.mulVec, dotProduct, Fin.sum_univ_two, sigmaX] using congrFun hX 1
  have f1 : v 0 = b * v 0 := by
    simpa [Matrix.mulVec, dotProduct, Fin.sum_univ_two, sigmaZ] using congrFun hZ 0
  have f2 : -v 1 = b * v 1 := by
    simpa [Matrix.mulVec, dotProduct, Fin.sum_univ_two, sigmaZ] using congrFun hZ 1
  have h2 : (2 : ℂ) * (v 0 * v 1) = 0 := by
    linear_combination v 1 * f1 - v 0 * f2
  have key : v 0 * v 1 = 0 :=
    (mul_eq_zero.mp h2).resolve_left (by norm_num)
  rcases mul_eq_zero.mp key with h | h
  · exact hv (both_zero h (by rw [e1, h, mul_zero]))
  · exact hv (both_zero (by rw [e2, h, mul_zero]) h)

private lemma no_common_YZ (v : Fin 2 → ℂ) (a b : ℂ) (hv : v ≠ 0)
    (hY : sigmaY.mulVec v = a • v) (hZ : sigmaZ.mulVec v = b • v) : False := by
  have g1 : -(Complex.I * v 1) = a * v 0 := by
    simpa [Matrix.mulVec, dotProduct, Fin.sum_univ_two, sigmaY] using congrFun hY 0
  have g2 : Complex.I * v 0 = a * v 1 := by
    simpa [Matrix.mulVec, dotProduct, Fin.sum_univ_two, sigmaY] using congrFun hY 1
  have f1 : v 0 = b * v 0 := by
    simpa [Matrix.mulVec, dotProduct, Fin.sum_univ_two, sigmaZ] using congrFun hZ 0
  have f2 : -v 1 = b * v 1 := by
    simpa [Matrix.mulVec, dotProduct, Fin.sum_univ_two, sigmaZ] using congrFun hZ 1
  have h2 : (2 : ℂ) * (v 0 * v 1) = 0 := by
    linear_combination v 1 * f1 - v 0 * f2
  have key : v 0 * v 1 = 0 :=
    (mul_eq_zero.mp h2).resolve_left (by norm_num)
  rcases mul_eq_zero.mp key with h | h
  · have h1 : v 1 = 0 := by
      have h' : Complex.I * v 1 = 0 := by
        have hg := g1
        rw [h, mul_zero] at hg
        exact neg_eq_zero.mp hg
      exact (mul_eq_zero.mp h').resolve_left Complex.I_ne_zero
    exact hv (both_zero h h1)
  · have h0 : v 0 = 0 := by
      have h' : Complex.I * v 0 = 0 := by rw [g2, h, mul_zero]
      exact (mul_eq_zero.mp h').resolve_left Complex.I_ne_zero
    exact hv (both_zero h0 h)

/-- TARGET: distinct non-identity Pauli matrices have no common eigenvector. -/
theorem pauli_no_common_eigenvector :
    ∀ (mu nu : BellLabel), mu ≠ nu → mu ≠ .phiP → nu ≠ .phiP →
    ∀ (v : Fin 2 → ℂ) (a b : ℂ), v ≠ 0 →
      Matrix.mulVec (pauliOf mu) v = a • v →
      Matrix.mulVec (pauliOf nu) v = b • v → False := by
  intro mu nu hmn hmu hnu v a b hv h1 h2
  cases mu <;> cases nu <;>
    (try simp only [pauliOf] at h1 h2) <;>
    (first
      | exact hmu rfl
      | exact hnu rfl
      | exact hmn rfl
      | exact no_common_XY v a b hv h1 h2
      | exact no_common_XY v b a hv h2 h1
      | exact no_common_XZ v a b hv h1 h2
      | exact no_common_XZ v b a hv h2 h1
      | exact no_common_YZ v a b hv h1 h2
      | exact no_common_YZ v b a hv h2 h1)

end Empiricist

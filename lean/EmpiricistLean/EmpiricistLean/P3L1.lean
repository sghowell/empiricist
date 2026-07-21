import EmpiricistLean.P3Amplitudes
import EmpiricistLean.P3Pauli
import Mathlib.Tactic.FinCases

namespace Empiricist

/-- `sigma0` is the identity matrix. -/
private lemma sigma0_eq_one : sigma0 = (1 : Matrix (Fin 2) (Fin 2) ℂ) := by
  ext a b
  fin_cases a <;> fin_cases b <;> simp [sigma0, Matrix.one_apply]

/-- Bridging lemma: each raw amplitude vanishes iff the corresponding Pauli trace vanishes.
    The `phiP` clause uses `sigma0 = 1`; the `psiM` clause cancels the nonzero prefactor `-I`. -/
private lemma rawAmp_zero_iff (U : Matrix (Fin 4) (Fin 4) ℂ) (i j : Fin 4) (nu : BellLabel) :
    rawAmp U i j nu = 0 ↔ (pauliOf nu * Q U i j).trace = 0 := by
  obtain ⟨hP, hX, hY, hZ⟩ := rawAmp_eq_traceForm U i j
  cases nu with
  | phiP => rw [hP]; simp [pauliOf, sigma0_eq_one]
  | psiP => rw [hX]; simp [pauliOf]
  | psiM => rw [hY]; simp [pauliOf, mul_eq_zero, Complex.I_ne_zero]
  | phiM => rw [hZ]; simp [pauliOf]

/-- L1 identification characterization: the raw amplitudes of `U` at `(i, j)` identify the
    Bell label `mu` iff the reduced matrix `Q U i j` is a nonzero scalar multiple of the
    Pauli matrix associated to `mu`. -/
theorem identifies_iff_prop (U : Matrix (Fin 4) (Fin 4) ℂ) (i j : Fin 4) (mu : BellLabel) :
    Identifies U i j mu ↔ ∃ t : ℂ, t ≠ 0 ∧ Q U i j = t • pauliOf mu := by
  unfold Identifies
  rw [prop_iff_traces_vanish (Q U i j) mu]
  constructor
  · rintro ⟨ha, hb⟩
    exact ⟨fun h => ha ((rawAmp_zero_iff U i j mu).mpr h),
      fun nu hnu => (rawAmp_zero_iff U i j nu).mp (hb nu hnu)⟩
  · rintro ⟨ha, hb⟩
    exact ⟨fun h => ha ((rawAmp_zero_iff U i j mu).mp h),
      fun nu hnu => (rawAmp_zero_iff U i j nu).mpr (hb nu hnu)⟩

end Empiricist

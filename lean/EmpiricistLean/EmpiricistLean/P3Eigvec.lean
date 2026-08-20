import Mathlib.Data.Matrix.Basic
import Mathlib.Data.Complex.Basic
import Mathlib.Tactic
import EmpiricistLean.Basic
import EmpiricistLean.P3Amplitudes
import EmpiricistLean.P3Pauli
import EmpiricistLean.P3TwoByTwo

open Matrix
open Empiricist

/-- Any nonzero eigenvector `w` of `sigmaZ = !![1,0;0,-1]` is axis-aligned:
`w 0 = 0` or `w 1 = 0`.  This is the σz instance of the
eigenvector-axis-aligned reduction engine.

Proof: row extraction of the eigen-equation gives `w 0 = c * w 0` and
`-(w 1) = c * w 1`.  If `w 0 ≠ 0` then `c = 1`, hence `2 * w 1 = 0` in `ℂ`,
so `w 1 = 0`; otherwise `w 0 = 0` already. -/
theorem pauli_eigvec_axis_aligned (w : Fin 2 → ℂ) (hw : w ≠ 0) (c : ℂ)
    (hev : (sigmaZ *ᵥ w) = c • w) : AxisAligned w := by
  -- Row 0 of `sigmaZ *ᵥ w` is `1 * w 0 + 0 * w 1 = w 0`.
  have e0 : w 0 = c * w 0 := by
    have h0 := congrFun hev 0
    simp [sigmaZ, Matrix.mulVec, dotProduct, Fin.sum_univ_two,
      Matrix.cons_val_zero, Matrix.cons_val_one, Matrix.head_cons,
      Pi.smul_apply, smul_eq_mul] at h0
    first
      | linear_combination h0
      | linear_combination -h0
      | exact h0
      | exact h0.symm
  -- Row 1 of `sigmaZ *ᵥ w` is `0 * w 0 + (-1) * w 1 = -(w 1)`.
  have e1 : -(w 1) = c * w 1 := by
    have h1 := congrFun hev 1
    simp [sigmaZ, Matrix.mulVec, dotProduct, Fin.sum_univ_two,
      Matrix.cons_val_zero, Matrix.cons_val_one, Matrix.head_cons,
      Pi.smul_apply, smul_eq_mul] at h1
    first
      | linear_combination h1
      | linear_combination -h1
      | exact h1
      | exact h1.symm
  -- Core disjunction: `w 0 = 0 ∨ w 1 = 0`.
  have hkey : w 0 = 0 ∨ w 1 = 0 := by
    by_cases hz : w 0 = 0
    · exact Or.inl hz
    · -- From `w 0 = c * w 0` we get `(c - 1) * w 0 = 0`; `w 0 ≠ 0` forces `c = 1`.
      have hfac : (c - 1) * w 0 = 0 := by linear_combination -e0
      have hc : c = 1 := by
        rcases mul_eq_zero.mp hfac with h | h
        · linear_combination h
        · exact absurd h hz
      -- With `c = 1`, the second equation gives `2 * w 1 = 0`, hence `w 1 = 0`.
      subst hc
      have h2 : (2 : ℂ) * w 1 = 0 := by linear_combination -e1
      rcases mul_eq_zero.mp h2 with h | h
      · norm_num at h
      · exact Or.inr h
  -- Conclude `AxisAligned w` from the disjunction.
  first
    | exact hkey
    | exact hkey.symm
    | simpa [AxisAligned] using hkey
    | (unfold AxisAligned; tauto)
    | (rcases hkey with h | h <;> simp [AxisAligned, h])
    | (constructor <;> tauto)
    | tauto

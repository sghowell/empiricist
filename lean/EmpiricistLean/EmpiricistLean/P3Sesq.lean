import EmpiricistLean.Basic
import EmpiricistLean.P3Amplitudes
import EmpiricistLean.P3Pauli
import Mathlib.Data.Complex.Basic
import Mathlib.Data.Fin.VecNotation
import Mathlib.Tactic

open Empiricist

noncomputable section

/-- The standard sesquilinear pairing on `ℂ²`, conjugate-linear in the second slot. -/
def sesq (u v : Fin 2 → ℂ) : ℂ :=
  u 0 * (starRingEnd ℂ) (v 0) + u 1 * (starRingEnd ℂ) (v 1)

/-- A nonzero vector in `ℂ²` has a nonzero coordinate. -/
lemma coord_ne {x : Fin 2 → ℂ} (hx : x ≠ 0) : x 0 ≠ 0 ∨ x 1 ≠ 0 := by
  by_contra hc
  push_neg at hc
  apply hx
  funext i
  fin_cases i
  · simpa using hc.1
  · simpa using hc.2

/-- Every Pauli matrix in the Bell dictionary is an involution. -/
lemma pauli_sq (b : BellLabel) : pauliOf b * pauliOf b = 1 := by
  cases b
  all_goals
    ext i j
    fin_cases i <;> fin_cases j <;>
      norm_num [pauliOf, sigma0, sigmaX, sigmaY, sigmaZ, Matrix.mul_apply,
        Fin.sum_univ_two, Matrix.one_fin_two, Matrix.one_apply,
        Matrix.cons_val_zero, Matrix.cons_val_one, Matrix.head_cons,
        Complex.I_mul_I]

/-- Hence each Pauli matrix acts injectively on vectors. -/
lemma pauli_mulVec_eq_zero (b : BellLabel) {w : Fin 2 → ℂ}
    (h : (pauliOf b).mulVec w = 0) : w = 0 := by
  have h2 : (pauliOf b).mulVec ((pauliOf b).mulVec w) = 0 := by
    rw [h, Matrix.mulVec_zero]
  rw [Matrix.mulVec_mulVec, pauli_sq b, Matrix.one_mulVec] at h2
  exact h2

/-- The `sesq`-orthocomplement of a nonzero vector of `ℂ²` is one-dimensional:
if `v` and `w` are both `sesq`-orthogonal to the same nonzero `u`, with `v ≠ 0`,
then `w` is a scalar multiple of `v`. -/
lemma ortho_pair_prop {u v w : Fin 2 → ℂ} (hu : u ≠ 0) (hv : v ≠ 0)
    (h1 : sesq u v = 0) (h2 : sesq u w = 0) : ∃ lam : ℂ, w = lam • v := by
  simp only [sesq] at h1 h2
  -- conjugated determinant identity: `conj v₀ ⬝ conj w₁ = conj v₁ ⬝ conj w₀`
  have hcdet : (starRingEnd ℂ) (v 0) * (starRingEnd ℂ) (w 1)
      = (starRingEnd ℂ) (v 1) * (starRingEnd ℂ) (w 0) := by
    rcases coord_ne hu with h0 | h0
    · refine mul_left_cancel₀ h0 ?_
      linear_combination (starRingEnd ℂ) (w 1) * h1 - (starRingEnd ℂ) (v 1) * h2
    · refine mul_left_cancel₀ h0 ?_
      linear_combination (starRingEnd ℂ) (v 0) * h2 - (starRingEnd ℂ) (w 0) * h1
  have hdet : v 0 * w 1 = v 1 * w 0 := by
    have h3 := congrArg (starRingEnd ℂ) hcdet
    simpa [map_mul, Complex.conj_conj] using h3
  by_cases hv0 : v 0 = 0
  · have hv1 : v 1 ≠ 0 := by
      rcases coord_ne hv with h | h
      · exact absurd hv0 h
      · exact h
    have h4 : v 1 * w 0 = 0 := by rw [← hdet, hv0, zero_mul]
    have hw0 : w 0 = 0 := by
      rcases mul_eq_zero.mp h4 with h | h
      · exact absurd h hv1
      · exact h
    refine ⟨w 1 / v 1, funext fun i => ?_⟩
    fin_cases i
    · show w 0 = w 1 / v 1 * v 0
      rw [hv0, hw0]; ring
    · show w 1 = w 1 / v 1 * v 1
      field_simp
  · refine ⟨w 0 / v 0, funext fun i => ?_⟩
    fin_cases i
    · show w 0 = w 0 / v 0 * v 0
      field_simp
    · show w 1 = w 0 / v 0 * v 1
      rw [div_mul_eq_mul_div, eq_div_iff hv0]
      linear_combination hdet

/-- **Eigenvectors and anticommuting Paulis: the two pairings are not both zero.**
If `u, v` are nonzero eigenvectors of `P = pauliOf μ`, and `Q = pauliOf ν`
anticommutes with `P`, then `sesq u v` and `sesq u (Q v)` cannot both vanish.
Conceptually: if both vanished, `v` and `Q v` would lie in the 1-dimensional
`sesq`-orthocomplement of `u`, forcing `Q v = λ • v`; anticommutation then forces
`λ ⬝ c_v = -(c_v ⬝ λ)`, so `λ = 0` or `c_v = 0`, and either way the invertibility
of the Paulis (they square to `1`) kills `v`. -/
theorem pauli_eigvec_sesq_pairing (mu nu : BellLabel) (hmu : mu ≠ BellLabel.phiP)
    (hanti : pauliOf mu * pauliOf nu = -(pauliOf nu * pauliOf mu))
    (u v : Fin 2 → ℂ) (hu : u ≠ 0) (hv : v ≠ 0) (cu cv : ℂ)
    (heu : (pauliOf mu).mulVec u = cu • u) (hev : (pauliOf mu).mulVec v = cv • v) :
    ¬(sesq u v = 0 ∧ sesq u ((pauliOf nu).mulVec v) = 0) := by
  rintro ⟨h1, h2⟩
  -- both `v` and `Q v` lie in the line orthogonal to `u`, hence are proportional
  obtain ⟨lam, hlam⟩ := ortho_pair_prop hu hv h1 h2
  -- compute `P (Q v)` in two ways
  have e1 : (pauliOf mu).mulVec ((pauliOf nu).mulVec v) = (lam * cv) • v := by
    rw [hlam, Matrix.mulVec_smul, hev, smul_smul]
  have e2 : (pauliOf mu).mulVec ((pauliOf nu).mulVec v) = -((cv * lam) • v) := by
    rw [Matrix.mulVec_mulVec, hanti, Matrix.neg_mulVec, ← Matrix.mulVec_mulVec, hev,
      Matrix.mulVec_smul, hlam, smul_smul]
  have key : (lam * cv) • v = -((cv * lam) • v) := e1.symm.trans e2
  have h4 : (lam * cv + cv * lam) • v = 0 := by
    rw [add_smul, key]
    simp
  have h6 : cv * lam = 0 := by
    rcases smul_eq_zero.mp h4 with h | h
    · linear_combination h / 2
    · exact absurd h hv
  rcases mul_eq_zero.mp h6 with hcv | hlam0
  · -- `cv = 0` would make `P v = 0`, contradicting invertibility of `P`
    exact hv (pauli_mulVec_eq_zero mu (by rw [hev, hcv, zero_smul]))
  · -- `lam = 0` would make `Q v = 0`, contradicting invertibility of `Q`
    exact hv (pauli_mulVec_eq_zero nu (by rw [hlam, hlam0, zero_smul]))

end

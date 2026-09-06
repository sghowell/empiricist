import Mathlib.Data.Matrix.Basic
import Mathlib.Data.Complex.Basic
import Mathlib.Data.Fin.VecNotation
import Mathlib.Tactic
import EmpiricistLean.Basic
import EmpiricistLean.P3Amplitudes
import EmpiricistLean.P3Pauli
import EmpiricistLean.P3Sesq

namespace Empiricist


/-- Non-identity Paulis square to the identity. -/
theorem pauliOf_mul_self_eq_one (mu : BellLabel) (hmu : mu ≠ BellLabel.phiP) :
    pauliOf mu * pauliOf mu = 1 := by
  first
    | exact pauli_sq mu hmu
    | exact pauli_sq hmu
    | exact pauli_sq mu
    | (cases mu; all_goals first
        | exact absurd rfl hmu
        | (ext i j; fin_cases i <;> fin_cases j <;>
            simp [pauliOf, sigma0, sigmaX, sigmaY, sigmaZ, Matrix.mul_apply,
              Fin.sum_univ_two, Matrix.one_apply])
        | (ext i j; fin_cases i <;> fin_cases j <;>
            simp [pauliOf, Matrix.mul_apply, Fin.sum_univ_two, Matrix.one_apply]))

set_option maxHeartbeats 1000000 in
theorem pauli_eigvec_sesq_sum_ne (mu nu : BellLabel) (hmu : mu ≠ BellLabel.phiP)
    (hanti : pauliOf mu * pauliOf nu = -(pauliOf nu * pauliOf mu))
    (u v : Fin 2 → Complex) (hu : u ≠ 0) (hv : v ≠ 0) (cu cv : Complex)
    (heu : (pauliOf mu).mulVec u = cu • u) (hev : (pauliOf mu).mulVec v = cv • v)
    (c : Complex) (hc : c ≠ 0) :
    sesq u v + c * sesq u ((pauliOf nu).mulVec v) ≠ 0 := by
  have hsq : pauliOf mu * pauliOf mu = 1 := pauliOf_mul_self_eq_one mu hmu
  -- eigenvalues of an involution square to one
  have hsq_eig : ∀ (w : Fin 2 → Complex) (cw : Complex), w ≠ 0 →
      (pauliOf mu).mulVec w = cw • w → cw * cw = 1 := by
    intro w cw hw hw'
    have h2 : (pauliOf mu * pauliOf mu).mulVec w = (cw * cw) • w := by
      first
        | (rw [← Matrix.mulVec_mulVec, hw', Matrix.mulVec_smul, hw', smul_smul])
        | simp [← Matrix.mulVec_mulVec, hw', Matrix.mulVec_smul, smul_smul]
    rw [hsq, Matrix.one_mulVec] at h2
    have h3 : (cw * cw - 1) • w = 0 := by
      rw [sub_smul, one_smul]
      exact sub_eq_zero.mpr h2.symm
    rcases smul_eq_zero.mp h3 with h | h
    · exact sub_eq_zero.mp h
    · exact absurd h hw
  have hcu2 : cu * cu = 1 := hsq_eig u cu hu heu
  have hcv2 : cv * cv = 1 := hsq_eig v cv hv hev
  have hpm : ∀ x : Complex, x * x = 1 → x = 1 ∨ x = -1 := by
    intro x hx
    have h : (x - 1) * (x + 1) = 0 := by linear_combination hx
    rcases mul_eq_zero.mp h with h | h
    · exact Or.inl (sub_eq_zero.mp h)
    · exact Or.inr (eq_neg_of_add_eq_zero_left h)
  have hI : Complex.I * Complex.I = -1 := Complex.I_mul_I
  -- coordinates
  obtain ⟨a, b, rfl⟩ : ∃ a b : Complex, u = ![a, b] :=
    ⟨u 0, u 1, by funext i; fin_cases i <;> first | rfl | simp⟩
  obtain ⟨p, q, rfl⟩ : ∃ p q : Complex, v = ![p, q] :=
    ⟨v 0, v 1, by funext i; fin_cases i <;> first | rfl | simp⟩
  have hab : a ≠ 0 ∨ b ≠ 0 := by
    by_contra hcon
    push_neg at hcon
    obtain ⟨rfl, rfl⟩ := hcon
    exact hu (by funext i; fin_cases i <;> first | rfl | simp)
  have hpq : p ≠ 0 ∨ q ≠ 0 := by
    by_contra hcon
    push_neg at hcon
    obtain ⟨rfl, rfl⟩ := hcon
    exact hv (by funext i; fin_cases i <;> first | rfl | simp)
  have hpq' : starRingEnd Complex p ≠ 0 ∨ starRingEnd Complex q ≠ 0 := by
    simpa using hpq
  have heu0 := congrFun heu 0
  have heu1 := congrFun heu 1
  have hev0 := congrFun hev 0
  have hev1 := congrFun hev 1
  have hev0' := congrArg (starRingEnd Complex) hev0
  have hev1' := congrArg (starRingEnd Complex) hev1
  have ha00 := congrFun (congrFun hanti 0) 0
  have ha01 := congrFun (congrFun hanti 0) 1
  have ha10 := congrFun (congrFun hanti 1) 0
  have ha11 := congrFun (congrFun hanti 1) 1
  clear hsq_eig hsq
  rcases hpm cu hcu2 with rfl | rfl <;>
  rcases hpm cv hcv2 with rfl | rfl <;>
  cases mu <;> cases nu
  all_goals first | exact absurd rfl hmu | skip
  all_goals first
    | simp [pauliOf, sigma0, sigmaX, sigmaY, sigmaZ, Matrix.mulVec, dotProduct, Fin.sum_univ_two, Matrix.mul_apply, Matrix.neg_apply, Matrix.one_apply, sesq] at heu0 heu1 hev0 hev1 hev0' hev1' ha00 ha01 ha10 ha11 ⊢
    | simp [pauliOf, Matrix.mulVec, dotProduct, Fin.sum_univ_two, Matrix.mul_apply, Matrix.neg_apply, Matrix.one_apply, sesq] at heu0 heu1 hev0 hev1 hev0' hev1' ha00 ha01 ha10 ha11 ⊢
    | skip
  all_goals try grind

end Empiricist

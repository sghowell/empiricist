import Mathlib.Data.Complex.Basic
import Mathlib.Data.Real.Sqrt
import Mathlib.Tactic
import Mathlib.LinearAlgebra.UnitaryGroup
import Mathlib.Algebra.BigOperators.Fin
import EmpiricistLean.Basic
import EmpiricistLean.P3Amplitudes

set_option maxHeartbeats 1600000
set_option maxRecDepth 8000

namespace Empiricist

noncomputable section

/-! ### Square-root constants and their algebraic relations -/

noncomputable def s2 : ℂ := (Real.sqrt 2 : ℝ)
noncomputable def s3 : ℂ := (Real.sqrt 3 : ℝ)
noncomputable def s6 : ℂ := (Real.sqrt 6 : ℝ)

lemma s2_sq : s2 * s2 = 2 := by
  simp only [s2]
  rw [← Complex.ofReal_mul, Real.mul_self_sqrt (by norm_num : (0:ℝ) ≤ 2)]
  norm_num

lemma s3_sq : s3 * s3 = 3 := by
  simp only [s3]
  rw [← Complex.ofReal_mul, Real.mul_self_sqrt (by norm_num : (0:ℝ) ≤ 3)]
  norm_num

lemma s6_eq : s6 = s2 * s3 := by
  simp only [s2, s3, s6]
  rw [show (6:ℝ) = 2 * 3 by norm_num, Real.sqrt_mul (by norm_num : (0:ℝ) ≤ 2) 3,
    Complex.ofReal_mul]

lemma s2_pow2 : s2 ^ 2 = 2 := by rw [pow_two, s2_sq]

lemma s3_pow2 : s3 ^ 2 = 3 := by rw [pow_two, s3_sq]

lemma s2_pow3 : s2 ^ 3 = 2 * s2 := by
  have h : s2 ^ 3 = s2 ^ 2 * s2 := by ring
  rw [h, s2_pow2]

lemma s3_pow3 : s3 ^ 3 = 3 * s3 := by
  have h : s3 ^ 3 = s3 ^ 2 * s3 := by ring
  rw [h, s3_pow2]

lemma I_pow3 : Complex.I ^ 3 = -Complex.I := by
  have h : Complex.I ^ 3 = Complex.I ^ 2 * Complex.I := by ring
  rw [h, Complex.I_sq, neg_one_mul]

lemma s2_ne_zero : s2 ≠ 0 := by
  intro h
  have h2 := s2_sq
  rw [h, mul_zero] at h2
  norm_num at h2

lemma s3_ne_I : s3 ≠ Complex.I := by
  intro h
  have h2 : (3:ℂ) = -1 := by rw [← s3_sq, h, Complex.I_mul_I]
  norm_num at h2

lemma one_ne_I_mul_s3 : (1:ℂ) ≠ Complex.I * s3 := by
  intro h
  have h2 : (1:ℂ) = -3 := by
    calc (1:ℂ) = 1 * 1 := by ring
    _ = (Complex.I * s3) * (Complex.I * s3) := by rw [← h]
    _ = (Complex.I * Complex.I) * (s3 * s3) := by ring
    _ = -3 := by rw [Complex.I_mul_I, s3_sq]; ring
  norm_num at h2

/-! ### The explicit 5-mode interferometer (one ancilla photon in input mode 4) -/

noncomputable def Vk1 : Matrix (Fin 5) (Fin 5) ℂ := Matrix.of
  ![![0, (-1/4) * s2 + (-1/4 * Complex.I) * s6, (1/8) * s2 + (-1/8 * Complex.I) * s6, (1/4) + (-1/4 * Complex.I) * s3, (1/4) * s2],
    ![0, (-1/4 * Complex.I) * s2 + (1/4) * s6, (-1/8 * Complex.I) * s2 + (-1/8) * s6, (-1/4 * Complex.I) + (-1/4) * s3, (-1/4 * Complex.I) * s2],
    ![(-1/4) * s2 + (-1/4 * Complex.I) * s6, 0, (1/4) + (-1/4 * Complex.I) * s3, 0, (-1/2)],
    ![(-1/2 * Complex.I) * s2, 0, (1/4 * Complex.I) + (-1/4) * s3, 0, (1/4 * Complex.I) + (1/4) * s3],
    ![0, 0, (1/4 * Complex.I) + (-1/4) * s3, (-1/4 * Complex.I) * s2 + (1/4) * s6, (-1/4 * Complex.I) + (-1/4) * s3]]

/-- Permanent of the 3x3 submatrix of `V` on rows `i j k` and columns `a b c`. -/
def perm3 (V : Matrix (Fin 5) (Fin 5) ℂ) (i j k : Fin 5) (a b c : Fin 5) : ℂ :=
  V i a * V j b * V k c + V i a * V j c * V k b + V i b * V j a * V k c
  + V i b * V j c * V k a + V i c * V j a * V k b + V i c * V j b * V k a

/-- The four unnormalised Bell amplitudes at the three-photon pattern `{i, j, k}`
(the ancilla photon always occupies input column 4). -/
def rawAmp3 (V : Matrix (Fin 5) (Fin 5) ℂ) (i j k : Fin 5) : BellLabel → ℂ
  | .phiP => perm3 V i j k 0 2 4 + perm3 V i j k 1 3 4
  | .phiM => perm3 V i j k 0 2 4 - perm3 V i j k 1 3 4
  | .psiP => perm3 V i j k 0 3 4 + perm3 V i j k 1 2 4
  | .psiM => perm3 V i j k 0 3 4 - perm3 V i j k 1 2 4

def Identifies3 (V : Matrix (Fin 5) (Fin 5) ℂ) (i j k : Fin 5) (mu : BellLabel) : Prop :=
  rawAmp3 V i j k mu ≠ 0 ∧ ∀ nu : BellLabel, nu ≠ mu → rawAmp3 V i j k nu = 0

/-! ### Matrix entries (rows 1–4, all columns), by definitional unfolding -/

lemma V10 : Vk1 1 0 = 0 := rfl
lemma V11 : Vk1 1 1 = (-1/4 * Complex.I) * s2 + (1/4) * s6 := rfl
lemma V12 : Vk1 1 2 = (-1/8 * Complex.I) * s2 + (-1/8) * s6 := rfl
lemma V13 : Vk1 1 3 = (-1/4 * Complex.I) + (-1/4) * s3 := rfl
lemma V14 : Vk1 1 4 = (-1/4 * Complex.I) * s2 := rfl
lemma V20 : Vk1 2 0 = (-1/4) * s2 + (-1/4 * Complex.I) * s6 := rfl
lemma V21 : Vk1 2 1 = 0 := rfl
lemma V22 : Vk1 2 2 = (1/4) + (-1/4 * Complex.I) * s3 := rfl
lemma V23 : Vk1 2 3 = 0 := rfl
lemma V24 : Vk1 2 4 = (-1/2) := rfl
lemma V30 : Vk1 3 0 = (-1/2 * Complex.I) * s2 := rfl
lemma V31 : Vk1 3 1 = 0 := rfl
lemma V32 : Vk1 3 2 = (1/4 * Complex.I) + (-1/4) * s3 := rfl
lemma V33 : Vk1 3 3 = 0 := rfl
lemma V34 : Vk1 3 4 = (1/4 * Complex.I) + (1/4) * s3 := rfl
lemma V40 : Vk1 4 0 = 0 := rfl
lemma V41 : Vk1 4 1 = 0 := rfl
lemma V42 : Vk1 4 2 = (1/4 * Complex.I) + (-1/4) * s3 := rfl
lemma V43 : Vk1 4 3 = (-1/4 * Complex.I) * s2 + (1/4) * s6 := rfl
lemma V44 : Vk1 4 4 = (-1/4 * Complex.I) + (-1/4) * s3 := rfl

/-! ### The sixteen amplitude evaluations.
Pipeline (inlined in each lemma): unfold the amplitude to a polynomial in
`s2`, `s3`, `Complex.I` (after eliminating `s6 = s2 * s3`), normalize with
`ring_nf`, rewrite the powers (degree ≤ 3 per atom) using `s2^2 = 2`,
`s2^3 = 2*s2`, `s3^2 = 3`, `s3^3 = 3*s3`, `I^2 = -1`, `I^3 = -I`, and
normalize again. -/

-- pattern (1, 3, 4): identifies phiP
lemma val_134_phiP : rawAmp3 Vk1 1 3 4 BellLabel.phiP = (1/4) * (s3 - Complex.I) := by
  simp only [rawAmp3, perm3, V10, V11, V12, V13, V14, V20, V21, V22, V23, V24,
    V30, V31, V32, V33, V34, V40, V41, V42, V43, V44, s6_eq]
  ring_nf
  try simp only [s2_pow2, s2_pow3, s3_pow2, s3_pow3, Complex.I_sq, I_pow3]
  try ring_nf
  try norm_num

lemma zero_134_phiM : rawAmp3 Vk1 1 3 4 BellLabel.phiM = 0 := by
  simp only [rawAmp3, perm3, V10, V11, V12, V13, V14, V20, V21, V22, V23, V24,
    V30, V31, V32, V33, V34, V40, V41, V42, V43, V44, s6_eq]
  ring_nf
  try simp only [s2_pow2, s2_pow3, s3_pow2, s3_pow3, Complex.I_sq, I_pow3]
  try ring_nf
  try norm_num

lemma zero_134_psiP : rawAmp3 Vk1 1 3 4 BellLabel.psiP = 0 := by
  simp only [rawAmp3, perm3, V10, V11, V12, V13, V14, V20, V21, V22, V23, V24,
    V30, V31, V32, V33, V34, V40, V41, V42, V43, V44, s6_eq]
  ring_nf
  try simp only [s2_pow2, s2_pow3, s3_pow2, s3_pow3, Complex.I_sq, I_pow3]
  try ring_nf
  try norm_num

lemma zero_134_psiM : rawAmp3 Vk1 1 3 4 BellLabel.psiM = 0 := by
  simp only [rawAmp3, perm3, V10, V11, V12, V13, V14, V20, V21, V22, V23, V24,
    V30, V31, V32, V33, V34, V40, V41, V42, V43, V44, s6_eq]
  ring_nf
  try simp only [s2_pow2, s2_pow3, s3_pow2, s3_pow3, Complex.I_sq, I_pow3]
  try ring_nf
  try norm_num

-- pattern (1, 2, 4): identifies phiM
lemma zero_124_phiP : rawAmp3 Vk1 1 2 4 BellLabel.phiP = 0 := by
  simp only [rawAmp3, perm3, V10, V11, V12, V13, V14, V20, V21, V22, V23, V24,
    V30, V31, V32, V33, V34, V40, V41, V42, V43, V44, s6_eq]
  ring_nf
  try simp only [s2_pow2, s2_pow3, s3_pow2, s3_pow3, Complex.I_sq, I_pow3]
  try ring_nf
  try norm_num

lemma val_124_phiM : rawAmp3 Vk1 1 2 4 BellLabel.phiM = (1/4) * (1 - Complex.I * s3) := by
  simp only [rawAmp3, perm3, V10, V11, V12, V13, V14, V20, V21, V22, V23, V24,
    V30, V31, V32, V33, V34, V40, V41, V42, V43, V44, s6_eq]
  ring_nf
  try simp only [s2_pow2, s2_pow3, s3_pow2, s3_pow3, Complex.I_sq, I_pow3]
  try ring_nf
  try norm_num

lemma zero_124_psiP : rawAmp3 Vk1 1 2 4 BellLabel.psiP = 0 := by
  simp only [rawAmp3, perm3, V10, V11, V12, V13, V14, V20, V21, V22, V23, V24,
    V30, V31, V32, V33, V34, V40, V41, V42, V43, V44, s6_eq]
  ring_nf
  try simp only [s2_pow2, s2_pow3, s3_pow2, s3_pow3, Complex.I_sq, I_pow3]
  try ring_nf
  try norm_num

lemma zero_124_psiM : rawAmp3 Vk1 1 2 4 BellLabel.psiM = 0 := by
  simp only [rawAmp3, perm3, V10, V11, V12, V13, V14, V20, V21, V22, V23, V24,
    V30, V31, V32, V33, V34, V40, V41, V42, V43, V44, s6_eq]
  ring_nf
  try simp only [s2_pow2, s2_pow3, s3_pow2, s3_pow3, Complex.I_sq, I_pow3]
  try ring_nf
  try norm_num

-- pattern (1, 3, 3): identifies psiP (bunched detection in mode 3)
lemma zero_133_phiP : rawAmp3 Vk1 1 3 3 BellLabel.phiP = 0 := by
  simp only [rawAmp3, perm3, V10, V11, V12, V13, V14, V20, V21, V22, V23, V24,
    V30, V31, V32, V33, V34, V40, V41, V42, V43, V44, s6_eq]
  ring_nf
  try simp only [s2_pow2, s2_pow3, s3_pow2, s3_pow3, Complex.I_sq, I_pow3]
  try ring_nf
  try norm_num

lemma zero_133_phiM : rawAmp3 Vk1 1 3 3 BellLabel.phiM = 0 := by
  simp only [rawAmp3, perm3, V10, V11, V12, V13, V14, V20, V21, V22, V23, V24,
    V30, V31, V32, V33, V34, V40, V41, V42, V43, V44, s6_eq]
  ring_nf
  try simp only [s2_pow2, s2_pow3, s3_pow2, s3_pow3, Complex.I_sq, I_pow3]
  try ring_nf
  try norm_num

lemma val_133_psiP : rawAmp3 Vk1 1 3 3 BellLabel.psiP = (1/4) * s2 * (Complex.I - s3) := by
  simp only [rawAmp3, perm3, V10, V11, V12, V13, V14, V20, V21, V22, V23, V24,
    V30, V31, V32, V33, V34, V40, V41, V42, V43, V44, s6_eq]
  ring_nf
  try simp only [s2_pow2, s2_pow3, s3_pow2, s3_pow3, Complex.I_sq, I_pow3]
  try ring_nf
  try norm_num

lemma zero_133_psiM : rawAmp3 Vk1 1 3 3 BellLabel.psiM = 0 := by
  simp only [rawAmp3, perm3, V10, V11, V12, V13, V14, V20, V21, V22, V23, V24,
    V30, V31, V32, V33, V34, V40, V41, V42, V43, V44, s6_eq]
  ring_nf
  try simp only [s2_pow2, s2_pow3, s3_pow2, s3_pow3, Complex.I_sq, I_pow3]
  try ring_nf
  try norm_num

-- pattern (1, 2, 2): identifies psiM (bunched detection in mode 2)
lemma zero_122_phiP : rawAmp3 Vk1 1 2 2 BellLabel.phiP = 0 := by
  simp only [rawAmp3, perm3, V10, V11, V12, V13, V14, V20, V21, V22, V23, V24,
    V30, V31, V32, V33, V34, V40, V41, V42, V43, V44, s6_eq]
  ring_nf
  try simp only [s2_pow2, s2_pow3, s3_pow2, s3_pow3, Complex.I_sq, I_pow3]
  try ring_nf
  try norm_num

lemma zero_122_phiM : rawAmp3 Vk1 1 2 2 BellLabel.phiM = 0 := by
  simp only [rawAmp3, perm3, V10, V11, V12, V13, V14, V20, V21, V22, V23, V24,
    V30, V31, V32, V33, V34, V40, V41, V42, V43, V44, s6_eq]
  ring_nf
  try simp only [s2_pow2, s2_pow3, s3_pow2, s3_pow3, Complex.I_sq, I_pow3]
  try ring_nf
  try norm_num

lemma zero_122_psiP : rawAmp3 Vk1 1 2 2 BellLabel.psiP = 0 := by
  simp only [rawAmp3, perm3, V10, V11, V12, V13, V14, V20, V21, V22, V23, V24,
    V30, V31, V32, V33, V34, V40, V41, V42, V43, V44, s6_eq]
  ring_nf
  try simp only [s2_pow2, s2_pow3, s3_pow2, s3_pow3, Complex.I_sq, I_pow3]
  try ring_nf
  try norm_num

lemma val_122_psiM : rawAmp3 Vk1 1 2 2 BellLabel.psiM = (-1/2) * Complex.I * s2 := by
  simp only [rawAmp3, perm3, V10, V11, V12, V13, V14, V20, V21, V22, V23, V24,
    V30, V31, V32, V33, V34, V40, V41, V42, V43, V44, s6_eq]
  ring_nf
  try simp only [s2_pow2, s2_pow3, s3_pow2, s3_pow3, Complex.I_sq, I_pow3]
  try ring_nf
  try norm_num

/-! ### The four identification witnesses -/

lemma identifies_134_phiP : Identifies3 Vk1 1 3 4 BellLabel.phiP := by
  unfold Identifies3
  refine ⟨?_, ?_⟩
  · rw [val_134_phiP]
    exact mul_ne_zero (by norm_num) (sub_ne_zero.mpr s3_ne_I)
  · intro nu hnu
    cases nu with
    | phiP => exact absurd rfl hnu
    | phiM => exact zero_134_phiM
    | psiP => exact zero_134_psiP
    | psiM => exact zero_134_psiM

lemma identifies_124_phiM : Identifies3 Vk1 1 2 4 BellLabel.phiM := by
  unfold Identifies3
  refine ⟨?_, ?_⟩
  · rw [val_124_phiM]
    exact mul_ne_zero (by norm_num) (sub_ne_zero.mpr one_ne_I_mul_s3)
  · intro nu hnu
    cases nu with
    | phiP => exact zero_124_phiP
    | phiM => exact absurd rfl hnu
    | psiP => exact zero_124_psiP
    | psiM => exact zero_124_psiM

lemma identifies_133_psiP : Identifies3 Vk1 1 3 3 BellLabel.psiP := by
  unfold Identifies3
  refine ⟨?_, ?_⟩
  · rw [val_133_psiP]
    exact mul_ne_zero (mul_ne_zero (by norm_num) s2_ne_zero)
      (sub_ne_zero.mpr (Ne.symm s3_ne_I))
  · intro nu hnu
    cases nu with
    | phiP => exact zero_133_phiP
    | phiM => exact zero_133_phiM
    | psiP => exact absurd rfl hnu
    | psiM => exact zero_133_psiM

lemma identifies_122_psiM : Identifies3 Vk1 1 2 2 BellLabel.psiM := by
  unfold Identifies3
  refine ⟨?_, ?_⟩
  · rw [val_122_psiM]
    exact mul_ne_zero (mul_ne_zero (by norm_num) Complex.I_ne_zero) s2_ne_zero
  · intro nu hnu
    cases nu with
    | phiP => exact zero_122_phiP
    | phiM => exact zero_122_phiM
    | psiP => exact zero_122_psiP
    | psiM => exact absurd rfl hnu

/-- The k = 1 counterpart of `p3_at_most_three`: with one ancilla photon in input
mode 4, the explicit 5-mode interferometer `Vk1` identifies all four Bell states. -/
theorem p3_k1_witness_all_four : ∀ mu : BellLabel, ∃ i j k : Fin 5, Identifies3 Vk1 i j k mu := by
  intro mu
  cases mu with
  | phiP => exact ⟨1, 3, 4, identifies_134_phiP⟩
  | phiM => exact ⟨1, 2, 4, identifies_124_phiM⟩
  | psiP => exact ⟨1, 3, 3, identifies_133_psiP⟩
  | psiM => exact ⟨1, 2, 2, identifies_122_psiM⟩

end

end Empiricist

/-! ## Appended: unitarity of `Vk1` and the k = 1 existence theorem -/

set_option maxHeartbeats 4000000

namespace Empiricist

noncomputable section

/-! ### Row 0 entries, by definitional unfolding -/

lemma V00 : Vk1 0 0 = 0 := rfl
lemma V01 : Vk1 0 1 = (-1/4) * s2 + (-1/4 * Complex.I) * s6 := rfl
lemma V02 : Vk1 0 2 = (1/8) * s2 + (-1/8 * Complex.I) * s6 := rfl
lemma V03 : Vk1 0 3 = (1/4) + (-1/4 * Complex.I) * s3 := rfl
lemma V04 : Vk1 0 4 = (1/4) * s2 := rfl

/-! ### Complex conjugation on the atomic constants -/

lemma star_eq_conj (z : ℂ) : star z = (starRingEnd ℂ) z := rfl

lemma conj_s2 : (starRingEnd ℂ) s2 = s2 := by
  simp only [s2, Complex.conj_ofReal]

lemma conj_s3 : (starRingEnd ℂ) s3 = s3 := by
  simp only [s3, Complex.conj_ofReal]

lemma conj_s6 : (starRingEnd ℂ) s6 = s6 := by
  simp only [s6, Complex.conj_ofReal]

/-- `Vk1` is unitary (its columns are orthonormal: `Vk1ᴴ * Vk1 = 1`), hence it is a
passive linear-optical 5-mode interferometer. -/
theorem Vk1_unitary : Vk1 ∈ Matrix.unitaryGroup (Fin 5) ℂ := by
  rw [Matrix.mem_unitaryGroup_iff']
  ext i j
  simp only [Matrix.mul_apply, Fin.sum_univ_five, Matrix.star_apply, star_eq_conj]
  fin_cases i <;> fin_cases j <;>
    (try simp [V00, V01, V02, V03, V04, V10, V11, V12, V13, V14,
      V20, V21, V22, V23, V24, V30, V31, V32, V33, V34,
      V40, V41, V42, V43, V44, Matrix.one_apply,
      map_add, map_mul, map_neg, map_div₀, map_one, map_ofNat,
      Complex.conj_I, Complex.conj_ofReal, conj_s2, conj_s3, conj_s6, s6_eq]) <;>
    (try ring_nf) <;>
    (try simp only [s2_pow2, s2_pow3, s3_pow2, s3_pow3, Complex.I_sq, I_pow3]) <;>
    (try ring_nf) <;>
    (try norm_num) <;>
    (try simp [s2_sq, s3_sq, s2_pow2, s3_pow2, Complex.I_sq, Complex.I_mul_I]) <;>
    (try ring_nf) <;>
    (try norm_num)

/-- The k = 1 counterpart of the formalized k = 0 impossibility theorem
`p3_at_most_three`: there EXISTS a unitary 5-mode interferometer (one ancilla
photon in input mode 4) that identifies all four Bell states. -/
theorem p3_k1_all_four_exists :
    ∃ V ∈ Matrix.unitaryGroup (Fin 5) ℂ, ∀ mu : BellLabel, ∃ i j k : Fin 5, Identifies3 V i j k mu :=
  ⟨Vk1, Vk1_unitary, p3_k1_witness_all_four⟩

end

end Empiricist

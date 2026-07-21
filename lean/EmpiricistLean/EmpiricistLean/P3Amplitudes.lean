import Mathlib.Data.Complex.Basic
import Mathlib.Data.Fin.VecNotation
import Mathlib.LinearAlgebra.Matrix.Trace
import Mathlib.Tactic.FinCases
import Mathlib.Tactic.Ring
import Mathlib.Tactic.DeriveFintype
import EmpiricistLean.Basic

namespace Empiricist

open Matrix

noncomputable section

/-- The 2×2 permanent of `U` over rows `{i, j}` and columns `{a, b}`.
For `i = j` this is `2 * U i a * U i b` (the bunched doubled-row case). -/
def perm2 (U : Matrix (Fin 4) (Fin 4) ℂ) (i j : Fin 4) (a b : Fin 4) : ℂ :=
  U i a * U j b + U j a * U i b

/-- Labels for the four Bell states. -/
inductive BellLabel
  | phiP
  | phiM
  | psiP
  | psiM
  deriving DecidableEq, Fintype

/-- Un-normalized Bell amplitudes for the click pair `{i, j}` (dual-rail encoding:
`phi± = |1010⟩ ± |0101⟩` on column pairs `{0,2}/{1,3}`, `psi± = |1001⟩ ± |0110⟩`
on `{0,3}/{1,2}`). -/
def rawAmp (U : Matrix (Fin 4) (Fin 4) ℂ) (i j : Fin 4) : BellLabel → ℂ
  | .phiP => perm2 U i j 0 2 + perm2 U i j 1 3
  | .phiM => perm2 U i j 0 2 - perm2 U i j 1 3
  | .psiP => perm2 U i j 0 3 + perm2 U i j 1 2
  | .psiM => perm2 U i j 0 3 - perm2 U i j 1 2

/-- The click pair `{i, j}` identifies the Bell label `mu`: its amplitude is nonzero
and all other Bell amplitudes vanish. -/
def Identifies (U : Matrix (Fin 4) (Fin 4) ℂ) (i j : Fin 4) (mu : BellLabel) : Prop :=
  rawAmp U i j mu ≠ 0 ∧ ∀ nu : BellLabel, nu ≠ mu → rawAmp U i j nu = 0

lemma perm2_comm (U : Matrix (Fin 4) (Fin 4) ℂ) (i j a b : Fin 4) :
    perm2 U j i a b = perm2 U i j a b := by
  simp only [perm2]
  ring

lemma rawAmp_comm (U : Matrix (Fin 4) (Fin 4) ℂ) (i j : Fin 4) :
    rawAmp U j i = rawAmp U i j := by
  funext mu
  cases mu <;> simp only [rawAmp, perm2] <;> ring

lemma identifies_comm (U : Matrix (Fin 4) (Fin 4) ℂ) (i j : Fin 4) (mu : BellLabel) :
    Identifies U j i mu ↔ Identifies U i j mu := by
  unfold Identifies
  rw [rawAmp_comm U i j]

/-- The 2×2 identity Pauli matrix. -/
def sigma0 : Matrix (Fin 2) (Fin 2) ℂ := Matrix.of ![![1, 0], ![0, 1]]

/-- The Pauli X matrix. -/
def sigmaX : Matrix (Fin 2) (Fin 2) ℂ := Matrix.of ![![0, 1], ![1, 0]]

/-- The Pauli Y matrix. -/
def sigmaY : Matrix (Fin 2) (Fin 2) ℂ := Matrix.of ![![0, -Complex.I], ![Complex.I, 0]]

/-- The Pauli Z matrix. -/
def sigmaZ : Matrix (Fin 2) (Fin 2) ℂ := Matrix.of ![![1, 0], ![0, -1]]

/-- The row block of `U` on rows `{i, j}` and columns `{0, 1}`. -/
def Xblk (U : Matrix (Fin 4) (Fin 4) ℂ) (i j : Fin 4) : Matrix (Fin 2) (Fin 2) ℂ :=
  Matrix.of ![![U i 0, U i 1], ![U j 0, U j 1]]

/-- The row block of `U` on rows `{i, j}` and columns `{2, 3}`. -/
def Yblk (U : Matrix (Fin 4) (Fin 4) ℂ) (i j : Fin 4) : Matrix (Fin 2) (Fin 2) ℂ :=
  Matrix.of ![![U i 2, U i 3], ![U j 2, U j 3]]

/-- The interference kernel `Q = Xᵀ · σX · Y` for the click pair `{i, j}`. -/
def Q (U : Matrix (Fin 4) (Fin 4) ℂ) (i j : Fin 4) : Matrix (Fin 2) (Fin 2) ℂ :=
  (Xblk U i j)ᵀ * sigmaX * Yblk U i j

/-- The interference kernel is exactly the matrix of 2×2 permanents:
`Q₀₀ = perm₂(0,2)`, `Q₀₁ = perm₂(0,3)`, `Q₁₀ = perm₂(1,2)`, `Q₁₁ = perm₂(1,3)`. -/
lemma Q_eq (U : Matrix (Fin 4) (Fin 4) ℂ) (i j : Fin 4) :
    Q U i j = Matrix.of ![![perm2 U i j 0 2, perm2 U i j 0 3],
                          ![perm2 U i j 1 2, perm2 U i j 1 3]] := by
  ext a b
  fin_cases a <;> fin_cases b <;>
    simp [Q, Xblk, Yblk, sigmaX, perm2, Matrix.mul_apply, Fin.sum_univ_two,
      Matrix.transpose_apply, Matrix.of_apply, Matrix.cons_val_zero,
      Matrix.cons_val_one, Matrix.head_cons] <;>
    ring

/-- The Pauli/trace representation of the raw Bell amplitudes:
`phiP = tr Q`, `psiP = tr(σX Q)`, `psiM = -I · tr(σY Q)`, `phiM = tr(σZ Q)`.
(The constant in the `psiM` clause is `-I`: one computes
`tr(σY Q) = -I·Q₁₀ + I·Q₀₁ = I·(Q₀₁ - Q₁₀) = I · psiM`, hence `psiM = -I · tr(σY Q)`.) -/
theorem rawAmp_eq_traceForm (U : Matrix (Fin 4) (Fin 4) ℂ) (i j : Fin 4) :
    rawAmp U i j .phiP = Matrix.trace (Q U i j) ∧
    rawAmp U i j .psiP = Matrix.trace (sigmaX * Q U i j) ∧
    rawAmp U i j .psiM = -Complex.I * Matrix.trace (sigmaY * Q U i j) ∧
    rawAmp U i j .phiM = Matrix.trace (sigmaZ * Q U i j) := by
  refine ⟨?_, ?_, ?_, ?_⟩
  · -- phiP = tr Q
    rw [Q_eq]
    simp [rawAmp, Matrix.trace_fin_two, Matrix.of_apply, Matrix.cons_val_zero,
      Matrix.cons_val_one, Matrix.head_cons] <;> ring
  · -- psiP = tr (σX Q)
    rw [Q_eq]
    simp [rawAmp, sigmaX, Matrix.trace_fin_two, Matrix.mul_apply,
      Fin.sum_univ_two, Matrix.of_apply, Matrix.cons_val_zero,
      Matrix.cons_val_one, Matrix.head_cons] <;> ring
  · -- psiM = -I · tr (σY Q)
    have h : Matrix.trace (sigmaY * Q U i j) =
        Complex.I * (perm2 U i j 0 3 - perm2 U i j 1 2) := by
      rw [Q_eq]
      simp [sigmaY, Matrix.trace_fin_two, Matrix.mul_apply, Fin.sum_univ_two,
        Matrix.of_apply, Matrix.cons_val_zero, Matrix.cons_val_one,
        Matrix.head_cons] <;> ring
    have hI : -Complex.I * Complex.I = 1 := by
      rw [neg_mul, Complex.I_mul_I, neg_neg]
    rw [h, ← mul_assoc, hI, one_mul]
    simp only [rawAmp]
  · -- phiM = tr (σZ Q)
    rw [Q_eq]
    simp [rawAmp, sigmaZ, Matrix.trace_fin_two, Matrix.mul_apply,
      Fin.sum_univ_two, Matrix.of_apply, Matrix.cons_val_zero,
      Matrix.cons_val_one, Matrix.head_cons] <;> ring

end

end Empiricist

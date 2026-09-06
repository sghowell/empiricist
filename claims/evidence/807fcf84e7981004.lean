/-
P3 / L2 (k = 0 chain): For a detector unitary `U : Matrix (Fin 4) (Fin 4) ℂ` and a
detector row-index `i : Fin 4`, the row-decoupling label set `Mset U i` — Bell labels
`μ` with `y_i` a *nonzero* scalar multiple of `x_i ⬝ K μ`, `K μ := σ_y * pauliOf μ` —
has at most two elements.

Proof (Fable's sketch): if `μ ≠ ν` both decouple row `i`, then `w := x_i ᵥ* σ_y ≠ 0`
satisfies `w ᵥ* P_μ = e • (w ᵥ* P_ν)` with `e ≠ 0`.  Right-multiplying by `P_ν` and
using `P_ν² = 1` together with the Pauli product rule `P_μ P_ν = c • P_{μ⊕ν}` (Klein
label `mulLabel`), `w` is a left eigenvector of `P_{μ⊕ν}`.  Three distinct decoupling
labels give left-eigenvector relations for two *distinct non-identity* Pauli labels
`μ⊕ν ≠ μ⊕ρ`; transposing (each Pauli satisfies `Pᵀ = ±P`) turns these into genuine
`*ᵥ` eigenvector relations, contradicting the trusted `pauli_no_common_eigenvector`.

FIX this round: `pauli_mul` / `pauli_transpose` previously used
`first | exact ⟨c, _, by tac⟩ | ...`; a failing nested `by` block does NOT make the
`exact` alternative fail (the error is recoverable), so `first` committed to the wrong
constant.  Both lemmas now use tactic-level `first` alternatives ending in `done`,
which genuinely backtrack until the correct phase in `{1, I, -I, -1}` is found.
-/
import Mathlib.LinearAlgebra.UnitaryGroup
import Mathlib.Data.Finset.Card
import EmpiricistLean.P3Amplitudes
import EmpiricistLean.P3Pauli
import EmpiricistLean.P3L1

open Matrix Complex

namespace Empiricist

/-! ### Row blocks of `U` at detector row `i` -/

/-- `x_i` : the length-2 row block of `U` at row `i`, over columns `0, 1`. -/
def xRow (U : Matrix (Fin 4) (Fin 4) ℂ) (i : Fin 4) : Fin 2 → ℂ :=
  fun a => U i ⟨(a : ℕ), by omega⟩

/-- `y_i` : the length-2 row block of `U` at row `i`, over columns `2, 3`. -/
def yRow (U : Matrix (Fin 4) (Fin 4) ℂ) (i : Fin 4) : Fin 2 → ℂ :=
  fun a => U i ⟨(a : ℕ) + 2, by omega⟩

/-- The decoupling kernel `K μ = σ_y * (pauliOf μ)` attached to the Bell label `μ`. -/
noncomputable def Kmat (μ : BellLabel) : Matrix (Fin 2) (Fin 2) ℂ :=
  sigmaY * pauliOf μ

/-- Detector `i`'s rows *decouple* at Bell label `μ` :
`y_i` is a nonzero scalar multiple of the row vector `x_i ⬝ K μ`. -/
def RowDecouples (U : Matrix (Fin 4) (Fin 4) ℂ) (i : Fin 4) (μ : BellLabel) : Prop :=
  ∃ c : ℂ, c ≠ 0 ∧ yRow U i = c • (xRow U i ᵥ* Kmat μ)

/-- `M_i` : the row-decoupling label set of detector `i`. -/
noncomputable def Mset (U : Matrix (Fin 4) (Fin 4) ℂ) (i : Fin 4) : Finset BellLabel :=
  @Finset.filter BellLabel (fun μ => RowDecouples U i μ)
    (fun _ => Classical.propDecidable _) Finset.univ

theorem mem_Mset {U : Matrix (Fin 4) (Fin 4) ℂ} {i : Fin 4} {μ : BellLabel} :
    μ ∈ Mset U i ↔ RowDecouples U i μ := by
  simp [Mset]

/-! ### Small vector/matrix helper lemmas (proved entrywise, no name guessing) -/

theorem smul_vecMul' (a : ℂ) (v : Fin 2 → ℂ) (M : Matrix (Fin 2) (Fin 2) ℂ) :
    (a • v) ᵥ* M = a • (v ᵥ* M) := by
  ext j
  simp only [Matrix.vecMul, dotProduct, Pi.smul_apply, smul_eq_mul, Fin.sum_univ_two]
  ring

theorem vecMul_smulMat' (c : ℂ) (v : Fin 2 → ℂ) (M : Matrix (Fin 2) (Fin 2) ℂ) :
    v ᵥ* (c • M) = c • (v ᵥ* M) := by
  ext j
  simp only [Matrix.vecMul, dotProduct, Matrix.smul_apply, Pi.smul_apply, smul_eq_mul,
    Fin.sum_univ_two]
  ring

theorem smulMat_mulVec' (c : ℂ) (M : Matrix (Fin 2) (Fin 2) ℂ) (v : Fin 2 → ℂ) :
    (c • M) *ᵥ v = c • (M *ᵥ v) := by
  ext j
  simp only [Matrix.mulVec, dotProduct, Matrix.smul_apply, Pi.smul_apply, smul_eq_mul,
    Fin.sum_univ_two]
  ring

theorem transpose_mulVec' (M : Matrix (Fin 2) (Fin 2) ℂ) (v : Fin 2 → ℂ) :
    Mᵀ *ᵥ v = v ᵥ* M := by
  ext j
  simp only [Matrix.mulVec, Matrix.vecMul, dotProduct, Matrix.transpose_apply,
    Fin.sum_univ_two]
  ring

/-! ### The Klein four-group of Bell labels and Pauli algebra facts -/

/-- The Klein group law on Bell labels induced by Pauli multiplication:
`pauliOf m * pauliOf n` is a nonzero multiple of `pauliOf (mulLabel m n)`. -/
def mulLabel : BellLabel → BellLabel → BellLabel
  | BellLabel.phiP, n => n
  | BellLabel.psiP, BellLabel.phiP => BellLabel.psiP
  | BellLabel.psiP, BellLabel.psiP => BellLabel.phiP
  | BellLabel.psiP, BellLabel.psiM => BellLabel.phiM
  | BellLabel.psiP, BellLabel.phiM => BellLabel.psiM
  | BellLabel.psiM, BellLabel.phiP => BellLabel.psiM
  | BellLabel.psiM, BellLabel.psiP => BellLabel.phiM
  | BellLabel.psiM, BellLabel.psiM => BellLabel.phiP
  | BellLabel.psiM, BellLabel.phiM => BellLabel.psiP
  | BellLabel.phiM, BellLabel.phiP => BellLabel.phiM
  | BellLabel.phiM, BellLabel.psiP => BellLabel.psiM
  | BellLabel.phiM, BellLabel.psiM => BellLabel.psiP
  | BellLabel.phiM, BellLabel.phiM => BellLabel.phiP

theorem mulLabel_ne_phiP : ∀ {m n : BellLabel}, m ≠ n → mulLabel m n ≠ BellLabel.phiP := by
  intro m n hmn
  cases m <;> cases n <;> simp_all [mulLabel]

theorem mulLabel_left_inj : ∀ {m ν ρ : BellLabel}, ν ≠ ρ → mulLabel m ν ≠ mulLabel m ρ := by
  intro m ν ρ h
  cases m <;> cases ν <;> cases ρ <;> simp_all [mulLabel]

/-- Every Pauli squares to the identity. -/
theorem pauli_sq (m : BellLabel) : pauliOf m * pauliOf m = 1 := by
  cases m
  all_goals
    ext a b
    fin_cases a <;> fin_cases b <;>
      simp [pauliOf, sigma0, sigmaX, sigmaY, sigmaZ, Matrix.mul_apply, Fin.sum_univ_two,
        Matrix.one_apply, Complex.I_mul_I]

/-- Pauli product rule: `pauliOf m * pauliOf n = c • pauliOf (mulLabel m n)`, `c ≠ 0`.
The phase `c ∈ {1, I, -I, -1}` is found by genuine tactic backtracking (`first` with
alternatives that must `done`). -/
theorem pauli_mul (m n : BellLabel) :
    ∃ c : ℂ, c ≠ 0 ∧ pauliOf m * pauliOf n = c • pauliOf (mulLabel m n) := by
  cases m <;> cases n <;>
    first
      | (refine ⟨1, one_ne_zero, ?_⟩
         ext a b
         fin_cases a <;> fin_cases b <;>
           simp [pauliOf, mulLabel, sigma0, sigmaX, sigmaY, sigmaZ,
             Matrix.mul_apply, Fin.sum_univ_two, Matrix.one_apply, Complex.I_mul_I]
         done)
      | (refine ⟨Complex.I, Complex.I_ne_zero, ?_⟩
         ext a b
         fin_cases a <;> fin_cases b <;>
           simp [pauliOf, mulLabel, sigma0, sigmaX, sigmaY, sigmaZ,
             Matrix.mul_apply, Fin.sum_univ_two, Matrix.one_apply, Complex.I_mul_I]
         done)
      | (refine ⟨-Complex.I, neg_ne_zero.mpr Complex.I_ne_zero, ?_⟩
         ext a b
         fin_cases a <;> fin_cases b <;>
           simp [pauliOf, mulLabel, sigma0, sigmaX, sigmaY, sigmaZ,
             Matrix.mul_apply, Fin.sum_univ_two, Matrix.one_apply, Complex.I_mul_I]
         done)
      | (refine ⟨-1, neg_ne_zero.mpr one_ne_zero, ?_⟩
         ext a b
         fin_cases a <;> fin_cases b <;>
           simp [pauliOf, mulLabel, sigma0, sigmaX, sigmaY, sigmaZ,
             Matrix.mul_apply, Fin.sum_univ_two, Matrix.one_apply, Complex.I_mul_I]
         done)

/-- Every Pauli is symmetric up to a nonzero sign: `Pᵀ = ε • P` with `ε ∈ {1, -1}`. -/
theorem pauli_transpose (m : BellLabel) :
    ∃ ε : ℂ, ε ≠ 0 ∧ (pauliOf m)ᵀ = ε • pauliOf m := by
  cases m <;>
    first
      | (refine ⟨1, one_ne_zero, ?_⟩
         ext a b
         fin_cases a <;> fin_cases b <;>
           simp [pauliOf, sigma0, sigmaX, sigmaY, sigmaZ]
         done)
      | (refine ⟨-1, neg_ne_zero.mpr one_ne_zero, ?_⟩
         ext a b
         fin_cases a <;> fin_cases b <;>
           simp [pauliOf, sigma0, sigmaX, sigmaY, sigmaZ]
         done)

/-- A left (row) eigenvector relation transposes to a genuine `*ᵥ` eigenvector
relation, since each Pauli satisfies `Pᵀ = ε • P` with `ε ≠ 0`. -/
theorem mulVec_eigen {P : Matrix (Fin 2) (Fin 2) ℂ} {ε : ℂ} (hε : ε ≠ 0)
    (hT : Pᵀ = ε • P) {w : Fin 2 → ℂ} {a : ℂ} (h : w ᵥ* P = a • w) :
    P *ᵥ w = (ε⁻¹ * a) • w := by
  have h1 : ε • (P *ᵥ w) = a • w := by
    rw [← smulMat_mulVec', ← hT, transpose_mulVec', h]
  calc P *ᵥ w = ε⁻¹ • (ε • (P *ᵥ w)) := by
        rw [smul_smul, inv_mul_cancel₀ hε, one_smul]
    _ = ε⁻¹ • (a • w) := by rw [h1]
    _ = (ε⁻¹ * a) • w := by rw [smul_smul]

/-- Core step: parallel Pauli images `w ᵥ* P_α = e • (w ᵥ* P_β)` make `w` a left
eigenvector of the product Pauli `P_{α⊕β}`. -/
theorem left_eigen_of_pair {w : Fin 2 → ℂ} {α β : BellLabel} {e : ℂ}
    (hrel : w ᵥ* pauliOf α = e • (w ᵥ* pauliOf β)) :
    ∃ a : ℂ, w ᵥ* pauliOf (mulLabel α β) = a • w := by
  obtain ⟨c, hc, hmul⟩ := pauli_mul α β
  refine ⟨c⁻¹ * e, ?_⟩
  have h1 : (w ᵥ* pauliOf α) ᵥ* pauliOf β = e • ((w ᵥ* pauliOf β) ᵥ* pauliOf β) := by
    rw [hrel, smul_vecMul']
  rw [Matrix.vecMul_vecMul, Matrix.vecMul_vecMul, hmul, pauli_sq β, Matrix.vecMul_one,
    vecMul_smulMat'] at h1
  calc w ᵥ* pauliOf (mulLabel α β)
      = c⁻¹ • (c • (w ᵥ* pauliOf (mulLabel α β))) := by
        rw [smul_smul, inv_mul_cancel₀ hc, one_smul]
    _ = c⁻¹ • (e • w) := by rw [h1]
    _ = (c⁻¹ * e) • w := by rw [smul_smul]

/-! ### Auxiliary facts about the row blocks -/

/-- `σ_y` is an involution. -/
theorem sigmaY_sq : sigmaY * sigmaY = 1 := by
  ext a b
  fin_cases a <;> fin_cases b <;>
    simp [sigmaY, Matrix.mul_apply, Fin.sum_univ_two, Matrix.one_apply, Complex.I_mul_I]

/-- A unitary matrix has no zero row: at least one of the two row blocks is nonzero. -/
theorem row_ne_zero_of_unitary {U : Matrix (Fin 4) (Fin 4) ℂ}
    (hU : U ∈ Matrix.unitaryGroup (Fin 4) ℂ) (i : Fin 4) :
    xRow U i ≠ 0 ∨ yRow U i ≠ 0 := by
  by_contra h
  push_neg at h
  obtain ⟨hx0, hy0⟩ := h
  have hrow : ∀ j : Fin 4, U i j = 0 := by
    intro j
    rcases Nat.lt_or_ge (j : ℕ) 2 with hj | hj
    · have h2 := congrFun hx0 ⟨(j : ℕ), hj⟩
      simpa [xRow, Fin.eta] using h2
    · have h2 := congrFun hy0 ⟨(j : ℕ) - 2, by omega⟩
      have h3 : (j : ℕ) - 2 + 2 = (j : ℕ) := by omega
      simpa [yRow, h3, Fin.eta] using h2
  have h1 : (U * star U) i i = (1 : Matrix (Fin 4) (Fin 4) ℂ) i i := by
    rw [Matrix.mem_unitaryGroup_iff.mp hU]
  rw [Matrix.one_apply_eq] at h1
  have h0 : (U * star U) i i = 0 := by
    rw [Matrix.mul_apply]
    refine Finset.sum_eq_zero fun j _ => ?_
    rw [hrow j, zero_mul]
  exact one_ne_zero (h1.symm.trans h0)

/-- If `x_i ≠ 0` then the conjugated row vector `w = x_i ᵥ* σ_y` is nonzero. -/
theorem w_ne_zero {U : Matrix (Fin 4) (Fin 4) ℂ} {i : Fin 4}
    (hx : xRow U i ≠ 0) : xRow U i ᵥ* sigmaY ≠ 0 := by
  intro hw0
  apply hx
  have h := congrArg (fun v => v ᵥ* sigmaY) hw0
  simpa only [Matrix.vecMul_vecMul, sigmaY_sq, Matrix.vecMul_one,
    Matrix.zero_vecMul] using h

/-- Two decoupling labels force `w ᵥ* P_α = e • (w ᵥ* P_β)` with `e ≠ 0`,
where `w = x_i ᵥ* σ_y`. -/
theorem decouple_pair {U : Matrix (Fin 4) (Fin 4) ℂ} {i : Fin 4} {α β : BellLabel}
    (hα : RowDecouples U i α) (hβ : RowDecouples U i β) :
    ∃ e : ℂ, e ≠ 0 ∧
      (xRow U i ᵥ* sigmaY) ᵥ* pauliOf α = e • ((xRow U i ᵥ* sigmaY) ᵥ* pauliOf β) := by
  obtain ⟨c, hc, hyc⟩ := hα
  obtain ⟨d, hd, hyd⟩ := hβ
  refine ⟨c⁻¹ * d, mul_ne_zero (inv_ne_zero hc) hd, ?_⟩
  have hcd : c • (xRow U i ᵥ* Kmat α) = d • (xRow U i ᵥ* Kmat β) := by
    rw [← hyc, ← hyd]
  have hmain : xRow U i ᵥ* Kmat α = (c⁻¹ * d) • (xRow U i ᵥ* Kmat β) := by
    calc xRow U i ᵥ* Kmat α
        = c⁻¹ • (c • (xRow U i ᵥ* Kmat α)) := by
          rw [smul_smul, inv_mul_cancel₀ hc, one_smul]
      _ = c⁻¹ • (d • (xRow U i ᵥ* Kmat β)) := by rw [hcd]
      _ = (c⁻¹ * d) • (xRow U i ᵥ* Kmat β) := by rw [smul_smul]
  simpa only [Kmat, ← Matrix.vecMul_vecMul] using hmain

/-! ### Main results -/

/-- **Core of L2.** If row `i` of `U` is not identically zero, then at most two Bell
labels can row-decouple detector `i` (Fable's common-eigenvector argument). -/
theorem card_Mset_le_two_of_row {U : Matrix (Fin 4) (Fin 4) ℂ} {i : Fin 4}
    (h : xRow U i ≠ 0 ∨ yRow U i ≠ 0) :
    (Mset U i).card ≤ 2 := by
  by_contra hcard
  push_neg at hcard
  obtain ⟨μ, ν, ρ, hμ, hν, hρ, hμν, hμρ, hνρ⟩ := Finset.two_lt_card_iff.mp hcard
  rw [mem_Mset] at hμ hν hρ
  -- `x_i ≠ 0`: otherwise decoupling forces `y_i = 0`, so row `i` vanishes.
  have hx : xRow U i ≠ 0 := by
    rcases h with hx | hy
    · exact hx
    · intro hx0
      obtain ⟨c, hc, hyc⟩ := hμ
      apply hy
      rw [hyc, hx0, Matrix.zero_vecMul, smul_zero]
  have hw : xRow U i ᵥ* sigmaY ≠ 0 := w_ne_zero hx
  obtain ⟨e, he, heq⟩ := decouple_pair hμ hν
  obtain ⟨f, hf, hfq⟩ := decouple_pair hμ hρ
  -- `w` is a left eigenvector of the two distinct non-identity Paulis `μ⊕ν` and `μ⊕ρ`.
  obtain ⟨a, ha⟩ := left_eigen_of_pair heq
  obtain ⟨b, hb⟩ := left_eigen_of_pair hfq
  obtain ⟨ε₁, hε₁, hT₁⟩ := pauli_transpose (mulLabel μ ν)
  obtain ⟨ε₂, hε₂, hT₂⟩ := pauli_transpose (mulLabel μ ρ)
  exact pauli_no_common_eigenvector (mulLabel μ ν) (mulLabel μ ρ)
    (mulLabel_left_inj hνρ) (mulLabel_ne_phiP hμν) (mulLabel_ne_phiP hμρ)
    (xRow U i ᵥ* sigmaY) (ε₁⁻¹ * a) (ε₂⁻¹ * b) hw
    (mulVec_eigen hε₁ hT₁ ha) (mulVec_eigen hε₂ hT₂ hb)

/-- **L2.** For a detector unitary `U` and any detector row `i`, the row-decoupling
label set `M_i` contains at most two of the four Bell labels. -/
theorem card_Mset_le_two (U : Matrix (Fin 4) (Fin 4) ℂ)
    (hU : U ∈ Matrix.unitaryGroup (Fin 4) ℂ) (i : Fin 4) :
    (Mset U i).card ≤ 2 :=
  card_Mset_le_two_of_row (row_ne_zero_of_unitary hU i)

end Empiricist

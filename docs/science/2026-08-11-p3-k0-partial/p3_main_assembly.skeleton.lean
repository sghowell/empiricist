import Mathlib.Data.Complex.Basic
import Mathlib.LinearAlgebra.UnitaryGroup
import Mathlib.Data.Fintype.Card
import EmpiricistLean.Basic
import EmpiricistLean.P3Amplitudes
import EmpiricistLean.P3Pauli
import EmpiricistLean.P3L1
import EmpiricistLean.P3L2
import EmpiricistLean.P3Counting

namespace Empiricist

/- KNOWN from earlier probes (recorded, probes deleted):
   Q U i j = (Xblk U i j).transpose * sigmaX * Yblk U i j
   xRow U i = fun a => U i ⟨a, _⟩,  yRow U i = fun a => U i ⟨a+2, _⟩
   Kmat μ = sigmaY * pauliOf μ;  pauliOf: phiP↦σ0, phiM↦σZ, psiP↦σX, psiM↦σY
   pauli_orthogonal : ∀ μ ν, μ ≠ ν → (pauliOf μ * pauliOf ν).trace = 0
   pauli_no_common_eigenvector : ∀ μ ν, μ ≠ ν → μ ≠ phiP → ν ≠ phiP →
     ∀ v a b, v ≠ 0 → mulVec (pauliOf μ) v = a•v → mulVec (pauliOf ν) v = b•v → False
   prop_iff_traces_vanish : (∃ t ≠ 0, M = t • pauliOf μ) ↔
     ((pauliOf μ * M).trace ≠ 0 ∧ ∀ ν ≠ μ, (pauliOf ν * M).trace = 0)
   pauli_invertible : ∀ μ, IsUnit (pauliOf μ) -/

/- ===== PROBE A (DELETED in final): bodies of Xblk, Yblk, sigmaX, sigmaY. -/
example (U : Matrix (Fin 4) (Fin 4) ℂ) (i j : Fin 4) :
    (Xblk U i j, Yblk U i j, sigmaX, sigmaY) = 0 := by
  first | unfold Xblk Yblk sigmaX sigmaY
        | simp only [Xblk, Yblk, sigmaX, sigmaY] | skip
  exact ?_

/- ===== PROBE B (DELETED): body of RowDecouples (and Mset if it unfolds). -/
example (U : Matrix (Fin 4) (Fin 4) ℂ) (i : Fin 4) (μ : BellLabel) :
    RowDecouples U i μ := by
  first | unfold RowDecouples | simp only [RowDecouples] | skip
  exact ?_

/- ===== PROBE C (DELETED): bodies of DoubledEdges and FourCycle. -/
example (M : Fin 4 → Finset (Fin 4)) : DoubledEdges M ∧ FourCycle M := by
  first | unfold DoubledEdges FourCycle
        | simp only [DoubledEdges, FourCycle] | skip
  exact ?_

/- ===== PROBE D (DELETED): exact types of cover_structure, mem_Mset,
card_Mset_le_two, identifies_iff_prop. -/
example : False := by
  have h1 := @cover_structure
  have h2 := @mem_Mset
  have h3 := @card_Mset_le_two
  have h4 := @identifies_iff_prop
  exact ?_

/-- BRIDGE, left half: Q(i,j) = t • pauliOf μ (t ≠ 0) row-decouples detector i. -/
theorem bridge_left (U : Matrix (Fin 4) (Fin 4) ℂ)
    (hU : U ∈ Matrix.unitaryGroup (Fin 4) ℂ) (i j : Fin 4) (μ : BellLabel)
    (t : ℂ) (ht : t ≠ 0) (hQ : Q U i j = t • pauliOf μ) :
    RowDecouples U i μ := by
  -- HOLE bridge-left
  exact ?_

/-- BRIDGE, right half: Q(i,j) = t • pauliOf μ (t ≠ 0) row-decouples detector j. -/
theorem bridge_right (U : Matrix (Fin 4) (Fin 4) ℂ)
    (hU : U ∈ Matrix.unitaryGroup (Fin 4) ℂ) (i j : Fin 4) (μ : BellLabel)
    (t : ℂ) (ht : t ≠ 0) (hQ : Q U i j = t • pauliOf μ) :
    RowDecouples U j μ := by
  -- HOLE bridge-right
  exact ?_

/-- Diagonal patterns identify nothing: Q U i i is singular while
t • pauliOf μ with t ≠ 0 is invertible. -/
theorem no_diag_identify (U : Matrix (Fin 4) (Fin 4) ℂ)
    (hU : U ∈ Matrix.unitaryGroup (Fin 4) ℂ) (i : Fin 4) (μ : BellLabel)
    (h : Identifies U i i μ) : False := by
  obtain ⟨t, ht, hQ⟩ := (identifies_iff_prop U i i μ).mp h
  -- HOLE no-diag
  exact ?_

/-- BRIDGE (assembled): a pattern (i,j) identifying μ row-decouples BOTH detectors. -/
theorem identifies_rowDecouples
    (U : Matrix (Fin 4) (Fin 4) ℂ) (hU : U ∈ Matrix.unitaryGroup (Fin 4) ℂ)
    (i j : Fin 4) (μ : BellLabel) (h : Identifies U i j μ) :
    RowDecouples U i μ ∧ RowDecouples U j μ := by
  obtain ⟨t, ht, hQ⟩ := (identifies_iff_prop U i j μ).mp h
  exact ⟨bridge_left U hU i j μ t ht hQ, bridge_right U hU i j μ t ht hQ⟩

/-- CASE a (DoubledEdges): two detector-pairs share equal 2-label sets, but a
single pattern's Q is ∝ at most one Pauli, so at most 2 labels get identified. -/
theorem case_doubled (U : Matrix (Fin 4) (Fin 4) ℂ)
    (hU : U ∈ Matrix.unitaryGroup (Fin 4) ℂ) (e : BellLabel ≃ Fin 4)
    (hall : ∀ μ : BellLabel, ∃ i j : Fin 4, Identifies U i j μ)
    (hd : DoubledEdges (fun i => (Mset U i).image e)) : False := by
  -- HOLE case-a
  exact ?_

/-- CASE b (FourCycle): complementary-pair detectors force two rows of U to be
non-orthogonal — contradiction with U ∈ unitaryGroup (L3/L4 killer step). -/
theorem case_fourCycle (U : Matrix (Fin 4) (Fin 4) ℂ)
    (hU : U ∈ Matrix.unitaryGroup (Fin 4) ℂ) (e : BellLabel ≃ Fin 4)
    (hall : ∀ μ : BellLabel, ∃ i j : Fin 4, Identifies U i j μ)
    (hc : FourCycle (fun i => (Mset U i).image e)) : False := by
  -- HOLE case-b
  exact ?_

/-- FINAL (k=0 chain): for every 4×4 unitary U it is NOT the case that all
four Bell labels are identifiable by some detector pattern. -/
theorem p3_at_most_three
    (U : Matrix (Fin 4) (Fin 4) ℂ) (hU : U ∈ Matrix.unitaryGroup (Fin 4) ℂ) :
    ¬ ∀ μ : BellLabel, ∃ i j : Fin 4, Identifies U i j μ := by
  intro hall
  -- Step 1 (covering): every label lies in Mset U i for two DISTINCT detectors.
  have hcov : ∀ μ : BellLabel, ∃ i j : Fin 4, i ≠ j ∧ μ ∈ Mset U i ∧ μ ∈ Mset U j := by
    intro μ
    obtain ⟨i, j, hid⟩ := hall μ
    obtain ⟨hri, hrj⟩ := identifies_rowDecouples U hU i j μ hid
    have hi : μ ∈ Mset U i := mem_Mset.mpr hri
    have hj : μ ∈ Mset U j := mem_Mset.mpr hrj
    by_cases hij : i = j
    · subst hij
      exact (no_diag_identify U hU i μ hid).elim
    · exact ⟨i, j, hij, hi, hj⟩
  -- Transport Mset U along BellLabel ≃ Fin 4 to match Counting's types.
  have hc4 : Fintype.card BellLabel = 4 := by
    first | rfl | decide | simp | exact ?_
  let e : BellLabel ≃ Fin 4 := Fintype.equivFinOfCardEq hc4
  -- Step 2 (L2): each transported set has card ≤ 2.
  have hcard' : ∀ i : Fin 4, ((Mset U i).image e).card ≤ 2 := by
    intro i
    calc ((Mset U i).image e).card ≤ (Mset U i).card := Finset.card_image_le
      _ ≤ 2 := card_Mset_le_two U hU i
  -- Covering in the filter-card form required by cover_structure.
  have hcov2 : ∀ ν : Fin 4,
      2 ≤ (Finset.univ.filter (fun i => ν ∈ (Mset U i).image e)).card := by
    intro ν
    obtain ⟨i, j, hij, h1, h2⟩ := hcov (e.symm ν)
    have h1' : i ∈ Finset.univ.filter (fun i => ν ∈ (Mset U i).image e) := by
      refine Finset.mem_filter.mpr ⟨Finset.mem_univ _, ?_⟩
      have hm := Finset.mem_image_of_mem e h1
      rwa [Equiv.apply_symm_apply] at hm
    have h2' : j ∈ Finset.univ.filter (fun i => ν ∈ (Mset U i).image e) := by
      refine Finset.mem_filter.mpr ⟨Finset.mem_univ _, ?_⟩
      have hm := Finset.mem_image_of_mem e h2
      rwa [Equiv.apply_symm_apply] at hm
    exact Finset.one_lt_card.mpr ⟨i, h1', j, h2', hij⟩
  -- Step 3 (Counting): DoubledEdges ∨ FourCycle.
  have hstruct : DoubledEdges (fun i => (Mset U i).image e) ∨
      FourCycle (fun i => (Mset U i).image e) := by
    first
      | exact cover_structure (fun i => (Mset U i).image e) hcard' hcov2
      | exact cover_structure _ hcard' hcov2
      | exact ?_
  rcases hstruct with hd | hc
  · exact case_doubled U hU e hall hd
  · exact case_fourCycle U hU e hall hc

/-- Corollary: some Bell label is identified by NO pattern. -/
theorem p3_min_support
    (U : Matrix (Fin 4) (Fin 4) ℂ) (hU : U ∈ Matrix.unitaryGroup (Fin 4) ℂ) :
    ∃ μ : BellLabel, ∀ i j : Fin 4, ¬ Identifies U i j μ := by
  by_contra hcon
  push_neg at hcon
  exact p3_at_most_three U hU hcon

end Empiricist
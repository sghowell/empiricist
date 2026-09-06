import Mathlib.Data.Complex.Basic
import Mathlib.LinearAlgebra.UnitaryGroup
import Mathlib.Data.Fintype.Card
import EmpiricistLean.Basic
import EmpiricistLean.P3Amplitudes
import EmpiricistLean.P3Pauli
import EmpiricistLean.P3L1
import EmpiricistLean.P3L2
import EmpiricistLean.P3Counting
import EmpiricistLean.P3Bridge
import EmpiricistLean.P3Doubled
import EmpiricistLean.P3FourCycle

namespace Empiricist

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
  have hc4 : Fintype.card BellLabel = 4 := by decide
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
      FourCycle (fun i => (Mset U i).image e) :=
    cover_structure (fun i => (Mset U i).image e) hcard' hcov2
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

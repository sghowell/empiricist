import Mathlib.Data.Finset.Card
import Mathlib.Data.Fintype.BigOperators
import Mathlib.Algebra.Order.BigOperators.Group.Finset
import Mathlib.Tactic.FinCases
import Mathlib.Tactic.Linarith
import EmpiricistLean.Basic

namespace Empiricist

open Finset

/-- Case (a): the four detectors split into two disjoint pairs `{i, j}` and `{k, l}`;
the detectors in each pair carry the SAME 2-element label set, and the two label
sets are disjoint 2-element sets that together partition the four labels. -/
def DoubledEdges (M : Fin 4 → Finset (Fin 4)) : Prop :=
  ∃ i j k l : Fin 4, ({i, j, k, l} : Finset (Fin 4)) = Finset.univ ∧
    M i = M j ∧ M k = M l ∧
    (M i).card = 2 ∧ (M k).card = 2 ∧
    Disjoint (M i) (M k) ∧ M i ∪ M k = Finset.univ

/-- Case (b): a 4-cycle -- the detectors can be ordered `i₀ i₁ i₂ i₃` (all four of
them) and the labels ordered `a b c d` (all four, distinct) so that the label sets
are the consecutive pairs `{a,b}, {b,c}, {c,d}, {d,a}` around the cycle. -/
def FourCycle (M : Fin 4 → Finset (Fin 4)) : Prop :=
  ∃ i₀ i₁ i₂ i₃ : Fin 4, ({i₀, i₁, i₂, i₃} : Finset (Fin 4)) = Finset.univ ∧
    ∃ a b c d : Fin 4, ({a, b, c, d} : Finset (Fin 4)) = Finset.univ ∧
      M i₀ = {a, b} ∧ M i₁ = {b, c} ∧ M i₂ = {c, d} ∧ M i₃ = {d, a}

/-- A 2-element finset containing `a` is `{a, x}` for a unique other element `x`. -/
lemma exists_pair_eq {α : Type*} [DecidableEq α] {s : Finset α} {a : α}
    (hs : s.card = 2) (ha : a ∈ s) : ∃ x, x ≠ a ∧ s = {a, x} := by
  obtain ⟨p, q, hpq, rfl⟩ := Finset.card_eq_two.mp hs
  rcases Finset.mem_insert.mp ha with rfl | ha'
  · exact ⟨q, Ne.symm hpq, rfl⟩
  · rw [Finset.mem_singleton] at ha'
    subst ha'
    exact ⟨p, hpq, Finset.pair_comm p a⟩

/-- A 2-element finset containing two distinct elements is exactly that pair. -/
lemma eq_pair_of_mem {α : Type*} [DecidableEq α] {s : Finset α} {a b : α}
    (hs : s.card = 2) (hab : a ≠ b) (ha : a ∈ s) (hb : b ∈ s) : s = {a, b} :=
  (Finset.eq_of_subset_of_card_le
    (Finset.insert_subset ha (Finset.singleton_subset_iff.mpr hb))
    (le_of_eq (by rw [hs, Finset.card_pair hab]))).symm

/-- Four pairwise distinct elements of `Fin 4` exhaust it. -/
lemma eq_univ_of_four_distinct {i₀ i₁ i₂ i₃ : Fin 4}
    (h01 : i₀ ≠ i₁) (h02 : i₀ ≠ i₂) (h03 : i₀ ≠ i₃)
    (h12 : i₁ ≠ i₂) (h13 : i₁ ≠ i₃) (h23 : i₂ ≠ i₃) :
    ({i₀, i₁, i₂, i₃} : Finset (Fin 4)) = Finset.univ := by
  apply Finset.eq_univ_of_card
  rw [Fintype.card_fin]
  rw [Finset.card_insert_of_notMem (by simp [h01, h02, h03]),
      Finset.card_insert_of_notMem (by simp [h12, h13]),
      Finset.card_insert_of_notMem (by simp [h23]),
      Finset.card_singleton]

/-- Counting lemma: if each of the four detectors carries at most 2 labels (H1),
and every label is carried by at least two distinct detectors (H2), then the
family `M` is a 2-regular multigraph on the labels and is exactly one of the two
shapes: two doubled edges, or a 4-cycle. -/
theorem cover_structure (M : Fin 4 → Finset (Fin 4))
    (H1 : ∀ i, (M i).card ≤ 2)
    (H2 : ∀ μ : Fin 4, 2 ≤ (Finset.univ.filter (fun i => μ ∈ M i)).card) :
    DoubledEdges M ∨ FourCycle M := by
  -- double counting: ∑_i |M i| = ∑_μ deg μ
  have hswap : (∑ i : Fin 4, (M i).card)
      = ∑ μ : Fin 4, (Finset.univ.filter (fun i => μ ∈ M i)).card := by
    calc ∑ i : Fin 4, (M i).card
        = ∑ i : Fin 4, (Finset.univ.filter (fun μ => μ ∈ M i)).card := by
          simp [Finset.filter_univ_mem]
      _ = ∑ i : Fin 4, ∑ μ : Fin 4, if μ ∈ M i then 1 else 0 := by
          simp only [Finset.card_filter]
      _ = ∑ μ : Fin 4, ∑ i : Fin 4, if μ ∈ M i then 1 else 0 := Finset.sum_comm
      _ = ∑ μ : Fin 4, (Finset.univ.filter (fun i => μ ∈ M i)).card := by
          simp only [Finset.card_filter]
  -- every detector carries exactly 2 labels
  have hcard : ∀ i, (M i).card = 2 := by
    intro i
    by_contra hne
    have hlt : (M i).card < 2 := lt_of_le_of_ne (H1 i) hne
    have hA : (∑ j : Fin 4, (M j).card) < ∑ _j : Fin 4, 2 :=
      Finset.sum_lt_sum (fun j _ => H1 j) ⟨i, Finset.mem_univ i, hlt⟩
    have hB : (∑ _μ : Fin 4, 2)
        ≤ ∑ μ : Fin 4, (Finset.univ.filter (fun i => μ ∈ M i)).card :=
      Finset.sum_le_sum (fun μ _ => H2 μ)
    have hconst : (∑ _j : Fin 4, 2) = 8 := by simp
    omega
  -- every label lies in exactly 2 detectors
  have hdeg : ∀ μ : Fin 4, (Finset.univ.filter (fun i => μ ∈ M i)).card = 2 := by
    intro μ
    by_contra hne
    have hgt : 2 < (Finset.univ.filter (fun i => μ ∈ M i)).card :=
      lt_of_le_of_ne (H2 μ) (Ne.symm hne)
    have hB : (∑ _ν : Fin 4, 2)
        < ∑ ν : Fin 4, (Finset.univ.filter (fun i => ν ∈ M i)).card :=
      Finset.sum_lt_sum (fun ν _ => H2 ν) ⟨μ, Finset.mem_univ μ, hgt⟩
    have hA : (∑ i : Fin 4, (M i).card) ≤ ∑ _i : Fin 4, 2 :=
      Finset.sum_le_sum (fun i _ => H1 i)
    have hconst : (∑ _i : Fin 4, 2) = 8 := by simp
    omega
  -- for a label in a given detector, there is exactly one other detector carrying it
  have deg_other : ∀ (μ i0 : Fin 4), μ ∈ M i0 →
      ∃ j, j ≠ i0 ∧ μ ∈ M j ∧ ∀ i, μ ∈ M i → i = i0 ∨ i = j := by
    intro μ i0 h0
    have hi0F : i0 ∈ Finset.univ.filter (fun i => μ ∈ M i) := by simp [h0]
    obtain ⟨j, hji, hF⟩ := exists_pair_eq (hdeg μ) hi0F
    refine ⟨j, hji, ?_, ?_⟩
    · have hjF : j ∈ Finset.univ.filter (fun i => μ ∈ M i) := by rw [hF]; simp
      simpa using hjF
    · intro i hi
      have hiF : i ∈ ({i0, j} : Finset (Fin 4)) := by
        rw [← hF]; simp [hi]
      simpa using hiF
  by_cases hdup : ∃ j, j ≠ 0 ∧ M j = M 0
  · -- Case (a): some other detector duplicates M 0
    obtain ⟨j, hj0, hMj0⟩ := hdup
    left
    have hc2 : (({0, j} : Finset (Fin 4))ᶜ).card = 2 := by
      rw [Finset.card_compl, Fintype.card_fin, Finset.card_pair (Ne.symm hj0)]
    obtain ⟨k, l, hkl, hklc⟩ := Finset.card_eq_two.mp hc2
    have hk : k ∉ ({0, j} : Finset (Fin 4)) := by
      rw [← Finset.mem_compl, hklc]; simp
    have hl : l ∉ ({0, j} : Finset (Fin 4)) := by
      rw [← Finset.mem_compl, hklc]; simp
    simp only [Finset.mem_insert, Finset.mem_singleton, not_or] at hk hl
    -- any detector other than 0, j carries the complementary label pair
    have key : ∀ m : Fin 4, m ≠ 0 → m ≠ j → M m = (M 0)ᶜ := by
      intro m hm0 hmj
      apply Finset.eq_of_subset_of_card_le
      · intro μ hμ
        rw [Finset.mem_compl]
        intro hμ0
        have hμj : μ ∈ M j := by rw [hMj0]; exact hμ0
        have hFsub : ({0, j} : Finset (Fin 4))
            ⊆ Finset.univ.filter (fun i => μ ∈ M i) := by
          intro i hi
          simp only [Finset.mem_insert, Finset.mem_singleton] at hi
          rcases hi with rfl | rfl
          · simp [hμ0]
          · simp [hμj]
        have hFeq : ({0, j} : Finset (Fin 4))
            = Finset.univ.filter (fun i => μ ∈ M i) :=
          Finset.eq_of_subset_of_card_le hFsub
            (le_of_eq (by rw [hdeg μ, Finset.card_pair (Ne.symm hj0)]))
        have hmmem : m ∈ ({0, j} : Finset (Fin 4)) := by
          rw [hFeq]; simp [hμ]
        simp only [Finset.mem_insert, Finset.mem_singleton] at hmmem
        rcases hmmem with h' | h'
        · exact hm0 h'
        · exact hmj h'
      · rw [Finset.card_compl, Fintype.card_fin, hcard 0, hcard m]
    have hMk := key k hk.1 hk.2
    have hMl := key l hl.1 hl.2
    refine ⟨0, j, k, l,
      eq_univ_of_four_distinct (Ne.symm hj0) (Ne.symm hk.1) (Ne.symm hl.1)
        (Ne.symm hk.2) (Ne.symm hl.2) hkl,
      hMj0.symm, hMk.trans hMl.symm, hcard 0, hcard k, ?_, ?_⟩
    · rw [hMk]; exact disjoint_compl_right
    · rw [hMk]; simp
  · -- Case (b): no duplicate of M 0, forces a 4-cycle
    push_neg at hdup
    obtain ⟨a, b, hab, hM0⟩ := Finset.card_eq_two.mp (hcard 0)
    have ha0 : a ∈ M 0 := by rw [hM0]; simp
    have hb0 : b ∈ M 0 := by rw [hM0]; simp
    obtain ⟨j, hj0, haj, haOnly⟩ := deg_other a 0 ha0
    obtain ⟨k, hk0, hbk, hbOnly⟩ := deg_other b 0 hb0
    have hjk : j ≠ k := by
      intro h
      apply hdup j hj0
      have hbj' : b ∈ M j := by rw [h]; exact hbk
      exact (eq_pair_of_mem (hcard j) hab haj hbj').trans hM0.symm
    -- the fourth detector l
    have hl_ex : ∃ l : Fin 4, l ≠ 0 ∧ l ≠ j ∧ l ≠ k := by
      have h3 : ({0, j, k} : Finset (Fin 4)).card ≤ 3 := by
        apply le_trans (Finset.card_insert_le _ _)
        have h2 : ({j, k} : Finset (Fin 4)).card ≤ 2 := by
          apply le_trans (Finset.card_insert_le _ _)
          simp
        omega
      have h4 : (({0, j, k} : Finset (Fin 4))ᶜ).Nonempty := by
        rw [← Finset.card_pos, Finset.card_compl, Fintype.card_fin]
        omega
      obtain ⟨l, hlmem⟩ := h4
      simp only [Finset.mem_compl, Finset.mem_insert, Finset.mem_singleton,
        not_or] at hlmem
      exact ⟨l, hlmem.1, hlmem.2.1, hlmem.2.2⟩
    obtain ⟨l, hl0, hlj, hlk⟩ := hl_ex
    have huniv : ({0, j, k, l} : Finset (Fin 4)) = Finset.univ :=
      eq_univ_of_four_distinct (Ne.symm hj0) (Ne.symm hk0) (Ne.symm hl0)
        hjk (Ne.symm hlj) (Ne.symm hlk)
    have hcases : ∀ i : Fin 4, i = 0 ∨ i = j ∨ i = k ∨ i = l := by
      intro i
      have hmem : i ∈ ({0, j, k, l} : Finset (Fin 4)) := by
        rw [huniv]; exact Finset.mem_univ i
      simpa using hmem
    -- a and b are absent from the remaining detectors
    have hbj : b ∉ M j := by
      intro h
      rcases hbOnly j h with h' | h'
      · exact hj0 h'
      · exact hjk h'
    have hak : a ∉ M k := by
      intro h
      rcases haOnly k h with h' | h'
      · exact hk0 h'
      · exact hjk h'.symm
    have hal : a ∉ M l := by
      intro h
      rcases haOnly l h with h' | h'
      · exact hl0 h'
      · exact hlj h'
    have hbl : b ∉ M l := by
      intro h
      rcases hbOnly l h with h' | h'
      · exact hl0 h'
      · exact hlk h'
    -- M l is the complementary label pair
    have hMl : M l = (M 0)ᶜ := by
      apply Finset.eq_of_subset_of_card_le
      · intro μ hμ
        rw [Finset.mem_compl, hM0]
        intro hc
        simp only [Finset.mem_insert, Finset.mem_singleton] at hc
        rcases hc with rfl | rfl
        · exact hal hμ
        · exact hbl hμ
      · rw [Finset.card_compl, Fintype.card_fin, hcard 0, hcard l]
    -- second labels of M j and M k
    obtain ⟨x, hxa, hMj⟩ := exists_pair_eq (hcard j) haj
    obtain ⟨y, hyb, hMk⟩ := exists_pair_eq (hcard k) hbk
    have hxb : x ≠ b := by
      intro h
      apply hbj
      rw [hMj, ← h]
      simp
    have hya : y ≠ a := by
      intro h
      apply hak
      rw [hMk, ← h]
      simp
    have hx0 : x ∉ M 0 := by rw [hM0]; simp [hxa, hxb]
    have hy0 : y ∉ M 0 := by rw [hM0]; simp [hya, hyb]
    have hcc : ((M 0)ᶜ).card = 2 := by
      rw [Finset.card_compl, Fintype.card_fin, hcard 0]
    -- x ≠ y, else the fourth label has degree ≤ 1
    have hxy : x ≠ y := by
      intro hxyeq
      have hMk' : M k = {b, x} := by rw [hMk, ← hxyeq]
      obtain ⟨z, hzx, hzc⟩ := exists_pair_eq hcc (Finset.mem_compl.mpr hx0)
      have hz0 : z ∉ M 0 := Finset.mem_compl.mp (by rw [hzc]; simp)
      have hza : z ≠ a := fun h => hz0 (by rw [h]; exact ha0)
      have hzb : z ≠ b := fun h => hz0 (by rw [h]; exact hb0)
      have hsub : (Finset.univ.filter (fun i => z ∈ M i)) ⊆ {l} := by
        intro i hi
        simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hi
        rcases hcases i with rfl | rfl | rfl | rfl
        · exact absurd hi hz0
        · rw [hMj] at hi; simp [hza, hzx] at hi
        · rw [hMk'] at hi; simp [hzb, hzx] at hi
        · simp
      have hle : (Finset.univ.filter (fun i => z ∈ M i)).card ≤ 1 := by
        simpa using Finset.card_le_card hsub
      have hdz := hdeg z
      omega
    right
    have hyc : y ∈ (M 0)ᶜ := Finset.mem_compl.mpr hy0
    have hxc : x ∈ (M 0)ᶜ := Finset.mem_compl.mpr hx0
    exact ⟨0, k, l, j,
      eq_univ_of_four_distinct (Ne.symm hk0) (Ne.symm hl0) (Ne.symm hj0)
        (Ne.symm hlk) (Ne.symm hjk) hlj,
      a, b, y, x,
      eq_univ_of_four_distinct hab (Ne.symm hya) (Ne.symm hxa)
        (Ne.symm hyb) (Ne.symm hxb) (Ne.symm hxy),
      hM0, hMk, hMl.trans (eq_pair_of_mem hcc (Ne.symm hxy) hyc hxc),
      hMj.trans (Finset.pair_comm a x)⟩

end Empiricist
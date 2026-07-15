import Mathlib.Combinatorics.SimpleGraph.Acyclic
import Mathlib.Combinatorics.SimpleGraph.Finite

/-!
# The double-star caterpillar is a tree

`doubleStar m n` on `Fin (m + n)` has two centers: vertex `0` (adjacent to `1, …, m-1`
and to vertex `m`) and vertex `m` (adjacent to `m+1, …, m+n-1`).  For `1 ≤ m`, `1 ≤ n`
it is a tree: it is connected and has exactly `m + n - 1` edges.
-/

namespace Empiricist

open SimpleGraph

/-- The double-star caterpillar on `Fin (m + n)`: vertex `0` is adjacent to the leaves
`1, …, m-1` and to the second center `m`; vertex `m` is adjacent to the leaves
`m+1, …, m+n-1`.  Unordered: `Adj i j` iff `i ≠ j` and one of them is `0` with the other
in `{1, …, m}` (the case `= m` being the center–center edge), or one of them is `m` with
the other in `{m+1, …, m+n-1}`. -/
def doubleStar (m n : ℕ) : SimpleGraph (Fin (m + n)) where
  Adj i j := i ≠ j ∧
    ((i.val = 0 ∧ j.val ≤ m) ∨ (j.val = 0 ∧ i.val ≤ m) ∨
     (i.val = m ∧ m ≤ j.val) ∨ (j.val = m ∧ m ≤ i.val))
  symm := by
    constructor
    rintro i j ⟨hne, h | h | h | h⟩
    · exact ⟨hne.symm, Or.inr (Or.inl h)⟩
    · exact ⟨hne.symm, Or.inl h⟩
    · exact ⟨hne.symm, Or.inr (Or.inr (Or.inr h))⟩
    · exact ⟨hne.symm, Or.inr (Or.inr (Or.inl h))⟩
  loopless := by
    constructor
    intro i h
    exact h.1 rfl

lemma doubleStar_adj {m n : ℕ} {i j : Fin (m + n)} :
    (doubleStar m n).Adj i j ↔ i ≠ j ∧
      ((i.val = 0 ∧ j.val ≤ m) ∨ (j.val = 0 ∧ i.val ≤ m) ∨
       (i.val = m ∧ m ≤ j.val) ∨ (j.val = m ∧ m ≤ i.val)) := Iff.rfl

instance (m n : ℕ) : DecidableRel (doubleStar m n).Adj := fun _ _ =>
  decidable_of_iff _ doubleStar_adj.symm

/-- Equality of unordered pairs of `Fin`s, read off at the value level. -/
lemma sym2_val_eq {k : ℕ} {x y z w : Fin k} (h : s(x, y) = s(z, w)) :
    (x.val = z.val ∧ y.val = w.val) ∨ (x.val = w.val ∧ y.val = z.val) := by
  rw [Sym2.eq_iff] at h
  rcases h with ⟨h1, h2⟩ | ⟨h1, h2⟩
  · exact Or.inl ⟨congrArg Fin.val h1, congrArg Fin.val h2⟩
  · exact Or.inr ⟨congrArg Fin.val h1, congrArg Fin.val h2⟩

/-- The double star is a tree as soon as both centers exist. -/
theorem doubleStar_isTree (m n : ℕ) (hm : 1 ≤ m) (hn : 1 ≤ n) :
    (doubleStar m n).IsTree := by
  have hmn : 0 < m + n := by omega
  have hm' : m < m + n := by omega
  -- value-level facts about the two centers, so that `omega` can use them
  have hval0 : ((⟨0, hmn⟩ : Fin (m + n)) : ℕ) = 0 := rfl
  have hvalm : ((⟨m, hm'⟩ : Fin (m + n)) : ℕ) = m := rfl
  -- the two centers are adjacent
  have hadj0m : (doubleStar m n).Adj ⟨0, hmn⟩ ⟨m, hm'⟩ :=
    doubleStar_adj.mpr ⟨Fin.ne_of_val_ne (show (0 : ℕ) ≠ m by omega),
      Or.inl ⟨rfl, le_refl m⟩⟩
  -- every vertex reaches vertex `0` through its center
  have reach : ∀ w : Fin (m + n), (doubleStar m n).Reachable w ⟨0, hmn⟩ := by
    intro w
    rcases eq_or_ne w ⟨0, hmn⟩ with h | h
    · subst h
      exact SimpleGraph.Reachable.refl _
    · by_cases hle : w.val ≤ m
      · exact (doubleStar_adj.mpr ⟨h, Or.inr (Or.inl ⟨rfl, hle⟩)⟩).reachable
      · have h1 : (doubleStar m n).Adj w ⟨m, hm'⟩ :=
          doubleStar_adj.mpr ⟨Fin.ne_of_val_ne (show w.val ≠ m by omega),
            Or.inr (Or.inr (Or.inr ⟨rfl, by omega⟩))⟩
        exact h1.reachable.trans hadj0m.symm.reachable
  have hconn : (doubleStar m n).Connected := by
    rw [SimpleGraph.connected_iff]
    exact ⟨fun u v => (reach u).trans (reach v).symm, ⟨⟨0, hmn⟩⟩⟩
  -- the edges are the image of the nonzero vertices, each joined to its center
  have himg : (doubleStar m n).edgeFinset =
      (Finset.univ.erase (⟨0, hmn⟩ : Fin (m + n))).image
        (fun v : Fin (m + n) =>
          if v.val ≤ m then s((⟨0, hmn⟩ : Fin (m + n)), v)
          else s((⟨m, hm'⟩ : Fin (m + n)), v)) := by
    ext e
    induction e using Sym2.ind with
    | _ i j =>
      simp only [SimpleGraph.mem_edgeFinset, SimpleGraph.mem_edgeSet, doubleStar_adj,
        Finset.mem_image, Finset.mem_erase, Finset.mem_univ, and_true]
      constructor
      · rintro ⟨hne, h⟩
        have hne' : i.val ≠ j.val := fun h' => hne (Fin.ext h')
        rcases h with ⟨hi, hj⟩ | ⟨hj, hi⟩ | ⟨hi, hj⟩ | ⟨hj, hi⟩
        · refine ⟨j, Fin.ne_of_val_ne (show j.val ≠ 0 by omega), ?_⟩
          rw [if_pos hj, Sym2.eq_iff]
          exact Or.inl ⟨Fin.ext (show (0 : ℕ) = i.val by omega), rfl⟩
        · refine ⟨i, Fin.ne_of_val_ne (show i.val ≠ 0 by omega), ?_⟩
          rw [if_pos hi, Sym2.eq_iff]
          exact Or.inr ⟨Fin.ext (show (0 : ℕ) = j.val by omega), rfl⟩
        · refine ⟨j, Fin.ne_of_val_ne (show j.val ≠ 0 by omega), ?_⟩
          rw [if_neg (show ¬ j.val ≤ m by omega), Sym2.eq_iff]
          exact Or.inl ⟨Fin.ext (show m = i.val by omega), rfl⟩
        · refine ⟨i, Fin.ne_of_val_ne (show i.val ≠ 0 by omega), ?_⟩
          rw [if_neg (show ¬ i.val ≤ m by omega), Sym2.eq_iff]
          exact Or.inr ⟨Fin.ext (show m = j.val by omega), rfl⟩
      · rintro ⟨v, hv, hfv⟩
        have hv0 : v.val ≠ 0 := fun hh => hv (Fin.ext hh)
        by_cases hle : v.val ≤ m
        · rw [if_pos hle] at hfv
          rcases sym2_val_eq hfv with ⟨h1, h2⟩ | ⟨h1, h2⟩
          · exact ⟨Fin.ne_of_val_ne (by omega), Or.inl ⟨by omega, by omega⟩⟩
          · exact ⟨Fin.ne_of_val_ne (by omega), Or.inr (Or.inl ⟨by omega, by omega⟩)⟩
        · rw [if_neg hle] at hfv
          rcases sym2_val_eq hfv with ⟨h1, h2⟩ | ⟨h1, h2⟩
          · exact ⟨Fin.ne_of_val_ne (by omega),
              Or.inr (Or.inr (Or.inl ⟨by omega, by omega⟩))⟩
          · exact ⟨Fin.ne_of_val_ne (by omega),
              Or.inr (Or.inr (Or.inr ⟨by omega, by omega⟩))⟩
  -- that map is injective on the nonzero vertices
  have hinj : Set.InjOn
      (fun v : Fin (m + n) =>
        if v.val ≤ m then s((⟨0, hmn⟩ : Fin (m + n)), v)
        else s((⟨m, hm'⟩ : Fin (m + n)), v))
      ↑(Finset.univ.erase (⟨0, hmn⟩ : Fin (m + n))) := by
    intro a ha b hb hab
    rw [Finset.mem_coe, Finset.mem_erase] at ha hb
    have ha0 : a.val ≠ 0 := fun hh => ha.1 (Fin.ext hh)
    have hb0 : b.val ≠ 0 := fun hh => hb.1 (Fin.ext hh)
    apply Fin.ext
    by_cases hA : a.val ≤ m <;> by_cases hB : b.val ≤ m
    · simp only [if_pos hA, if_pos hB] at hab
      rcases sym2_val_eq hab with ⟨-, h⟩ | ⟨h1, h2⟩ <;> omega
    · simp only [if_pos hA, if_neg hB] at hab
      rcases sym2_val_eq hab with ⟨h1, h2⟩ | ⟨h1, h2⟩ <;> omega
    · simp only [if_neg hA, if_pos hB] at hab
      rcases sym2_val_eq hab with ⟨h1, h2⟩ | ⟨h1, h2⟩ <;> omega
    · simp only [if_neg hA, if_neg hB] at hab
      rcases sym2_val_eq hab with ⟨-, h⟩ | ⟨h1, h2⟩ <;> omega
  -- hence exactly `m + n - 1` edges
  have hedge : (doubleStar m n).edgeFinset.card = m + n - 1 := by
    rw [himg, Finset.card_image_of_injOn hinj,
      Finset.card_erase_of_mem (Finset.mem_univ _), Finset.card_univ, Fintype.card_fin]
  have hedge' : Nat.card ((doubleStar m n).edgeSet) = m + n - 1 := by
    rw [Nat.card_eq_fintype_card, ← Set.toFinset_card]
    exact hedge
  rw [SimpleGraph.isTree_iff_connected_and_card]
  refine ⟨hconn, ?_⟩
  rw [hedge', Nat.card_eq_fintype_card, Fintype.card_fin]
  omega

end Empiricist

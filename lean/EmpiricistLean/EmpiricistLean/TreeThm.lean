import Mathlib.Combinatorics.SimpleGraph.Acyclic
import Mathlib.Tactic
import EmpiricistLean.Foundation
import EmpiricistLean.LocalComp
import EmpiricistLean.FusionRule

open SimpleGraph

namespace Empiricist

/-- Every tree on `n ≥ 3` vertices is producible using `n - 3` fusions.
Strong induction on `n` with the vertex type quantified inside the motive. -/
theorem producibleBy_tree :
    ∀ (n : ℕ) {V : Type} [inst : Fintype V] (T : SimpleGraph V) [instDec : DecidableRel T.Adj],
      Fintype.card V = n → T.IsTree → 3 ≤ n → ProducibleBy (n - 3) T := by
  intro n
  induction n using Nat.strong_induction_on with
  | _ n ih =>
    intro V inst T instDec hcard hT hn
    classical
    have hconnT : T.Connected := hT.isConnected
    have hacycT : T.IsAcyclic := hT.IsAcyclic
    rcases Nat.lt_or_ge n 4 with hlt | hge
    · -- Base case: n = 3.  Classify the unique 3-vertex tree as a path v — w — u.
      have hn3 : n = 3 := by omega
      subst hn3
      haveI hnt : Nontrivial V := by
        rw [← Fintype.one_lt_card_iff_nontrivial]; omega
      obtain ⟨v, hv⟩ : ∃ v : V, T.degree v = 1 := by
        first
          | exact hT.exists_vert_degree_one_of_nontrivial hnt
          | exact hT.exists_vert_degree_one_of_nontrivial
      obtain ⟨w, hvw, hwuniq⟩ : ∃! w : V, T.Adj v w := by
        first
          | exact degree_eq_one_iff_existsUnique_adj.mp hv
          | exact (degree_eq_one_iff_existsUnique_adj v).mp hv
          | exact (degree_eq_one_iff_existsUnique_adj T v).mp hv
      have hne_vw : v ≠ w := hvw.ne
      obtain ⟨u, huv, huw⟩ : ∃ u : V, u ≠ v ∧ u ≠ w := by
        by_contra hcon
        push_neg at hcon
        have hsub : (Finset.univ : Finset V) ⊆ ({v, w} : Finset V) := by
          intro x _
          by_cases hx : x = v
          · simp [hx]
          · simp [hcon x hx]
        have hle := Finset.card_le_card hsub
        have h2 : ({v, w} : Finset V).card ≤ 2 :=
          le_trans (Finset.card_insert_le _ _) (by simp)
        rw [Finset.card_univ, hcard] at hle
        omega
      have hall : ∀ x : V, x = v ∨ x = w ∨ x = u := by
        have hcard3 : ({v, w, u} : Finset V).card = 3 :=
          Finset.card_eq_three.mpr ⟨v, w, u, hne_vw, Ne.symm huv, Ne.symm huw, rfl⟩
        have huniv : ({v, w, u} : Finset V) = Finset.univ :=
          Finset.eq_univ_of_card _ (by rw [hcard3, hcard])
        intro x
        have hx : x ∈ ({v, w, u} : Finset V) := huniv.symm ▸ Finset.mem_univ x
        simpa using hx
      have hnadj_vu : ¬ T.Adj v u := fun h => huw (hwuniq u h)
      have hadj_wu : T.Adj w u := by
        obtain ⟨p⟩ := hconnT.preconnected u v
        cases p with
        | nil => exact absurd rfl huv
        | @cons _ b _ h q =>
          rcases hall b with rfl | rfl | rfl
          · exact absurd h.symm hnadj_vu
          · exact h.symm
          · exact absurd rfl h.ne
      have hadj_iff : ∀ x y : V,
          T.Adj x y ↔
            ((x = v ∧ y = w) ∨ (x = w ∧ y = v) ∨ (x = w ∧ y = u) ∨ (x = u ∧ y = w)) := by
        intro x y
        constructor
        · intro hxy
          rcases hall x with rfl | rfl | rfl <;> rcases hall y with rfl | rfl | rfl
          · exact absurd rfl hxy.ne
          · exact Or.inl ⟨rfl, rfl⟩
          · exact absurd hxy hnadj_vu
          · exact Or.inr (Or.inl ⟨rfl, rfl⟩)
          · exact absurd rfl hxy.ne
          · exact Or.inr (Or.inr (Or.inl ⟨rfl, rfl⟩))
          · exact absurd hxy.symm hnadj_vu
          · exact Or.inr (Or.inr (Or.inr ⟨rfl, rfl⟩))
          · exact absurd rfl hxy.ne
        · rintro (⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩)
          · exact hvw
          · exact hvw.symm
          · exact hadj_wu
          · exact hadj_wu.symm
      -- T is the path v — w — u; transport `ProducibleBy.base` along an iso
      -- GHZ3graph = pathGraph 3, with 0 ↦ v, 1 ↦ w, 2 ↦ u.
      refine ProducibleBy.iso ProducibleBy.base ?_
      exact
        { toFun := fun i => if i = 0 then v else if i = 1 then w else u
          invFun := fun x => if x = v then 0 else if x = w then 1 else 2
          left_inv := by
            intro i
            fin_cases i <;> simp [Ne.symm hne_vw, huv, huw]
          right_inv := by
            intro x
            rcases hall x with rfl | rfl | rfl <;> simp [Ne.symm hne_vw, huv, huw]
          map_rel_iff' := by
            intro a b
            fin_cases a <;> fin_cases b <;>
              simp [GHZ3graph, pathGraph_adj, hadj_iff, hne_vw, Ne.symm hne_vw,
                huv, Ne.symm huv, huw, Ne.symm huw] }
    · -- Inductive step: n ≥ 4.  Remove a leaf, apply IH, reattach via ghz3LeafMerge.
      haveI hnt : Nontrivial V := by
        rw [← Fintype.one_lt_card_iff_nontrivial]; omega
      obtain ⟨v, hv⟩ : ∃ v : V, T.degree v = 1 := by
        first
          | exact hT.exists_vert_degree_one_of_nontrivial hnt
          | exact hT.exists_vert_degree_one_of_nontrivial
      obtain ⟨w, hvw, hwuniq⟩ : ∃! w : V, T.Adj v w := by
        first
          | exact degree_eq_one_iff_existsUnique_adj.mp hv
          | exact (degree_eq_one_iff_existsUnique_adj v).mp hv
          | exact (degree_eq_one_iff_existsUnique_adj T v).mp hv
      have hleaf_adj : ∀ x : V, T.Adj v x ↔ x = w := by
        intro x
        exact ⟨fun hx => hwuniq x hx, fun hx => hx ▸ hvw⟩
      have hleaf_adj' : ∀ x : V, T.Adj x v ↔ x = w := fun x =>
        ⟨fun h => (hleaf_adj x).mp h.symm, fun h => ((hleaf_adj x).mpr h).symm⟩
      have hwv : w ≠ v := hvw.ne'
      have hwmem : w ∈ ({v}ᶜ : Set V) := by simpa using hwv
      have hconn' : (T.induce ({v}ᶜ : Set V)).Connected := by
        first
          | exact hconnT.induce_compl_singleton_of_degree_eq_one hv
          | exact hconnT.induce_compl_singleton_of_degree_eq_one v hv
          | exact Connected.induce_compl_singleton_of_degree_eq_one hconnT hv
      have hacyc' : (T.induce ({v}ᶜ : Set V)).IsAcyclic := by
        first
          | exact hacycT.induce _
          | exact hacycT.induce
          | exact IsAcyclic.induce hacycT _
      have htree' : (T.induce ({v}ᶜ : Set V)).IsTree := ⟨hconn', hacyc'⟩
      have h2 : Fintype.card ({v} : Set V) = 1 := by
        first
          | exact Set.card_singleton v
          | simp
      have h1 : Fintype.card ({v}ᶜ : Set V) = Fintype.card V - Fintype.card ({v} : Set V) := by
        first
          | exact Fintype.card_compl_set _
          | exact Fintype.card_compl_set ({v} : Set V)
          | simp [Fintype.card_compl_set]
      have hcard' : Fintype.card ({v}ᶜ : Set V) = n - 1 := by rw [h1, h2, hcard]
      have hIH : ProducibleBy (n - 1 - 3) (T.induce ({v}ᶜ : Set V)) :=
        ih (n - 1) (by omega) (T.induce ({v}ᶜ : Set V)) hcard' htree' (by omega)
      have harith : n - 1 - 3 = n - 4 := by omega
      rw [harith] at hIH
      have hmerged : ProducibleBy ((n - 4) + 1)
          (ghz3LeafMerge (T.induce ({v}ᶜ : Set V)) ⟨w, hwmem⟩) :=
        ProducibleBy.merge _ _ hIH
      have hiso1 : ghz3LeafMerge (T.induce ({v}ᶜ : Set V)) ⟨w, hwmem⟩ ≃g
          addPendant (T.induce ({v}ᶜ : Set V)) ⟨w, hwmem⟩ :=
        ghz3LeafMerge_iso_addPendant _ _
      have hiso2 : addPendant (T.induce ({v}ᶜ : Set V)) ⟨w, hwmem⟩ ≃g T := by
        refine
          { toFun := fun x => x.elim v Subtype.val
            invFun := fun x => if h : x = v then none else some ⟨x, by simpa using h⟩
            left_inv := by
              rintro (_ | ⟨u, hu⟩)
              · simp
              · have hu' : u ≠ v := by simpa using hu
                simp [hu']
            right_inv := by
              intro x
              by_cases h : x = v
              · subst h; simp
              · simp [h]
            map_rel_iff' := ?_ }
        intro a b
        rcases a with _ | ⟨x, hx⟩ <;> rcases b with _ | ⟨y, hy⟩
        · simp [addPendant_not_adj_none_none, SimpleGraph.irrefl]
        · simp [addPendant_adj_none_some, hleaf_adj]
        · simp [addPendant_adj_some_none, hleaf_adj']
        · simp [addPendant_adj_some_some, SimpleGraph.induce_adj]
      have hstep : n - 3 = (n - 4) + 1 := by omega
      rw [hstep]
      exact ProducibleBy.iso hmerged (hiso1.trans hiso2)

/-- **F(T) = N − 3 for every tree.** The lower bound (any valid fusion schedule
uses at least `N − 3` fusions) is supplied by `fusion_cost_lower_bound`; the
matching producibility upper bound is `producibleBy_tree`. -/
theorem tree_min_fusions {V : Type} [Fintype V] (T : SimpleGraph V) [DecidableRel T.Adj]
    (hT : T.IsTree) (hcard : 3 ≤ Fintype.card V) :
    ProducibleBy (Fintype.card V - 3) T ∧
      ∀ (g f : ℕ) (c : ℕ → ℕ), Fintype.card V + 2 * f = 3 * g → c 0 = g → c f = 1 →
        (∀ i, i < f → c i ≤ c (i + 1) + 1) → Fintype.card V - 3 ≤ f := by
  refine ⟨producibleBy_tree (Fintype.card V) T rfl hT hcard, ?_⟩
  intro g f c h1 h2 h3 h4
  exact fusion_cost_lower_bound (Fintype.card V) g f c hcard h1 h2 h3 h4

end Empiricist
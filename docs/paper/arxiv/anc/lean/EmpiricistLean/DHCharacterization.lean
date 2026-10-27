import Mathlib.Combinatorics.SimpleGraph.Acyclic
import Mathlib.Data.Fintype.Option
import EmpiricistLean.Basic
import EmpiricistLean.LocalComp
import EmpiricistLean.FusionRule
import EmpiricistLean.CenterMerge
import EmpiricistLean.TrueTwin
import EmpiricistLean.ProducibleExt
import EmpiricistLean.Foundation

namespace Empiricist

inductive PendantTwinBuildable : {V : Type} → SimpleGraph V → Prop
  | core {V} (G : SimpleGraph V) :
      (Nonempty (G ≃g GHZ3graph)) ∨
      (Nonempty (G ≃g localComplement GHZ3graph (1 : Fin 3))) →
      PendantTwinBuildable G
  | pendant {V} (G : SimpleGraph V) (a : V) :
      PendantTwinBuildable G → PendantTwinBuildable (addPendant G a)
  | falseTwin {V} (G : SimpleGraph V) (a : V) :
      PendantTwinBuildable G → PendantTwinBuildable (addFalseTwin G a)
  | trueTwin {V} (G : SimpleGraph V) (a : V) :
      PendantTwinBuildable G → PendantTwinBuildable (addTrueTwin G a)
  | lc {V} (G : SimpleGraph V) (v : V) :
      PendantTwinBuildable G → PendantTwinBuildable (localComplement G v)
  | iso {V W} {G : SimpleGraph V} {H : SimpleGraph W} :
      PendantTwinBuildable G → G ≃g H → PendantTwinBuildable H

theorem PendantTwinBuildable.finite {V : Type} {G : SimpleGraph V}
    (h : PendantTwinBuildable G) : Finite V := by
  induction h with
  | @core V G hcore =>
      rcases hcore with hn | hn
      · obtain ⟨e⟩ := hn
        exact Finite.of_equiv (Fin 3) e.toEquiv.symm
      · obtain ⟨e⟩ := hn
        exact Finite.of_equiv (Fin 3) e.toEquiv.symm
  | @pendant V G a hb ih =>
      haveI : Finite V := ih
      haveI := Fintype.ofFinite V
      first | exact Finite.of_fintype (Option V) | infer_instance
  | @falseTwin V G a hb ih =>
      haveI : Finite V := ih
      haveI := Fintype.ofFinite V
      first | exact Finite.of_fintype (Option V) | infer_instance
  | @trueTwin V G a hb ih =>
      haveI : Finite V := ih
      haveI := Fintype.ofFinite V
      first | exact Finite.of_fintype (Option V) | infer_instance
  | @lc V G v hb ih =>
      exact ih
  | @iso V W G H hb e ih =>
      haveI : Finite V := ih
      exact Finite.of_equiv V e.toEquiv

theorem PendantTwinBuildable.three_le_natCard {V : Type} {G : SimpleGraph V}
    (h : PendantTwinBuildable G) : 3 ≤ Nat.card V := by
  induction h with
  | @core V G hcore =>
      rcases hcore with hn | hn
      · obtain ⟨e⟩ := hn
        have hc : Nat.card V = 3 := by
          rw [Nat.card_congr e.toEquiv, Nat.card_eq_fintype_card, Fintype.card_fin]
        omega
      · obtain ⟨e⟩ := hn
        have hc : Nat.card V = 3 := by
          rw [Nat.card_congr e.toEquiv, Nat.card_eq_fintype_card, Fintype.card_fin]
        omega
  | @pendant V G a hb ih =>
      haveI : Finite V := hb.finite
      haveI := Fintype.ofFinite V
      have hcard : Nat.card (Option V) = Nat.card V + 1 := by
        first
          | simp [Nat.card_eq_fintype_card]
          | rw [Nat.card_eq_fintype_card, Nat.card_eq_fintype_card, Fintype.card_option]
      omega
  | @falseTwin V G a hb ih =>
      haveI : Finite V := hb.finite
      haveI := Fintype.ofFinite V
      have hcard : Nat.card (Option V) = Nat.card V + 1 := by
        first
          | simp [Nat.card_eq_fintype_card]
          | rw [Nat.card_eq_fintype_card, Nat.card_eq_fintype_card, Fintype.card_option]
      omega
  | @trueTwin V G a hb ih =>
      haveI : Finite V := hb.finite
      haveI := Fintype.ofFinite V
      have hcard : Nat.card (Option V) = Nat.card V + 1 := by
        first
          | simp [Nat.card_eq_fintype_card]
          | rw [Nat.card_eq_fintype_card, Nat.card_eq_fintype_card, Fintype.card_option]
      omega
  | @lc V G v hb ih =>
      exact ih
  | @iso V W G H hb e ih =>
      have hc : Nat.card V = Nat.card W := Nat.card_congr e.toEquiv
      omega

theorem PendantTwinBuildable.three_le_card {V : Type} [Fintype V]
    {G : SimpleGraph V} (h : PendantTwinBuildable G) : 3 ≤ Fintype.card V := by
  have h3 := h.three_le_natCard
  rwa [Nat.card_eq_fintype_card] at h3

theorem dh_forward_nat {V : Type} {G : SimpleGraph V}
    (h : PendantTwinBuildable G) : ProducibleByExt (Nat.card V - 3) G := by
  classical
  induction h with
  | @core V G hcore =>
      rcases hcore with hn | hn
      · obtain ⟨e⟩ := hn
        have hc : Nat.card V = 3 := by
          rw [Nat.card_congr e.toEquiv, Nat.card_eq_fintype_card, Fintype.card_fin]
        have h0 : Nat.card V - 3 = 0 := by omega
        rw [h0]
        exact ProducibleByExt.base.iso e.symm
      · obtain ⟨e⟩ := hn
        have hc : Nat.card V = 3 := by
          rw [Nat.card_congr e.toEquiv, Nat.card_eq_fintype_card, Fintype.card_fin]
        have h0 : Nat.card V - 3 = 0 := by omega
        rw [h0]
        exact (ProducibleByExt.lc GHZ3graph (1 : Fin 3) ProducibleByExt.base).iso e.symm
  | @pendant V G a hb ih =>
      haveI : Finite V := hb.finite
      haveI := Fintype.ofFinite V
      have hk : 3 ≤ Nat.card V := hb.three_le_natCard
      have hcard : Nat.card (Option V) = Nat.card V + 1 := by
        first
          | simp [Nat.card_eq_fintype_card]
          | rw [Nat.card_eq_fintype_card, Nat.card_eq_fintype_card, Fintype.card_option]
      have hexp : Nat.card (Option V) - 3 = Nat.card V - 3 + 1 := by omega
      rw [hexp]
      first
        | exact (ProducibleByExt.leafMerge G a ih).iso (ghz3LeafMerge_iso_addPendant G a)
        | exact (ProducibleByExt.leafMerge G a ih).iso (ghz3LeafMerge_iso_addPendant G a).symm
  | @falseTwin V G a hb ih =>
      haveI : Finite V := hb.finite
      haveI := Fintype.ofFinite V
      have hk : 3 ≤ Nat.card V := hb.three_le_natCard
      have hcard : Nat.card (Option V) = Nat.card V + 1 := by
        first
          | simp [Nat.card_eq_fintype_card]
          | rw [Nat.card_eq_fintype_card, Nat.card_eq_fintype_card, Fintype.card_option]
      have hexp : Nat.card (Option V) - 3 = Nat.card V - 3 + 1 := by omega
      rw [hexp]
      first
        | exact (ProducibleByExt.centerMerge G a ih).iso (ghz3CenterMerge_iso_addFalseTwin G a)
        | exact (ProducibleByExt.centerMerge G a ih).iso (ghz3CenterMerge_iso_addFalseTwin G a).symm
  | @trueTwin V G a hb ih =>
      haveI : Finite V := hb.finite
      haveI := Fintype.ofFinite V
      have hk : 3 ≤ Nat.card V := hb.three_le_natCard
      have s1 : ProducibleByExt (Nat.card V - 3) (localComplement G a) :=
        ProducibleByExt.lc G a ih
      have s2 : ProducibleByExt (Nat.card V - 3 + 1)
          (addPendant (localComplement G a) a) := by
        first
          | exact (ProducibleByExt.leafMerge (localComplement G a) a s1).iso
              (ghz3LeafMerge_iso_addPendant (localComplement G a) a)
          | exact (ProducibleByExt.leafMerge (localComplement G a) a s1).iso
              (ghz3LeafMerge_iso_addPendant (localComplement G a) a).symm
      have s3 : ProducibleByExt (Nat.card V - 3 + 1)
          (localComplement (addPendant (localComplement G a) a) (some a)) :=
        ProducibleByExt.lc (addPendant (localComplement G a) a) (some a) s2
      rw [addPendant_localComplement_center (localComplement G a) a,
          localComplement_involutive] at s3
      have hcard : Nat.card (Option V) = Nat.card V + 1 := by
        first
          | simp [Nat.card_eq_fintype_card]
          | rw [Nat.card_eq_fintype_card, Nat.card_eq_fintype_card, Fintype.card_option]
      have hexp : Nat.card (Option V) - 3 = Nat.card V - 3 + 1 := by omega
      rw [hexp]
      exact s3
  | @lc V G v hb ih =>
      exact ProducibleByExt.lc G v ih
  | @iso V W G H hb e ih =>
      have hc : Nat.card V = Nat.card W := Nat.card_congr e.toEquiv
      rw [← hc]
      exact ih.iso e

theorem dh_forward {V : Type} [Fintype V] (G : SimpleGraph V)
    (h : PendantTwinBuildable G) : ProducibleByExt (Fintype.card V - 3) G := by
  have hd := dh_forward_nat h
  rwa [Nat.card_eq_fintype_card] at hd

theorem dh_reverse {V : Type} {m : ℕ} (G : SimpleGraph V)
    (h : ProducibleByExt m G) : PendantTwinBuildable G := by
  classical
  induction h with
  | base =>
      refine PendantTwinBuildable.core GHZ3graph (Or.inl ⟨?_⟩)
      first
        | exact SimpleGraph.Iso.refl GHZ3graph
        | exact SimpleGraph.Iso.refl
        | exact SimpleGraph.Iso.refl _
        | rfl
  | leafMerge G' a _ ih =>
      first
        | exact (PendantTwinBuildable.pendant G' a ih).iso
            (ghz3LeafMerge_iso_addPendant G' a).symm
        | exact (PendantTwinBuildable.pendant G' a ih).iso
            (ghz3LeafMerge_iso_addPendant G' a)
  | centerMerge G' a _ ih =>
      first
        | exact (PendantTwinBuildable.falseTwin G' a ih).iso
            (ghz3CenterMerge_iso_addFalseTwin G' a).symm
        | exact (PendantTwinBuildable.falseTwin G' a ih).iso
            (ghz3CenterMerge_iso_addFalseTwin G' a)
  | lc G' v _ ih =>
      exact PendantTwinBuildable.lc G' v ih
  | iso _ e ih =>
      exact PendantTwinBuildable.iso ih e

theorem dh_characterization {V : Type} [Fintype V] (G : SimpleGraph V) :
    ProducibleByExt (Fintype.card V - 3) G ↔ PendantTwinBuildable G :=
  ⟨fun h => dh_reverse G h, fun h => dh_forward G h⟩

theorem dh_min_fusions {V : Type} [Fintype V] (G : SimpleGraph V)
    (h : PendantTwinBuildable G) :
    ProducibleByExt (Fintype.card V - 3) G ∧
      ∀ (g f : ℕ) (c : ℕ → ℕ), Fintype.card V + 2 * f = 3 * g → c 0 = g → c f = 1 →
        (∀ i, i < f → c i ≤ c (i + 1) + 1) → Fintype.card V - 3 ≤ f :=
  ⟨dh_forward G h,
   fun g f c hq h0 hf hstep =>
     fusion_cost_lower_bound (Fintype.card V) g f c (h.three_le_card) hq h0 hf hstep⟩

end Empiricist
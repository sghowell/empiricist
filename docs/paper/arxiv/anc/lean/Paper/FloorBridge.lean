import Mathlib.Combinatorics.SimpleGraph.Acyclic
import Mathlib.Data.Fintype.Option
import EmpiricistLean.Basic
import EmpiricistLean.LocalComp
import EmpiricistLean.FusionRule
import EmpiricistLean.CenterMerge
import EmpiricistLean.ProducibleExt
import EmpiricistLean.DHCharacterization

namespace Empiricist

/-- Schedule model extending the production model with an over-approximated
intra-blob fusion step: `intra` destroys two qubits and may produce an
arbitrary graph on the remaining vertices (no rewrite rule assumed).
Over-approximating only strengthens the floor theorem below. -/
inductive BlobSchedule : Nat → {V : Type} → SimpleGraph V → Prop
  | base : BlobSchedule 0 GHZ3graph
  | leafMerge {f : Nat} {V : Type} (G : SimpleGraph V) (a : V) :
      BlobSchedule f G → BlobSchedule (f + 1) (ghz3LeafMerge G a)
  | centerMerge {f : Nat} {V : Type} (G : SimpleGraph V) (a : V) :
      BlobSchedule f G → BlobSchedule (f + 1) (ghz3CenterMerge G a)
  | lc {f : Nat} {V : Type} (G : SimpleGraph V) (v : V) :
      BlobSchedule f G → BlobSchedule f (localComplement G v)
  | iso {f : Nat} {V W : Type} {G : SimpleGraph V} {H : SimpleGraph W} :
      BlobSchedule f G → G ≃g H → BlobSchedule f H
  | intra {f : Nat} {V W : Type} (G : SimpleGraph V) (H : SimpleGraph W) :
      BlobSchedule f G → Nat.card W + 2 = Nat.card V → BlobSchedule (f + 1) H

/-- Cardinality of the merge carrier in the finite case: one vertex removed,
two added, so the count grows by exactly one. -/
private lemma natCard_merge_carrier {V : Type} [Finite V] (a : V) :
    Nat.card ({v : V // v ≠ a} ⊕ Bool) = Nat.card V + 1 := by
  classical
  haveI := Fintype.ofFinite V
  have hpos : 0 < Fintype.card V := Fintype.card_pos_iff.mpr ⟨a⟩
  simp only [Nat.card_eq_fintype_card, Fintype.card_sum, Fintype.card_bool, ne_eq,
    Fintype.card_subtype_compl, Fintype.card_subtype_eq]
  omega

/-- Cardinality of the merge carrier in the infinite case: `Nat.card` is zero. -/
private lemma natCard_merge_carrier_infinite {V : Type} [Infinite V] (a : V) :
    Nat.card ({v : V // v ≠ a} ⊕ Bool) = 0 := by
  have h1 : ({a} : Set V).Finite := Set.finite_singleton a
  have h2 : (({a} : Set V)ᶜ).Infinite := h1.infinite_compl
  haveI h3 : Infinite (({a} : Set V)ᶜ : Set V) := h2.to_subtype
  haveI h4 : Infinite {v : V // v ≠ a} :=
    Infinite.of_injective
      (fun x : (({a} : Set V)ᶜ : Set V) =>
        (⟨x.1, Set.mem_compl_singleton_iff.mp x.2⟩ : {v : V // v ≠ a}))
      (fun x y hxy => Subtype.ext (congrArg Subtype.val hxy))
  haveI : Infinite ({v : V // v ≠ a} ⊕ Bool) :=
    Infinite.of_injective Sum.inl Sum.inl_injective
  exact Nat.card_eq_zero_of_infinite

/-- Counting bound: any graph reachable with `f` fusions has at most `f + 3` vertices. -/
theorem BlobSchedule.natCard_le {V : Type} {f : ℕ} {G : SimpleGraph V}
    (h : BlobSchedule f G) : Nat.card V ≤ f + 3 := by
  induction h with
  | base =>
    have h3 : Nat.card (Fin 3) = 3 := by simp [Nat.card_eq_fintype_card]
    omega
  | @leafMerge f V G a _hprev ih =>
    cases finite_or_infinite V with
    | inl hfin =>
      haveI := hfin
      have hc := natCard_merge_carrier (V := V) a
      omega
    | inr hinf =>
      haveI := hinf
      have hc := natCard_merge_carrier_infinite (V := V) a
      omega
  | @centerMerge f V G a _hprev ih =>
    cases finite_or_infinite V with
    | inl hfin =>
      haveI := hfin
      have hc := natCard_merge_carrier (V := V) a
      omega
    | inr hinf =>
      haveI := hinf
      have hc := natCard_merge_carrier_infinite (V := V) a
      omega
  | @lc f V G v _hprev ih => exact ih
  | @iso f V W G H _hprev e ih =>
    have hVW : Nat.card V = Nat.card W := Nat.card_congr e.toEquiv
    omega
  | @intra f V W G H _hprev hc ih => omega

/-- Every extended-production derivation is (trivially) a blob schedule. -/
theorem ProducibleByExt.toBlobSchedule {V : Type} {f : ℕ} {G : SimpleGraph V}
    (h : ProducibleByExt f G) : BlobSchedule f G := by
  induction h with
  | base => exact BlobSchedule.base
  | leafMerge G a _ ih => exact BlobSchedule.leafMerge G a ih
  | centerMerge G a _ ih => exact BlobSchedule.centerMerge G a ih
  | lc G v _ ih => exact BlobSchedule.lc G v ih
  | iso _ e ih => exact BlobSchedule.iso ih e

/-- Auxiliary version of the floor theorem with the cardinality hypothesis in the
conclusion (so that induction on the schedule can generalize the carrier). -/
private theorem blobSchedule_floor_aux {V : Type} {f : ℕ} {G : SimpleGraph V}
    (h : BlobSchedule f G) : Nat.card V = f + 3 → ProducibleByExt f G := by
  induction h with
  | base =>
    intro _
    exact ProducibleByExt.base
  | @leafMerge f V G a _hprev ih =>
    intro hcard
    cases finite_or_infinite V with
    | inl hfin =>
      haveI := hfin
      have hc := natCard_merge_carrier (V := V) a
      exact ProducibleByExt.leafMerge G a (ih (by omega))
    | inr hinf =>
      haveI := hinf
      have hc := natCard_merge_carrier_infinite (V := V) a
      exact absurd hcard (by omega)
  | @centerMerge f V G a _hprev ih =>
    intro hcard
    cases finite_or_infinite V with
    | inl hfin =>
      haveI := hfin
      have hc := natCard_merge_carrier (V := V) a
      exact ProducibleByExt.centerMerge G a (ih (by omega))
    | inr hinf =>
      haveI := hinf
      have hc := natCard_merge_carrier_infinite (V := V) a
      exact absurd hcard (by omega)
  | @lc f V G v _hprev ih =>
    intro hcard
    exact ProducibleByExt.lc G v (ih hcard)
  | @iso f V W G H _hprev e ih =>
    intro hcard
    have hVW : Nat.card V = Nat.card W := Nat.card_congr e.toEquiv
    exact ProducibleByExt.iso (ih (by omega)) e
  | @intra f V W G H hprev hc _ih =>
    intro hcard
    -- The sub-derivation would need `Nat.card V = f + 6`, contradicting `natCard_le`.
    have hle : Nat.card V ≤ f + 3 := hprev.natCard_le
    exact absurd hle (by omega)

/-- The floor theorem: a blob schedule reaching the fusion floor `f = N - 3`
cannot contain any intra-blob fusion, hence lies in the extended production model. -/
theorem blobSchedule_floor {V : Type} [Fintype V] {f : ℕ} {G : SimpleGraph V}
    (h : BlobSchedule f G) (hcard : Fintype.card V = f + 3) : ProducibleByExt f G :=
  blobSchedule_floor_aux h (by rw [Nat.card_eq_fintype_card]; exact hcard)

/-- COUNTING BRIDGE: floor blob schedules (with fusion count `N - 3`) produce
exactly the distance-hereditary (pendant-twin buildable) graphs. -/
theorem floor_schedule_iff_dh {V : Type} [Fintype V] (G : SimpleGraph V)
    (hN : 3 ≤ Fintype.card V) :
    BlobSchedule (Fintype.card V - 3) G ↔ PendantTwinBuildable G := by
  constructor
  · intro h
    exact dh_reverse G (blobSchedule_floor h (by omega))
  · intro h
    exact (dh_forward G h).toBlobSchedule

end Empiricist
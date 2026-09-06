import Mathlib.Combinatorics.SimpleGraph.Basic
import Mathlib.Logic.Relation
import EmpiricistLean.Basic

/-!
# The complete bipartite graph is LC-equivalent to the double star

We define local complementation of a simple graph at a vertex, the induced
one-step relation `LCStep` and its equivalence closure `LCEquiv`, the complete
bipartite graph `K_{m,n}` on `Fin (m + n)` (parts `{v | v.val < m}` and
`{v | m ≤ v.val}`), and the double-star caterpillar (centres `0` and `m`,
joined by an edge, with `0` adjacent to `1, …, m-1` and `m` adjacent to
`m+1, …, m+n-1`).

The main theorem `Empiricist.bipartite_lcEquiv_doubleStar` shows that for
`m, n ≥ 1` the complete bipartite graph is local-complementation-equivalent to
the double star, via the verified LC sequence τ₀, τ_m, τ₀ (local
complementations at vertex `0`, then vertex `m`, then vertex `0`).  The three
steps are verified one at a time through the explicit intermediate graphs
`stage1` and `stage2`.
-/

namespace Empiricist

variable {V : Type*}

/-- Unfold `Xor'` into its defining disjunction (definitional). -/
theorem xor'_iff (a b : Prop) : Xor' a b ↔ (a ∧ ¬b) ∨ (b ∧ ¬a) := Iff.rfl

/-- Local complementation of `G` at `v`: toggle the edges between distinct
neighbours of `v`. -/
def localComplement (G : SimpleGraph V) (v : V) : SimpleGraph V where
  Adj x y := Xor' (G.Adj x y) (x ≠ y ∧ G.Adj x v ∧ G.Adj y v)
  symm := by
    constructor
    intro x y h
    simp only [Xor'] at h ⊢
    rcases h with ⟨h1, h2⟩ | ⟨h1, h2⟩
    · exact Or.inl ⟨h1.symm, fun hd => h2 ⟨hd.1.symm, hd.2.2, hd.2.1⟩⟩
    · exact Or.inr ⟨⟨h1.1.symm, h1.2.2, h1.2.1⟩, fun hd => h2 hd.symm⟩
  loopless := by
    constructor
    intro x h
    simp only [Xor'] at h
    rcases h with ⟨h1, _⟩ | ⟨h1, _⟩
    · exact G.irrefl h1
    · exact h1.1 rfl

@[simp] theorem localComplement_adj (G : SimpleGraph V) (v x y : V) :
    (localComplement G v).Adj x y ↔
      Xor' (G.Adj x y) (x ≠ y ∧ G.Adj x v ∧ G.Adj y v) :=
  Iff.rfl

/-- One step of local complementation: `H` is obtained from `G` by a local
complementation at some vertex. -/
def LCStep (G H : SimpleGraph V) : Prop := ∃ v, H = localComplement G v

/-- Local-complementation equivalence: the equivalence closure of `LCStep`. -/
def LCEquiv (G H : SimpleGraph V) : Prop := Relation.EqvGen LCStep G H

theorem lcEquiv_equivalence : Equivalence (@LCEquiv V) :=
  ⟨fun G => Relation.EqvGen.refl G,
   fun h => Relation.EqvGen.symm _ _ h,
   fun h₁ h₂ => Relation.EqvGen.trans _ _ _ h₁ h₂⟩

theorem lcEquiv_localComplement (G : SimpleGraph V) (v : V) :
    LCEquiv G (localComplement G v) :=
  Relation.EqvGen.rel _ _ ⟨v, rfl⟩

theorem lcEquiv_trans {G H K : SimpleGraph V} (h₁ : LCEquiv G H) (h₂ : LCEquiv H K) :
    LCEquiv G K :=
  Relation.EqvGen.trans _ _ _ h₁ h₂

/-- The complete bipartite graph `K_{m,n}` on `Fin (m + n)`, with parts
`A = {v | v.val < m}` and `B = {v | m ≤ v.val}`: two vertices are adjacent
iff they lie on opposite sides. -/
def completeBipartite (m n : ℕ) : SimpleGraph (Fin (m + n)) where
  Adj i j := decide ((i : ℕ) < m) ≠ decide ((j : ℕ) < m)
  symm := by
    constructor
    intro i j h
    exact Ne.symm h
  loopless := by
    constructor
    intro i h
    exact h rfl

@[simp] theorem completeBipartite_adj (m n : ℕ) (i j : Fin (m + n)) :
    (completeBipartite m n).Adj i j ↔
      decide ((i : ℕ) < m) ≠ decide ((j : ℕ) < m) :=
  Iff.rfl

/-- The double-star caterpillar on `Fin (m + n)`: centres `0` and `m` are
joined by an edge, `0` is adjacent to `1, …, m-1` (and to `m`), and `m` is
adjacent to `m+1, …, m+n-1`. -/
def doubleStar (m n : ℕ) : SimpleGraph (Fin (m + n)) where
  Adj i j :=
    ((i : ℕ) = 0 ∧ 0 < (j : ℕ) ∧ (j : ℕ) ≤ m) ∨
    ((j : ℕ) = 0 ∧ 0 < (i : ℕ) ∧ (i : ℕ) ≤ m) ∨
    ((i : ℕ) = m ∧ m < (j : ℕ)) ∨
    ((j : ℕ) = m ∧ m < (i : ℕ))
  symm := by
    constructor
    rintro i j (h | h | h | h)
    · exact Or.inr (Or.inl h)
    · exact Or.inl h
    · exact Or.inr (Or.inr (Or.inr h))
    · exact Or.inr (Or.inr (Or.inl h))
  loopless := by
    constructor
    intro i h
    rcases h with ⟨h1, h2, h3⟩ | ⟨h1, h2, h3⟩ | ⟨h1, h2⟩ | ⟨h1, h2⟩ <;> omega

@[simp] theorem doubleStar_adj (m n : ℕ) (i j : Fin (m + n)) :
    (doubleStar m n).Adj i j ↔
      ((i : ℕ) = 0 ∧ 0 < (j : ℕ) ∧ (j : ℕ) ≤ m) ∨
      ((j : ℕ) = 0 ∧ 0 < (i : ℕ) ∧ (i : ℕ) ≤ m) ∨
      ((i : ℕ) = m ∧ m < (j : ℕ)) ∨
      ((j : ℕ) = m ∧ m < (i : ℕ)) :=
  Iff.rfl

/-- The graph obtained from `K_{m,n}` by local complementation at `0`:
the complete bipartite graph together with a clique on the bottom part `B`. -/
def stage1 (m n : ℕ) : SimpleGraph (Fin (m + n)) where
  Adj i j := i ≠ j ∧ (m ≤ (i : ℕ) ∨ m ≤ (j : ℕ))
  symm := by
    constructor
    intro i j h
    exact ⟨h.1.symm, h.2.symm⟩
  loopless := by
    constructor
    intro i h
    exact h.1 rfl

@[simp] theorem stage1_adj (m n : ℕ) (i j : Fin (m + n)) :
    (stage1 m n).Adj i j ↔ i ≠ j ∧ (m ≤ (i : ℕ) ∨ m ≤ (j : ℕ)) :=
  Iff.rfl

/-- The graph obtained from `stage1` by local complementation at `m`:
a clique on `A ∪ {m}` together with `m` joined to every other vertex. -/
def stage2 (m n : ℕ) : SimpleGraph (Fin (m + n)) where
  Adj i j := i ≠ j ∧ ((i : ℕ) = m ∨ (j : ℕ) = m ∨ ((i : ℕ) < m ∧ (j : ℕ) < m))
  symm := by
    constructor
    intro i j h
    obtain ⟨h1, h2 | h2 | ⟨h2, h3⟩⟩ := h
    · exact ⟨h1.symm, Or.inr (Or.inl h2)⟩
    · exact ⟨h1.symm, Or.inl h2⟩
    · exact ⟨h1.symm, Or.inr (Or.inr ⟨h3, h2⟩)⟩
  loopless := by
    constructor
    intro i h
    exact h.1 rfl

@[simp] theorem stage2_adj (m n : ℕ) (i j : Fin (m + n)) :
    (stage2 m n).Adj i j ↔
      i ≠ j ∧ ((i : ℕ) = m ∨ (j : ℕ) = m ∨ ((i : ℕ) < m ∧ (j : ℕ) < m)) :=
  Iff.rfl

set_option maxHeartbeats 800000 in
/-- First LC step: local complementation of `K_{m,n}` at vertex `0`. -/
theorem lc_completeBipartite (m n : ℕ) (hm : 1 ≤ m)
    (v0 : Fin (m + n)) (h0 : (v0 : ℕ) = 0) :
    localComplement (completeBipartite m n) v0 = stage1 m n := by
  ext x y
  simp only [localComplement_adj, xor'_iff, completeBipartite_adj, stage1_adj,
    ne_eq, decide_eq_decide, Fin.ext_iff, h0]
  omega

set_option maxHeartbeats 800000 in
/-- Second LC step: local complementation of `stage1` at vertex `m`. -/
theorem lc_stage1 (m n : ℕ) (vm : Fin (m + n)) (hmv : (vm : ℕ) = m) :
    localComplement (stage1 m n) vm = stage2 m n := by
  ext x y
  simp only [localComplement_adj, xor'_iff, stage1_adj, stage2_adj, ne_eq,
    Fin.ext_iff, hmv]
  omega

set_option maxHeartbeats 800000 in
/-- Third LC step: local complementation of `stage2` at vertex `0` yields the
double star. -/
theorem lc_stage2 (m n : ℕ) (hm : 1 ≤ m)
    (v0 : Fin (m + n)) (h0 : (v0 : ℕ) = 0) :
    localComplement (stage2 m n) v0 = doubleStar m n := by
  ext x y
  simp only [localComplement_adj, xor'_iff, stage2_adj, doubleStar_adj, ne_eq,
    Fin.ext_iff, h0]
  omega

/-- The complete bipartite graph `K_{m,n}` (with `m, n ≥ 1`) is
local-complementation-equivalent to the double-star caterpillar, via the
verified LC sequence τ₀, τ_m, τ₀. -/
theorem bipartite_lcEquiv_doubleStar (m n : ℕ) (hm : 1 ≤ m) (hn : 1 ≤ n) :
    LCEquiv (completeBipartite m n) (doubleStar m n) := by
  have h0mn : 0 < m + n := by omega
  have hmmn : m < m + n := by omega
  have e1 : localComplement (completeBipartite m n) ⟨0, h0mn⟩ = stage1 m n :=
    lc_completeBipartite m n hm ⟨0, h0mn⟩ rfl
  have e2 : localComplement (stage1 m n) ⟨m, hmmn⟩ = stage2 m n :=
    lc_stage1 m n ⟨m, hmmn⟩ rfl
  have e3 : localComplement (stage2 m n) ⟨0, h0mn⟩ = doubleStar m n :=
    lc_stage2 m n hm ⟨0, h0mn⟩ rfl
  have h1 : LCEquiv (completeBipartite m n) (stage1 m n) := by
    rw [← e1]; exact lcEquiv_localComplement _ _
  have h2 : LCEquiv (stage1 m n) (stage2 m n) := by
    rw [← e2]; exact lcEquiv_localComplement _ _
  have h3 : LCEquiv (stage2 m n) (doubleStar m n) := by
    rw [← e3]; exact lcEquiv_localComplement _ _
  exact lcEquiv_trans (lcEquiv_trans h1 h2) h3

end Empiricist

import Mathlib.Data.Matrix.Basic
import Mathlib.Data.Complex.Basic
import Mathlib.Data.Fintype.BigOperators
import Mathlib.Tactic
import EmpiricistLean.Basic

/-!
# Concrete 2×2 complex pairing engine

Two bilinear pairings on `Fin 2 → ℂ`:
* `plainPair u v = u 0 * v 0 + u 1 * v 1` (plain bilinear product)
* `twistPair u v = u 0 * v 1 + u 1 * v 0` (swap-twisted product)

A vector is *axis-aligned* iff one of its two coordinates vanishes.
Headline: for nonzero axis-aligned `u v`, the two pairings cannot both vanish.
-/

namespace Empiricist

/-- The plain bilinear inner product on `Fin 2 → ℂ`. -/
def plainPair (u v : Fin 2 → ℂ) : ℂ := u 0 * v 0 + u 1 * v 1

/-- The swap-twisted bilinear product on `Fin 2 → ℂ`
(the plain pairing of `u` against the coordinate-swapped `v`). -/
def twistPair (u v : Fin 2 → ℂ) : ℂ := u 0 * v 1 + u 1 * v 0

/-- `u` is axis-aligned iff one of its coordinates is zero. -/
def AxisAligned (u : Fin 2 → ℂ) : Prop := u 0 = 0 ∨ u 1 = 0

/-- A nonzero axis-aligned vector has exactly one nonzero coordinate. -/
lemma axis_cases {u : Fin 2 → ℂ} (hu : u ≠ 0) (ha : AxisAligned u) :
    (u 0 ≠ 0 ∧ u 1 = 0) ∨ (u 0 = 0 ∧ u 1 ≠ 0) := by
  rcases ha with h | h
  · right
    refine ⟨h, fun h1 => hu ?_⟩
    funext i
    fin_cases i <;> simp [h, h1]
  · left
    refine ⟨fun h0 => hu ?_, h⟩
    funext i
    fin_cases i <;> simp [h, h0]

/-- For nonzero axis-aligned `u, v : Fin 2 → ℂ`, the plain pairing and the
swap-twisted pairing cannot both vanish. -/
theorem axis_pairing_not_both_zero {u v : Fin 2 → ℂ}
    (hu : u ≠ 0) (hv : v ≠ 0) (hau : AxisAligned u) (hav : AxisAligned v) :
    ¬ (plainPair u v = 0 ∧ twistPair u v = 0) := by
  rintro ⟨hp, ht⟩
  rcases axis_cases hu hau with ⟨hu0, hu1⟩ | ⟨hu0, hu1⟩ <;>
    rcases axis_cases hv hav with ⟨hv0, hv1⟩ | ⟨hv0, hv1⟩
  · -- both nonzero in slot 0: plainPair = u 0 * v 0 ≠ 0
    exact mul_ne_zero hu0 hv0 (by simpa [plainPair, hu1, hv1] using hp)
  · -- u in slot 0, v in slot 1: twistPair = u 0 * v 1 ≠ 0
    exact mul_ne_zero hu0 hv1 (by simpa [twistPair, hu1, hv0] using ht)
  · -- u in slot 1, v in slot 0: twistPair = u 1 * v 0 ≠ 0
    exact mul_ne_zero hu1 hv0 (by simpa [twistPair, hu0, hv1] using ht)
  · -- both nonzero in slot 1: plainPair = u 1 * v 1 ≠ 0
    exact mul_ne_zero hu1 hv1 (by simpa [plainPair, hu0, hv0] using hp)

/-- Corollary: under the same hypotheses, if the plain pairing vanishes then the
twisted pairing does not. -/
theorem axis_plain_zero_twist_ne {u v : Fin 2 → ℂ}
    (hu : u ≠ 0) (hv : v ≠ 0) (hau : AxisAligned u) (hav : AxisAligned v)
    (hp : plainPair u v = 0) : twistPair u v ≠ 0 := fun ht =>
  axis_pairing_not_both_zero hu hv hau hav ⟨hp, ht⟩

end Empiricist
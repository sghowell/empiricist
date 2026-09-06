import Mathlib.Data.Matrix.Basic
import Mathlib.Data.Complex.Basic
import Mathlib.Tactic
import EmpiricistLean.Basic
import EmpiricistLean.P3Amplitudes
import EmpiricistLean.P3Pauli
import EmpiricistLean.P3TwoByTwo

namespace Empiricist

/-!
# Round-2 probe (error-tolerant)

Round 1 returned `gate=None` with no reported goal states, i.e. the module hit
hard elaboration errors (guessed namespaces / argument types / `unfold`s)
before any `?_` hole could be diagnosed.  In this round every reference to the
pinned `EmpiricistLean` API sits inside a `first | ... | trivial` alternative:
a wrong guess degrades to `trivial` (no hard error), while a correct guess
parks the resolved constant in the local context of a named `?hole`, or
exposes its definitional body via a `delta`-transformed goal.  The expected
outcome is `gate=diagnostics` ("unsolved goals") whose goal states surface the
exact API; the faithful headline theorem is then written against it.
-/

/-- Headline placeholder for this probe round.  The hole `?engine_type` reports
the exact statement of the promoted engine `axis_pairing_not_both_zero`
(hence also the exact types of `plainPair`, `twistPair`, `AxisAligned`). -/
theorem pauli_eigvec_axis_aligned : True := by
  first
  | (have hEngine := @EmpiricistLean.P3TwoByTwo.axis_pairing_not_both_zero;
      exact ?engine_type)
  | (have hEngine := @axis_pairing_not_both_zero; exact ?engine_type_bare)
  | trivial

/-- Type of `pauliOf` (also reveals the real name/namespace of `BellLabel`
and the matrix type used). -/
theorem probe_pauliOf_type : True := by
  first
  | (have h := @EmpiricistLean.P3Pauli.pauliOf; exact ?pauliOf_type)
  | (have h := @EmpiricistLean.pauliOf; exact ?pauliOf_type_mid)
  | (have h := @pauliOf; exact ?pauliOf_type_bare)
  | trivial

/-- Body of `pauliOf` (reveals the `BellLabel` match arms and which sigma
matrix each label maps to). -/
theorem probe_pauliOf_body : True := by
  first
  | (refine (fun _ : @EmpiricistLean.P3Pauli.pauliOf = @EmpiricistLean.P3Pauli.pauliOf => True.intro) ?_;
      first | (delta EmpiricistLean.P3Pauli.pauliOf; exact ?pauliOf_body) | exact ?pauliOf_eq)
  | (refine (fun _ : @pauliOf = @pauliOf => True.intro) ?_;
      first | (delta pauliOf; exact ?pauliOf_body_bare) | exact ?pauliOf_eq_bare)
  | trivial

/-- Types of `pauli_expansion` and `pauli_invertible`. -/
theorem probe_pauli_lemmas : True := by
  first
  | (have h1 := @EmpiricistLean.P3Pauli.pauli_expansion;
      have h2 := @EmpiricistLean.P3Pauli.pauli_invertible;
      exact ?pauli_lemmas)
  | (have h1 := @EmpiricistLean.P3Pauli.pauli_expansion; exact ?pauli_expansion_only)
  | (have h1 := @pauli_expansion; exact ?pauli_expansion_bare)
  | trivial

/-- Body of `plainPair`. -/
theorem probe_plainPair : True := by
  first
  | (refine (fun _ : @EmpiricistLean.P3TwoByTwo.plainPair = @EmpiricistLean.P3TwoByTwo.plainPair => True.intro) ?_;
      first | (delta EmpiricistLean.P3TwoByTwo.plainPair; exact ?plainPair_body) | exact ?plainPair_eq)
  | (have h := @EmpiricistLean.P3TwoByTwo.plainPair; exact ?plainPair_type)
  | (have h := @plainPair; exact ?plainPair_type_bare)
  | trivial

/-- Body of `twistPair`. -/
theorem probe_twistPair : True := by
  first
  | (refine (fun _ : @EmpiricistLean.P3TwoByTwo.twistPair = @EmpiricistLean.P3TwoByTwo.twistPair => True.intro) ?_;
      first | (delta EmpiricistLean.P3TwoByTwo.twistPair; exact ?twistPair_body) | exact ?twistPair_eq)
  | (have h := @EmpiricistLean.P3TwoByTwo.twistPair; exact ?twistPair_type)
  | (have h := @twistPair; exact ?twistPair_type_bare)
  | trivial

/-- Body of `AxisAligned`. -/
theorem probe_axisAligned : True := by
  first
  | (refine (fun _ : @EmpiricistLean.P3TwoByTwo.AxisAligned = @EmpiricistLean.P3TwoByTwo.AxisAligned => True.intro) ?_;
      first | (delta EmpiricistLean.P3TwoByTwo.AxisAligned; exact ?axisAligned_body) | exact ?axisAligned_eq)
  | (have h := @EmpiricistLean.P3TwoByTwo.AxisAligned; exact ?axisAligned_type)
  | (have h := @AxisAligned; exact ?axisAligned_type_bare)
  | trivial

/-- Bodies of the four sigma matrices. -/
theorem probe_sigmas : True := by
  first
  | (refine (fun _ : (@EmpiricistLean.P3Amplitudes.sigma0, @EmpiricistLean.P3Amplitudes.sigmaX, @EmpiricistLean.P3Amplitudes.sigmaY, @EmpiricistLean.P3Amplitudes.sigmaZ) = (@EmpiricistLean.P3Amplitudes.sigma0, @EmpiricistLean.P3Amplitudes.sigmaX, @EmpiricistLean.P3Amplitudes.sigmaY, @EmpiricistLean.P3Amplitudes.sigmaZ) => True.intro) ?_;
      first
        | (delta EmpiricistLean.P3Amplitudes.sigma0 EmpiricistLean.P3Amplitudes.sigmaX EmpiricistLean.P3Amplitudes.sigmaY EmpiricistLean.P3Amplitudes.sigmaZ; exact ?sigma_bodies)
        | exact ?sigma_types)
  | (have h := @EmpiricistLean.P3Amplitudes.sigma0; exact ?sigma0_type)
  | (have h := @EmpiricistLean.sigma0; exact ?sigma0_type_mid)
  | (have h := @sigma0; exact ?sigma0_type_bare)
  | trivial

/-- Constructors of `BellLabel`: after `cases`, each hole's target `⊢ c = c`
displays a constructor name. -/
theorem probe_bellLabel : True := by
  first
  | (refine (fun _ : (∀ μ : EmpiricistLean.BellLabel, μ = μ) => True.intro) ?_;
      intro μ; cases μ <;> exact ?_)
  | (refine (fun _ : (∀ μ : EmpiricistLean.P3Pauli.BellLabel, μ = μ) => True.intro) ?_;
      intro μ; cases μ <;> exact ?_)
  | (refine (fun _ : (∀ μ : EmpiricistLean.Basic.BellLabel, μ = μ) => True.intro) ?_;
      intro μ; cases μ <;> exact ?_)
  | (refine (fun _ : (∀ μ : BellLabel, μ = μ) => True.intro) ?_;
      intro μ; cases μ <;> exact ?_)
  | trivial

end Empiricist
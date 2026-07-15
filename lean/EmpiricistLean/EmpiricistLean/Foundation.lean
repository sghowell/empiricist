/-
  EmpiricistLean.FusionLowerBound

  Universal minimum-fusion lower bound F(G) ≥ N - 3 for the P5 GHZ3 fusion model,
  with connectivity DERIVED from component-merge dynamics (not assumed).

  Model:
  • Resource states are GHZ3 (3-qubit) states: starting from g resource states,
    the total qubit count is 3*g. Each fusion consumes 2 qubits, so a schedule
    of f fusions producing an N-qubit output satisfies N + 2*f = 3*g.
  • c : Nat → Nat tracks the number of connected components after i fusions:
    c 0 = g (initially g disjoint GHZ3 components), c f = 1 (final state connected),
    and each fusion merges at most two components, i.e. c i ≤ c (i+1) + 1.

  No imports needed: `omega` and structural `induction` are core Lean 4 tactics.
-/

namespace Empiricist

/--
**Component-merge bound.** If a process starts with `g` components (`c 0 = g`),
ends with `1` component (`c f = 1`), and each of the `f` steps decreases the
component count by at most one (`c i ≤ c (i+1) + 1` for all `i < f`), then
`g ≤ f + 1`. This DERIVES the connectivity constraint: reaching a single
connected component from `g` pieces forces at least `g - 1` fusions.

Proof: induction establishing the invariant `g ≤ c i + i` for all `i ≤ f`,
then evaluate at `i = f` where `c f = 1`.
-/
theorem components_merge_bound (g f : Nat) (c : Nat → Nat)
    (h0 : c 0 = g) (hf : c f = 1)
    (hstep : ∀ i, i < f → c i ≤ c (i + 1) + 1) :
    g ≤ f + 1 := by
  -- Invariant: at every step `i ≤ f`, we have `g ≤ c i + i`.
  have key : ∀ i, i ≤ f → g ≤ c i + i := by
    intro i
    induction i with
    | zero =>
      intro _
      omega
    | succ n ih =>
      intro hle
      have hn : n < f := Nat.lt_of_succ_le hle
      have h1 : g ≤ c n + n := ih (Nat.le_of_lt hn)
      have h2 : c n ≤ c (n + 1) + 1 := hstep n hn
      omega
  -- Evaluate the invariant at `i = f`, where `c f = 1`.
  have hfin : g ≤ c f + f := key f (Nat.le_refl f)
  omega

/--
**Arithmetic step.** Qubit conservation for GHZ3 resources: each of the `g`
resource states contributes 3 qubits and each fusion consumes 2, so an
`N`-qubit output satisfies `N + 2*f = 3*g`. Combined with the connectivity
requirement `g ≤ f + 1`, this yields `N ≤ f + 3`.
-/
theorem fusion_cost_lb_arith (N g f : Nat)
    (hN : 3 ≤ N) (hqubits : N + 2 * f = 3 * g) (hconn : g ≤ f + 1) :
    N ≤ f + 3 := by
  omega

/--
**MAIN THEOREM (universal minimum-fusion lower bound).**
Any GHZ3-fusion schedule of `f` fusions on `g` initial GHZ3 resource states
that produces a connected `N`-vertex (N ≥ 3) output graph state — where the
component count `c` starts at `g` (`c 0 = g`), ends at `1` (`c f = 1`, i.e.
the output is connected), and each fusion merges at most two components
(`c i ≤ c (i+1) + 1`) — must use at least `N - 3` fusions:  `N - 3 ≤ f`.

The connectivity hypothesis `g ≤ f + 1` is DISCHARGED by the component-merge
dynamics via `components_merge_bound`, then combined with qubit conservation
via `fusion_cost_lb_arith`. Since `N ≤ f + 3` holds, the Nat-subtraction form
`N - 3 ≤ f` follows without truncation pitfalls.
-/
theorem fusion_cost_lower_bound (N g f : Nat) (c : Nat → Nat)
    (hN : 3 ≤ N) (hqubits : N + 2 * f = 3 * g)
    (h0 : c 0 = g) (hf : c f = 1)
    (hstep : ∀ i, i < f → c i ≤ c (i + 1) + 1) :
    N - 3 ≤ f := by
  have hconn : g ≤ f + 1 := components_merge_bound g f c h0 hf hstep
  have hbound : N ≤ f + 3 := fusion_cost_lb_arith N g f hN hqubits hconn
  omega

end Empiricist

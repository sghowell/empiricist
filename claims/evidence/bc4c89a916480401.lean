namespace Empiricist

/-- Arithmetic core of the P5 minimum-fusion lower bound.

Photon counting: `g` GHZ₃ resources contribute `3*g` qubits; each of the `f`
fusions consumes 2 qubits, leaving the `N` qubits of the target state, so
`N + 2*f = 3*g`. Connectivity: at least `g - 1` merging fusions are needed to
connect `g` components, i.e. `g ≤ f + 1`. Conclusion: `N ≤ f + 3`, equivalently
the fusion count satisfies `f ≥ N - 3`. -/
theorem fusion_cost_lb_arith (N g f : Nat)
    (hN : 3 ≤ N) (hcount : N + 2 * f = 3 * g) (hconn : g ≤ f + 1) :
    N ≤ f + 3 := by
  omega

end Empiricist

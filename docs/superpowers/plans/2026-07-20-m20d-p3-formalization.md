# M20d: Formalizing "at most 3 of 4" (P3, k=0) — Campaign Plan

**Goal:** the first fully-verified new P3 theorem: for every U ∈ U(4), at most three of the
four Bell states admit unambiguously-identifying detection patterns — hence min_B p_B = 0
for every passive k=0 dual-rail scheme. Source: Fable's L1–L4 proof sketch (ledger artifact
`aed4942e`, runs/p3-campaign), whose L1 bunched-pattern claim is engine-verified.

**Method:** the M18 Fable→Lean formalize loop (propose → hardened gate → goal-state
feedback → revise), decomposed into modules that each fit one call under the 64k output cap
(the K_{m,n} lesson). Fable authors all Lean; the coordinator reviews faithfulness and
promotes reusable modules into the trusted set. Formalizer effort stays HIGH (the effort
ladder applies to open-ended search/strategy calls, not the formalizer, which converges).

**Faithfulness architecture (locked):**
1. All statements live at the AMPLITUDE-VANISHING level. `Identifies U n μ` :=
   (rawAmp μ n U ≠ 0) ∧ (∀ ν ≠ μ, rawAmp ν n U = 0). Normalization constants are dropped —
   identification is invariant under them, and the probability corollary needs only
   "no identifying pattern ⟹ p_B = 0".
2. `rawAmp` is DEFINED by the explicit 2×2 permanent sums, mirroring the
   quadruple-verified `domain/p3/poly.py` construction (both engines + independent symbolic
   review). For pattern {i,j} (i ≤ j; i = j is bunched with the doubled-row permanent
   2·U_ia·U_ib):
   - Φ± : Per(U[{i,j},{0,2}]) ± Per(U[{i,j},{1,3}])
   - Ψ± : Per(U[{i,j},{0,3}]) ± Per(U[{i,j},{1,2}])
   with Per over rows {i,j}, cols {a,b} = U_ia·U_jb + U_ja·U_ib.
   This textual bridge to the verified domain code is the modeled-boundary warrant (the D6
   discipline).
3. The final theorem's TYPE carries the full claim: unitarity hypothesis, quantification
   over all patterns (all 10 multisets), no auxiliary producibility scaffolding.

**Module decomposition (each = one formalize-loop task; promote after PASS + review):**

| # | Module | Content | Target decl |
|---|--------|---------|-------------|
| 1 | `P3Amplitudes` | Pattern type (i ≤ j pairs over Fin 4), rawAmp definitions (4 Bell labels), `Identifies`, and L0: the Q-representation — define σ₀,σₓ,σ_y,σ_z and Q(i,j) := Xᵀσₓ Y (X, Y the 2×2 row-blocks) and prove rawAmp_μ = tr(σ-basis expansion of Q) up to the fixed linear change of basis (Φ⁺↔tr Q, Φ⁻↔tr(σ_z Q), Ψ⁺↔tr(σₓ Q), Ψ⁻↔ −i·tr(σ_y Q) — Fable derives the exact correspondence; the gate arbitrates) | `rawAmp_eq_traceForm` |
| 2 | `P3Pauli` | 2×2 lemmas: Paulis invertible/rank-2; every 2×2 M has unique expansion M = Σ c_μ σ_μ; M ∝ σ_μ ⟺ other three trace-coefficients vanish; distinct non-identity Paulis share no common eigenvector (up to scalar); K_μ := σ_y σ_μ unitary; the 2×2 cofactor identity cof(X) = ε X ε ᵀ form used by L1's row-decoupling | `pauli_no_common_eigenvector` |
| 3 | `P3L1L2` | L1: `Identifies U {i,j} μ ⟺ Q(i,j) = t·σ_μ, t ≠ 0`; bunched Q has rank ≤ 1 hence never identifies; row-decoupling `y_i = λ·x_i·K_μ`, `y_j = −λ·x_j·K_μ` (X invertible case). L2: `M_i := {μ | ∃λ ≠ 0, y_i = λ·x_i·K_μ}` has ≤ 2 elements (via module 2's no-common-eigenvector) | `card_Mset_le_two` |
| 4 | `P3Counting` | Pure finite combinatorics: if every μ ∈ (Fin 4 labels) is "covered" by some pair {i,j} with μ ∈ M_i ∩ M_j, and all |M_i| ≤ 2 over 4 detectors, then either two doubled edges (and a single pattern identifies ≤ 1 label — fed as a hypothesis from L1's Q ∝ unique σ_μ) or the M-sets form a 4-cycle. Stated abstractly over `Fin 4 → Finset (Fin 4)` so it needs no matrix content | `cover_structure` |
| 5 | `P3Main` | L3/L4: in the 4-cycle configuration, rows i and k of U (the complementary-pair detectors) cannot be orthogonal — the anticommuting-Pauli eigenbasis argument — contradicting unitarity. Assembly: `p3_at_most_three : ∀ U ∈ unitaryGroup (Fin 4) ℂ, ¬ ∀ μ, ∃ n, Identifies U n μ` + corollary `p3_min_support : ∀ U…, ∃ μ, ∀ n, ¬ Identifies U n μ` | `p3_at_most_three` |

**Risks / honesty:**
- Hardest formalization target yet (complex 2×2 algebra vs. the graph combinatorics of P5);
  the sketch is Fable's own and HEURISTIC — the gate may expose real gaps, especially in
  L1's row-decoupling (the cofactor manipulation) and L4's orthogonality contradiction. A
  module that stalls ≥ 2 full loop runs triggers re-decomposition or an honest campaign
  pause with the partial chain recorded.
- The ledger for this campaign is `runs/p3-campaign` (same problem, same provenance rules).
  Promoted modules enter `_TRUSTED_EMPIRICIST_MODULES` + lakefile + allow-lists with the
  full slow_lean security suite per promotion (the established mechanism).
- Success = `p3_at_most_three` FORMALIZED and faithful. Partial success (modules 1–3 landed,
  counting/4-cycle open) is still recorded value: the L1/L2 structure alone is reusable for
  the k=2 analog.

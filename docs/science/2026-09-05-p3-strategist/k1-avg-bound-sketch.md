## 1. Proof sketch for p_avg ≤ 1/2 at k = 1

**Setup Lemma S0 (frame reduction) — mechanical.**
Let x₀,x₁ (columns 0,1 of U), y₀,y₁ (columns 2,3), and v := Uw = Σ_c w_c u_c. Then (x₀,x₁,y₀,y₁,v) is an **orthonormal 5-frame** in ℂᵐ — crucially v ⊥ all four signal columns, since w is supported on ancilla modes. Every k=1 scheme is exactly the data (5-frame in ℂᵐ, detector basis, assignment f). Amplitudes: with a_{αβ}(n) := ⟨n| Sym(x_α ⊗ y_β ⊗ v)-image, the four vectors u_{αβ} := U a†_α b†_β c†_w|0⟩ are orthonormal, and the Bell amplitudes are z_{Φ±}(n) = (a₀₀ ± a₁₁)/√2, z_{Ψ±}(n) = (a₀₁ ± a₁₀)/√2.

**L1\* (3-photon Pauli reduction) — mechanical, the exact analogue of L1.**
Define T(n) ∈ ℂ^{2×2} by T_{αβ}(n) = a_{αβ}(n) = per([x_α | y_β | v]_n)/√(n!). Then z_μ(n) = tr(P_μᵀ T(n))/√2 with (P_{Φ+},P_{Φ−},P_{Ψ+},P_{Ψ−}) = (I, σ_z, σ_x, iσ_y). Pauli orthogonality gives:
- **n identifies μ ⟺ T(n) = c·P_μ, c ≠ 0** (a Pauli-ray condition, exactly as "Q ∝ σ_μ" at k=0, up to a fixed relabeling dictionary);
- ‖z(n)‖² = ‖T(n)‖²_F, and Parseval/unitarity: Σ_n ‖T(n)‖²_F = 4. So **p_avg ≤ 1/2 ⟺ Σ_{n identified} ‖T(n)‖²_F ≤ 2.**

**L2\* (v-column expansion; the ancilla adds one column) — mechanical.**
Expanding each 3×3 permanent along the v column: for distinct i,j,k,
T(ijk) = v_i M_{jk} + v_j M_{ik} + v_k M_{ij},  T(2p,q) = (2v_p M_{pq} + v_q M_{pp})/√2,  T(3p) ∝ v_p M_{pp},
where M_{pq} := ξ_pᵀη_q + ξ_qᵀη_p with row data ξ_p = (x₀(p),x₁(p)), η_p = (y₀(p),y₁(p)). **M_{pq} is literally the verified k=0 matrix Q_{pq} = X_{pq}ᵀσ_x Y_{pq}** (identical expression). Corollaries, mechanical: M_{pp} has rank ≤ 1, so triple-bunched patterns identify nothing (Paulis are invertible); identification at (2p,q) requires the rank-2 completion by v_p M_{pq}.

**L3\* (inherited k=0 structure) — mechanical given the existing Lean development.**
The intrinsic row label sets M_p = {μ : η_p ∥ ξ_p K_μ} still satisfy |M_p| ≤ 2 (verified L2), and the 4-cycle obstruction (L4) still holds for the M-field. What is *lost* at k=1: T(n) ∝ P_μ no longer forces μ ∈ M_i ∩ M_j ∩ M_k, because a sum of three non-Pauli M's can lie on a Pauli ray. This is exactly why all four states become identifiable (numerics: (1, 1/6, 1/2, 2/9)) and why the k=1 bound **cannot be a pattern-counting argument; it must be a mass inequality.**

**L4\* (coherence budget) — mechanical scaffold.**
Unitarity gives Σ_n ā₀₀a₁₁ = 0. On E_Φ := E_{Φ+} ∪ E_{Φ−}, |a₀₀| ≡ |a₁₁| with locked phase (0 on E_{Φ+}, π on E_{Φ−}). Writing s_± = p_{Φ±}/2, Cauchy–Schwarz off E_Φ gives |s₊ − s₋| ≤ 1 − s₊ − s₋, i.e. p_{Φ±} ≤ 1 each (and same for Ψ). This alone is the trivial bound (Σ ≤ 4); it is the ledger into which linear optics must be injected. Notably, at the numerical all-four optimum the Φ-budget is **exactly saturated**: s₊ = 1/2, s₋ = 1/12, 1 − s₊ − s₋ = 5/12 = |s₊−s₋|, forcing a₁₁(n) = −a₀₀(n) *pointwise* off E_Φ. So off-E patterns are "Φ−-like in the diagonal sector, contaminated by off-diagonals" — the correct extremal picture.

**L5\* (phase rigidity) — mechanical.**
Replacing U by U·(phase θ on mode 1) rotates the Bell basis (Φ_θ family). A pattern with full contrast identifies the θ-rotated basis for exactly one θ mod π; identified sets for distinct phases are disjoint. This converts "identification" into "full-contrast fringe with locked phase," a variational handle.

**L6\* (CORE — one-photon distillation bound) — the real content.**
*Claim.* For every orthonormal 5-frame (x₀,x₁,y₀,y₁,v) in ℂᵐ: Σ_{n : T(n) ∈ ∪_μ ℂ*P_μ} ‖T(n)‖²_F ≤ 2.
Equivalently: since each a_{αβ}(n) is **linear in v** (L2\*), a_{αβ}(n) = ⟨c̄_n^{αβ}, v⟩ with c-vectors built from the k=0 M-field, and Σ_n c̄_n^{αβ}(c̄_n^{αβ})† = P_V (resolution of identity on V = span(x,y)^⊥, for each αβ), the claim is: the quadratic form v ↦ 2v†(Σ_{E_Φ} C^{00}_n + Σ_{E_Ψ} C^{01}_n)v, **subject to the pointwise Pauli-ray constraints on v**, is ≤ 2.
*Why this is where the content sits:* the four c-fields are rigidly correlated because each pair (p,q) of detectors is shared by m−2 patterns and M_{pq} is a sum of two rank-ones from the same isometry; distilling monochromatic mass at one pattern forcibly deposits mixed mass at sibling patterns sharing its pairs.
*Proposed proof route:* at an optimum, (i) L5\* first-order conditions force the saturation structure seen numerically (off-E pointwise anti-alignment a₁₁ = −κa₀₀, κ = 1 by norm matching); (ii) pointwise proportionality of two symmetrized product tensors Sym(x₁⊗y₁⊗v) ∝ Sym(x₀⊗y₀⊗v) on a full-mass set is a strong algebraic condition — push it through the row decomposition to force, on the dominant rows, the eigen-Pauli alignment of the verified L2; (iii) close with the verified 4-cycle contradiction (L4) to show Σ > 2 forces an inconsistent 2-regular label graph on the rows carrying the saturated coherence.
**This is the step I am least sure of** — specifically (ii), converting off-E pointwise proportionality into row decoupling. Confidence the *claim* L6\* is true: 0.90 (two exact-arithmetic engines, three values of m, never above 1/2, extremal structure coherent). Confidence this exact route closes without a new idea: 0.5.

Everything above L6\* is formalizable now with the existing k=0 infrastructure (S0, L1\*, L2\* are permanent expansions and Pauli orthogonality; L3\* is reuse; L4\*, L5\* are Cauchy–Schwarz and phase bookkeeping).

## 2. Could it be false?

I assign ≤ 0.10 to falsity. If false, the counterexample must have this structure (each clause is a theorem-or-test):

- **Genuine 3-photon interference at identified patterns.** Provable lemma (easy, formalize first): if every identified pattern has one click in a detector where all four signal columns vanish, the ancilla factors out and the scheme reduces to k=0, hence ≤ 1/2 by Calsamiglia–Lütkenhaus. So v's detector support must overlap the output support of *both* rails at the identified patterns.
- Refutable predictions for the optimizer:
  - **T1:** maximize Σ_μ p_μ subject to p_{Φ+} + p_{Φ−} ≥ 1 + δ (δ = 0.05) at m = 6,7,8. Prediction: total stays ≤ 2; the constraint region collapses toward the (1, 1/6, ·, ·) family.
  - **T2:** all-four-identification cap. Prediction: max Σ_μ p_μ over all-four schemes is exactly 17/9 at m = 5, and ≤ 2 − 1/9 for m ≤ 8.
  - **T3 (saturation signature):** at every exact optimum with Φ-pair best-identified, a₁₁(n) = −a₀₀(n) pointwise off E_Φ. Any optimum violating this falsifies my extremal picture (and weakens the L6\* route even if the bound holds).
  - **T4:** for all-four schemes, p_{Φ+} + p_{Ψ+} ≤ 3/2 (observed as equality at the min-optimal scheme). A violation would point to where >1/2 leverage lives.
  - If a counterexample exists at all, I predict it needs m ≥ 7, complex (not real-orthogonal) U, and identified patterns exclusively of type (1,1,1) with all three detectors in the joint support of v and both rails.

## 3. Simple 1/2 + ε bound?

Honest answer: **I do not know a simple conservation argument giving any ε < 1/2.** The obvious ledgers (L4\* coherence budget, Gram identity Σ_n z(n)z(n)† = I₄) only yield p_μ ≤ 1 each, i.e. p_avg ≤ 1, and are saturated by general-POVM discrimination — every ε strictly below 1 must use optical structure, and the cheapest such structure (rank of M, sharing of pairs) already lands you in L6\* territory. What *is* cheap and rigorous:
- p_avg = 1/2 exactly for any scheme whose ancilla does not interfere (reduction lemma above) — formalize this first; it certifies the conjectured optimum is achieved and localizes any violation to interfering schemes.
- Triple-bunched patterns identify nothing; (2p,q) patterns need v_p ≠ 0 and rank-2 completion — prunes the assignment space.
- **Machine route to an explicit ε:** the problem is polynomial after S0. Use the relaxation: identified mass ≤ Σ_n (2|z_{f(n)}(n)|² − ‖z(n)‖²)₊, which is exact on monochromatic patterns. For fixed m = 5 (35 patterns, pruned by the rank lemmas) and fixed assignment branch, "Σ ≤ 3" (p_avg ≤ 3/4) is a degree-12 rational-SOS target over the 5-frame variety — heavier than the k=0 certificate but the same technology. I'd stake ε = 1/4 (certified p_avg ≤ 3/4 at m = 5) as the realistic first machine milestone, with the tight 2 reserved for the L6\* chain.

Summary of confidences: p\*_avg(1) = 1/2 true: 0.90. Sketch S0–L5\* formalizable as stated: 0.95. L6\* is the correct minimal core lemma: 0.85. Proposed route to L6\*: 0.5. Existence of a *simple* analytic ε-argument: 0.3.
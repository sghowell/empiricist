## 1. Mechanism of the certified 5-mode scheme

**The circuit, decoded.** Gauge-fix and factor the matrix. Rows 0 and 4 have all-|1/2| entries on the Bell columns with the sign pattern (col1 = −col0, col3 = col2) in row 0 and (col1 = +col0, col3 = −col2) in row 4. Writing a± = (a₀±a₁)/√2, b± = (a₂±a₃)/√2 (i.e. **Hadamards on both dual-rail qubits**), the certified U is, up to output phases/permutations:

1. H on qubit A's rails, H on qubit B's rails.
2. Two 50/50 beamsplitters on the *anti-correlated* rotated pairs: BS₁(a₋, b₊) → outputs (mode 0, d₁); BS₂(a₊, b₋) → outputs (mode 4, d₂).
3. A **balanced tritter** (π/6-lattice phases, DFT-type) on (d₁, d₂, ancilla) → modes 1, 2, 3.

Consistency check on moduli: each Bell rail reaches each tritter output through *both* d₁ and d₂ with amplitude 1/(2√3) each and relative phase ±π/2, giving |amp|² = 2·(1/12) = 1/6 ✓; trigger rows are H·BS paths, (1/√2)² per path summed to modulus 1/2 ✓; ancilla weight 1/3 in rows 1–3 ✓; rows 0,4 never see the ancilla ✓. **Claim (confidence ~0.9): the 5×5 matrix is exactly this circuit under output-phase/permutation and local dual-rail (hence WLOG) input symmetries.** Machine check: multiply the four-layer factorization and compare in ℚ(i,√2,√3).

**Why Φ− and Ψ− become identifiable at all.** In the rotated basis: Φ⁺ → a₊b₊+a₋b₋, Ψ⁺ → a₊b₊−a₋b₋ (cross-pair: one photon into each BS), Φ⁻ → a₊b₋+a₋b₊, Ψ⁻ → a₊b₋−a₋b₊ (within-pair: both photons into the *same* BS). Then:

- **Within-pair states HOM-bunch**: a₋b₊ enters the two input ports of BS₁, so the output has *no* (m₀,d₁) coincidence — only m₀² − d₁². Φ⁻ and Ψ⁻ become (m₀²−d₁²) ± (m₄²−d₂²), differing only by one relative sign. On trigger-bunched events (n₀=2 or n₄=2) that sign is invisible → those events are ⊥. On d-bunched events, the states |2_{d₁}⟩ ± c|2_{d₂}⟩ **plus the ancilla** enter the tritter as *three-photon* states. This is precisely how the k=0 obstruction is evaded: at k=0 a coincidence pattern's amplitude is a fixed ±-combination of two Pauli-pair permanents and unitarity (your 4-cycle/sesquilinear lemma) forbids isolating one sign globally; here each amplitude is a 3×3 permanent *linear in the ancilla column w*, so the tritter phases can zero the unwanted sign pattern-by-pattern. Tichy-type suppression in the balanced tritter gives Φ⁻ some patterns (e.g. (1,1,1) in modes 1–3) where the Ψ⁻ permanent vanishes and vice versa (e.g. (0,2,1),(1,2,0)).
- **Cross-pair states anti/co-bunch across BSs**: Φ⁺ → (m₀d₂ + m₄d₁)/√2, Ψ⁺ → (m₀m₄ + d₁d₂)/√2 (the phase choices cancel the complementary terms — visible in the data: every Φ⁺ pattern has n₀+n₄ = 1, every identified Ψ⁺ pattern has n₀ = n₄ = 1).

**Why (1, 1/6, 1/2, 2/9).**
- p_{Φ⁺} = 1: the signature "exactly one trigger photon (n₀+n₄=1) and two photons in the tritter" is exclusive to Φ⁺ at the *coarse* level — Ψ⁺ gives trigger count 0 or 2, and Φ⁻/Ψ⁻ give trigger count 0 or 2 by HOM. No fine-tuning needed; deterministic.
- p_{Ψ⁺} = 1/2: the m₀m₄ branch (both triggers fire, ancilla alone in the tritter) carries weight 1/2 and is exclusive; the d₁d₂ branch collides with Φ⁻/Ψ⁻ three-photon events and is sacrificed.
- p_{Φ⁻} = 1/6, p_{Ψ⁻} = 2/9: each has weight 1/2 in the d-bunched branch; the balanced tritter converts conditional fractions 1/3 and 4/9 of it (three-photon permanent zeros of the "+" vs "−" superpositions; 4/9 = 2·(2/9) bunching amplitudes, 1/3 from the (1,1,1)-type zero). Sum of conditionals 1/3+4/9 = 7/9 < 1: the residual 2/9 of the d-branch is where both permanents are nonzero → ⊥.

So the textbook line is: **"X-basis Bell analyser whose two HOM ports are fed, together with the single ancilla photon, into a balanced tritter."** The vector's asymmetry is structural: the Klein four-group of local Paulis (passive dual-rail optics) can permute which state gets the 1, so the family is really the V₄-orbit of (1, 1/6, 1/2, 2/9).

## 2. Is 1/6 the max? No. Conjecture: max–min = 1/4, for all m

**1/6 is already refuted at m = 5 by your own data**: the exact, lifted balanced witness (1/4, 1/4, 1/4, 1/4). So decisively: max_min ≥ 1/4 at m = 5.

**Conjecture (confidence 0.75): for k = 1 and every m, max_U min_B p_B = 1/4**, attained by the balanced m = 5 witness. Supporting evidence: two independent engines, 130 restarts across m = 5,6,7, hard ceiling at 1/4, exact lift at two mode numbers.

**Sharper frontier conjecture (confidence 0.6): p₍₁₎ + p₍₂₎ ≤ 1/2 for k = 1** (two smallest successes), which implies min ≤ 1/4. Checks: balanced witness 1/4+1/4 = 1/2 (tight); the 1/6-family 1/6+2/9 = 7/18 ✓; k=0 schemes have p₍₁₎ = p₍₂₎ = 0 ✓; Grice (k=2) violates it at 1, correctly signalling the bound is k-dependent.

**Proof strategy and the exact lemma to machine-check.** Set up: for a three-photon pattern n, the four Bell amplitudes are (v₀₂±v₁₃)/√2 and (v₀₃±v₁₂)/√2, where v_S(n) = Σ_r w_r · c(n,r) · perm(U[n−e_r | S]) is *linear in the ancilla column w*, with 2×2 permanents inheriting the k=0 Pauli structure Q = XᵀσₓY at each reduced pattern n−e_r.

- **Lemma L1 (easy, already implicit; formalize first):** the four vectors (Ã_S(n))ₙ, S ∈ {02,13,03,12}, form an orthonormal 4-frame (three-photon unitarity: overlaps = permanents of Gram matrices of {e_i,e_j,w} = δ). Unambiguity forces Ã₀₃ = Ã₁₂ = 0 on M_{Φ±} and Ã₀₂ = Ã₁₃ = 0 on M_{Ψ±}; hence p_{Φ⁺}+p_{Φ⁻} ≤ 2 and p_{Ψ⁺}+p_{Ψ⁻} ≤ 2, so Σ_B p_B ≤ 4. **Important negative finding**: I checked that the orthonormal-frame relaxation alone permits min = 1 — it does *not* cap the min at all. So the true bound is genuinely permanental (bosonic), exactly as at k=0.
- **Lemma L2 (the hard target):** on the permanental variety {Ã_S(n) = perm(U[n|S∪{4}])/√(n!) : U ∈ U(5)}, prove p₍₁₎ + p₍₂₎ ≤ 1/2. Concrete machine-checkable route: fix m = 5 (see prediction P1 for why m is WLOG-plausible), parametrize by the 2-photon cofactor permanents and w, express p₍₁₎+p₍₂₎ − 1/2 ≤ 0 on the variety cut out by the unitarity polynomials, and find a **sum-of-squares / Positivstellensatz certificate numerically, then verify it in exact arithmetic in Lean** (rational SOS with denominators cleared). This is the same "find witness numerically, certify exactly" pipeline that produced the 1/6 scheme, pointed at an inequality instead of an equality. Fallback weaker target: Σ_B p_B ≤ 2 for k = 1 (confidence 0.6; the 1/6-family sits at 17/9, suspiciously close), which only forces min ≤ 1/2 but would be the first quantitative k=1 no-go.
- **Mode-reduction lemma (needed for "all m"):** any k=1 scheme's success vector at m > 5 is achieved at m = 5... I do *not* believe this literally (confidence in literal statement 0.3); instead check the weaker, sufficient claim that the SOS certificate's degree bounds are m-uniform, or run the L2 pipeline at m = 6.

## 3. Refutable predictions for the optimizer

**P1 (m-independence).** With ≥200 restarts and a slower annealing of the unambiguity gate, m = 7 will reach exactly 1/4 balanced, and no restart at m = 6, 7, 8 will exceed 1/4 by more than solver tolerance (10⁻⁶). Confidence 0.75. Any exceedance kills the main conjecture.

**P2 (frontier).** Directly maximize p₍₁₎ + p₍₂₎ (not the min). Prediction: plateau at exactly 1/2 for m = 5, 6, with maximizers including the balanced witness and points with vectors like (x, 1/2−y, ·, ·). Confidence 0.6. A value > 1/2 refutes the frontier conjecture but not necessarily max-min = 1/4.

**P3 (entangled single-photon ancilla — this is a theorem, not a bet).** A single photon in a superposition over ancilla modes 4,5 at m = 6 gives *identical* optimum to a single-mode ancilla at m = 6: prepend a 2-mode unitary rotating the superposition to mode 4 and absorb it into U. Confidence 0.98. The optimizer must reproduce the m = 6 single-mode landscape exactly; any statistically significant deviation indicates a harness bug, so this doubles as a validation test.

**P4 (arithmetic of exact optima).** Every exactly-liftable stationary unambiguous k=1 scheme at m ≤ 6 has p_B ∈ ℚ with denominator dividing 72, drawn from tritter/BS event probabilities {1, 1/2, 1/4, 1/6, 2/9, 1/8, 1/9, 1/18, ...}, and matrix entries in ℚ(i, √2, √3) with phases on the π/12 lattice. Corollary bet: the 0.1524 balanced plateau is *not* a global-family member — predict it is a saddle whose exactification fails (no algebraic lift in that field) and which flows to 1/4 or 1/6 under continued annealing. Confidence 0.5 on the denominator claim, 0.7 on the 0.1524 claim.

**P5 (structure of the balanced 1/4 witness).** Its identifying-pattern classes are permuted by the Klein group V₄ of Bell relabellings (equivalently: the scheme is V₄-covariant up to output permutation, unlike the 1/6 scheme, which spontaneously breaks V₄ to put all weight on Φ⁺). Test by inspecting the lifted witness's pattern table. Confidence 0.6.

**P6 (average metric cross-check).** Maximizing the *average* at k = 1 will plateau at exactly 1/2 for all m ≤ 7 (achieved by routing the ancilla to a decoupled mode + standard analyser; 17/36 < 1/2 for the 1/6-family is consistent). Confidence 0.7 — consistent with the Olivo–Grosshans numerics; exceeding 1/2 with one photon would itself be publishable and would force re-examination of P1.

**Priority order:** P3 (free validation) → P1 at m = 7 → P2 → L2's numerical SOS search at m = 5. If P1 and P2 hold, commit to formalizing L1 in Lean immediately (it is a finite permanent–Gram computation, same toolkit as the k=0 sesquilinear identity) while the SOS certificate for L2 is hunted numerically.
# P3 upper bounds: the photon-number moment bound p_avg ≤ (k + 1)/(k + 2)

**Date:** 2026-10-26 · **Problem:** P3 (ancilla-boosted linear-optical Bell measurement) ·
**Milestone:** M27b (`docs/superpowers/plans/2026-10-26-m27b-p3-upper-bounds.md`) ·
**Method:** a feasibility pass on the direct SOS route, which found instead an
assignment-free relaxation by photon-number moments; an exact SOS certificate for its
one lemma; exact moment identities at fixed (k, m); numeric probes of the next level.
No model spend outside the review receipts (accounted below).

## Headline

**Theorem (moment bound).** Let a Bell-measurement scheme use a passive interferometer
U ∈ U(m), an ancilla state of exactly k photons on the ancilla modes (any state, possibly
entangled, any number of modes), photon-number-resolving detection, and any unambiguous
assignment. Then its average success satisfies

    p_avg = (1/4) Σ_B p_B  ≤  (k + 1)/(k + 2),

and hence so does min_B p_B, the problem's p.

| k | bound | known value / construction | status of the bound |
|---|---|---|---|
| 0 | 1/2 | 1/2 (standard BSM) — Calsamiglia–Lütkenhaus | tight; reproved for **every** assignment |
| 1 | 2/3 | best known 1/2 (130 optimizer restarts; conjecture 1/2) | first bound below 1 at k = 1 |
| 2 | 3/4 | 3/4 (Grice, Bell-pair ancilla) | **tight: p*_avg(2) = 3/4** |
| 2^N − 2 | 1 − 2^{−N} | 1 − 2^{−N} (Grice) | **tight along the whole family** |

Consequences for the problem's open parts (average metric unless stated):

- **P3(ii)** "prove or refute p*(2) = 3/4 over all passive interferometers and all
  two-photon ancilla states": for the literature's average metric it is **proved** —
  no k = 2 scheme beats Grice. For the problem's min metric the bound gives
  p*_min(2) ≤ 3/4; the best fixed scheme known has min 1/2 (a classical coin reaches 3/4,
  `docs/science/2026-07-20-p3-certificates-and-proofs.md`), so the min-metric question
  narrows to whether a single scheme can balance Grice.
- **P3(iii)** "decide whether 1 − p*(k) = e^{−Θ(k)} is achievable, or prove
  1 − p*(k) = Ω(1/poly(k))": **1 − p*(k) ≥ 1/(k + 2) for every k** (both metrics), and
  Grice gives 1 − p*_avg(k) ≤ 1/(k + 2) along k = 2^N − 2. Exponential decay is
  impossible; for the average metric 1 − p*_avg(k) = Θ(1/k), with the exact value
  1/(k + 2) along k = 2^N − 2.
- **P3(i)** at k = 1: p*_avg(1) ≤ 2/3 (conjecture 1/2), the brief's target B beaten for
  every m, not only m = 5.

**Status and caution.** The general statement is HEURISTIC in the ledger (a paper proof,
five steps, below); its one lemma and three instances are CERTIFIED. The argument is short,
and its consequences are stronger than the "open" status the problem statement gives (ii)
and (iii). Before it is cited outside this repository it needs a literature check — the
Calsamiglia–Lütkenhaus first-detection argument (2001) is its k = 0 ancestor, and an
ancilla version may exist — and the Lean formalization (Next steps).

## The proof

Notation. Dual-rail qubit A on input modes 0, 1 (rail 0 ↔ |0⟩), qubit B on 2, 3; the four
Bell states |B⟩ (Φ± = (|00⟩ ± |11⟩)/√2, Ψ± = (|01⟩ ± |10⟩)/√2); |in_B⟩ = |B⟩ ⊗ |A⟩ with
|A⟩ the k-photon ancilla state; |out_B⟩ = Γ(U)|in_B⟩ the (k + 2)-photon output;
z_B(n) = ⟨n|out_B⟩ for an output pattern n; N_i = b_i†b_i the photon number of output
mode i.

**Step 1 (identified patterns are Bell-diagonal).** Put G(n) = z(n) z(n)† (a 4 × 4
matrix indexed by Bell labels). If the assignment sends n to B, unambiguity says
z_{B'}(n) = 0 for every B' ≠ B, so G(n) = |z_B(n)|² e_B e_B†. Let E be the set of
assigned patterns. Then Σ_B p_B = Σ_{n∈E} tr G(n).

**Step 2 (counting photons).** Every pattern has k + 2 photons: Σ_i n_i = k + 2. So
(k + 2) Σ_B p_B = Σ_i tr Λ_i with Λ_i := Σ_{n∈E} n_i G(n), a Bell-diagonal PSD matrix.

**Step 3 (the moment identity).** D_i := Σ_n n_i G(n) has entries
D_i[B, B'] = ⟨out_{B'}|N_i|out_B⟩, the Gram matrix of the conditional states b_i|out_B⟩.
Since Γ(U)† N_i Γ(U) = Σ_{j,l} Ū_ij U_il a_j† a_l, D_i is (the transpose of) the
Bell-basis matrix of the two-qubit operator

    Ô_i = s_A |α⟩⟨α| ⊗ I + s_B I ⊗ |β⟩⟨β| + c_i I,

where s_A = |U_i0|² + |U_i1|² and α ∝ (Ū_i0, Ū_i1) (the single-photon operator of output
mode i on qubit A's rails, which is rank one), s_B, β likewise on qubit B's rails, and
c_i = ⟨A|Γ(U)†N_iΓ(U)|A⟩ ≥ 0 the ancilla's mean photon number in output mode i. (The
ancilla contributes only to the diagonal: a_j†a_l with both modes on the ancilla gives
⟨B'|B⟩ ⟨A|a_j†a_l|A⟩; mixed signal/ancilla terms change the signal photon number and
vanish between Bell states.)

**Step 4 (one-body USD lemma).** D_i − Λ_i = Σ_{n∉E} n_i G(n) ⪰ 0, so the Bell-diagonal
Λ_i = Σ_B λ_B |B⟩⟨B| satisfies Λ_i ⪯ Ô_i. *Lemma:* for unit α, β and any real
s_A, s_B, c, Bell-diagonal Λ ⪯ s_A|α⟩⟨α| ⊗ I + s_B I ⊗ |β⟩⟨β| + cI implies
tr Λ ≤ s_A + s_B + 4c. *Proof:* Y = |α⊥⟩⟨α⊥| ⊗ I + I ⊗ |β⊥⟩⟨β⊥| is PSD; every maximally
entangled |B⟩ has ⟨B|Y|B⟩ = 1/2 + 1/2 = 1, so tr Λ = tr(YΛ) ≤ tr(YÔ) =
s_A·1 + s_B·1 + c·tr Y = s_A + s_B + 4c. (Equivalently: the expectations of Ô − Λ in the
product states |α β⊥⟩, |α⊥ β⟩ and twice |α⊥ β⊥⟩ sum to s_A + s_B + 4c − tr Λ ≥ 0.)
The lemma is tight: α = β = |0⟩, s_A = s_B = s gives Λ = diag_Bell(c, c, c + s, c + s).

**Step 5 (summing over modes).** Σ_i s_A(i) = ‖U e_0‖² + ‖U e_1‖² = 2, Σ_i s_B(i) = 2,
Σ_i c_i = ⟨A|N_anc|A⟩ = k. Hence (k + 2) Σ_B p_B ≤ 2 + 2 + 4k, i.e.
p_avg ≤ (k + 1)/(k + 2). ∎

Reading: weight each detected photon equally ("a uniformly random photon of the pattern");
conditioned on that photon being in mode i, the four Bell states leave conditional states
with Gram matrix D_i, and unambiguous discrimination of four such states succeeds at most
s_A + s_B + 4c_i (in units of the conditioning weight). A detected signal photon is worth
at most half of its Bell information; an ancilla photon at most all of it.

**Tightness (numeric, both float paths).** The whole chain is an equality on the standard
BSM (Σ_B p_B = 2: true value = relaxation = row bound = 2) and on Grice (Σ_B p_B = 3:
true value = relaxation = row bound = 3). At k = 1 it is not tight: the first-moment
relaxation reaches 8/3 on the non-interfering scheme whose true total is 2 (the relaxation
thinks the idle ancilla photon reveals the Bell state; the remaining two photons cannot).

## Machine evidence (what is CERTIFIED, what is not)

| claim | statement (scope) | verifier | level |
|---|---|---|---|
| `P3.one_body_usd_lemma` | Step 4's lemma, all α, β, s_A, s_B, c, Λ | `sos_certificate` (core.py) | **CERTIFIED** (round 2: two PASS receipts) |
| `P3.k0_m4_p_avg_upper_bound` | k = 0, m = 4, **every** assignment: p_avg ≤ 1/2 | `p3_moment_bound` | **CERTIFIED** (two REVISE receipts, warnings only) |
| `P3.k1_m5_p_avg_upper_bound` | k = 1, m = 5, every assignment: p_avg ≤ 2/3, so min ≤ 2/3 | `p3_moment_bound` | **CERTIFIED** (round 2: two REVISE receipts, warnings only) |
| `P3.k1_m6_p_avg_upper_bound` | k = 1, m = 6, any single-photon ancilla, every assignment: p_avg ≤ 2/3 | `p3_moment_bound` | **CERTIFIED** (round 2 after the mixed-ancilla step: two REVISE receipts) |
| `P3.moment_bound_general_k` | the theorem for every k and m | none (paper proof above) | HEURISTIC until Lean |

Evidence files: `claims/evidence/p3_moment/{one_body_usd_lemma,k0_m4_p_avg_bound,k1_m5_p_avg_bound,k1_m6_p_avg_bound}.json`;
each opens with an `about` block stating the claim text verbatim, what is machine-checked,
and the written steps outside replay (W0–W6: the ancilla rotation at m = 6, U†U = I,
identified patterns Bell-diagonal, the transpose, rank-one rows, photon count, unit columns).

- **The lemma** is an exact SOS certificate over 47 real variables (α, β, s_A, s_B, c,
  λ_B, and W ∈ ℂ^{4×4} with Ô − Λ = WW†), 18 constraints, a 128-monomial Gram
  (`certificates/p3_moment.py`); `core.check_certificate` passes it in 0.3 s. The tests
  pin the caller's half of the contract (the constraints vanish on the intended variety,
  the projectors are the repo's Bell states, corruptions fail — including a product state
  in place of a Bell state, which breaks the identity because the lemma uses maximally
  mixed marginals).
- **The instances** go through the new pack verifier `p3_moment_bound`
  (`certificates/p3_moment_check.py`): it checks that the payload's lemma certificate is
  the canonical one and passes core.py, verifies the moment identity exactly at (k, m) —
  for every output mode and Bell pair, Σ_n n_i A_B Ā_{B'} = Σ_{j,l} U_ij Ū_il
  H_jl(U†U) as a polynomial identity for **all** complex U (Laplace expansion along row
  i and Cauchy–Binet for permanents), and Σ_{j,l} U_ij Ū_il H_jl(I) = ⟨B'|Ô_i|B⟩ — and
  that the claimed bound is at least (k + 1)/(k + 2). The amplitude polynomials are
  `poly.bell_amp_poly`, cross-validated against both engines on probabilities and on the
  cross terms A_B Ā_{B'} (through superposition inputs). At (k, m) = (1, 5): 80 identities,
  degree 6 in 50 real variables, 31 s; at (1, 6): 96 identities in 72 variables, 51 s. The
  glue (Steps 1, 2, 5 and the transpose/rank-one remarks) is the derivation the verifier's
  docstring states and each evidence file discloses; it is short and is the formalization
  target.
- **Not certified:** the general-(k, m) statement. Its proof is the five steps above;
  instances certify it at (0, 4), (1, 5) and (1, 6). k = 2 instances need 4-photon patterns
  and a general two-photon ancilla (polynomial in the ancilla amplitudes) — the next exact
  extension.
- **Review history.** Round 1 (two Fable samples per claim) BLOCKed the lemma: my statement
  had added "the bound is attained at a = b = |0⟩, s_A = s_B", which the certificate does not
  establish and which is false for negative s_A = s_B under the statement's own quantifiers;
  it also BLOCKed the k = 1, m = 5 instance, capped by the then-CONJECTURED, CHALLENGED
  lemma. Both rounds also flagged that the review bundle presented a pack verifier as
  "not a command verifier declared in this repository" with an `argv=None` replay note — a
  harness gap now fixed (`claims/review.py`, `claims/promote.py`). The statements were
  corrected (the lemma's text is now the certificate's `statement` field verbatim; the
  instances define "unambiguous assignment" and the rail convention), the evidence files
  gained their disclosures, and round 2 PASSed the lemma (both samples re-derived the 18
  constraints by hand). The instance claims then drew REVISE receipts only (no blocking
  finding): k = 1, m = 5 in its round 2, k = 0, m = 4 in its first round. One k = 1, m = 6
  warning was substantive — "any single-photon ancilla state" admits mixed states that the
  rotation step W0 does not cover — so that evidence gained W0' (convexity: an assignment
  unambiguous for a mixture is unambiguous for each pure component) and went back for
  review before promotion. Two presentation warnings recurred: the first PASS entries came
  from a verifier binary re-stamped before promotion, and "80 identities" counted cases;
  `p3_moment_bound` is now v1.1 and its detail states the count. All receipts stay in
  `receipts/`.

## Feasibility record (the direct SOS route and the moment hierarchy)

**Direct SOS at m = 5, k = 1 (the strategist's route) — infeasible as stated.**
U ∈ U(5): 50 real variables (19 after the 6-dimensional phase gauge: output phases, the
ancilla column's phase, the common signal phase). The objective p_B = Σ_{f(n)=B}|perm₃|²
has degree 6, so the Gram basis at degree 3 has C(53, 3) = 23,426 monomials (C(28, 3) =
3,276 even on the real orthogonal slice); M20c's k = 0 SDP at 561 monomials already did
not converge in SCS. The assignment has 30 patterns that can identify (the 5 triple-bunched
ones never do: their T(n) has rank one), so per-branch certificates face 5^30 ≈ 9 × 10^20
branches (≈ 3 × 10^17 after S_5 × S_4 symmetry). The moment relaxation avoids both: it is
assignment-free and its lemma has degree ≤ 5 in 47 variables.

**Moment relaxations, numeric (cvxpy/Clarabel, HEURISTIC).** Level 1 is Λ_i ⪯ D_i per mode;
level 2 adds Λ_ij ⪯ D_ij = Σ_n n_i(n_j − δ_ij) G(n) with Σ_j Λ_ij = (k + 1) Λ_i. One
level-2 solve at m = 5 is 22 ms.

| scheme | true Σ_B p_B / min | level 1 sum / min | level 2 sum / min |
|---|---|---|---|
| standard BSM + idle ancilla (k = 1) | 2 / 0 | 8/3 / 1/3 | 2.000 / 0.000 |
| balanced witness (k = 1) | 1 / 1/4 | 1.695 / 0.378 | 1.006 / 0.2500 |
| random U(5) (three draws) | 0 / 0 | 1.59–1.61 / 0.37–0.39 | 0.25–0.36 / 0.05–0.08 |

- **Target A (min ≤ 1/4) is out of reach of level 2.** Projected ascent of the level-2
  min relaxation over U(5) (13 starts, 2 step sizes, 150 iterations each, 3.5 min)
  reached 0.2780 > 1/4 at a non-degenerate point; level 2 therefore cannot certify
  max min = 1/4. Level 3 is the exact problem (for k = 1 the third moments are the
  pattern probabilities).
- **Level 2 for the conjecture p_avg ≤ 1/2 at k = 1: inconclusive.** From random starts
  the level-2 sum relaxation plateaued at 1.39 (12 starts); from the non-interfering scheme
  (value exactly 2) every perturbation, down to noise 0.01, dropped it to ≈ 1.1 and
  ascent did not return above 1.36 (16 runs); an ε-regularised ascent (D + εI, ε annealed
  0.1 → 0, 11 starts) reached 1.42. The relaxation is only upper semicontinuous (maxdiag
  jumps on rank-deficient D_ij, e.g. the rank-one k = 0 coincidence terms), so its maximum
  sits on exactly structured U that local search cannot find. Whether level 2 proves 1/2 is
  open; a dual in closed form (the level-1 lemma's analogue, see Next steps) is the way to
  settle it, not more ascent. The ε-regularised min ascent ends at 0.273–0.278 from 8 of 11
  starts (best 0.2778, numerically 5/18), confirming that level 2 stops above 1/4.

## Targets of the brief

- **A (min ≤ 1/4 at k = 1):** not reached. Certified: min ≤ p_avg ≤ 2/3 at m = 5 (and the
  general bound). Level 2 provably cannot give 1/4 (above); the frontier conjecture
  p₍₁₎ + p₍₂₎ ≤ 1/2 stays HEURISTIC.
- **B (p_avg ≤ c < 1 at k = 1, m = 5):** **c = 2/3, CERTIFIED** (beats the 3/4 milestone),
  and the paper proof gives it for every m.
- **C (reduction lemma):** done exactly, as a test rather than a claim
  (`tests/test_p3_poly_k1.py::test_non_interfering_ancilla_reduces_to_k0_exactly`). At
  m = 5 with the ancilla column e_r (row r is then e_4^T by unitarity), every k = 1 Bell
  amplitude equals, as an exact polynomial after substitution, the k = 0 amplitude of the
  4 × 4 block on the other modes at the pattern with the mode-r photon removed, and every
  pattern with n_r ≠ 1 has amplitude 0 — for each r. Such a scheme has exactly the k = 0
  success vector, so min = 0 (`p3_at_most_three`, FORMALIZED) and p_avg ≤ 1/2
  (`P3.k0_m4_p_avg_upper_bound`, every assignment). The average half is anyway subsumed
  by the theorem's k = 1 bound only up to 2/3; the reduction gives the sharp 1/2 for this
  subclass.

## Next steps

1. **Lean.** Not started here (no mathlib build in this worktree). The first target is the
   k = 1, m = 5 instance on the existing definitions of `P3K1Witness.lean` (`perm3`,
   `rawAmp3`, `BellLabel`), stated for an arbitrary assignment:

   ```lean
   /-- An unambiguous assignment of the three-photon patterns (sorted row triples). -/
   structure Assign3 (V : Matrix (Fin 5) (Fin 5) ℂ) where
     f : Fin 5 → Fin 5 → Fin 5 → Option BellLabel
     unamb : ∀ i j k μ, f i j k = some μ → ∀ ν, ν ≠ μ → rawAmp3 V i j k ν = 0

   /-- Success of Bell state μ: Σ over sorted triples i ≤ j ≤ k assigned to μ of
   ‖rawAmp3 V i j k μ‖² / (2 · multFact i j k)  (multFact = product of multiplicity factorials). -/
   def succ3 (V) (A : Assign3 V) (μ : BellLabel) : ℝ := …

   theorem p3_k1_m5_avg_le_two_thirds (V : Matrix (Fin 5) (Fin 5) ℂ)
       (hV : V ∈ Matrix.unitaryGroup (Fin 5) ℂ) (A : Assign3 V) :
       (∑ μ, succ3 V A μ) / 4 ≤ 2 / 3
   ```

   Proof plan in four lemmas: (i) the one-body lemma on `Matrix (Fin 4) (Fin 4) ℂ`
   (expectations in three product vectors; mathlib's `PosSemidef`); (ii) for each output
   mode i, Σ_patterns n_i · rawAmp3 μ · conj(rawAmp3 ν)/(2·multFact) = the one-body matrix
   entry, from unitarity — 80 polynomial identities modulo `star V * V = 1`, best proved
   structurally (expansion of `perm3` along row i plus the 2 × 2 Cauchy–Binet identity) rather
   than by brute `ring`; (iii) identified patterns give Bell-diagonal rank-one terms
   (`Assign3.unamb`); (iv) the sum over modes with column norms. The general-(k, m)
   theorem needs a Fock-space permanent library and is the second target.
2. **k = 2 instance** (Grice optimality at, e.g., m = 6, certified): extend the checker to
   4-photon patterns and a general two-photon ancilla.
3. **k = 1 conjecture 1/2 and min ≤ 1/4:** a closed-form level-2 dual, or level 2 plus
   per-pattern structure (the rank-one triple-bunched and (2,1) patterns). The level-2 dual
   has, per output mode i, a multiplier ν_i ∈ ℝ⁴ on the consistency Σ_j Λ_ij = 2Λ_i, with
   PSD Y_i, Y_ij subject to diag(Y_i) ≥ 1/3 − 2ν_i and diag(Y_ij) ≥ ν_i, and value
   Σ_i tr(Y_i D_i) + Σ_ij tr(Y_ij D_ij). Level 1 is ν = 0. On the non-interfering scheme
   (ancilla in mode 5) the choice ν_5 = 1/6, Y_5 = 0, Y_5j = (1/6)·(the lemma's dual for
   row j) moves the ancilla row's cost from 4/3 to 2/3 and the bound from 8/3 to exactly 2:
   the slack of level 1 is the ancilla photon "seen first". A closed-form ν_i(row) that does
   this for every U — at k = 1 D_ij = S(v_i ξ_j + v_j ξ_i, v_i η_j + v_j η_i) + m_ij m_ij†,
   the one-body form of a virtual row plus the rank-one k = 0 coincidence term — is the
   concrete next target for P3(i).

## Accounting

No strategist or formalizer calls. Model spend is the review receipts only (Fable, max
effort, two samples per review, `receipts/P3.*.20261027.*`): $32.08 over 14 samples (seven reviews: lemma ×2, k = 1 m = 5 ×2, k = 0 m = 4 ×1, k = 1 m = 6 ×2). Compute: the exact
(1, 5) expansion is 31 s, (1, 6) 51 s; the numeric probes ran ≈ 25 CPU-minutes in scratch
scripts (cvxpy/Clarabel). Wall time ≈ 2 h 55 min.

Open review warnings carried by the CERTIFIED instance claims (non-blocking; recorded in
their notes): the earliest PASS entries were made by a p3_moment_bound binary that was
re-stamped before promotion (the verifier is now v1.1, whose detail states its count:
cases × two identities); p_B is defined in the evidence's `setting`, not in the statement
text (the problem's own definition); W6's min-clause is idle at k = 0.

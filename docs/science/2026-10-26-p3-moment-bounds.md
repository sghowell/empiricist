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

| claim | statement (scope) | verifier | evidence |
|---|---|---|---|
| `P3.one_body_usd_lemma` | Step 4's lemma, all α, β, s_A, s_B, c, Λ | `sos_certificate` (core.py) | `claims/evidence/p3_moment/one_body_usd_lemma.json` |
| `P3.k0_m4_p_avg_upper_bound` | k = 0, m = 4, **every** assignment: p_avg ≤ 1/2 | `p3_moment_bound` | `claims/evidence/p3_moment/k0_m4_p_avg_bound.json` |
| `P3.k1_m5_p_avg_upper_bound` | k = 1, m = 5, every assignment: p_avg ≤ 2/3 (so min ≤ 2/3) | `p3_moment_bound` | `claims/evidence/p3_moment/k1_m5_p_avg_bound.json` |
| `P3.moment_bound_general_k` | the theorem for every k and m | none (paper proof above) | HEURISTIC until Lean |

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
  degree 6 in 50 real variables, 31 s. The glue (Steps 1, 2, 5) is the derivation the
  verifier's docstring states; it is short and is the formalization target.
- **Not certified:** the general-(k, m) statement. Its proof is the five steps above;
  instances certify it at (0, 4) and (1, 5). k = 2 instances need 4-photon patterns and a
  general two-photon ancilla (polynomial in the ancilla amplitudes) — the next exact
  extension.

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
  ascent did not return above 1.36 (16 runs). The relaxation is only upper semicontinuous
  (maxdiag jumps on rank-deficient D_ij, e.g. the rank-one k = 0 coincidence terms), so
  its maximum sits on exactly structured U that local search cannot find. Whether level 2
  proves 1/2 is open; a dual in closed form (the level-1 lemma's analogue) is the way to
  settle it, not more ascent.

## Targets of the brief

- **A (min ≤ 1/4 at k = 1):** not reached. Certified: min ≤ p_avg ≤ 2/3 at m = 5 (and the
  general bound). Level 2 provably cannot give 1/4 (above); the frontier conjecture
  p₍₁₎ + p₍₂₎ ≤ 1/2 stays HEURISTIC.
- **B (p_avg ≤ c < 1 at k = 1, m = 5):** **c = 2/3, CERTIFIED** (beats the 3/4 milestone),
  and the paper proof gives it for every m.
- **C (reduction lemma):** subsumed for the average (the theorem covers interfering and
  non-interfering ancillas alike). For a non-interfering ancilla at m = 5 (column 5 = e_r),
  the success vector equals that of the k = 0 scheme on the other four modes, so
  min = 0 (`p3_at_most_three`) and p_avg ≤ 1/2 (`P3.k0_m4_p_avg_upper_bound`, now for every
  assignment); the identity itself was not separately certified.

## Next steps

1. **Lean.** Formalize the theorem for general k and m: the moment identity is the
   photon-number expectation Γ(U)†N_iΓ(U) = Σ Ū_ij U_il a_j†a_l (or, at fixed small m,
   a `ring` identity over the existing `perm3` definitions); the lemma is 4 × 4 linear
   algebra (three expectation values); Steps 1, 2, 5 are finite sums. Not started here
   (no mathlib build in this worktree).
2. **k = 2 instance** (Grice optimality at, e.g., m = 6, certified): extend the checker to
   4-photon patterns and a general two-photon ancilla.
3. **k = 1 conjecture 1/2 and min ≤ 1/4:** a closed-form level-2 dual, or level 2 plus
   per-pattern structure (the rank-one triple-bunched and (2,1) patterns).

## Accounting

No strategist or formalizer calls. Model spend: the review receipts for the CERTIFIED
promotions (recorded in the receipts' provenance; total in the PR). Compute: the exact
(1, 5) expansion is 31 s; the numeric probes ran ≈ 15 CPU-minutes in scratch scripts.

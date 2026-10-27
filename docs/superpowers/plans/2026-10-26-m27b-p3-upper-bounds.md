# M27b: P3 upper bounds at k = 1 — the photon-number moment hierarchy

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Machine-checked UPPER bounds for Problem 3 with one ancilla photon. Targets, in the
brief's priority order: (A) worst case max min_B p_B ≤ 1/4 at k = 1 (m = 5 first), via the
frontier p₍₁₎ + p₍₂₎ ≤ 1/2 or directly; (B) an explicit certified p_avg ≤ c < 1 at k = 1,
m = 5 (3/4 is the strategist's first milestone, 1/2 the conjecture); (C) the reduction lemma
"a non-interfering ancilla reduces to k = 0". Every bound states its exact scope (m, k, metric,
assignment class).

**Architecture — why not the direct SOS:** the strategist's route is a rational SOS certificate
on the permanental variety at m = 5. Two size facts kill it as stated (Task 1 records them):
the objective p_B = Σ_{f(n)=B} |perm₃|² has degree 6 in the 50 real entries of U, so the Gram
basis at degree 3 has C(53, 3) = 23,426 monomials before symmetry reduction (the k = 0
problem at 561 monomials already defeated SCS in M20c); and the assignment f ranges over
5³⁰ maps on the 30 patterns that can identify, so per-branch certificates cannot be enumerated.
The plan replaces it with an assignment-free relaxation that is found in the feasibility pass:
the **photon-number moment hierarchy**. For an output mode i let
D_i[B, B'] = Σ_n n_i z_B(n) z̄_{B'}(n) = ⟨out_{B'}|N_i|out_B⟩ (the Gram matrix of the
conditional states b_i|out_B⟩). Identified patterns contribute Bell-diagonal rank-one terms,
so the identified part Λ_i is a Bell-diagonal matrix with 0 ⪯ Λ_i ⪯ D_i, and
(k + 2)·Σ_B p_B = Σ_i tr Λ_i for every unambiguous assignment at once. One body: D_i depends
on row i only, D_i = s_A P_α ⊗ I + s_B I ⊗ P_β + c_i I (two rank-one qubit terms plus the
ancilla's photon number), and a three-line dual (Y = P_{α⊥} ⊗ I + I ⊗ P_{β⊥}) gives
tr Λ_i ≤ s_A + s_B + 4c_i. Summing over rows: **p_avg ≤ (k + 1)/(k + 2)** for every k, m,
interferometer, k-photon ancilla and assignment — 1/2 at k = 0 (Calsamiglia–Lütkenhaus),
2/3 at k = 1, 3/4 at k = 2 (Grice is tight). Level 2 (pairs, Σ_n n_i(n_j − δ_ij) G(n)) is
the next rung for A and for the k = 1 conjecture 1/2.

**Trust boundary (locked):** numeric relaxations and optimizer values are HEURISTIC. What can
reach CERTIFIED: (i) the one-body USD lemma as an exact SOS certificate checked by
`certificates/core.py` (`sos_certificate`, general statement over all α, β, s_A, s_B, c and
all Bell-diagonal Λ ⪯ D); (ii) the moment identity D_i = S_i + c_i I at (k, m) = (1, 5) as an
exact polynomial identity with explicit unitarity multipliers, also checked by `core.py`
(zero Gram); the glue (identified ⇒ Bell-diagonal; Σ_i n_i = k + 2; column norms) is the
paper proof and stays at PROVED_DRAFT-level until Lean. The general theorem is the Lean
target (FORMALIZED later, not in this worktree).

**Tech stack:** Python ≥ 3.11, `fractions` (exact side), numpy + cvxpy/Clarabel (search side,
`uv sync --group certs`), the claims CLI.

**Spec:** `docs/open_problems_ftfbqc.md` Problem 3; `docs/science/2026-09-05-p3-min-metric-landscape.md`;
the strategist notes in `docs/science/2026-09-05-p3-strategist/`; M20c / M21b plans.

## Global Constraints

- `certificates/core.py` stays untouched and stdlib-only; it is the trust boundary.
- Every polynomial that feeds a certificate is cross-validated against BOTH float engines
  (`engine_permanent`, `engine_fock`) on random unitaries (the F3 discipline of M20c).
- TDD for every verifier-facing module and for certificate builders; goldens pin PASS and
  must-fail cases.
- Statements name their metric (min or avg), k, m, and assignment class ("every unambiguous
  assignment" or a named one).
- No Lean build in this worktree (mathlib rebuild cost); Lean statements are drafted as text.
- Branch `feat/m27b-p3-upper-bounds`, PR, coordinator merges. Stage files explicitly. No AI
  attribution in commit messages. `runs/` stays local.

---

### Task 0: this plan

- [x] Commit `M27b: plan`.

### Task 1: feasibility and sizing (recorded, no ledger effect)

- Direct SOS at m = 5, k = 1: variables (50 real; 19 after the 6-dim phase gauge), objective
  degree, Gram basis sizes at degrees 2–3 with and without the real restriction, constraint
  counts (25 unitarity, 6 real per assigned pattern per other state), the branch count.
- Moment relaxations, numeric (cvxpy/Clarabel, scratch scripts): level 1 (one body) and level 2
  (pairs with Σ_j Λ_ij = (k + 1) Λ_i), values on the standard BSM, Grice, the k = 1 witnesses,
  random U; per-solve timings; projected-ascent maximisation over U(5) of the level-2 sum and
  min relaxations.
- [x] Record the table in the science note (Task 6) and in this plan's outcome.

### Task 2: exact k ≥ 1 amplitudes (`domain/p3/poly.py`)

**Files:** `src/empiricist/domain/p3/poly.py`, `tests/test_p3_poly.py`.

- `amp_poly(m, bell_label, pattern, ancilla_cols)` → the complex amplitude
  ⟨n|out_B⟩·√(n!)·√2 as a (re, im) pair of exact `Poly`s for a single-photon ancilla in a
  given input column (k = 1), alongside the existing k = 0 `prob_poly` (whose scope guard is
  unchanged).
- Tests: evaluated at random unitaries, |amp|²/(2·n!) reproduces both engines'
  distributions to 1e-10 for every 3-photon pattern at m = 5 and m = 6.
- [x] Commit `M27b: exact k=1 amplitudes, engine cross-validated`.

### Task 3: the one-body USD lemma certificate (`certificates/p3_moment.py`)

**Files:** `src/empiricist/certificates/p3_moment.py`, `certificates/data/p3_one_body_usd.json`,
`tests/test_p3_moment.py`.

- Variables: α, β ∈ ℂ² (8 real), s_A, s_B, c, λ_B (4), W ∈ ℂ^{4×4} (32 real).
  Constraints: |α|² = 1, |β|² = 1, and the 16 real entries of
  s_A αα†⊗I + s_B I⊗ββ† + cI − Σ_B λ_B|B⟩⟨B| − WW† = 0 (Bell basis explicit).
  Objective Σ_B λ_B − s_A − s_B − 4c, bound 0. Multipliers from Y = α⊥α⊥†⊗I + I⊗β⊥β⊥†
  (α⊥ = (−ᾱ₁, ᾱ₀), polynomial), SOS part ‖(α⊥†⊗I)W‖² + ‖(I⊗β⊥†)W‖² as an explicit Gram on the
  basis {α_a W_rc, β_b W_rc}.
- Tests: the certificate PASSes `check_certificate`; a numeric spot check that the constraint
  polynomials vanish exactly when D − Λ = WW† is built from random data; must-fail
  mutations (bound coefficient 4c → 3c, a dropped constraint, a Bell sign flip) are rejected.
- [x] Commit `M27b: exact SOS certificate for the one-body USD lemma`.

### Task 4: the moment identity at (k, m) = (1, 5)

- For each output mode i and Bell pair (B, B'), Σ_n n_i z_B z̄_{B'} − D_i[B, B'] lies in the
  unitarity ideal, with multipliers built from Γ(U)†Γ(U) = Γ(U†U) on two-photon states
  (expansion along row i, then G = I + E). Emitted as zero-Gram `SOSCertificate`s (one per real
  and imaginary part) and checked by `core.py`; the target polynomials are the Task 2 ones.
- Tests: the D_i polynomials match `S_i + |v_i|² I` built from row data; certificates PASS;
  a mutated identity (ancilla term dropped) FAILs.
- [x] Commit `M27b: moment identity at k=1, m=5 certified exactly`.

### Task 5: level 2 and the min metric (targets A, B → 1/2)

- Numeric level-2 relaxation maximised over U(5) for both metrics (scratch, background);
  if a value above the conjecture appears, the relaxation is too weak at level 2 and the
  finding is recorded; if it plateaus at 2 (sum) or 1/4 (min), extract duals and look for
  closed forms (the level-1 lemma's analogue).
- [x] Record outcome; mint HEURISTIC claims only where the evidence is numeric.

### Task 6: claims, note, PR

- Claims (problem P3): the one-body lemma (CERTIFIED via `sos_certificate`, receipt), the
  moment identity instance (CERTIFIED), the k = 1, m = 5 instance and the general theorem
  (level by evidence; the general statement waits for Lean), the reduction lemma (C).
- Science note `docs/science/2026-10-26-p3-moment-bounds.md`: theorem, proof, tightness
  (standard BSM, Grice), the feasibility table, what failed, the Lean target.
- `claims check --min-claims 1` green; ruff; tests; PR via `env -u GH_TOKEN gh pr create`.
- [ ] Commit, push, PR.

## Honest ceiling

The certified pieces are the lemma (general) and the identity (one instance); the glue that
turns them into "p_avg ≤ (k + 1)/(k + 2) for every k and m" is a paper proof until the Lean
formalization lands. The bound is tight at k = 0 and k = 2 but not at k = 1 (conjecture 1/2);
the min-metric target 1/4 needs more than level 2 of the hierarchy if Task 5 finds the level-2
relaxation exceeding 1/4.

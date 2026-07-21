# M20c: P3 Certificate Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert P3 search-resistance into machine-checkable upper-bound certificates: an
exact polynomialization of scheme probabilities, an exact-rational SOS certificate CHECKER
(the trust side), a numerical SDP solve+rationalize pipeline (the search side), and a golden
certificate reproducing a known bound.

**Architecture — the trust boundary (locked):** finding a certificate may use any heavy
numerical machinery (cvxpy/SCS, floats); *verifying* one uses exact rational arithmetic only
(`fractions.Fraction`), zero solver dependencies, and is the only thing the ledger trusts.
A certificate is a data object (polynomial identity + rational PSD Gram matrices); the
checker validates (a) the algebraic identity exactly and (b) PSD exactly via rational
LDL^T. This mirrors the two-engine discipline: the solver proposes, the checker disposes —
and the checker is the future Lean-verification target (rational linear algebra).

**Two tracks (Track A is a campaign action, not in this plan's tasks):**
- **Track A (run first, cheap):** Fable free-form strategist calls on the two wave-1
  patterns — "prove: every unambiguous passive k=0 dual-rail scheme has min_B p_B = 0" and
  the k=2 floor analog. A direct proof routes to the proven M18 Lean loop and skips SOS
  entirely for those claims. Outcome feeds Track B's target selection.
- **Track B (this plan):** the SOS pipeline, needed regardless for k=1-type bounds.

**Tech stack:** Python ≥3.11; `fractions` (stdlib) for all exact arithmetic; new
dev-quarantined dependency `cvxpy` + `scs` for the SOLVE side only (design decision D3).

**Design decisions (locked):**
1. **Exactness lives in ℚ.** Scheme probabilities are polynomials with rational
   coefficients in the real/imag parts of the interferometer unitary's entries (dual-rail
   Bell inputs have 1/√2 amplitudes — handled by working with √2·amplitude, keeping
   everything in ℚ; document the scaling convention in poly.py's docstring).
2. **The polynomial generator is engine-cross-validated** (the F3 discipline): evaluated at
   random unitaries it must reproduce both engines' distributions to 1e-10. A generator bug
   would silently produce vacuous certificates; this check is its warrant.
3. **Solver quarantine:** `cvxpy`/`scs` are imported ONLY inside `certificates/solve.py`;
   the checker module imports nothing beyond stdlib. CI/fast-suite must pass with cvxpy
   absent (solve tests skip if the import fails; checker tests never skip).
4. **Golden = a known bound, D4-style.** The pipeline's acceptance is reproducing a known
   result as an exact certificate at the smallest feasible size — target: the
   Calsamiglia–Lütkenhaus-type bound `p_avg ≤ 1/2` for k=0 unambiguous schemes, in the
   REAL-orthogonal restricted class first if full U(4) sizing is impractical (an honest,
   stated restriction; the class is part of the certificate statement). Task 3 measures
   sizes and gates the choice.

**File structure:**
- Create: `src/empiricist/domain/p3/poly.py` — exact polynomialization
- Create: `src/empiricist/certificates/__init__.py`, `src/empiricist/certificates/core.py`
  — Polynomial/Certificate data model + the EXACT CHECKER
- Create: `src/empiricist/certificates/solve.py` — SDP assembly + solve + rationalization
  (quarantined deps)
- Test: `tests/test_p3_poly.py`, `tests/test_certificates_core.py`,
  `tests/test_certificates_solve.py` (skippable), `tests/test_p3_certificate_golden.py`

---

### Task 1: Exact polynomialization (`domain/p3/poly.py`)

**Files:** Create `src/empiricist/domain/p3/poly.py`; Test `tests/test_p3_poly.py`

Variables: for an m-mode scheme, `x[i][j]` and `y[i][j]` are the real/imag parts of
`U[i][j]`. A monomial is a sorted tuple of variable indices; a polynomial is
`dict[monomial, Fraction]`. For each detection pattern `n` and Bell state `B`, produce the
polynomial `P_{n,B}` equal to `2·Pr[n|B]` (the ×2 clears the Bell 1/√2² — document).
Construction: amplitude = sum over the Bell state's two Fock components of
`±(1/√2)·Per(U[S,T])/√(∏s!∏t!)`; expand the permanent symbolically over the variable
entries; multiply by conjugate for the probability; the √-factorial normalizations for
multi-photon patterns keep coefficients rational only when `∏s_i!∏t_j!` is a perfect
square times powers of 2 — handle by producing `P = 2·(∏s!)·Pr[n|B]`-style scalings per
pattern, RECORDING the exact rational scale factor alongside each polynomial (the checker
consumes (poly, scale) pairs; scales are exact Fractions).

- [ ] **Step 1 (tests first):** `poly_for(m, bell_label, pattern)` returns (poly, scale)
      such that evaluating poly at the STANDARD BSM's unitary entries (√2-scaled to stay
      rational where possible — evaluate numerically with floats here) reproduces
      `PermanentEngine`'s `Pr[pattern|B]` to 1e-10, for every pattern and all four B, for
      (a) the standard BSM and (b) 20 random 4-mode meshes (build U via `mesh_unitary`,
      evaluate the polynomial at its entries, compare to the engine). Also a pure-exactness
      pin: all coefficients are `Fraction`s.
- [ ] **Step 2:** implement; the permanent expansion for 2-photon patterns is a 2×2
      permanent (u_a·u_d + u_b·u_c) — keep the general (S,T)-multiset construction but it
      only needs to be correct for the sizes the tests exercise (2 photons; assert
      NotImplementedError beyond 3 photons for now, documented).
- [ ] **Step 3:** tests + `uv run ruff check src tests`; commit
      `feat(p3): exact polynomialization of scheme probabilities`.

### Task 2: Certificate model + EXACT checker (`certificates/core.py`)

**Files:** Create the package + `core.py`; Test `tests/test_certificates_core.py`

Data model (all Fractions):
```python
@dataclass(frozen=True)
class SOSCertificate:
    statement: str                     # human-readable bound claim
    variables: tuple[str, ...]         # variable names, fixed order
    objective: Poly                    # the polynomial being bounded
    bound: Fraction                    # claimed: objective <= bound ON the variety
    constraints: tuple[Poly, ...]      # g_i = 0 on the variety (e.g. unitarity rows)
    multipliers: tuple[Poly, ...]      # lambda_i, one per constraint
    gram_basis: tuple[Monomial, ...]   # monomial basis b for the SOS part
    gram: tuple[tuple[Fraction, ...], ...]  # Q PSD: SOS = b^T Q b
```
The checker verifies EXACTLY (no floats anywhere):
1. **Identity:** `bound − objective − Σ multipliers[i]·constraints[i] == b^T·Q·b` as
   polynomials (expand both sides over ℚ; dict equality).
2. **PSD:** rational LDL^T of Q with symmetric pivoting: all pivots ≥ 0 and the
   factorization consumes the whole matrix (semidefinite allowed). Implement LDL^T over
   Fraction from scratch (no numpy in this module).
Checker returns a verdict object (PASS/FAIL + which check failed); NEVER raises on
malformed certificates (the P3 verify discipline).

- [ ] **Step 1 (tests first):** hand-built tiny certificates: (a) `x² ≤ 1` on the variety
      `x² − 1 = 0`... use the true toy: objective `x`, bound 1, constraint `x²−1=0`,
      certificate `1 − x = ½·(x−1)² − ½·(x²−1)` → multipliers=(−½,), Gram=[[½]] over
      basis ((x−1) as expressed via monomials {1, x}: Q = ½·[[1,−1],[−1,1]]) — CHECK the
      identity by hand when writing the test; (b) a WRONG Gram (not PSD) → FAIL(psd);
      (c) a broken identity → FAIL(identity); (d) garbage shapes → FAIL, never raise.
- [ ] **Step 2:** implement (polynomial arithmetic helpers shared with poly.py — put the
      Poly type in certificates/core.py and have domain/p3/poly.py import it; core must
      not import domain).
- [ ] **Step 3:** tests + ruff; commit `feat(certificates): exact SOS certificate checker`.

### Task 3: SDP solve + rationalization (`certificates/solve.py`)

**Files:** Create `solve.py`; Test `tests/test_certificates_solve.py` (module skips
cleanly if cvxpy/scs missing)

- [ ] **Step 1:** add `cvxpy>=1.4` and `scs>=3.2` to pyproject `[dependency-groups]` under
      a new `certs = [...]` group (NOT main dependencies — document install:
      `uv sync --group certs`).
- [ ] **Step 2 (tests first, `pytest.importorskip("cvxpy")`):** on the toy problem from
      Task 2 (bound `x` subject to `x²=1`), `solve_sos(objective, constraints, degree=2)`
      returns a numerical certificate with bound ≈ 1; `rationalize(cert_num, denominator_limit)`
      rounds Gram+multipliers to Fractions and REPAIRS the identity (solve the linear
      system for the affine coefficients exactly — the standard trick: keep Gram rational,
      recompute the multiplier polynomials by exact linear solve so the identity holds
      exactly; if repair is infeasible, return None) such that the Task-2 checker PASSES it.
- [ ] **Step 3:** implement: standard moment/SOS assembly (monomial basis up to degree d,
      Gram PSD variable, equality of polynomial coefficients as linear constraints,
      minimize the bound). Keep it generic over the Poly type.
- [ ] **Step 4:** tests + ruff (fast suite must pass with the certs group NOT installed —
      verify by running the checker tests in isolation); commit
      `feat(certificates): SDP solve + exact rationalization (quarantined deps)`.

### Task 4: The golden certificate

**Files:** Test `tests/test_p3_certificate_golden.py`; possibly
`src/empiricist/certificates/p3_targets.py` (assembling P3 objectives/constraints from
poly.py)

- [ ] **Step 1:** assemble the k=0, m=4 problem: objective = the p_avg polynomial for a
      FIXED natural assignment class (start with: patterns partitioned by the derived rule
      applied symbolically is NOT polynomial — so certify the standard relaxation instead:
      `p_avg ≤ Σ_n max_B Pr[n|B]`-style bounds are also not polynomial; the honest
      certifiable statement at this stage is the ASSIGNMENT-FIXED bound: for the standard
      BSM's assignment structure, or summed-probability bounds like
      `Σ_B Pr[fixed pattern set_B | B] ≤ bound` subject to unitarity + the unambiguity
      EQUALITIES for that assignment). MEASURE the SDP size for: full U(4) (32 vars) vs
      real-orthogonal (16 vars) at Gram degree 2; report both.
- [ ] **Step 2 — DECISION GATE (report to the coordinator before proceeding):** if even
      the restricted class exceeds practical solve size (SDP > ~2000×2000), STOP and
      report the numbers; the coordinator re-scopes (options: smaller sub-statements,
      symmetry reduction, or deferring the golden to M20d with the infrastructure landed).
- [ ] **Step 3 (if gate passes):** produce the certificate, rationalize, CHECK with the
      exact checker, and pin it as the golden: the test stores the certificate as JSON
      (Fractions as strings) under `tests/goldens/p3_k0_certificate.json` and asserts the
      checker PASSES it and the bound ≤ the known value + 0 (exact).
- [ ] **Step 4:** commit `feat(p3): first exact certificate (golden)`.

---

## Acceptance
1. Fast suite green WITHOUT the certs dependency group installed (checker never skips;
   solve tests skip cleanly); with the group installed, all green.
2. The polynomial generator cross-validates against both engines (20 random meshes).
3. The checker rejects tampered certificates (identity break, PSD break) and never raises.
4. Task 4 either lands the golden certificate or produces the measured decision-gate
   report — both are acceptable milestone outcomes (the infrastructure is the deliverable;
   the golden may re-scope).

## Out of scope (M20d+)
- New-science certificates (k=0 p_min=0, k=2 floor, k=1 < 0.51) — they consume this
  pipeline next, informed by Track A's outcome.
- Lean verification of rational certificates (the checker is designed as its target).
- Symmetry reduction, sup-over-m mode bounds (P3(iv)).

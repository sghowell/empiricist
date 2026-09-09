# P8(b) — Stable bounces in a fixed covariant DHOST ladder

Status: formulation v1.1, 2026-09-04. The scoped linear P8(b) classification
is complete: all 16 rows are decided for each of M0 and M1. Minimal optional
supports are C or D for M0, and CD for M1. Evidence and the precise theorem
are in `notes/s3-classification.md` and `certificates/classification.json`.
P8(a), nonlinear stability, strong coupling and UV completion remain outside
this completed scope. The original P8-0 certificate retains its narrower
source-level meaning. The project-level preregistration is unchanged.

## 1. Scope and conventions

Work on P8(b); quantum-energy-inequality singularity theorems, P8(a), are
deferred. The target is an all-time, spatially flat FLRW bounce with healthy
linear principal part and propagation inside the physical metric light cone.
This does not by itself establish nonlinear stability, weak coupling, UV
completion, or observational viability.

Use cosmic time, never x = ln a as the evolution coordinate. The covariant
conventions follow An et al., arXiv:2501.09985v2 (A25): signature (+,−,−,−),
ds² = dt² − a²(t) dx², X = g^{μν}φ_,μ φ_,ν (no factor 1/2),
Y = g^{μν}χ_,μ χ_,ν. Units c = hbar = 1; M denotes the reduced Planck mass.
R^ρ_{σμν} = ∂_μ Γ^ρ_{νσ} − ∂_ν Γ^ρ_{μσ} + Γ^ρ_{μλ}Γ^λ_{νσ}
− Γ^ρ_{νλ}Γ^λ_{μσ}, R_{σν} = R^ρ_{σρν}; thus R = −6(Ḣ+2H²).
The Einstein term is −M²R/2. On a homogeneous clock X = φ̇² > 0.

P9(b) instead uses (−,+,+,+), X = φ̇²/2 and H-normalized alpha functions.
No P9 coefficient formula is imported without a checked dictionary. Reuse
the method (exact expansion, explicit boundary terms, independent arithmetic),
not its H > 0 restrictions. H = 0 must be an ordinary evaluation point.

## 2. Covariant object and finite group ladder

Freeze quadratic DHOST Ia in the physical matter frame:

    Sφ = ∫√−g [F(φ,X) + K(φ,X) □φ + F2(φ,X) R + Σ_i Ai(φ,X) Li],
    L1 = φ_;μν φ^;μν,                  L2 = (□φ)²,
    L3 = φ^,μ φ_;μν φ^,ν □φ,
    L4 = φ^,μ φ_;μν φ^;νρ φ_,ρ,       L5 = (φ^,μ φ_;μν φ^,ν)².

Independent functions: F, K, F2, A1, A3. A2, A4, A5 are fixed by the
Ia relations in A25 (3a–c), transcribed in `src/p8/matter.py`.
Their covariant velocity-Hessian degeneracy and the linear degree count are
checked in S1, including tilted slicing; this is not a formalization of the
nonlinear Dirac analysis. Require F2 − X A1 ≠ 0 on an open neighbourhood
of the trajectory.

Baseline: arbitrary F(φ,X) and F2(φ), with K = A1 = A3 = 0. The four
optional **function groups** are:

| Flag | Permission when enabled | Restriction when disabled |
|---|---|---|
| B | kinetic braiding K_X | K_X ≡ 0; absorb K(φ)□φ into F by IBP |
| C | X-dependent curvature coupling | F2_X ≡ 0 |
| A | A1 (and its dependent Ia completion) | A1 ≡ 0 |
| D | A3 (and its dependent Ia completion) | A3 ≡ 0 |

There are 16 inclusion-ordered rows. Enabled means *allowed*, not forced
nonzero; a witness belongs to its smallest supporting row. Off means an
identity on an open (φ,X) domain, **not merely zero on X = X(t)**. F2(φ)
is allowed in every row; this is group-minimality relative to that baseline,
not a basis-independent count of Lagrangian monomials. Do not quotient by
disformal transformations that change the prescribed matter coupling.
Horndeski's quartic locus has A1 = 2F2_X, A3 = 0 (and A4 = A5 = 0), so
it is a relation inside the ladder, not every point in row {A,C}.
Quintic Horndeski/cubic DHOST are outside this classification, although the
quadratic-action no-go template also applies when their reduction has that form.

Each row gets separate verdicts for two fixed matter sectors:

- M0: no extra scalar.
- M1: a free canonical, minimally metric-coupled scalar, Sχ = ∫√−g Y/2,
  with a³χ̇ = Cχ ≠ 0. Thus Y = Cχ²/a⁶ > 0 at every finite time.
  Backreaction is included, not an infinitesimal spectator approximation.

M1 does not allow φ-dependent kinetic factors or potentials. The published
A25 two-field model uses those interactions and is an **external regression**,
not a witness for M1. Any broader matter class needs a formulation revision.
The exact final witness choices are frozen in `notes/s2-rational-witnesses.md`.
They followed exploratory inverse reconstruction, not a preregistered blind
numerical search (revision log). A failed bounded search is never a whole-row
no-go; no search failure is used by this classification.

## 3. Acceptance contract for a witness

1. **Background and domain.** Smooth real covariant functions on an open
   neighbourhood of a solution for all t ∈ R; a(t) ≥ a_min > 0;
   finite curvature at every finite time; monotone scalar clock. At a
   designated bounce t_b, H(t_b) = 0 and Ḣ(t_b) > 0. Background metric and
   scalar equations must vanish exactly or have a validated solution enclosure.
   A reconstructed function along X(t) alone is not a covariant witness.
2. **Asymptotics.** State and prove both tails. Initial target: a grows
   as positive powers of |t|, H → 0, and the action tends to Einstein gravity
   plus healthy conventional scalars after explicitly nonsingular local field
   redefinitions at finite time. Require F_T,G_T → M² > 0. Quantitative
   derivative/remainder bounds, not plots, establish these statements.
   No ekpyrotic exponent is imposed on every candidate.
   The promoted witnesses provide uniform bounds on a covariant clock tube
   X in [9/10,11/10], including normalized coefficient remainders and their
   first two derivatives. This is not an assumed analytic X=0 scattering
   vacuum. The conventional tails also give the GR metric-gradient coupling
   Lambda -> M²; scalar clock reparametrization does not change that limit.
3. **Tensor principal part.** With S_T² = (1/8)∫a³[G_T ḣ² −
   F_T (∂h)²/a²], prove G_T ≥ F_T > 0 everywhere. In A25 conventions,
   G_T = −2F2 + 2XA1 and F_T = −2F2 are source formulas to rederive.
4. **Coupled scalar principal part.** In a regular variable chart,
   S_S² = ∫a³[v̇ᵀ Kv̇ − (∂v)ᵀG(∂v)/a² + lower-derivative terms].
   Prove K ≻ 0, G ≻ 0, K−G ⪰ 0. These are equivalent to positive kinetic
   energy and all generalized eigenvalues 0 < c_i² ≤ 1. Saturation at
   c² = 1 is allowed (M1 needs it); c² = 0 is not a healthy witness.
   For 2×2 matrices use both principal minors for positive definiteness;
   for K−G use both diagonal entries and its determinant for semidefiniteness.
5. **Crossings and constraints.** Record every constraint determinant and
   change of variables. Θ = 0 (gamma crossing) is not automatically a
   physical singularity. A quotient chart is valid only away from its poles.
   Prove a regular continuation, constraint rank/degree count and chart
   compatibility through every such point. Multiplying a matrix by Θ²
   and testing the limit does not discharge this obligation.
6. **Completeness.** Prove physical null affine length ∫a dt diverges at
   both ends, and timelike proper length ∫dt/sqrt(1+p²/a²) diverges for
   every conserved spatial momentum p. Our a_min bound suffices for both.
   Separately check ∫a F_T dt, the tensor-frame integral used in the no-go
   argument; it is not interchangeable with physical null completeness
   outside the stated tensor assumptions.
7. **Coverage and evidence.** Split R into two tails, compact intervals,
   and crossing neighbourhoods. Every part needs exact or outward-rounded
   evidence. Record denominator hypotheses and zeros explicitly. A finite
   sampling grid, a rescaled singular matrix, or a finite-time bounce alone
   earns no existence verdict.

UV positivity and a quantitative strong-coupling hierarchy are separate
later gates. Never call a linear witness UV-complete or controlled solely
because F_T stays positive. P9(b)'s conditional POS prior is not imported.

## 4. First benchmark and known-answer gates

Primary benchmark: A25 v2, §3, eqs. (28), (30), (36), (42)–(45), (50).
Use D = 2phi_dot(2F2_X−A1) from MRV20 (8a), not the inconsistent
A25 (10g); the exact discrepancy and three checks are in the source digest.
The subsequently discovered Sigma (47) inconsistency is also retained as
a negative control. Reconstruct F from the independently derived Sigma to
realize the source's target (50); do not assert agreement with printed (47).
Use their dimensionless time with φ̄ = t̄, X̄ = 1, and the **eq. (45)**
parameters τ = 10, ε = 5, w = 2, u = 1/10 (not the ε = 10 of Fig. 1).
First reproduce background, tensor coefficients, H = 0 limits, gamma
crossings, and the scalar principal coefficients for M0. Reconstruct F
from the background equations before claiming this as our checked solution.
Then use §4 only as a separate test of the general coupled-matrix interface.

The benchmark has F2 = −1/2 + g1(φ)(1−X) and A1 = a1(φ)(X−1).
Hence F_T = G_T = 1 on X = 1 although A1_X = a1 need not vanish.
It is not in the covariantly luminal restriction A1 ≡ 0. K = 0; its
candidate supporting row is {A,C,D}, subject to reconstruction/domain checks.

Other mandatory regressions before classification: KYY11 quadratic reduction;
Kobayashi16 no-go under its hypotheses; the strong-gravity asymptotic loophole;
CPS16's beyond-Horndeski escape; and the luminal-matter exceptional-locus test.
See `notes/literature-digest.md`. Known constructions validate our verifier;
their reproduction is not a new existence discovery.

## 5. Stages and next gate

| Stage | Deliverable | Current status |
|---|---|---|
| S0 | freeze scope, ladder, matter and benchmark; exact local identity anchor | complete 2026-09-04; P8-0, 29 tests |
| S1 | covariant → background/constraints/principal action; regular crossing charts | complete; P8-1 |
| S2 | replay no-go and known bounce/loophole regressions with explicit coverage | complete; corrected A25 regression, CPS16 dictionary and explicit strong-gravity countercheck |
| S3 | freeze exact candidates; certify M0/M1 witnesses and scoped exclusions | complete; P8-2.C, P8-2.D, P8-2.CD |
| S4 | row/minimality theorem and adversarial self-review; UV applicability audit | complete for the frozen linear classification; P8-3; no UV or strong-coupling verdict |

The chain replays with `python -m p8.verify_all --check` (see README for
the project environment). Applicable analytic lemmas are explicit written
proofs; the exact/interval certificates do not claim Lean FORMALIZED status.
No UV prior or quantitative coupling criterion was frozen, so those later
questions are not silently declared passed or used to discard ladder rows.

## Revision log

- 2026-09-04 v1: initial P8(b) scope. Separate M0/M1 from the interacting
  published benchmark; distinguish all-time geometry, crossing regularity,
  linear subluminality, and UV control. S0 certificate scope starts at a
  transcribed quadratic action, not the covariant theory.
- 2026-09-04 v1 source clarification during S0: retain A25 (10g) as a
  failing negative control; use MRV20 (8a) for D. No row verdict depends
  on an unrecorded correction to the published coefficient dictionary.
- 2026-09-04 v1.1 closure: document the independently checked Sigma (47)
  discrepancy and corrected external reconstruction. Freeze three rational
  witnesses after exploratory construction, explicitly not a blind
  preregistered search. Strong-gravity and CPS16 gates are mechanism-level
  covariant/dictionary regressions, not assertions of reproducing every
  published example. No class, matter sector, speed bound, or tensor-tail
  requirement is relaxed. Quantify the existing canonical-tube asymptotic
  requirement and preserve the separate UV/strong-coupling scope. Complete
  all 32 sector-row verdicts with an explicit regular-crossing no-go proof.

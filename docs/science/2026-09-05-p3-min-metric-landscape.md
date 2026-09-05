# P3 under its own metric: k = 0 gives exactly 0, one ancilla photon certifies at least 1/4

**Date:** 2026-09-05 · **Problem:** P3 (ancilla-boosted linear-optical Bell measurement) ·
**Method:** the M21b deterministic tier — `empiricist p3-optimize` (numpy batched-Ryser
evaluator, annealed unambiguity surrogate, scipy random-restart L-BFGS-B, both engines on every
optimum) with exact lifts checked by `P3ExactVerifier` in ℚ(i)(√2, √3) — `runs/p3-campaign`,
no model spend. Plan: `docs/superpowers/plans/2026-09-05-m21b-p3-deterministic-tier.md`.

## The metric clarification

Problem 3 defines a scheme's success as `p = min_B p_B`, the worst Bell state; the literature
(Calsamiglia–Lütkenhaus, Grice, Ewert–van Loock) quotes the average over the four states. The
two disagree sharply, and the harness now has machine-checked results for both:

| k | metric | value | status | evidence |
|---|---|---|---|---|
| 0 | min | exactly 0 | FORMALIZED | `p3_at_most_three` / `p3_min_support` (Lean 4, 2026-08-21): every U ∈ U(4) leaves a Bell state unidentified |
| 0 | avg | ≤ 1/2 (standard assignment) | CERTIFIED | exact SOS certificate (M20c), ingested 2026-09-05 (`d11c6b25…`) |
| 1 | min | ≥ 1/4 | CERTIFIED | exact witnesses at m = 5 (`ffbda750…`) and m = 6 (`204b4f97…`): vector (1/4, 1/4, 1/4, 1/4) |
| 1 | min | ≥ 1/6 (second family) | CERTIFIED | exact witnesses with vector (1, 1/6, 1/2, 2/9) up to relabelling (m = 7, `bbd741f5…`; also at m = 5, 6) |
| 1 | avg | 1/2 best found, never above | HEURISTIC | 130 restarts at m = 5, 6, 7: the optimizer saturates at exactly 1/2 and no design exceeds it |
| 2 | min | 1/2 (fixed mesh, Grice); 3/4 with one classical bit | VERIFIED (July) | `docs/science/2026-07-20-p3-certificates-and-proofs.md` |

So under the problem's literal definition a single ancilla photon is **not** useless: it
lifts p* from exactly 0 to at least 1/4. Under the literature's average it appears useless
(the p*(1) = 1/2 conjecture survives another 130 designs).

## The k = 1 landscape

Random-restart optimisation of the universal (Clements-style) mesh plus a single-photon
ancilla over the m − 4 extra modes, both metrics, τ annealed from 0.3 to 1e-5:

| m | target | restarts | best (float, two engines) | exact lifts found | plateaus |
|---|---|---|---|---|---|
| 5 | min | 60 | 1/4 | (1/4, 1/4, 1/4, 1/4); (1, 1/6, 1/2, 2/9) | 1/4 ×4, 1/6 ×8, 0.1524 ×1, 0 ×47 |
| 6 | min | 40 | 1/4 | (1/4, 1/4, 1/4, 1/4); (1, 1/6, 1/2, 2/9) | 1/4 ×1, 1/6 ×5, 1/8 ×2, 0 ×32 |
| 7 | min | 30 | 1/6 | (1, 1/6, 1/2, 2/9) | 1/6 ×5, 0 ×25 |
| 5 | avg | 60 | 1/2 | (1, 0, 0, 1) [trivial: ancilla idle] | 1/2 ×28, 17/36 ×9, lower ×23 |
| 6 | avg | 40 | 1/2 | (1, 1/6, 13/18, 0) [avg 17/36] | 1/2 best, never above |
| 7 | avg | 30 | 1/2 | (1, 2/9, 1/2, 1/6) [avg 17/36] | 1/2 best, never above |

Reading the table: the average-metric optima at 1/2 sit in continuous families (generic
members are off the exact lattice, so they do not lift) and every one of them leaves a Bell
state at 0; the best **all-four** designs have average 17/36 = 0.472. The min-metric optima
come in two exact families. Every lifted witness is an exact isometry whose exact
per-pattern distributions reproduce the engines' float distributions to 1e-6.

## The witnesses

- **Balanced 1/4 (m = 5).** Gauge-fixed, the 5 × 5 isometry has |entry|² ∈ {1/2, 1/4, 1/8, 0}
  with phases on the π/6 lattice: each rail of qubit A feeds two output modes with weight 1/2,
  qubit B's rails and the ancilla spread with weights 1/4 and 1/8, and each Bell state is
  identified by exactly two detection patterns of probability 1/8 (eight identifying patterns
  in all). The other restarts at 1/4 have moduli off the small-rational lattice, consistent
  with a continuous family sharing the vector, which is why only one of four lifted.
- **(1, 1/6, 1/2, 2/9) (m = 5).** Rows 0 and 4 form a standard analyser-like block that never
  sees the ancilla (|entry|² = 1/4); rows 1–3 split the ancilla photon evenly (1/3 each) and
  every Bell mode with weight 1/6, with phases on the π/6 lattice — a tritter coupling the
  ancilla into three output modes. Its average, 17/36, equals that of the 3-of-4 designs
  (1, 1/6, 13/18, 0): the two families redistribute the same total success 17/9.

The exact witnesses are ledger artifacts of kind `certificate` with claims of the form
"there is an unambiguous scheme with k = 1 … whose exact success vector is …; hence
p*(1) = sup min_B p_B ≥ 1/4"; the artifact content is the isometry itself in ℚ(i)(√d)
notation, re-checkable by `P3ExactVerifier` from the stored bytes.

## The strategist round (two free-form calls, $5.90)

Verbatim answers with provenance: `docs/science/2026-09-05-p3-strategist/`. What they say,
and what the harness could check today:

- **Mechanism of the (1, 1/6, 1/2, 2/9) family.** The strategist decodes it as an X-basis
  Bell analyser whose two HOM output ports feed a balanced tritter together with the ancilla
  photon: within-pair Bell states HOM-bunch, and the three-photon permanents in the tritter
  — linear in the ancilla column — zero the unwanted sign pattern by pattern, which is
  exactly what the k = 0 obstruction forbade. **Checked (exact arithmetic):** in the certified
  witness the Bell block of the three tritter rows has rank 2, its flat left-null vector
  (|entries|² = 1/3 each) carries the ancilla entirely, and the two trigger rows never see
  the ancilla — i.e. rows 1–3 are a balanced three-mode mixer on two Bell-only ports plus
  the ancilla. The literal layer-by-layer factorisation as written (Hadamards, two 50:50
  splitters on the rotated pairs, DFT tritter) evaluates, with the harness's conventions, to
  the sibling design (2/3, 0, 1, 2/9) (same total 17/9, one state at 0), so the exact
  matrix identity is not confirmed as stated; the structural claim is.
- **Optimality.** Conjecture (their confidence 0.75): max_U min_B p_B = 1/4 for k = 1 and
  every m, attained by the balanced witness; sharper frontier conjecture (0.6):
  p₍₁₎ + p₍₂₎ ≤ 1/2 (the two smallest successes). Both are now optimizer targets
  (`p_low2`, `p_sum_all4`); the frontier batch at m = 5, 6 is recorded in
  `runs/p3-campaign/opt/`. Their proof route: the orthonormal 4-frame relaxation alone
  permits min = 1 (so any bound is genuinely bosonic), then a rational-SOS certificate for
  p₍₁₎ + p₍₂₎ ≤ 1/2 on the permanental variety at m = 5.
- **Average metric.** A lemma ladder S0–L6\* for p_avg ≤ 1/2 at k = 1: S0–L5\* (frame
  reduction, three-photon Pauli reduction T(n) with the k = 0 matrix Q as the cofactor,
  coherence budget, phase rigidity) are mechanical on the existing Lean development; L6\*,
  the "one-photon distillation bound" Σ_{identified} ‖T(n)‖² ≤ 2, is the content
  (their confidence in the claim 0.9, in the route 0.5). Named machine milestones: the
  reduction lemma "a non-interfering ancilla reduces to k = 0" (cheap), and a certified
  p_avg ≤ 3/4 at m = 5 via rational SOS (heavy, same technology as the k = 0 certificate).

## Honest accounting

- Float optima are HEURISTIC (two-engine agreement, declared leakage budget 1e-9); only
  lifted exact witnesses are CERTIFIED.
- Nothing here bounds p*(1) from above; the strategist's conjectures and lemma ladder are
  HEURISTIC and stay so until a certificate or a Lean proof lands.
- The lost wave-1 design with vector (1/16, 3/16, 9/16, 1) (min 1/16) was never
  re-found; both certified families dominate it on the min metric.
- k = 2 sanity runs (m = 8, 12 restarts per metric) are recorded in
  `runs/p3-campaign/opt/`; see the addendum below once complete.

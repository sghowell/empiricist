# P3: first live search wave — three targets, three informative refusals

**Date:** 2026-07-20 · **Problem:** P3 (ancilla-boosted linear-optical Bell measurement) ·
**Method:** Fable-5 iterative design through the M20a campaign loop (propose → screen →
two-engine verify → feedback), `runs/p3-campaign`.

## Setup

Each task ran the `P3SearchLoop`: Fable emits one `BellSchemeOut` per round; the screen caps
resources; `verify_scheme_agreed` evaluates the scheme on both independent engines and checks
the claimed target; FAIL rounds feed the exact per-state success vector back. Zero leakage
budget throughout: a detection pattern counts for a Bell state only if no other Bell state can
produce it. Effort tier: LOW (the operational finding of the launch — HIGH emitted 0/12
rounds, thinking past every wall or overflowing the 64k output cap; MEDIUM 4/12; LOW 24/28
across the wave).

## Task 1 — k=0 min-balanced (target `p_min ≥ 1/2`): NOT ACHIEVED, with a pattern

16 rounds, 14 verified schemes. **Every scheme saturated the Calsamiglia–Lütkenhaus average
exactly (`p_avg = 1/2`) and every scheme left at least one Bell state at exactly 0.** The
explored vectors cover the family (0,0,1,1), (0,½,½,1), (1,0,1,0), (½,½,0,1), (½,0,1,½) —
three-way redistributions of the ½ average exist, but no design balanced all four states.

> **Emerging conjecture (heuristic; needs the P3 conjecture machinery for formal grounding):**
> passive k=0 schemes force `p_min = 0` — the CL average of ½ can be redistributed across at
> most three Bell states; some state is always never-identified.

## Task 2 — k=2 min-balanced (target `p_min ≥ 3/4`): NOT ACHIEVED, same wall

12 rounds, 12 verified schemes. Best `p_min = 1/2` — exactly Grice's own vector (½,½,1,1).
Fable's genuine rebalancing attempts (nontrivial intermediate values `p_min = 3/16`,
`≈ 0.0732`) all *traded the floor down*: moving success probability toward the weak states
lowered the minimum instead of raising it. The mirror of Task 1's pattern one tier up:
the discrimination structure appears to permit shifting *which* states get certainty, but
not lifting the worst case above ½ at k=2.

## Task 3 — p*(1) refutation probe (target `p_avg ≥ 0.51`): CONJECTURE SURVIVED

12 rounds, 10 verified k=1 schemes attacking the "one ancilla photon is useless" conjecture.
Best genuine ancilla-interference designs reached `p_avg = 29/64 ≈ 0.4531` (three distinct
designs); the best overall exactly recovered `p_avg = 1/2` — the k=0 optimum, never exceeded.
Ten verified best-effort failures are evidence *for* `p*(1) = 1/2`, consistent with the known
mechanism (a single photon cannot supply the second-order interference that splits φ± in
Grice-type boosting).

## Honest accounting

- ~50 verified scheme evaluations across the wave; **zero PASSes** — no ledger artifacts
  ingested (the ingestion path is exercised by tests; the physics simply resisted).
- Round histories (vectors + verdicts) persisted to `runs/p3-campaign/*-history.json`; the
  per-round *meshes* of failed schemes were not persisted (known loop improvement).
- These are search results, not bounds: "not achieved in N rounds" is evidence, not proof.
  The natural next step for Tasks 1–2 is the M20 certificate layer (SOS/SDP upper bounds on
  `p_min` at fixed k, m), which could convert the two infeasibility patterns into theorems;
  for Task 3, accumulating structured failure data and eventually a k=1 upper-bound
  certificate below 0.51.

## Operational findings (for the record)

1. **Effort ladder** (the campaign-critical discovery): iterative-design loops need LOW
   effort — HIGH never emits (rumination past any wall, or 64k output-cap overflow),
   MEDIUM emits ~1/3, LOW emits ~6/7. The design signal lives in the verified feedback,
   not in per-round deliberation.
2. The four-verdict contract worked as designed under fire: timeout kills → NO_ARTIFACT,
   malformed ancillas → SCREENED, no false alarms, no crashes, full provenance.

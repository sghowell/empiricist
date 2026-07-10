# P5 live campaign: the model-in-the-loop machine on real tokens

**Date:** 2026-07-09 · **Problem:** P5 (minimum GHZ₃ fusions `F(G)` for graph-state
orbits) · **Model:** Fable 5 via Claude Code (subscription) · **Spend:** $140.99
(reported cost proxy) · **Run:** `runs/p5-live` (ledger + CAS, local, not committed).

> **Headline (beyond the deterministic frontier):** the model produced **3 exact
> `F(G)` values that no deterministic tier in the M5c tablebase reached** — the
> 3-regular n=6 orbit at **F=9=N+3**, and 2 of the 4 n=7 orbits at **F=10=N+3**
> (Tier-2 territory: 2 intra-fusions beyond all-merge, which the Tier-0/Tier-1
> tablebase never explored). All three independently re-verified (both fusion
> engines agree). This is the case a heuristic proposer + cheap certified verifier
> is *for*: finding constructions where exhaustive enumeration was never run.

This is the first end-to-end run of the Empiricist inner loop with a live model:
the harness drove Fable 5 to propose fusion `Construction`s and closed-form
conjectures, screened and verified every output with the certified machinery, and
promoted nothing above HEURISTIC without machine evidence. **Every result below was
independently re-verified from scratch** (fresh `verify_agreed` / `attack` runs),
not trusted on the campaign's own recorded verdicts.

## Results

### 1. Four new exact values in the F(G) table (SEARCH)

The M5c tablebase left 59 orbits at n=8 open at `F ≥ 8 = N` (Tier-1 was not run past
n=7). The live SEARCH closed **4 of them exactly at F = 8**:

| # | achieved orbit (n=8) | prior M5c bound | now | witness |
|---|---|---|---|---|
| 1 | distinct LC-orbit | `F ≥ 8` (open) | **F = 8** | 8-fusion `Construction`, CAS `28a13736…` |
| 2 | distinct LC-orbit | `F ≥ 8` (open) | **F = 8** | CAS `30b3f164…` |
| 3 | distinct LC-orbit | `F ≥ 8` (open) | **F = 8** | CAS `b29cbaab…` |
| 4 | distinct LC-orbit | `F ≥ 8` (open) | **F = 8** | CAS `e2a5d0ea…` |

**Independent re-verification (4/4):** each construction was rebuilt from its CAS
JSON and re-run through a fresh `verify_agreed` — all PASS, **both fusion engines
(stim tableau ∧ GF(2)) agree**, each achieves a **distinct** LC-orbit that was an
`exact=False` row in the M5c dataset. Exactness follows from achievability (the
certified F=8 witness) + the Tier-0 lower bound + the L2 mod-3 ladder.

These 4 n=8 orbits are Tier-1-reachable (F = N), so `tier1_search(8)` would also
resolve them — the weight here is the *live model→verify loop* producing correct
two-engine-certified witnesses, not novelty past the solver.

### 1b. Three exact values BEYOND the deterministic frontier (SEARCH, n=6/7)

The genuinely-novel result. The M5c tablebase ran only Tier-0 (all-merge) and
Tier-1 (≤1 intra-fusion), leaving 5 orbits open at `F ≥ N+3` — 1 at n=6, 4 at
n=7 — that require **≥2 intra-fusions (Tier-2), which no deterministic search in
the project has ever run.** After generalizing the exact-upgrade target to the
achievable rung (`target_f = lower_bound = N+3`, commit on this branch), live
SEARCH **closed 3 of them:**

| orbit | prior bound | now | witness (independently re-verified) |
|---|---|---|---|
| n=6 3-regular (the sole n=6 open) | `F ≥ 9` | **F = 9 = N+3** | R=8, 9 fusions, 3 LC — `verify_agreed` PASS, engines agree, `6 = 3·8 − 2·9` (`235f4cd0…`) |
| n=7 open orbit A | `F ≥ 10` | **F = 10 = N+3** | R=9, 10 fusions, 1 LC — PASS, agree, `7 = 3·9 − 2·10` (`960c7fec…`) |
| n=7 open orbit B | `F ≥ 10` | **F = 10 = N+3** | R=9, 10 fusions, 2 LC — PASS, agree (`b8fe46d3…`) |

Exactness: achievability (the certified F=N+3 witness) meets the proven
`F ≥ N+3` floor (Tier-1 exhaustively excluded F ≤ N) on the L2 mod-3 ladder ⇒
`F = N+3` exactly. **Table impact:** all 11 n=6 orbits are now exact (was 10+1);
24 of 26 n=7 orbits are now exact (was 22+4). The remaining 2 n=7 opens and the
n=8/9 opens the model did not crack stay honestly open.

This is where the model earns its keep: it found multi-intra-fusion constructions
(with the free LC steps that the M5c pre-review proved are orbit-changing and
sometimes *necessary*) in a region the deterministic solver never enumerated — and
every one is machine-certified by two independent engines, not taken on the model's
word.

### 2. Four distinct grounded closed forms (CONJECTURE)

The CONJECTURE pipeline mined closed forms per graph family and auto-ATTACKed each
against the exact table + the invariants (`F ≡ N−3 mod 3`, `F ≥ N−3`) + open-row
lower bounds. **Four distinct forms survived** (0 refuted); each was **independently
re-attacked from scratch (21 grounded checks, no counterexample):**

| family | conjectured closed form | independent re-attack |
|---|---|---|
| path | `F(N) = N − 3` (N ≥ 3) | survived, 21 checks |
| star | `F(N) = N − 3` (N ≥ 3) | survived, 21 checks |
| complete | `F(N) = N − 3` (N ≥ 3) | survived, 21 checks |
| **cycle** | **`F(n) = n − 3` for n ≤ 4; `F(n) = n` for n ≥ 5** | survived, 21 checks |

The **cycle** result is the notable one: the model did not restate the universal
lower bound — it discovered the *piecewise* law with the transition at n=5 (cycles
become Tier-1 there), correctly handling the small-n exceptions (C₃, C₄ collapse to
Tier-0 orbits at `F = N−3`) and the jump to `F = N` for n ≥ 5. That matches the
exact table cell-for-cell (C₅→5, C₆→6, C₇→7) and meets the `F ≥ 8, ≥ 9` bounds at
n = 8, 9. path/star/complete share the formula `F = N−3` but are distinct family
claims.

## Trust audit (F1–F5) — clean

- **F1** (model-as-oracle): 0 artifacts ≥ VERIFIED_N without a certified-verifier
  PASS evidence row. The 4 orbit closures live at HEURISTIC (constructions) with
  PASS `verify_agreed` evidence; dataset-row promotion to exact is a deliberate
  manual/audited step, not auto-applied.
- **F3** (verifier gaming): 0 engine-disagreement (`f3_alarm`) events — the two
  independent fusion engines agreed on every certified construction.
- **F4** (proof-by-intimidation): every CONJECTURED artifact carries an
  `auto_attack` evidence row with > 0 grounded checks; ungrounded/vacuous
  conjectures are refused (M6 grounding rule).
- **F5** (unbounded burn): every phase stopped on `stalled_out` (genuine
  convergence), total $140.99 under the authorized ceiling; cost tracked per call.
- Ledger DB and CAS blobs are local-only (gitignored), never committed.

## Two harness weaknesses the live pilot surfaced (both fixed)

A pilot's job is to break the machine under real conditions. Two issues surfaced,
both fixed on this branch and re-validated live:

1. **Conjecture dedup was byte-level.** The Conjecturer restated `path: F=N−3` ten
   different ways in prose; the dedup hashed the full JSON *including the prose*, so
   10 semantically-identical restatements landed as 10 distinct CONJECTURED
   artifacts — an F4-adjacent count-inflation risk. **Fix:** dedup identity is now
   the semantic tuple `(family, predicted_values)`; the 10 collapse to 1, and a
   family-diversity nudge steers the model to uncovered families (which produced
   star, complete, and the cycle discovery). CAS content still preserves the
   first-seen full conjecture.
2. **Conjecturer calls bypassed the ledger.** `mine()` did not thread `ledger`, so
   conjecture model calls were neither cost-tracked nor provenance-recorded (the
   budget saw only SEARCH spend). **Fix:** `mine()` now bills every call as a run.

## Cost & convergence notes (for the next campaign)

- A SEARCH generation is **~$8.6** (searcher role fires k=32 attempts × ~$0.27;
  Fable's always-on thinking is ~5k output tokens/call even at low effort) — ~170×
  the stale M4 per-call estimate. Budget SEARCH accordingly; CONJECTURE is cheap
  (~$0.4–1.5 per wave).
- SEARCH converged (`stalled_out`) after the easy Tier-1 witnesses were found; the
  marginal orbit-closure rate falls as the reachable orbits go first.
- CONJECTURE converged at 4 forms because `family_graph` covers exactly
  {path, cycle, star, complete}; adding families (wheel, tree, …) would extend it.
- The exact-upgrade detector now targets the achievable rung
  (`target_f = lower_bound`, generalized from the old hardcoded `N` on this
  branch) — this is what unlocked the n=6/7 `F ≥ N+3` beyond-frontier closures
  (§1b) while staying backward-compatible for the n=8/9 opens (`lower_bound = N`).
- The n=6/7 beyond-frontier orbits are small and cheap to verify but hard to hit:
  the model cracked 3 of 5 across the search budget; the 2 remaining n=7 opens are
  future work (more attempts, or a deterministic Tier-2 search as a cross-check).

## Provenance

Run directory `runs/p5-live/` (ledger `ledger.db`, CAS `store/`); VERIFIED_N P5
dataset artifact = the M5c tablebase re-derived by ENUMERATE; 640 billed SEARCH
model runs + the CONJECTURE runs; auto-generated ledger report snapshot at
`docs/science/2026-07-09-p5-live-campaign-report.md` (regenerable from the ledger
via `empiricist report`). All promoted claims reproducible by re-running
`verify_agreed` / `attack` against the committed dataset.

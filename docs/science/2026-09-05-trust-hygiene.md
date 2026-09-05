# Trust hygiene: the legacy Lean chain re-verified, the CERTIFIED tier wired

**Date:** 2026-09-05 · **Milestone:** M21a (`docs/superpowers/plans/2026-09-05-m21a-trust-hygiene.md`)
· **Ledgers:** `runs/p5-formalize`, `runs/p5-live`, `runs/p3-campaign` (local, gitignored).

## What the 2026-09-03 audit found

`empiricist audit` flagged every FORMALIZED Lean artifact in the two P5 ledgers as
`elevated_missing_certified_evidence`: 20 in `p5-formalize` (the Fable foundation chain
the preprint cites: universal lower bound, the five family theorems, the twin/centre-merge
modules, `dh_forward`, `dh_characterization`, `floor_schedule_iff_dh`) and 2 in `p5-live`
(the July-10 `complete_min_fusions` / `tree_min_fusions`). Their PASS rows predate
golden-suite-hash tracking (verifier `lean` 3.2/3.3, no `golden_suite_hash`, no claim),
so the hardened gate had nothing to cross-check them against. Both ledgers were still at
schema v0. `p3-campaign` was clean on that code (6 `run_billing_unknown` receipts remain:
spend there is a documented lower bound). The CERTIFIED tier had zero rows in any ledger.

## What was done

1. **`empiricist reverify`** (new): opens the ledger for writing (v0 → v1 migration in
   place, additive), certifies the current `LeanVerifier` (3.3) against the live Lean
   golden suite in that ledger, then re-runs the full sandboxed kernel gate over each
   FORMALIZED artifact's stored source and records a claim-bound PASS row pinned to the
   suite hash through the same certification-gated transaction ingestion uses. A non-PASS
   would be recorded as evidence only (never a demotion — REFUTED would assert falsity).
2. **Outcome:** `p5-formalize` 20/20 PASS (3 min 51 s wall, including certification);
   `p5-live` 2/2 PASS (1 min 21 s). Both ledgers now `audit OK`. Backups of all three
   ledgers were taken first (`runs/_backup-2026-09-05/`, sqlite online backup).
3. **The CERTIFIED tier** now has a real path: `SOSCertificateVerifier` (identity over
   `certificates/{core,ingest,p3_targets,verifier}.py`) with a mutation-resistant golden
   suite (identity / PSD / shape must-fail cases), and `ingest_p3_certificate`, which
   re-derives the target's objective and constraint polynomials from `p3_targets` before
   the checker runs — a certificate can only certify the target it declares — and records
   the claim with wording that matches the warrant: the U(4)-universal statement only when
   no unambiguity side-constraint multiplier is used, the restricted statement otherwise
   (the adversarial review's blocker).
4. **Loop robustness:** the P3 search loop persists every attempt of every round (scheme,
   achieved vector, run id) through a committed JSONL driver; both model loops recognise
   the rate-limit receipt signature (instant non-zero exit, no output tokens), back off
   exponentially under a fresh run id, and abort the task without an F3 alarm.

## Audit tallies after

| ledger | artifacts | evidence rows | audit |
|---|---|---|---|
| p5-formalize | 20 | 40 | OK |
| p5-live | 25 | 27 | OK |
| p3-campaign | 18 | 20 | 6 × `run_billing_unknown` (spend lower bound; unchanged) |

Provenance: `runs/p5-formalize/reverify-2026-09-05.log`, `runs/p5-live/reverify-2026-09-05.log`.
The k=0 exact ½ certificate is ingested at CERTIFIED into `runs/p3-campaign` as the next
campaign action (M21a Task 4.2), after this PR merges.

# Ledger hygiene: relabelled P3 lemmas, superseded conjectures, a vacuous theorem, and a verifier that changed under a claim

**Date:** 2026-09-07 · **Milestone:** M23a (`docs/superpowers/plans/2026-09-07-m23a-ledger-hygiene.md`)
· **Ledgers:** `runs/p3-campaign`, `runs/p5-formalize`, `runs/p5-live` (local, gitignored; backups
under `runs/_backup-2026-09-07/`) · **Repository ledger:** `claims/` (63 → 77 claim files).

## What the survey found

1. **Fourteen P3 Lean lemmas filed under P5.** The P3 k=0 formalization chain (`rawAmp_eq_traceForm`,
   `pauli_no_common_eigenvector`, `identifies_iff_prop`, `card_Mset_le_two`, `cover_structure`,
   `identifies_rowDecouples`, `case_doubled`, `axis_pairing_not_both_zero`, both
   `pauli_eigvec_axis_aligned` modules, `pauli_eigvec_sesq_pairing`, `pauli_eigvec_sesq_sum_ne`,
   `case_fourCycle`, and the headline `p3_at_most_three`) was ingested through `FormalizeTask`,
   whose `problem` field defaulted to `"P5"`. The ledger and `CLAIMS.md` listed them as P5 results.
2. **Thirteen rows that FORMALIZED theorems already prove.** The 2026-07-09 live campaign predated
   semantic conjecture dedup and left ten rewordings of `F(path_N) = N−3` at CONJECTURED, plus the
   star and complete-graph conjectures; `pathGraph_min_fusions`, `star_min_fusions` and
   `complete_min_fusions` prove them. The Fable-generated distance-hereditary conjecture is proved
   at the model level by `floor_schedule_iff_dh` (with `dh_characterization` and `dh_min_fusions`).
   Two July-10 copies of `complete_min_fusions` / `tree_min_fusions` duplicated the July-15 theorems.
3. **A FORMALIZED claim whose statement is `True`.** Artifact `adcedf47…`, titled
   `Empiricist.pauli_eigvec_axis_aligned`, is a diagnostic probe module ("Headline placeholder for
   this probe round") whose headline theorem is `theorem pauli_eigvec_axis_aligned : True`. The
   Lean gate correctly passes a proof of `True`; the ledger should never have recorded it as a
   result. The real lemma is artifact `f2322820…` (`P3.pauli_eigvec_axis_aligned`).
4. **The SOS certificate checker had changed under a CERTIFIED claim, unnoticed.** PR #71 (M22b)
   added the batch hook to `certificates/ingest.py`, which is part of `SOSCertificateVerifier`'s
   identity. The live hash became `68a61a8d…` while the committed stamp and the evidence under
   `P3.k0_standard_assignment_p_avg` still said `78e59a05…`. `check` compared only command
   verifiers to their declarations, so it stayed green. This is the charter's second kill-gate
   event: a verifier that changed under a promoted claim in the course of research, not induced.

## What was done

- **`check` now compares built-in verifier stamps to the live identities** (`lean`,
  `sos_certificate`, `p3_exact_witness`; `verifiers/builtin.py`). On the pre-hygiene repository
  it immediately reported `verifier_drift: sos_certificate` and derived
  `P3.k0_standard_assignment_p_avg` STALE. Root cause of the earlier miss fixed at the source.
- **`reverify` now covers certificates** (`certificates/reverify.py`): both checkers are
  re-certified against their golden suites when their live identity lacks a stamp, and every
  CERTIFIED certificate artifact is re-run from its stored payload through the same
  certification-gated ingest that promoted it. `empiricist reverify --only {lean,certificates}`.
- **`Ledger.relabel_artifact` / `empiricist relabel`**: an artifact's `problem` is metadata (the id
  is the content digest), so the relabel rewrites the column and leaves a finished `runs` row
  (`move='relabel'`, argv = what changed and why) in the same transaction. Fourteen relabels in
  `runs/p3-campaign`.
- **The importer materialises a relabelled artifact as a superseding claim**: the old `P5.*` file is
  untouched (its derived standing becomes SUPERSEDED), the new `P3.*` claim carries the same
  evidence and names the old one in `supersedes`. `check` no longer enforces the lock on a
  superseded row (its successor holds the path's current verifier identity).
- **Lean ingest hygiene**: `problem` is a required argument of `ingest_lean_artifact`,
  `verify_and_ingest_lean_artifact` and `FormalizeTask` (no default); a PASS whose resolved
  statement is the bare `True` is refused at ingest (`VacuousStatementError`; the formalize loop
  feeds it back as gate `vacuous`; `reverify` reports it SKIPPED and records nothing).
- **Re-verification under the edited code** (editing `verifiers/lean.py` moves
  `LeanVerifier.binary_hash`, so every ledger re-certified the gate first):

  | ledger | Lean artifacts | certificates | wall |
  |---|---|---|---|
  | `p3-campaign` | 15 PASS, 1 SKIPPED (the `True` probe) | 8 PASS (1 SOS, 7 exact witnesses) | 241 s |
  | `p5-formalize` | 20 PASS | — | 182 s |
  | `p5-live` | 2 PASS | — | 73 s |

  `import-ledger` then re-stamped the repository registry (`lean` 3.3 `34cd2464…`,
  `sos_certificate` 1.0 `68a61a8d…`, `p3_exact_witness` unchanged) and every FORMALIZED and
  CERTIFIED claim is CURRENT again on evidence from the live identities.
- **Supersedes links** recorded by hand on the five theorem claims (human-owned field, with a
  dated note each): `pathGraph_min_fusions` ⊃ ten path conjectures; `star_min_fusions` ⊃ the star
  conjecture; `complete_min_fusions` ⊃ the complete-graph conjecture and its July-10 copy;
  `tree_min_fusions` ⊃ its July-10 copy; `floor_schedule_iff_dh` ⊃ the distance-hereditary
  conjecture, with the one honest boundary stated in the note (the single-blob normal form is
  engine-checked, not formalized). The cycle conjecture (`F(C_n) = n` for n ≥ 5) stays open.
- **The `True` claim**: one model-reviewer sample on `P3.Empiricist.pauli_eigvec_axis_aligned`
  (BLOCK with six blocking findings, all on the vacuous statement and the probe's own docstrings, receipt `P3.Empiricist.pauli_eigvec_axis_aligned.20260907.model`, $2.24); demoted to HEURISTIC on that
  receipt and superseded by `P3.pauli_eigvec_axis_aligned`, the lemma it was probing for.

## Where the ledger stands

`claims check --repo . --min-claims 1`: 77 claims, 0 issues; standings {CURRENT: 47 (35 FORMALIZED, 8 CERTIFIED, 3 CONJECTURED, 1 VERIFIED_N),
SUPERSEDED: 30}. `empiricist audit` is clean on all three run directories.

## Kill-gate status (charter §1)

- Event 1 (a receipt blocked a genuine defect): 2026-09-06, death_and_gravity P8-A.7.
- Event 2 (a genuine stale claim caught): 2026-09-07, `sos_certificate` drift under
  `P3.k0_standard_assignment_p_avg`, caught by `check` the moment it could see built-in
  identities, re-earned through `reverify` + `import-ledger`. The change was made for the batch
  hook (M22b), not to test the tool.

## Follow-ups

- M23b: the P5 campaign under v1 (materialise conjecture and dataset promotions through the batch
  hook; an end-of-campaign catch-up; a "settled families" nudge for the conjecturer).
- The 2026-07-09 campaign's exact-upgrade witnesses (four n=8 closures, three n=6/7 Tier-2
  closures, the 2×4 cluster) are HEURISTIC constructions with two-engine PASS evidence in
  `runs/p5-live`; they never rise above HEURISTIC in the v0 lattice, so they do not materialise as
  claims. A CERTIFIED path for agreed witnesses is the obvious next design question for M23b.

---
name: empiricist-claims
description: Use when a research repository keeps its claims in `claims/*.yaml` with a `claims.lock.json` and a rendered `CLAIMS.md` (an Empiricist v1 claim ledger) — to add a claim, attach machine evidence, review it, raise or lower its level, or find out why `claims check` is red. Every level change goes through the `empiricist claims` CLI; never edit levels, standings, or CLAIMS.md by hand.
---

# Empiricist claim ledger — interactive workflow

The ledger is git-tracked: one file per claim in `claims/<id>.yaml`, the hash lock
`claims.lock.json`, review receipts in `receipts/`, verifier declarations in
`claims/verifiers/*.yaml`, the committed registry `claims/verifiers.json`, and the
rendered table `CLAIMS.md`. Commit all of them together. `.empiricist/` (model-run
provenance) is local and gitignored.

Run the CLI as `empiricist claims <command> --repo .` (an installed `empiricist`, or
`uv run --project <empiricist checkout> empiricist claims ...`).

## Levels and standing

- Levels: HEURISTIC < CONJECTURED < VERIFIED_N < CERTIFIED < FORMALIZED; REFUTED is
  terminal. A level rises **only** through `promote`, which runs the verifier itself.
- Standing is derived, never edited: CURRENT, STALE (an evidence file, a dependency, or
  the verifier changed), CHALLENGED (a blocking review finding is open), SUPERSEDED.
- A claim imported from an older table shows `HEURISTIC (legacy CERTIFIED, not re-earned)`
  until `promote` re-earns the level with a certified verifier.
- A claim's level may not exceed the lowest level among the claims it depends on
  (`promote` refuses; `check` reports `level_inversion`). Re-earn chains bottom-up, or a
  human receipt waives it once: `review --human ... --waive level_inversion`.
- `claims deps-from-pins --repo .` adds the dependency edges your certificates pin
  (`prior_*_sha256` fields naming another claim's evidence file).

## The workflow

1. **Declare a verifier once per checker** — `claims/verifiers/<name>.yaml`:
   ```yaml
   name: p8a_remainder
   version: "1"
   argv: [.venv/bin/python, tools/empiricist_check.py, p8a_remainder, "{evidence}"]
   cwd: .
   env: {PYTHONPATH: "problems/P8/a/src:..."}   # values verbatim; nothing else is inherited
   inputs: [tools/empiricist_check.py, problems/P8/a/src, ...]  # every file the command runs
   fixtures:
     pass: [problems/.../certificates/radiation-remainder.json]
     fail: [claims/fixtures/p8a_remainder/fail-mutated-status.json]
   fail_exit_codes: [3]      # only these exits mean FAIL; any other non-zero exit is ERROR
   timeout_s: 1800
   ```
   The FAIL fixture must be a real, committed file the command genuinely rejects (a
   mutated copy of a certificate). `tools/empiricist_check.py` (installed with this
   skill) adapts any checker module exposing `REPORT`, `build_report()` and
   `validate_report(expected, actual)`; edit it for other conventions.
2. **Certify it**: `claims certify-verifier --repo . --name <name>` runs every PASS and
   FAIL fixture and stamps `claims/verifiers.json`. Re-run after any change to the
   declaration, its inputs, or its fixtures (`claims check` reports `verifier_drift`).
3. **Formulate**: `claims formulate --repo . --id <id> --problem <P> --formulation-version
   <v> --kind statement|dataset|construction --statement "..." [--depends-on <id-or-path>]`
   freezes the exact statement at HEURISTIC.
4. **Promote on evidence**: `claims promote --repo . --id <id> --level <L> --verifier
   <name> --evidence <repo-relative file> [--n N --coverage exhaustive|sampled]`. The
   verifier runs inside `promote`; PASS is required (a declared FAIL exit for REFUTED).
   CERTIFIED/FORMALIZED for a `statement` claim, and REFUTED for anything at CONJECTURED
   or above, also need `--receipt <id>` (step 5).
5. **Review**: `claims review --repo . --id <id> --target-level CERTIFIED` runs the
   independent model reviewer (two samples for elevated targets; one receipt each,
   provenance under `.empiricist/`), or `claims review --repo . --id <id> --human
   --reviewer "<name>" --verdict PASS|REVISE|BLOCK [--finding dimension:severity:text ...]
   [--closes <receipt id> ...]` records a human review. Dimensions: evidence_support,
   assumption_explicitness, internal_consistency, ledger_consistency,
   confidence_calibration, decision_soundness. A blocking finding makes the claim
   CHALLENGED until a later receipt on the same claim closes it: fix the record or the
   claim, then `review --closes <blocking receipt id> ...` (a fresh model sample that
   raises no blocking finding closes; a human `--human --closes` closes too).
6. **Keep it green**: `claims check --repo . --min-claims <n>` (pure; belongs in
   pre-commit/CI) and `claims report --repo .` (writes derived standings and CLAIMS.md).
   `claims reverify --repo . [--id <id>]` re-runs the verifiers of STALE claims;
   `claims demote --repo . --id <id> --level <L> --receipt <id> --reason "..."` lowers a
   level behind a receipt.

## What `promote` refuses, and what to do

| refusal | do |
|---|---|
| `no current stamp` / `fixtures changed` | `certify-verifier` again |
| `is STALE ...; run reverify first` | `reverify`, or fix the evidence file it names |
| `is CHALLENGED by blocking receipt(s)` | address the finding; record a closing receipt |
| `requires a review receipt` | `review` (model or human), then pass `--receipt` |
| `dependency X is STALE` | `reverify` (or promote) X first |
| `is above dependency X at <level>` | re-earn X first, or a human receipt with `--waive level_inversion` |
| `returned FAIL, not PASS` | the evidence does not pass; the FAIL entry is recorded |
| `not a committed regular file` | commit the file; no symlinks, nothing outside the repo |

## Rules

- Never hand-edit `level`, `standing`, `evidence`, `claims.lock.json`, or `CLAIMS.md`;
  `claims check` treats a mismatch as blocking.
- Never write a receipt by hand for a review that did not happen.
- A legacy `CLAIMS.md` is imported once (`claims import-table --file CLAIMS.md --repo .`)
  and replaced once (`claims report --repo . --force`).

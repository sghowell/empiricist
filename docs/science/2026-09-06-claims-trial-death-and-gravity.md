# The v1 claim ledger in a real research repository: the death_and_gravity trial

**Date:** 2026-09-06. **Repository:** `~/dev/research/death_and_gravity`, branch
`empiricist-claims-import` (pushed). **Charter:** `docs/superpowers/specs/2026-09-04-empiricist-v1-charter.md`,
first deliverable (2026-09-18): `check` green there and one promotion through `promote`
with a receipt.

## What the repository looked like

A 51-row hand-maintained `CLAIMS.md` (`id | problem | statement | level | evidence |
updated`): 47 rows at CERTIFIED, 4 at CONJECTURED. Evidence cells point at certificate
JSONs replayed by per-problem `verify.py --check` modules (20 P8 checkers share one
convention: `REPORT`, `build_report()`, `validate_report(expected, actual)`), pytest
suites (P4 uses python-flint arb), notes, and other rows ("as P9b-0").

## Import (M22a)

`empiricist claims import-table --file CLAIMS.md --repo .` produced `claims/*.yaml` for
all 51 rows. Two rows (`P4-4`, `P4-7`) contain unescaped `|` in their statements; the
first importer silently dropped them, the reviewed one re-joins the surplus cells into
the statement. Evidence cells resolved through problem-directory-relative paths, globs,
`{a,b}` braces, directory expansion, comma lists, and `as <id>` references; unresolved
fragments are kept in `notes`.

Levels are earned: every row entered at **HEURISTIC** with the table's level kept as
`legacy_level` ("not re-earned") and its evidence files locked as `IMPORTED` entries
that never count as PASS. `claims report --force` replaced the hand table with the
rendered one, once. `claims check --min-claims 50` is green.

## One certified verifier (M22b)

`tools/empiricist_check.py` adapts any `<package>.verify` checker: it replays
`build_report()` and compares it with the certificate named on the command line
(`{evidence}`), exiting 0 on exact reproduction and 3 on any difference.
`claims/verifiers/p8a_remainder.yaml` declares argv, cwd, the seven-directory
`PYTHONPATH` (all listed in `inputs`, so an edit anywhere in the chain changes the
verifier's binary hash), `fail_exit_codes: [3]`, the pinned certificate as the PASS
fixture and a mutated copy (`status` changed) as the FAIL fixture. `certify-verifier`
runs both (~4 s each) and stamps `claims/verifiers.json`.

`promote --id P8-A.7 --level CONJECTURED --verifier p8a_remainder --evidence <certificate>`
ran the replay inside `promote` and recorded a PASS entry with the exact argv, cwd, exit
code and environment hash. `promote --level CERTIFIED` was refused: a `statement` claim
needs a review receipt. Changing the declaration later (adding `fail_exit_codes`) made
the claim STALE (verifier drift) until `certify-verifier` and `reverify` re-earned it.

## Review and the first genuine promotion (M22c)

<!-- REVIEW-RESULTS -->

## What the next problem needs

- P8's other 19 checkers: one declaration each (same adapter, same shape), one mutated
  certificate each as a FAIL fixture, then `promote` per row. Mechanical.
- P9 (`problems/P9/src/p9/verify.py`) and P4 (pytest + python-flint) do not follow the
  `REPORT`/`build_report` convention; each needs a small adapter or a pytest-based
  declaration (`argv: [.venv/bin/python, -m, pytest, "{evidence}"]` with a FAIL fixture
  that is a deliberately failing test module).
- Model reviews cost a few dollars per elevated promotion (two samples at MAX effort);
  human receipts are free and equally valid to `promote`.

## Lessons

- The legacy importer must not mint evidence: with PASS entries from `table-import`, 46
  claims were CERTIFIED with `check` green and no verifier ever run. Earned levels keep
  `check` honest from the first commit.
- A FAIL fixture is the only proof a verifier can say no. Missing, symlinked, or
  crash-only FAIL fixtures certify nothing; only declared exit codes mean FAIL.
- The checker's environment must be the declaration's, not the operator's shell: a
  `PYTHONPATH` in the parent process could flip a verdict without changing any hash.
- `check` must stay pure and cheap: verifier drift is caught by hashing inputs against the
  stamp, so an edited checker shows up in CI before anyone runs anything.

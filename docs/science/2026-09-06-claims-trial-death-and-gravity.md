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

`claims review --id P8-A.7 --target-level CERTIFIED` ran two independent reviewer
samples (the `reviewer` role: paid only for concrete defects along six dimensions, fresh
context each, MAX effort; $2.93 and $1.90, about five minutes each).

**Round 1: both samples BLOCKED**, independently, on the same defect. The ledger record
said `depends_on: []` while the certificate pins the A.6 certificate
(`prior_A6_sha256 = 1101c2c2…`), `verify.py` re-replays A.6 before anything else, the
statement is scoped to "the unchanged A.5/A.6 … preparation", and the proof imports
reference scales from A.3. A CERTIFIED node with no dependency edges would not go STALE
when A.6 changes. Real, and mine to fix: the importer had no way to derive dependencies
from the evidence. Both samples also warned that `formulation_version: legacy-table`
did not name the FORMULATION.md the certificate pins, and that two PASS entries carried
the same verifier version with different binary hashes.

Record corrected on the trial branch (a540755): `depends_on` = P8-A.3, P8-A.5, P8-A.6
and the pinned A.6 certificate file (now locked, so an A.6 change propagates as STALE);
`formulation_version = FORMULATION.md@bb415f07`; `p8a_remainder` bumped to version 2;
the verifier history written into the claim notes.

**Round 2: both samples REVISE, no blocking finding** ($2.71, $2.13). Sample 4 notes
"the prior blocking condition (empty dependency list) is addressed". What remains is
mostly for the author, not the harness:

- *Level inversion.* CERTIFIED would sit on three dependencies that stand at HEURISTIC
  (legacy CERTIFIED, not re-earned), and the proof imports substantive lemmas from A.6.
  The ledger has no rule capping a level by its dependencies' levels. Either the chain is
  re-earned bottom-up (one declaration per checker; the adapter makes it mechanical), or
  the charter states that levels are per-claim and dependency levels are advisory. A
  decision for the charter, proposed in Mindpalace.
- *Statement scope.* The clause "explicit quadratic finite-amplitude error constants"
  carries no `2<=y<=3` envelope qualifier although the constants are derived only there;
  `t_star` is undefined in the bound text; `P1` is defined twice in the written proof.
  Wording changes to the claim are the author's.
- *Evidence breadth.* The pinned `tests/*.py` suite is never executed as evidence; the
  Wick-C2 constants are computed once rather than cross-checked; the analytic steps
  (IR Volterra, UV Gronwall, coincidence limit) are prose, as the certificate's own
  verification boundary discloses.
- *Harness.* The bundle truncated FORMULATION.md because one large certificate consumed
  the byte cap (fixed: fair per-file shares); the round-2 samples carry `closes: []`
  because only PASS samples closed blocks under the rule in force (fixed: any fresh
  sample without a blocking finding closes).

**Outcome.** P8-A.7 is CONJECTURED with a certified-verifier PASS, four receipts, and
standing CHALLENGED until a later receipt closes the two round-1 blocks (a human
`review --human --closes …`, or another model round under the corrected rule). The
promotion to CERTIFIED has not happened: the reviewer would not sign it while the
dependencies are un-earned, and neither should the harness. Cost of the trial's reviews:
$9.67; total model spend of the day $11.44.

For the charter's kill gate this is the first of its two events: a receipt has blocked a
promotion on a genuine defect. The other (a genuine stale claim caught) has a rehearsal:
changing the verifier declaration made P8-A.7 STALE until re-certification and
re-verification.

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

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

**Outcome of the first two rounds.** P8-A.7 was CONJECTURED with a certified-verifier
PASS, four receipts, and standing CHALLENGED until a later receipt closes the two
round-1 blocks. The reviewer would not sign CERTIFIED while the dependencies were
un-earned, and neither should the harness; the next section is what followed.

For the charter's kill gate this is the first of its two events: a receipt has blocked a
promotion on a genuine defect. The other (a genuine stale claim caught) has a rehearsal:
changing the verifier declaration made P8-A.7 STALE until re-certification and
re-verification.

## Re-earning the chain bottom-up (the same evening)

Sean chose the recommendations: the dependency-level rule (a claim's level is capped by
its dependencies' levels; a human receipt may waive it once; PR #74) and re-earning the
P8(a) chain rather than promoting P8-A.7 over HEURISTIC dependencies.

- `claims deps-from-pins` derived 18 dependency edges from the certificates' own
  `prior_*_sha256` fields (the A.1→…→A.7 chain, the S5 D/CD chains, S6), each as a claim
  edge and a locked path dependency.
- Six more command verifiers (`p8a` … `p8a_response`) were declared and certified in
  minutes; A.1–A.6 went through `promote` to CONJECTURED on their certificates.
- The first P8-A.1 review round returned REVISE twice for record defects of mine
  (`formulation_version: legacy-table`; the verifier shown as a truncated hash without
  its declaration) and asked what CERTIFIED means in this ledger. Fixes: formulation pins
  for every claim, `claims/LEVELS.md` (the repository's own level semantics, now the
  first thing every reviewer reads), and the bundle listing each verifier's committed
  declaration with full hashes (PR #75).
- The second round still returned REVISE, now on a wording defect in LEVELS.md and a
  checker-quality note, while the stricter sample checked every quantitative clause of
  the statement against the certificate and found it backed. That exposed a rule of my
  own that was stricter than the charter: F4's bar is "a receipt with no blocking
  finding", and a PASS-only rule was turning documentation nits into vetoes. PR #76
  restores F4's bar; warnings stay in the receipt and are counted in the claim notes.
- Under that bar a driver climbed the chain: **P8-A.1, A.2, A.3, A.4, A.5 are CERTIFIED**,
  each on two independent samples with no blocking finding (A.5 got a PASS). The
  deliverable's stricter wording, a promotion to CERTIFIED through `promote` with a
  review receipt, is met.
- The usage limit then cut three samples short (cost 0, six seconds). The harness had
  recorded them honestly as "no parseable review" REVISE receipts, but the driver
  promoted A.6 on one of them. PR #77 marks such receipts `usable: false` (they warrant
  nothing and close nothing); A.6 was withdrawn to CONJECTURED through `demote` with the
  reason on record and re-reviewed: two real samples, REVISE with warnings, no blocking
  finding, and **A.6 is CERTIFIED**.
- P8-A.7's third round, now over the corrected record and CERTIFIED dependencies,
  returned one PASS and one REVISE; the PASS sample closed the two round-1 blocking
  receipts and **P8-A.7 is CERTIFIED** on it. The whole P8(a) chain, A.1 through A.7,
  is CERTIFIED with review receipts; `check` is green with 51 claims and no
  `level_inversion`.

**Cost.** 24 reviewer calls on the trial, $47.28 (about $2.40 per sample, five to
eleven minutes each); 17 usable receipts warrant the seven promotions, three unusable
receipts record the usage-limit cut. Day total including the empiricist-side accidental
call: $49.05.

**What the reviewer is worth.** Across 14 real samples it found one genuine record
defect (the missing dependency edges, which the importer now derives from certificate
pins), three documentation gaps that are now part of the harness (formulation pins,
level semantics in the bundle, full verifier declarations), and a standing list of
statement-precision points for the author (missing envelope qualifiers, undefined
symbols, a double-defined `P1`, single-implementation constants). It never contradicted
a certified number.

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

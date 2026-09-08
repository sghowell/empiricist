# P5 under v1: witness closures become claims, and the first unattended run that writes claim files

**Date:** 2026-09-07 · **Milestone:** M23b (`docs/superpowers/plans/2026-09-07-m23b-p5-campaign-under-v1.md`)
· **Run directory:** `runs/p5-live` (resumed; local, gitignored; pre-M23b backup
`runs/_backup-2026-09-07/p5-live-pre-m23b.db`) · **Claims repository:** this one (`claims/`).

## The gap the charter's batch rule exposed

Charter deliverable 2 says an unattended campaign "materializes its promotions as claim files".
Under the v0 lattice the P5 campaign promoted only two kinds of artifact — the VERIFIED_N
tablebase and surviving CONJECTURED statements. Its actual scientific output, an exact `F(G)`
value closed by a construction that two independent certified fusion engines replay to the
target orbit, was recorded as a HEURISTIC construction with a PASS row, and therefore never
became a claim. July's eight closures (four n=8 orbits at F=8, the n=6 3-regular orbit at
F=9=N+3, two n=7 orbits at F=10=N+3, the 2×4 cluster at F=8=N) sat below the ledger's own
threshold for a year of the project's calendar.

That is a status-lattice error against spec §4.1 ("CERTIFIED: a certificate checked by a
certified verifier"), not a v1 problem. The fix touches one recording path; the charter's
"v0's inner loops are untouched" is deliberately deviated from there and nowhere else.

## What was built

- **`verify_agreed` is certified in its own right** (`verifiers/registry.py`): every P5 golden
  case is run through both engines and the agreement logic, and the stamp names the agreement
  module's source hash. `ensure_certified` issues it after the two engine stamps; the search loop
  fails closed before any paid call if it is missing.
- **An exact upgrade is a CERTIFIED claim** (`search/loop.py`): the witness JSON (already in the
  CAS) is recorded through `record_claimed_artifact` with a canonical claim row —
  `F(G) = f for the LC-orbit … (representative edges …): a construction with f fusions reaches
  the orbit (both certified fusion engines agree) and the exact tablebase's lower bound for the
  orbit is f` — and projected into the claims repository by the batch hook. A PASS witness above
  the target's rung stays a population elite (an upper bound, not a claim). Titles name the orbit
  by the tail of its LC key instead of the zero-run head.
- **Every campaign ingest path calls the batch hook**: `conjecture.submit` (CONJECTURED or
  REFUTED), `ingest_dataset` (VERIFIED_N), the exact-upgrade path; `run_campaign` ends with an
  idempotent catch-up; `run`/`resume --claims-repo PATH` (else `EMPIRICIST_CLAIMS_REPO`).
- **The conjecturer is told what is settled**: path, star and complete are FORMALIZED theorems in
  the repository ledger; the prompt names them (only when the claims repository confirms each
  theorem CURRENT). Of the conjecturer's four families only `cycle` is open.
- **`reverify --only constructions`** re-runs the certified engines over every exact-upgrade
  witness and promotes the ones meeting their recorded lower bound.

## July's closures, back-filled

`reverify --run-dir runs/p5-live --only constructions`: 8 of 8 witnesses re-verified PASS under
the live engine identities and promoted HEURISTIC → CERTIFIED, each with its claim row.
`import-ledger` wrote eight claim files:

| claim | n | F | what it closes |
|---|---|---|---|
| `P5.n6_orbit_0000000000f8` | 6 | 9 = N+3 | the sole n=6 open orbit (3-regular), Tier-2 |
| `P5.n7_orbit_00000000009c`, `P5.n7_orbit_0000000000e8` | 7 | 10 = N+3 | two of the four n=7 Tier-2 opens |
| `P5.n8_orbit_0000000000b0`, `…bc`, `…d2`, `…e8`, `…f4` | 8 | 8 = N | five n=8 orbits, one of them the 2×4 cluster |

The repository ledger went from 77 to 85 claims, `check` green (55 CURRENT, 30 SUPERSEDED).

## The live run

Resumed `runs/p5-live` (recorded spend before today $207.28; the population remembers every
solved orbit, so no closed target is re-bought). `--claims-repo .`; searcher k=32 per generation;
conjecture wave every third generation with the settled-families line in its prompt.

| phase | targets | generations | samples | screened / refuted / inserted | closures | new spend | wall |
|---|---|---|---|---|---|---|---|
| A | n=7, the 2 remaining Tier-2 opens (F=10) | 6 | 192 | 50 / 142 / 0 | 0 | $42.06 | 878 s |
| B | n=8, 54 open orbits (F=8) | 10 | 320 | 19 / 134 / 1 | 1 | $17.66 | 621 s |

Phase A is an honest negative: every one of 192 candidates for the two n=7 Tier-2 orbits was
either malformed or refuted by the engines. The model closed two of these four orbits in July;
the last two do not yield to the same prompt.

Phase B closed one n=8 orbit exactly at F=8 in generation 9021: the witness passed both
engines, met the tablebase's lower bound, was recorded CERTIFIED with its claim row, and the
batch hook wrote `claims/P5.n8_orbit_0000000000f4_2.yaml` (CERTIFIED, CURRENT) while the
campaign was still running — the first claim file an unattended run has ever produced. The
run then stalled out (three no-progress generations) and stopped itself. Two honest
qualifications. First, 166 of the 320 samples produced no usable construction: 25 were
zero-cost transport failures (exit 1, about 1.5 s each — the provider's usage limit) and 141
were paid calls that returned no artifact, against none of either kind in Phase A — the n=8
prompt draws far more empty or refused outputs than the n=7 one, and the average paid sample
cost a quarter of Phase A's ($0.06 vs $0.22), so the effective search was about 150
candidates. Second, the new claim's id carries a `_2` suffix because the family name uses the
last twelve hex characters of the LC key, which two distinct n=8 orbits share — the ids are
unique (the importer guarantees it) but the family slug should hash the whole key.

## Where the ledger stands

`claims check --repo . --min-claims 1`: 86 claims, 0 issues; standings
{CURRENT: 56, SUPERSEDED: 30}. `empiricist audit runs/p5-live`: OK.
Model spend today (M23a review + M23b phases A and B): $61.96 ($2.24 review, $42.06 phase A, $17.66 phase B).

## Deliverable 2 status

Batch: the campaign's promotions are claim files in the same format and they pass `check` —
exercised by the orchestrator test with a scripted client, by the back-fill, and by the live
run's hook and catch-up. The live run produced one such claim file and the catch-up import confirmed the projection
was already complete (idempotent: 26 artifacts re-projected, nothing changed).

## Follow-ups

- Deterministic Tier-1 at n=8 (transients to size 10, ~11.7M graphs): a timed feasibility spike
  would close the Tier-1-reachable n=8 orbits without model spend and leave the model only the
  genuinely-beyond-frontier targets.
- A `grid` family for the conjecturer (2×2, 2×3, 2×4 exact; 3×3 open) so the 2D-cluster
  conjecture can be stated and attacked in-campaign.
- A receipt path for `construction` claims (charter F4 applies to `statement` kinds today).

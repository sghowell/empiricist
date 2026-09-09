# Empiricist v1 Charter

**Date:** 2026-09-04. **Status:** draft for review. **Scope:** this page.

Empiricist v1 is v0's harness made portable across research repositories: one
git-tracked claim ledger shared by unattended campaigns and coding-agent
sessions, with staleness tracking and review receipts. It absorbs the Lem v3
design (§8) and is not a platform. Where this page conflicts with the v0 spec
(`2026-07-06-empiricist-harness-design.md`) it wins; elsewhere the v0 spec and
`docs/empiricist_harness.md` remain the source of truth for batch internals.

## 0. Definition of done

v1 succeeds when one ledger format records promotions from both modes in two
research repositories: this one, whose research content becomes the `ftfbqc`
pack, and `death_and_gravity`.

1. **Interactive.** A Claude Code or Codex session in `death_and_gravity`
   promotes a claim to CERTIFIED through `promote` with a review receipt, and
   within thirty days of first use `check` catches a genuine stale claim: a
   data manifest, certificate, or verifier version that changed under a
   promoted claim in the course of research, not induced to test the tool.
2. **Batch.** An unattended P3 or P5 campaign materializes its promotions as
   claim files in the same format, and they pass `check`.
3. **Report.** A status report rendered from claim files alone that a referee
   could audit without trusting a line of model output.

## 1. Metric and kill gate

The metric is v0's: status promotions per dollar. A promotion counts only when
it exists as a claim file that passes `check` in a research repository.

First `check` on the cosmology ledger is targeted for 2026-09-18. If by
2026-10-18 no genuine stale claim has been caught and no receipt has blocked
or revised a promotion, v1 stops: `CLAIMS.md` stays as it is and v0 keeps
running campaigns.

## 2. Invariants

F1–F5 carry over from v0. Two are re-scoped, two are added.

| # | Failure mode | Structural kill |
|---|---|---|
| F1 | Model as oracle | Nothing rises above HEURISTIC without a PASS evidence entry from a certified verifier, in either mode. The mechanism is one promotion path, not "no shell". |
| F2 | Context rot | The ledger is memory. Batch: fresh context per attempt. Interactive: sessions start from claim files and notes, never transcripts. |
| F3 | Verifier gaming | Golden-certified verifiers, two independent implementations where load-bearing. Agent-authored verifier code enters the registry only through certification, in both modes; Toolwright is un-deferred under that rule. |
| F4 | Proof by intimidation | Lemma DAGs and the Critic, plus faithfulness: elevated promotions (CERTIFIED, FORMALIZED) of `statement` claims require a receipt with no blocking issue. |
| F5 | Unbounded burn | Unchanged: per-move caps, stall detection, resume from the ledger. |
| F6 | Silent staleness | Promoted claims carry hash-locked evidence and explicit dependencies. A change to either flips standing to STALE, which blocks new promotions on top of it until re-verified. |
| F7 | Self-certification | The harness never reports on its own readiness or delivery. Progress is claim files changing in research repositories. |

**Shell rule.** Batch mode keeps "the model never gets a shell" as its sandbox
trust argument. In interactive mode the agent's shell is outside the trust
boundary: nothing it runs is evidence until a registered verifier re-runs it
through `promote`.

## 3. Ledger

Canonical, committed, inside the research repository:

- `claims/<id>.yaml`, one per claim: id; problem and frozen formulation
  version; kind (`statement`, `dataset`, `construction`); statement; level
  (v0's lattice, with `n` and coverage on VERIFIED_N and PROVED_DRAFT as a
  substatus); standing; `depends_on` (claim ids and data-manifest paths);
  `supersedes`; evidence entries (path, verifier, version, verdict, stamped
  time); receipt ids; notes.
- `claims.lock.json`: for every evidence path and dependency, the sha256 at
  promotion time plus the verifier's name, version, binary hash, and
  golden-suite hash. Only committed files are hashed; a certificate summary
  embedding the hashes of large local artifacts is the committed file.
- `receipts/<id>.json`, one per reviewer sample: reviewer (model family or
  human); claim id, statement hash, and evidence hashes reviewed; findings per
  dimension with severity; verdict. Dimensions: evidence support, assumption
  explicitness, internal consistency, ledger consistency (agreement with the
  other claims), confidence calibration, decision soundness.
- `CLAIMS.md`: rendered by `report`, never hand-edited. Existing tables are
  imported once.

SQLite stays local and uncommitted for campaign state: artifacts, populations,
frontiers, runs, cost, search events, resume. Its `claims` table becomes a
rebuildable index of the claim files.

**Standing.** CURRENT: every lock hash matches, every dependency is CURRENT,
no unclosed blocking issue. STALE: an evidence hash differs, the registry holds
a newer certified version of a verifier named in the evidence, or a dependency
is STALE or SUPERSEDED or its level is REFUTED; STALE propagates forward along
`depends_on`, a DAG. CHALLENGED: a receipt with a blocking issue exists that
no later receipt has closed. SUPERSEDED: a newer claim names this one in
`supersedes`; the row is kept. A claim whose standing is not CURRENT cannot
appear in the `depends_on` of a new promotion. STALE returns to CURRENT only
through `reverify`, which re-runs the verifiers and writes fresh evidence;
CHALLENGED only through a closing receipt; otherwise the level drops through
`demote`, which records the reason in a receipt. Levels change only alongside
an evidence entry or a receipt.

**The review bar (clarified 2026-09-06).** F4's bar is exactly "a receipt with no
blocking finding": a REVISE receipt (warnings, no blocker) warrants an elevated
promotion; its warnings stay on record in the receipt and are counted in the claim
notes for the author. A BLOCK, or any open blocking receipt on the claim, refuses.

**Dependency-level rule (decided 2026-09-06).** A claim's level may not exceed
the lowest level among the claims it depends on: `promote` refuses to widen the
gap, and `check` reports `level_inversion` (non-blocking) for records that
predate the rule or were waived. A human receipt may waive the rule for one
promotion (`review --human --waive level_inversion`); model reviews never waive.
Consequence: an imported chain is re-earned bottom-up. Dependencies that the
evidence itself pins (`prior_*_sha256` fields naming another claim's evidence
file) are added by `claims deps-from-pins`, as claim edges and as locked path
dependencies.

## 4. Two modes, one promotion path

`promote` is the only way a level rises. It checks the verifier's
certification stamp, runs the verifier on the evidence, requires PASS, requires
a matching receipt for elevated promotions of `statement` claims, requires
every dependency CURRENT, then writes evidence, lock, claim file, and the
rendered table, or refuses with a reason. The CLI wraps it; batch loops call it
in-process.

`check` recomputes hashes against the lock, validates schemas and the DAG,
propagates STALE, and exits nonzero on any level without matching evidence or
any CURRENT claim resting on a non-CURRENT one. It runs no verifiers, so it
belongs in pre-commit and CI.

`review` runs an independent reviewer (fresh context, bounty framing, two
samples for elevated promotions) or records a human review, and writes the
receipt. A blocking issue sets CHALLENGED and escalates to the gate queue.

**Batch.** v0's inner loops are untouched. When a loop promotes a claim that
has a ledger id, at CONJECTURED or above, or refutes one, it calls `promote`,
which materializes the claim file. Screened samples never leave SQLite.

**Interactive.** A skill pack shipped here and installed into the research
repository, over the CLI: `formulate` (freeze a statement and declare its
certificate interface), `promote`, `review`, `check`, `reverify`, `demote`,
`report`. The generic command verifier, a declared command with hashed inputs
and golden PASS and FAIL fixtures, is the bridge that makes existing pytest
certification suites admissible evidence in week one.

## 5. Registry and packs

v0's registry rule stands. Core owns the verifier protocol, certification, the
generic command verifier, the Lean verifier, the ledger and its commands, the
model client and roles, the batch loops, and the sandbox. A pack,
`empiricist.packs.<name>`, holds one domain's verifiers and golden suites,
screens and canonical forms, moves and playbooks, and problem documents with
frozen versions, declared in one manifest. Core imports no pack; the CLI,
config, roles, schemas, and report carry no domain names. The boundary is
proven when a second pack lands without touching core. v1 packs: `ftfbqc`
(today's P3 and P5 code) and `cosmology` (ball-arithmetic, Taylor-model,
Krawczyk, and conic-dual checkers ported from `death_and_gravity`). No plugin
system.

*Status 2026-09-07 (M24a):* `empiricist.packs` exists — a fixed namespace
(`ftfbqc`, `cosmology`, `zx`), one `PackManifest` per pack declaring verifiers
and golden suites, and the claim ledger resolving a verifier by name from the
repository's own declarations first and installed packs second
(`certify-verifier`, `promote`, `reverify`, `check` drift, `claims packs`).
`ftfbqc` is a manifest with v1 evidence adapters over the existing P3/P5
verifiers; the physical move of `domain/`, `certificates/`, `search/` and
`campaign/` under the pack, and the P3/P5 CLI verbs (`run P5`, `p3-optimize`,
`p3-ingest-results`, `certify`), are deferred as recorded debt: the cosmology
port did not demand them. `cosmology` (M24b) and `zx` (M24c) are being built
against this API in parallel; either landing without a core change is the
boundary's proof.

## 6. Human gates

v0's four: REDUCE, PROOF_CAMPAIGN, ACCEPT_DRAFT, RELEASE. Written down from
practice: promotion into the trusted foundation set is a pull request, and
CHALLENGED escalations land in the gate queue. No new gates.

## 7. Anti-scope

Kept from v0: no distributed execution, vector database, fine-tuning, web UI
beyond the report, multi-agent structure beyond Prover, Critic, and Reviewer,
or autonomous literature claims. Added from Lem's failure: no service or
daemon, TUI, host-runtime adapters beyond the skill pack, readiness or delivery
reports, fixture-only providers in production paths, phase queues, or pack
that is only a manifest and fixtures. Deferred, not banned: PROV-O or RO-Crate
export of receipts (they are plain JSON), and Toolwright in batch mode.

## 8. Lineage

This page overrides the v0 spec on the shell rule's scope (§2), repository
visibility (now public), and Toolwright (D11). Lem v3 (2026-03) is absorbed,
not continued: standing and propagation from its evidence-graph document, the
six review dimensions from its cognitive document, `supersedes` from its
exact-hash versus semantic-key split. Those documents, the lineage map, and the
GPD memo are copied to `docs/lineage/lem-v3/`; the `lem` repository is
archived.

## 9. Build order and tripwire

| By | Deliverable | Counts only if |
|---|---|---|
| 2026-09-18 | Claim files, lock, standing, `check`, generic command verifier, one-time import; `promote`, `review`, `reverify`, `demote`, `report`; skill pack; batch loops materialize claims | `check` runs green in `death_and_gravity` and one promotion goes through `promote` there |
| *status 2026-09-06 (night)* | *Met. PRs #70–#77 merged. `check` is green in death_and_gravity (51 claims, branch `empiricist-claims-import`); P8-A.1…A.7 are CERTIFIED through `promote`, each on two independent review samples with no blocking finding; P8-A.7's round-1 blocks caught a real record defect (no dependency edges) before anything was promoted over it. See `docs/science/2026-09-06-claims-trial-death-and-gravity.md`.* | *section 1's first event (a receipt blocked a genuine defect) has happened; the second (a genuine stale claim caught) has a rehearsal (verifier drift)* |
| *status 2026-09-07* | *Hygiene pass on the repository's own ledger (M23a): fourteen P3 lemmas relabelled through `relabel` + superseding claims, thirteen proven-conjecture rows superseded, a `True` "theorem" demoted on a receipt, `check` now sees built-in verifier identities, `reverify` covers certificates. See `docs/science/2026-09-07-ledger-hygiene.md`.* | *section 1's second event has happened: the SOS certificate checker had changed under `P3.k0_standard_assignment_p_avg` since PR #71 (a batch-hook edit, not induced); `check` caught it the moment it could compare built-in stamps to live identities, and the claim was re-earned through `reverify` + `import-ledger`* |
| *status 2026-09-07 (evening)* | *Deliverable 2 ("Batch") exercised live (M23b): two-engine-agreed exact witnesses are now CERTIFIED claims (one recording path deviates from "v0's inner loops are untouched", stated in the plan), every campaign ingest path calls the batch hook, and a resumed P5 run wrote `claims/P5.n8_orbit_0000000000f4_2.yaml` while running; July's eight closures were back-filled the same way. See `docs/science/2026-09-07-p5-campaign-under-v1.md`.* | *repository ledger 86 claims, `check` green; live spend $59.72 for one new exact value (n=8, F=8) and an honest negative on the two n=7 Tier-2 opens* |
| 2026-10-02 | Cosmology pack; core factored from packs as far as that port demands; `ftfbqc` extracted only as far as the factoring requires | A cosmology claim is promoted with a pack verifier and a receipt |
| *status 2026-09-08* | *Met early (M24, PRs #81–#83). `empiricist.packs` is the boundary (§5 status); `cosmology` ports death_and_gravity's ten P8 replay checkers as certified pack verifiers; `zx` (Problem 6 machinery: 29 JPV rules, four verifiers) landed as the third pack. Neither pack touched core — the boundary's proof. `ftfbqc` is a manifest with adapters; the physical extraction of its code and the P3/P5 CLI verbs remain recorded debt.* | *P8-0 in death_and_gravity is CERTIFIED on `cosmo_p8_s0` with two review receipts ($5.50); `claims check` green there (51 claims) and here (86 claims)* |
| 2026-10-18 | Kill gate review | §1 |

Any week without a claim-file change in a research repository stops feature
work until one happens. No milestone is delivered by its own tests. Core stays
under twenty thousand lines of Python.

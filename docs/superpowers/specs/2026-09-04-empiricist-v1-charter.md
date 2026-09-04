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
| 2026-10-02 | Cosmology pack; core factored from packs as far as that port demands; `ftfbqc` extracted only as far as the factoring requires | A cosmology claim is promoted with a pack verifier and a receipt |
| 2026-10-18 | Kill gate review | §1 |

Any week without a claim-file change in a research repository stops feature
work until one happens. No milestone is delivered by its own tests. Core stays
under twenty thousand lines of Python.

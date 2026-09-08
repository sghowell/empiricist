# M23b: the P5 campaign under v1 — witness closures become claims, batch hooks, first live run

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the first unattended P5 campaign whose results land as claim files that pass `check` (charter deliverable 2, "Batch"), with the campaign's real scientific output — exact `F(G)` values closed by two-engine-certified witnesses — reaching the ledger at CERTIFIED instead of staying HEURISTIC, and July's eight closures (including the 2×4 cluster) back-filled the same way.

**Architecture:** `verify_agreed` gets a derived certification stamp (it is certified exactly when both fusion engines hold current stamps), so the search loop can record an exact upgrade through `record_claimed_artifact` with a canonical claim row at CERTIFIED; every campaign ingest path (`conjecture.submit`, `ingest_dataset`, the exact-upgrade path) calls the batch hook; `run_campaign` ends with an idempotent catch-up; `CampaignState.claims_repo` comes from `--claims-repo` or `EMPIRICIST_CLAIMS_REPO`. A construction reverify pass re-runs `verify_agreed` over July's HEURISTIC upgrade witnesses and promotes the exact ones. The conjecturer is told which families the claims ledger already holds FORMALIZED.

**Tech Stack:** Python 3.11+, SQLite ledger + blake3 CAS, the P5 fusion engines (stim, GF(2)), `FakeLLMClient` for tests, `ClaudeCodeClient` for the run.

**Spec:** `docs/superpowers/specs/2026-09-04-empiricist-v1-charter.md` §1 (deliverable 2), §4 ("Batch"); harness spec §4.1 (CERTIFIED: a certificate checked by a certified verifier).

## Global Constraints

- Statuses change only alongside evidence rows; nothing rises above HEURISTIC without a PASS from a certified verifier; REFUTED is terminal.
- **Stated deviation from charter §4 "v0's inner loops are untouched":** the exact-upgrade recording path changes from (HEURISTIC + PASS row) to (CERTIFIED + claim row + PASS row). This corrects the v0 lattice to spec §4.1 for a two-engine-certified witness that meets the proven lower bound; nothing else in the loops changes. It is one function and reversible.
- Non-exact witnesses (F above the lower bound) stay HEURISTIC population elites.
- The model never gets a shell; the campaign's model calls are `runs` rows with receipts.
- Budget for the live run: `--max-cost 150` (the July run spent $141 for 1440 searcher calls). Nothing else spends.
- No AI attribution in commit messages. Branch `feat/m23b-p5-campaign-v1` off `main` after #79 merges.

---

### Task 1: exact upgrades are CERTIFIED claims

**Files:**
- Modify: `src/empiricist/verifiers/registry.py` (`certify_agreed`, `AGREED_VERSION`, `agreed_binary_hash()`)
- Modify: `src/empiricist/campaign/moves.py` (`ensure_certified` also stamps `verify_agreed`; `open_targets` fills `TargetSpec.orbit_id`)
- Modify: `src/empiricist/search/loop.py` (`TargetSpec.orbit_id: str = ""`; the exact-upgrade branch records a claimed CERTIFIED artifact; title `exact value: n={n} LC-orbit …{key[-12:]} F={f}`)
- Test: `tests/test_search_loop.py`, `tests/test_campaign_moves.py`

**Interfaces:**
- `certify_agreed(ledger) -> Certification`: stamps `verify_agreed` (version `1.0`, binary hash = `module_source_hash` of `verifiers/registry.py`, golden suite = `suite_hash()`) with PASS iff both `StabFusionVerifier` and `EnumFusionVerifier` hold current PASS stamps; otherwise raises `UncertifiedVerifierError`. Idempotent.
- `exact_value_claim(*, artifact_id, target: TargetSpec, f: int, details: dict) -> Claim` (in `search/loop.py`): statement `"F(G) = {f} for the LC-orbit {key} of connected {n}-qubit graph states (representative edges {edges}): a construction with {f} fusions reaches the orbit (both certified fusion engines agree) and the tablebase's lower bound for the orbit is {f} (Tier-0 exclusion and the mod-3 ladder)."`, family `f"n{n}_orbit_{key[-12:]}"`, metric `"min_fusions"`, scope `{n, lc_orbit_key, orbit_id, f, lower_bound, stab_fusion_id, enum_fusion_id}`.
- The exact-upgrade branch: `Artifact(kind="construction", problem="P5", status=CERTIFIED, title=…)` + `EvidenceRow(verifier="verify_agreed", version, binary_hash, golden_suite_hash=suite_hash(), claim_id=claim.id, PASS, details)` → `ledger.record_claimed_artifact(art, claim, ev, expected_golden_suite_hash=suite_hash())`, then `materialize_after_ingest(ledger, store, art.id, claims_repo=self._claims_repo)`.

- [ ] **Step 1: Failing tests** — `test_exact_upgrade_records_a_certified_claim` (scripted PASS construction meeting `target_f`: artifact CERTIFIED, one claim row with `metric == "min_fusions"`, evidence `verifier == "verify_agreed"` with `claim_id`; title has no zero-run); `test_non_exact_witness_stays_heuristic_elite`; `test_ensure_certified_stamps_verify_agreed` (after `ensure_certified`, `ledger.get_certification("verify_agreed", "1.0", agreed_binary_hash())` is PASS with the live suite hash; editing nothing keeps it idempotent); `test_certify_agreed_refuses_without_both_engines`.
- [ ] **Step 2: Run → FAIL.** **Step 3: Implement.** **Step 4: `uv run pytest tests/test_search_loop.py tests/test_campaign_moves.py tests/test_search_integration.py -p no:warnings`.** **Step 5: Commit** `M23b: exact upgrades are CERTIFIED claims (verify_agreed carries a derived stamp)`.

---

### Task 2: batch hooks on every campaign ingest path, catch-up, `--claims-repo`

**Files:**
- Modify: `src/empiricist/search/conjecture.py` (`submit(..., claims_repo=None)` calls the hook after the status-changing `record_evidence`), `src/empiricist/domain/p5/dataset.py` (`ingest_dataset(..., claims_repo=None)`), `src/empiricist/search/loop.py` (`SearchLoop(..., claims_repo=None)`), `src/empiricist/campaign/state.py` (`claims_repo: Path | None`, `load(run_dir, claims_repo=None)` defaulting to `claims_repo_from_env()`), `src/empiricist/campaign/moves.py` (thread it), `src/empiricist/campaign/orchestrator.py` (`run_campaign(run_dir, cfg, client, *, claims_repo=None)`; in `finally`, before `state.close()`: `materialize_artifacts(state.ledger, state.store, repo)` when configured, exceptions logged), `src/empiricist/cli.py` (`--claims-repo PATH` on run/resume; passed through)
- Test: `tests/test_claims_materialize.py` (submit + dataset hooks), `tests/test_campaign_orchestrator.py` (`test_run_campaign_materializes_claims_when_a_repo_is_configured`: the scripted true conjecture and the dataset appear as claim files; `check(repo).ok`), `tests/test_cli.py` (`--claims-repo` reaches `run_campaign`)

- [ ] **Step 1: Failing tests.** **Step 2: Run → FAIL.** **Step 3: Implement.** **Step 4: Run the four files + `tests/test_search_conjecture.py`.** **Step 5: Commit** `M23b: campaign ingest paths call the batch hook; end-of-campaign catch-up; --claims-repo`.

---

### Task 3: the conjecturer knows what is settled

**Files:**
- Create: `src/empiricist/domain/p5/settled.py` — `SETTLED_FAMILIES = {"path": "P5.Empiricist.pathGraph_min_fusions", "star": "P5.Empiricist.star_min_fusions", "complete": "P5.Empiricist.complete_min_fusions"}`; `settled_families(claims_repo) -> dict[str, str]`: the subset whose claim is present, FORMALIZED and CURRENT in the repository (empty when no repository).
- Modify: `src/empiricist/search/conjecture.py` (`mine(..., settled=None)`: prompt line `"Settled by a FORMALIZED theorem in the claims ledger (do not re-conjecture): path (P5.Empiricist.pathGraph_min_fusions), …"`), `src/empiricist/campaign/moves.py` (`conjecture_move` passes `settled_families(state.claims_repo)`)
- Test: `tests/test_search_conjecture.py` (prompt carries the settled line only for present FORMALIZED CURRENT claims), `tests/test_campaign_moves.py`

- [ ] Steps 1–5 as above. Commit `M23b: the conjecturer is told which families the claims ledger holds FORMALIZED`.

---

### Task 4: construction reverify (back-fill July's closures)

**Files:**
- Create: `src/empiricist/domain/p5/reverify.py` — `reverify_construction_artifacts(ledger, store, *, artifact_ids=None, dry_run=False, certify=True) -> ReverifyReport`: targets = `kind="construction"` artifacts whose latest PASS row is `verify_agreed` with `details["upgrade"] is True`; rebuild the `Construction` from the CAS JSON, `ensure` both engines and `verify_agreed` are stamped, re-run `verify_agreed`; on PASS with `f == details["target"]["target_f"]` promote through `record_claimed_artifact` (CERTIFIED, `exact_value_claim`, new PASS row); on PASS above the bound → evidence-only row, outcome `PASS` with detail `"witness above the lower bound; stays HEURISTIC"`; non-PASS → evidence-only row.
- Modify: `src/empiricist/cli.py` (`reverify --only {lean,certificates,constructions}`; default runs all three)
- Test: `tests/test_p5_reverify.py` (a HEURISTIC upgrade witness becomes CERTIFIED with a claim row; a non-upgrade witness is skipped; idempotent)

- [ ] Steps 1–5. Commit `M23b: reverify covers construction witnesses; exact ones are promoted to CERTIFIED`.

---

### Task 5: apply — back-fill `runs/p5-live` and materialise

- [ ] `sqlite3 runs/p5-live/ledger.db ".backup runs/_backup-2026-09-07/p5-live-pre-m23b.db"`
- [ ] `uv run empiricist reverify --run-dir runs/p5-live --only constructions` → expect 8 PASS promotions (4 at n=8 F=8, the n=6 F=9 and two n=7 F=10 Tier-2 closures, the 2×4 cluster F=8).
- [ ] `uv run empiricist claims import-ledger --run-dir runs/p5-live --repo .` → 8 new `P5.n{n}_orbit_…` claims at CERTIFIED; `claims check --repo . --min-claims 1` green; `audit` OK.
- [ ] Commit the data: `M23b: July's eight witness closures materialised as CERTIFIED claims`.

---

### Task 6: the live run

- [ ] Launch in the background: `uv run empiricist resume --run-dir runs/p5-live --live --max-cost 150 --claims-repo .` (defaults: search n=8, 8 targets per generation, conjecture wave every 3 generations). Log to the scratchpad; monitor `campaign summary`, `exact_upgrades`, spend.
- [ ] While it runs: nothing else spends. Every exact upgrade should appear as a claim file within the generation (the hook) and `claims check` must stay green at every look.
- [ ] After the stop: `claims import-ledger --run-dir runs/p5-live --repo .` (catch-up; idempotent), `claims report --repo . --force`, `check`, `audit`.
- [ ] Science note `docs/science/2026-09-07-p5-campaign-under-v1.md`: what closed, spend, the materialisation record, kill-gate status. Charter §9 status row. Memory.
- [ ] PR; squash-merge after CI.

## Follow-ups (not in this plan)

- Deterministic Tier-1 at n=8 (transients to size 10, ~11.7M graphs) — a timed feasibility spike; it would close the Tier-1-reachable n=8 orbits without model spend.
- A "grid" family for the conjecturer (2×2, 2×3, 2×4 exact; 3×3 open) so the marquee 2D-cluster conjecture can be stated and attacked in-campaign.
- A CERTIFIED→receipt path for construction claims (charter F4 applies to `statement` kinds today).

## Outcome (2026-09-07)

Tasks 1–6 done on `feat/m23b-p5-campaign-v1`. Fast suite 1129 passed before the live run. Back-fill: 8/8 July witnesses promoted to CERTIFIED and materialised. Live run on the resumed `runs/p5-live`: phase A (n=7, 6 generations, $42.06) closed nothing; phase B (n=8, 10 generations, $17.66) closed one orbit at F=8 and the hook wrote its claim file during the run; stall stop. Repository ledger 86 claims, `check` green, `audit` OK. Narrative: `docs/science/2026-09-07-p5-campaign-under-v1.md`. Known wart: the family slug uses the LC key's last twelve hex characters, which collide across orbits (ids stay unique via `_2`).

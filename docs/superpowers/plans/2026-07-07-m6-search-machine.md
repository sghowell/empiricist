# Empiricist M6: The SEARCH / CONJECTURE / ATTACK machine

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The model-driven inner loop (spec §9): a **SEARCH** loop where Fable-5 proposes fusion `Construction`s that are screened, canonicalized, verified by the certified A∧B pair, and retained in a no-silent-truncation population; a **CONJECTURE→auto-ATTACK** pipeline where closed-form claims mined from the `VERIFIED_N` dataset are attacked against exact data before earning `CONJECTURED`; and **stall detection**. All deterministic/offline in tests via `FakeLLMClient`; the live run is M9.

**The concrete scientific payloads (what search is FOR, post-M5c):**
1. **Open-orbit closing (SEARCH):** M5c left 59 orbits at n=8 and 336 at n=9 with only `F ≥ N`. Any verified construction achieving `F = N` for such an orbit makes it **exact** (achievability + the Tier-0 lower bound + L2's ladder). No exhaustiveness needed — a single certified witness per orbit is a permanent scientific upgrade. This is the search objective: minimize fusion count per target orbit; improvement events = a new orbit reached or a strictly better verified count for a known one.
2. **Family closed forms (CONJECTURE):** mine the exact table for `F` formulas per family (paths, cycles, stars/complete, trees, wheels…), predict values, and auto-ATTACK against (a) every exact row, (b) the `F ≡ N−3 (mod 3)` ladder + `F ≥ N−3` floor, (c) open-row lower bounds (a prediction below a proven bound is refuted). Survivors enter the ledger at `CONJECTURED` with falsification effort recorded; contradictions are `REFUTED` with the counterexample.

**Architecture:** `search/database.py` (Population over the existing ledger tables: `population` upsert/elite semantics keyed by `lc_orbit_key`, `evicted` audit log, `search_events`) · `search/schemas.py` (`ConstructionOut` — the Searcher's pydantic output: resources, steps as tagged unions `{"fuse": [a,b]}` | `{"lc": v}`, target edges; converter → `domain.p5.Construction`, ValueError-safe) · `search/loop.py` (`SearchLoop`: generation = k nonce-diverse prompts → `client.complete_many(searcher)` → parse/screen → convert → `verify_agreed` → population insert + events + evidence rows; per-candidate failures recorded, never crash the wave) · `search/conjecture.py` (`mine_conjectures`: Conjecturer role over a dataset summary → `ConjectureOut`s; `attack`: the deterministic falsifier vs table+invariants+bounds; `submit`: ledger artifacts HEURISTIC → CONJECTURED/REFUTED via `record_evidence`) · `search/stall.py` (two-signal: no-improvement generations + distinct-key diversity floor; emits `search_events`, recommends island reset/hard restart).

**Trust discipline unchanged:** the model's output is *never* trusted — every Construction goes through `verify_agreed` (certified registry); every conjecture through the deterministic attacker; population/evidence writes go through the single-writer Ledger. `attack` uses ONLY exact table rows + proven bounds/invariants — never model output — as ground truth.

**Branch:** `feat/m6-search` off `main`.

---

### Task 1: Population + events (`search/database.py`)

Thin, tested wrapper over the M1-2 schema (tables exist: `population`, `evicted`, `search_events`).

API: `Population(ledger)` — `consider(lc_orbit_key, island, cell, objective_vec, cert_hash) -> bool` (insert if new key → True/improvement; if existing key: strictly-better vec (lexicographic on [fusion_count]) → replace + log old to `evicted(reason='improved', dominated_by=new cert)` → True; worse/equal → `hit_count += 1` → False); `get(key)`, `count()`, `log_event(gen, trigger, detail)`, `events(trigger=None)`. All writes in `_tx`. Tests: upsert semantics, eviction audit rows, hit-count, event log round-trip, persistence across reopen.

Commit: `feat: search population with no-silent-truncation eviction audit`

### Task 2: Searcher schema + screen (`search/schemas.py`)

`ConstructionOut(BaseModel, extra="forbid")`: `resources: int`, `steps: list[StepOut]` where `StepOut = {"op": Literal["fuse","lc"], "args": list[int]}` (CLI-schema-safe: no unions-of-objects weirdness — flat tagged form), `target_edges: list[list[int]]`, `target_n: int`. `to_construction(out) -> Construction` (validates: fuse args len 2, lc args len 1, edges valid, size identity — raising `ScreenReject(reason)` on any violation; the SCREEN gate). `json_schema_for(ConstructionOut)` must be CLI-ready (test: additionalProperties false, JSON-serializable). Tests incl. adversarial: negative qubits, self-fusion, wrong size, garbage steps → ScreenReject with reasons (these are the millisecond screen tier of spec §4).

Commit: `feat: Searcher construction schema + screen gate`

### Task 3: The search loop (`search/loop.py`)

`SearchLoop(client, ledger, store, registry, population, config)` with `async run_generation(gen: int, targets: list[TargetSpec]) -> GenerationReport`:
1. Build k prompts (k = min(role.k, len-scaled)): each names a target orbit (representative edges, n, current-best/bound), demands a `ConstructionOut`, carries a distinct nonce + a hint block (e.g. "one intra fusion after all merges reaches F=N" for open orbits — L2/L4 as prompt physics).
2. `client.complete_many(ROLES["searcher"], prompts, schema=ConstructionOut, ledger=ledger)`.
3. Per result: not `has_artifact` → count `sample_failed`; ScreenReject → count + reason; else `verify_agreed(registry, construction)`: ERROR with disagreement → **raise F3Alarm (stop the world)**; ERROR otherwise / FAIL → counted + logged; PASS → compute achieved `lc_orbit_key` from details, `population.consider(...)`, store the Construction JSON in the CAS, and — when the achieved orbit matches a target open orbit at its lower bound — record a ledger evidence row upgrading that dataset row's claim (via a returned `exact_upgrades` list; actual dataset-row mutation is the orchestrator's job in M7 — here we emit the evidence + report).
4. `GenerationReport`: counts (sampled, screened_out, verified_pass/fail/error, improvements, exact_upgrades), all logged to `search_events`.
Tests: fully scripted `FakeLLMClient` — a wave containing [valid-improving, valid-duplicate, screen-reject, refusal/None, verify-FAIL] produces exactly the right report/population/events; the F3-disagreement path raises F3Alarm (monkeypatched verify_agreed); an exact-upgrade case (target open orbit, F=N witness) is detected. No real model calls.

Commit: `feat: search loop (screen -> verify_agreed -> population, F3 alarm, exact-upgrade detection)`

### Task 4: Conjecture + auto-ATTACK (`search/conjecture.py`) and stall (`search/stall.py`)

`conjecture.py`:
- `dataset_summary(dataset) -> str` (compact per-family table the Conjecturer sees: for named families [path, cycle, star/complete, tree-of-max-degree…], the known exact F per n with orbit lookup via `lc_orbit_key` of constructed family graphs — paths/cycles/stars/complete generated programmatically).
- `mine(client, dataset) -> list[ConjectureOut]` (Conjecturer role, k samples).
- `attack(conj, dataset) -> AttackReport`: refuted if any predicted value contradicts an exact row; or violates `F ≡ N−3 (mod 3)` or `F ≥ N−3`; or undercuts a proven lower bound on an open row. Survivor: `checked` counts recorded (the falsification effort).
- `submit(ledger, store, conj, report)`: ingest artifact (HEURISTIC), then `record_evidence` → `CONJECTURED` (attack survived, `details` = checks) or `REFUTED` (counterexample in details). Tests: a true conjecture (path F=N−3 built from real table rows) survives and lands CONJECTURED; a false one (off-by-one, mod-3-violating, bound-undercutting — three cases) lands REFUTED with the exact counterexample; ledger statuses + evidence verified; FakeLLMClient scripted.

`stall.py`: `StallDetector(config)` fed per-generation reports → `assess() -> "healthy" | "island_reset" | "hard_restart"` per spec §9 (no-improvement window = cfg.stall_window_generations; diversity = distinct new keys / window vs cfg.diversity_floor); emits recommendations only (the M7 scheduler acts). Tests: scripted report sequences hit each state.

Commit: `feat: conjecture mining + deterministic auto-ATTACK + stall detection`

### Task 5: Closeout

Full suite + ruff; push; PR to main (`M6: search/conjecture/attack machine`); final whole-branch review (integration: the loop against a REAL M5c dataset fixture + stub claude binary end-to-end — one integration test that runs a generation with the stub emitting a canned valid ConstructionOut and confirms population/evidence side-effects).

---

## Plan self-review

- Spec §9 coverage: population w/ eviction audit ✅ T1; screen cascade (parse→schema→convert-validate) ✅ T2; loop with per-candidate isolation + F3 alarm propagation ✅ T3; mandatory auto-ATTACK before CONJECTURED + REFUTED counterexamples ✅ T4; two-signal stall ✅ T4; frontier-improvement events = population improvements (documented: the global Pareto `ledger.frontier` is not wired in v0 — 1-D objectives per orbit make per-key elites the correct structure; noted for M7).
- Trust: model output only enters via verify_agreed / deterministic attack; F3 disagreement halts; evidence rows for everything; CAS for artifacts.
- Type consistency: ConstructionOut→Construction (LocalComplement steps supported via {"op":"lc"}), verify_agreed contract (PASS/FAIL/ERROR+disagreement) from M5b, Population over M1-2 tables, ROLES/complete_many/has_artifact from M4, dataset rows from M5c.
- Deferred: dataset-row mutation on exact upgrades (M7 orchestrator applies; M6 emits evidence + report), scheduler wiring of stall recommendations (M7), live Searcher runs (M9).

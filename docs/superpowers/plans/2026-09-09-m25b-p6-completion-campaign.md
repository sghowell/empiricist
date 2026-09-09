# M25b: the P6 completion campaign — a model proposes rewrite systems, the pack certifies, the ledger records

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The first paid P6 work. A pack-owned batch loop in which the model proposes one candidate rewrite system per round for the stabilizer fragment (rules by library name or inline JSON, a termination measure, a joinability depth) and the harness certifies it in cost order — soundness, termination, local confluence at residual arity ≤ 2, bounded completeness on C(2, 2, 4) and then the largest class that surveys within budget — feeding the first FAIL's witness back to the next round. Every certified property of a serious candidate becomes a claim file: PASS → VERIFIED_N over the stated class, a non-joinable pair or an incompleteness witness → REFUTED. Stop on a system passing all four on both classes, or on budget.

**Architecture:** Everything domain-specific lives in `empiricist.packs.zx.campaign` (charter §5: packs hold moves and playbooks). Core provides the model client (`ClaudeCodeClient`/`FakeLLMClient`, `complete_many` with a schema, `runs` rows in a run-directory ledger), one new generic role `proposer`, and the claim ledger (`formulate`, `promote`, `check`). A candidate system is `SystemOut` (a closed pydantic schema exported to the model). `evaluate(system)` runs the four pack verifiers on evidence payload files written under `claims/evidence/p6/cand_<id>/`, where `<id>` is the first 10 hex of the sha256 of the canonical rule JSON, and mints claims `P6.cand_<id>_{sound,terminates,locally_confluent_d<d>_k2,complete_<class>}` through `promote` with the pack verifiers already stamped in `claims/verifiers.json`. Context per round is fresh: the prompt carries the playbook, the library, the known-good seed (R0core + R1's scalar rules), and a compact history of every prior candidate's outcome and witness (never transcripts). A `phase_vertices` termination component (spiders with non-zero phase, evaluated conservatively on symbolic phases) gives the model a way to orient phase-only rules.

**Tech Stack:** Python 3.11+, pydantic 2, the zx pack, core `llm` and `claims`; `ClaudeCodeClient` for the run.

**Spec:** charter §4 ("Batch": a loop that promotes calls `promote`), §5; `docs/problems/p6-zx-v1.md`; the M25a note and loop proposal.

## Global Constraints

- Core changes limited to: one role `proposer` in `llm/roles.py` (generic wording, no domain names). Everything else under `src/empiricist/packs/zx/`, `tests/`, `claims/`, `docs/`.
- The model never gets a shell; its output is `SystemOut` JSON; nothing it says changes a level except through `promote` on a pack verifier's verdict.
- Claims only for serious candidates: a system whose rules are all sound and whose measure orients every rule. Unsound rules and un-orientable measures are model errors, fed back, never claims. Non-joinable pairs and incompleteness witnesses are facts about the system and become REFUTED claims; passes become VERIFIED_N.
- Verifier budgets are part of every claim statement (depth, arity, node budget, class); ERROR (budget) is fed back as "undecided", never recorded.
- Budget: `--max-cost 100` (recorded spend, cumulative in the run directory), `--max-rounds 16`, k = 2 proposals per round. Stop on success or either limit.
- No AI attribution in commit messages. Branch `feat/m25b-p6-completion` off `main`.

---

### Task 0: the classes (measured)

- [x] Measured (enumeration only, budget 2,000,000): C(3, 2, 4) 235,799 diagrams in 10.2 s; C(2, 2, 5) 241,143 in 9.8 s; C(2, 2, 6) 563,975 in 23.7 s; C(3, 3, 4) exceeds 2,000,000 (107 s). The campaign checks C(2, 2, 4) first, then C(3, 2, 4) (three wires: the first class with two-qubit maps), then C(2, 2, 6); the full check costs roughly three times the enumeration.

### Task 1: a phase-aware termination component

**Files:** `src/empiricist/packs/zx/termination.py`, tests.

- Components `phase_vertices` (spiders with non-zero phase) and `pi_vertices` (phase exactly π). On a pattern vertex with a symbolic phase the contribution is an interval [0, 1]; `check_rule` compares the LHS lower bound against the RHS upper bound (base = lo(LHS) − hi(RHS)), so a decrease is only ever claimed when it holds for every grounding. Structural components are unchanged (lo = hi). Residual legs do not carry phases. Tests: `hadamard-on-a-state` rules (ground) decrease `hadamard_edges` after tying on `phase_vertices`; a symbolic rule cannot be shown to decrease `phase_vertices`; the existing goldens still certify (their measures are structural).
- [ ] Commit `M25b: phase-aware termination components with conservative symbolic evaluation`.

### Task 2: `SystemOut`, the playbook prompt, `evaluate`

**Files:** `src/empiricist/packs/zx/campaign.py`, `src/empiricist/llm/roles.py` (`proposer`: "You are the Proposer. Given a problem statement, a formal object schema, the verified facts so far and the exact witnesses of earlier failures, propose ONE candidate object that addresses the last failure without breaking earlier passes. Emit only the schema."), `tests/test_packs_zx_campaign.py`.

- `SystemOut(_Closed)`: `rules: list[str | dict]` (library names forward, or inline rule JSON incl. reversed library rules), `measure: list[str]`, `depth: int (1..6)`, `rationale: str`.
- `candidate_id(system) -> str`; `write_payloads(repo, cid, system, classes) -> dict[verifier, evidence_rel]`.
- `evaluate(repo, system, *, classes, star_legs=2, max_nodes=20000) -> Evaluation(cid, steps: list[(verifier, verdict, detail)], serious: bool, success: bool, claims: list[str])`: order soundness → termination → critical pairs → completeness per class; stop at the first non-PASS; ERROR is `undecided`. Claims per the constraints, statements generated from a template naming the rules (library names, inline rule names with their JSON in the evidence file), the measure, depth, arity, class, and counts.
- `build_prompt(history: list[Evaluation], seed, classes, nonce) -> str`: the P6 (ii)(a) goal in three sentences; the formulation's rule/matching semantics in a paragraph; the JSON of every library rule (name, lhs, rhs, residual, reference) and how to reverse one; the measure components; the four verifiers' contracts and budgets; the seed system and why it passes; then per prior candidate: its rules, which step failed, the witness (non-joinable pair's overlap and both results; the incompleteness pair) or "passed all"; finally the instruction to emit one `SystemOut`.
- Tests with `FakeLLMClient`: an unsound candidate is not serious and mints no claim; a sound, terminating candidate with a non-joinable pair mints two VERIFIED_N claims and one REFUTED; the seed system evaluated on C(2, 1, 2) mints a complete claim; `candidate_id` is stable under rule reordering of the same set; `check(repo)` green after each evaluation.
- [ ] Commit `M25b: the completion move — SystemOut, the playbook prompt, evaluate with claim minting`.

### Task 3: the loop and the driver

**Files:** `src/empiricist/packs/zx/campaign.py` (`run_campaign`), `src/empiricist/packs/zx/__main__.py` (driver: `python -m empiricist.packs.zx campaign --repo . --run-dir runs/p6-completion --max-cost 100 --max-rounds 16 [--k 2] [--classes 2,2,4;...] [--fake <scripted json>]`).

- `run_campaign(client, repo, run_dir, *, max_rounds, max_cost, k, classes, now=None) -> CampaignReport`: per round, `k` prompts (nonce-diversified), `complete_many(role=proposer, schema=SystemOut, ledger=run ledger)`, parse (schema-invalid → feedback "invalid schema" for that slot), `evaluate` each, append to history, stop on success or limits; spend read from the run ledger between rounds (like the P5 loop); every round logged as a `search_events`-style JSON line in `run_dir/campaign.jsonl`.
- Tests: a scripted three-round campaign with `FakeLLMClient` (invalid JSON, an unsound system, then the seed-plus-colour-change system) stops on success with the expected claims; the budget stop; the round limit.
- [ ] Commit `M25b: the P6 completion loop and its driver`.

### Task 4: the live run

- [ ] `uv run python -m empiricist.packs.zx campaign --repo . --run-dir runs/p6-completion --max-cost 100 --max-rounds 16 --k 2` in the background with a log; monitor rounds, spend, claims minted; `claims check` stays green throughout.
- [ ] After the stop: `claims report --force`, `check`, a science note `docs/science/2026-09-09-p6-completion-campaign.md` (rounds, spend, the candidates and their fates, what a passing system looks like or why none passed), plan outcome, memory, PR.

## Honest ceiling

A system passing all four is sound, terminating, locally confluent at residual arity ≤ 2 within the stated depth, and complete for two bounded classes. It is not proven confluent on all hosts (the critical-pair lemma for star rules is not established) and not proven complete for the fragment. Those are the next milestones, not this one.

## Outcome (2026-09-09, first run)

Tasks 0–3 done (Task 1 by the coordinator; Tasks 2–3 by a subagent on `feat/m25b-p6-loop`, rebased in): `phase_vertices`/`pi_vertices` with conservative symbolic bounds; `campaign.py` (`SystemOut`, the playbook prompt, `evaluate` with claim minting, `run_campaign`), the `proposer` role, the `python -m empiricist.packs.zx campaign` driver; 21 loop tests. Task 4, the live run: rounds 1–2 produced three serious candidates (sound, terminating, locally confluent at depth 4 / arity ≤ 2; each incomplete for C(2, 2, 4) with a certified witness — the zero-scalar class, then the two-spider scalar, then a one-output state with a Hadamard self-loop), 16 claim files, $6.64; from round 2 on the proposer calls hung to the 1800 s timeout (usage-limit stalls) and the run was paused after round 3 (resumable from `campaign.jsonl`). Process: editing `termination.py` mid-milestone moved `zx_termination`'s identity; the loop refused the `terminates` promotion until the stamp was renewed. Follow-ups: a transport stall detector in the loop; resume the run when the provider is responsive. Ledger: 108 claims, `check` green. Narrative: `docs/science/2026-09-09-p6-completion-campaign.md`.

### Run 2 (2026-09-09, after M25c's stall detector)

Rounds 4–9, $9.60 more (total $16.24), thirteen more claims (29 in all, ledger green at 122). Four serious candidates; the best, `cand_4a10138ea8` (39 rules), is locally confluent at depth 5 over 6,521 critical pairs and fails C(2,2,4) on a zero-map pair — the finding that the zero class is not local under up-to-scalar semantics (see the note). The run stopped itself with `transport_stall` after two empty rounds. Next: a formulation decision on the zero class (`p6-zx-v2`: unique normal forms on non-zero classes plus a certified zero criterion), then resume.

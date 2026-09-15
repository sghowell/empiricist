# M26c: slow is not stalled — proposer timeouts, unrecorded spend, and the stall detector

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the P6 campaign from killing its own proposals and from under-counting what it spends. The run ledger shows that every successful proposer call since round 2 emitted 22k–56k output tokens at roughly 78 tokens/s (269–724 s wall), so the 600 s `--proposer-timeout` M25c introduced kills any proposal past about 45k tokens; the stall detector then reads two such rounds as a transport stall and stops the run. A killed call is billed for everything it generated but records `cost_usd = 0` (the ledger's `spent()` docstring says so: a lower bound; "a capped campaign must reserve in-flight cost against the cap"), so the run's recorded $16.24 understates real spend by the thirteen killed calls.

**Architecture:** Three changes in `empiricist.packs.zx.campaign` and its driver, no core change. (1) The default proposer timeout becomes 1500 s (a 60k-token proposal at the measured rate), and the playbook tells the model to reuse earlier inline rules by name and never re-emit their JSON. (2) `unrecorded_estimate(ledger)` charges every killed proposer call (exit code −9, no cost) at the ledger's observed cost-per-second of generation for successful proposer calls (`mean(cost_usd / wall_s)`, or 0 with no such call) times its wall time; the cost cap compares `recorded + estimate` against `--max-cost`, and every `round` and `stop` log record carries `spent_usd`, `unrecorded_usd` and `timeouts`. (3) A round whose calls all died at the timeout is a `timeouts` round; two in a row stop the run with reason `proposer_timeout` (exit code 3, as for `transport_stall`), and the driver prints the measured output rate and the timeout to raise.

**Tech Stack:** Python 3.11+, the zx pack, the run ledger (`Ledger.conn`, `runs` rows).

**Spec:** charter §4; `docs/superpowers/plans/2026-09-09-m25b-p6-completion-campaign.md` (budget constraint: "`--max-cost 100` (recorded spend)") — amended here to recorded plus the estimate for killed calls.

## Global Constraints

- Core untouched (the ledger method is a follow-up); only `src/empiricist/packs/zx/`, `tests/`, `docs/`.
- The estimate is conservative: a killed call is charged for its whole wall time at the observed rate (an upper bound, since generation may have ended before the kill).
- No AI attribution in commit messages. Branch `feat/m26c-slow-is-not-stalled` off `main`.

---

### Task 1: unrecorded spend and timeout rounds

**Files:** `src/empiricist/packs/zx/campaign.py`, `src/empiricist/packs/zx/__main__.py`, `tests/test_packs_zx_campaign.py`.

- `killed_proposer_runs(ledger) -> list[(run_id, wall_s)]` (exit code −9, cost 0, wall > 0, role proposer), `generation_rate(ledger) -> float` (mean cost/wall over successful proposer calls with wall > 0), `unrecorded_estimate(ledger) -> float`.
- `run_campaign`: `spent = recorded + unrecorded` for the cap; `timeouts` per round = killed proposer runs started in that round; `empty_rounds` counts rounds with no artifact as before, `timeout_rounds` counts rounds where every call was killed; stop reasons `proposer_timeout` (timeout rounds ≥ `max_empty_rounds`) or `transport_stall`; log fields `unrecorded_usd`, `timeouts`.
- Driver: `--proposer-timeout` default 1500; exit code 3 for both stall reasons; the report line states recorded, estimated unrecorded, and timeouts.
- Tests: a ledger with two successful and one killed proposer row gives the expected estimate; a client that records a killed row per call makes the run stop with `proposer_timeout` after two rounds; the budget stop triggers on recorded + estimate.
- [x] Commit `M26c: killed proposer calls count against the cap; timeout rounds stop with proposer_timeout; 1500 s default`.

### Task 2: the playbook asks for names, not JSON

- The task paragraph: "Reuse a rule listed under 'Inline rules proposed so far' by its name; never re-emit its JSON. Give JSON only for a rule that is new." Test: the string is in the prompt.
- [x] Commit `M26c: the playbook asks for rule names, not re-emitted JSON`.

### Task 3: the record and the relaunch

- [x] Science note `docs/science/2026-09-15-p6-slow-is-not-stalled.md` (a note of its own; the M25b note carries a correction): the measured rates, the thirteen killed calls, the estimate, the corrected spend picture for runs 1–3.
- [x] Relaunch: `campaign --run-dir runs/p6-completion --max-cost 100 --max-rounds 16 --k 2 --classes "2,2,4;3,2,4;2,2,6" --proposer-timeout 1500`; the cap now includes the estimate for the earlier killed calls.

## Outcome (2026-09-15)

Tasks 1–2 done in one commit on `feat/m26c-slow-is-not-stalled` (the two tasks touch the same functions): `killed_proposer_runs`, `generation_rate` (totals over totals, so short cache-heavy calls do not skew it), `unrecorded_estimate`; the cap on recorded plus estimate; `timeouts` per round, `timeout_rounds`, stop reason `proposer_timeout`; driver default 1500 s, exit code 3 for both stall reasons, the rate printed; the playbook's names-not-JSON sentence. Three new tests. Measured on `runs/p6-completion`: 78.5 output tokens/s, $0.0057/s; 15 killed calls (12,601 s), estimate $71.78, effective $88.01. Run 3 (2026-09-09) minted nothing: rounds 10–11 were four 600 s kills. Task 3: the note, the correction in the M25b note and the charter row, the relaunch with `--proposer-timeout 1500`.

### Run 4 (2026-09-15)

Rounds 12–13 under the corrected cap, then `budget` (recorded $26.34; sixteen killed calls charged $84.28). Two serious candidates (44 and 42 rules), both REFUTED at local confluence before completeness ran; six claims, ledger 138 green. One successful call emitted 106k output tokens in 1,441 s ($6.54) while its sibling died at 1,500 s; the next round's two calls took 50–65 s. Follow-ups: streaming token accounting in the transport so a killed call records its cost; a deliberation cap in the proposer role card. See the note's run-4 section.

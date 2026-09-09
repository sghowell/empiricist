# M25a: P6 groundwork — rule soundness, completeness checking, arity-explicit confluence, the first P6 claims

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the three load-bearing gaps the zx pack recorded before any completion attempt on Problem 6 (ii)(a) — rule soundness as a certified verifier, a completeness check against the semantic oracle, and confluence statements that are explicit about residual arity — and mint the first P6 claim files from them, so the ledger holds machine-verified facts about the stabilizer rewrite theory (including honest REFUTED rows) before a model proposes anything. No model calls in this milestone.

**Architecture:** Two new pack verifiers in `empiricist.packs.zx`: `zx_rule_sound` (every rule in a payload, grounded over the fragment's phases with up to `star_legs` residual legs per star vertex, is semantically an equation up to scalar) and `zx_completeness` (every diagram in an enumerated bounded class of stabilizer diagrams reduces under the payload's rules to a normal form, and semantically equal diagrams share one; a FAIL is a certified counterexample pair). The existing `zx_critical_pairs` gains a `per_arity` detail (joinability at each residual arity 0..star_legs) so a claim can state exactly what was checked. Claim files under `claims/` with problem `P6`, formulation `p6-zx-v1`, whose problem document defines the pack's rewriting relation and what "locally confluent at residual arity ≤ k" means.

**Tech Stack:** Python 3.11+, numpy; the zx pack (`diagram`, `rules`, `rewrite`, `semantics`, `critical_pairs`, `termination`, `verifiers`); the claim ledger CLI (`formulate`, `certify-verifier`, `promote`).

**Spec:** `docs/open_problems_ftfbqc.md` Problem 6; `docs/superpowers/plans/2026-09-07-m24c-zx-pack.md` outcome (gaps 1–3); charter §3 (levels), §5 (packs).

## Global Constraints

- Core is not touched; only `src/empiricist/packs/zx/`, `tests/`, `claims/`, `docs/`.
- Verifiers are total and pure; ERROR means "could not judge" (budgets, malformed payloads), never a verdict.
- Every new verifier ships PASS and near-miss FAIL goldens.
- Levels are earned: a claim's level is what its evidence entry supports. A property checked exhaustively over a bounded, explicitly stated class is VERIFIED_N (`n` = the number of instances or pairs checked, `coverage: exhaustive`); a universal statement refuted by a certified FAIL is REFUTED (terminal) and stays in the ledger as a data point.
- No model spend. No AI attribution in commit messages. Branch `feat/m25a-p6-groundwork` off `main`.

---

### Task 1: `zx_rule_sound`

**Files:** `src/empiricist/packs/zx/soundness.py` (engine), `src/empiricist/packs/zx/verifiers.py` (`ZXRuleSoundVerifier`, `GOLDENS` entry), `src/empiricist/packs/zx/goldens/zx_rule_sound__*.json`, `src/empiricist/packs/zx/__init__.py` (manifest), `tests/test_packs_zx.py`.

**Contract.** Payload `{"rules": [names or inline rules], "fragment": "clifford"|"clifford+t" (default clifford+t), "star_legs": 0..2 (default 1), "max_instances": int (default 4096)}`. For each rule: ground every variable over the fragment's phases (all combinations), and for each star vertex every sequence of 0..`star_legs` extra boundary legs with plain/Hadamard flags (all combinations across stars); build the LHS instance as in the test helper `instance()`, apply the rule with the identity matching, evaluate both sides with `semantics.matrix`, compare with `equal_up_to_scalar`. Instances over the semantic budget are skipped and counted; a rule with zero judged instances is ERROR ("unjudgeable"), as is exceeding `max_instances`. PASS iff every judged instance of every rule is an equation; FAIL names the rule, the bindings, the leg configuration and the two matrices' first differing entry. Details always carry `instances`, `skipped`, per-rule counts.

**Engine API.** `soundness.check(rules: Mapping[str, Rule], *, phases, star_legs, max_instances) -> SoundnessReport(rules, instances, skipped, failure: RuleFailure | None, per_rule)`; `soundness.instances_of(rule, phases, star_legs) -> Iterator[(bindings, legs, host)]`.

**Goldens.** PASS: the 24 Clifford library rules at `star_legs` 1, fragment clifford; the five Clifford+T rules at `star_legs` 0. FAIL (near misses): colour change with the residual flip removed (sound with no legs, unsound with one — the golden uses `star_legs` 1); `pi_commute` with `-a` replaced by `a` on the RHS; `identity_z_h` with the Hadamard flag dropped on the RHS edge.

- [ ] Steps: failing tests (engine on fusion/colour_change; verifier PASS/FAIL/ERROR; goldens certify) → implement → `uv run pytest tests/test_packs_zx.py -p no:warnings` → commit `M25a: zx_rule_sound — rule soundness as a certified pack verifier`.

---

### Task 2: `zx_completeness`

**Files:** `src/empiricist/packs/zx/completeness.py` (enumeration + normal forms), `verifiers.py` (`ZXCompletenessVerifier`), goldens, manifest, tests.

**Contract.** Payload `{"rules": [...], "fragment": "clifford" (only; ERROR otherwise), "max_wires": 0..3 (default 2), "max_vertices": 0..4 (default 3: interior spiders), "max_edges": int (default 6, counting multiplicity; self-loops allowed), "max_steps": int (default 200: rewrite steps per diagram before ERROR "does not terminate within budget"), "max_diagrams": int (default 20000)}`. Enumerate every well-formed diagram in the class up to isomorphism (canonical dedup): interior vertices of kind Z/X with phases in the fragment's set, boundary vertices as inputs then outputs with `wires_in + wires_out ≤ max_wires`, edges as a multiset over vertex pairs with a Hadamard flag; skip diagrams over the semantic budget. Reduce each to a normal form by applying the first applicable rule (deterministic order: rules in payload order, matchings in `find_matchings` order) until none applies; canonicalise. Group diagrams by semantic class (matrix up to scalar; zero matrices form one class) — PASS iff every class maps to exactly one normal form (up to isomorphism); FAIL names a witness: two enumerated diagrams that are semantically equal with different normal forms (both diagrams and both normal forms in the details). ERROR on any budget. Details carry `diagrams`, `classes`, `normal_forms`, `steps_max`.

**Engine API.** `completeness.enumerate_diagrams(phases, max_wires, max_vertices, max_edges, max_diagrams) -> list[Diagram]`; `completeness.normal_form(d, rules, max_steps) -> Diagram`; `completeness.check(rules, *, phases, max_wires, max_vertices, max_edges, max_steps, max_diagrams) -> CompletenessReport`.

**Goldens.** PASS: the wire-only class (`max_vertices` 0) under any rules (every class has one diagram); the class `max_wires` 2, `max_vertices` 1, `max_edges` 2 under {identity_z, identity_x, identity_z_h, identity_x_h, identity_z_hh, identity_x_hh, loop_z, loop_x, loop_z_h, loop_x_h} — verify by running it; if it FAILs, keep the smallest PASSing class you find and record why in the outcome. FAIL (near miss): the same class with `identity_x` removed (an X(0) wire and a Z(0) wire are equal but only one reduces).

- [ ] Steps as in Task 1; commit `M25a: zx_completeness — bounded completeness check against the semantic oracle`.

---

### Task 3: arity-explicit confluence and the problem document

**Files:** `src/empiricist/packs/zx/critical_pairs.py` (`check(..., per_arity=True)` records, per rule pair, joinability at each `star_legs` value 0..k), `verifiers.py` (`zx_critical_pairs` detail `per_arity`), `docs/problems/p6-zx-v1.md`.

- `per_arity`: when set, `check` runs the enumeration at each `star_legs` in 0..k and reports `{arity: {pairs, overlaps, joined, failures}}`; the verdict is unchanged (PASS iff joinable at the requested `star_legs`). Tests: the `{fusion, identity_z}` set at depth 1 is joinable at every arity 0..2.
- `docs/problems/p6-zx-v1.md`: the frozen formulation the P6 claims name: the diagram model (open multigraph, Z/X/B, phases in k·π/4, plain/Hadamard edges), the pack's rewriting relation (matching conditions: injective on spiders, identification condition for interface images, degree-exact non-stars, star residual legs re-attached with flips), what a rule is (LHS/RHS over a shared interface, `residual`), semantic equality up to non-zero scalar, "sound", "terminating under measure M", "locally confluent within depth d at residual arity ≤ k", "complete for the class C(w, v, e)"; the statement that the critical-pair lemma for star rules is not established (a confluence claim at arity ≤ k is exactly that, no more); references [20], [21].
- [ ] Commit `M25a: critical pairs per residual arity; the p6-zx-v1 problem document`.

---

### Task 4: the first P6 claims

In this repository's `claims/` (problem `P6`, `formulation_version: p6-zx-v1`), evidence files under `claims/evidence/p6/`, verifiers certified into `claims/verifiers.json` with `certify-verifier --name zx_*`.

1. **P6.clifford_rules_sound** — statement: "Each of the 24 Clifford rules of the zx pack's JPV library (listed) is a semantic equation up to a non-zero scalar on every stabilizer instance with up to 2 residual legs of each type per star vertex." Evidence: `zx_rule_sound` payload (rules = CLIFFORD_RULES, fragment clifford, star_legs 2). Level VERIFIED_N, `n` = judged instances, `coverage: exhaustive` (of the stated class).
2. **P6.jpv_clifford_oriented_not_locally_confluent** — statement: "The 24 Clifford rules oriented left-to-right form a locally confluent system within depth 5 at residual arity ≤ 1." Evidence: `zx_critical_pairs` (depth 5, star_legs 1, max_nodes 20000) → FAIL → promote to REFUTED with the witness (the bialgebra/colour_change pair). Terminal; the ledger's first P6 data point.
3. **P6.graphlike_core_terminates_and_is_locally_confluent** — the candidate core R0 = {fusion, fusion_x, identity_z, identity_x, identity_z_h, identity_x_h, identity_z_hh, identity_x_hh, loop_z, loop_x, loop_z_h, loop_x_h, hopf_h}: statement "R0 is terminating under the lexicographic measure (vertices, edges) and locally confluent within depth 4 at residual arity ≤ 2." Two evidence entries: `zx_termination` PASS and `zx_critical_pairs` PASS (per_arity 0..2). If either FAILs, shrink R0 (drop hopf_h first) until both PASS and state the surviving set; record every FAIL as its own REFUTED claim about the larger set. Level VERIFIED_N (`n` = critical pairs checked, exhaustive at the stated arity).
4. **P6.graphlike_core_incomplete_c2_3_6** — statement: "R0 is complete for the class C(2, 3, 6) of stabilizer diagrams (≤ 2 boundary wires, ≤ 3 interior spiders, ≤ 6 edges)." Evidence: `zx_completeness` → expected FAIL (a subset cannot be complete) → REFUTED with the witness pair. If it unexpectedly PASSes, the claim is VERIFIED_N and worth a science note.

Each claim: `formulate` → `promote --verifier zx_… --evidence …` (REFUTED via `--level REFUTED` on a FAIL, which needs a receipt at ≥ CONJECTURED only — these start at HEURISTIC, so no receipt), `claims check --min-claims 1` green, `claims report`.

- [ ] Commit `M25a: the first P6 claims — soundness, an oriented-JPV non-confluence witness, the graph-like core, a bounded incompleteness witness`.

---

### Task 5: note, outcome, PR

- `docs/science/2026-09-09-p6-groundwork.md`: what the verifiers judge, the four claims with their numbers (instances, pairs, wall times), the REFUTED witnesses, and what M25b (the completion campaign) will do with them.
- Plan outcome; full fast suite; ruff; `claims check`; PR; squash-merge on green.

## Next (M25b, not here)

The completion move: the model proposes orientations of the JPV equations and auxiliary rules for the stabilizer fragment; the pack certifies soundness, termination, local confluence at arity ≤ k, and bounded completeness; the ledger records every PASS as a claim and every FAIL as a REFUTED row; stop when a system passes all four on C(2, 3, 6) and C(2, 4, 8). Budget on the order of $100.

## Outcome notes (verifiers)

Tasks 1, 2 and the code half of Task 3, branch `feat/m25a-zx-verifiers` (three commits, one per task). The manifest declares six verifiers; every one certifies in a temporary repository through `certify_pack_verifier`.

### `zx_rule_sound` (Task 1) — as planned

Engine `packs/zx/soundness.py`: `instances_of(rule, phases, star_legs)` yields `(bindings, legs, host)` — variables in name order over the fragment's phases (all combinations), then for each star vertex every *multiset* of 0..`star_legs` residual legs, plain or Hadamard, all combinations across stars; the host is the LHS as in the old test helper `instance()`; the rule is applied through the identity matching; both sides go through `semantics.matrix` and `equal_up_to_scalar`. `check(rules, *, phases, star_legs, max_instances)` refuses the class *before any work* when its total instance count exceeds `max_instances`, skips and counts instances over the semantic budget, stops at the first non-equation (`RuleFailure`: rule, bindings, legs, host, result, first differing entry after scalar alignment), and raises "unjudgeable" when some rule has no judged instance and no rule failed (a FAIL wins over an unjudgeable sibling). Verifier payload exactly as the plan: `rules`, `fragment` (default clifford+t), `star_legs` 0..2 (default 1), `max_instances` (default 4096); details always carry `instances`, `skipped`, `per_rule`, `rules`, `fragment`, `star_legs`. The fragment phase sets moved from `critical_pairs` to `rules` so both engines hash one definition.

Numbers (this laptop): the 24 Clifford rules, clifford phases — 663 instances at `star_legs` 1 in 0.09 s, 2451 at `star_legs` 2 in 0.46 s (fits the default budget, no skips); the five Clifford+T rules at `star_legs` 0 — 530 instances (512 of them `commute_controls`) in 0.40 s; all 29 library rules, clifford+t phases, `star_legs` 1 — 2997 instances in 0.72 s, all equations. Goldens: `clifford_rules_star_legs_1` PASS, `clifford_t_rules_star_legs_0` PASS, `colour_change_no_flip` FAIL (at a = 0 with one plain leg: the X(0) state against the Z(0) state, entry [1, 0]), `pi_commute_wrong_sign` FAIL (at a = 1/2: entry [2, 0] is i against −i), `identity_z_h_no_h` FAIL (H against the wire). The FAIL goldens each list the sound library rule next to its broken twin.

### `zx_completeness` (Task 2) — as planned, with one finding about the goldens

Engine `packs/zx/completeness.py`: `enumerate_diagrams` builds every well-formed diagram of C(w, v, e) — every (inputs, outputs) split with inputs + outputs ≤ w, every multiset of ≤ v (kind, phase) labels, every boundary attachment (each boundary vertex to a spider or to a later boundary vertex, plain or Hadamard), every multiset of ≤ e − (boundary edges) interior edges including self-loops — canonicalises each and dedups (smallest first). `reduce` applies the first applicable rule in payload order, its first `find_matchings` matching, until none applies (`CompletenessError` past `max_steps`). `check` computes every matrix first (semantic key: wire signature + the matrix scaled by its first entry of maximal magnitude, rounded to 6 places, confirmed against the bucket's representative with `equal_up_to_scalar`; zero matrices one class per signature), then reduces the diagrams in enumeration order and **stops at the first class that shows a second normal form** — so a FAIL costs a few reductions and its witness is the smallest pair in enumeration order. Details: `diagrams`, `skipped`, `classes` (always complete), `reduced`, `normal_forms` and `steps_max` (over the diagrams reduced before the verdict — all of them on a PASS). Payload as planned (`fragment` clifford only, `max_wires` 0..3 default 2, `max_vertices` 0..4 default 3, `max_edges` 0..16 default 6, `max_steps` default 200, `max_diagrams` default 20000).

**The plan's PASS golden class fails, for a reason that matters for M25b: scalars count.** C(2, 1, 2) has 391 diagrams in 59 semantic classes; under the ten identity/loop rules the first witness is the empty diagram against the 0-leg Z(0) — both non-zero scalars, hence one class, both normal forms. Every class with `max_vertices` ≥ 1 contains the six non-zero 0-leg spiders (Z/X at 0, π/2, 3π/2), so no such class passes under those rules, and the only PASSing classes are wire-only. The shipped PASS golden `one_spider_two_wires` keeps the plan's class and adds `colour_change` plus nine sound inline rules (checked with `zx_rule_sound`): six scalar eliminations (a non-zero 0-leg spider is the empty diagram), two Hadamard-on-a-state rules (Z(π/2) with a Hadamard leg is Z(3π/2) with a plain leg, and vice versa), and one zero absorption (next to the zero scalar Z(π) a Hadamard wire is a plain wire, both sides being zero) — 20 rules, 391 diagrams, 59 classes, 59 normal forms, at most 4 steps, 0.12 s. Near misses: `one_spider_two_wires_no_identity_z_hh` FAIL (witness: the plain cup against Z(0) with two Hadamard legs; found after 151 of 391 reductions) and `one_spider_two_wires_no_scalar_rules` FAIL (the plan's ten rules alone; the scalar witness above). The plan's stated near miss — remove `identity_x` — does not fail in this set because colour change makes `identity_x` redundant (X(0) with two plain legs → Z(0) with two Hadamard legs → wire); `identity_z_hh` is the rule whose removal reproduces the intended "a wire-shaped spider does not reduce" witness. The wire-only golden `wires_only` (C(2, 0, 2), 7 diagrams, 7 classes) PASSes as planned.

Enumeration sizes and wall times (up to isomorphism; raw candidates before dedup in parentheses): C(2, 0, 2) = 7 (7); C(2, 1, 2) = 391 (391); C(2, 2, 3) = 27 095 (30 087), 1.1 s; C(2, 2, 4) = 89 367 (99 783), 3.8 s; C(2, 3, 4) > 300 000 (2 480 343 raw); **C(2, 3, 6) has 39 813 303 raw candidates** — at the measured ~26 000 candidates/s the enumeration alone is ~25 minutes and the class holds tens of millions of diagrams, so the plan's default `max_diagrams` (20 000) is exceeded after 0.6 s and the verifier reports ERROR, honestly. The class C(2, 3, 6) named in Task 4 is out of reach for an exhaustive Python enumeration; C(2, 2, 4) (89 367 diagrams, 199 semantic classes) is the largest class checked here. R0 (the graph-like core of Task 4) FAILs on C(2, 1, 2) and on C(2, 2, 4) in 0.0 s and 10.1 s with the same scalar witness (empty diagram against the 0-leg Z(0)); on C(2, 3, 6) with the default budget it is ERROR. A bounded incompleteness claim about R0 can be minted on C(2, 2, 4) (or C(2, 1, 2)); the witness is the scalar pair, which is the true first obstruction — any system for the stabilizer fragment "up to scalars" needs rules for closed components or a formulation that quotients them out.

### `zx_critical_pairs` per arity (Task 3, code)

`critical_pairs.check(..., per_arity=True)` runs the enumeration at every residual arity 0..`star_legs` and records `per_arity: {arity: {pairs, overlaps, joined, failures}}` (`failures` bounded by `max_failures`); the verdict is that of the requested arity, and since the arity-k enumeration contains every lower-arity leg configuration, PASS at k implies PASS below. The verifier accepts the boolean `per_arity` and, when set, carries the detail keyed by arity as strings. {fusion, identity_z} at depth 1 is joinable at every arity 0..2 (overlaps strictly increasing with arity).

Data points for Task 4's R0 (measured here, no claim files written). R0 with `hopf_h` terminates under (vertices, edges) but is **not** locally confluent within depth 4 at any arity: the `hopf_h`/`identity_z_hh` peak on Z(0) and Z(b) joined by two Hadamard edges (no other legs) gives Z(0) ⊗ Z(b) by `hopf_h` and Z(b) by `identity_z_hh` then `loop_z`; equal up to the scalar Z(0) = 2, not joinable (the same scalar obstruction as in completeness) — arity 0: 32 pairs, 55 overlaps, 0.1 s; arity 1: 679 overlaps, 1.2 s; arity 2: 4345 overlaps, 10.2 s with `per_arity`. R0 without `hopf_h` (the plan's fallback) PASSes both: termination under (vertices, edges), and local confluence within depth 4 at arity ≤ 2 — 78 pairs; overlaps 68 / 432 / 2388 at arity 0 / 1 / 2, all joined, no case split, 5.0 s (clifford phases, `max_nodes` 20000).

### Tests and lint

`tests/test_packs_zx_p6.py` (new, 18 tests) and `tests/test_packs_zx.py` (six-verifier manifest; the golden, certification and totality tests are parametrised over all six): 124 collected across the two files. `ruff check src tests` clean.

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

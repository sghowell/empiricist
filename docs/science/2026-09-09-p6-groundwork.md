# P6 groundwork: the first machine-verified facts about ZX rewriting in the ledger

**Date:** 2026-09-09 · **Problem:** P6 (proof complexity and confluence of ZX rewriting),
formulation `p6-zx-v1` (`docs/problems/p6-zx-v1.md`) · **Milestone:** M25a
(`docs/superpowers/plans/2026-09-09-m25a-p6-groundwork.md`) · **Model spend:** none.

## What the verifiers judge

Every statement below is about the zx pack's own rewriting relation (matching injective on
spiders, identification condition on interface images, degree-exact non-star vertices, star
vertices carrying residual legs), over the stabilizer phases, and is certified by a pack
verifier whose golden suite is stamped in `claims/verifiers.json`:

- `zx_termination`: every rule strictly decreases a lexicographic measure of local counts,
  checked symbolically over every residual-leg category.
- `zx_critical_pairs`: every critical overlap of every rule pair, with star vertices carrying
  up to k context legs of each type, is joinable within d forward steps per side. **A PASS is
  local confluence at residual arity ≤ k, no more**: the critical-pair lemma for star rules is
  not established in this formulation, so nothing here says "locally confluent" without the
  arity bound.
- `zx_rule_sound` (new): every rule is a semantic equation up to scalar on every grounding over
  the fragment's phases with up to k residual legs per star, checked exhaustively within the
  oracle's budget.
- `zx_completeness` (new): every diagram in a bounded class C(w, v, e) reduces to a normal
  form and semantically equal diagrams share one; a FAIL is a certified counterexample pair.

## The claims

| claim | level | evidence | wall |
|---|---|---|---|
| `P6.jpv_clifford_oriented_locally_confluent_d5_k1` — the 24 JPV Clifford rules oriented left-to-right are locally confluent within depth 5 at arity ≤ 1 | **REFUTED** | `zx_critical_pairs` FAIL: bialgebra against colour_change has a critical pair with no common diagram within depth 5 | 14 s |
| `P6.r0_with_hopf_h_locally_confluent_d4_k2` — the 13-rule core R0 (fusion, identity, loop rules, hopf_h) is locally confluent within depth 4 at arity ≤ 2 | **REFUTED** | `zx_critical_pairs` FAIL: hopf_h against identity_z_hh at the instance b=0 (also not joinable at depth 6, `claims/evidence/p6/r0_cp_depth6_arity2.json`) | 7.7 s |
| `P6.r0_core_terminates_and_locally_confluent_d4_k2` — the 12-rule core R0core (R0 without hopf_h) is terminating under (vertices, edges) and locally confluent within depth 4 at arity ≤ 2 | **VERIFIED_N** n = 2388, exhaustive | `zx_termination` PASS (12 rules); `zx_critical_pairs` PASS: 2388 critical pairs over 78 rule pairs, 0 case splits | 3.7 s |
| `P6.clifford_rules_sound_k2` — each of the 24 Clifford rules is a semantic equation on every stabilizer instance with up to 2 residual legs per star | **VERIFIED_N** n = 2451, exhaustive | `zx_rule_sound` PASS: 2451 instances judged, 0 skipped | 0.5 s |
| `P6.r0_core_complete_c224` — R0core is complete for C(2, 2, 4) | **REFUTED** | `zx_completeness` FAIL: the empty diagram and the zero-leg spider Z(0) are semantically equal and both are normal forms (89,367 diagrams, 199 classes) | 10.6 s |
| `P6.r1_complete_c212` — the 20-rule R1 (identity and loop rules, colour change, six scalar eliminations, two Hadamard-on-a-state rules, zero absorption) is sound at arity ≤ 1 and complete for C(2, 1, 2) | **VERIFIED_N** n = 391, exhaustive | `zx_completeness` PASS: 391 diagrams, 59 classes, one normal form each, ≤ 4 steps; `zx_rule_sound` PASS: 75 instances | 0.1 s |

**Scalars count.** The completeness checker's first finding was not about rewriting at all: every
class C(w, v ≥ 1, e) contains the six non-zero zero-leg spiders (Z or X with phase 0, π/2 or
3π/2), which are one semantic class — non-zero scalars — with six normal forms under any system
that never touches a legless spider. So no orientation of the JPV equations alone can be complete
for any bounded class that admits a spider; scalar-elimination rules are part of the target system,
not bookkeeping. The plan's intended class C(2, 3, 6) also turned out to have about 40 million raw
candidates; C(2, 2, 4) (89,367 diagrams) is the largest class the checker surveys in seconds.

Two of the first three rows are refutations, and that is the point: the ledger now records, with
certified witnesses, that the raw JPV equations do not orient into a confluent system and that
adding the graph-like Hopf rule to the normalisation core breaks its local confluence at the
depths tried. The positive row is small but exact: the 12-rule core that fuses spiders, removes
identities and removes self-loops is terminating and locally confluent at bounded arity, and
its 2388 critical pairs all join within four steps.

## What this sets up

M25b, the completion campaign: the model proposes orientations of the remaining JPV
equations and auxiliary rules on top of R0core; the pack certifies soundness, termination, local
confluence at arity ≤ 2 and bounded completeness; every PASS becomes a VERIFIED_N claim and
every FAIL a REFUTED row with its witness. The stopping condition is a system that passes all
four on C(2, 3, 6) and C(2, 4, 8). The honest ceiling stays: without the critical-pair lemma
for star rules, such a system is locally confluent at bounded arity, not proven confluent.

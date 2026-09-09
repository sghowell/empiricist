# P6 completion campaign, first run: three serious candidates, every one incomplete for a certified reason

**Date:** 2026-09-09 · **Problem:** P6 (ii)(a), a terminating confluent system for the stabilizer
fragment, formulation `p6-zx-v1` · **Milestone:** M25b
(`docs/superpowers/plans/2026-09-09-m25b-p6-completion-campaign.md`) · **Run:** `runs/p6-completion`
(local, gitignored; resumable from `campaign.jsonl`) · **Spend:** $16.24 over two runs (rounds 1–3, then 4–9 with the stall detector).

## The move

One proposal is one candidate system: rules by library name or inline JSON (a reversed library
rule allowed), a lexicographic termination measure, a joinability depth. The harness certifies in
cost order — `zx_rule_sound` (arity ≤ 2), `zx_termination`, `zx_critical_pairs` (arity ≤ 2, node
budget 20,000), `zx_completeness` on C(2, 2, 4), then C(3, 2, 4), then C(2, 2, 6) — and stops at
the first non-PASS, feeding that verifier's witness back to the next round. A candidate is
*serious* once it is sound and terminating; from then on every verdict becomes a claim file
(PASS → VERIFIED_N over the stated class, FAIL → REFUTED with the witness in the notes). Unsound
or un-orientable proposals are model errors: fed back, never claims. Context is fresh each round
(the playbook, the library JSON, the seed and every prior candidate's outcome and witness).

## What happened

| round | candidate | rules | sound | terminates | locally confluent d4 k2 | complete C(2,2,4) |
|---|---|---|---|---|---|---|
| 0 (seed) | `cand_b51dae7256` | R0core + 6 scalar eliminations (18) | 1260 instances | (vertices, edges) | 2388 pairs | **REFUTED**: Z(0) and X(0) with a Hadamard self-loop are both the zero scalar; their normal forms Z(π), X(π) differ |
| 1 | `cand_9f596fed9c` | + `scalar_x_pi`, `zero_fuse` (20) | 1262 | (vertices, edges, x_vertices) | 2390 pairs | **REFUTED**: the empty diagram vs two Z(0) spiders joined by a Hadamard edge (a non-zero scalar with no rule) |
| 1 | `cand_56b3796e8a` | + `scalar_x_pi` (19) | 1261 | (vertices, edges, x_vertices) | 2388 pairs | **REFUTED**: same witness |
| 2 | `cand_8a870c24f6` | + colour_change, hopf_h, two Hadamard-on-a-state rules, `scalar_x_pi`, `zero_fuse`, five `zz_h_*` two-spider scalar rules (29) | 1875 | (vertices, x_vertices, hadamard_edges, edges, …) | 4677 pairs over 435 rule pairs | **REFUTED**: a one-output pair — a Z(0) state with a Hadamard leg vs a Z(0) state attached through a Z(0) spider carrying a Hadamard self-loop (found after 7,137 of 89,367 diagrams) |
| 2 | — | — | schema-invalid output | | | |
| 3 | — | — | two calls hung for the full 1800 s timeout | | | |

Sixteen claim files were minted (four per serious candidate); the ledger is green at 108 claims.
The model's trajectory is the right one: round 1 fixed the zero-scalar class, round 2 fixed the
two-spider scalars and reached the first non-scalar obstruction, a state that a Hadamard
self-loop rule must normalise. Every REFUTED row carries the exact pair that the next round has to
rewrite. The best candidate so far, `cand_8a870c24f6`, is the largest system the pack has
certified locally confluent: 29 rules, 4,677 critical pairs at residual arity ≤ 2, all joinable
within four steps.

## Why the run paused

From round 2 on, proposer calls began hanging until the transport's 1800-second timeout (one of
two in round 2, both in round 3, both in round 4 when the run was stopped). The calls that did
return cost $1.6–3.1 each. The loop has no stall detector beyond the per-call timeout; a run
that keeps hitting the provider's usage limit spends an hour per round on nothing. The run is
resumable: `python -m empiricist.packs.zx campaign --repo . --run-dir runs/p6-completion …`
rebuilds the history from `campaign.jsonl` and continues at round 4.

## Run 2 (with the stall detector): rounds 4–9, $9.60, thirteen more claims

| round | candidate | rules | certified | outcome |
|---|---|---|---|---|
| 4 | `cand_dc1277268e` | 35 (adds six "plug" state rules) | sound 1911, terminating (phase-aware measure), locally confluent d4 over 5,679 pairs | **REFUTED** for C(2,2,4): the same one-output state pair as round 2 |
| 5 | `cand_dda1f96c55` | 41 (adds `zero_merge`, `zero_cup_h`, `zero_unh`, three `zp_*`) | sound 2530, terminating | **REFUTED**: `identity_z` vs `zero_merge` not joinable within depth 4 |
| 5 | `cand_b71466cd3e` | 41 (adds `zero_bb_h`, `zero_boundary_h`, `zero_unlink_h`, three `zero_phase_*`) | sound 2530, terminating | **REFUTED**: `hopf_h` vs `zero_bb_h` not joinable within depth 5 |
| 6 | — | — | two empty calls | — |
| 7 | `cand_4a10138ea8` | 39 (adds `zero_state_h`, three `zp_*`) | sound 1930, terminating, **locally confluent d5 over 6,521 pairs of 780 rule pairs** | **REFUTED** for C(2,2,4): a two-output pair, both the zero map — a plain wire beside a zero-scalar spider vs a Hadamard wire beside it (found after 28,824 diagrams) |
| 8, 9 | — | — | four empty calls | `transport_stall` |

`cand_4a10138ea8` is the largest system the pack has certified locally confluent, and its
witness is the campaign's second structural finding. **The zero class is not local.** Under
"up to non-zero scalar" semantics every diagram containing a zero-scalar component (a Z(0)
with a Hadamard self-loop, a Z(π) with no legs, …) denotes the zero map, so all of them are
one semantic class — and a system of local rules cannot give that class one normal form, since
the rest of the diagram is untouched by any rule that fires on the scalar. Completeness on
C(w, v, e) as `p6-zx-v1` defines it therefore needs either a global absorption rule
("zero ⊗ D → zero", which is not a diagram rewrite in this model) or a formulation that treats
the zero class separately: check unique normal forms on the non-zero classes and detect zero
by a separate certified criterion. That is a formulation decision for the author, recorded here
and in the loop note; the campaign as run is measuring against a bar no local system can pass.

The stall detector did its job: rounds 8 and 9 returned nothing at zero cost and the run
stopped itself after twenty minutes instead of two hours.

## Two process notes

- Editing `termination.py` mid-milestone moved `zx_termination`'s identity; the loop correctly
  refused to promote the seed's `terminates` claim on an uncertified verifier until the stamp was
  renewed (the claim was promoted by hand afterwards; later candidates promoted normally). The
  drift check and the refusal both did their jobs.
- A stall detector for the transport (stop the round after two consecutive zero-output calls
  rather than waiting out 1800 s each) is the loop's first follow-up.

## Where this leaves P6

The stabilizer target is now a concrete search with certified feedback: the obstruction class is
known to the model at every round, and each serious candidate leaves four claims. What a
passing system would establish is bounded exactly as before — sound, terminating, locally
confluent at residual arity ≤ 2 within the stated depth, complete for the stated finite classes —
and the critical-pair lemma for star rules remains the gap between that and a confluence proof.

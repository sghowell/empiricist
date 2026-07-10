# P5: the universal minimum-fusion lower bound, formalized in Lean

**Date:** 2026-07-10 · **Problem:** P5, part (ii)/lower-bound · **Toolchain:** Lean
4.31.0 + mathlib v4.31.0 · **Gate:** the Empiricist FORMALIZED verifier (6-adversarial-
pass-hardened: sandboxed elaboration + `leanchecker` kernel re-check + frozen
snapshot + axiom whitelist).

This is the harness's first **FORMALIZED** scientific content (the prior FORMALIZED
artifact was a graph-theory scaffold lemma). It lights up the top of the epistemic
ladder for real: the folklore `F(G) ≥ N−3` lower bound is now a Lean-checked
theorem, certified through the hardened gate and ingested as a FORMALIZED artifact.

## What is proven (`lean/EmpiricistLean/EmpiricistLean/FusionCost.lean`)

The problem doc's folklore bound, verbatim: *"If g GHZ₃ states are consumed and f
fusions performed, photon counting gives N = 3g − 2f, and connectivity of the output
forces f ≥ g − 1; eliminating g yields F(G) ≥ N − 3."* Five theorems, all
gate-certified PASS with axioms ⊆ {propext, Classical.choice, Quot.sound}:

- **Arithmetic core** — `fusion_cost_lower_bound`: `N + 2f = 3g → g ≤ f+1 → N ≤ f+3`
  (`N ≤ f+3` is exactly `f ≥ N−3` in ℕ; additive forms avoid truncated subtraction;
  `omega`-clean).
- **Connectivity, derived two ways (NOT assumed):**
  - `components_merge_bound`: a component-count trajectory `c` with `c 0 = g`,
    `c f = 1`, and the local rule `c i ≤ c(i+1)+1` (each fusion drops the component
    count by ≤ 1) ⟹ `g ≤ f+1`. The conservative, honest model — only the local
    per-fusion fact.
  - `merge_graph_connectivity_bound`: the merges form a `SimpleGraph` on the `g`
    initial components; `Connected → edgeFinset.card ≤ f → g ≤ f+1`, reusing the
    pinned scaffold lemma `connected_edge_bound` (connected ⟹ ≥ g−1 edges = the
    spanning-tree argument).
- **Combined** — `fusion_cost_lower_bound_derived` / `..._of_merge_graph`: photon
  counting + a merge process ⟹ `N ≤ f+3`, with the connectivity bound *discharged*,
  not hypothesized. This is the full lower-bound argument.

## Faithfulness — exactly what this does and does not claim

**Honest scope (reviewed at the statement level, not just "it compiles"):** this
formalizes the folklore *argument* rigorously, at the argument's own abstraction
level. Its two modeled physical facts are the two the folklore proof itself invokes:
1. **Photon counting** `N = 3g − 2f` — exact qubit bookkeeping (each GHZ₃ = 3
   qubits; each fusion is a destructive 2-qubit measurement).
2. **The fusion merge effect** — each fusion drops the number of connected
   components by at most 1 (equivalently, the merges form a graph on the components).

Nothing smuggles the conclusion into a definition; the non-trivial content (g→1
needs ≥ g−1 merges) is genuinely proved. What this is **not**: a first-principles
derivation from a full Lean formalization of graph states, stabilizers, the
Bell-measurement graph rule, LC-equivalence, and `F` as a minimum over that model —
that is a much larger project. So the precise claim is: **"the counting +
connectivity lower-bound argument is Lean-verified"**, which is what the problem
doc's Formalization note calls formalizable ("arithmetic plus connectivity
induction"). This half is universal (holds for every connected G) and is the tight
half for the N−3 families.

## What remains (the harder half)

The exact family values `F(path/star/complete) = N−3` need the **upper bound**
`F ≤ N−3`: an explicit all-merge schedule (f = g−1 = N−3) that provably *produces*
the family graph. Faithfully, that requires formalizing the fusion→graph
transformation rule (the {X_aZ_b, Z_aX_b} Bell measurement → complete-bipartite
neighbourhood merge, ratified in spec D6 and used by the two verification engines)
and an induction on N that the schedule yields the target — a genuine
formalization sub-project, staged separately. The live campaign already exhibits
machine-*verified* witnesses for specific N (the engines certify them); lifting
those to an all-N Lean theorem is the open work.

## Provenance
Certified through `LeanVerifier` v3.2 (the hardened gate); FORMALIZED artifact
ingested (`kind='lean'`, `problem='P5'`, evidence `verifier=lean/3.2`, verdict PASS,
resolved statement recorded). The full slow_lean security suite (poison-import,
TOCTOU, kernel-injection, command-override, residue) was re-run after the verifier's
residue allow-list was widened for the new committed file — all still fail closed.

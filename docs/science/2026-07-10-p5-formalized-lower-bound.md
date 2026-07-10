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

## The path family, exact — `F(path_N) = N − 3` (upper bound DONE)

The upper-bound half is now formalized for the **path family**
(`lean/EmpiricistLean/EmpiricistLean/FamilyUpper.lean`), giving the first
gate-certified **exact** minimum-fusion value. The FORMALIZED-ingested claim
(`pathGraph_min_fusions`, statement recorded faithfully in the ledger):

> for `N ≥ 3`: `pathGraph N` is producible by exactly `N − 3` GHZ₃ leaf-merge
> fusions, **and** every schedule (photon counting + component-merge dynamics)
> producing an `N`-vertex connected output uses `≥ N − 3` fusions.

Together ⟹ `F(path_N) = N − 3`. What made this tractable and faithful:
- The D6 disjoint leaf-merge is **modeled as a `SimpleGraph` rewrite**
  (`ghz3LeafMerge`) and proven isomorphic to "attach one pendant"
  (`ghz3LeafMerge_iso_addPendant` — a *theorem*). This modeled rule is
  **cross-checked against the two verified engines**: a McKay-certificate check
  found 0/200 mismatches vs `merge_fresh_ghz3(role="leaf")`, and leaf-merging onto
  a path endpoint yields the longer path on *both* `fusion_gf2` and `fusion_stim`
  (N=3..7). The construction produces the path **exactly** (not just up-to-LC), so
  no LC-equivalence machinery was needed.
- The upper bound (`producibleBy_pathGraph`) is a genuine induction exhibiting the
  N−3-fusion construction; the lower bound is the universal `FusionCost` argument
  re-derived inline. The exact-value statement carries the *general* lower bound in
  its own type (not hidden behind a construction-class `Achievable` set — an earlier
  `IsLeast` framing was tightened after review because it read as general optimality
  while quantifying only over the construction class).

**Modeled-vs-proved boundary (unchanged):** the D6 graph rewrite is the modeled
primitive (justified by the engine cross-check), and the component-merge dynamics is
the same faithful folklore abstraction as the lower bound; this is not a
first-principles derivation from qubit-level stabilizer semantics.

## What remains

- **star, complete** exact values: reuse the same rule-formalization scaffold with
  their own (non-path) constructions — the natural next families.
- The genuinely-open P5 parts — 2D cluster / lattice family structure, the
  NP-completeness of FUSION-COST (part i), and the extremal growth of μ(N) (part
  iii) — remain research-frontier, not mechanical follow-ons.

## Provenance
Certified through `LeanVerifier` v3.2 (the hardened gate); FORMALIZED artifact
ingested (`kind='lean'`, `problem='P5'`, evidence `verifier=lean/3.2`, verdict PASS,
resolved statement recorded). The full slow_lean security suite (poison-import,
TOCTOU, kernel-injection, command-override, residue) was re-run after the verifier's
residue allow-list was widened for the new committed file — all still fail closed.

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

## A whole graph class, exact — `F(T) = N − 3` for EVERY tree

The strongest formalized result: not a single family but an infinite class.
`tree_min_fusions` (gate-certified PASS, FORMALIZED-ingested) proves that **every
tree** — mathlib's genuine `SimpleGraph.IsTree` (`Connected ∧ IsAcyclic`), over any
finite vertex type — has minimum fusion cost exactly `N − 3`:

> for a tree `T` with `N = card V ≥ 3`: `ProducibleBy (N−3) T` (an explicit N−3
> leaf-merge construction produces `T` exactly), **and** every schedule (photon
> counting + component-merge dynamics) uses `≥ N−3` fusions.

The upper bound is a genuine leaf-removal induction (every finite tree has a leaf;
delete it → a smaller tree by `Connected.induce_compl_singleton_of_degree_eq_one` +
`IsAcyclic.induce`; the IH's construction plus one `ghz3LeafMerge` at the leaf's
neighbour rebuilds `T`), reusing mathlib's tree API throughout. **Path and star are
now corollaries** (both are trees). Data-confirmed exhaustively: every
non-isomorphic tree orbit at N = 3..8 is `F = N−3`. This subsumes the two
tree-shaped named families below into one class theorem; the complete graph `K_N`
(not a tree) remains its own result via local complementation.

## Named exact family values — `F(path_N) = F(star_N) = F(K_N) = N − 3`

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

### The star family, exact — `F(star_N) = N − 3`

`star_min_fusions` (same faithful shape as `pathGraph_min_fusions`, gate-certified
PASS, FORMALIZED-ingested) reuses the entire path scaffold: `starGraph N` is genuine
K_{1,N-1} (center 0 adjacent to all, no leaf–leaf edges), and the **same
`ghz3LeafMerge` rule** attaching pendants at the fixed *center* (rather than a path
endpoint) grows `star_{N-1}` → `star_N` **exactly** (a pure relabelling iso — no LC).
Engine cross-check: `merge_fresh_ghz3(star_N, center, "leaf")` yields exactly
K_{1,N} (degree sequence: one degree-N center + N degree-1 leaves) on *both* engines,
N=3..7. So two of the three `N−3` families are now machine-proven exact.

### The complete family, exact — `F(K_N) = N − 3` (via formalized local complementation)

The third family needed **local complementation formalized** (mathlib has none), because
`K_N` is not producible by leaf-merges exactly — it is the star's LC-orbit. Delivered
(`complete_min_fusions`, gate-certified PASS, FORMALIZED-ingested):
- `localComplement G v` = `Xor (G.Adj x y) (x ≠ y ∧ G.Adj x v ∧ G.Adj y v)` — the τ_v
  rule **matching the verified domain `localcomp.py` exactly** (toggle within N(v),
  v's edges untouched), proven an **involution** as the domain asserts.
- `localComplement (starGraph N) center = completeGraph (Fin N)` — proven as an
  **equality** (`τ_center(star) = K_N`), matching the domain cross-check (N=3..7).
- `LCEquiv` = the genuine equivalence closure of "one local complementation or one
  relabelling" (the domain's LC-orbit notion); `star_N ≃_LC K_N` in one step.
- `ProducibleUpToLC f H` = `∃ G, ProducibleBy f G ∧ LCEquiv G H` — the **faithful
  physical `F`** (up to LC, since single-qubit Cliffords are free). This also makes
  path/star more faithful: exact production ⟹ up-to-LC (`ProducibleBy.toUpToLC`).

So `K_N` is producible in `N − 3` fusions up to LC (via `star_N`), and the universal
lower bound gives `≥ N − 3` (LC preserves vertex count + connectivity) ⟹
`F(K_N) = N − 3`. **All three `N−3` families are now machine-proven exact**, with the
fusion rule *and* local complementation formalized and cross-checked against the
verified engines/domain.

## What remains (the honest research frontier)

The genuinely-open P5 parts, none a mechanical follow-on:
- **(ii) hard families:** general trees, complete bipartite `K_{m,n}`, and the
  physically-central `L×L` 2D cluster + `FN₆`/Raussendorf lattice families ("even the
  2D cluster family is open") — large graphs past enumeration, needing general
  structural arguments.
- **(i) complexity:** is `FUSION-COST` NP-complete? A reduction proof — a different
  mode from construction search, plausibly out of this harness's scope.
- **(iii) extremal:** the growth of `μ(N) = max_G F(G)`.

## Provenance
Certified through `LeanVerifier` v3.2 (the hardened gate); FORMALIZED artifact
ingested (`kind='lean'`, `problem='P5'`, evidence `verifier=lean/3.2`, verdict PASS,
resolved statement recorded). The full slow_lean security suite (poison-import,
TOCTOU, kernel-injection, command-override, residue) was re-run after the verifier's
residue allow-list was widened for the new committed file — all still fail closed.

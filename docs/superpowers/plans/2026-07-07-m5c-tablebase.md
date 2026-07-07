# Empiricist M5c: The min-fusion tablebase — exact F(G) past the published frontier

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The exact minimum-fusion table `F(G)` for connected graph-state orbits in the GHZ₃ model — the harness's first `VERIFIED_N` dataset, novel science (no published GHZ₃ table exists). Tiered, honest claims: Tier-0 decides `F = N−3` vs `F ≥ N` **for every connected orbit up to n = 9** (past the 8-qubit frontier); Tier-1 resolves `F = N` vs `F ≥ N+3` for n ≤ 7. Every value is backed by (a) an achievability **witness Construction certified by the A∧B verifiers**, (b) **exhaustive BFS minimality re-derived by a second independent implementation**, and (c) the structural theorems below.

---

## The four structural lemmas (the science core — reviewers MUST check these)

**L1 (Commutation / single-blob WLOG).** Every fusion destructively measures a commuting Pauli pair on two qubits, each qubit measured at most once in a schedule; hence all fusion measurements in a schedule have disjoint supports and **commute** — the final state is independent of fusion order. Consequently any schedule can be reordered as: pick one resource as the seed **blob**; traverse the merge-tree blob-first (each merge fuses the current blob with one fresh GHZ₃); insert intra-component fusions anywhere (order-free). **Therefore a BFS over single-component states with two move types — (M1) fuse a blob qubit with a fresh GHZ₃ qubit, (M2) fuse two blob qubits intra-component — explores a superset-equivalent of all schedules.** No multiset-of-components state is needed. *(Empirical check in Task 1: both engines, two disjoint fusions applied in both orders → identical LC-orbit key, randomized.)*

**L2 (The mod-3 ladder).** For a schedule with `g` GHZ₃ resources, `f_m` merge fusions and `f_i` intra fusions producing one connected component of size `N`: merges reduce component count by exactly 1, so `f_m = g − 1`; qubit counting gives `N = 3g − 2(f_m + f_i)`. Eliminating `g`: **`f = f_m + f_i = N − 3 + 3·f_i`.** So every achievable fusion count satisfies `F ≡ N (mod 3)`... precisely: `F(G) ∈ {N−3, N, N+3, …}`. Corollaries: the folklore floor `F ≥ N−3`; `F = N−3` ⟺ an all-merge (`f_i = 0`) schedule exists; **the dataset invariant `F(G) ≡ N−3 (mod 3)` must hold for every entry** (a free mutation-resistant check).

**L3 (All-merge schedules are cap-free and depth-fixed).** In blob order, an all-merge schedule's component size grows monotonically 3 → 4 → … → N (each merge: k + 3 − 2 = k+1). So **every all-merge schedule has exactly N−3 fusions and never exceeds component size N.** Tier-0 is therefore pure *reachability*: which size-N orbits does the (M1)-only BFS reach? Reached ⟺ `F = N−3` (exact, unconditional); unreached ⟺ `F ≥ N` (by L2).

**L4 (Bounded transient for f_i ≤ c).** Order merges first, intra fusions last: the blob peaks at `N + 2·f_i`. So the Tier-c search (allowing `f_i ≤ c` intra fusions) is exhaustive over graphs of size ≤ `N + 2c` — **the transient cap is not an assumption but a theorem**: Tier-1 exactness for size-N targets needs only graphs ≤ N+2.

**Search-space consequence (why this is tractable).** States are single connected graphs **up to isomorphism** (iso-certificate dedup), with **0-cost local-complementation edges** walked inside a 0-1 BFS (deque) — so LC orbits are traversed lazily and `lc_orbit_key` is NEVER called in the hot loop (this resolves the PR-#4 memoization contract: orbits fall out as the 0-edge connected components of the search graph). Connected graphs up to iso: n=9 → 261,080; n=10 → 11.7M. Tier-0 to n=9 visits ≤ ~275k states — cheap. Tier-1 for n ≤ 7 visits graphs ≤ 9 — cheap. (Tier-1 at n=8/9 and Tier-2 are feature-flagged stretch, off by default.)

**Trust architecture (who certifies what).** The DP itself is a fast *proposer* using the closed-form disjoint-merge graph rewrite (the complete-bipartite rule proven in M5b's goldens) + engine-B-style intra fusion. Its trust comes from: (1) each reported value's **witness Construction is certified by `verify_agreed`** (both independent engines); (2) the whole reachable set is **re-derived by a second, independently-coded BFS** (different traversal, different rewrite implementation) with exact agreement on the per-n orbit partition; (3) the closed-form rewrite is **fuzz-validated against BOTH engines** on randomized cases (Task 1); (4) the L2 mod-3 and Adcock-count invariants hold over the whole table (the per-n reachable+unreachable orbit counts must sum to Adcock's 1,1,1,2,4,11,26,101,440).

**Branch:** `feat/m5c-tablebase` off `feat/m5b-fusion-verifiers` (stacked).

---

### Task 1: The move kernel — closed-form rewrites, validated against both engines

**Files:**
- Create: `src/empiricist/domain/p5/moves.py`
- Test: `tests/test_p5_moves.py`

**Design (`moves.py`):** pure graph-level move functions on `GraphState` (fast, no tableau in the hot loop):
- `merge_fresh_ghz3(gs, a, role) -> GraphState`: fuse blob qubit `a` with a fresh GHZ₃ at qubit `role` ("center" | "leaf"). Closed form (disjoint fusion, M5b-proven): new vertices = blob \ {a} + the 2 surviving GHZ₃ qubits; edges = blob edges minus those at `a`, plus GHZ₃'s surviving internal edge(s), plus complete bipartite `N(a) × N(b)` where `N(b)` is the fresh star's neighbors of the fused qubit (center→both leaves; leaf→the center). Deterministic relabeling to 0..n.
- `intra_fuse(gs, a, b) -> GraphState`: fuse two qubits of the SAME component. No trusted closed form — delegate to the **GF2Engine** (fast pure-Python bitmask; certified in M5b) and extract; this is not the hot path (Tier-1 only).
- `local_complements(gs) -> iterator[GraphState]`: the 0-cost edges (τ_v for each v).

- [ ] **Step 1: failing tests** — `tests/test_p5_moves.py`:
  - `test_merge_rule_matches_both_engines_fuzz`: for 25 random seeds — random connected blob (n=4..7), random blob qubit `a`, both roles: `merge_fresh_ghz3` result's `lc_orbit_key` MUST equal what StimEngine AND GF2Engine produce for the same fusion on the blob ⊗ fresh-star state. **The closed form is only trusted because of this fuzz.**
  - `test_commutation_L1`: for 15 random seeds — a 2-blob workspace with two disjoint fusion pairs applied in both orders on both engines → identical orbit key (the L1 empirical check).
  - `test_intra_fuse_agrees_with_stim`: 10 seeds — `intra_fuse` (GF2-backed) vs StimEngine on the same intra pair → same orbit key.
  - `test_merge_golden_p4`: star₃ blob, fuse a leaf with a fresh star's leaf → P₄ (the M5b golden through the closed form).
  - `test_mod3_invariant_smoke`: chains of k merges from GHZ₃ always land at size 3+k with k fusions (= N−3 ✓ L2/L3 shape).

- [ ] **Step 2: fail-first.** — [ ] **Step 3: implement.** — [ ] **Step 4: pass.** If the closed-form fuzz disagrees with the engines, THE CLOSED FORM IS WRONG — fix it (the engines are the certified authority). Never weaken the fuzz.

- [ ] **Step 5: full suite + ruff; commit** — `feat: P5 move kernel (engine-validated closed-form merge, GF2 intra fuse)`

---

### Task 2: Tier-0 tablebase — the all-merge reachability BFS to n = 9

**Files:**
- Create: `src/empiricist/domain/p5/tablebase.py`
- Test: `tests/test_p5_tablebase.py`

**Design (`tablebase.py`):**
- `tier0_search(n_max, *, on_progress=None) -> Tier0Result`: 0-1 BFS from GHZ₃ (K₃ representative). Deque; 0-cost moves = `local_complements` (same size), 1-cost moves = `merge_fresh_ghz3` (size +1; only while size < n_max). Dedup by `iso_certificate` (bytes, per-graph — NOT orbit key). Track for each visited graph: its size and (for witnesses) the parent + move that first reached it. Since all-merge depth is forced (= size − 3, L3), BFS-by-size IS BFS-by-depth; assert `depth == size − 3` throughout.
- Orbit assignment WITHOUT `lc_orbit_key`: orbits = connected components under the 0-edges among visited graphs of the same size. Implement as union-find over iso-certificates, unioning `g ~ τ_v(g)`.
- `Tier0Result`: for each n ≤ n_max: `reachable_orbits` (list of orbit reps + witness constructions) and — via exhaustive comparison — `unreachable_orbits`. Computing the complement needs ALL connected orbits at size n: enumerate all connected graphs up to iso at size n (use `networkx.graph_atlas` for n ≤ 7 or a nauty-free iso-deduped enumeration; for n = 8, 9 use the union-find orbit partition of the FULL graph set only if cheap — otherwise compare orbit COUNTS: reachable-orbit count vs Adcock's known totals (101 at 8, 440 at 9), and materialize unreachable orbits only for n ≤ 7). Record the method per n.
- `witness(graph) -> Construction`: walk parents to build the fusion-step list in workspace coordinates (resources = depth+1, steps = the merge fusions; qubit bookkeeping mapped to `build_workspace` layout).
- Invariants asserted in-code: every reachable size-n graph has depth n−3 (L3); orbit counts per n ≤ Adcock totals.

- [ ] **Step 1: failing tests** — `tests/test_p5_tablebase.py`:
  - `test_tier0_small_n_exact`: n ≤ 6 — every connected orbit is classified; for each n the reachable+unreachable orbit counts sum to Adcock (1,1,1,2,4,11); K₃'s orbit is reachable at depth 0; P₄/C₄'s orbit reachable at depth 1.
  - `test_tier0_witnesses_certify`: for n ≤ 6, every reachable orbit's witness Construction passes `verify_agreed` (a certified Registry over a tmp Ledger) — the A∧B certificate on every claimed value.
  - `test_tier0_depth_equals_size_minus_3` (L3 assertion surfaced as a test).
  - `test_tier0_n7`: reachable+unreachable counts sum to 26; report the split (this is NEW science — record the number in the test as a regression pin after first run, with a comment).
  - `test_mod3_ladder_holds`: every reported F value ≡ N−3 (mod 3) — trivially N−3 here; the test pins the invariant plumbing for Tier-1.
  - marked `slow`: `test_tier0_n8_n9`: counts sum to 101 and 440; record the reachable counts (SCIENCE OUTPUT — pin after first run).

- [ ] **Step 2: fail-first.** — [ ] **Step 3: implement.** — [ ] **Step 4: pass; run the slow n=8/9 and RECORD the reachable/unreachable split per n in the test pins + report.**

- [ ] **Step 5: full suite + ruff; commit** — `feat: Tier-0 tablebase (all-merge reachability to n=9, A∧B-certified witnesses)`

---

### Task 3: Second independent search + Tier-1 (n ≤ 7) + the VERIFIED_N dataset artifact

**Files:**
- Create: `src/empiricist/domain/p5/tablebase_check.py` (the independent re-derivation — write it BLIND per the F3 discipline: different author-run, different traversal (e.g. size-layered worklist instead of deque 0-1 BFS), different orbit-union mechanics; it may use the ENGINES for merges instead of the closed form)
- Modify: `src/empiricist/domain/p5/tablebase.py` (add `tier1_search(n_max)`)
- Create: `src/empiricist/domain/p5/dataset.py` (assemble the table → a canonical JSON artifact + ledger ingestion as VERIFIED_N with coverage + witness references)
- Test: `tests/test_p5_tablebase_check.py`, `tests/test_p5_dataset.py`

**Tier-1 (`tier1_search`)**: continue the BFS past size n with (M1) up to size ≤ n+2, allow exactly one (M2) intra fusion landing back at target sizes; a size-n orbit first reached this way (and not in Tier-0) has **F = N exactly** (L2+L4). n_max default 7 (transient ≤ 9).

**Dataset artifact (`dataset.py`)**: rows = (n, orbit_id, orbit_representative_edges, F_value_or_lower_bound, exact: bool, witness_construction | None, tier). Canonical JSON (sorted); blake3 = artifact id; `ingest_dataset(ledger, store, result) -> Artifact` at `Status.VERIFIED_N` with `status_n`, `coverage='exhaustive'`, and `details` in an evidence row from `verify_agreed` over every witness (recorded via `record_evidence`). The mod-3 + Adcock invariants re-checked at ingestion (raise on violation).

- [ ] Tests: independent-check agreement (`tablebase_check` reproduces Tier-0's per-n orbit partition EXACTLY for n ≤ 6, and its independence is guarded — no imports from `tablebase.py`'s internals beyond the public result type); Tier-1 on n ≤ 6 (known: all 11 n=6 orbits should be classified F=3 or F=6 — record the split); dataset round-trip + ledger ingestion (artifact at VERIFIED_N, evidence rows PASS, invariants enforced); a deliberately-corrupted table (one F bumped) must be REJECTED at ingestion (mod-3/witness check fires).

- [ ] full suite + ruff; commit — `feat: independent tablebase re-derivation, Tier-1, VERIFIED_N dataset ingestion`

---

### Task 4: Run the science + closeout

- [ ] Run Tier-0 to n=9 (+ n=10 best-effort behind a flag if runtime < ~30 min) and Tier-1 to n=7; capture the FULL results: per-n reachable/unreachable orbit counts, the Tier-1 F=N orbits, total runtime. **This output is the first novel science of the project — report it prominently.**
- [ ] Ingest into a real ledger + CAS in a scratch run dir; generate the canonical dataset artifact; confirm VERIFIED_N + evidence rows.
- [ ] Full suite + ruff; push; PR to `feat/m5b-fusion-verifiers`: title `M5c: exact F(G) tablebase to n=9 (VERIFIED_N)` — body MUST include the science results table (per-n: orbits, F=N−3 count, F≥N count; Tier-1 splits for n ≤ 7) + the four lemmas summary + the trust architecture.
- [ ] Final whole-branch review (physics + integration).

---

## Plan self-review (done at write time)

- **Spec §8.4 refinement**: the spec's multiset-BFS is superseded by the L1-justified single-blob search (provably equivalent — commutation); the transient cap becomes theorem L4 rather than an assumption; coverage claims are per-tier and honest. A spec amendment (like D6) should be committed once L1's empirical check passes in Task 1.
- **PR-#4 memoization contract resolved structurally**: no `lc_orbit_key` in the hot loop (0-1 BFS + union-find orbits).
- **The residual SPOF (shared canonicalizer)** is narrowed further: the tablebase's orbit partition never uses `canonical.py` at all in-loop; `lc_orbit_key` appears only in Task-1 fuzz comparisons and witness certification, where both engines' agreement covers it.
- **Trust chain explicit**: closed-form ← engine fuzz; values ← witness certificates (A∧B) + second implementation + L2/L3/L4 + Adcock/mod-3 invariants; corrupted-table rejection tested.
- **Feasibility**: Tier-0 n=9 ≈ ≤275k states (fine); Tier-1 n=7 transient ≤ 9 (fine); n=8/9 Tier-1 and Tier-2 are explicitly out/flagged.
- **Honest limits documented**: unreached-at-Tier-0 orbits get `F ≥ N` lower bounds (not exact values) unless Tier-1 resolves them; the dataset `exact` flag distinguishes.

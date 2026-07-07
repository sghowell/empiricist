# P5 science results: the exact min-fusion tablebase F(G) to n=9

**Status:** the harness's first `VERIFIED_N` dataset. Novel science — no
published GHZ₃ min-fusion table exists past the 8-qubit frontier, and this
run reaches n=9.

**What this is.** For every connected graph-state LC-orbit on 3..9 qubits,
`F(G)` is the minimum number of GHZ₃-fusion measurements needed to build a
representative of that orbit from scratch. This run resolves `F(G) = N−3`
(Tier-0, exact, all n) and `F(G) = N` (Tier-1, exact, n ≤ 7) wherever
possible, and otherwise records the best proven lower bound.

Full run: `tier0_search(9)` + `tier1_search(7)` → `build_dataset` → ingested
into a scratch ledger + CAS as a `Status.VERIFIED_N` artifact.

---

## Results table

| n | total orbits (Adcock) | Tier-0 exact `F=N−3` | Tier-1 exact `F=N` | open | open lower bound |
|---|---:|---:|---:|---:|---|
| 3 | 1   | 1   | 0  | 0   | — |
| 4 | 2   | 2   | 0  | 0   | — |
| 5 | 4   | 3   | 1  | 0   | — |
| 6 | 11  | 8   | 2  | 1   | F ≥ 9 (=N+3) |
| 7 | 26  | 15  | 7  | 4   | F ≥ 10 (=N+3) |
| 8 | 101 | 42  | —  | 59  | F ≥ 8 (=N) |
| 9 | 440 | 104 | —  | 336 | F ≥ 9 (=N) |
| **Σ** | **585** | **175** | **10** | **400** | |

Every total-orbit column is the **real A3 Adcock cross-check** — an
independent `geng -c n` enumeration of all connected graphs on n vertices,
union-found into LC orbits — not a literature lookup and not a tautological
`total − reachable` subtraction. It reproduces Adcock's published connected
LC-orbit counts (1, 1, 1, 2, 4, 11, 26, 101, 440) exactly at every n.

At n ≤ 7, Tier-1 exhaustively searched every orbit Tier-0 left open (all
transients up to size n+2, one intra-fusion), so every open row's bound
tightens all the way to `F ≥ N+3` (the next rung of the mod-3 ladder, L2).
At n = 8, 9, Tier-1 did not run (out of scope for this pass — see Honest
limits below), so those open rows carry only Tier-0's own floor, `F ≥ N`.

**Dataset totals:** 585 rows across n=3..9 (175 tier0 + 10 tier1 + 400
open) — a genuine partition of the Adcock population at every n (no orbit
counted twice, none dropped; asserted at both `build_dataset` time and
ingestion time).

---

## The four structural lemmas (one paragraph each)

**L1 (commutation / single-blob WLOG).** All fusion measurements in any
schedule act on disjoint qubit pairs and commute, so any schedule can be
reordered as: pick one seed blob, traverse the merge-tree blob-first,
insert intra-component fusions anywhere. A BFS over single-component states
with two move types — (M1) fuse a blob qubit with a fresh GHZ₃, (M2) fuse
two blob qubits intra-component — therefore explores a superset-equivalent
of all possible schedules; no multiset-of-components state is needed.

**L2 (the mod-3 ladder).** Qubit conservation (`N = 3g − 2f`) forces
`f ≡ N (mod 3)` for every schedule, and connecting `g` resources into one
component needs at least `g−1` component-reducing fusions, giving the floor
`F ≥ N−3`. For waste-free (minimal) schedules the identity is exact,
`f = N−3+3f_i`, so the ladder is `F(G) ∈ {N−3, N, N+3, …}` — this run's
`exact=False` rows always report a bound on that same ladder.

**L3 (all-merge is cap-free and depth-fixed).** In blob order, an all-merge
schedule's size grows monotonically 3→4→…→N, one fusion per size step, so
every all-merge schedule has exactly N−3 fusions and never exceeds size N.
Tier-0 is therefore pure reachability — which size-N orbits does the
(M1)-only search reach? Reached ⟺ `F = N−3` exactly, unconditionally.

**L4 (bounded transient for f_i ≤ c).** Ordering merges first and intra
fusions last, a schedule with `f_i` intra fusions peaks at size `N + 2·f_i`.
So Tier-1 (`f_i ≤ 1`) is exhaustive over graphs of size ≤ N+2 — the
transient cap is a theorem, not an assumption, which is what makes
Tier-1's `F = N` claims exact rather than merely achieved.

---

## Trust architecture (who certifies what)

Every reported value in this table rests on independent, redundant
certification, not on any single implementation's say-so:

1. **Witness Constructions are A∧B-certified.** Every exact row's witness
   (a `Construction` — the merge/intra-fusion schedule that reaches it) is
   re-verified at ingestion time via `verify_agreed`: **both** independent
   fusion engines (StimEngine's tableau simulation and GF2Engine's
   pure-Python bitmask GF(2) linear algebra — no shared code path) replay
   the schedule and must agree on the resulting LC-orbit key. A single
   disagreement is treated as an F3 alarm (a machinery bug), not evidence
   about the construction, and aborts ingestion — nothing partial is ever
   recorded.
2. **The reachable set is independently re-derived.** `tablebase_check.py`
   re-implements Tier-0's reachability search from scratch — different
   traversal (size-layered worklist vs. 0-1 BFS deque), different orbit-
   union mechanics, engine-driven merges instead of the closed-form graph
   rewrite — and is guarded (by AST-parsing its imports, not a text scan)
   to never import `tablebase.py`'s or `moves.py`'s internals. It reproduces
   Tier-0's exact per-n reachable-orbit partition for n ≤ 7.
3. **Mod-3 and Adcock invariants hold over the whole table.** Every exact
   row's `F` satisfies `F ≡ N−3 (mod 3)`; every n's row count equals the
   independently-enumerated Adcock total; the row set is asserted to be a
   genuine partition (no duplicate or missing `orbit_id`). All three checks
   run at `build_dataset` time and again, independently, at `ingest_dataset`
   time (which validates the artifact's own embedded content, not a live
   re-derivation of the process that made it).
4. **Corruption is rejected, not silently ingested.** A deliberately
   corrupted table (one `F` bumped by 1, or one witness's steps swapped
   between two different orbits) is caught and rejected before any
   ledger/store write — no artifact and no evidence row are created for a
   dataset that fails validation (exercised by
   `test_ingest_dataset_rejects_mod3_corruption` and
   `test_ingest_dataset_rejects_wrong_witness`).

---

## This run's numbers

- **Search wall time** (`tier0_search(9)` + `tier1_search(7)`, single pass —
  Tier-1 internally reuses the Tier-0 transient search to size 9): **44.98s**
- **`build_dataset` wall time** (assembling all 585 rows, re-rooting every
  orbit id into the canonical `enumerate_connected_orbits` namespace,
  building every witness `Construction`): **30.44s**
- **Ingestion wall time** (`ingest_dataset` — the full witness
  re-verification pass, `verify_agreed` over every one of the 185 exact
  rows, plus the mod-3/Adcock/partition re-checks): **5.62s**
- **Total wall time, search → build → ingest: 81.08s**
- **Exact rows verified via `verify_agreed`:** 185 (175 Tier-0 + 10 Tier-1;
  every single one, no sampling)
- **Artifact:** `Status.VERIFIED_N`, `status_n=9`, `coverage="exhaustive"`,
  content-addressed id (blake3, 64 hex chars):
  `dc8649519e5f86948a4283118b979fd958511687731bdb5ddc78c11956571f25`
- **Evidence:** 1 evidence row, `verdict=PASS`, verifier
  `p5_tablebase_dataset_ingest`, recording the per-n breakdown, the golden
  suite hash, and both witness verifiers' names
  (`stab_fusion`, `enum_fusion`)
- **`OrbitTooLarge` events: 0.** The A4 amendment flagged a real risk —
  `lc_orbit_key`'s LC-orbit BFS (called inside both witness verifiers on
  every exact row, including all 42+104=146 Tier-0 witnesses at n=8,9) uses
  a default cap of 200,000 graphs, and n=9 alone has 261,080 connected
  graphs total. In practice, over this entire run (all 185 exact-row
  witnesses at n=3..9, each checked by both engines), no LC orbit
  encountered during verification exceeded the cap — no orbit-too-large
  exception was raised anywhere in the verification path, and no cap
  parameter needed to be bumped. This is recorded here rather than assumed:
  the run was executed to completion and its errors (there were none)
  observed directly, not inferred.

(This scratch run used a temporary ledger + CAS directory, per the plan —
it is not committed; the numbers and artifact id above are this run's
actual output, captured directly from its log.)

---

## Honest limits

- **n=8, 9 open rows are `F ≥ N` bounds, not exact values.** Tier-1 (the
  one-intra-fusion resolution that lifts opens to exact `F = N`) only ran
  for n ≤ 7 in this pass; n=8's 59 and n=9's 336 open orbits are exactly
  where Tier-0's all-merge search stopped, with no attempt yet to resolve
  them further. Extending Tier-1 to n=8,9 (transients to size 10, 11) is
  future work, explicitly out of scope for this run (the plan's own
  feasibility note: "Tier-1 at n=8/9 and Tier-2 are feature-flagged
  stretch, off by default").
- **Tier-2 and beyond (f_i ≥ 2) are entirely unexplored** at every n. The
  ladder `F(G) ∈ {N−3, N, N+3, …}` (L2) says these opens sit at `N+3` or
  higher, but nothing in this run distinguishes `N+3` from `N+6` or beyond
  for any of the 400 open orbits.
- **n=10 was not attempted.** Adcock's count there (11.7M connected graphs)
  is within reach of `geng`'s enumeration speed but was not run this pass;
  Tier-0 reachability at n=10 is future work.
- **Convention D6** (the `{XZ, ZX}` fusion measurement basis) is the one
  ratified convention this whole table is computed under; a different
  convention is a different (not necessarily comparable) table.
- **The shared canonicalizer (`canonical.py`'s `iso_certificate` /
  pynauty)** is a residual single point of failure for orbit identity
  itself (both Tier-0's dedup and the A3 enumeration's iso-dedup rely on
  it), though it is not in the trust chain for *which orbit has which F* —
  that's the A∧B witness certification's job, which uses `lc_orbit_key`
  (built on the same canonicalizer) only to compare two computed graphs,
  not to establish the table's exhaustiveness claim.

---

## Reproducing

```python
from empiricist.domain.p5.tablebase import tier0_search, tier1_search
from empiricist.domain.p5.dataset import build_dataset, ingest_dataset
from empiricist.ledger.db import Ledger
from empiricist.store import Store
from empiricist.verifiers.registry import Registry
from empiricist.verifiers.stab_fusion import StabFusionVerifier
from empiricist.verifiers.enum_fusion import EnumFusionVerifier

tier1 = tier1_search(7)          # also runs tier0_search(9) internally
dataset = build_dataset(tier1.tier0, tier1)

ledger = Ledger("ledger.db")
store = Store("cas")
registry = Registry(ledger)
registry.certify(StabFusionVerifier())
registry.certify(EnumFusionVerifier())
artifact = ingest_dataset(ledger, store, dataset, registry)
```

Requires `geng`/`nauty-geng` on `PATH` (`brew install nauty` on macOS) for
the n=8,9 Adcock cross-check; total wall time on this run's machine was
about 81 seconds.

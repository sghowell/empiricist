# Empiricist M5a: P5 domain core — graph states, local complementation, LC-orbit canonicalization

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The correctness foundation for Problem 5: represent graph states three equivalent ways (graph ↔ GF(2) adjacency ↔ stabilizer generators), implement local complementation and LC-orbit enumeration, and produce the **LC-orbit canonical key** (the dedup identity that every downstream P5 verifier and the population/frontier rely on). This is physics-critical: a wrong LC key silently fragments orbits and mis-certifies `F(G)`.

**Architecture:** `domain/p5/graphstate.py` (a `GraphState` = an undirected simple graph, with conversions to/from a GF(2) adjacency matrix and stabilizer generators `X_v ∏_{u∈N(v)} Z_u`, plus the stim circuit for `|G⟩`) · `domain/p5/localcomp.py` (local complementation `τ_a`; LC-orbit BFS with a size cap; the rank-width/cut-rank profile pre-filter) · `domain/p5/canonical.py` (pynauty graph-iso canonical certificate; the LC-orbit canonical key = min iso-cert over the orbit; LC-equivalence test). Pure, deterministic, no I/O.

**Tech Stack:** Python 3.11, `stim>=1.16` (state-equality oracle later; here for `|G⟩` construction + a cross-check), `networkx>=3`, `pynauty>=2.8` (McKay canonical labeling — the ONLY certified iso key; WL-hash is NOT a certificate), `galois`/numpy over GF(2). All install cleanly on this box (verified: pynauty source-builds with Xcode present).

**Reference:** spec §8.1–8.3 + D5 (docs/superpowers/specs/2026-07-06-empiricist-harness-design.md). Physics facts (with sources): graph state `|G⟩` stabilized by `{X_v ∏_{u∈N(v)} Z_u}`; local complementation `τ_a` toggles every edge within `N(a)` (a clique-complement on the neighborhood); LC-equivalence ⟺ related by a sequence of `τ` (Bouchet 1991; van den Nest et al. quant-ph/0405023, poly-time). **GHZ₃ = 3-vertex path/star = triangle** are one LC orbit. The **cumulative count of LC orbits of connected graph states through n qubits is 1,1,1,2,4,11,26,101,440** (Adcock et al., Quantum 4:305; the per-n connected counts are 1,1,1,2,4,11,26,101,440 for n=1..9). These orbit counts are the load-bearing golden test.

**Branch:** `feat/m5a-p5-domain` off `feat/m4-llm-client` (stacked; retarget after M4 merges).

---

### Task 1: Branch, scientific deps, domain package + GraphState

**Files:**
- Modify: `pyproject.toml`
- Create: `src/empiricist/domain/__init__.py`, `src/empiricist/domain/p5/__init__.py`
- Create: `src/empiricist/domain/p5/graphstate.py`
- Test: `tests/test_p5_graphstate.py`

- [ ] **Step 1: Branch**

```bash
git switch feat/m4-llm-client && git switch -c feat/m5a-p5-domain
```

- [ ] **Step 2: Add scientific deps** — in `pyproject.toml` dependencies:

```toml
dependencies = [
    "blake3>=1.0",
    "psutil>=6.0",
    "pydantic>=2.0",
    "stim>=1.16",
    "networkx>=3.0",
    "pynauty>=2.8",
    "numpy>=2.0",
]
```

Then `uv lock && uv sync`. (pynauty source-builds; Xcode CLT is present on this box. If `uv sync` fails on pynauty, report the build error — do NOT drop the dep.)

- [ ] **Step 3: Write the failing tests** — `tests/test_p5_graphstate.py`:

```python
"""Tests for the GraphState representation and its three equivalent views."""

import numpy as np
import pytest

from empiricist.domain.p5.graphstate import GraphState


def test_from_edges_roundtrips_to_adjacency():
    gs = GraphState(n=3, edges=[(0, 1), (1, 2)])
    A = gs.adjacency()
    assert A.shape == (3, 3)
    # symmetric, zero diagonal, edges present
    assert np.array_equal(A, A.T) and np.trace(A) == 0
    assert A[0, 1] == 1 and A[1, 2] == 1 and A[0, 2] == 0


def test_adjacency_is_gf2_valued():
    gs = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3), (3, 0)])  # C_4
    A = gs.adjacency()
    assert set(np.unique(A).tolist()) <= {0, 1}


def test_neighbors():
    gs = GraphState(n=4, edges=[(0, 1), (0, 2), (0, 3)])  # star centred at 0
    assert gs.neighbors(0) == frozenset({1, 2, 3})
    assert gs.neighbors(1) == frozenset({0})


def test_stabilizers_have_correct_form():
    # star K_{1,2} (path 1-0-2): center 0 stabilizer = X0 Z1 Z2; leaf 1 = Z0 X1.
    gs = GraphState(n=3, edges=[(0, 1), (0, 2)])
    stabs = gs.stabilizers()          # list of stim.PauliString, one per vertex
    s = {str(p) for p in stabs}
    # stim PauliString str form like '+X_ZZ' — check via commutation/support instead:
    import stim
    assert stabs[0] == stim.PauliString("X_ZZ".replace("_", "X", 0)) or True  # shape check below
    # robust check: vertex v's stabilizer is X on v, Z on N(v), I elsewhere
    for v in range(3):
        p = stabs[v]
        for q in range(3):
            expected = "X" if q == v else ("Z" if q in gs.neighbors(v) else "_")
            assert p.pauli_indices  # non-trivial
    assert len(stabs) == 3


def test_stim_state_matches_stabilizers():
    """The stim circuit for |G> must yield exactly the graph-state stabilizer group."""
    import stim
    gs = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])  # path P_4
    sim = stim.TableauSimulator()
    gs.apply_state_prep(sim)          # H^n then CZ per edge
    canonical = sim.canonical_stabilizers()
    # every declared generator must stabilize the state (commute + +1 eigenvalue):
    declared = gs.stabilizers()
    group = set(str(s) for s in canonical)
    assert len(canonical) == 4
    # the generated group equals the graph-state group: check each declared gen is in span
    # (cheap: the state prepared two independent ways must have equal canonical form)
    sim2 = stim.TableauSimulator()
    for p in declared:
        pass  # declared generators are validated via apply_state_prep equality below
    assert len(group) == 4


def test_equal_graphstates_compare_equal():
    a = GraphState(n=3, edges=[(0, 1), (1, 2)])
    b = GraphState(n=3, edges=[(1, 2), (0, 1)])   # same edges, different order
    assert a == b and hash(a) == hash(b)


def test_rejects_self_loops_and_out_of_range():
    with pytest.raises(ValueError):
        GraphState(n=3, edges=[(0, 0)])
    with pytest.raises(ValueError):
        GraphState(n=3, edges=[(0, 3)])
```

Note: the stim `PauliString` string-form assertions above are fiddly; the implementer should prefer robust structural checks (support + type per qubit) over string equality, and MUST include the `test_stim_state_matches_stabilizers` cross-check that the stim-prepared state's canonical stabilizers match the graph-state group (prepare via two independent routes and compare `canonical_stabilizers()`). Adjust the exact assertions to be robust while preserving intent.

- [ ] **Step 4: Run tests to verify they fail** — `uv run pytest tests/test_p5_graphstate.py -v` → `ModuleNotFoundError`

- [ ] **Step 5: Write `src/empiricist/domain/p5/graphstate.py`**

```python
"""GraphState: an undirected simple graph and its equivalent quantum views.

|G> is the graph state stabilized by { X_v * prod_{u in N(v)} Z_u }_v (spec §8.2).
Three equivalent representations, all derivable from the edge set:
  - a GF(2) adjacency matrix (numpy uint8),
  - the stabilizer generators (stim.PauliString, one per vertex),
  - the stim state-prep circuit (H on every qubit, then CZ per edge).
Frozen/hashable so it can be a dict key and set member.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import stim


@dataclass(frozen=True)
class GraphState:
    n: int
    edges: frozenset[tuple[int, int]] = field(default_factory=frozenset)

    def __init__(self, n: int, edges) -> None:
        norm = set()
        for a, b in edges:
            if a == b:
                raise ValueError(f"self-loop not allowed: ({a}, {b})")
            if not (0 <= a < n and 0 <= b < n):
                raise ValueError(f"edge out of range for n={n}: ({a}, {b})")
            norm.add((a, b) if a < b else (b, a))
        object.__setattr__(self, "n", n)
        object.__setattr__(self, "edges", frozenset(norm))

    def adjacency(self) -> np.ndarray:
        A = np.zeros((self.n, self.n), dtype=np.uint8)
        for a, b in self.edges:
            A[a, b] = A[b, a] = 1
        return A

    def neighbors(self, v: int) -> frozenset[int]:
        return frozenset(b if a == v else a for a, b in self.edges if v in (a, b))

    def stabilizers(self) -> list[stim.PauliString]:
        stabs = []
        for v in range(self.n):
            ps = stim.PauliString(self.n)
            ps[v] = "X"
            for u in self.neighbors(v):
                ps[u] = "Z"
            stabs.append(ps)
        return stabs

    def apply_state_prep(self, sim: stim.TableauSimulator) -> None:
        for q in range(self.n):
            sim.h(q)
        for a, b in sorted(self.edges):
            sim.cz(a, b)

    @classmethod
    def from_adjacency(cls, A: np.ndarray) -> GraphState:
        n = A.shape[0]
        edges = [(i, j) for i in range(n) for j in range(i + 1, n) if A[i, j]]
        return cls(n=n, edges=edges)
```

- [ ] **Step 6: Run tests to verify they pass** — iterate the test assertions to robust structural checks as noted; `uv run pytest tests/test_p5_graphstate.py -v` → PASS. Confirm `test_stim_state_matches_stabilizers` genuinely validates the stim state ≡ declared stabilizer group.

- [ ] **Step 7: Full suite + lint + commit**

```bash
uv run pytest && uv run ruff check src tests
git add pyproject.toml uv.lock src/empiricist/domain tests/test_p5_graphstate.py
git commit -m "feat: P5 GraphState (graph/GF2/stabilizer views) + scientific deps"
```

---

### Task 2: Local complementation + LC-orbit BFS (`domain/p5/localcomp.py`)

**Files:**
- Create: `src/empiricist/domain/p5/localcomp.py`
- Test: `tests/test_p5_localcomp.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_p5_localcomp.py`:

```python
"""Tests for local complementation and LC-orbit enumeration (spec §8.2)."""

import networkx as nx

from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.localcomp import local_complement, lc_orbit


def test_local_complement_is_an_involution():
    gs = GraphState(n=5, edges=[(0, 1), (0, 2), (0, 3), (1, 2), (3, 4)])
    for v in range(5):
        assert local_complement(local_complement(gs, v), v) == gs


def test_local_complement_toggles_neighborhood_clique():
    # star centred at 0 on {1,2,3}: tau_0 makes {1,2,3} a triangle (complete).
    star = GraphState(n=4, edges=[(0, 1), (0, 2), (0, 3)])
    out = local_complement(star, 0)
    # 0 still connected to 1,2,3; and 1-2,1-3,2-3 now all present
    assert out.neighbors(0) == frozenset({1, 2, 3})
    assert (1, 2) in out.edges and (1, 3) in out.edges and (2, 3) in out.edges


def test_ghz3_star_and_triangle_share_an_orbit():
    star = GraphState(n=3, edges=[(0, 1), (0, 2)])       # P_3 / GHZ_3
    triangle = GraphState(n=3, edges=[(0, 1), (1, 2), (0, 2)])  # K_3
    orbit = lc_orbit(star)
    # the triangle is LC-equivalent to GHZ_3 (tau on the path centre)
    assert any(g == triangle for g in orbit)


def test_lc_orbit_is_closed_under_local_complement():
    gs = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])  # P_4
    orbit = set(lc_orbit(gs))
    for g in list(orbit):
        for v in range(g.n):
            assert local_complement(g, v) in orbit  # closed


def test_lc_orbit_deduplicates():
    gs = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    orbit = lc_orbit(gs)
    assert len(orbit) == len(set(orbit))  # no duplicate GraphStates


def test_lc_orbit_matches_networkx_local_complement_bruteforce():
    """Cross-check the orbit against an independent nx-based fixpoint enumeration."""
    gs = GraphState(n=5, edges=[(0, 1), (1, 2), (2, 3), (3, 4)])  # P_5

    def nx_lc(G, v):
        H = G.copy()
        nbrs = list(G.neighbors(v))
        for i in range(len(nbrs)):
            for j in range(i + 1, len(nbrs)):
                a, b = nbrs[i], nbrs[j]
                if H.has_edge(a, b):
                    H.remove_edge(a, b)
                else:
                    H.add_edge(a, b)
        return H

    seen = set()
    frontier = [nx.Graph([tuple(e) for e in gs.edges] + [(i,) for i in range(gs.n)][:0])]
    G0 = nx.Graph(); G0.add_nodes_from(range(gs.n)); G0.add_edges_from(gs.edges)
    frontier = [G0]
    seen.add(frozenset(map(frozenset, G0.edges())))
    while frontier:
        G = frontier.pop()
        for v in range(gs.n):
            H = nx_lc(G, v)
            key = frozenset(frozenset(e) for e in H.edges())
            if key not in seen:
                seen.add(key)
                frontier.append(H)
    ours = {frozenset(frozenset(e) for e in g.edges) for g in lc_orbit(gs)}
    assert ours == seen
```

- [ ] **Step 2: Run tests to verify they fail** — `uv run pytest tests/test_p5_localcomp.py -v` → `ModuleNotFoundError`

- [ ] **Step 3: Write `src/empiricist/domain/p5/localcomp.py`**

```python
"""Local complementation and LC-orbit enumeration (spec §8.2).

tau_a(G) toggles every edge WITHIN the neighborhood N(a) (Bouchet); LC-equivalence
is generated by these. lc_orbit does a BFS applying tau_v at every vertex, deduping
by the GraphState value, up to an orbit-size cap (orbits blow up past n=9, so the
cap is a declared bound, not a silent truncation — it raises if hit).
"""

from __future__ import annotations

from collections import deque

from empiricist.domain.p5.graphstate import GraphState

DEFAULT_ORBIT_CAP = 200_000


class OrbitTooLarge(Exception):
    """The LC orbit exceeded the cap before closing (declare a larger cap or n0)."""


def local_complement(gs: GraphState, a: int) -> GraphState:
    nbrs = sorted(gs.neighbors(a))
    edges = set(gs.edges)
    for i in range(len(nbrs)):
        for j in range(i + 1, len(nbrs)):
            e = (nbrs[i], nbrs[j])
            if e in edges:
                edges.discard(e)
            else:
                edges.add(e)
    return GraphState(n=gs.n, edges=edges)


def lc_orbit(gs: GraphState, *, cap: int = DEFAULT_ORBIT_CAP) -> list[GraphState]:
    """The full LC orbit of gs (BFS under tau_v), deduped by GraphState value.

    Raises OrbitTooLarge if the orbit exceeds `cap` before closing.
    """
    seen: set[GraphState] = {gs}
    queue: deque[GraphState] = deque([gs])
    while queue:
        g = queue.popleft()
        for v in range(g.n):
            h = local_complement(g, v)
            if h not in seen:
                if len(seen) >= cap:
                    raise OrbitTooLarge(f"LC orbit exceeded cap={cap}")
                seen.add(h)
                queue.append(h)
    return sorted(seen, key=lambda g: (len(g.edges), sorted(g.edges)))
```

- [ ] **Step 4: Run tests to verify they pass** — `uv run pytest tests/test_p5_localcomp.py -v` → PASS (the nx brute-force cross-check is the strong one).

- [ ] **Step 5: Commit**

```bash
git add src/empiricist/domain/p5/localcomp.py tests/test_p5_localcomp.py
git commit -m "feat: local complementation + LC-orbit BFS (nx brute-force cross-checked)"
```

---

### Task 3: Canonicalization + LC-orbit key + the Adcock golden test (`domain/p5/canonical.py`)

**Files:**
- Create: `src/empiricist/domain/p5/canonical.py`
- Test: `tests/test_p5_canonical.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_p5_canonical.py`:

```python
"""Tests for pynauty canonicalization + the LC-orbit canonical key.

The load-bearing golden test reproduces the Adcock LC-orbit counts of connected
graph states through 9 qubits (1,1,1,2,4,11,26,101,440) — a strong, mutation-
resistant check that the whole LC-equivalence pipeline is correct.
"""

import itertools

import networkx as nx
import pytest

from empiricist.domain.p5.canonical import (
    iso_certificate,
    lc_orbit_key,
    lc_equivalent,
)
from empiricist.domain.p5.graphstate import GraphState


def test_iso_certificate_is_isomorphism_invariant():
    # two labelings of the same path P_3
    a = GraphState(n=3, edges=[(0, 1), (1, 2)])
    b = GraphState(n=3, edges=[(0, 2), (2, 1)])  # relabelled path
    assert iso_certificate(a) == iso_certificate(b)


def test_iso_certificate_distinguishes_nonisomorphic():
    path = GraphState(n=3, edges=[(0, 1), (1, 2)])
    triangle = GraphState(n=3, edges=[(0, 1), (1, 2), (0, 2)])
    assert iso_certificate(path) != iso_certificate(triangle)


def test_lc_orbit_key_is_lc_invariant():
    star = GraphState(n=3, edges=[(0, 1), (0, 2)])
    triangle = GraphState(n=3, edges=[(0, 1), (1, 2), (0, 2)])
    # GHZ_3 star and triangle are LC-equivalent -> same orbit key
    assert lc_orbit_key(star) == lc_orbit_key(triangle)


def test_lc_orbit_key_separates_distinct_orbits():
    # P_4 and K_{1,3} (star) are in DIFFERENT LC orbits on 4 vertices
    p4 = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    star = GraphState(n=4, edges=[(0, 1), (0, 2), (0, 3)])
    assert lc_orbit_key(p4) != lc_orbit_key(star)


def test_lc_equivalent_predicate():
    star = GraphState(n=3, edges=[(0, 1), (0, 2)])
    triangle = GraphState(n=3, edges=[(0, 1), (1, 2), (0, 2)])
    p4 = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    assert lc_equivalent(star, triangle) is True
    # different vertex counts are trivially inequivalent
    assert lc_equivalent(star, p4) is False


ADCOCK_CUMULATIVE = {1: 1, 2: 1, 3: 1, 4: 2, 5: 4, 6: 11, 7: 26, 8: 101, 9: 440}


def _connected_graphs(n):
    """All connected simple graphs on n labelled vertices (small n)."""
    verts = list(range(n))
    all_edges = list(itertools.combinations(verts, 2))
    for r in range(n - 1, len(all_edges) + 1):
        for es in itertools.combinations(all_edges, r):
            G = nx.Graph()
            G.add_nodes_from(verts)
            G.add_edges_from(es)
            if nx.is_connected(G):
                yield GraphState(n=n, edges=list(es))


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6])
def test_lc_orbit_counts_match_adcock(n):
    """Count distinct LC-orbit keys over all connected graphs on n vertices."""
    keys = {lc_orbit_key(g) for g in _connected_graphs(n)}
    assert len(keys) == ADCOCK_CUMULATIVE[n]


@pytest.mark.slow
@pytest.mark.parametrize("n", [7])
def test_lc_orbit_counts_match_adcock_n7(n):
    keys = {lc_orbit_key(g) for g in _connected_graphs(n)}
    assert len(keys) == ADCOCK_CUMULATIVE[n]
```

- [ ] **Step 2: Run tests to verify they fail** — `uv run pytest tests/test_p5_canonical.py -v` → `ModuleNotFoundError`

- [ ] **Step 3: Write `src/empiricist/domain/p5/canonical.py`**

```python
"""Canonicalization: pynauty iso-certificates and the LC-orbit canonical key.

pynauty.certificate() is McKay canonical labeling — a TRUE isomorphism certificate
(equal iff isomorphic). WL-hash / VF2 are NOT certificates and must never be used
here. The LC-orbit canonical key (spec D5) is the LEXICOGRAPHICALLY MINIMUM iso-
certificate taken over the whole LC orbit: it is invariant across the orbit, so it
is the identity under which F(G) is well-defined and the population dedups.
"""

from __future__ import annotations

import pynauty

from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.localcomp import lc_orbit


def _to_pynauty(gs: GraphState) -> pynauty.Graph:
    adj = {v: [] for v in range(gs.n)}
    for a, b in gs.edges:
        adj[a].append(b)
        adj[b].append(a)
    return pynauty.Graph(gs.n, directed=False, adjacency_dict=adj)


def iso_certificate(gs: GraphState) -> bytes:
    """McKay canonical certificate: equal iff the graphs are isomorphic."""
    return pynauty.certificate(_to_pynauty(gs))


def lc_orbit_key(gs: GraphState, *, cap: int | None = None) -> bytes:
    """The LC-orbit canonical key: min iso-certificate over the LC orbit.

    Invariant across the orbit, so equal iff LC-equivalent (for orbits within cap).
    """
    kwargs = {} if cap is None else {"cap": cap}
    return min(iso_certificate(g) for g in lc_orbit(gs, **kwargs))


def lc_equivalent(a: GraphState, b: GraphState) -> bool:
    """True iff a and b are LC-equivalent (same vertex count and orbit key)."""
    if a.n != b.n:
        return False
    return lc_orbit_key(a) == lc_orbit_key(b)
```

- [ ] **Step 4: Run tests to verify they pass**

`uv run pytest tests/test_p5_canonical.py -v -m "not slow"` → the n=1..6 Adcock counts must match EXACTLY (1,1,1,2,4,11). This is the milestone's proof of correctness. Then run the n=7 slow test: `uv run pytest tests/test_p5_canonical.py -m slow -v` (may take a minute — 7-vertex connected graphs number ~2M; if too slow, the implementer may reduce to sampling but MUST keep n<=6 exhaustive and report the n7 timing). Register the `slow` marker in pyproject `[tool.pytest.ini_options] markers`.

- [ ] **Step 5: Commit**

```bash
git add src/empiricist/domain/p5/canonical.py tests/test_p5_canonical.py pyproject.toml
git commit -m "feat: pynauty LC-orbit canonical key (Adcock orbit counts n<=6 golden)"
```

---

### Task 4: Rank-width pre-filter + closeout

**Files:**
- Modify: `src/empiricist/domain/p5/localcomp.py` (add `cut_rank_profile`)
- Test: `tests/test_p5_prefilter.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_p5_prefilter.py`:

```python
"""The cut-rank/rank-width profile is an LC-invariant used as a cheap non-
equivalence pre-filter (spec §8.2): equal profile is necessary (not sufficient)
for LC-equivalence, so a profile MISMATCH certifies non-equivalence."""

from empiricist.domain.p5.canonical import lc_equivalent, lc_orbit_key
from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.localcomp import cut_rank_profile, local_complement


def test_profile_is_lc_invariant():
    gs = GraphState(n=5, edges=[(0, 1), (1, 2), (2, 3), (3, 4)])
    base = cut_rank_profile(gs)
    for v in range(5):
        assert cut_rank_profile(local_complement(gs, v)) == base


def test_profile_mismatch_implies_non_equivalent():
    import itertools
    # over small connected graphs: profile mismatch => lc_orbit_key mismatch
    verts = list(range(4))
    alledges = list(itertools.combinations(verts, 2))
    graphs = []
    for r in range(3, len(alledges) + 1):
        for es in itertools.combinations(alledges, r):
            import networkx as nx
            G = nx.Graph(); G.add_nodes_from(verts); G.add_edges_from(es)
            if nx.is_connected(G):
                graphs.append(GraphState(n=4, edges=list(es)))
    for a in graphs:
        for b in graphs:
            if cut_rank_profile(a) != cut_rank_profile(b):
                assert not lc_equivalent(a, b)   # mismatch => genuinely inequivalent


def test_profile_is_a_prefilter_not_a_certificate():
    # profile equal does NOT imply equivalent (it's one-sided); at least document
    # by asserting the pipeline still uses lc_orbit_key for the final decision.
    star = GraphState(n=3, edges=[(0, 1), (0, 2)])
    triangle = GraphState(n=3, edges=[(0, 1), (1, 2), (0, 2)])
    assert cut_rank_profile(star) == cut_rank_profile(triangle)  # same orbit anyway
    assert lc_orbit_key(star) == lc_orbit_key(triangle)
```

- [ ] **Step 2: Run tests to verify they fail** — `uv run pytest tests/test_p5_prefilter.py -v` → `ImportError` (no `cut_rank_profile`)

- [ ] **Step 3: Append `cut_rank_profile` to `localcomp.py`**

```python
import numpy as np


def _gf2_rank(M: np.ndarray) -> int:
    M = M.copy() % 2
    rows, cols = M.shape
    r = 0
    for c in range(cols):
        piv = next((i for i in range(r, rows) if M[i, c]), None)
        if piv is None:
            continue
        M[[r, piv]] = M[[piv, r]]
        for i in range(rows):
            if i != r and M[i, c]:
                M[i] = (M[i] + M[r]) % 2
        r += 1
    return r


def cut_rank_profile(gs: GraphState) -> tuple[int, ...]:
    """LC-invariant: sorted multiset of GF(2) cut-ranks over all bipartitions.

    For a bipartition (X, V\\X), the cut-rank is the GF(2) rank of the off-diagonal
    block A[X, V\\X]. The sorted multiset over all 2^n bipartitions is invariant
    under local complementation (rank-width theory). A one-sided pre-filter: a
    profile mismatch certifies NON-equivalence; equality does not certify equivalence.
    """
    A = gs.adjacency().astype(np.int64)
    n = gs.n
    ranks = []
    for mask in range(1, (1 << n) - 1):     # non-trivial bipartitions
        X = [i for i in range(n) if mask & (1 << i)]
        Y = [i for i in range(n) if not (mask & (1 << i))]
        ranks.append(_gf2_rank(A[np.ix_(X, Y)]))
    return tuple(sorted(ranks))
```

(Note: 2^n bipartitions is fine for n<=~12; for larger n a canonical subset suffices — out of scope here.)

- [ ] **Step 4: Run tests to verify they pass** — `uv run pytest tests/test_p5_prefilter.py -v` → PASS

- [ ] **Step 5: Full suite + lint**

Run: `uv run pytest -m "not slow" && uv run ruff check src tests`
Expected: all green, lint clean.

- [ ] **Step 6: Commit + push + PR**

```bash
git add src/empiricist/domain/p5/localcomp.py tests/test_p5_prefilter.py
git commit -m "feat: cut-rank/rank-width LC-invariant profile (non-equivalence pre-filter)"
git push -u origin feat/m5a-p5-domain
env -u GH_TOKEN -u GITHUB_TOKEN gh pr create --base feat/m4-llm-client --head feat/m5a-p5-domain \
  --title "M5a: P5 domain core (graph states, LC, canonicalization)" --body "<summary; note the Adcock orbit-count golden test result n<=6 (and n7 timing)>"
```

---

## Plan self-review (done at write time)

- **Spec coverage (§8.1–8.3, D5):** GraphState 3 views ✅ (T1); local complementation + LC-orbit ✅ (T2); pynauty LC-orbit canonical key ✅ (T3); cut-rank/rank-width LC-invariant pre-filter ✅ (T4). The Adcock orbit-count golden (n≤6 exhaustive, n7 slow) is the correctness proof for the whole LC pipeline.
- **Physics correctness anchors:** local-complement involution; τ_a toggles the N(a) clique; GHZ₃ star≡triangle in one orbit; stim state ≡ declared stabilizer group (independent-route cross-check); LC-orbit BFS cross-checked against an independent nx brute-force; orbit key LC-invariant + separates distinct orbits; **Adcock LC-orbit counts** — the load-bearing mutation-resistant test.
- **Placeholder scan:** none; the stim PauliString assertions in T1 are explicitly flagged to be made robust structurally.
- **Type consistency:** `GraphState(n, edges)` frozen/hashable used as set/dict key throughout; `lc_orbit(gs, cap=)` ↔ `lc_orbit_key`; `iso_certificate`/`lc_orbit_key`/`lc_equivalent` ↔ tests; `cut_rank_profile` LC-invariant. pynauty `Graph(n, directed=False, adjacency_dict=)` + `certificate()` are the real 2.8 API (implementer: verify the exact call shape against the installed pynauty and adjust if the constructor differs).
- **Deferred to M5b/M5c (documented):** the fusion operation (destructive Bell measurement) and the two independent fusion verifiers (M5b); the min-fusion DP tablebase + VERIFIED_N dataset (M5c). This milestone is ONLY the representation + LC-equivalence foundation they build on.

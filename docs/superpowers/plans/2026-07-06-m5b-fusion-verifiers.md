# Empiricist M5b: The two independent fusion verifiers + registry

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The fusion operation (destructive Bell measurement) realized on TWO independent stabilizer engines — A: stim tableau; B: pure-Python GF(2) bitmask tableau — whose **agreement on the post-fusion LC-orbit key is the certificate** (F3: two independent implementations, different data structures, no shared transition code). Plus the `Construction` artifact (spec Appendix E), the Verifier protocol, and the certification-stamped registry (spec §7).

**Physics (the ground truth both engines must implement):**
- A **fusion** on qubits (a, b) = destructive measurement of the commuting pair `{X_a X_b, Z_a Z_b}` (Bell basis). v0 postselects the (+1, +1) branch WLOG — all four outcomes differ by Pauli corrections, which are local Cliffords, and our identity is the LC orbit (spec D6). If the +1 branch of an observable is impossible (already-determined −1, can happen intra-component), postselect the −1 branch instead — same LC orbit.
- After both measurements, qubits a,b hold a Bell state **disentangled from the rest**; they are removed. n qubits → n−2.
- The post-fusion state is a stabilizer state = LC-equivalent to a graph state (Van den Nest). **Graph extraction** from a stabilizer tableau: take the k×2k binary generator matrix [X|Z] on the remaining qubits; while rank_GF2(X) < k, apply H on a qubit whose X/Z column swap increases the rank (H is a local Clifford — free); then `A_adj = X⁻¹Z (mod 2)`; zero the diagonal (diagonal 1s = S gates, also LC); the result is a symmetric adjacency → GraphState.
- **Signs may be ignored throughout**: sign changes are Pauli corrections = local Cliffords, invisible to the LC orbit. (This is a deliberate, documented simplification — both engines track only the [X|Z] part.)

**Golden facts (fail-loudly tests):**
- GHZ₃ ⊗ GHZ₃, fusing one leaf of each star: for the `{XX, ZZ}` fusion of qubits a,b in *disjoint* components, the graph rule is **connect every former neighbor of a to every former neighbor of b (complete bipartite), delete a,b**. Star₃(c₁;l₁,a) fused at (a,b) with Star₃(c₂;b,l₂) → edges {l₁c₁, c₁c₂, c₂l₂} = **P₄**. So 2 resources, 1 fusion → the 4-qubit path: consistent with F(P₄) = 4−3 = 1.
- Chaining g GHZ₃ stars leaf-to-leaf with g−1 fusions yields **P_{g+2}** — the F(path_N) = N−3 achievability witness for any N ≥ 3.
- Both engines must agree on the LC-orbit key for randomized fusions on random small graphs (the A≡B fuzz).

**Architecture:** `domain/p5/fusion_stim.py` (engine A: `StimEngine` — state_from_graph / fuse / to_graphstate, using stim + numpy) · `domain/p5/fusion_gf2.py` (engine B: `GF2Engine` — same public triple, implemented with pure-Python **int bitmasks** (x_bits, z_bits per generator), no stim, no numpy — genuinely different data structures) · `domain/p5/construction.py` (the Appendix-E artifact: `FusionOp`, `Construction`, `build_workspace` = resources GHZ₃ stars at qubits 3i..3i+2, `apply(construction, engine)` → final GraphState) · `verifiers/base.py` (Verifier protocol: `applicable`/`verify` → Verdict + details) · `verifiers/stab_fusion.py` + `verifiers/enum_fusion.py` (thin Verifier wrappers over the engines) · `verifiers/registry.py` (certification-stamp-gated dispatch per spec §7, wired to the M1-2 ledger `certifications` table) · `verifiers/goldens/p5.py` (the golden suite both fusion verifiers must pass to earn their stamp).

**The independence rule (F3), precisely:** A and B share NOTHING below their public interface — A uses stim tableaux + numpy GF(2) elimination; B uses pure-Python bitmask generators + its own elimination. They MAY both call M5a's `lc_orbit_key` (the shared, Adcock-proven canonicalizer — sanctioned by spec §8.3) and both consume `GraphState`. A reviewer must be able to diff the two engines and find no copied logic.

**Branch:** `feat/m5b-fusion-verifiers` off `feat/m5a-p5-domain` (stacked).

---

### Task 1: Engine A — fusion on the stim tableau (`domain/p5/fusion_stim.py`)

**Files:**
- Create: `src/empiricist/domain/p5/fusion_stim.py`
- Test: `tests/test_p5_fusion_stim.py`

**Interface (both engines implement this shape):**

```python
class StimEngine:
    """Engine A: fusion on a stim TableauSimulator. Tracks (sim, active qubit ids)."""

    def state_from_graph(self, gs: GraphState) -> "StimState": ...
    def fuse(self, state: "StimState", a: int, b: int) -> "StimState":
        """Destructive Bell measurement {X_aX_b, Z_aZ_b} on ACTIVE qubits a,b.
        Postselects +1 (falls back to -1 if forced); removes a,b from active."""
    def to_graphstate(self, state: "StimState") -> GraphState:
        """LC-equivalent graph extraction over the active qubits (relabelled 0..k-1)."""
```

`StimState` = frozen dataclass holding the `stim.TableauSimulator` + a tuple of active global qubit indices. `fuse` raises `ValueError` on inactive/equal qubits.

**Implementation notes (verify each against the real stim 1.16 API — do not guess):**
- state prep: `gs.apply_state_prep(sim)` (from M5a; fresh sim).
- measurement: build `stim.PauliString` of the right length with X at a,b (then Z at a,b); use `sim.postselect_observable(obs, desired_value=False)` for the +1 branch (stim's desired_value=False ↔ +1 eigenvalue — VERIFY this convention empirically on a known case before trusting it; if it's inverted, adapt). If postselecting +1 raises (impossible branch), postselect the −1 branch.
- extraction: `sim.canonical_stabilizers()` → keep generators, drop the two supported only on {a,b} — after the fusion the Bell pair on (a,b) is disentangled, so canonical form contains exactly 2 such generators; assert this. Build the k×2k [X|Z] numpy matrix over the active qubits, run the rank-completion + `A = X⁻¹Z` extraction (numpy GF(2) Gauss). Zero the diagonal. `GraphState.from_adjacency` (it validates symmetry — if extraction ever yields asymmetric A, that's a bug, let it raise).

- [ ] **Step 1: Write the failing tests** — `tests/test_p5_fusion_stim.py`:

```python
"""Engine A (stim) fusion goldens. A wrong fusion rule MUST fail these."""

import pytest

from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.fusion_stim import StimEngine
from empiricist.domain.p5.graphstate import GraphState


@pytest.fixture()
def eng():
    return StimEngine()


def star(center, leaves, n):
    return GraphState(n=n, edges=[(center, leaf) for leaf in leaves])


def test_roundtrip_no_fusion(eng):
    """state_from_graph then to_graphstate must return the same LC orbit."""
    for gs in [
        GraphState(n=3, edges=[(0, 1), (0, 2)]),
        GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)]),
        GraphState(n=5, edges=[(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)]),  # C_5
    ]:
        st = eng.state_from_graph(gs)
        out = eng.to_graphstate(st)
        assert lc_orbit_key(out) == lc_orbit_key(gs)


def test_ghz3_pair_fusion_gives_p4(eng):
    """THE core golden: star3 x star3 fused leaf-leaf -> P4 (F(P4)=1 witness)."""
    # qubits 0,1,2 = star(0;1,2); qubits 3,4,5 = star(3;4,5)
    two = GraphState(n=6, edges=[(0, 1), (0, 2), (3, 4), (3, 5)])
    st = eng.state_from_graph(two)
    st = eng.fuse(st, 2, 4)     # fuse leaf 2 with leaf 4
    out = eng.to_graphstate(st)
    p4 = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    assert lc_orbit_key(out) == lc_orbit_key(p4)


def test_disjoint_leaf_fusion_matches_complete_bipartite_rule(eng):
    """For disjoint components, {XX,ZZ} fusion = connect N(a) x N(b), delete a,b."""
    # star(0;1,2,3) + star(4;5,6): fuse leaf 3 with leaf 5
    g = GraphState(n=7, edges=[(0, 1), (0, 2), (0, 3), (4, 5), (4, 6)])
    st = eng.state_from_graph(g)
    st = eng.fuse(st, 3, 5)
    out = eng.to_graphstate(st)
    # expected: N(3)={0}, N(5)={4} -> edge 0-4; remaining qubits 0,1,2,4,6 -> relabel
    expected = GraphState(n=5, edges=[(0, 1), (0, 2), (0, 3), (3, 4)])
    assert lc_orbit_key(out) == lc_orbit_key(expected)


@pytest.mark.parametrize("g", [3, 4, 5, 6])
def test_ghz3_chain_gives_path(eng, g):
    """Chaining g GHZ3 stars with g-1 leaf fusions yields P_{g+2}: the
    F(path_N)=N-3 achievability witness."""
    n = 3 * g
    edges = []
    for i in range(g):
        c = 3 * i
        edges += [(c, c + 1), (c, c + 2)]
    st = eng.state_from_graph(GraphState(n=n, edges=edges))
    for i in range(g - 1):
        st = eng.fuse(st, 3 * i + 2, 3 * (i + 1) + 1)   # leaf of i with leaf of i+1
    out = eng.to_graphstate(st)
    path = GraphState(n=g + 2, edges=[(i, i + 1) for i in range(g + 1)])
    assert lc_orbit_key(out) == lc_orbit_key(path)


def test_intra_component_fusion_works(eng):
    """Fusing two qubits of the SAME component must not crash (needed for cycles)."""
    # P_6, fuse the two endpoint qubits -> should yield a 4-qubit state (cycle-ish)
    p6 = GraphState(n=6, edges=[(i, i + 1) for i in range(5)])
    st = eng.state_from_graph(p6)
    st = eng.fuse(st, 0, 5)
    out = eng.to_graphstate(st)
    assert out.n == 4   # 6 - 2; exact orbit checked in the A/B fuzz + M5c


def test_fuse_rejects_bad_qubits(eng):
    gs = GraphState(n=4, edges=[(0, 1), (2, 3)])
    st = eng.state_from_graph(gs)
    with pytest.raises(ValueError):
        eng.fuse(st, 0, 0)          # same qubit
    st2 = eng.fuse(st, 1, 2)
    with pytest.raises(ValueError):
        eng.fuse(st2, 1, 3)         # 1 is no longer active


def test_fusion_reduces_qubits_by_two(eng):
    gs = GraphState(n=6, edges=[(0, 1), (0, 2), (3, 4), (3, 5)])
    st = eng.state_from_graph(gs)
    assert len(st.active) == 6
    st = eng.fuse(st, 2, 4)
    assert len(st.active) == 4
```

- [ ] **Step 2: fail-first** — `uv run pytest tests/test_p5_fusion_stim.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Implement `fusion_stim.py`** per the interface + implementation notes. VERIFY the stim `postselect_observable` sign convention empirically first (prepare a known state, postselect, peek). The extraction's rank-completion loop: for each qubit column (in order), if current X-block rank < k and applying H at that qubit (swapping its X/Z columns) increases the rank, apply the swap; repeat until rank k (this terminates — a stabilizer matrix has full rank over [X|Z]).

- [ ] **Step 4: tests pass** — the goldens (P₄, complete-bipartite, chains) are the physics proof for engine A.

- [ ] **Step 5: Full suite + ruff + commit** — `feat: engine A — stim tableau fusion + LC graph extraction (P4/chain goldens)`

---

### Task 2: Engine B — independent GF(2) bitmask tableau (`domain/p5/fusion_gf2.py`)

**Files:**
- Create: `src/empiricist/domain/p5/fusion_gf2.py`
- Test: `tests/test_p5_fusion_gf2.py`

**The independence mandate:** NO stim import, NO numpy import. Generators are pure-Python **(x_bits: int, z_bits: int)** pairs (bit i = qubit i). The implementer must write from the physics spec below, NOT by translating engine A's code. Same public triple: `state_from_graph`, `fuse`, `to_graphstate` on a `GF2State` (tuple of generators + active mask).

**Physics spec for B (self-contained):**
- Graph state generators: for each vertex v: `x_bits = 1<<v`, `z_bits = OR of 1<<u for u in N(v)`.
- Two Paulis (x1,z1),(x2,z2) **anticommute** iff `parity(x1&z2) != parity(x2&z1)` (symplectic product = popcount(x1&z2) + popcount(x2&z1) mod 2 = 1).
- **Measuring** observable P on a stabilizer state (signs ignored): find generators anticommuting with P. If none: outcome deterministic, state unchanged. Else: pick one such generator g_pivot; replace every OTHER anticommuting generator g with g·g_pivot (bitwise XOR of x and z parts); replace g_pivot with P itself.
- **Fusion** (a,b): measure `X_aX_b` (x_bits = (1<<a)|(1<<b), z=0), then `Z_aZ_b` (z_bits = (1<<a)|(1<<b), x=0). Then **remove** a,b: by construction the final two replaced generators are exactly XX and ZZ on {a,b}; use Gaussian elimination (XOR of generators) to clear any a/b support from all other generators — pivot on the XX generator to clear X-support at a,b (multiply any generator with X or Y at a or b by it... careful: clearing must zero BOTH x and z bits at a and b for every remaining generator; use the XX and ZZ generators as pivots: XOR by XX clears paired X support, by ZZ clears paired Z support; single-sided support at a xor b cannot remain if the Bell pair is disentangled — assert it doesn't). Drop the two pivot generators; drop bits a,b (compact remaining bit positions to 0..k-1).
- **Extraction to graph** (own implementation, bitmask Gauss): with generators as rows of an implicit [X|Z] over k qubits — while the X-side rank < k, find a qubit j such that swapping x/z bits at position j across ALL generators increases the X-rank; swap (that's H on j, a local Clifford). Then row-reduce so the X side becomes the identity (each row i has x_bits == 1<<i after elimination); read the adjacency: row i's z_bits = neighbors of i (zero the diagonal bit). Build GraphState from those edges (assert symmetry: j in N(i) iff i in N(j)).

- [ ] **Step 1: failing tests** — `tests/test_p5_fusion_gf2.py`: the SAME golden set as Task 1 (roundtrip, GHZ₃ pair → P₄, complete-bipartite rule, chains → paths, intra-component, bad-qubit rejection, qubit count) but importing `GF2Engine` — write them fresh, do not import from the A test module.

- [ ] **Step 2: fail-first.**

- [ ] **Step 3: Implement `fusion_gf2.py`** from the physics spec. Pure Python ints only.

- [ ] **Step 4: tests pass.** If a golden disagrees with engine A's result, one of the two engines is WRONG — debug the physics (the complete-bipartite rule is the arbiter for disjoint leaf fusions), never adjust a golden.

- [ ] **Step 5: Add the independence guard test** (in the same file):

```python
def test_engine_b_is_independent_of_stim_and_numpy():
    import inspect
    from empiricist.domain.p5 import fusion_gf2
    src = inspect.getsource(fusion_gf2)
    assert "import stim" not in src and "import numpy" not in src
    assert "fusion_stim" not in src   # no cross-import of engine A
```

- [ ] **Step 6: Full suite + ruff + commit** — `feat: engine B — independent GF(2) bitmask fusion engine (same goldens)`

---

### Task 3: A≡B agreement fuzz + Construction artifact (`domain/p5/construction.py`)

**Files:**
- Create: `src/empiricist/domain/p5/construction.py`
- Test: `tests/test_p5_construction.py`, `tests/test_p5_ab_agreement.py`

- [ ] **Step 1: failing tests** — `tests/test_p5_ab_agreement.py` (the F3 heart):

```python
"""A/B agreement fuzz: the two independent engines must produce the SAME
LC-orbit key for the same fusion sequence. Disagreement = one engine is wrong."""

import random

import pytest

from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.fusion_gf2 import GF2Engine
from empiricist.domain.p5.fusion_stim import StimEngine
from empiricist.domain.p5.graphstate import GraphState


def random_connected_graph(rng, n):
    while True:
        edges = [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < 0.5]
        gs = GraphState(n=n, edges=edges)
        import networkx as nx
        if nx.is_connected(gs.to_networkx()):
            return gs


@pytest.mark.parametrize("seed", range(20))
def test_ab_agree_on_random_single_fusions(seed):
    rng = random.Random(seed)
    n = rng.randint(4, 7)
    gs = random_connected_graph(rng, n)
    a, b = rng.sample(range(n), 2)
    ea, eb = StimEngine(), GF2Engine()
    out_a = ea.to_graphstate(ea.fuse(ea.state_from_graph(gs), a, b))
    out_b = eb.to_graphstate(eb.fuse(eb.state_from_graph(gs), a, b))
    assert lc_orbit_key(out_a) == lc_orbit_key(out_b), (
        f"A/B DISAGREE on seed={seed} gs={sorted(gs.edges)} fuse=({a},{b})"
    )


@pytest.mark.parametrize("seed", range(10))
def test_ab_agree_on_multi_fusion_sequences(seed):
    rng = random.Random(1000 + seed)
    # two disjoint stars + extra edges, then 2 sequential fusions on random actives
    gs = GraphState(n=8, edges=[(0, 1), (0, 2), (0, 3), (4, 5), (4, 6), (4, 7)])
    ea, eb = StimEngine(), GF2Engine()
    sa, sb = ea.state_from_graph(gs), eb.state_from_graph(gs)
    active = list(range(8))
    for _ in range(2):
        a, b = rng.sample(active, 2)
        sa, sb = ea.fuse(sa, a, b), eb.fuse(sb, a, b)
        active.remove(a); active.remove(b)
    assert lc_orbit_key(ea.to_graphstate(sa)) == lc_orbit_key(eb.to_graphstate(sb))
```

And `tests/test_p5_construction.py`:

```python
"""The Construction artifact (spec Appendix E) and its apply() on both engines."""

import pytest

from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.construction import Construction, FusionOp, apply_construction, build_workspace
from empiricist.domain.p5.fusion_gf2 import GF2Engine
from empiricist.domain.p5.fusion_stim import StimEngine
from empiricist.domain.p5.graphstate import GraphState


def test_workspace_is_ghz3_stars():
    ws = build_workspace(resources=2)
    assert ws.n == 6
    assert ws.edges == frozenset({(0, 1), (0, 2), (3, 4), (3, 5)})


def test_p4_construction_verifies_on_both_engines():
    c = Construction(
        resources=2,
        steps=(FusionOp(a=2, b=4),),
        target=GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)]),
    )
    for eng in (StimEngine(), GF2Engine()):
        out = apply_construction(c, eng)
        assert lc_orbit_key(out) == lc_orbit_key(c.target)
    assert c.fusion_count == 1


def test_wrong_target_fails_verification():
    c = Construction(
        resources=2,
        steps=(FusionOp(a=2, b=4),),
        target=GraphState(n=4, edges=[(0, 1), (0, 2), (0, 3)]),  # star, NOT P4's orbit
    )
    out = apply_construction(c, StimEngine())
    assert lc_orbit_key(out) != lc_orbit_key(c.target)


def test_construction_rejects_wrong_target_size():
    with pytest.raises(ValueError):
        Construction(resources=2, steps=(FusionOp(a=2, b=4),),
                     target=GraphState(n=5, edges=[]))   # 3*2-2*1 = 4 != 5
```

- [ ] **Step 2: fail-first.**

- [ ] **Step 3: Implement `construction.py`:** frozen `FusionOp(a, b)`; frozen `Construction(resources, steps, target)` validating `target.n == 3*resources - 2*len(steps)`; `fusion_count` property; `build_workspace(resources)` = GHZ₃ star at qubits (3i; 3i+1, 3i+2) for each i; `apply_construction(c, engine)` = state_from_graph(workspace) → fuse each step in order → to_graphstate. (LocalClifford steps from spec Appendix E are OMITTED in v0: identity is up-to-LC, so they're no-ops — note this in the docstring.)

- [ ] **Step 4: tests pass** (the A≡B fuzz across 30 seeds is the F3 certificate mechanism working).

- [ ] **Step 5: Full suite + ruff + commit** — `feat: Construction artifact + A/B agreement fuzz (30 randomized seeds)`

---

### Task 4: Verifier protocol + certification-gated registry + golden suite; closeout

**Files:**
- Create: `src/empiricist/verifiers/__init__.py`, `src/empiricist/verifiers/base.py`, `src/empiricist/verifiers/stab_fusion.py`, `src/empiricist/verifiers/enum_fusion.py`, `src/empiricist/verifiers/registry.py`, `src/empiricist/verifiers/goldens.py`
- Test: `tests/test_verifiers.py`

**Design:**
- `base.py`: `FusionVerdict` = the ledger's `Verdict`; `VerifierResult(verdict, details: dict)`; the `Verifier` Protocol (`name`, `version`, `binary_hash` property = blake3 of the verifier's own module source + its engine module source, `applicable(artifact_kind)`, `verify(construction) -> VerifierResult`).
- `stab_fusion.py` / `enum_fusion.py`: wrap engines A/B. `verify(construction)`: apply_construction; PASS iff `lc_orbit_key(result) == lc_orbit_key(construction.target)`; details = `{lc_orbit_key, fusion_count, target_key}`. ERROR (not raise) on engine exceptions, with the message in details.
- `goldens.py`: `P5_GOLDEN_SUITE` = list of (Construction, expected_pass: bool) — the P₄ construction (pass), the chain constructions g=3..5 (pass), a wrong-target case (must FAIL — a suite that can't fail certifies nothing), plus `suite_hash()` = blake3 of the suite's canonical repr.
- `registry.py`: `Registry(ledger)` — `certify(verifier) -> Certification` (runs every golden; stamp PASS iff every case matches its expected outcome; `ledger.add_certification(...)` with suite hash + binary hash); `verify(verifier, construction)` raises `UncertifiedVerifierError` unless `ledger.is_certified(name, version, binary_hash)` AND the stamp's `golden_suite_hash == suite_hash()` (the full spec §7 rule — the M1-2 `get_certification` accessor exists for exactly this).
- **Agreement helper**: `verify_agreed(registry, construction) -> VerifierResult` — runs BOTH certified fusion verifiers; PASS only if both PASS **and** their result keys are identical; details records both. This is the function M5c/M6 call.

- [ ] **Step 1: failing tests** — `tests/test_verifiers.py`:

```python
"""Verifier protocol + certification-gated registry (spec §7, F3)."""

import pytest

from empiricist.domain.p5.construction import Construction, FusionOp
from empiricist.domain.p5.graphstate import GraphState
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Verdict
from empiricist.verifiers.enum_fusion import EnumFusionVerifier
from empiricist.verifiers.goldens import P5_GOLDEN_SUITE, suite_hash
from empiricist.verifiers.registry import Registry, UncertifiedVerifierError
from empiricist.verifiers.stab_fusion import StabFusionVerifier


P4 = Construction(resources=2, steps=(FusionOp(a=2, b=4),),
                  target=GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)]))
WRONG = Construction(resources=2, steps=(FusionOp(a=2, b=4),),
                     target=GraphState(n=4, edges=[(0, 1), (0, 2), (0, 3)]))


@pytest.fixture()
def registry(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    yield Registry(lg)
    lg.close()


def test_verify_refused_without_certification(registry):
    v = StabFusionVerifier()
    with pytest.raises(UncertifiedVerifierError):
        registry.verify(v, P4)


def test_certify_then_verify_pass(registry):
    v = StabFusionVerifier()
    stamp = registry.certify(v)
    assert stamp.verdict == Verdict.PASS
    assert stamp.golden_suite_hash == suite_hash()
    res = registry.verify(v, P4)
    assert res.verdict == Verdict.PASS
    assert "lc_orbit_key" in res.details


def test_wrong_target_fails_verification(registry):
    v = StabFusionVerifier()
    registry.certify(v)
    assert registry.verify(v, WRONG).verdict == Verdict.FAIL


def test_both_verifiers_certify_and_agree(registry):
    a, b = StabFusionVerifier(), EnumFusionVerifier()
    assert registry.certify(a).verdict == Verdict.PASS
    assert registry.certify(b).verdict == Verdict.PASS
    from empiricist.verifiers.registry import verify_agreed
    res = verify_agreed(registry, P4)
    assert res.verdict == Verdict.PASS
    assert res.details["stab_fusion_key"] == res.details["enum_fusion_key"]


def test_agreement_fails_on_wrong_target(registry):
    registry.certify(StabFusionVerifier())
    registry.certify(EnumFusionVerifier())
    from empiricist.verifiers.registry import verify_agreed
    assert verify_agreed(registry, WRONG).verdict == Verdict.FAIL


def test_golden_suite_contains_a_must_fail_case():
    """A suite that cannot fail certifies nothing (spec §7 mutation-resistance)."""
    assert any(expected is False for _, expected in P5_GOLDEN_SUITE)


def test_stamp_is_binary_hash_specific(registry):
    """Tampering with the verifier's code must invalidate its stamp."""
    v = StabFusionVerifier()
    registry.certify(v)
    class Tampered(StabFusionVerifier):
        @property
        def binary_hash(self):
            return "0" * 64
    with pytest.raises(UncertifiedVerifierError):
        registry.verify(Tampered(), P4)


def test_engine_error_is_error_verdict_not_crash(registry):
    v = StabFusionVerifier()
    registry.certify(v)
    bad = Construction(resources=2, steps=(FusionOp(a=0, b=0),),
                       target=GraphState(n=4, edges=[]))
    res = registry.verify(v, bad)
    assert res.verdict == Verdict.ERROR and "error" in res.details
```

Note: `Construction` validates target size at construction; `FusionOp(a=0,b=0)` passes size validation (fusion count 1) but the ENGINE rejects same-qubit fusion → the verifier must catch and return ERROR. If Construction itself rejects a==b at validation, adapt the bad-case to trigger an engine-level error another way (e.g. fusing an already-consumed qubit via two steps) — keep an ERROR-verdict path tested.

- [ ] **Step 2: fail-first.** — [ ] **Step 3: implement.** — [ ] **Step 4: tests pass.**

- [ ] **Step 5: Full suite + ruff; commit** — `feat: fusion verifiers + certification-gated registry + P5 golden suite`

- [ ] **Step 6: Push + PR**

```bash
git push -u origin feat/m5b-fusion-verifiers
env -u GH_TOKEN -u GITHUB_TOKEN gh pr create --base feat/m5a-p5-domain --head feat/m5b-fusion-verifiers \
  --title "M5b: two independent fusion verifiers + certification registry" \
  --body "<summary: engines A (stim) & B (pure GF(2) bitmask, no stim/numpy) implement the destructive Bell fusion independently; goldens (GHZ3+GHZ3=P4, complete-bipartite rule, chains=paths); 30-seed A/B agreement fuzz; Construction artifact; certification-stamp-gated registry with a must-fail golden. F3 made concrete.>"
```

---

## Plan self-review (done at write time)

- **Spec coverage (§8.3, §7, D6, App B/E):** fusion = tableau-level Bell measurement (never a graph rewrite) ✅ T1/T2; two independent engines, different data structures (stim+numpy vs pure-int bitmask), independence guard test ✅ T2; agreement = same LC-orbit key ✅ T3 fuzz + T4 verify_agreed; Construction artifact w/ size validation (N = 3g−2f) ✅ T3; Verifier protocol + registry stamped by (name, version, binary_hash) + suite-hash check (uses M1-2 get_certification) ✅ T4; golden suite with a must-fail case (mutation resistance) ✅ T4.
- **Physics anchors:** the complete-bipartite rule for disjoint {XX,ZZ} leaf fusion (independent arbiter); GHZ₃×GHZ₃→P₄; chains→paths (the F(path)=N−3 witness); roundtrip identity; intra-component fusion supported (cycles need it, per the M5c DP requirement); signs ignored = documented LC-safe simplification.
- **Known verification asks for implementers:** stim `postselect_observable` sign convention (verify empirically); the disentangled-Bell-pair assertion after fusion; extraction rank-completion termination. All flagged in-task.
- **Type consistency:** engines share the (state_from_graph, fuse, to_graphstate) shape consumed by apply_construction; lc_orbit_key (hex str, M5a) is the agreement token; Verdict/Certification/Ledger from M1-2 (`add_certification`, `is_certified`, `get_certification` all exist).
- **Deferred (documented):** LocalClifford steps in Construction (no-ops up to LC); wiring verify_agreed into the ledger Evidence rows + budgets (M6/M7); the memoized canonicalization API (M5c, noted on PR #4).

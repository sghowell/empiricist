# M19: P3 Domain Layer (linear-optical Bell-measurement schemes) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** A P3 domain layer — exact simulation of ancilla-boosted linear-optical Bell
measurements by two independent engines, a `verify_agreed`-style PASS/FAIL/ERROR contract, and
a golden suite pinned to exactly-known physics — so a Fable campaign (M20) can search schemes,
hunt certificates, and mine conjectures about `p*(k)`.

**Architecture:** A scheme is `(m, mesh, ancilla)`: `m` optical modes, a beamsplitter mesh
(guaranteeing unitarity by construction), and a `k`-photon ancilla Fock superposition on modes
`4..m-1`. Dual-rail Bell states live on modes 0–3. Engine A computes detection-pattern
probabilities via matrix permanents of the mesh's unitary; Engine B never forms the unitary or
a permanent — it applies each mesh element as an exact operator on the photon-number-sector
Fock basis. The assignment `f` is **derived** (a pattern is assigned to a Bell state iff only
that state can produce it), and the verifier reports the per-Bell-state success vector, its
min (the problem's `p`), and its average (the literature's figure). Engines share the mesh
convention definition and nothing else.

**Tech stack:** Python ≥3.11, numpy (complex128; cross-engine tolerance 1e-8), pytest.
No new dependencies. No subprocesses (pure in-process math — the `test_no_bare_subprocess`
rule is untouched).

**Design decisions (locked here):**
1. **Mesh, not raw unitary.** Schemes are parametrized as beamsplitter/phase lists so every
   emitted scheme is exactly unitary; a model can never submit a non-unitary `U`.
   Convention (used by BOTH engines, implemented independently): `bs(i, j, θ, φ)` acts on
   creation operators as `a†_i → cosθ·a†_i + e^{iφ}sinθ·a†_j`,
   `a†_j → −e^{−iφ}sinθ·a†_i + cosθ·a†_j`; `phase(i, α)` acts as `a†_i → e^{iα}a†_i`.
2. **Two metrics.** `p_min = min_B Σ_{f(n)=B} Pr[n|B]` (the problem's definition) and
   `p_avg = (1/4)Σ_B …` (the literature's). Both are recorded; claims name their metric.
3. **Floats now, exactness at the certificate layer.** M19 engines are complex128 with 1e-8
   agreement tolerance (fine for goldens with values like 3/4 exactly). Exact-rational SOS
   certificates are M20's job and verify independently of engine arithmetic.
4. **Golden values are the spec.** Where a published construction (Grice) is reconstructed
   from the paper, the acceptance test pins the *published exact success vector*; if the mesh
   reconstruction is wrong the golden fails and the mesh — never the golden — gets fixed.

**File structure:**
- Create: `src/empiricist/domain/p3/__init__.py` (empty)
- Create: `src/empiricist/domain/p3/fock.py` — pattern enumeration + combinatorics
- Create: `src/empiricist/domain/p3/interferometer.py` — mesh → unitary (Engine A's input)
- Create: `src/empiricist/domain/p3/engine_permanent.py` — Engine A
- Create: `src/empiricist/domain/p3/engine_fock.py` — Engine B
- Create: `src/empiricist/domain/p3/scheme.py` — BellScheme, Bell states, derived `f`, metrics
- Create: `src/empiricist/domain/p3/verify.py` — the agreed-verdict contract
- Test: `tests/test_p3_fock.py`, `tests/test_p3_engines.py`, `tests/test_p3_scheme.py`,
  `tests/test_p3_goldens.py`

---

### Task 1: Fock combinatorics (`fock.py`)

**Files:** Create `src/empiricist/domain/p3/fock.py`, `src/empiricist/domain/p3/__init__.py`;
Test `tests/test_p3_fock.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_p3_fock.py
from empiricist.domain.p3.fock import patterns, pattern_index, factorial_prod


def test_patterns_enumerates_all_compositions():
    ps = patterns(n_photons=2, n_modes=3)
    assert ps == [(0, 0, 2), (0, 1, 1), (0, 2, 0), (1, 0, 1), (1, 1, 0), (2, 0, 0)]


def test_patterns_counts():
    # compositions of n into m parts: C(n+m-1, m-1)
    assert len(patterns(4, 8)) == 330
    assert len(patterns(0, 5)) == 1  # the vacuum


def test_pattern_index_roundtrip():
    ps = patterns(3, 4)
    for i, p in enumerate(ps):
        assert pattern_index(p) == i or ps[pattern_index(p)] == p


def test_factorial_prod():
    assert factorial_prod((2, 0, 3)) == 12
```

- [ ] **Step 2: Run tests, verify they fail** — `uv run pytest tests/test_p3_fock.py -q`
      (fails: module not found)

- [ ] **Step 3: Implement**

```python
# src/empiricist/domain/p3/fock.py
"""Fock-basis combinatorics for the P3 linear-optics domain.

A detection pattern is a tuple (n_0, ..., n_{m-1}) of photon counts summing to
the total photon number. `patterns` enumerates the full n-photon sector in a
deterministic lexicographic order shared by both engines.
"""

from __future__ import annotations

from functools import lru_cache
from math import factorial


@lru_cache(maxsize=None)
def patterns(n_photons: int, n_modes: int) -> list[tuple[int, ...]]:
    """All (n_0..n_{m-1}) with sum == n_photons, lexicographically sorted."""
    if n_modes == 1:
        return [(n_photons,)]
    out: list[tuple[int, ...]] = []
    for first in range(n_photons + 1):
        for rest in patterns(n_photons - first, n_modes - 1):
            out.append((first, *rest))
    return out


def pattern_index(pattern: tuple[int, ...]) -> int:
    """Index of `pattern` within patterns(sum(pattern), len(pattern))."""
    return patterns(sum(pattern), len(pattern)).index(pattern)


def factorial_prod(pattern: tuple[int, ...]) -> int:
    out = 1
    for n in pattern:
        out *= factorial(n)
    return out
```

- [ ] **Step 4: Run tests, verify pass** — `uv run pytest tests/test_p3_fock.py -q`
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat(p3): Fock pattern combinatorics"`

### Task 2: Mesh → unitary (`interferometer.py`)

**Files:** Create `src/empiricist/domain/p3/interferometer.py`; Test `tests/test_p3_engines.py`
(first tests)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_p3_engines.py
import numpy as np
from empiricist.domain.p3.interferometer import Mesh, mesh_unitary


def test_single_bs_unitary():
    # Convention: a†_0 -> c a†_0 + s a†_1, a†_1 -> -s a†_0 + c a†_1 (phi = 0);
    # columns of U are the images of the input modes.
    m = Mesh(n_modes=2, elements=[("bs", 0, 1, np.pi / 4, 0.0)])
    u = mesh_unitary(m)
    c = 1 / np.sqrt(2)
    assert np.allclose(u, np.array([[c, -c], [c, c]]), atol=1e-12)


def test_mesh_unitary_is_unitary_random():
    rng = np.random.default_rng(0)
    for _ in range(20):
        n = int(rng.integers(2, 9))
        els = []
        for _ in range(int(rng.integers(1, 12))):
            i, j = sorted(rng.choice(n, size=2, replace=False).tolist())
            els.append(("bs", i, j, float(rng.uniform(0, np.pi)), float(rng.uniform(0, 2 * np.pi))))
        els.append(("phase", int(rng.integers(0, n)), float(rng.uniform(0, 2 * np.pi)), 0.0, 0.0))
        u = mesh_unitary(Mesh(n_modes=n, elements=els))
        assert np.allclose(u @ u.conj().T, np.eye(n), atol=1e-10)
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement**

```python
# src/empiricist/domain/p3/interferometer.py
"""Beamsplitter-mesh parametrization of a passive interferometer.

The mesh guarantees unitarity by construction -- a scheme emitted as a mesh can
never be non-unitary. Convention (the ONE definition both engines consume):

  bs(i, j, theta, phi):   a†_i -> cos(theta) a†_i + e^{i phi} sin(theta) a†_j
                          a†_j -> -e^{-i phi} sin(theta) a†_i + cos(theta) a†_j
  phase(i, alpha):        a†_i -> e^{i alpha} a†_i

`mesh_unitary` composes the elements IN ORDER into the m x m mode unitary U with
a†_i -> sum_j U[j, i] a†_j (columns are images of input modes).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# element: ("bs", i, j, theta, phi) or ("phase", i, alpha, 0.0, 0.0)
Element = tuple[str, int, int | float, float, float]


@dataclass(frozen=True)
class Mesh:
    n_modes: int
    elements: list[Element] = field(default_factory=list)


def _element_unitary(n: int, el: Element) -> np.ndarray:
    u = np.eye(n, dtype=np.complex128)
    kind = el[0]
    if kind == "bs":
        _, i, j, theta, phi = el
        i, j = int(i), int(j)
        c, s = np.cos(theta), np.sin(theta)
        u[i, i] = c
        u[j, i] = np.exp(1j * phi) * s
        u[i, j] = -np.exp(-1j * phi) * s
        u[j, j] = c
    elif kind == "phase":
        _, i, alpha = el[0], el[1], el[2]
        u[int(i), int(i)] = np.exp(1j * float(alpha))
    else:
        raise ValueError(f"unknown mesh element kind {kind!r}")
    return u


def mesh_unitary(mesh: Mesh) -> np.ndarray:
    u = np.eye(mesh.n_modes, dtype=np.complex128)
    for el in mesh.elements:
        u = _element_unitary(mesh.n_modes, el) @ u
    return u
```

- [ ] **Step 4: Run tests, verify pass.**
- [ ] **Step 5: Commit** — `git commit -m "feat(p3): beamsplitter mesh -> mode unitary"`

### Task 3: Engine A — permanents (`engine_permanent.py`)

**Files:** Create `src/empiricist/domain/p3/engine_permanent.py`; extend
`tests/test_p3_engines.py`

- [ ] **Step 1: Write the failing tests** (HOM dip: two photons into a 50:50 BS never
      anti-bunch — the exactly-known physics pin)

```python
def test_hom_dip_engine_a():
    from empiricist.domain.p3.engine_permanent import PermanentEngine
    m = Mesh(n_modes=2, elements=[("bs", 0, 1, np.pi / 4, 0.0)])
    eng = PermanentEngine()
    dist = eng.output_distribution(m, {(1, 1): 1.0})
    assert abs(dist.get((1, 1), 0.0)) < 1e-12          # HOM: no coincidences
    assert abs(dist[(2, 0)] - 0.5) < 1e-12
    assert abs(dist[(0, 2)] - 0.5) < 1e-12
    assert abs(sum(dist.values()) - 1.0) < 1e-12


def test_superposed_input_engine_a():
    from empiricist.domain.p3.engine_permanent import PermanentEngine
    m = Mesh(n_modes=2, elements=[])
    eng = PermanentEngine()
    amp = 1 / np.sqrt(2)
    dist = eng.output_distribution(m, {(1, 0): amp, (0, 1): amp})
    assert abs(dist[(1, 0)] - 0.5) < 1e-12 and abs(dist[(0, 1)] - 0.5) < 1e-12
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement** — amplitude `⟨S|Û|T⟩ = Per(U[S,T]) / √(∏s_i!∏t_j!)`, where
      `U[S,T]` repeats column `j` `t_j` times and row `i` `s_i` times; Ryser's formula for
      the permanent; inputs are Fock superpositions (dict pattern → complex amplitude).

```python
# src/empiricist/domain/p3/engine_permanent.py
"""Engine A: detection-pattern distributions via matrix permanents.

For input Fock state |T> and output |S> (equal total photon number n),
  <S| U_hat |T> = Per(U[S, T]) / sqrt(prod_i s_i! * prod_j t_j!)
where U[S, T] repeats column j of U t_j times and row i s_i times. Inputs are
finite Fock superpositions; amplitudes add linearly before squaring.
Independence: this engine is the ONLY code that forms U or a permanent.
"""

from __future__ import annotations

import numpy as np

from .fock import factorial_prod, patterns
from .interferometer import Mesh, mesh_unitary

FockState = dict[tuple[int, ...], complex]


def _permanent(a: np.ndarray) -> complex:
    """Ryser's formula with Gray-code-free simple subset sum (n <= ~12 here)."""
    n = a.shape[0]
    if n == 0:
        return 1.0 + 0.0j
    total = 0.0 + 0.0j
    for mask in range(1, 1 << n):
        col_sum = np.zeros(n, dtype=np.complex128)
        bits = 0
        for j in range(n):
            if mask & (1 << j):
                col_sum += a[:, j]
                bits += 1
        total += (-1) ** bits * np.prod(col_sum)
    return ((-1) ** n) * total


def _submatrix(u: np.ndarray, out_pattern: tuple[int, ...], in_pattern: tuple[int, ...]) -> np.ndarray:
    rows = [i for i, s in enumerate(out_pattern) for _ in range(s)]
    cols = [j for j, t in enumerate(in_pattern) for _ in range(t)]
    return u[np.ix_(rows, cols)]


class PermanentEngine:
    name = "permanent"

    def output_distribution(self, mesh: Mesh, input_state: FockState) -> dict[tuple[int, ...], float]:
        u = mesh_unitary(mesh)
        n_photons = sum(next(iter(input_state)))
        for pat in input_state:
            if sum(pat) != n_photons:
                raise ValueError("input superposition mixes photon numbers")
        out: dict[tuple[int, ...], float] = {}
        for s in patterns(n_photons, mesh.n_modes):
            amp = 0.0 + 0.0j
            for t, a_t in input_state.items():
                if a_t == 0:
                    continue
                per = _permanent(_submatrix(u, s, t))
                amp += a_t * per / np.sqrt(factorial_prod(s) * factorial_prod(t))
            p = abs(amp) ** 2
            if p > 1e-15:
                out[s] = float(p)
        return out
```

- [ ] **Step 4: Run tests, verify pass.**
- [ ] **Step 5: Commit** — `git commit -m "feat(p3): Engine A (permanent-based)"`

### Task 4: Engine B — Fock-space evolution (`engine_fock.py`)

**Files:** Create `src/empiricist/domain/p3/engine_fock.py`; extend `tests/test_p3_engines.py`

Engine B never forms `U` and never computes a permanent: it applies each mesh element
directly as an operator on the n-photon Fock basis (2-mode beamsplitter action by binomial
expansion of the transformed creation operators). Only `fock.py` (basis order) and the mesh
*convention* are shared with Engine A.

- [ ] **Step 1: Write the failing tests** — the same HOM/superposition tests as Task 3 but for
      `FockEngine`, PLUS the cross-engine fuzz (the M5b pattern — this is the core warrant):

```python
def test_engines_agree_fuzz():
    from empiricist.domain.p3.engine_fock import FockEngine
    from empiricist.domain.p3.engine_permanent import PermanentEngine
    rng = np.random.default_rng(7)
    for trial in range(30):
        n_modes = int(rng.integers(2, 7))
        n_photons = int(rng.integers(1, 4))
        els = []
        for _ in range(int(rng.integers(1, 10))):
            i, j = sorted(rng.choice(n_modes, size=2, replace=False).tolist())
            els.append(("bs", i, j, float(rng.uniform(0, np.pi)), float(rng.uniform(0, 2 * np.pi))))
        mesh = Mesh(n_modes=n_modes, elements=els)
        from empiricist.domain.p3.fock import patterns
        basis = patterns(n_photons, n_modes)
        amps = rng.normal(size=len(basis)) + 1j * rng.normal(size=len(basis))
        amps /= np.linalg.norm(amps)
        state = {b: complex(a) for b, a in zip(basis, amps)}
        da = PermanentEngine().output_distribution(mesh, state)
        db = FockEngine().output_distribution(mesh, state)
        keys = set(da) | set(db)
        for k in keys:
            assert abs(da.get(k, 0.0) - db.get(k, 0.0)) < 1e-8, (trial, k)
        assert abs(sum(da.values()) - 1.0) < 1e-9
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement**

```python
# src/empiricist/domain/p3/engine_fock.py
"""Engine B: direct Fock-space evolution, element by element.

Never forms the mode unitary and never computes a permanent. Each mesh element
acts on the n-photon sector: a 2-mode beamsplitter maps |n1, n2> by binomial
expansion of (cos a†_i + e^{i phi} sin a†_j)^{n1} (-e^{-i phi} sin a†_i + cos a†_j)^{n2},
with sqrt-factorial normalization. Shares ONLY fock.py's basis order and the mesh
convention definition with Engine A.
"""

from __future__ import annotations

from math import comb, factorial, sqrt

import numpy as np

from .fock import patterns
from .interferometer import Mesh

FockState = dict[tuple[int, ...], complex]


def _bs_two_mode(n1: int, n2: int, theta: float, phi: float) -> dict[tuple[int, int], complex]:
    """Image of |n1, n2> under bs(theta, phi), as {(p, q): amplitude}."""
    c, s = np.cos(theta), np.sin(theta)
    e_pos, e_neg = np.exp(1j * phi), np.exp(-1j * phi)
    out: dict[tuple[int, int], complex] = {}
    for k1 in range(n1 + 1):          # a†_i exponent from the first factor
        for k2 in range(n2 + 1):      # a†_i exponent from the second factor
            coeff = (
                comb(n1, k1) * comb(n2, k2)
                * (c ** k1) * ((e_pos * s) ** (n1 - k1))
                * ((-e_neg * s) ** k2) * (c ** (n2 - k2))
            )
            p, q = k1 + k2, (n1 - k1) + (n2 - k2)
            norm = sqrt(factorial(p) * factorial(q)) / sqrt(factorial(n1) * factorial(n2))
            out[(p, q)] = out.get((p, q), 0.0 + 0.0j) + coeff * norm
    return out


class FockEngine:
    name = "fock"

    def output_distribution(self, mesh: Mesh, input_state: FockState) -> dict[tuple[int, ...], float]:
        state = {tuple(k): complex(v) for k, v in input_state.items()}
        for el in mesh.elements:
            if el[0] == "bs":
                _, i, j, theta, phi = el
                i, j = int(i), int(j)
                nxt: FockState = {}
                for pat, amp in state.items():
                    for (p, q), c in _bs_two_mode(pat[i], pat[j], float(theta), float(phi)).items():
                        new = list(pat)
                        new[i], new[j] = p, q
                        key = tuple(new)
                        nxt[key] = nxt.get(key, 0.0 + 0.0j) + amp * c
                state = nxt
            elif el[0] == "phase":
                _, i, alpha = el[0], int(el[1]), float(el[2])
                state = {pat: amp * np.exp(1j * alpha * pat[i]) for pat, amp in state.items()}
            else:
                raise ValueError(f"unknown mesh element kind {el[0]!r}")
        return {pat: float(abs(amp) ** 2) for pat, amp in state.items() if abs(amp) ** 2 > 1e-15}
```

- [ ] **Step 4: Run all engine tests, verify pass (30/30 fuzz agreement).**
- [ ] **Step 5: Commit** — `git commit -m "feat(p3): Engine B (Fock evolution) + cross-engine fuzz"`

### Task 5: Schemes, Bell states, derived assignment, metrics (`scheme.py`)

**Files:** Create `src/empiricist/domain/p3/scheme.py`; Test `tests/test_p3_scheme.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_p3_scheme.py
import numpy as np
from empiricist.domain.p3.interferometer import Mesh
from empiricist.domain.p3.scheme import (
    BELL_LABELS, BellScheme, bell_input_states, evaluate_scheme,
)
from empiricist.domain.p3.engine_permanent import PermanentEngine


def test_bell_states_are_normalized_two_photon():
    for label, state in bell_input_states(n_modes=4, ancilla={}).items():
        assert abs(sum(abs(a) ** 2 for a in state.values()) - 1.0) < 1e-12
        assert all(sum(p) == 2 for p in state)


def test_standard_bsm_success_vector():
    # 50:50 BS between corresponding rails: identifies Psi+ and Psi- with certainty,
    # Phi+ / Phi- are mutually ambiguous. Per-B success = (0, 0, 1, 1); avg 1/2; min 0.
    scheme = BellScheme(
        n_modes=4, n_ancilla_photons=0, ancilla={},
        mesh=Mesh(n_modes=4, elements=[("bs", 0, 2, np.pi / 4, 0.0),
                                       ("bs", 1, 3, np.pi / 4, 0.0)]),
    )
    report = evaluate_scheme(scheme, PermanentEngine())
    per_b = report.success_by_state
    assert abs(per_b["phi+"]) < 1e-10 and abs(per_b["phi-"]) < 1e-10
    assert abs(per_b["psi+"] - 1.0) < 1e-10 and abs(per_b["psi-"] - 1.0) < 1e-10
    assert abs(report.p_avg - 0.5) < 1e-10
    assert abs(report.p_min - 0.0) < 1e-10
    assert report.unambiguous  # the derived f never mislabels
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement**

```python
# src/empiricist/domain/p3/scheme.py
"""Bell-measurement schemes: dual-rail Bell inputs, derived assignment, metrics.

Dual-rail encoding on modes 0..3 (qubit A rails 0,1; qubit B rails 2,3):
  |phi+-> = (|1,0,1,0> +- |0,1,0,1>)/sqrt(2)
  |psi+-> = (|1,0,0,1> +- |0,1,1,0>)/sqrt(2)
The ancilla is a k-photon Fock superposition on modes 4..m-1. The assignment f
is DERIVED: pattern n is assigned to B iff Pr[n|B] > tol and Pr[n|B'] <= tol
for the other three -- so schemes are unambiguous by construction and the only
reported quantities are the per-state success probabilities.

Metrics (design decision D2): p_min = min_B (the problem's p) AND
p_avg = mean_B (the literature's figure). Claims must name their metric.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from .interferometer import Mesh

BELL_LABELS = ("phi+", "phi-", "psi+", "psi-")
_AMBIG_TOL = 1e-11

FockState = dict[tuple[int, ...], complex]


def _embed(pattern4: tuple[int, int, int, int], ancilla_pattern: tuple[int, ...]) -> tuple[int, ...]:
    return (*pattern4, *ancilla_pattern)


def bell_input_states(n_modes: int, ancilla: FockState) -> dict[str, FockState]:
    """The four Bell (x) ancilla input states on n_modes modes."""
    anc = ancilla if ancilla else {(): 1.0 + 0.0j}
    r = 1 / sqrt(2)
    bell4 = {
        "phi+": {(1, 0, 1, 0): r, (0, 1, 0, 1): r},
        "phi-": {(1, 0, 1, 0): r, (0, 1, 0, 1): -r},
        "psi+": {(1, 0, 0, 1): r, (0, 1, 1, 0): r},
        "psi-": {(1, 0, 0, 1): r, (0, 1, 1, 0): -r},
    }
    out: dict[str, FockState] = {}
    for label, b4 in bell4.items():
        state: FockState = {}
        for p4, a4 in b4.items():
            for pa, aa in anc.items():
                full = _embed(p4, tuple(pa))
                if len(full) != n_modes:
                    raise ValueError("ancilla pattern length must be n_modes - 4")
                state[full] = a4 * aa
        out[label] = state
    return out


@dataclass(frozen=True)
class BellScheme:
    n_modes: int
    n_ancilla_photons: int
    ancilla: FockState          # patterns on modes 4..m-1; {} means no ancilla
    mesh: Mesh

    def validate(self) -> None:
        if self.mesh.n_modes != self.n_modes:
            raise ValueError("mesh/scheme mode mismatch")
        if self.ancilla:
            norms = sum(abs(a) ** 2 for a in self.ancilla.values())
            if abs(norms - 1.0) > 1e-9:
                raise ValueError("ancilla not normalized")
            for pat in self.ancilla:
                if len(pat) != self.n_modes - 4:
                    raise ValueError("ancilla pattern on wrong number of modes")
                if sum(pat) != self.n_ancilla_photons:
                    raise ValueError("ancilla photon number mismatch")
        elif self.n_ancilla_photons != 0:
            raise ValueError("k > 0 requires an ancilla state")


@dataclass(frozen=True)
class SchemeReport:
    success_by_state: dict[str, float]
    p_min: float
    p_avg: float
    unambiguous: bool           # always True for the derived f; kept for the record
    distributions: dict[str, dict[tuple[int, ...], float]]


def evaluate_scheme(scheme: BellScheme, engine) -> SchemeReport:
    scheme.validate()
    dists = {
        label: engine.output_distribution(scheme.mesh, state)
        for label, state in bell_input_states(scheme.n_modes, scheme.ancilla).items()
    }
    success = dict.fromkeys(BELL_LABELS, 0.0)
    all_patterns = set().union(*dists.values())
    for pat in all_patterns:
        probs = {b: dists[b].get(pat, 0.0) for b in BELL_LABELS}
        supported = [b for b, p in probs.items() if p > _AMBIG_TOL]
        if len(supported) == 1:
            success[supported[0]] += probs[supported[0]]
    p_min = min(success.values())
    p_avg = sum(success.values()) / 4.0
    return SchemeReport(success_by_state=success, p_min=p_min, p_avg=p_avg,
                        unambiguous=True, distributions=dists)
```

- [ ] **Step 4: Run tests, verify pass.**
- [ ] **Step 5: Commit** — `git commit -m "feat(p3): BellScheme + derived assignment + metrics"`

### Task 6: The agreed-verdict contract (`verify.py`)

**Files:** Create `src/empiricist/domain/p3/verify.py`; extend `tests/test_p3_scheme.py`

Mirrors P5's F3 discipline: PASS iff both engines agree (per-pattern, per-Bell-state, 1e-8)
and the claimed metric is achieved; FAIL is an honest miss (engines agree, claim not met);
ERROR is engine disagreement — the stop-the-world alarm.

- [ ] **Step 1: Write the failing tests**

```python
def test_verify_agreed_pass_and_fail():
    from empiricist.domain.p3.verify import verify_scheme_agreed
    scheme = ...  # the standard BSM from test_standard_bsm_success_vector
    ok = verify_scheme_agreed(scheme, claimed_p_avg=0.5)
    assert ok.verdict == "PASS" and abs(ok.report.p_avg - 0.5) < 1e-10
    miss = verify_scheme_agreed(scheme, claimed_p_avg=0.75)
    assert miss.verdict == "FAIL"


def test_verify_agreed_error_on_disagreement(monkeypatch):
    from empiricist.domain.p3 import verify as vmod
    from empiricist.domain.p3.verify import verify_scheme_agreed

    class LyingEngine(vmod.FockEngine):
        def output_distribution(self, mesh, state):
            d = super().output_distribution(mesh, state)
            k = next(iter(d))
            d[k] = d[k] + 0.5   # corrupt
            return d

    monkeypatch.setattr(vmod, "FockEngine", LyingEngine)
    r = verify_scheme_agreed(scheme, claimed_p_avg=0.5)
    assert r.verdict == "ERROR"
```

(Fill `scheme = ...` with the standard-BSM construction from Task 5's test — repeat it, do
not import across test files.)

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement**

```python
# src/empiricist/domain/p3/verify.py
"""Two-engine agreed verdict for P3 schemes (the F3 discipline).

PASS: engines agree on every per-Bell-state distribution (1e-8) and the claimed
metric is achieved (1e-9). FAIL: engines agree, claim not met. ERROR: the
engines disagree -- stop the world; a physics-model bug, never a search miss.
"""

from __future__ import annotations

from dataclasses import dataclass

from .engine_fock import FockEngine
from .engine_permanent import PermanentEngine
from .scheme import BELL_LABELS, BellScheme, SchemeReport, evaluate_scheme

_AGREE_TOL = 1e-8
_CLAIM_TOL = 1e-9


@dataclass(frozen=True)
class AgreedResult:
    verdict: str                 # "PASS" | "FAIL" | "ERROR"
    report: SchemeReport | None
    detail: str


def verify_scheme_agreed(
    scheme: BellScheme,
    *,
    claimed_p_min: float | None = None,
    claimed_p_avg: float | None = None,
) -> AgreedResult:
    ra = evaluate_scheme(scheme, PermanentEngine())
    rb = evaluate_scheme(scheme, FockEngine())
    for b in BELL_LABELS:
        keys = set(ra.distributions[b]) | set(rb.distributions[b])
        for k in keys:
            da = ra.distributions[b].get(k, 0.0)
            db = rb.distributions[b].get(k, 0.0)
            if abs(da - db) > _AGREE_TOL:
                return AgreedResult("ERROR", None,
                                    f"engine disagreement on {b} pattern {k}: {da} vs {db}")
    claims_met = True
    if claimed_p_min is not None and ra.p_min < claimed_p_min - _CLAIM_TOL:
        claims_met = False
    if claimed_p_avg is not None and ra.p_avg < claimed_p_avg - _CLAIM_TOL:
        claims_met = False
    return AgreedResult("PASS" if claims_met else "FAIL", ra,
                        "agreed" if claims_met else "claim not achieved")
```

- [ ] **Step 4: Run tests, verify pass.**
- [ ] **Step 5: Commit** — `git commit -m "feat(p3): two-engine agreed-verdict contract"`

### Task 7: Golden suite (`tests/test_p3_goldens.py`)

**Files:** Test `tests/test_p3_goldens.py` (and, if the Grice mesh needs a helper, put the
construction in `src/empiricist/domain/p3/known_schemes.py`)

The exactly-known physics pins. **The published success vectors are the spec** (design
decision D4): if a reconstruction misses its vector, fix the mesh against the paper — never
relax the golden.

- [ ] **Step 1: Standard BSM golden** — per-state vector `(0, 0, 1, 1)`, `p_avg = 1/2`,
      `p_min = 0` (already pinned in Task 5's test; here re-asserted through
      `verify_scheme_agreed`, both engines).

- [ ] **Step 2: Grice boosted golden.** Construct Grice's k=2 scheme (PRA 84, 042331 (2011)):
      8 modes; ancilla = dual-rail Bell pair `(|1,0,1,0⟩+|0,1,0,1⟩)/√2` on modes 4–7; first
      layer = the standard BSM beamsplitters on the input pair, second layer interferes the
      previously-ambiguous outputs with the ancilla through 50:50 beamsplitters
      (rail-matched: modes (0,4),(1,5),(2,6),(3,7) — adjust pairing against the paper until
      the golden passes). Acceptance (exact published values):

```python
def test_grice_boosted_success_vector():
    scheme = grice_scheme()          # in known_schemes.py
    r = verify_scheme_agreed(scheme, claimed_p_avg=0.75)
    assert r.verdict == "PASS"
    v = r.report.success_by_state
    assert abs(v["psi+"] - 1.0) < 1e-9 and abs(v["psi-"] - 1.0) < 1e-9
    assert abs(v["phi+"] - 0.5) < 1e-9 and abs(v["phi-"] - 0.5) < 1e-9
    assert abs(r.report.p_avg - 0.75) < 1e-9 and abs(r.report.p_min - 0.5) < 1e-9
```

- [ ] **Step 3: No-perfect-BM sanity** — over the Task 4 fuzz meshes reinterpreted as k=0
      schemes (4 modes), assert `p_avg < 1 - 1e-6` always (perfect linear-optical BM is
      impossible; a fuzz counterexample means an engine bug).

- [ ] **Step 4: Run the full suite** — `uv run pytest tests/test_p3_goldens.py -q`; all pass.
- [ ] **Step 5: Commit** — `git commit -m "feat(p3): golden suite (standard BSM, Grice 3/4)"`

### Task 8: Ledger + certification wiring

**Files:** Modify `src/empiricist/verifiers/registry.py` (pattern-match how the P5 fusion
pair registers); Test extend `tests/test_p3_scheme.py`

- [ ] **Step 1:** Register the P3 engine pair in the certification registry exactly as M5b
      registered the fusion pair: verifier name `p3_scheme_agreed`, version `1.0`,
      `binary_hash` = blake3 over `fock.py + interferometer.py + engine_permanent.py +
      engine_fock.py + scheme.py + verify.py`, golden-suite gate = Task 7's tests. Read
      `registry.py` first and mirror its existing registration/certification API — do not
      invent a parallel one.
- [ ] **Step 2:** Test: a `get_certification`-style lookup returns the P3 pair with the
      golden hash; evaluating a scheme through the registry writes a `runs` row (provenance)
      exactly as P5 verifications do.
- [ ] **Step 3:** Run `uv run pytest -m "not slow and not slow_lean" -q` — full fast suite
      green (including `test_no_bare_subprocess`).
- [ ] **Step 4: Commit** — `git commit -m "feat(p3): certification registry + ledger wiring"`

### Task 9: Model-facing schema (`llm/schemas.py`)

**Files:** Modify `src/empiricist/llm/schemas.py`; extend an existing schema test file

- [ ] **Step 1:** Add `BellSchemeOut(_Closed)`: `n_modes: int`, `n_ancilla_photons: int`,
      `ancilla: list[tuple[list[int], float, float]]` (pattern, re, im),
      `mesh: list[tuple[str, int, int, float, float]]`, `claimed_p_min: float`,
      `claimed_p_avg: float`, `notes: str = ""` — plus a `to_scheme()` converter in
      `scheme.py` with validation (photon counts, normalization, mode bounds). Schema-valid
      guarantees SHAPE only; `verify_scheme_agreed` decides truth (the M4 discipline).
- [ ] **Step 2:** Test: a valid JSON round-trips to a `BellScheme` and evaluates; an
      unnormalized ancilla raises on `validate()`.
- [ ] **Step 3:** Run the fast suite; commit —
      `git commit -m "feat(p3): BellSchemeOut model schema + converter"`

---

## Acceptance for the milestone (all must hold before the PR)

1. `uv run pytest -m "not slow and not slow_lean" -q` — green, including 30/30 cross-engine
   fuzz agreement and the golden suite.
2. `uv run ruff check src tests` — clean.
3. The two engines share only `fock.py`'s basis order and the mesh-convention definition
   (grep: `engine_fock.py` must not import `interferometer.mesh_unitary` or
   `engine_permanent`; `engine_permanent.py` must not import `engine_fock`).
4. Grice golden pins per-state `(1/2, 1/2, 1, 1)`, `p_avg = 3/4`, `p_min = 1/2` — and the
   min-vs-avg distinction is recorded in `scheme.py`'s module docstring.
5. No new subprocess call sites; no change to the Lean gate or its allow-lists.

## Explicitly out of scope (M20+)

- The SOS/SDP certificate pipeline (upper bounds on `p*(k)`) and its exact-rational Lean
  verification.
- The mode-bound reduction (P3(iv)) and any Fable campaign (search/conjecture over schemes —
  including the sharp opening question M19 surfaces: *is there a k=0 scheme with
  `p_min = 1/2`, and a k=2 scheme with `p_min = 3/4`?* — the min-balanced variants of the
  classical results).
- Exact-arithmetic engines (floats + 1e-8 agreement suffice for the golden tier).

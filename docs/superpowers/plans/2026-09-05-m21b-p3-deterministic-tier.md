# M21b: P3 Deterministic Tier + Exact Witnesses Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give P3 the deterministic tier P5 always had — a numerical optimizer over meshes
and ancillas that maps the k=1 (and k=0/k=2 sanity) landscape for BOTH metrics without
model spend — and an EXACT evaluator so that a scheme whose mesh angles are multiples of
π/4 and whose ancilla amplitudes live in ℚ(i, √2) gets its success vector computed in exact
arithmetic and ingested at CERTIFIED as a witness (e.g. `p*_min(1) ≥ 1/16`, "all four Bell
states identified with one ancilla photon").

**Architecture:** `domain/p3/exact.py` implements the number field ℚ(ζ₈) = ℚ(i, √2) over
`fractions.Fraction` (stdlib only, no numpy) and re-derives the engines' probability
formula `Pr[S|ψ] = |Σ_T a_T perm(U[S,T]) / √(Π t!)|² / Π s!` in that field, with an EXACT
assignment (a pattern identifies B iff its other three probabilities are exactly zero).
`verifiers/p3_exact.py` wraps it as a certified `Verifier` (golden suite: standard BSM,
Grice, must-fail claims, an unsupported-angle scheme) and `domain/p3/exact_ingest.py`
records a certified PASS at CERTIFIED (kind `certificate`) through
`record_claimed_artifact`, exactly like M21a's SOS path. `domain/p3/optimize.py` is the
search side: numpy batched permanents, a smooth surrogate of the assignment-derived
metrics with an annealed ambiguity gate, scipy L-BFGS-B with random restarts, a "snap to
octant angles" step that hands exact-looking optima to the exact verifier, and a `runs`
row per optimizer invocation. Nothing on the search side is trusted; the float path
still ingests at HEURISTIC via the existing two-engine `ingest_scheme_artifact`.

**Tech Stack:** Python ≥3.11, `fractions` (exact side), numpy + scipy (search side;
scipy becomes a declared main dependency), pytest.

**Spec:** `docs/superpowers/specs/2026-07-06-empiricist-harness-design.md` §4.1
(CERTIFIED = general statement + model-independent machine-checkable certificate), §7
(certification-gated verifiers, two independent implementations for load-bearing
verifiers — here the exact evaluator is cross-checked against BOTH float engines in its
golden suite and fuzz tests), §8.5/§9 (deterministic tiers before model search: "do not
point SEARCH at what enumeration resolves"). Science context:
`docs/science/2026-07-20-p3-first-wave.md` (Task 3: the k=1 vector (1/16, 3/16, 9/16, 1)
whose mesh was not persisted) and `docs/science/2026-07-20-p3-certificates-and-proofs.md`.

## Global Constraints

- `domain/p3/exact.py` is stdlib-only (no numpy): it is a trust-boundary checker like
  `certificates/core.py`.
- The exact evaluator must reproduce `PermanentEngine`/`FockEngine` to 1e-12 on every
  supported scheme (fuzz test over random octant meshes + random ℚ(i,√2) ancillas).
- Exact-witness promotion is CERTIFIED only through `record_claimed_artifact` with the
  `p3_exact_witness` verifier's current stamp; float results stay HEURISTIC.
- No model calls anywhere in this plan. Optimizer runs record a `runs` row
  (`move="OPTIMIZE"`, seed, config hash) when given a ledger.
- Branch `feat/m21b-p3-deterministic-tier`, PR, squash-merge. Lint + fast suite green
  before every commit. No AI attribution in commits.

---

## File structure

| File | Responsibility |
|---|---|
| `src/empiricist/domain/p3/exact.py` (new) | `Q8` number field, `QR` (ℚ(√2) reals), octant trig tables, `snap_q8`/`snap_octant`, `exact_unitary`, `exact_permanent`, `exact_distributions`, `exact_report` (`ExactReport`), `ExactUnsupported`. |
| `src/empiricist/verifiers/p3_exact.py` (new) | `P3ExactVerifier` (name `p3_exact_witness`, version `1.0`, binary_hash over exact.py + scheme.py + fock.py + interferometer.py) and `qr_to_json`/`qr_from_json`. |
| `src/empiricist/verifiers/p3_exact_goldens.py` (new) | `P3_EXACT_GOLDEN_SUITE`, `p3_exact_suite_hash()`, `certify_p3_exact()`. |
| `src/empiricist/domain/p3/exact_ingest.py` (new) | `verify_and_ingest_exact_witness`, `ingest_exact_witness` → CERTIFIED. |
| `src/empiricist/domain/p3/optimize.py` (new) | `MeshTopology`, `params_to_scheme`, `FastEvaluator` (batched Ryser), `surrogate`, `optimize_scheme`, `snap_scheme`, `OptResult`. |
| `src/empiricist/cli.py` (modify) | `empiricist p3-optimize --run-dir R --k K --m M --target p_min|p_avg --restarts N --seed S --out FILE [--ingest]`. |
| `pyproject.toml` (modify) | add `scipy>=1.12` to main dependencies. |
| `tests/test_p3_exact.py`, `tests/test_p3_exact_verifier.py`, `tests/test_p3_exact_ingest.py`, `tests/test_p3_optimize.py` (new); `tests/test_cli.py` (extend) | Tests. |

---

### Task 1: ℚ(i, √2) arithmetic and the exact evaluator

**Files:**
- Create: `src/empiricist/domain/p3/exact.py`
- Test: `tests/test_p3_exact.py`

**Interfaces:**
- Consumes: `BellScheme`, `bell_input_states`, `BELL_LABELS` (`domain/p3/scheme.py`),
  `patterns`, `factorial_prod` (`domain/p3/fock.py`), `Mesh` (`domain/p3/interferometer.py`).
- Produces:
  ```python
  class ExactUnsupported(ValueError): ...           # angle/amplitude outside ℚ(i,√2)

  @dataclass(frozen=True)
  class QR:            # a + b*sqrt(2), a,b: Fraction   (the real subfield)
      a: Fraction; b: Fraction
      __add__/__sub__/__mul__/__neg__; is_zero(); is_rational(); to_float(); __lt__ via sign test
      @staticmethod  def from_rational(x) -> QR
  @dataclass(frozen=True)
  class Q8:            # re + i*im, re, im: QR
      re: QR; im: QR
      __add__/__sub__/__mul__/__neg__; conj(); abs2() -> QR; is_zero(); to_complex()
      @staticmethod  def from_rational(x) -> Q8
  OCTANT_COS: dict[int, QR]; OCTANT_SIN: dict[int, QR]        # keyed by k in 0..7 (angle = k*pi/4)
  def snap_octant(angle: float, tol: float = 1e-9) -> int        # k with angle ≡ k*pi/4, else ExactUnsupported
  def snap_qr(x: float, *, max_denom: int = 16, tol: float = 1e-9) -> QR   # a + b√2 with small denominators, else ExactUnsupported
  def snap_q8(z: complex, **kw) -> Q8
  def exact_unitary(mesh: Mesh) -> list[list[Q8]]              # same composition/convention as mesh_unitary
  def exact_permanent(rows: list[list[Q8]]) -> Q8
  def exact_scheme(scheme: BellScheme) -> tuple[list[list[Q8]], dict[tuple[int,...], Q8]]   # (U, exact ancilla)
  def exact_distributions(scheme: BellScheme) -> dict[str, dict[tuple[int, ...], QR]]
  @dataclass(frozen=True)
  class ExactReport:
      success: dict[str, QR]; p_min: QR; p_avg: QR; assignment: dict[tuple[int,...], str]
      all_identified: bool          # every label has success > 0 (exactly)
  def exact_report(scheme: BellScheme) -> ExactReport
  ```

- [ ] **Step 1: Write the failing tests** (`tests/test_p3_exact.py`)

```python
"""Exact ℚ(i,√2) evaluation of octant-angle Bell schemes (the trust side of M21b)."""
from __future__ import annotations

from fractions import Fraction
from math import pi, sqrt

import numpy as np
import pytest

from empiricist.domain.p3.engine_fock import FockEngine
from empiricist.domain.p3.engine_permanent import PermanentEngine
from empiricist.domain.p3.exact import (
    Q8, QR, ExactUnsupported, exact_distributions, exact_permanent, exact_report,
    exact_unitary, snap_octant, snap_q8, snap_qr,
)
from empiricist.domain.p3.interferometer import Mesh, mesh_unitary
from empiricist.domain.p3.known_schemes import grice_boosted_bsm, standard_bsm
from empiricist.domain.p3.scheme import BellScheme, evaluate_scheme

F = Fraction


def test_qr_and_q8_arithmetic_is_a_field():
    r2 = QR(F(0), F(1))
    assert r2 * r2 == QR(F(2), F(0))
    z = Q8(QR(F(1, 2), F(0)), QR(F(0), F(1, 2)))       # 1/2 + i*sqrt2/2
    assert z.abs2() == QR(F(1, 4) + F(1, 2), F(0))     # 1/4 + 2/4
    assert (z * z.conj()).im.is_zero()
    assert Q8.from_rational(3).to_complex() == 3 + 0j
    assert abs((z * z).to_complex() - (z.to_complex() ** 2)) < 1e-15


def test_snap_recognises_octant_angles_and_small_field_elements():
    assert snap_octant(pi / 4) == 1 and snap_octant(-pi / 2) == 6 and snap_octant(0.0) == 0
    with pytest.raises(ExactUnsupported):
        snap_octant(0.3)
    assert snap_qr(sqrt(2) / 2) == QR(F(0), F(1, 2))
    assert snap_qr(0.25) == QR(F(1, 4), F(0))
    assert snap_qr(1 + sqrt(2)) == QR(F(1), F(1))
    with pytest.raises(ExactUnsupported):
        snap_qr(0.123456789)
    assert snap_q8(complex(0, sqrt(2) / 2)) == Q8(QR(F(0), F(0)), QR(F(0), F(1, 2)))


def test_exact_unitary_matches_float_unitary_on_octant_meshes():
    rng = np.random.default_rng(3)
    for _ in range(20):
        m = int(rng.integers(2, 7))
        els = []
        for _ in range(int(rng.integers(1, 8))):
            i, j = sorted(rng.choice(m, size=2, replace=False).tolist())
            els.append(("bs", i, j, float(rng.integers(0, 8)) * pi / 4,
                        float(rng.integers(0, 8)) * pi / 4))
        els.append(("phase", int(rng.integers(0, m)), float(rng.integers(0, 8)) * pi / 4))
        mesh = Mesh(n_modes=m, elements=els)
        exact = exact_unitary(mesh)
        approx = mesh_unitary(mesh)
        for r in range(m):
            for c in range(m):
                assert abs(exact[r][c].to_complex() - approx[r, c]) < 1e-12


def test_exact_permanent_small_cases():
    one, two = Q8.from_rational(1), Q8.from_rational(2)
    assert exact_permanent([[one, two], [two, one]]) == Q8.from_rational(5)   # 1*1 + 2*2
    assert exact_permanent([]) == one


def test_standard_bsm_and_grice_vectors_are_exact():
    rep = exact_report(standard_bsm())
    assert [rep.success[b] for b in ("phi+", "phi-", "psi+", "psi-")] == [
        QR(F(0), F(0)), QR(F(0), F(0)), QR(F(1), F(0)), QR(F(1), F(0))]
    assert rep.p_avg == QR(F(1, 2), F(0)) and rep.p_min.is_zero() and not rep.all_identified
    g = exact_report(grice_boosted_bsm())
    assert g.success["phi+"] == QR(F(1, 2), F(0)) and g.success["psi-"] == QR(F(1), F(0))
    assert g.p_avg == QR(F(3, 4), F(0)) and g.p_min == QR(F(1, 2), F(0)) and g.all_identified


def test_exact_distributions_agree_with_both_engines_fuzz():
    rng = np.random.default_rng(11)
    field_vals = [0.0, 1.0, -1.0, 0.5, sqrt(2) / 2, -sqrt(2) / 2]
    for _ in range(25):
        k = int(rng.integers(0, 3))
        m = 4 if k == 0 else int(rng.integers(5, 8))
        els = []
        for _ in range(int(rng.integers(2, 12))):
            i, j = sorted(rng.choice(m, size=2, replace=False).tolist())
            els.append(("bs", i, j, float(rng.integers(0, 8)) * pi / 4,
                        float(rng.integers(0, 8)) * pi / 4))
        from empiricist.domain.p3.fock import patterns
        anc_pats = patterns(k, m - 4)
        raw = {p: complex(rng.choice(field_vals), rng.choice(field_vals)) for p in anc_pats}
        norm = sqrt(sum(abs(v) ** 2 for v in raw.values()))
        if norm == 0:
            continue
        # keep amplitudes in the field: only scale by 1, 1/sqrt2, 1/2, 1/(2 sqrt2)
        if abs(norm - 1) > 1e-12 and abs(norm - sqrt(2)) > 1e-12 and abs(norm - 2) > 1e-12:
            continue
        anc = {p: v / norm for p, v in raw.items() if v != 0}
        scheme = BellScheme(n_modes=m, n_ancilla_photons=k, ancilla=anc,
                            mesh=Mesh(n_modes=m, elements=els))
        exact = exact_distributions(scheme)
        for engine in (PermanentEngine(), FockEngine()):
            rep = evaluate_scheme(scheme, engine)
            for b, dist in rep.distributions.items():
                keys = set(dist) | set(exact[b])
                for key in keys:
                    assert abs(exact[b].get(key, QR(F(0), F(0))).to_float()
                               - dist.get(key, 0.0)) < 1e-12, (k, m, b, key)


def test_non_octant_angle_and_off_field_amplitude_are_unsupported():
    bad = BellScheme(n_modes=4, n_ancilla_photons=0, ancilla={},
                     mesh=Mesh(n_modes=4, elements=(("bs", 0, 2, 0.3, 0.0),)))
    with pytest.raises(ExactUnsupported):
        exact_report(bad)
    anc = BellScheme(n_modes=5, n_ancilla_photons=1, ancilla={(1,): complex(0.6, 0.8)},
                     mesh=Mesh(n_modes=5, elements=(("bs", 0, 4, pi / 4, 0.0),)))
    with pytest.raises(ExactUnsupported):
        exact_report(anc)


def test_three_photons_in_one_ancilla_mode_is_unsupported():
    # sqrt(3!) leaves ℚ(i,√2): refuse rather than approximate.
    s = BellScheme(n_modes=5, n_ancilla_photons=3, ancilla={(3,): 1.0 + 0j},
                   mesh=Mesh(n_modes=5, elements=(("bs", 0, 4, pi / 4, 0.0),)))
    with pytest.raises(ExactUnsupported):
        exact_report(s)
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_p3_exact.py -q` → ImportError.

- [ ] **Step 3: Implement `domain/p3/exact.py`**

```python
"""Exact evaluation of Bell-measurement schemes in the number field ℚ(i, √2).

Why: the float engines certify `leakage == 0.0` only up to the 1e-15 floor
(domain/p3/verify.py's epistemic boundary). A scheme whose beamsplitter angles
are multiples of π/4 and whose ancilla amplitudes lie in ℚ(i,√2) -- every
published scheme, and every "snapped" optimizer optimum -- has an EXACT success
vector in ℚ(√2). This module computes it with `fractions.Fraction` only (stdlib;
it is a trust-boundary checker like certificates/core.py and must never import
numpy) and derives the assignment with EXACT zero tests, so "all four Bell
states are identified" and "p_min = 1/16" become machine-checked statements.

Formula (identical to engine_permanent.py): for input |T> and output |S>,
    <S|U|T> = perm(U[S,T]) / sqrt(Π s_i! Π t_j!)
so  Pr[S|ψ] = |Σ_T a_T perm(U[S,T]) / sqrt(Π t_j!)|² / Π s_i!.
The 1/sqrt(Π t!) factor stays in the field iff Π t! ∈ {1, 2, 4, 8, ...} (each
t_j! must be a power of two: t_j ≤ 2). Higher single-mode ancilla occupations
raise ExactUnsupported instead of being approximated.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from fractions import Fraction
from math import pi

from .fock import factorial_prod, patterns
from .interferometer import Mesh
from .scheme import BELL_LABELS, BellScheme, bell_input_states


class ExactUnsupported(ValueError):
    """The scheme has a parameter outside ℚ(i, √2) (or an unsupported occupation)."""


@dataclass(frozen=True)
class QR:
    """a + b*sqrt(2) with rational a, b (the real subfield ℚ(√2))."""

    a: Fraction
    b: Fraction

    @staticmethod
    def from_rational(x) -> QR:
        return QR(Fraction(x), Fraction(0))

    def __add__(self, o: QR) -> QR:
        return QR(self.a + o.a, self.b + o.b)

    def __sub__(self, o: QR) -> QR:
        return QR(self.a - o.a, self.b - o.b)

    def __neg__(self) -> QR:
        return QR(-self.a, -self.b)

    def __mul__(self, o: QR) -> QR:
        return QR(self.a * o.a + 2 * self.b * o.b, self.a * o.b + self.b * o.a)

    def is_zero(self) -> bool:
        return self.a == 0 and self.b == 0

    def is_rational(self) -> bool:
        return self.b == 0

    def sign(self) -> int:
        """Exact sign of a + b√2 (compare a² vs 2b² with the right signs)."""
        a, b = self.a, self.b
        if b == 0:
            return (a > 0) - (a < 0)
        if a == 0:
            return (b > 0) - (b < 0)
        if (a > 0) == (b > 0):
            return 1 if a > 0 else -1
        # opposite signs: |a| vs |b|√2  <=>  a² vs 2b²
        if a * a > 2 * b * b:
            return 1 if a > 0 else -1
        if a * a < 2 * b * b:
            return 1 if b > 0 else -1
        return 0  # impossible for rationals unless both zero (√2 irrational)

    def __lt__(self, o: QR) -> bool:
        return (self - o).sign() < 0

    def to_float(self) -> float:
        return float(self.a) + float(self.b) * 2 ** 0.5


ZERO_QR = QR(Fraction(0), Fraction(0))
ONE_QR = QR(Fraction(1), Fraction(0))
HALF_SQRT2 = QR(Fraction(0), Fraction(1, 2))  # cos(pi/4) = sin(pi/4) = √2/2


@dataclass(frozen=True)
class Q8:
    """re + i*im with re, im ∈ ℚ(√2): the eighth cyclotomic field ℚ(ζ₈)."""

    re: QR
    im: QR

    @staticmethod
    def from_rational(x) -> Q8:
        return Q8(QR.from_rational(x), ZERO_QR)

    @staticmethod
    def from_qr(r: QR) -> Q8:
        return Q8(r, ZERO_QR)

    def __add__(self, o: Q8) -> Q8:
        return Q8(self.re + o.re, self.im + o.im)

    def __sub__(self, o: Q8) -> Q8:
        return Q8(self.re - o.re, self.im - o.im)

    def __neg__(self) -> Q8:
        return Q8(-self.re, -self.im)

    def __mul__(self, o: Q8) -> Q8:
        return Q8(self.re * o.re - self.im * o.im, self.re * o.im + self.im * o.re)

    def conj(self) -> Q8:
        return Q8(self.re, -self.im)

    def abs2(self) -> QR:
        return self.re * self.re + self.im * self.im

    def is_zero(self) -> bool:
        return self.re.is_zero() and self.im.is_zero()

    def to_complex(self) -> complex:
        return complex(self.re.to_float(), self.im.to_float())


ZERO_Q8 = Q8(ZERO_QR, ZERO_QR)
ONE_Q8 = Q8(ONE_QR, ZERO_QR)

# cos(k*pi/4), sin(k*pi/4) for k = 0..7, exactly.
OCTANT_COS: dict[int, QR] = {
    0: ONE_QR, 1: HALF_SQRT2, 2: ZERO_QR, 3: -HALF_SQRT2,
    4: -ONE_QR, 5: -HALF_SQRT2, 6: ZERO_QR, 7: HALF_SQRT2,
}
OCTANT_SIN: dict[int, QR] = {
    0: ZERO_QR, 1: HALF_SQRT2, 2: ONE_QR, 3: HALF_SQRT2,
    4: ZERO_QR, 5: -HALF_SQRT2, 6: -ONE_QR, 7: -HALF_SQRT2,
}


def snap_octant(angle: float, tol: float = 1e-9) -> int:
    k = round(angle / (pi / 4))
    if abs(angle - k * pi / 4) > tol:
        raise ExactUnsupported(f"angle {angle!r} is not a multiple of pi/4")
    return k % 8


def snap_qr(x: float, *, max_denom: int = 16, tol: float = 1e-9) -> QR:
    """Recognise x = a + b√2 with |a|,|b| having denominators <= max_denom."""
    r2 = 2 ** 0.5
    for qb in range(1, max_denom + 1):
        for pb in range(-4 * qb, 4 * qb + 1):
            b = Fraction(pb, qb)
            rest = x - float(b) * r2
            for qa in range(1, max_denom + 1):
                pa = round(rest * qa)
                if abs(rest - pa / qa) <= tol:
                    return QR(Fraction(pa, qa), b)
    raise ExactUnsupported(f"{x!r} is not a small element of Q(sqrt2)")


def snap_q8(z: complex, **kw) -> Q8:
    return Q8(snap_qr(z.real, **kw), snap_qr(z.imag, **kw))


def _octant_phase(k: int) -> Q8:
    return Q8(OCTANT_COS[k], OCTANT_SIN[k])


def _element_unitary(n: int, el) -> list[list[Q8]]:
    u = [[ONE_Q8 if r == c else ZERO_Q8 for c in range(n)] for r in range(n)]
    kind = el[0]
    if kind == "bs":
        _, i, j, theta, phi = el
        kt, kp = snap_octant(theta), snap_octant(phi)
        c, s = Q8.from_qr(OCTANT_COS[kt]), Q8.from_qr(OCTANT_SIN[kt])
        e_pos, e_neg = _octant_phase(kp), _octant_phase((-kp) % 8)
        u[i][i] = c
        u[j][i] = e_pos * s
        u[i][j] = -(e_neg * s)
        u[j][j] = c
    elif kind == "phase":
        _, i, alpha = el[0], el[1], el[2]
        u[int(i)][int(i)] = _octant_phase(snap_octant(float(alpha)))
    else:  # pragma: no cover - Mesh validates kinds
        raise ExactUnsupported(f"unknown element kind {kind!r}")
    return u


def _matmul(a: list[list[Q8]], b: list[list[Q8]]) -> list[list[Q8]]:
    n = len(a)
    out = [[ZERO_Q8 for _ in range(n)] for _ in range(n)]
    for r in range(n):
        for c in range(n):
            acc = ZERO_Q8
            for k in range(n):
                if not a[r][k].is_zero() and not b[k][c].is_zero():
                    acc = acc + a[r][k] * b[k][c]
            out[r][c] = acc
    return out


def exact_unitary(mesh: Mesh) -> list[list[Q8]]:
    """Composition IN ORDER, identical to `interferometer.mesh_unitary`."""
    n = mesh.n_modes
    u = [[ONE_Q8 if r == c else ZERO_Q8 for c in range(n)] for r in range(n)]
    for el in mesh.elements:
        u = _matmul(_element_unitary(n, el), u)
    return u


def exact_permanent(rows: list[list[Q8]]) -> Q8:
    n = len(rows)
    if n == 0:
        return ONE_Q8
    total = ZERO_Q8
    for perm in itertools.permutations(range(n)):
        term = ONE_Q8
        for r, c in enumerate(perm):
            term = term * rows[r][c]
            if term.is_zero():
                break
        total = total + term
    return total


def _inverse_sqrt_factorials(pattern: tuple[int, ...]) -> Q8:
    """1/sqrt(Π t_j!) as a field element; t_j ≤ 2 only (1/√2 ∈ ℚ(√2))."""
    factor = ONE_Q8
    for t in pattern:
        if t <= 1:
            continue
        if t == 2:
            factor = factor * Q8.from_qr(HALF_SQRT2)  # 1/√2 = √2/2
        else:
            raise ExactUnsupported(
                f"occupation {t} in an input pattern: sqrt({t}!) leaves Q(i, sqrt2)"
            )
    return factor


def exact_scheme(scheme: BellScheme) -> tuple[list[list[Q8]], dict[tuple[int, ...], Q8]]:
    scheme.validate()
    u = exact_unitary(scheme.mesh)
    anc = {p: snap_q8(complex(a)) for p, a in scheme.ancilla.items()}
    return u, anc


def _exact_bell_inputs(n_modes: int, anc: dict[tuple[int, ...], Q8]):
    """Mirror `scheme.bell_input_states` with exact 1/√2 amplitudes."""
    r = Q8.from_qr(HALF_SQRT2)
    anc_terms = anc if anc else {(): ONE_Q8}
    bell4 = {
        "phi+": {(1, 0, 1, 0): r, (0, 1, 0, 1): r},
        "phi-": {(1, 0, 1, 0): r, (0, 1, 0, 1): -r},
        "psi+": {(1, 0, 0, 1): r, (0, 1, 1, 0): r},
        "psi-": {(1, 0, 0, 1): r, (0, 1, 1, 0): -r},
    }
    out = {}
    for label, b4 in bell4.items():
        state = {}
        for p4, a4 in b4.items():
            for pa, aa in anc_terms.items():
                full = (*p4, *pa)
                if len(full) != n_modes:
                    raise ValueError("ancilla pattern length must be n_modes - 4")
                state[full] = a4 * aa
        out[label] = state
    return out


def exact_distributions(scheme: BellScheme) -> dict[str, dict[tuple[int, ...], QR]]:
    u, anc = exact_scheme(scheme)
    inputs = _exact_bell_inputs(scheme.n_modes, anc)
    n_photons = scheme.n_ancilla_photons + 2
    out: dict[str, dict[tuple[int, ...], QR]] = {}
    for label, state in inputs.items():
        dist: dict[tuple[int, ...], QR] = {}
        prepared = []
        for t, a_t in state.items():
            if a_t.is_zero():
                continue
            cols = [j for j, tj in enumerate(t) for _ in range(tj)]
            prepared.append((cols, a_t * _inverse_sqrt_factorials(t)))
        for s in patterns(n_photons, scheme.n_modes):
            rows_idx = [i for i, si in enumerate(s) for _ in range(si)]
            amp = ZERO_Q8
            for cols, coeff in prepared:
                sub = [[u[r][c] for c in cols] for r in rows_idx]
                amp = amp + coeff * exact_permanent(sub)
            if amp.is_zero():
                continue
            p = amp.abs2()
            inv = Fraction(1, factorial_prod(s))
            dist[s] = QR(p.a * inv, p.b * inv)
        out[label] = dist
    return out


@dataclass(frozen=True)
class ExactReport:
    success: dict[str, QR]
    p_min: QR
    p_avg: QR
    assignment: dict[tuple[int, ...], str]
    all_identified: bool


def exact_report(scheme: BellScheme) -> ExactReport:
    """Exact assignment: pattern -> B iff Pr[s|B] != 0 and every other Pr is 0."""
    dists = exact_distributions(scheme)
    all_patterns = set().union(*(dists[b] for b in BELL_LABELS))
    assignment: dict[tuple[int, ...], str] = {}
    success = {b: ZERO_QR for b in BELL_LABELS}
    for pat in all_patterns:
        supported = [b for b in BELL_LABELS if pat in dists[b]]
        if len(supported) == 1:
            assignment[pat] = supported[0]
            success[supported[0]] = success[supported[0]] + dists[supported[0]][pat]
    p_min = min(success.values(), key=lambda q: (q.sign(), q.to_float()))
    total = ZERO_QR
    for v in success.values():
        total = total + v
    p_avg = QR(total.a / 4, total.b / 4)
    # exact min: sort with the exact comparator
    ordered = sorted(success.values(), key=lambda q: q.to_float())
    p_min = ordered[0]
    for cand in ordered[1:]:
        if cand < p_min:
            p_min = cand
    return ExactReport(
        success=success, p_min=p_min, p_avg=p_avg, assignment=assignment,
        all_identified=all(v.sign() > 0 for v in success.values()),
    )
```

(The `bell_input_states` import is intentionally unused-by-name; drop it if ruff
complains — `_exact_bell_inputs` mirrors it and a test pins agreement with the engines.)

- [ ] **Step 4: Run tests, lint, commit**

```bash
uv run pytest tests/test_p3_exact.py -q && uv run ruff check src tests
git add src/empiricist/domain/p3/exact.py tests/test_p3_exact.py
git commit -m "Add exact Q(i,sqrt2) evaluation of octant-angle P3 schemes"
```

---

### Task 2: `P3ExactVerifier`, its golden suite, and CERTIFIED witness ingest

**Files:**
- Create: `src/empiricist/verifiers/p3_exact.py`, `src/empiricist/verifiers/p3_exact_goldens.py`, `src/empiricist/domain/p3/exact_ingest.py`
- Test: `tests/test_p3_exact_verifier.py`, `tests/test_p3_exact_ingest.py`

**Interfaces:**
- Consumes: Task 1; `screen_scheme` (`search/p3_screen.py`); `certify_with_suite`;
  `record_claimed_artifact`; `P3_SCHEME_PROBLEM_VERSION` pattern from `domain/p3/ingest.py`.
- Produces:
  ```python
  # verifiers/p3_exact.py
  def qr_to_json(q: QR) -> list[str]            # ["a", "b"] Fraction strings, value a + b*sqrt2
  def qr_from_json(v) -> QR                      # ValueError on shape
  class P3ExactVerifier:
      name = "p3_exact_witness"; version = "1.0"
      binary_hash -> str  # blake3 over domain/p3/{exact,scheme,fock,interferometer}.py + this file
      def verify(self, scheme: BellScheme, *, claimed_success: dict[str, QR],
                 require_all_identified: bool = False) -> VerifierResult
      # PASS iff exact success vector == claimed_success (all four labels) and, when
      # required, all four are > 0. FAIL on mismatch; FAIL with details["unsupported"]
      # on ExactUnsupported; never raises.
  # verifiers/p3_exact_goldens.py
  P3_EXACT_GOLDEN_SUITE: list[tuple[BellScheme, dict, Verdict]]
  def p3_exact_suite_hash() -> str
  def certify_p3_exact(ledger, verifier) -> Certification
  # domain/p3/exact_ingest.py
  P3_EXACT_WITNESS_PROBLEM_VERSION = "p3-exact-witness-v1"
  def verify_and_ingest_exact_witness(ledger, store, *, scheme_json: dict, claimed_success: dict[str, list[str]],
        require_all_identified: bool, title: str, run_id=None) -> tuple[VerifierResult, Artifact | None]
  def ingest_exact_witness(...) -> Artifact      # CERTIFIED, kind "certificate"
  ```

Golden suite cases: (standard BSM, claim (0,0,1,1)) → PASS; (Grice, (1/2,1/2,1,1)) →
PASS; (Grice, (1/2,1/2,1,1), require_all_identified=True) → PASS; (standard BSM,
(0,0,1,1), require_all_identified=True) → FAIL; (standard BSM claiming (0,0,1/2,1)) → FAIL;
(a θ=0.3 mesh, any claim) → FAIL (unsupported); (Grice claiming p_min side wrong: phi+ =
1/4) → FAIL. Claim statement for the ingest:
"There is an unambiguous passive linear-optical Bell-measurement scheme with k={k}
ancilla photon(s) on m={m} modes whose exact per-Bell-state success vector is
(phi+, phi-, psi+, psi-) = ({v}); hence p*_min({k}) >= {pmin} and p*_avg({k}) >= {pavg}
(exact evaluation in Q(i, sqrt2))." — with `family=f"k{k}_m{m}_exact_witness"`,
`metric="exact_success_vector"`, `scope={"k","m","success","p_min","p_avg","all_identified"}`.
Artifact content = canonical JSON of `{"scheme": scheme_json, "claimed_success": ...,
"require_all_identified": ...}`.

Tests mirror `tests/test_certificates_ingest.py` (certified fixture; PASS ingests at
CERTIFIED with a clean audit; wrong vector → nothing recorded; uncertified → fails
closed; idempotent; the float `ingest_scheme_artifact` of the same scheme stays
HEURISTIC and is a DIFFERENT artifact id).

- [ ] Steps: failing tests → implement → `uv run pytest tests/test_p3_exact_verifier.py tests/test_p3_exact_ingest.py -q` → lint → commit
  `"Add the exact-witness verifier and CERTIFIED ingest for P3 schemes"`.

---

### Task 3: The numerical optimizer (deterministic tier)

**Files:**
- Create: `src/empiricist/domain/p3/optimize.py`
- Modify: `pyproject.toml` (`scipy>=1.12` in `dependencies`), `src/empiricist/cli.py`
- Test: `tests/test_p3_optimize.py`, `tests/test_cli.py`

**Interfaces:**
```python
@dataclass(frozen=True)
class MeshTopology:                      # Clements-style universal rectangular mesh
    n_modes: int
    pairs: tuple[tuple[int, int], ...]   # bs (i, j) in order, m layers of nearest-neighbour pairs
    @staticmethod def universal(m: int) -> MeshTopology
    @property def n_params(self) -> int   # 2*len(pairs) + m  (theta, phi per bs; final phases)

def ancilla_basis(k: int, m: int) -> tuple[tuple[int, ...], ...]        # patterns(k, m-4)
def params_to_scheme(k: int, m: int, x: np.ndarray, topo: MeshTopology) -> BellScheme
    # x = [mesh params..., ancilla re/im pairs...]; ancilla normalised; k=0 -> vacuum pattern
class FastEvaluator:
    def __init__(self, k: int, m: int): ...  # precomputes output patterns, row index arrays, Bell input columns
    def probabilities(self, unitary: np.ndarray, ancilla: np.ndarray) -> np.ndarray   # (n_patterns, 4)
def batched_permanents(mats: np.ndarray) -> np.ndarray                # (N, n, n) -> (N,) Ryser
def surrogate(P: np.ndarray, *, target: str, tau: float) -> float   # higher is better
def snap_scheme(scheme: BellScheme) -> BellScheme | None            # octant angles + field ancilla, else None
@dataclass(frozen=True)
class OptResult:
    scheme_json: dict; report: SchemeReport; snapped_json: dict | None; snapped_report: SchemeReport | None
    restart: int; objective: float
def optimize_scheme(k: int, m: int, *, target: str, restarts: int = 20, seed: int = 0,
                    max_iter: int = 300, ledger: Ledger | None = None,
                    tau_schedule=(0.3, 0.1, 0.03, 0.01)) -> list[OptResult]   # sorted best-first by exact-assignment metric
```

Surrogate (documented in the module): with `P[s,B] = Pr[s|B]`, `w(s) = argmax_B P[s,B]`,
`r(s) = (Σ_B P[s,B] − max_B P[s,B]) / max_B P[s,B]` (relative leak) and gate
`g(s) = exp(−r(s)/τ)`: `S_B = Σ_{s: w(s)=B} P[s,B]·g(s)`; `p_avg` target maximises
`mean_B S_B`, `p_min` target maximises `softmin_τ(S_B) = −τ·log Σ_B exp(−S_B/τ)`.
Anneal τ over `tau_schedule`, warm-starting each stage from the previous optimum
(`scipy.optimize.minimize(method="L-BFGS-B")` on `−surrogate`, numerical gradient).
After the last stage: build the scheme, evaluate with `verify_scheme_agreed` (both
engines) for the reported metric, then `snap_scheme` and re-evaluate; keep the snapped
version when its metric is ≥ the continuous one − 1e-9. Sanity expectations pinned by
tests: k=0, m=4 → best p_avg = 1/2 exactly after snapping and p_min = 0; k=1, m=5,
target p_min → best p_min ≥ 1/16 within a handful of restarts (this is the lost wave-1
design; the test asserts ≥ 0.06 with 20 restarts, seed 0); every `FastEvaluator`
probability row agrees with `PermanentEngine` to 1e-10 on random schemes.

CLI: `empiricist p3-optimize --run-dir R --k K --m M --target {p_min,p_avg} [--restarts N]
[--seed S] [--max-iter I] --out FILE [--ingest]` — writes all results as JSON (schemes +
reports + snapped), records the `runs` row, and with `--ingest` ingests the best float
scheme at HEURISTIC (`ingest_scheme_artifact`, claims = achieved − 1e-9) and, when a
snapped scheme exists, the exact witness at CERTIFIED (`ingest_exact_witness`, claim =
its exact vector, `require_all_identified = all four > 0`).

- [ ] Steps: failing tests (evaluator agreement fuzz; surrogate monotonicity: a
  leakage-free scheme scores exactly its metric at every τ; `snap_scheme` on Grice returns
  Grice; the k=0 and k=1 sanity runs above; CLI writes the JSON and exits 0) → implement
  → `uv run pytest tests/test_p3_optimize.py tests/test_cli.py -q` → lint → commit
  `"Add the P3 deterministic tier: mesh/ancilla optimizer with exact snapping"`.

---

### Task 4: Campaign actions (after the PR merges; no code)

- [ ] **4.1** `empiricist p3-optimize --run-dir runs/p3-campaign --k 1 --m 5 --target p_min --restarts 200 --seed 1 --out runs/p3-campaign/opt-k1-m5-pmin.json --ingest`, then m=6, m=7; then `--target p_avg` for the same; then k=0/m=4 and k=2/m=8 as sanity rows. Expect: the 1/16 design recovered at m=5; report the best exact vectors per (k, m, target).
- [ ] **4.2** Certify + ingest: the best exact k=1 witness at CERTIFIED (`p*_min(1) ≥ …`, all four identified). `empiricist audit` must stay clean; `status` should show CERTIFIED ≥ 2.
- [ ] **4.3** Science note `docs/science/2026-09-xx-p3-min-metric-landscape.md`: the metric clarification, per-(k,m) landscape tables (float, HEURISTIC) and exact witnesses (CERTIFIED), the k=0 theorem, the k=2 randomization gap. Feed the strategist targets (M21c) from what plateaus.

## Self-review

- Spec: CERTIFIED via cert-gated transaction (Task 2); two-engine cross-check as the
  exact evaluator's warrant (Task 1 fuzz + Task 2 goldens); deterministic tier before
  model search (Task 3); provenance row per optimizer run (Task 3).
- Types: `QR`/`Q8` names consistent across tasks; `claimed_success` is `dict[str, QR]`
  at the verifier and `dict[str, list[str]]` in JSON; `OptResult.report` is the two-engine
  `SchemeReport`.
- Scope guard: k ≤ 2 for exactness (occupation ≤ 2 per ancilla mode); the optimizer's
  fast path handles n = k+2 ≤ 4 photons via batched Ryser.

## Amendment (2026-09-05, during execution)

The first k=1 optimum (p_min = 1/6, vector (1, 1/6, 1/2, 2/9)) showed that the exact
structure lives in the overall unitary, not in mesh angles: gauge-fixed, its entries have
|U|² ∈ {1/4, 1/6, 1/3, 0} and phases on the π/6 lattice (a tritter coupling the ancilla
into three modes), which needs √3 and √6. Tasks 1–3 were therefore built as:

- `domain/p3/exact.py`: the multiquadratic field ℚ(i)(√d …) (`Alg`, exact zero test via
  linear independence of √ of distinct square-free integers; exact signs by rational
  interval arithmetic), roots of unity on the π/12 lattice, `ExactWitness` = an m × n_in
  isometry over the photon-carrying input modes + exact ancilla, `from_mesh` for lattice
  meshes, `snap_isometry` for numeric matrices.
- `verifiers/p3_exact.py` certifies witness JSON (the artifact bytes) directly.
- `domain/p3/optimize.py`: `to_exact_witness` = absorb a single ancilla photon into one
  column, gauge-fix rows / qubit pairs / the ancilla column onto the lattice (numeric
  search), snap, require an exact isometry whose exact vector reproduces the engines'.
- The p_min surrogate uses a log-product shaping during annealing (the soft minimum is
  flat at 0 whenever a Bell state is unidentified) and anneals τ down to 1e-5, at which
  point the gate is effectively an exact-unambiguity indicator.

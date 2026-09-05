"""Exact evaluation of Bell-measurement schemes over Q(i)(sqrt d_1, sqrt d_2, ...).

Why: the float engines certify `leakage == 0.0` only up to the 1e-15 floor
(domain/p3/verify.py's epistemic boundary). The schemes that matter -- every
published one, and every optimiser optimum with a rational success vector --
have interferometer entries whose squared moduli are small rationals and whose
phases lie on the pi/12 lattice (the structure the optimiser finds is in the
overall unitary, NOT in individual mesh angles). Such entries live in a
multiquadratic extension Q(i)(sqrt 2, sqrt 3, sqrt 5, ...), and in that field
the success vector is EXACT: "all four Bell states are identified" and
"p_min = 1/6" become machine-checked statements.

This module is stdlib-only (`fractions`, `math`): it is a trust-boundary
checker like certificates/core.py and must never import numpy.

Representation. `Alg` is an element of Q(i)(sqrt d : d square-free) stored as
{radicand d -> Gaussian-rational coefficient (re, im)}; products of radicals
reduce by extracting square parts, and the square roots of distinct square-free
integers are linearly independent over Q(i) (Besicovitch), so "every
coefficient is zero" is an EXACT zero test. Signs of real elements are decided
by rational interval arithmetic with rigorous rational bounds on each sqrt d.

The physics (identical to engine_permanent.py): for input |T> and output |S>,
    <S|V|T> = perm(V[S,T]) / sqrt(prod s_i! prod t_j!)
so  Pr[S|psi] = |sum_T a_T perm(V[S,T]) / sqrt(prod t_j!)|^2 / prod s_i!,
where V is the m x n_in ISOMETRY made of the input columns that carry photons
(V^dagger V = I exactly -- any isometry extends to a unitary, and the
probabilities depend on these columns only). Ancilla occupations t_j <= 2 keep
1/sqrt(t_j!) in the field; higher ones raise ExactUnsupported.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from fractions import Fraction
from math import pi
from typing import TYPE_CHECKING

from .fock import factorial_prod, patterns

if TYPE_CHECKING:  # the Mesh type only; interferometer.py pulls numpy in at runtime
    from .interferometer import Mesh

# Kept equal to scheme.BELL_LABELS by a test; scheme.py imports numpy transitively
# and this module must stay stdlib-only.
BELL_LABELS = ("phi+", "phi-", "psi+", "psi-")

Gauss = tuple[Fraction, Fraction]  # re + i*im


class ExactUnsupported(ValueError):
    """A parameter lies outside the supported field (or an unsupported occupation)."""


# Compute caps for witness JSON (the exact analogue of search/p3_screen.py's caps,
# kept equal by a test): the number of output patterns is C(m+k+1, k+2) and every
# one costs exact permanents, so an unbounded witness is a DoS on a checker whose
# contract is "never a crash".
MAX_EXACT_MODES = 12
MAX_EXACT_PHOTONS = 4       # ancilla photons k
MAX_RADICAND = 10**6        # `_sqfree` trial-divides; keep it bounded


# ---------------------------------------------------------------------------
# Square-free bookkeeping
# ---------------------------------------------------------------------------


def _sqfree(n: int) -> tuple[int, int]:
    """n = s^2 * r with r square-free; returns (s, r). n >= 1."""
    if n < 1:
        raise ValueError("radicand must be >= 1")
    s, r, p = 1, 1, 2
    while p * p <= n:
        while n % (p * p) == 0:
            n //= p * p
            s *= p
        if n % p == 0:
            n //= p
            r *= p
        p += 1
    return s, r * n


# ---------------------------------------------------------------------------
# The field element
# ---------------------------------------------------------------------------


def _gmul(x: Gauss, y: Gauss) -> Gauss:
    return (x[0] * y[0] - x[1] * y[1], x[0] * y[1] + x[1] * y[0])


@dataclass(frozen=True)
class Alg:
    """sum_d (re_d + i im_d) sqrt(d) over square-free d (d = 1 is the rational part)."""

    terms: dict[int, Gauss] = field(default_factory=dict)

    # -- constructors -------------------------------------------------------
    @staticmethod
    def rational(x, y=0) -> Alg:
        c = (Fraction(x), Fraction(y))
        return Alg({1: c}) if c != (0, 0) else Alg({})

    @staticmethod
    def sqrt_rational(x) -> Alg:
        """sqrt(x) for a rational x >= 0, exactly: n/d -> sqrt(n d)/d."""
        x = Fraction(x)
        if x < 0:
            raise ExactUnsupported("sqrt of a negative rational")
        if x == 0:
            return Alg({})
        s, r = _sqfree(x.numerator * x.denominator)
        return Alg({r: (Fraction(s, x.denominator), Fraction(0))})

    @staticmethod
    def root_of_unity_24(k: int) -> Alg:
        """exp(i k pi / 12), exactly (cos/sin of multiples of 15 degrees)."""
        k %= 24
        # cos, sin for k = 0..6 (0..90 degrees) in the field.
        s2, s3, s6 = Alg.sqrt_rational(2), Alg.sqrt_rational(3), Alg.sqrt_rational(6)
        quarter = Alg.rational(Fraction(1, 4))
        half = Alg.rational(Fraction(1, 2))
        table = {
            0: (Alg.rational(1), Alg({})),
            1: ((s6 + s2) * quarter, (s6 - s2) * quarter),
            2: (s3 * half, half),
            3: (s2 * half, s2 * half),
            4: (half, s3 * half),
            5: ((s6 - s2) * quarter, (s6 + s2) * quarter),
            6: (Alg({}), Alg.rational(1)),
        }
        if k <= 6:
            c, s = table[k]
        elif k <= 12:
            c0, s0 = table[12 - k]
            c, s = -c0, s0
        elif k <= 18:
            c0, s0 = table[k - 12]
            c, s = -c0, -s0
        else:
            c0, s0 = table[24 - k]
            c, s = c0, -s0
        return c + s * Alg.rational(0, 1)

    @staticmethod
    def polar(modulus2, k: int) -> Alg:
        """sqrt(modulus2) * exp(i k pi / 12)."""
        return Alg.sqrt_rational(modulus2) * Alg.root_of_unity_24(k)

    # -- arithmetic ---------------------------------------------------------
    def __add__(self, o: Alg) -> Alg:
        out = dict(self.terms)
        for d, (a, b) in o.terms.items():
            x, y = out.get(d, (Fraction(0), Fraction(0)))
            c = (x + a, y + b)
            if c == (0, 0):
                out.pop(d, None)
            else:
                out[d] = c
        return Alg(out)

    def __neg__(self) -> Alg:
        return Alg({d: (-a, -b) for d, (a, b) in self.terms.items()})

    def __sub__(self, o: Alg) -> Alg:
        return self + (-o)

    def __mul__(self, o: Alg) -> Alg:
        out: dict[int, Gauss] = {}
        for d1, c1 in self.terms.items():
            for d2, c2 in o.terms.items():
                s, r = _sqfree(d1 * d2)
                a, b = _gmul(c1, c2)
                x, y = out.get(r, (Fraction(0), Fraction(0)))
                c = (x + a * s, y + b * s)
                if c == (0, 0):
                    out.pop(r, None)
                else:
                    out[r] = c
        return Alg(out)

    def conj(self) -> Alg:
        return Alg({d: (a, -b) for d, (a, b) in self.terms.items()})

    def abs2(self) -> Alg:
        return self * self.conj()

    def scale(self, c) -> Alg:
        c = Fraction(c)
        if c == 0:
            return Alg({})
        return Alg({d: (a * c, b * c) for d, (a, b) in self.terms.items()})

    # -- predicates ---------------------------------------------------------
    def is_zero(self) -> bool:
        return not self.terms

    def is_real(self) -> bool:
        return all(b == 0 for _, b in self.terms.values())

    def is_rational(self) -> bool:
        return set(self.terms) <= {1} and self.is_real()

    def to_complex(self) -> complex:
        z = 0j
        for d, (a, b) in self.terms.items():
            z += complex(a, b) * math.sqrt(d)
        return z

    def to_float(self) -> float:
        if not self.is_real():
            raise ValueError("not a real element")
        return self.to_complex().real

    def sign(self) -> int:
        """Exact sign of a REAL element (rational interval arithmetic)."""
        if not self.is_real():
            raise ValueError("sign of a non-real element")
        if self.is_zero():
            return 0
        for digits in (40, 80, 160):
            scale = 10**digits
            lo = hi = Fraction(0)
            for d, (a, _) in self.terms.items():
                root_lo = Fraction(math.isqrt(d * scale * scale), scale)
                root_hi = root_lo + Fraction(1, scale)
                if a >= 0:
                    lo += a * root_lo
                    hi += a * root_hi
                else:
                    lo += a * root_hi
                    hi += a * root_lo
            if lo > 0:
                return 1
            if hi < 0:
                return -1
        raise ArithmeticError("could not decide the sign of a non-zero algebraic number")

    def __lt__(self, o: Alg) -> bool:
        return (self - o).sign() < 0

    def __le__(self, o: Alg) -> bool:
        return (self - o).sign() <= 0


ZERO = Alg({})
ONE = Alg.rational(1)
INV_SQRT2 = Alg.sqrt_rational(Fraction(1, 2))


def alg_str(x: Alg) -> str:
    """Human-readable canonical form, e.g. '1/6', '1/4 + 1/4*sqrt2', '(1/2 + 1/2 i)*sqrt3'."""
    if x.is_zero():
        return "0"
    parts = []
    for d in sorted(x.terms):
        a, b = x.terms[d]
        coeff = str(a) if b == 0 else (f"{b} i" if a == 0 else f"({a} + {b} i)")
        parts.append(coeff if d == 1 else f"{coeff}*sqrt{d}")
    return " + ".join(parts)


def alg_to_json(x: Alg) -> list[list]:
    """[[d, "re", "im"], ...] sorted by radicand; [] is zero."""
    return [[d, str(a), str(b)] for d, (a, b) in sorted(x.terms.items())]


def alg_from_json(v) -> Alg:
    """Inverse of `alg_to_json`; also accepts a bare rational string/int.
    Radicands must be square-free positive integers. ValueError otherwise."""
    try:
        if isinstance(v, (str, int)):
            return Alg.rational(Fraction(v))
        out = ZERO
        for d, a, b in v:
            d = int(d)
            if d < 1 or d > MAX_RADICAND:
                raise ValueError(f"radicand {d} outside [1, {MAX_RADICAND}]")
            if _sqfree(d) != (1, d):
                raise ValueError(f"radicand {d} is not square-free")
            coeff = (Fraction(a), Fraction(b))
            if coeff != (0, 0):
                out = out + Alg({d: coeff})
        return out
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise ValueError(f"not an algebraic number: {v!r} ({exc})") from exc


# ---------------------------------------------------------------------------
# Snapping floats into the field (stdlib; the search side calls these)
# ---------------------------------------------------------------------------


def snap_lattice_phase(z: complex, *, lattice: int = 24, tol: float = 1e-7) -> int:
    """k with arg(z) = 2 pi k / lattice within tol (radians), else ExactUnsupported."""
    ang = math.atan2(z.imag, z.real)
    step = 2 * pi / lattice
    k = round(ang / step)
    if abs(ang - k * step) > tol:
        raise ExactUnsupported(f"phase {ang / pi:.6f} pi is not on the 2pi/{lattice} lattice")
    return k % lattice


def snap_rational(x: float, *, max_denom: int = 64, tol: float = 1e-9) -> Fraction:
    f = Fraction(x).limit_denominator(max_denom)
    if abs(float(f) - x) > tol:
        raise ExactUnsupported(f"{x!r} is not a rational with denominator <= {max_denom}")
    return f


def snap_complex(z: complex, *, max_denom: int = 64, tol: float = 1e-7) -> Alg:
    """z -> sqrt(|z|^2) exp(i k pi/12) with |z|^2 a small rational. An entry with
    |z|^2 <= tol is an exact zero (the same tolerance `snap_rational` uses, so the
    zero threshold is not silently looser than the documented one)."""
    z = complex(z)
    r2 = abs(z) ** 2
    if r2 <= tol:
        return ZERO
    modulus2 = snap_rational(r2, max_denom=max_denom, tol=tol)
    if modulus2 == 0:
        return ZERO
    return Alg.polar(modulus2, snap_lattice_phase(z, tol=tol))


def snap_octant(angle: float, tol: float = 1e-9) -> int:
    """k in 0..23 with angle = k*pi/12 within tol, else ExactUnsupported."""
    angle = float(angle)
    k = round(angle / (pi / 12))
    if abs(angle - k * pi / 12) > tol:
        raise ExactUnsupported(f"angle {angle!r} is not a multiple of pi/12")
    return k % 24


# ---------------------------------------------------------------------------
# Exact isometries: from a lattice mesh, or snapped from a numeric matrix
# ---------------------------------------------------------------------------


def _identity(n: int) -> list[list[Alg]]:
    return [[ONE if r == c else ZERO for c in range(n)] for r in range(n)]


def _element_unitary(n: int, el) -> list[list[Alg]]:
    """Mirror of interferometer._element_unitary for angles on the pi/12 lattice."""
    u = _identity(n)
    if el[0] == "bs":
        _, i, j, theta, phi = el
        i, j = int(i), int(j)
        kt, kp = snap_octant(theta), snap_octant(phi)
        ct, st = Alg.root_of_unity_24(kt), Alg.root_of_unity_24(kt)
        c = Alg({d: (a, Fraction(0)) for d, (a, _) in ct.terms.items() if a != 0})  # cos
        s = Alg({d: (b, Fraction(0)) for d, (_, b) in st.terms.items() if b != 0})  # sin
        u[i][i] = c
        u[j][i] = Alg.root_of_unity_24(kp) * s
        u[i][j] = -(Alg.root_of_unity_24(-kp) * s)
        u[j][j] = c
    elif el[0] == "phase":
        i = int(el[1])
        u[i][i] = Alg.root_of_unity_24(snap_octant(el[2]))
    else:  # pragma: no cover - Mesh validates kinds
        raise ExactUnsupported(f"unknown mesh element kind {el[0]!r}")
    return u


def _matmul(a: list[list[Alg]], b: list[list[Alg]]) -> list[list[Alg]]:
    n, p, q = len(a), len(b), len(b[0]) if b else 0
    out = [[ZERO for _ in range(q)] for _ in range(n)]
    for r in range(n):
        for c in range(q):
            acc = ZERO
            for k in range(p):
                x, y = a[r][k], b[k][c]
                if x.is_zero() or y.is_zero():
                    continue
                acc = acc + x * y
            out[r][c] = acc
    return out


def exact_unitary(mesh: Mesh) -> list[list[Alg]]:
    """The full m x m unitary of a mesh whose angles all lie on the pi/12 lattice
    (composition IN ORDER, identical to interferometer.mesh_unitary)."""
    u = _identity(mesh.n_modes)
    for el in mesh.elements:
        u = _matmul(_element_unitary(mesh.n_modes, el), u)
    return u


def is_exact_isometry(v: list[list[Alg]]) -> bool:
    """V^dagger V == I exactly (columns orthonormal)."""
    if not v:
        return False
    n_in = len(v[0])
    for i in range(n_in):
        for j in range(n_in):
            acc = ZERO
            for row in v:
                if row[i].is_zero() or row[j].is_zero():
                    continue
                acc = acc + row[i].conj() * row[j]
            if acc != (ONE if i == j else ZERO):
                return False
    return True


def snap_isometry(
    columns: list[list[complex]], *, max_denom: int = 64, tol: float = 1e-7
) -> list[list[Alg]]:
    """Snap an m x n numeric matrix (rows of complex numbers) entry-wise onto
    the field and check it is EXACTLY an isometry. Gauge fixing (which phases
    are free) is the caller's job; this function only snaps and checks. Raises
    ExactUnsupported when an entry is off-lattice or the result is not an
    isometry."""
    v = [[snap_complex(z, max_denom=max_denom, tol=tol) for z in row] for row in columns]
    if not is_exact_isometry(v):
        raise ExactUnsupported("snapped matrix is not an exact isometry")
    return v


# ---------------------------------------------------------------------------
# Exact witnesses and their evaluation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExactWitness:
    """An exact scheme: `isometry` is m x n_in (rows = output modes, columns =
    the input modes that carry photons: 0..3 the dual-rail Bell pair, 4.. the
    ancilla modes), `ancilla` maps k-photon patterns on the n_in - 4 ancilla
    modes to exact amplitudes ({} for k = 0)."""

    n_modes: int
    n_ancilla_photons: int
    isometry: tuple[tuple[Alg, ...], ...]
    ancilla: dict[tuple[int, ...], Alg]

    @property
    def n_in(self) -> int:
        return len(self.isometry[0]) if self.isometry else 0

    def validate(self) -> None:
        if self.n_modes < 4 or self.n_in < 4:
            raise ValueError("a Bell scheme needs at least the 4 dual-rail modes")
        if self.n_modes > MAX_EXACT_MODES:
            raise ValueError(
                f"n_modes {self.n_modes} exceeds the exact-checker cap {MAX_EXACT_MODES}"
            )
        if not (0 <= self.n_ancilla_photons <= MAX_EXACT_PHOTONS):
            raise ValueError(
                f"n_ancilla_photons {self.n_ancilla_photons} outside [0, {MAX_EXACT_PHOTONS}]"
            )
        if len(self.isometry) != self.n_modes or any(len(r) != self.n_in for r in self.isometry):
            raise ValueError("isometry shape must be n_modes x n_in")
        if self.n_in > self.n_modes:
            raise ValueError("an isometry cannot have more input than output modes")
        n_anc_modes = self.n_in - 4
        if self.n_ancilla_photons == 0:
            if self.ancilla:
                raise ValueError("k = 0 must have an empty ancilla")
            if n_anc_modes != 0:
                raise ValueError("k = 0 witnesses carry no ancilla columns")
        else:
            if not self.ancilla:
                raise ValueError("k > 0 requires an ancilla state")
            norm = ZERO
            for pat, amp in self.ancilla.items():
                if len(pat) != n_anc_modes or any(p < 0 for p in pat):
                    raise ValueError("ancilla pattern on wrong number of modes")
                if sum(pat) != self.n_ancilla_photons:
                    raise ValueError("ancilla photon number mismatch")
                norm = norm + amp.abs2()
            if norm != ONE:
                raise ValueError("ancilla not exactly normalised")
        if not is_exact_isometry([list(r) for r in self.isometry]):
            raise ValueError("isometry columns are not exactly orthonormal")

    @staticmethod
    def from_mesh(scheme, *, max_denom: int = 64) -> ExactWitness:
        """From a BellScheme whose mesh angles are on the pi/12 lattice and
        whose ancilla amplitudes snap into the field (the full unitary's
        used columns become the isometry)."""
        scheme.validate()
        u = exact_unitary(scheme.mesh)
        n_in = scheme.n_modes  # all columns kept: ancilla may span every extra mode
        iso = tuple(tuple(row[:n_in]) for row in u)
        anc = {tuple(p): snap_complex(complex(a), max_denom=max_denom)
               for p, a in scheme.ancilla.items()}
        if scheme.n_modes == 4 or scheme.n_ancilla_photons == 0:
            iso = tuple(tuple(row[:4]) for row in u)
            anc = {}
        w = ExactWitness(scheme.n_modes, scheme.n_ancilla_photons, iso, anc)
        w.validate()
        return w


def witness_to_json(w: ExactWitness) -> dict:
    return {
        "n_modes": w.n_modes,
        "n_ancilla_photons": w.n_ancilla_photons,
        "isometry": [[alg_to_json(x) for x in row] for row in w.isometry],
        "ancilla": [[list(p), alg_to_json(a)] for p, a in sorted(w.ancilla.items())],
    }


def witness_from_json(data) -> ExactWitness:
    """Inverse of `witness_to_json`; validates. ValueError on any defect."""
    try:
        iso = tuple(tuple(alg_from_json(x) for x in row) for row in data["isometry"])
        anc = {tuple(int(i) for i in p): alg_from_json(a) for p, a in data["ancilla"]}
        w = ExactWitness(int(data["n_modes"]), int(data["n_ancilla_photons"]), iso, anc)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"malformed exact witness: {type(exc).__name__}: {exc}") from exc
    w.validate()
    return w


def _inverse_sqrt_factorials(pattern: tuple[int, ...]) -> Alg:
    factor = ONE
    for t in pattern:
        if t <= 1:
            continue
        if t == 2:
            factor = factor * INV_SQRT2
        else:
            raise ExactUnsupported(
                f"occupation {t} in an input pattern: sqrt({t}!) is not supported"
            )
    return factor


def _bell_inputs(w: ExactWitness) -> dict[str, dict[tuple[int, ...], Alg]]:
    """Mirror of scheme.bell_input_states over the witness's n_in input modes."""
    r = INV_SQRT2
    anc_terms = w.ancilla if w.ancilla else {(): ONE}
    bell4 = {
        "phi+": {(1, 0, 1, 0): r, (0, 1, 0, 1): r},
        "phi-": {(1, 0, 1, 0): r, (0, 1, 0, 1): -r},
        "psi+": {(1, 0, 0, 1): r, (0, 1, 1, 0): r},
        "psi-": {(1, 0, 0, 1): r, (0, 1, 1, 0): -r},
    }
    out: dict[str, dict[tuple[int, ...], Alg]] = {}
    for label, b4 in bell4.items():
        state: dict[tuple[int, ...], Alg] = {}
        for p4, a4 in b4.items():
            for pa, aa in anc_terms.items():
                state[(*p4, *pa)] = a4 * aa
        out[label] = state
    return out


def exact_permanent(rows: list[list[Alg]]) -> Alg:
    n = len(rows)
    if n == 0:
        return ONE
    total = ZERO
    for perm in itertools.permutations(range(n)):
        term = ONE
        for r, c in enumerate(perm):
            term = term * rows[r][c]
            if term.is_zero():
                break
        total = total + term
    return total


def exact_distributions(w: ExactWitness) -> dict[str, dict[tuple[int, ...], Alg]]:
    """Pr[s|B] (real, exact) for every output pattern s with NON-ZERO probability."""
    w.validate()
    inputs = _bell_inputs(w)
    n_photons = w.n_ancilla_photons + 2
    out: dict[str, dict[tuple[int, ...], Alg]] = {}
    for label, state in inputs.items():
        prepared: list[tuple[list[int], Alg]] = []
        for t, a_t in state.items():
            if a_t.is_zero():
                continue
            cols = [j for j, tj in enumerate(t) for _ in range(tj)]
            prepared.append((cols, a_t * _inverse_sqrt_factorials(t)))
        dist: dict[tuple[int, ...], Alg] = {}
        for s in patterns(n_photons, w.n_modes):
            rows_idx = [i for i, si in enumerate(s) for _ in range(si)]
            amp = ZERO
            for cols, coeff in prepared:
                sub = [[w.isometry[r][c] for c in cols] for r in rows_idx]
                amp = amp + coeff * exact_permanent(sub)
            if amp.is_zero():
                continue
            dist[s] = amp.abs2().scale(Fraction(1, factorial_prod(s)))
        out[label] = dist
    return out


@dataclass(frozen=True)
class ExactReport:
    success: dict[str, Alg]                  # per Bell label, exact and real
    p_min: Alg
    p_avg: Alg
    assignment: dict[tuple[int, ...], str]   # identifying patterns only (exact)
    all_identified: bool                     # every label has success > 0


def exact_report(w: ExactWitness) -> ExactReport:
    """Exact assignment: pattern s identifies B iff Pr[s|B] != 0 and every other
    Pr[s|B'] is exactly 0 -- no tolerance anywhere."""
    dists = exact_distributions(w)
    all_patterns: set[tuple[int, ...]] = set()
    for b in BELL_LABELS:
        all_patterns |= set(dists[b])
    assignment: dict[tuple[int, ...], str] = {}
    success = dict.fromkeys(BELL_LABELS, ZERO)
    for pat in sorted(all_patterns):
        supported = [b for b in BELL_LABELS if pat in dists[b]]
        if len(supported) == 1:
            winner = supported[0]
            assignment[pat] = winner
            success[winner] = success[winner] + dists[winner][pat]
    values = list(success.values())
    p_min = values[0]
    for v in values[1:]:
        if v < p_min:
            p_min = v
    total = ZERO
    for v in values:
        total = total + v
    return ExactReport(
        success=success,
        p_min=p_min,
        p_avg=total.scale(Fraction(1, 4)),
        assignment=assignment,
        all_identified=all(v.sign() > 0 for v in values),
    )

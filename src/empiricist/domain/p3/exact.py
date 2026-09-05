"""Exact evaluation of Bell-measurement schemes in the number field Q(i, sqrt2).

Why: the float engines certify `leakage == 0.0` only up to the 1e-15 floor
(domain/p3/verify.py's epistemic boundary). A scheme whose beamsplitter angles
are multiples of pi/4 and whose ancilla amplitudes lie in Q(i, sqrt2) -- every
published scheme, and every "snapped" optimizer optimum -- has an EXACT success
vector in Q(sqrt2). This module computes it with `fractions.Fraction` only
(stdlib; it is a trust-boundary checker like certificates/core.py and must never
import numpy) and derives the assignment with EXACT zero tests, so "all four
Bell states are identified" and "p_min = 1/16" become machine-checked statements.

Formula (identical to engine_permanent.py): for input |T> and output |S>,
    <S|U|T> = perm(U[S,T]) / sqrt(prod s_i! * prod t_j!)
so  Pr[S|psi] = |sum_T a_T perm(U[S,T]) / sqrt(prod t_j!)|^2 / prod s_i!.
The 1/sqrt(prod t!) factor stays in the field iff every t_j! is a power of two
(t_j <= 2). Higher single-mode ancilla occupations raise ExactUnsupported
instead of being approximated. Everything else -- unitary composition order,
the beamsplitter convention, the dual-rail Bell inputs, the pattern order --
mirrors interferometer.py / scheme.py / fock.py exactly, and a fuzz test pins
agreement with BOTH float engines to 1e-12.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from fractions import Fraction
from math import pi

from .fock import factorial_prod, patterns
from .interferometer import Mesh
from .scheme import BELL_LABELS, BellScheme


class ExactUnsupported(ValueError):
    """The scheme has a parameter outside Q(i, sqrt2) (or an unsupported occupation)."""


@dataclass(frozen=True)
class QR:
    """a + b*sqrt(2) with rational a, b (the real subfield Q(sqrt2))."""

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

    def scale(self, c: Fraction) -> QR:
        return QR(self.a * c, self.b * c)

    def is_zero(self) -> bool:
        return self.a == 0 and self.b == 0

    def is_rational(self) -> bool:
        return self.b == 0

    def sign(self) -> int:
        """Exact sign of a + b*sqrt2."""
        a, b = self.a, self.b
        if b == 0:
            return (a > 0) - (a < 0)
        if a == 0:
            return (b > 0) - (b < 0)
        if (a > 0) == (b > 0):
            return 1 if a > 0 else -1
        # Opposite signs: the larger magnitude wins; |a| vs |b|*sqrt2 <=> a^2 vs 2 b^2
        # (never equal for rationals with b != 0 since sqrt2 is irrational).
        return (1 if a > 0 else -1) if a * a > 2 * b * b else (1 if b > 0 else -1)

    def __lt__(self, o: QR) -> bool:
        return (self - o).sign() < 0

    def __le__(self, o: QR) -> bool:
        return (self - o).sign() <= 0

    def to_float(self) -> float:
        return float(self.a) + float(self.b) * 2**0.5


ZERO_QR = QR(Fraction(0), Fraction(0))
ONE_QR = QR(Fraction(1), Fraction(0))
HALF_SQRT2 = QR(Fraction(0), Fraction(1, 2))  # cos(pi/4) = sin(pi/4) = 1/sqrt2


@dataclass(frozen=True)
class Q8:
    """re + i*im with re, im in Q(sqrt2): the eighth cyclotomic field Q(zeta_8)."""

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
    """k in 0..7 with angle = k*pi/4 (mod 2*pi) within tol, else ExactUnsupported."""
    angle = float(angle)
    k = round(angle / (pi / 4))
    if abs(angle - k * pi / 4) > tol:
        raise ExactUnsupported(f"angle {angle!r} is not a multiple of pi/4")
    return k % 8


def snap_qr(x: float, *, max_denom: int = 16, tol: float = 1e-9) -> QR:
    """Recognise x = a + b*sqrt2 with a, b of denominator <= max_denom and
    |b| <= 4 (every published scheme amplitude is far inside this box)."""
    x = float(x)
    r2 = 2**0.5
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
    z = complex(z)
    return Q8(snap_qr(z.real, **kw), snap_qr(z.imag, **kw))


def _octant_phase(k: int) -> Q8:
    """exp(i*k*pi/4)."""
    return Q8(OCTANT_COS[k % 8], OCTANT_SIN[k % 8])


def _identity(n: int) -> list[list[Q8]]:
    return [[ONE_Q8 if r == c else ZERO_Q8 for c in range(n)] for r in range(n)]


def _element_unitary(n: int, el) -> list[list[Q8]]:
    """Mirror of interferometer._element_unitary in the field."""
    u = _identity(n)
    kind = el[0]
    if kind == "bs":
        _, i, j, theta, phi = el
        i, j = int(i), int(j)
        kt, kp = snap_octant(theta), snap_octant(phi)
        c, s = Q8.from_qr(OCTANT_COS[kt]), Q8.from_qr(OCTANT_SIN[kt])
        u[i][i] = c
        u[j][i] = _octant_phase(kp) * s
        u[i][j] = -(_octant_phase(-kp) * s)
        u[j][j] = c
    elif kind == "phase":
        i, alpha = int(el[1]), el[2]
        u[i][i] = _octant_phase(snap_octant(alpha))
    else:  # pragma: no cover - Mesh validates kinds
        raise ExactUnsupported(f"unknown mesh element kind {kind!r}")
    return u


def _matmul(a: list[list[Q8]], b: list[list[Q8]]) -> list[list[Q8]]:
    n = len(a)
    out = _identity(n)
    for r in range(n):
        row = a[r]
        for c in range(n):
            acc = ZERO_Q8
            for k in range(n):
                x, y = row[k], b[k][c]
                if x.is_zero() or y.is_zero():
                    continue
                acc = acc + x * y
            out[r][c] = acc
    return out


def exact_unitary(mesh: Mesh) -> list[list[Q8]]:
    """Composition IN ORDER, identical to `interferometer.mesh_unitary`
    (columns are images of input modes)."""
    u = _identity(mesh.n_modes)
    for el in mesh.elements:
        u = _matmul(_element_unitary(mesh.n_modes, el), u)
    return u


def exact_permanent(rows: list[list[Q8]]) -> Q8:
    """Permanent by explicit expansion (n <= 4 here: at most k+2 <= 4 photons)."""
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
    """1/sqrt(prod t_j!) as a field element; each t_j <= 2 (1/sqrt2 in Q(sqrt2))."""
    factor = ONE_Q8
    for t in pattern:
        if t <= 1:
            continue
        if t == 2:
            factor = factor * Q8.from_qr(HALF_SQRT2)
        else:
            raise ExactUnsupported(
                f"occupation {t} in an input pattern: sqrt({t}!) leaves Q(i, sqrt2)"
            )
    return factor


def exact_scheme(scheme: BellScheme) -> tuple[list[list[Q8]], dict[tuple[int, ...], Q8]]:
    """The exact mode unitary and the exact ancilla amplitudes of `scheme`.
    Raises ExactUnsupported (a ValueError) when either leaves the field, and
    ValueError (via validate) for a malformed scheme."""
    scheme.validate()
    u = exact_unitary(scheme.mesh)
    anc = {tuple(p): snap_q8(complex(a)) for p, a in scheme.ancilla.items()}
    return u, anc


def _exact_bell_inputs(
    n_modes: int, anc: dict[tuple[int, ...], Q8]
) -> dict[str, dict[tuple[int, ...], Q8]]:
    """Mirror of scheme.bell_input_states with exact 1/sqrt2 amplitudes."""
    r = Q8.from_qr(HALF_SQRT2)
    anc_terms = anc if anc else {(): ONE_Q8}
    bell4 = {
        "phi+": {(1, 0, 1, 0): r, (0, 1, 0, 1): r},
        "phi-": {(1, 0, 1, 0): r, (0, 1, 0, 1): -r},
        "psi+": {(1, 0, 0, 1): r, (0, 1, 1, 0): r},
        "psi-": {(1, 0, 0, 1): r, (0, 1, 1, 0): -r},
    }
    out: dict[str, dict[tuple[int, ...], Q8]] = {}
    for label, b4 in bell4.items():
        state: dict[tuple[int, ...], Q8] = {}
        for p4, a4 in b4.items():
            for pa, aa in anc_terms.items():
                full = (*p4, *pa)
                if len(full) != n_modes:
                    raise ValueError("ancilla pattern length must be n_modes - 4")
                state[full] = a4 * aa
        out[label] = state
    return out


def exact_distributions(scheme: BellScheme) -> dict[str, dict[tuple[int, ...], QR]]:
    """Pr[s|B] for every output pattern s with a NON-ZERO exact probability."""
    u, anc = exact_scheme(scheme)
    inputs = _exact_bell_inputs(scheme.n_modes, anc)
    n_photons = scheme.n_ancilla_photons + 2
    out: dict[str, dict[tuple[int, ...], QR]] = {}
    for label, state in inputs.items():
        prepared: list[tuple[list[int], Q8]] = []
        for t, a_t in state.items():
            if a_t.is_zero():
                continue
            cols = [j for j, tj in enumerate(t) for _ in range(tj)]
            prepared.append((cols, a_t * _inverse_sqrt_factorials(t)))
        dist: dict[tuple[int, ...], QR] = {}
        for s in patterns(n_photons, scheme.n_modes):
            rows_idx = [i for i, si in enumerate(s) for _ in range(si)]
            amp = ZERO_Q8
            for cols, coeff in prepared:
                sub = [[u[r][c] for c in cols] for r in rows_idx]
                amp = amp + coeff * exact_permanent(sub)
            if amp.is_zero():
                continue
            dist[s] = amp.abs2().scale(Fraction(1, factorial_prod(s)))
        out[label] = dist
    return out


@dataclass(frozen=True)
class ExactReport:
    success: dict[str, QR]                   # per Bell label, exact
    p_min: QR
    p_avg: QR
    assignment: dict[tuple[int, ...], str]   # identifying patterns only (exact)
    all_identified: bool                     # every label has success > 0


def exact_report(scheme: BellScheme) -> ExactReport:
    """Exact assignment: pattern s identifies B iff Pr[s|B] != 0 and every other
    Pr[s|B'] is exactly 0 -- no tolerance anywhere."""
    dists = exact_distributions(scheme)
    all_patterns: set[tuple[int, ...]] = set()
    for b in BELL_LABELS:
        all_patterns |= set(dists[b])
    assignment: dict[tuple[int, ...], str] = {}
    success = dict.fromkeys(BELL_LABELS, ZERO_QR)
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
    total = ZERO_QR
    for v in values:
        total = total + v
    return ExactReport(
        success=success,
        p_min=p_min,
        p_avg=total.scale(Fraction(1, 4)),
        assignment=assignment,
        all_identified=all(v.sign() > 0 for v in values),
    )

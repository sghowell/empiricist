"""The exact SOS certificate checker -- M20c's trust boundary.

This module is the ONLY thing the ledger trusts about a claimed SOS
(sum-of-squares) upper-bound certificate, and it is the intended future
Lean-verification target (its arithmetic is rational linear algebra, nothing
more). Finding a certificate may use arbitrary heavy numerical machinery
(cvxpy/SCS, floats, whatever) -- that lives in `certificates/solve.py` and is
never trusted. *Checking* a certificate happens here, in exact
`fractions.Fraction` arithmetic only: this module is stdlib-only (no numpy,
no solver imports of any kind) and MUST NOT be relaxed to import either.

Exactness guarantee: every arithmetic step in `check_certificate` -- the
polynomial identity expansion and the rational LDL^T factorization -- is
performed in `Fraction`, never `float`. There is no rounding anywhere on this
path; a PASS is a mathematically exact proof, not a numerical approximation.

Never-raise contract: `check_certificate` NEVER raises, for any input
(including malformed shapes, wrong types, or `None`). Malformed certificates
are reported as `CheckResult(ok=False, failure="shape", ...)`; this mirrors
the P3 verify discipline that the checker is a total function from "anything
claiming to be a certificate" to a verdict, never a crash.

What a PASS certifies: `check_certificate(cert).ok` being `True` means
exactly

    objective(v) <= bound   for every point v with constraints[i](v) == 0 for all i,

proved via the identity

    bound - objective - sum_i(multipliers[i] * constraints[i]) == b^T Q b

(an exact polynomial identity, where `b` is `gram_basis` and `Q` is `gram`)
together with `Q` being positive semidefinite (so `b^T Q b >= 0` for every
real assignment to the variables). This is a SOUND bound ON THE VARIETY
`{constraints = 0}` -- it says NOTHING about points where some constraint is
nonzero. Whether the `constraints` polynomials actually vanish on the
INTENDED variety (e.g. the unitarity rows of an interferometer, or whatever
domain fact the caller cares about) is entirely the CALLER's responsibility;
this checker only verifies the algebra of the certificate itself, never the
domain meaning of the constraint polynomials.

Poly representation (must match `domain/p3/poly.py` exactly -- see that
module's docstring for the shared convention; the two modules keep
independent copies of the same arithmetic by design for this milestone, see
the M20c Task 2 plan note, and are not unified here):

    Monomial = tuple[int, ...]      # SORTED tuple of variable indices;
                                     # repeated indices are powers; () is the
                                     # constant monomial 1.
    Poly = dict[Monomial, Fraction]  # canonical form: zero coefficients are
                                     # dropped, and every key is sorted.

`poly_mul` produces monomials by concatenating two operand monomials, so the
result is RE-SORTED (`tuple(sorted(a + b))`) before being used as a dict key
-- never assume multiplication preserves an input's sortedness "for free";
the helpers below always re-sort.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

Monomial = tuple[int, ...]
Poly = dict[Monomial, Fraction]


# ---------------------------------------------------------------------------
# Shared polynomial arithmetic (dict-based, exact, canonical).
# ---------------------------------------------------------------------------


def _mono_mul(a: Monomial, b: Monomial) -> Monomial:
    """Monomial product: concatenate variable-index tuples and RE-SORT --
    multiplication does not preserve a sorted-tuple key on its own."""
    return tuple(sorted(a + b))


def poly_add(p: Poly, q: Poly) -> Poly:
    """`p + q`, canonical (zero coefficients dropped)."""
    out = dict(p)
    for mono, coef in q.items():
        c = out.get(mono, Fraction(0)) + coef
        if c:
            out[mono] = c
        else:
            out.pop(mono, None)
    return out


def poly_scale(p: Poly, c: Fraction) -> Poly:
    """`c * p`, canonical."""
    if not c:
        return {}
    return {mono: c * coef for mono, coef in p.items() if c * coef}


def poly_sub(p: Poly, q: Poly) -> Poly:
    """`p - q`, canonical."""
    return poly_add(p, poly_scale(q, Fraction(-1)))


def poly_mul(p: Poly, q: Poly) -> Poly:
    """`p * q`. Every product monomial is re-sorted (see `_mono_mul`);
    canonical (zero coefficients dropped)."""
    out: Poly = {}
    for ma, ca in p.items():
        for mb, cb in q.items():
            mono = _mono_mul(ma, mb)
            out[mono] = out.get(mono, Fraction(0)) + ca * cb
    return {mono: c for mono, c in out.items() if c}


def poly_eq(p: Poly, q: Poly) -> bool:
    """Exact polynomial equality: every monomial's coefficient agrees
    (absent keys are implicitly zero -- works whether or not either side is
    in perfectly dropped-zero canonical form)."""
    for mono in set(p) | set(q):
        if p.get(mono, Fraction(0)) != q.get(mono, Fraction(0)):
            return False
    return True


# ---------------------------------------------------------------------------
# The certificate data model.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SOSCertificate:
    """A claimed SOS certificate for `objective <= bound` on the variety
    `{constraints[i] == 0 for all i}`. See the module docstring for the
    precise semantics of a PASS. All numeric fields are expected to be
    `Fraction` (or plain `int`, which `check_certificate` coerces); floats
    are rejected by the checker as a shape error, never silently accepted."""

    statement: str
    variables: tuple[str, ...]
    objective: Poly
    bound: Fraction
    constraints: tuple[Poly, ...]
    multipliers: tuple[Poly, ...]
    gram_basis: tuple[Monomial, ...]
    gram: tuple[tuple[Fraction, ...], ...]


@dataclass(frozen=True)
class CheckResult:
    """The checker's verdict. `failure` is `""` on success, else one of
    `"shape"`, `"identity"`, `"psd"` naming which of the three checks failed
    (see `check_certificate`). `detail` is a free-text explanation for
    humans; never parsed by callers."""

    ok: bool
    failure: str
    detail: str = ""


# ---------------------------------------------------------------------------
# The checker.
# ---------------------------------------------------------------------------


def _to_fraction(x: Any) -> Fraction:
    """Coerce a certificate scalar to `Fraction`. Plain `int` is accepted
    (coerced); `Fraction` passes through; anything else (notably `float`,
    which cannot represent exact rationals in general and is explicitly
    disallowed in certificates) raises `TypeError` -- callers of this
    helper are always inside the shape-validation try/except."""
    if isinstance(x, Fraction):
        return x
    if isinstance(x, int) and not isinstance(x, bool):
        return Fraction(x)
    raise TypeError(f"certificate coefficients must be Fraction (or int), got {x!r}")


def _coerce_monomial(mono: Any) -> Monomial:
    if not isinstance(mono, tuple) or not all(
        isinstance(v, int) and not isinstance(v, bool) for v in mono
    ):
        raise TypeError(f"monomial must be a tuple of ints, got {mono!r}")
    return tuple(sorted(mono))


def _coerce_poly(p: Any) -> Poly:
    if not isinstance(p, dict):
        raise TypeError(f"polynomial must be a dict, got {type(p).__name__}")
    out: Poly = {}
    for mono, coef in p.items():
        canon = _coerce_monomial(mono)
        c = out.get(canon, Fraction(0)) + _to_fraction(coef)
        if c:
            out[canon] = c
        else:
            out.pop(canon, None)
    return out


def _prepare(cert: Any) -> tuple[Poly, Fraction, tuple[Poly, ...], tuple[Poly, ...],
                                  tuple[Monomial, ...], tuple[tuple[Fraction, ...], ...]]:
    """Validate + coerce every field of `cert` needed downstream. Raises
    (any exception type) on any shape problem; the sole caller,
    `check_certificate`, wraps this in a blanket try/except and reports
    `failure="shape"` -- this function is intentionally allowed to raise,
    it is never called from anywhere else."""
    if not isinstance(cert, SOSCertificate):
        raise TypeError(f"expected SOSCertificate, got {type(cert).__name__}")

    if len(cert.multipliers) != len(cert.constraints):
        raise ValueError(
            f"multipliers length {len(cert.multipliers)} != "
            f"constraints length {len(cert.constraints)}"
        )

    n = len(cert.gram_basis)
    if len(cert.gram) != n:
        raise ValueError(f"gram has {len(cert.gram)} rows, expected {n} (== len(gram_basis))")
    for row in cert.gram:
        if len(row) != n:
            raise ValueError(f"gram row has {len(row)} entries, expected {n}")

    gram = tuple(tuple(_to_fraction(v) for v in row) for row in cert.gram)
    for a in range(n):
        for b in range(n):
            if gram[a][b] != gram[b][a]:
                raise ValueError(f"gram is not symmetric at ({a}, {b})")

    gram_basis = tuple(_coerce_monomial(m) for m in cert.gram_basis)
    objective = _coerce_poly(cert.objective)
    bound = _to_fraction(cert.bound)
    constraints = tuple(_coerce_poly(c) for c in cert.constraints)
    multipliers = tuple(_coerce_poly(m) for m in cert.multipliers)

    return objective, bound, constraints, multipliers, gram_basis, gram


def _is_psd(gram: tuple[tuple[Fraction, ...], ...]) -> bool:
    """Rational LDL^T with symmetric pivoting, exact throughout. At each
    step, pivot on the LARGEST remaining diagonal entry (by `Fraction`
    comparison):

    - a negative pivot means the matrix is not PSD -> False.
    - a zero pivot is only consistent with PSD-ness if the ENTIRE remaining
      row/column for that index is also zero (a PSD matrix cannot have a
      zero diagonal entry with a nonzero off-diagonal in its row); if so,
      that index contributes nothing and is simply dropped (semidefinite
      certificates -- zero pivots with zero rows -- PASS).
    - otherwise, eliminate that index via the ordinary symmetric Schur
      complement and recurse on what remains.

    An empty matrix is vacuously PSD.
    """
    n = len(gram)
    mat = [list(row) for row in gram]
    active = list(range(n))
    while active:
        pivot = max(active, key=lambda i: mat[i][i])
        pivot_val = mat[pivot][pivot]
        if pivot_val < 0:
            return False
        if pivot_val == 0:
            if any(mat[pivot][j] != 0 for j in active):
                return False
            active.remove(pivot)
            continue
        remaining = [i for i in active if i != pivot]
        for i in remaining:
            factor = mat[i][pivot] / pivot_val
            for j in remaining:
                mat[i][j] = mat[i][j] - factor * mat[pivot][j]
        active = remaining
    return True


def check_certificate(cert: SOSCertificate) -> CheckResult:
    """Verify `cert` exactly. Never raises -- see the module docstring's
    never-raise contract. Three checks, in order:

    1. SHAPE: `cert` is a well-formed `SOSCertificate` with matching
       `multipliers`/`constraints` lengths, a square symmetric `gram` of
       dimension `len(gram_basis)`, and every coefficient an exact `Fraction`
       or `int` (floats -- and any other type, or any malformed `cert` at
       all, including `None` -- are rejected here). Any exception raised
       while checking this is caught and reported as `failure="shape"`.
    2. IDENTITY: `bound - objective - sum_i(multipliers[i] * constraints[i])`
       equals `b^T Q b` (`b = gram_basis`, `Q = gram`) as polynomials,
       expanded exactly and compared with `poly_eq`.
    3. PSD: `gram` is positive semidefinite via exact rational LDL^T
       (`_is_psd`); semidefinite (zero pivots with zero rows) PASSES.
    """
    try:
        objective, bound, constraints, multipliers, gram_basis, gram = _prepare(cert)

        n = len(gram_basis)

        combined_constraints: Poly = {}
        for mult, constr in zip(multipliers, constraints, strict=True):
            combined_constraints = poly_add(combined_constraints, poly_mul(mult, constr))

        lhs = poly_sub(poly_sub({(): bound} if bound else {}, objective), combined_constraints)

        rhs: Poly = {}
        for a in range(n):
            for b in range(n):
                coef = gram[a][b]
                if not coef:
                    continue
                mono = _mono_mul(gram_basis[a], gram_basis[b])
                c = rhs.get(mono, Fraction(0)) + coef
                if c:
                    rhs[mono] = c
                else:
                    rhs.pop(mono, None)
    except Exception as exc:  # noqa: BLE001 - never raise is the contract
        return CheckResult(False, "shape", f"{type(exc).__name__}: {exc}")

    if not poly_eq(lhs, rhs):
        return CheckResult(
            False,
            "identity",
            "bound - objective - sum(multipliers * constraints) != b^T Q b",
        )

    if not _is_psd(gram):
        return CheckResult(False, "psd", "gram is not positive semidefinite (rational LDL^T)")

    return CheckResult(True, "", "")

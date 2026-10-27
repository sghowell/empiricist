"""Exact checker for the P3 photon-number moment bound at a fixed (k, m) -- M27b.

THE STATEMENT a PASS supports (k in {0, 1}; for k = 1 the ancilla photon enters input mode 4,
which at m = 5 is the only ancilla mode; at m >= 6 any single-photon ancilla state is rotated
into mode 4 by a unitary on the ancilla modes that is absorbed into U):

    for every U in U(m) and every unambiguous assignment of the (k+2)-photon detection
    patterns, the average success (1/4) sum_B p_B is at most (k + 1)/(k + 2).

WHAT IS CHECKED (exact arithmetic over Q, no floats):

(a) LEMMA. The payload's `lemma_certificate` passes `core.check_certificate` AND equals the
    canonical one-body USD lemma (`p3_moment.one_body_usd_certificate`) in its variables,
    objective, bound and constraints -- so what is certified is THE lemma:
        Bell-diagonal Lambda <= s_A |a><a| (x) I + s_B I (x) |b><b| + c I
        (unit a, b; any real s_A, s_B, c)  ==>  tr Lambda <= s_A + s_B + 4c.
(b) MOMENT IDENTITY, for every output mode i and Bell pair (B, B'), two polynomial
    identities in the 2m^2 real variables of U (`poly.var_x`/`var_y`):
    (I1)  sum_n n_i A_B(n) conj(A_B'(n)) = sum_{j,l} U_ij conj(U_il) H_jl^{BB'}(U^dag U)
          for EVERY complex matrix U, where A_B(n) = <n|out_B> is `poly.bell_amp_poly`
          and H_jl^{BB'}(G) = <a_l in_B'| Gamma(G) |a_j in_B> is spelled out with
          permanents: H = (1/2) sum_{e,e'} s_e s'_e' [j in T_e][l in T'_e']
          perm(G[T'_e' - l, T_e - j]) (T_e the 0/1 occupations of the two Fock components);
    (I2)  sum_{j,l} U_ij conj(U_il) H_jl^{BB'}(I) = <B'| O_A(i) (x) I + I (x) O_B(i) + c_i I |B>
          with (O_A)_pq = conj(U_ip) U_iq on qubit A's rails, O_B likewise on qubit B's,
          c_i = |U_i4|^2 (k = 1) or 0 (k = 0).
(c) BOUND. `claimed_p_avg_bound` (an exact rational string) is >= (k + 1)/(k + 2).

WHY (a)-(c) IMPLY THE STATEMENT (the derivation this checker encodes; the science note
`docs/science/2026-10-26-p3-moment-bounds.md` has it in full). On U(m), U^dag U = I, so (I1)
and (I2) give D_i[B, B'] := sum_n n_i A_B conj(A_B') = <B'| Ohat_i |B>, Ohat_i the operator
of (I2). Fix an unambiguous assignment and let E be the set of assigned patterns. For n in
E only the assigned Bell state has a non-zero amplitude, so G(n) = A(n) A(n)^dag is
Bell-diagonal; hence Lambda_i := sum_{n in E} n_i G(n) is Bell-diagonal and
D_i - Lambda_i = sum_{n not in E} n_i G(n) is PSD. D_i is the transpose of the Bell-basis
matrix of Ohat_i, and transposition preserves the PSD order against a real diagonal matrix,
so Lambda_i <= Ohat_i as operators. O_A(i) = conj(u) u^T (u = row i on qubit A's rails) is
PSD of rank <= 1, i.e. s_A |a><a| with s_A = |U_i0|^2 + |U_i1|^2 and a unit a; likewise O_B.
The lemma gives tr Lambda_i <= s_A(i) + s_B(i) + 4 c_i. Summing over i, with
sum_i tr Lambda_i = (k + 2) sum_B p_B (each pattern has k + 2 photons), and with
sum_i s_A(i) = sum_i s_B(i) = 2 and sum_i c_i = k (unit columns of U):
(k + 2) sum_B p_B <= 4 + 4k, i.e. (1/4) sum_B p_B <= (k + 1)/(k + 2).

Never-raise contract (like `core.check_certificate`): `check_moment_bound` returns a
`BoundCheck` for ANY input; `failure` is one of "shape", "lemma", "identity", "bound".
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import cache
from typing import Any

from empiricist.certificates.core import (
    Poly,
    check_certificate,
    poly_add,
    poly_eq,
    poly_mul,
    poly_scale,
    poly_sub,
)
from empiricist.certificates.p3_moment import BELL_LABELS, BELL_SQRT2, one_body_usd_certificate
from empiricist.domain.p3.fock import patterns
from empiricist.domain.p3.poly import bell_amp_poly, var_x, var_y

CPoly = tuple[Poly, Poly]
ANCILLA_MODE = 4
SUPPORTED: frozenset[tuple[int, int]] = frozenset({(0, 4), (0, 5), (1, 5), (1, 6)})
F = Fraction


@dataclass(frozen=True)
class MomentCheck:
    ok: bool
    detail: str
    n_identities: int


@dataclass(frozen=True)
class BoundCheck:
    ok: bool
    failure: str
    detail: str = ""
    bound: Fraction | None = None


# ---------------------------------------------------------------------------
# complex polynomials as (re, im) pairs
# ---------------------------------------------------------------------------


def _cadd(a: CPoly, b: CPoly) -> CPoly:
    return (poly_add(a[0], b[0]), poly_add(a[1], b[1]))


def _cmul(a: CPoly, b: CPoly) -> CPoly:
    return (poly_sub(poly_mul(a[0], b[0]), poly_mul(a[1], b[1])),
            poly_add(poly_mul(a[0], b[1]), poly_mul(a[1], b[0])))


def _cscale(a: CPoly, c: Fraction) -> CPoly:
    return (poly_scale(a[0], c), poly_scale(a[1], c))


def _conj(a: CPoly) -> CPoly:
    return (a[0], poly_scale(a[1], F(-1)))


def _entry(i: int, j: int, m: int) -> CPoly:
    return ({(var_x(i, j, m),): F(1)}, {(var_y(i, j, m),): F(1)})


def _components(label: str, k: int, m: int) -> list[tuple[tuple[int, ...], int]]:
    """The two Fock components (0/1 occupation tuples on m modes) with their signs."""
    pad = [0] * (m - 4)
    if k == 1:
        pad[ANCILLA_MODE - 4] = 1
    if label.startswith("phi"):
        t1, t2 = (1, 0, 1, 0), (0, 1, 0, 1)
    else:
        t1, t2 = (1, 0, 0, 1), (0, 1, 1, 0)
    sign = 1 if label.endswith("+") else -1
    return [((*t1, *pad), 1), ((*t2, *pad), sign)]


def _perm(mat: list[list[CPoly]]) -> CPoly:
    n = len(mat)
    if n == 1:
        return mat[0][0]
    if n == 2:
        return _cadd(_cmul(mat[0][0], mat[1][1]), _cmul(mat[0][1], mat[1][0]))
    raise ValueError("only 1- and 2-photon conditional states are supported")


# ---------------------------------------------------------------------------
# the moment matrices and identities
# ---------------------------------------------------------------------------


def hermitian_moment_matrices(k: int, m: int) -> list[list[list[CPoly]]]:
    """mats[i][b][bp] = sum_n n_i A_B(n) conj(A_B'(n)) as an exact complex polynomial."""
    anc = ANCILLA_MODE if k == 1 else None
    pats = patterns(2 + k, m)
    amps = {(b, n): bell_amp_poly(m, b, n, anc) for b in BELL_LABELS for n in pats}
    mats = [[[({}, {}) for _ in BELL_LABELS] for _ in BELL_LABELS] for _ in range(m)]
    for bi, b in enumerate(BELL_LABELS):
        for bpi, bp in enumerate(BELL_LABELS):
            for n in pats:
                (re1, im1), scale = amps[b, n]
                (re2, im2), _ = amps[bp, n]
                if not (re1 or im1) or not (re2 or im2):
                    continue
                prod = _cscale(_cmul((re1, im1), (re2, poly_scale(im2, F(-1)))), scale)
                for i in range(m):
                    if n[i]:
                        mats[i][bi][bpi] = _cadd(mats[i][bi][bpi], _cscale(prod, F(n[i])))
    return mats


def _gram_entries(m: int, modes: list[int]) -> dict[tuple[int, int], CPoly]:
    """G_ab = (U^dag U)_ab = sum_r conj(U_ra) U_rb for the input modes that carry photons."""
    out: dict[tuple[int, int], CPoly] = {}
    for a in modes:
        for b in modes:
            acc: CPoly = ({}, {})
            for r in range(m):
                acc = _cadd(acc, _cmul(_conj(_entry(r, a, m)), _entry(r, b, m)))
            out[a, b] = acc
    return out


def _h_matrix(b: str, bp: str, k: int, m: int, gram) -> dict[tuple[int, int], CPoly]:
    """H_jl^{BB'}(G) = <a_l in_B'| Gamma(G) |a_j in_B>; `gram` maps (row, col) to an entry
    (a CPoly, or a Fraction for the identity)."""
    out: dict[tuple[int, int], CPoly] = {}
    for t, s in _components(b, k, m):
        for tp, sp in _components(bp, k, m):
            for j in range(m):
                if not t[j]:
                    continue
                cols = [c for c in range(m) if t[c] and c != j]
                for ll in range(m):
                    if not tp[ll]:
                        continue
                    rows = [r for r in range(m) if tp[r] and r != ll]
                    mat = [[gram(r, c) for c in cols] for r in rows]
                    term = _cscale(_perm(mat), F(s * sp, 2))
                    out[j, ll] = _cadd(out.get((j, ll), ({}, {})), term)
    return out


def _const(x: Fraction) -> CPoly:
    return ({(): x} if x else {}, {})


def moment_identities(k: int, m: int, *, _drop_ancilla_term: bool = False) -> MomentCheck:
    """Check (I1) and (I2) for every output mode and Bell pair. `_drop_ancilla_term` exists
    for the must-fail test only (it removes c_i from the (I2) right-hand side)."""
    if (k, m) not in SUPPORTED:
        return MomentCheck(False, f"(k, m) = ({k}, {m}) not supported", 0)
    lhs = hermitian_moment_matrices(k, m)
    modes = sorted({j for b in BELL_LABELS for t, _ in _components(b, k, m) for j in range(m)
                    if t[j]})
    gram = _gram_entries(m, modes)
    count = 0
    for bi, b in enumerate(BELL_LABELS):
        for bpi, bp in enumerate(BELL_LABELS):
            h_g = _h_matrix(b, bp, k, m, lambda r, c: gram[r, c])
            h_i = _h_matrix(b, bp, k, m, lambda r, c: _const(F(int(r == c))))
            for i in range(m):
                rhs1: CPoly = ({}, {})
                rhs3: CPoly = ({}, {})
                for (j, ll), h in h_g.items():
                    w = _cmul(_entry(i, j, m), _conj(_entry(i, ll, m)))
                    rhs1 = _cadd(rhs1, _cmul(w, h))
                    rhs3 = _cadd(rhs3, _cmul(w, h_i[j, ll]))
                count += 1
                if not (poly_eq(lhs[i][bi][bpi][0], rhs1[0])
                        and poly_eq(lhs[i][bi][bpi][1], rhs1[1])):
                    return MomentCheck(False, f"(I1) fails at i={i}, B={b}, B'={bp}", count)
                want = one_body_matrix(i, bi, bpi, k, m, _drop_ancilla=_drop_ancilla_term)
                if not (poly_eq(rhs3[0], want[0]) and poly_eq(rhs3[1], want[1])):
                    return MomentCheck(False, f"(I2) fails at i={i}, B={b}, B'={bp}", count)
    return MomentCheck(True, "", count)


def one_body_matrix(
    i: int, bi: int, bpi: int, k: int, m: int, *, _drop_ancilla: bool = False
) -> CPoly:
    """<B'| O_A(i) (x) I + I (x) O_B(i) + c_i I |B> from row i (two-qubit index 2*qA + qB);
    `bi`, `bpi` index `BELL_LABELS`."""
    def o(p: int, q: int) -> CPoly:
        return _cmul(_conj(_entry(i, p, m)), _entry(i, q, m))

    op = [[({}, {}) for _ in range(4)] for _ in range(4)]
    for qa in range(2):
        for qb in range(2):
            for qa2 in range(2):
                for qb2 in range(2):
                    r, s = 2 * qa + qb, 2 * qa2 + qb2
                    acc: CPoly = ({}, {})
                    if qb == qb2:
                        acc = _cadd(acc, o(qa, qa2))            # O_A (x) I, rails 0/1
                    if qa == qa2:
                        acc = _cadd(acc, o(2 + qb, 2 + qb2))    # I (x) O_B, rails 2/3
                    if r == s and k == 1 and not _drop_ancilla:
                        acc = _cadd(acc, o(ANCILLA_MODE, ANCILLA_MODE))
                    op[r][s] = acc
    vb, vbp = BELL_SQRT2[bi], BELL_SQRT2[bpi]
    out: CPoly = ({}, {})
    for r in range(4):
        for s in range(4):
            coef = F(vbp[r] * vb[s], 2)
            if coef:
                out = _cadd(out, _cscale(op[r][s], coef))
    return out


# ---------------------------------------------------------------------------
# the payload checker
# ---------------------------------------------------------------------------


def _lemma_matches_canonical(cert) -> bool:
    canon = one_body_usd_certificate()
    return (
        tuple(cert.variables) == canon.variables
        and cert.objective == canon.objective
        and cert.bound == canon.bound
        and tuple(cert.constraints) == canon.constraints
    )


def check_moment_bound(payload: Any) -> BoundCheck:
    """PASS iff (a), (b) and (c) of the module docstring hold. Never raises."""
    try:
        from empiricist.certificates.verifier import certificate_from_json

        if not isinstance(payload, dict):
            raise TypeError("payload must be a JSON object")
        k, m = payload["k"], payload["m"]
        if not (isinstance(k, int) and isinstance(m, int)) or isinstance(k, bool):
            raise TypeError("k and m must be integers")
        if (k, m) not in SUPPORTED:
            return BoundCheck(False, "shape", f"(k, m) = ({k}, {m}) not supported")
        raw = payload["claimed_p_avg_bound"]
        if isinstance(raw, bool) or not isinstance(raw, (str, int)):
            raise TypeError("claimed_p_avg_bound must be an exact rational string")
        claimed = Fraction(raw)
        lemma = certificate_from_json(payload["lemma_certificate"])
    except Exception as exc:  # noqa: BLE001 - never raise is the contract
        return BoundCheck(False, "shape", f"{type(exc).__name__}: {exc}")

    # Cheapest gates first; all three must hold for a PASS, so the order only decides which
    # failure is reported.
    theorem = F(k + 1, k + 2)
    if claimed < theorem:
        return BoundCheck(False, "bound", f"claimed {claimed} < (k+1)/(k+2) = {theorem}")
    if not _lemma_matches_canonical(lemma):
        return BoundCheck(False, "lemma", "lemma certificate is not the canonical one-body lemma")
    res = check_certificate(lemma)
    if not res.ok:
        return BoundCheck(False, "lemma", f"lemma certificate rejected: {res.failure}")
    try:
        ident = _cached_identities(k, m)
    except Exception as exc:  # noqa: BLE001
        return BoundCheck(False, "identity", f"{type(exc).__name__}: {exc}")
    if not ident.ok:
        return BoundCheck(False, "identity", ident.detail)
    return BoundCheck(True, "", f"{ident.n_identities} identities; bound {theorem}", theorem)


@cache
def _cached_identities(k: int, m: int) -> MomentCheck:
    """`moment_identities` is a pure function of (k, m); one exact expansion per process."""
    return moment_identities(k, m)

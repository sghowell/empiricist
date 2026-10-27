"""P3 moment certificates (M27b): exact builders for the photon-number moment bound.

This is an ASSEMBLY module like `p3_targets.py`: it builds exact `SOSCertificate`s whose
algebra `certificates/core.py` checks. Nothing here is trusted; whether the constraint
polynomials encode the intended variety is pinned by `tests/test_p3_moment.py`.

The mathematics (the science note `docs/science/2026-10-26-p3-moment-bounds.md` has the full
proof). For a Bell-measurement scheme with a k-photon ancilla, output mode i and Bell states
B, B', let G(n) = z(n) z(n)^dagger with z_B(n) = <n|out_B>, and

    D_i[B, B'] = sum_n n_i z_B(n) conj(z_B'(n)) = <out_B'| N_i |out_B>,

the Gram matrix of the conditional states b_i|out_B>. A pattern that identifies a Bell state
contributes a Bell-diagonal rank-one term, so for every unambiguous assignment the
identified part Lambda_i = sum_{n identified} n_i G(n) is Bell-diagonal with
0 <= Lambda_i <= D_i, and (k + 2) * sum_B p_B = sum_i tr Lambda_i. One body: D_i is the
matrix of the two-qubit operator s_A |a><a| (x) I + s_B I (x) |b><b| + c_i I in the Bell basis
(s_A, s_B the squared norms of row i on qubit A's and qubit B's rails, c_i the ancilla's
photon number in output mode i). THE ONE-BODY USD LEMMA bounds tr Lambda_i by
s_A + s_B + 4 c_i; summed over i (sum s_A = sum s_B = 2, sum c_i = k) it gives

    p_avg <= (k + 1) / (k + 2)      for every k, m, U, k-photon ancilla and assignment.

`one_body_usd_certificate` is the lemma as an exact SOS certificate. Variables (47 real):
alpha, beta in C^2 (re/im), s_A, s_B, c, lambda_B (one per Bell label, `BELL_LABELS`
order), W in C^{4x4} (re/im). Constraints: |alpha|^2 = 1, |beta|^2 = 1, and the 16 real
entries of  E = D - Lambda - W W^dagger  (diagonal real parts, then real and imaginary
parts above the diagonal). Objective sum_B lambda_B - s_A - s_B - 4c, bound 0. The proof
is weak duality with the dual Y = |a_perp><a_perp| (x) I + I (x) |b_perp><b_perp|,
a_perp = (-conj(a_1), conj(a_0)): Y is PSD, <B|Y|B> = (|a|^2 + |b|^2)/2 for every
maximally entangled B, tr(Y D) = (s_A + s_B)|a|^2|b|^2 + 2c(|a|^2 + |b|^2), and
tr(Y W W^dagger) = ||(a_perp^dagger (x) I) W||^2 + ||(I (x) b_perp^dagger) W||^2 is the SOS.
Two-qubit basis |jk> = index 2j + k; qubit A's rail 0 is |0>, qubit B's rail 2 is |0>.
"""
from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from empiricist.certificates.core import (
    Monomial,
    Poly,
    SOSCertificate,
    poly_add,
    poly_mul,
    poly_scale,
    poly_sub,
)

BELL_LABELS = ("phi+", "phi-", "psi+", "psi-")
# sqrt(2) * |B> in the computational basis |00>, |01>, |10>, |11> (integer entries).
BELL_SQRT2: tuple[tuple[int, int, int, int], ...] = (
    (1, 0, 0, 1),    # phi+ = (|00> + |11>)/sqrt2
    (1, 0, 0, -1),   # phi-
    (0, 1, 1, 0),    # psi+ = (|01> + |10>)/sqrt2
    (0, 1, -1, 0),   # psi-
)

ONE_BODY_USD_DATA = Path(__file__).resolve().parent / "data" / "p3_one_body_usd.json"

CPoly = tuple[Poly, Poly]  # (real part, imaginary part)
_ZERO: CPoly = ({}, {})
F = Fraction


# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------


def one_body_usd_variables() -> tuple[str, ...]:
    names: list[str] = []
    for j in range(2):
        names += [f"alpha{j}_re", f"alpha{j}_im"]
    for j in range(2):
        names += [f"beta{j}_re", f"beta{j}_im"]
    names += ["sA", "sB", "c"]
    names += [f"lam_{b}" for b in BELL_LABELS]
    for r in range(4):
        for s in range(4):
            names += [f"W{r}{s}_re", f"W{r}{s}_im"]
    return tuple(names)


_NAMES = one_body_usd_variables()
_IDX = {n: i for i, n in enumerate(_NAMES)}


def _real(name: str) -> Poly:
    return {(_IDX[name],): F(1)}


def _cvar(stem: str) -> CPoly:
    return (_real(f"{stem}_re"), _real(f"{stem}_im"))


# ---------------------------------------------------------------------------
# Complex polynomial arithmetic over (re, im) pairs of exact real polynomials
# ---------------------------------------------------------------------------


def _cadd(a: CPoly, b: CPoly) -> CPoly:
    return (poly_add(a[0], b[0]), poly_add(a[1], b[1]))


def _csub(a: CPoly, b: CPoly) -> CPoly:
    return (poly_sub(a[0], b[0]), poly_sub(a[1], b[1]))


def _cmul(a: CPoly, b: CPoly) -> CPoly:
    re = poly_sub(poly_mul(a[0], b[0]), poly_mul(a[1], b[1]))
    im = poly_add(poly_mul(a[0], b[1]), poly_mul(a[1], b[0]))
    return (re, im)


def _cscale_real(a: CPoly, p: Poly) -> CPoly:
    return (poly_mul(a[0], p), poly_mul(a[1], p))


def _conj(a: CPoly) -> CPoly:
    return (a[0], poly_scale(a[1], F(-1)))


def _const(x: Fraction) -> CPoly:
    return ({(): x} if x else {}, {})


def _abs2(a: CPoly) -> Poly:
    return poly_add(poly_mul(a[0], a[0]), poly_mul(a[1], a[1]))


def _outer(u: list[CPoly], v: list[CPoly]) -> list[list[CPoly]]:
    """u v^dagger."""
    return [[_cmul(ui, _conj(vj)) for vj in v] for ui in u]


def _kron(a: list[list[CPoly]], b: list[list[CPoly]]) -> list[list[CPoly]]:
    n, p = len(a), len(b)
    out = [[_ZERO] * (n * p) for _ in range(n * p)]
    for i in range(n):
        for j in range(n):
            for k in range(p):
                for ll in range(p):
                    out[p * i + k][p * j + ll] = _cmul(a[i][j], b[k][ll])
    return out


def _eye(n: int) -> list[list[CPoly]]:
    return [[_const(F(int(i == j))) for j in range(n)] for i in range(n)]


def _madd(a, b):
    return [[_cadd(x, y) for x, y in zip(ra, rb, strict=True)] for ra, rb in zip(a, b, strict=True)]


def _mscale(a, p: Poly):
    return [[_cscale_real(x, p) for x in row] for row in a]


# ---------------------------------------------------------------------------
# The lemma certificate
# ---------------------------------------------------------------------------


def _default_projectors() -> list[list[list[Fraction]]]:
    return [[[F(u * v, 2) for v in vec] for u in vec] for vec in BELL_SQRT2]


def _to_gram(squares: list[Poly]) -> tuple[tuple[Monomial, ...], tuple[tuple[Fraction, ...], ...]]:
    """sum_k q_k^2 as b^T Q b over the monomials the q_k use: Q = sum_k c_k c_k^T."""
    basis = sorted({m for q in squares for m in q}, key=lambda m: (len(m), m))
    pos = {m: i for i, m in enumerate(basis)}
    n = len(basis)
    gram = [[F(0)] * n for _ in range(n)]
    for q in squares:
        items = [(pos[m], c) for m, c in q.items()]
        for a, ca in items:
            for b, cb in items:
                gram[a][b] += ca * cb
    return tuple(basis), tuple(tuple(row) for row in gram)


def one_body_usd_certificate(
    bell_projectors: list[list[list[Fraction]]] | None = None,
) -> SOSCertificate:
    """The exact SOS certificate of the one-body USD lemma (see the module docstring).

    `bell_projectors` (four rational 4x4 matrices, default the Bell projectors) exists for
    the must-fail tests only: the lemma needs maximally mixed marginals, and a product
    projector in place of a Bell projector must break the identity."""
    projectors = bell_projectors if bell_projectors is not None else _default_projectors()
    alpha = [_cvar("alpha0"), _cvar("alpha1")]
    beta = [_cvar("beta0"), _cvar("beta1")]
    sA, sB, c = _real("sA"), _real("sB"), _real("c")
    lam = [_real(f"lam_{b}") for b in BELL_LABELS]
    W = [[_cvar(f"W{r}{s}") for s in range(4)] for r in range(4)]

    eye2 = _eye(2)
    D = _madd(
        _madd(_mscale(_kron(_outer(alpha, alpha), eye2), sA),
              _mscale(_kron(eye2, _outer(beta, beta)), sB)),
        _mscale(_eye(4), c),
    )
    Lam = [[_ZERO] * 4 for _ in range(4)]
    for k in range(4):
        for r in range(4):
            for s in range(4):
                if projectors[k][r][s]:
                    Lam[r][s] = _cadd(Lam[r][s], (poly_scale(lam[k], projectors[k][r][s]), {}))
    WWd = [[_ZERO] * 4 for _ in range(4)]
    for r in range(4):
        for s in range(4):
            acc = _ZERO
            for t in range(4):
                acc = _cadd(acc, _cmul(W[r][t], _conj(W[s][t])))
            WWd[r][s] = acc
    E = [[_csub(_csub(D[r][s], Lam[r][s]), WWd[r][s]) for s in range(4)] for r in range(4)]

    g_alpha = poly_sub(poly_add(_abs2(alpha[0]), _abs2(alpha[1])), {(): F(1)})
    g_beta = poly_sub(poly_add(_abs2(beta[0]), _abs2(beta[1])), {(): F(1)})
    beta2 = poly_add(_abs2(beta[0]), _abs2(beta[1]))
    sum_lam = {}
    for p in lam:
        sum_lam = poly_add(sum_lam, p)

    # The dual Y = |a_perp><a_perp| (x) I + I (x) |b_perp><b_perp|, polynomial in alpha, beta.
    a_perp = [poly_neg_conj(alpha[1]), _conj(alpha[0])]
    b_perp = [poly_neg_conj(beta[1]), _conj(beta[0])]
    Y = _madd(_kron(_outer(a_perp, a_perp), eye2), _kron(eye2, _outer(b_perp, b_perp)))

    # Constraints and multipliers (see the module docstring for the derivation):
    #   sum mu_k g_k = s_A + s_B + 4c - sum lambda - tr(Y W W^dagger), with
    #   mu_alpha = -(s_A + s_B)|beta|^2 - 2c + sum(lambda)/2,
    #   mu_beta  = -(s_A + s_B)         - 2c + sum(lambda)/2,
    #   and tr(Y E) spelled out over the real entries of the Hermitian E.
    half = F(1, 2)
    s_ab = poly_add(sA, sB)
    mu_alpha = poly_add(poly_add(poly_scale(poly_mul(s_ab, beta2), F(-1)), poly_scale(c, F(-2))),
                        poly_scale(sum_lam, half))
    mu_beta = poly_add(poly_add(poly_scale(s_ab, F(-1)), poly_scale(c, F(-2))),
                       poly_scale(sum_lam, half))
    constraints: list[Poly] = [g_alpha, g_beta]
    multipliers: list[Poly] = [mu_alpha, mu_beta]
    for r in range(4):
        constraints.append(E[r][r][0])
        multipliers.append(Y[r][r][0])
    for r in range(4):
        for s in range(r + 1, 4):
            constraints.append(E[r][s][0])
            multipliers.append(poly_scale(Y[s][r][0], F(2)))
            constraints.append(E[r][s][1])
            multipliers.append(poly_scale(Y[s][r][1], F(-2)))

    # The SOS: ||(a_perp^dagger (x) I) W||^2 + ||(I (x) b_perp^dagger) W||^2, real squares.
    squares: list[Poly] = []
    ap_c = [_conj(x) for x in a_perp]
    bp_c = [_conj(x) for x in b_perp]
    for col in range(4):
        for k in range(2):  # (a_perp^dagger (x) I) W : row k of qubit B
            q = _cadd(_cmul(ap_c[0], W[2 * 0 + k][col]), _cmul(ap_c[1], W[2 * 1 + k][col]))
            squares += [q[0], q[1]]
        for j in range(2):  # (I (x) b_perp^dagger) W : row j of qubit A
            q = _cadd(_cmul(bp_c[0], W[2 * j + 0][col]), _cmul(bp_c[1], W[2 * j + 1][col]))
            squares += [q[0], q[1]]
    squares = [q for q in squares if q]
    gram_basis, gram = _to_gram(squares)

    objective = poly_sub(poly_sub(poly_sub(sum_lam, sA), sB), poly_scale(c, F(4)))
    return SOSCertificate(
        statement=(
            "P3 one-body USD lemma: for unit alpha, beta in C^2, real s_A, s_B, c, lambda_B "
            "and W in C^{4x4} with s_A|a><a|(x)I + s_B I(x)|b><b| + cI - sum_B lambda_B|B><B| "
            "= W W^dag (B the Bell states), sum_B lambda_B <= s_A + s_B + 4c"
        ),
        variables=_NAMES,
        objective=objective,
        bound=F(0),
        constraints=tuple(constraints),
        multipliers=tuple(multipliers),
        gram_basis=gram_basis,
        gram=gram,
    )


def poly_neg_conj(a: CPoly) -> CPoly:
    """-conj(a)."""
    return (poly_scale(a[0], F(-1)), a[1])

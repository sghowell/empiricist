"""Exact polynomialization of dual-rail Bell-measurement detection probabilities.

Converts `Pr[pattern | bell_state]` for a passive linear-optical Bell
measurement (no ancilla; k=0) into a polynomial identity with EXACT rational
(`fractions.Fraction`) coefficients in the real/imaginary parts of the
interferometer unitary's entries, plus an exact rational scale factor. This
is the input layer for the P3 SOS certificate pipeline (M20c): everything
downstream (the exact checker, the rationalized SDP output) trusts that this
generator reproduces the two independent numeric engines
(`engine_permanent.PermanentEngine`, `engine_fock.FockEngine`); a bug here
would silently manufacture vacuous certificates. THE WARRANT for this module
is `tests/test_p3_poly.py`'s cross-validation: the polynomial, evaluated
numerically at a mesh's unitary entries, must reproduce both engines'
`output_distribution` to 1e-10 -- on the standard BSM and on 20 random 4-mode
meshes.

Variable indexing (normative, stable -- do not renumber without updating
every caller): for an m-mode interferometer, U[i][j] = x_ij + i*y_ij with

    x_ij = var_x(i, j, m) = 2*(i*m + j)
    y_ij = var_y(i, j, m) = 2*(i*m + j) + 1

Both are flat non-negative integer indices into the same variable space
(2*m*m real variables total). A polynomial (`Poly`) is
`dict[tuple[int, ...], Fraction]`: keys are SORTED tuples of variable
indices (a monomial; repeated indices are powers, `()` is the constant
monomial), values are the (always exact) coefficients.

Scaling convention. For a Bell state B = (1/sqrt2)*(|T1> +- |T2>) (see
`scheme.bell_input_states` for the exact Fock components and signs) and an
output pattern S (both 2-photon patterns here), the transition amplitude is

    A_{S,B} = (1/sqrt2) * (Per(U[S,T1])/N1 +- Per(U[S,T2])/N2)

with Nk = sqrt(prod(S!) * prod(Tk!)) (see `engine_permanent`'s amplitude
formula). Dual-rail Bell components always have 0/1 occupations, so
prod(Tk!) = 1 and Nk = sqrt(prod(S!)) for both k, giving

    A_{S,B} = (1 / (sqrt2 * sqrt(prod(S!)))) * (Per(U[S,T1]) +- Per(U[S,T2]))
    Pr[S|B] = |A_{S,B}|^2 = (1 / (2*prod(S!))) * |Per(U[S,T1]) +- Per(U[S,T2])|^2

`prob_poly` returns `(poly, scale)` with

    poly  = |Per(U[S,T1]) +- Per(U[S,T2])|^2   -- degree-4, INTEGER-coefficient
    scale = Fraction(1, 2 * prod(S!))           -- exact rational

such that `Pr[S|B] == scale * eval_poly(poly, values)`. The two permanents
are each degree-2 polynomials in the real/imaginary variables (a 2x2
permanent, since exactly 2 photons are supported -- see `_symbolic_permanent`);
expanding `|z|^2 = re(z)^2 + im(z)^2` symbolically keeps every coefficient in
the poly an exact integer (represented as `Fraction` for interface
uniformity with the certificate checker).

Scope: this module supports exactly 2-photon detection patterns on k=0
(no-ancilla) dual-rail Bell schemes, m>=4 modes. `prob_poly` raises
`NotImplementedError` for any other total photon number (k>=1 ancilla
schemes are out of scope for M20c Task 1; the underlying permanent
machinery is written generally over the photon number, but the scope guard
in `prob_poly` is where the restriction is enforced and documented).
"""

from __future__ import annotations

import itertools
from fractions import Fraction

from .fock import factorial_prod

Monomial = tuple[int, ...]
Poly = dict[Monomial, Fraction]
# A complex-valued polynomial, represented as (real part, imaginary part),
# each a real `Poly`. Never exposed publicly -- an internal bookkeeping type
# for expanding permanents of complex-linear entries symbolically.
_CPoly = tuple[Poly, Poly]

_BELL_LABELS = ("phi+", "phi-", "psi+", "psi-")


def var_x(i: int, j: int, m: int) -> int:
    """Flat variable index for Re(U[i][j]) among an m-mode interferometer's
    2*m*m real variables. See the module docstring for the indexing scheme
    and its pairing with `var_y`."""
    return 2 * (i * m + j)


def var_y(i: int, j: int, m: int) -> int:
    """Flat variable index for Im(U[i][j]); see `var_x`."""
    return 2 * (i * m + j) + 1


def _mono_mul(a: Monomial, b: Monomial) -> Monomial:
    return tuple(sorted(a + b))


def poly_add(p: Poly, q: Poly) -> Poly:
    out = dict(p)
    for mono, coef in q.items():
        c = out.get(mono, Fraction(0)) + coef
        if c:
            out[mono] = c
        else:
            out.pop(mono, None)
    return out


def poly_scale(p: Poly, c: Fraction) -> Poly:
    if not c:
        return {}
    return {mono: c * coef for mono, coef in p.items()}


def poly_mul(p: Poly, q: Poly) -> Poly:
    out: Poly = {}
    for ma, ca in p.items():
        for mb, cb in q.items():
            mono = _mono_mul(ma, mb)
            out[mono] = out.get(mono, Fraction(0)) + ca * cb
    return {mono: c for mono, c in out.items() if c}


def _cplx_add(a: _CPoly, b: _CPoly) -> _CPoly:
    return (poly_add(a[0], b[0]), poly_add(a[1], b[1]))


def _cplx_scale(a: _CPoly, c: Fraction) -> _CPoly:
    return (poly_scale(a[0], c), poly_scale(a[1], c))


def _cplx_mul(a: _CPoly, b: _CPoly) -> _CPoly:
    ar, ai = a
    br, bi = b
    re = poly_add(poly_mul(ar, br), poly_scale(poly_mul(ai, bi), Fraction(-1)))
    im = poly_add(poly_mul(ar, bi), poly_mul(ai, br))
    return (re, im)


def _cplx_entry(i: int, j: int, m: int) -> _CPoly:
    """U[i][j] as a degree-1 complex polynomial: x_ij + i*y_ij."""
    return ({(var_x(i, j, m),): Fraction(1)}, {(var_y(i, j, m),): Fraction(1)})


def _submatrix_rows_cols(
    out_pattern: tuple[int, ...], in_pattern: tuple[int, ...]
) -> tuple[list[int], list[int]]:
    """Same row/column-repetition convention as `engine_permanent._submatrix`
    (mirrored here independently, symbolically): row i repeated s_i times,
    column j repeated t_j times."""
    rows = [i for i, s in enumerate(out_pattern) for _ in range(s)]
    cols = [j for j, t in enumerate(in_pattern) for _ in range(t)]
    return rows, cols


def _symbolic_permanent(
    m: int, out_pattern: tuple[int, ...], in_pattern: tuple[int, ...]
) -> _CPoly:
    """Per(U[S, T]) as a complex polynomial (a (real, imag) pair of real
    `Poly`s), via the direct permutation-sum definition of the permanent
    (general over k = sum(S) = sum(T); this module's public entry point,
    `prob_poly`, restricts k to 2 -- see its scope guard -- but the
    machinery here does not itself assume k)."""
    rows, cols = _submatrix_rows_cols(out_pattern, in_pattern)
    k = len(rows)
    if k != len(cols):
        raise ValueError("row/col photon-number mismatch in symbolic permanent")
    if k == 0:
        return ({(): Fraction(1)}, {})
    entries = [[_cplx_entry(rows[a], cols[b], m) for b in range(k)] for a in range(k)]
    total: _CPoly = ({}, {})
    for perm in itertools.permutations(range(k)):
        term: _CPoly = ({(): Fraction(1)}, {})
        for a, b in enumerate(perm):
            term = _cplx_mul(term, entries[a][b])
        total = _cplx_add(total, term)
    return total


def _bell_components(
    bell_label: str, m: int
) -> tuple[tuple[int, ...], tuple[int, ...], int]:
    """The two Fock components (T1, T2) and their relative sign for a Bell
    label, padded with vacuum on ancilla modes 4..m-1 (k=0 schemes only --
    matches `scheme.bell_input_states`'s empty-ancilla convention)."""
    if bell_label not in _BELL_LABELS:
        raise ValueError(f"unknown bell_label {bell_label!r}; expected one of {_BELL_LABELS}")
    pad = (0,) * (m - 4)
    if bell_label.startswith("phi"):
        t1, t2 = (1, 0, 1, 0) + pad, (0, 1, 0, 1) + pad
    else:
        t1, t2 = (1, 0, 0, 1) + pad, (0, 1, 1, 0) + pad
    sign = 1 if bell_label.endswith("+") else -1
    return t1, t2, sign


def prob_poly(m: int, bell_label: str, pattern: tuple[int, ...]) -> tuple[Poly, Fraction]:
    """Exact `(poly, scale)` such that `scale * eval_poly(poly, values)` equals
    `Pr[pattern | bell_label]` for a k=0 dual-rail Bell scheme on `m` modes,
    where `values` maps each `var_x`/`var_y` index to Re/Im of the
    interferometer unitary's corresponding entry. See the module docstring
    for the exact scaling convention and its derivation.

    Supports exactly 2-photon detection patterns (m >= 4); raises
    `NotImplementedError` for any other total photon number (k>=1 ancilla
    schemes -- out of scope for M20c Task 1).
    """
    if m < 4:
        raise ValueError(f"a Bell scheme needs at least 4 modes, got m={m}")
    if len(pattern) != m:
        raise ValueError(f"pattern {pattern!r} has {len(pattern)} entries, expected m={m}")
    n_photons = sum(pattern)
    if n_photons != 2:
        raise NotImplementedError(
            "prob_poly supports exactly 2-photon detection patterns (k=0 dual-rail "
            f"Bell schemes); got {n_photons} photons for pattern={pattern!r}. Multi-photon "
            "ancilla schemes (k>=1) are out of scope for M20c Task 1."
        )
    t1, t2, sign = _bell_components(bell_label, m)
    per1 = _symbolic_permanent(m, pattern, t1)
    per2 = _symbolic_permanent(m, pattern, t2)
    combined = _cplx_add(per1, _cplx_scale(per2, Fraction(sign)))
    re, im = combined
    poly = poly_add(poly_mul(re, re), poly_mul(im, im))
    scale = Fraction(1, 2 * factorial_prod(pattern))
    return poly, scale


def eval_poly(poly: Poly, values: dict[int, float] | list[float]) -> float:
    """Evaluate `poly` at `values` (indexed by `var_x`/`var_y` indices).

    Test helper: no float casts are performed internally, so passing
    `fractions.Fraction` values (e.g. entries of an exactly rational unitary
    like the identity) keeps the ENTIRE evaluation in exact arithmetic and
    returns a `Fraction` -- the pure-ℚ path used to pin exact results.
    Passing Python floats (the common case, e.g. a numeric `mesh_unitary`
    output) returns a float, for cross-validation against the numeric
    engines.
    """
    total = 0
    for mono, coef in poly.items():
        term = coef
        for idx in mono:
            term = term * values[idx]
        total = total + term
    return total

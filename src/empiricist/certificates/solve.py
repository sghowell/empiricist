"""SDP assembly, numeric solve, and exact rationalization for SOS
certificates -- M20c's SEARCH side (`certificates/core.py` is the TRUST
side; see that module's docstring for the full boundary discussion). This
module FINDS certificates using heavy numerical machinery (cvxpy/SCS SDP
solve, floats) and then RATIONALIZES the numeric result into an exact
`Fraction`-only `SOSCertificate` that `certificates.core.check_certificate`
can verify from scratch. Nothing found here is ever trusted directly --
only a certificate that PASSES the exact checker is ever returned by
`rationalize`.

Quarantine. `cvxpy` (and its `scs` backend) is a heavy dependency, kept out
of the main dependency set and installed only via the `certs` dependency
group (`uv sync --group certs`; see pyproject.toml). `cvxpy` is imported
ONLY inside `solve_sos`, at the top of the function body (never at module
level, never anywhere else in this file), so

    import empiricist.certificates.solve

succeeds even in an environment where `cvxpy` is not installed at all --
only *calling* `solve_sos` requires it (and raises a clear `ImportError`
telling the caller how to install it if it's missing). `rationalize` needs
no heavy dependency whatsoever: it is pure `fractions.Fraction` linear
algebra (Gauss-Jordan elimination), deliberately -- repairing an exact
certificate from a numeric one is a stdlib-only operation once the numeric
solve has already happened.

Poly convention: identical to `certificates.core` (see that module's
docstring) -- `Monomial = tuple[int, ...]` (sorted variable-index tuple),
`Poly = dict[Monomial, Fraction]`. `variables: tuple[str, ...]` gives the
human-readable name for variable index `i` at position `variables[i]`;
every `Poly` here is a monomial-indexed dict over those same indices.
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

from empiricist.certificates.core import (
    Monomial,
    Poly,
    SOSCertificate,
    check_certificate,
    poly_sub,
)

# ---------------------------------------------------------------------------
# Shared helpers (deliberately a local copy of the monomial-product
# convention -- see certificates/core.py's docstring on why this small bit
# of arithmetic is duplicated per module rather than shared for this
# milestone).
# ---------------------------------------------------------------------------


def _mono_mul(a: Monomial, b: Monomial) -> Monomial:
    return tuple(sorted(a + b))


def _poly_degree(p: Poly) -> int:
    """Max total degree among `p`'s monomials (0 for the zero polynomial or
    a pure constant)."""
    return max((len(mono) for mono in p), default=0)


def _monomials_up_to_degree(nvars: int, degree: int) -> tuple[Monomial, ...]:
    """All monomials over variable indices `0..nvars-1` with total degree
    `0..degree`, each a sorted tuple (repeated indices are powers; `()` is
    the constant monomial), in a stable canonical order (grouped by
    ascending degree). For any monomial basis `b` built this way, pairwise
    products `b[a]*b[b]` span EVERY monomial of total degree `0..2*degree`
    (split any degree-<=2*degree monomial's variable multiset into two
    halves, each of degree <= degree) -- this is what guarantees `solve_sos`
    and `rationalize`'s linear systems are always well-posed relative to the
    Gram part."""
    out: list[Monomial] = [()]
    for d in range(1, degree + 1):
        out.extend(itertools.combinations_with_replacement(range(nvars), d))
    return tuple(out)


# ---------------------------------------------------------------------------
# The numeric solve.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NumericCertificate:
    """A numerically-solved SOS certificate: everything `solve_sos` produces,
    in floats, BEFORE rationalization. Never checked directly against
    `check_certificate` (floats are rejected by the checker's shape check
    anyway) -- pass to `rationalize` to obtain an exact `SOSCertificate`."""

    variables: tuple[str, ...]
    degree: int
    bound: float
    gram_basis: tuple[Monomial, ...]
    gram: tuple[tuple[float, ...], ...]
    multiplier_basis: tuple[tuple[Monomial, ...], ...]
    multiplier_coeffs: tuple[tuple[float, ...], ...]


def solve_sos(
    objective: Poly,
    constraints: Sequence[Poly],
    variables: tuple[str, ...],
    degree: int,
) -> NumericCertificate | None:
    """Assemble and numerically solve the SOS relaxation for

        minimize t
        subject to  t - objective - sum_i(lambda_i * constraints[i])
                        == b^T Q b        (coefficient-wise, every monomial)
                    Q PSD

    where `b` (`gram_basis`) is every monomial over `variables`' indices of
    total degree `0..degree`, and each multiplier `lambda_i` ranges freely
    (unconstrained sign -- `constraints[i] == 0` on the variety, so its
    multiplier need not be nonnegative) over monomials of degree
    `0..(2*degree - deg(constraints[i]))`: exactly enough room for
    `lambda_i * constraints[i]` to reach the SOS part's degree `2*degree`.

    Returns `None` if: the identity is structurally unsatisfiable at this
    `degree` (e.g. `objective` has a monomial of degree > `2*degree`), or
    the solver does not report an optimal (or optimal-inaccurate) status.
    Never raises on solver failure -- solver exceptions are caught and
    reported as `None`.

    Imports `cvxpy` lazily (see module docstring): raises `ImportError`
    with an actionable message if it is not installed. This is the ONLY
    function in this module that touches cvxpy.
    """
    try:
        import cvxpy as cp
    except ImportError as exc:
        raise ImportError(
            "solve_sos requires cvxpy (and the scs backend); install with: "
            "uv sync --group certs"
        ) from exc

    nvars = len(variables)
    gram_basis = _monomials_up_to_degree(nvars, degree)
    n = len(gram_basis)

    multiplier_bases = tuple(
        _monomials_up_to_degree(nvars, max(2 * degree - _poly_degree(g), 0))
        for g in constraints
    )

    t = cp.Variable()
    gram_var = cp.Variable((n, n), symmetric=True)
    lambda_vars = [cp.Variable(len(mb)) for mb in multiplier_bases]

    # For every monomial reachable via a Gram-basis product, which (a, b)
    # index pairs contribute to it (both (a, b) and (b, a) -- matches
    # check_certificate's rhs, which sums over the full a, b range).
    gram_pairs: dict[Monomial, list[tuple[int, int]]] = defaultdict(list)
    for a in range(n):
        for b in range(n):
            gram_pairs[_mono_mul(gram_basis[a], gram_basis[b])].append((a, b))

    # For every monomial reachable via (multiplier-basis-monomial *
    # constraint-monomial), which (coefficient-index, weight) pairs
    # contribute to it, per constraint.
    mult_pairs: list[dict[Monomial, list[tuple[int, float]]]] = []
    for g, mbasis in zip(constraints, multiplier_bases, strict=True):
        d: dict[Monomial, list[tuple[int, float]]] = defaultdict(list)
        for k, basis_mono in enumerate(mbasis):
            for c_mono, c_val in g.items():
                d[_mono_mul(basis_mono, c_mono)].append((k, float(c_val)))
        mult_pairs.append(d)

    all_monos: set[Monomial] = set(objective) | {()} | set(gram_pairs)
    for d in mult_pairs:
        all_monos |= set(d)

    identity_constraints = []
    for mono in all_monos:
        expr = 0
        if mono == ():
            expr = expr + t
        obj_val = float(objective.get(mono, 0))
        if obj_val:
            expr = expr - obj_val
        for lam, d in zip(lambda_vars, mult_pairs, strict=True):
            for k, c_val in d.get(mono, ()):
                expr = expr - c_val * lam[k]
        for a, b in gram_pairs.get(mono, ()):
            expr = expr - gram_var[a, b]
        if isinstance(expr, (int, float)):
            if abs(expr) > 1e-9:
                # Structurally unsatisfiable: this monomial's coefficient
                # can never be zeroed by any choice of t/lambda/Q at this
                # degree (e.g. objective has a monomial beyond 2*degree).
                return None
            continue
        identity_constraints.append(expr == 0)

    identity_constraints.append(gram_var >> 0)

    problem = cp.Problem(cp.Minimize(t), identity_constraints)
    try:
        problem.solve(solver=cp.SCS)
    except Exception:
        return None

    if problem.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
        return None
    if t.value is None or gram_var.value is None:
        return None

    gram_val = tuple(tuple(float(v) for v in row) for row in gram_var.value)
    multiplier_coeffs = tuple(
        tuple(float(v) for v in lam.value)
        if lam.value is not None
        else tuple(0.0 for _ in mb)
        for lam, mb in zip(lambda_vars, multiplier_bases, strict=True)
    )

    return NumericCertificate(
        variables=variables,
        degree=degree,
        bound=float(t.value),
        gram_basis=gram_basis,
        gram=gram_val,
        multiplier_basis=multiplier_bases,
        multiplier_coeffs=multiplier_coeffs,
    )


# ---------------------------------------------------------------------------
# Exact rationalization.
# ---------------------------------------------------------------------------


_BOUND_SLACK = Fraction(1, 1000)


def _round_gram(
    gram: Sequence[Sequence[float]],
    gram_basis: tuple[Monomial, ...],
    denominator_limit: int,
) -> tuple[tuple[Fraction, ...], ...]:
    """Round the Gram matrix to `Fraction`, with PSD headroom.

    Rounding: every Gram entry via `limit_denominator(denominator_limit)`,
    then symmetrized exactly (average with the transpose -- independent
    per-entry rounding can break the exact symmetry `check_certificate`
    requires even when the float matrix was symmetric).

    Slack: a fixed `1/1000` margin is added to the Gram entry `Q[c][c]`
    (where `c` is the constant monomial `()`'s index in `gram_basis`, if
    present), for PSD headroom: `Q[c][c] += slack` is a rank-1 PSD update
    (`Q + slack * e_c e_c^T`, `slack >= 0`), so by Weyl's inequality every
    eigenvalue of `Q` can only increase -- it can only help the PSD check
    survive rounding error elsewhere, never hurt it. The polynomial
    identity stays exactly balanced because the BOUND IS SOLVED AFTER this
    slack is applied (`_rationalize_attempt` treats the bound as a free
    unknown of the exact repair system): on the variety the identity forces
    `bound = objective(v) + b^T Q b(v)`, and the slack lifts `b^T Q b` by
    exactly `slack` everywhere (the constant basis monomial evaluates to
    1), so the solved bound absorbs it automatically. If `()` is not in
    `gram_basis` (contrived degree-0 cases only), the slack is skipped.
    """
    n = len(gram)
    rounded = [
        [Fraction(gram[a][b]).limit_denominator(denominator_limit) for b in range(n)]
        for a in range(n)
    ]
    sym = [[(rounded[a][b] + rounded[b][a]) / 2 for b in range(n)] for a in range(n)]
    if () in gram_basis:
        const_idx = gram_basis.index(())
        sym[const_idx][const_idx] += _BOUND_SLACK
    return tuple(tuple(row) for row in sym)


def _solve_linear_exact(
    rows: list[list[Fraction]], rhs: list[Fraction], ncols: int
) -> list[Fraction] | None:
    """Solve `A @ x = rhs` over `Fraction` via Gauss-Jordan elimination
    (pivot on any nonzero entry in the remaining rows/column), returning a
    particular solution (free variables set to 0) or `None` if the system
    is inconsistent. `rows`/`rhs` may be over- or under-determined relative
    to `ncols`."""
    m = len(rows)
    aug = [row[:] + [rhs[i]] for i, row in enumerate(rows)]
    pivot_row = 0
    pivot_cols: list[int] = []
    for col in range(ncols):
        sel = None
        for r in range(pivot_row, m):
            if aug[r][col] != 0:
                sel = r
                break
        if sel is None:
            continue
        aug[pivot_row], aug[sel] = aug[sel], aug[pivot_row]
        pv = aug[pivot_row][col]
        aug[pivot_row] = [v / pv for v in aug[pivot_row]]
        for r in range(m):
            if r != pivot_row and aug[r][col] != 0:
                factor = aug[r][col]
                aug[r] = [aug[r][j] - factor * aug[pivot_row][j] for j in range(ncols + 1)]
        pivot_cols.append(col)
        pivot_row += 1
        if pivot_row == m:
            break

    for r in range(m):
        if all(v == 0 for v in aug[r][:ncols]) and aug[r][ncols] != 0:
            return None  # inconsistent: 0 == nonzero

    x = [Fraction(0)] * ncols
    for i, col in enumerate(pivot_cols):
        x[col] = aug[i][ncols]
    return x


def _rationalize_attempt(
    num_cert: NumericCertificate,
    objective: Poly,
    constraints: Sequence[Poly],
    variables: tuple[str, ...],
    denominator_limit: int,
) -> tuple[SOSCertificate | None, bool]:
    """One rationalization attempt at a fixed `denominator_limit`. Returns
    `(cert, retry_worthy)`: on success `cert` is the exact `SOSCertificate`
    and `retry_worthy` is `False`; on failure `cert` is `None` and
    `retry_worthy` is `True` only when the failure was specifically a PSD
    rejection by the exact checker (rounding pushed the Gram just barely
    non-PSD -- worth retrying with a larger denominator_limit), `False` for
    anything else (shape mismatches, an unrepairable identity).

    The BOUND is a free unknown of the exact repair system, NOT a
    pre-rounded input. Rounding it independently of the Gram would make the
    system infeasible on tight problems: on the variety the identity forces
    `bound - objective(v) == b^T Q b(v)` EXACTLY, so with `Q` fixed
    rational the bound is pinned (up to genuine slack in the system) and
    any independent rounding of it violates the relation by O(rounding).
    Solving for it alongside the multiplier coefficients strictly enlarges
    the repairable set, and soundness is automatic: whatever bound comes
    out, a checker PASS still proves `objective <= bound` on the variety.
    """
    n = len(num_cert.gram_basis)
    if len(num_cert.gram) != n or any(len(row) != n for row in num_cert.gram):
        return None, False
    if len(num_cert.multiplier_basis) != len(constraints):
        return None, False

    gram = _round_gram(num_cert.gram, num_cert.gram_basis, denominator_limit)

    # b^T Q b, exact, over the (now-rational) rounded Gram.
    gram_poly: Poly = {}
    for a in range(n):
        for b in range(n):
            coef = gram[a][b]
            if not coef:
                continue
            mono = _mono_mul(num_cert.gram_basis[a], num_cert.gram_basis[b])
            c = gram_poly.get(mono, Fraction(0)) + coef
            if c:
                gram_poly[mono] = c
            else:
                gram_poly.pop(mono, None)

    # The identity to repair, with both the multipliers AND the bound as
    # unknowns: sum_i(lambda_i * constraints[i]) - bound * 1 must equal
    # -objective - b^T Q b exactly, monomial by monomial.
    residual = poly_sub(poly_sub({}, objective), gram_poly)

    mbasis = num_cert.multiplier_basis
    offsets: list[int] = []
    total_cols = 0
    for mb in mbasis:
        offsets.append(total_cols)
        total_cols += len(mb)
    bound_col = total_cols  # one extra unknown: the bound itself

    col_targets: dict[Monomial, list[tuple[int, Fraction]]] = defaultdict(list)
    for i, (g, mb) in enumerate(zip(constraints, mbasis, strict=True)):
        for k, basis_mono in enumerate(mb):
            for c_mono, c_val in g.items():
                mono = _mono_mul(basis_mono, c_mono)
                col_targets[mono].append((offsets[i] + k, c_val))
    # The bound contributes -bound to the constant monomial's row (it
    # appears as +bound on the identity's LHS, moved across with the
    # unknowns). Always include the constant monomial so the bound is
    # constrained by its row rather than dangling free.
    col_targets[()].append((bound_col, Fraction(-1)))

    all_monos = sorted(set(residual) | set(col_targets), key=lambda m: (len(m), m))
    rows: list[list[Fraction]] = []
    rhs: list[Fraction] = []
    for mono in all_monos:
        row = [Fraction(0)] * (total_cols + 1)
        for col, val in col_targets.get(mono, ()):
            row[col] += val
        rows.append(row)
        rhs.append(residual.get(mono, Fraction(0)))

    solution = _solve_linear_exact(rows, rhs, total_cols + 1)
    if solution is None:
        return None, False  # unrepairable identity -- not a PSD issue

    bound = solution[bound_col]

    multipliers: list[Poly] = []
    for i, mb in enumerate(mbasis):
        poly: Poly = {}
        for k, basis_mono in enumerate(mb):
            val = solution[offsets[i] + k]
            if val:
                poly[basis_mono] = poly.get(basis_mono, Fraction(0)) + val
        multipliers.append(poly)

    cert = SOSCertificate(
        statement=f"rationalized SOS certificate (gram basis degree {num_cert.degree})",
        variables=variables,
        objective=objective,
        bound=bound,
        constraints=tuple(constraints),
        multipliers=tuple(multipliers),
        gram_basis=num_cert.gram_basis,
        gram=gram,
    )
    result = check_certificate(cert)
    if result.ok:
        return cert, False
    return None, result.failure == "psd"


def rationalize(
    num_cert: NumericCertificate,
    objective: Poly,
    constraints: Sequence[Poly],
    variables: tuple[str, ...],
    denominator_limit: int = 10**6,
) -> SOSCertificate | None:
    """Turn a numeric certificate into an exact one that
    `certificates.core.check_certificate` PASSES, or `None` if that proves
    impossible. Never raises: any malformed `num_cert` (wrong shapes,
    inconsistent lengths, whatever) is caught and reported as `None`,
    exactly like a genuine repair failure -- mirrors the checker's
    never-raise / total-function discipline.

    Steps: (a) round `num_cert.gram` to `Fraction` at `denominator_limit`,
    symmetrize exactly, and add a small PSD-headroom slack on the
    constant-monomial diagonal (see `_round_gram`); (b) REPAIR the
    polynomial identity exactly by solving for the multiplier coefficients
    AND the bound via exact Gauss-Jordan elimination over `Fraction` (with
    `Q` fixed rational, the system is linear in those unknowns; the bound
    must be solved, not pre-rounded -- see `_rationalize_attempt` for why
    pre-rounding it makes tight problems unrepairable); (c) run the
    assembled certificate through `check_certificate`. If that specifically
    fails on `"psd"` (rounding can push a numerically-PSD Gram just barely
    non-semidefinite), retry ONCE at `denominator_limit * 100`. Any other
    failure -- or a second failure -- returns `None`.

    The Gram slack in step (a) lifts the solved bound by the same amount
    (roughly `1/1000` above the numeric optimum), so returned bounds are
    valid-but-not-tight by construction.
    """
    try:
        cert, retry_worthy = _rationalize_attempt(
            num_cert, objective, constraints, variables, denominator_limit
        )
        if cert is not None:
            return cert
        if retry_worthy:
            cert, _ = _rationalize_attempt(
                num_cert, objective, constraints, variables, denominator_limit * 100
            )
            return cert
        return None
    except Exception:
        return None

"""Assemble the P3 k=0 certificate SDP: the assignment-fixed p_avg target.

M20c Task 4. This is the ASSEMBLY layer between `domain/p3/poly.py` (the exact
polynomialization of `Pr[pattern | bell_state]`) and `certificates/solve.py`
(the SDP solve) / `certificates/core.py` (the exact checker). It builds, as
exact `Fraction`-coefficient polynomials, the pieces of one honest, machine-
checkable bound:

    THE TARGET (assignment-fixed p_avg, the standard-BSM class):

        objective(U) = (1/4) * sum_B sum_{S in A_B} Pr[S | B]

    subject to the interferometer being unitary and to the UNAMBIGUITY
    equalities of the standard BSM's assignment (each assigned pattern has
    zero probability under the other three Bell states):

        unitarity:    U^dag U = I         (16 real degree-2 polys for m=4)
        unambiguity:  Pr[S | B'] = 0       for every S in A_B, B' != B

    where A_B is the standard linear-optical Bell measurement's assignment
    (see `known_schemes.standard_bsm`):

        psi+ : {(1,1,0,0), (0,0,1,1)}
        psi- : {(1,0,0,1), (0,1,1,0)}
        phi+ : {}          phi- : {}

    KNOWN VALUE: the maximum of `objective` over this variety is 1/2, achieved
    by the standard BSM itself (each of the four assigned probabilities is 1/2;
    p_avg = (1/4)*4*(1/2) = 1/2). A SOUND SOS certificate is one whose checked
    bound is <= 1/2 (+ tiny rational slack). This is a slice of the classic
    Calsamiglia-Lutkenhaus k=0 ceiling p_avg <= 1/2, fixed to one assignment
    structure so it is an exact polynomial optimization problem.

Why 1/2 is the ceiling (informal, for orientation only -- the certificate is
the actual warrant): for a fixed Bell state B, the assigned patterns are
disjoint outcomes, so sum_{S in A_B} Pr[S|B] <= sum_all_S Pr[S|B] = 1 by
probability conservation (itself an identity on the unitarity variety). Only
psi+ and psi- carry assigned patterns, contributing at most 1 each, so
objective <= (1/4)(1 + 1) = 1/2.

Variable indexing is `poly.py`'s: for an m-mode interferometer U[i][j] =
x_ij + i*y_ij with x_ij = var_x(i,j,m) = 2*(i*m+j) and y_ij = var_y = 2*(i*m+j)+1,
giving 2*m*m real variables (32 for m=4). Every polynomial here is a
`dict[sorted-tuple-of-int, Fraction]`, the shared `Poly` convention.

Homogeneity note (used by the exact self-tests): each `Pr[S|B]` polynomial is
homogeneous of degree 4 in the entry variables (a 2x2 permanent is degree 2;
|.|^2 doubles it), so `objective` is degree-4 homogeneous. Hence
`objective(c*U) = c^4 * objective(U)`; evaluating at sqrt(2)*U_standard (whose
entries are exactly integers in {-1,0,1}) gives 4 * objective(U_standard) = 2
in EXACT rational arithmetic -- the pure-Q pin. The unitarity constraints are
NOT homogeneous (a constant -1 term), so they are pinned exactly at U = I
(identity mesh) instead.

------------------------------------------------------------------------------
MEASUREMENT REPORT (M20c Task 4 sizing / decision gate) -- see `measure_sdp`:

    Full U(4), Gram degree 2 :  32 variables; Gram basis 561 monomials
                                (1 + 32 + C(33,2)); Gram is 561x561
                                (157,641 upper-tri entries); ~58,905 distinct
                                identity monomials (degree-<=4 coefficient
                                equalities); 16 unitarity + 12 unambiguity
                                constraints.

    Real-orthogonal (y=0), Gram degree 2 :  16 variables; Gram basis 153
                                monomials (1 + 16 + C(17,2)); Gram 153x153
                                (11,781 upper-tri entries); ~4,845 distinct
                                identity monomials; 10 orthogonality + 12
                                unambiguity constraints.

    Gate threshold: STOP if the Gram basis exceeds ~3000 monomials. Both
    classes are well under it (561 and 153), so the basis-size gate does NOT
    trip.

    SOLVE OUTCOMES (M20c Task 4, degree 2, SCS):
      * Full U(4): SCS did NOT converge within a 520 s wall budget (the
        ~58,905-row identity system + 561x561 PSD cone is too large) -- a
        genuine size / SCS failure.
      * Real-orthogonal (y=0): SCS CONVERGED in ~24 s to numeric bound ~0.5000,
        but `rationalize` could not repair it: the bound is TIGHT (true max is
        exactly 1/2), so the numeric Gram sits on the SOS-cone boundary and its
        rounding (resolution ~1e-6) lands outside the exact constraint module
        (margin ~3e-6) -- the linear repair is inconsistent, at any denominator
        limit. A boundary/rank-deficiency limitation of rounding-then-repair on
        tight problems, not the (already-fixed) bound-rounding bug.

    GOLDEN LANDED (not via the numeric pipeline): the exact certificate in
    `tests/goldens/p3_k0_standard_assignment.json` (bound EXACTLY 1/2, over the
    full U(4) unitary variety) is constructed analytically from the
    probability-conservation identity `sum_all_S Pr[S|B] = 1` (each `Pr` is a
    manifest sum of squares `re^2 + im^2`) and verified by the exact checker
    (`tests/test_p3_certificate_golden.py`). The checker -- not the finder -- is
    the trust boundary, so an analytically-found certificate is as sound as a
    rationalized numeric one. Only 8 of the 16 unitarity multipliers are
    nonzero; the 12 unambiguity multipliers are identically zero (the bound is
    the pure Calsamiglia-Lutkenhaus k=0 ceiling and needs only unitarity).
------------------------------------------------------------------------------
"""

from __future__ import annotations

import itertools
from fractions import Fraction

from empiricist.domain.p3.poly import (
    Poly,
    poly_add,
    poly_scale,
    prob_poly,
    var_x,
    var_y,
)

BELL_LABELS = ("phi+", "phi-", "psi+", "psi-")

# The standard linear-optical BSM's assignment (see `known_schemes.standard_bsm`
# and its golden pin in `tests/test_p3_goldens.py`): each Bell state's set of
# unambiguously-identifying 2-photon detection patterns. phi+/phi- HOM-bunch
# and are mutually ambiguous, so they identify nothing (empty sets).
STANDARD_ASSIGNMENT: dict[str, tuple[tuple[int, ...], ...]] = {
    "phi+": (),
    "phi-": (),
    "psi+": ((1, 1, 0, 0), (0, 0, 1, 1)),
    "psi-": ((1, 0, 0, 1), (0, 1, 1, 0)),
}


def _mono(*indices: int) -> tuple[int, ...]:
    """A sorted monomial from raw variable indices (repeats = powers)."""
    return tuple(sorted(indices))


def unitarity_constraints(m: int) -> list[Poly]:
    """The `U^dag U = I` polynomial constraints for an m-mode interferometer:
    exact degree-2 `Poly`s that vanish EXACTLY on the unitary variety.

    Column-orthonormality (U^dag U = I) fully characterizes unitarity for a
    square U (it implies U U^dag = I), so these constraints alone cut out the
    unitary group. For columns a <= b, (U^dag U)_{ab} = sum_i conj(U[i][a]) U[i][b]:

        a == b (real):   sum_i (x_ia^2 + y_ia^2) - 1 = 0        (m constraints)
        a <  b (real):   sum_i (x_ia x_ib + y_ia y_ib) = 0      (C(m,2))
        a <  b (imag):   sum_i (x_ia y_ib - y_ia x_ib) = 0      (C(m,2))

    Total 2*C(m,2) + m = m^2 real degree-2 constraints (16 for m=4). Verified
    numerically to vanish at `mesh_unitary` outputs by `tests/test_p3_targets.py`.
    """
    constraints: list[Poly] = []
    # Diagonal: column a has unit norm.
    for a in range(m):
        p: Poly = {}
        for i in range(m):
            p = poly_add(p, {_mono(var_x(i, a, m), var_x(i, a, m)): Fraction(1)})
            p = poly_add(p, {_mono(var_y(i, a, m), var_y(i, a, m)): Fraction(1)})
        p = poly_add(p, {(): Fraction(-1)})
        constraints.append(p)
    # Off-diagonal: distinct columns are orthogonal (real and imaginary parts).
    for a in range(m):
        for b in range(a + 1, m):
            re: Poly = {}
            im: Poly = {}
            for i in range(m):
                xa, ya = var_x(i, a, m), var_y(i, a, m)
                xb, yb = var_x(i, b, m), var_y(i, b, m)
                re = poly_add(re, {_mono(xa, xb): Fraction(1)})
                re = poly_add(re, {_mono(ya, yb): Fraction(1)})
                im = poly_add(im, {_mono(xa, yb): Fraction(1)})
                im = poly_add(im, {_mono(ya, xb): Fraction(-1)})
            constraints.append(re)
            constraints.append(im)
    return constraints


def standard_assignment_objective(m: int = 4) -> Poly:
    """The p_avg objective for the standard-BSM assignment, as a single exact
    `Poly`: `(1/4) * sum_B sum_{S in A_B} Pr[S | B]`.

    The `1/4` average and each `Pr[S|B]`'s exact rational scale factor (from
    `prob_poly`) are folded into the coefficients, so the returned polynomial
    IS `p_avg(U)` with no residual scaling. Degree-4 homogeneous (see the
    module docstring); evaluates to exactly 1/2 at the standard BSM.
    """
    obj: Poly = {}
    quarter = Fraction(1, 4)
    for label, pats in STANDARD_ASSIGNMENT.items():
        for pattern in pats:
            poly, scale = prob_poly(m, label, pattern)
            obj = poly_add(obj, poly_scale(poly, scale * quarter))
    return obj


def unambiguity_constraints(m: int = 4) -> list[Poly]:
    """The unambiguity equalities pinning the standard-BSM assignment: for each
    assigned pattern S in A_B, the polynomial `Pr[S | B'] = 0` for every OTHER
    Bell state B' != B (so S identifies B and nothing else).

    Returns the degree-4 `Pr[S|B']` polynomials directly (the `prob_poly`
    `poly` part, dropping the positive rational `scale` -- `Pr = scale * poly`
    with `scale > 0`, so `poly = 0` cuts out exactly the same variety). For the
    standard assignment there are 4 assigned patterns * 3 other states = 12
    constraints; each vanishes EXACTLY at the standard BSM (self-tested).
    """
    constraints: list[Poly] = []
    for label, pats in STANDARD_ASSIGNMENT.items():
        for pattern in pats:
            for other in BELL_LABELS:
                if other == label:
                    continue
                poly, _scale = prob_poly(m, other, pattern)
                constraints.append(poly)
    return constraints


# ---------------------------------------------------------------------------
# Real-orthogonal restriction (y = 0): an honest WEAKER sub-statement, used if
# the full U(4) SDP is impractical (M20c Task 4, step 4). Restricts to the real
# orthogonal group by setting every imaginary variable y_ij to zero and
# remapping the m^2 real variables x_ij to a CONTIGUOUS index space 0..m^2-1
# (required by `solve_sos`, which enumerates monomials over 0..nvars-1).
# ---------------------------------------------------------------------------


def restrict_to_real(poly: Poly) -> Poly:
    """Substitute every y-variable (odd raw index) with 0 and remap each
    x-variable (even raw index `k`) to the contiguous index `k // 2`. Monomials
    containing any y-variable vanish; the rest survive with remapped indices.

    Exact and coefficient-preserving. Applied to the objective it yields the
    real-orthogonal objective; applied to a unitarity constraint it yields the
    orthogonality constraint (the imaginary-part constraints, being pure x*y,
    vanish identically and should be filtered out by the caller)."""
    out: Poly = {}
    for mono, coef in poly.items():
        if any(idx % 2 == 1 for idx in mono):
            continue
        remapped = tuple(sorted(idx // 2 for idx in mono))
        c = out.get(remapped, Fraction(0)) + coef
        if c:
            out[remapped] = c
        else:
            out.pop(remapped, None)
    return out


def real_orthogonal_target(m: int = 4) -> tuple[Poly, list[Poly], tuple[str, ...]]:
    """The real-orthogonal restriction of the full target: `(objective,
    constraints, variables)` over the m^2 contiguous real variables x_ij
    (indices 0..m^2-1, names `x{i}{j}`). Constraints are the non-trivial
    orthogonality rows (m + C(m,2) real ones; the imaginary rows drop) followed
    by the restricted unambiguity polynomials, with any that collapse to the
    zero polynomial filtered out. An honest WEAKER statement than full U(4):
    it bounds p_avg over real orthogonal interferometers only (a subclass that
    still contains the standard BSM, so the 1/2 ceiling is still tight)."""
    objective = restrict_to_real(standard_assignment_objective(m))
    constraints: list[Poly] = []
    for g in unitarity_constraints(m):
        rg = restrict_to_real(g)
        if rg:
            constraints.append(rg)
    for g in unambiguity_constraints(m):
        rg = restrict_to_real(g)
        if rg:
            constraints.append(rg)
    variables = tuple(f"x{i}{j}" for i in range(m) for j in range(m))
    return objective, constraints, variables


# ---------------------------------------------------------------------------
# SDP sizing (the Task-4 decision-gate measurement). Pure combinatorics; no
# cvxpy dependency, mirrors `solve_sos`'s monomial enumeration exactly.
# ---------------------------------------------------------------------------


def _poly_degree(p: Poly) -> int:
    return max((len(mono) for mono in p), default=0)


def _monomials_up_to_degree(nvars: int, degree: int) -> list[tuple[int, ...]]:
    out: list[tuple[int, ...]] = [()]
    for d in range(1, degree + 1):
        out.extend(itertools.combinations_with_replacement(range(nvars), d))
    return out


def measure_sdp(
    objective: Poly,
    constraints: list[Poly],
    variables: tuple[str, ...],
    degree: int,
) -> dict[str, int]:
    """Measure the SDP `solve_sos` would assemble, WITHOUT solving (no cvxpy):
    the Gram basis size, Gram matrix dimension and upper-triangular entry count,
    the number of distinct identity monomials (coefficient-equality rows), the
    total free multiplier variables, and the constraint count. This is the
    Task-4 decision-gate instrument: the gate trips if `gram_basis` exceeds
    ~3000 (or, downstream, if SCS fails to converge)."""
    nvars = len(variables)
    gram_basis = _monomials_up_to_degree(nvars, degree)
    n = len(gram_basis)

    multiplier_bases = [
        _monomials_up_to_degree(nvars, max(2 * degree - _poly_degree(g), 0))
        for g in constraints
    ]

    identity_monos: set[tuple[int, ...]] = set(objective) | {()}
    for a in range(n):
        for b in range(n):
            identity_monos.add(tuple(sorted(gram_basis[a] + gram_basis[b])))
    for g, mb in zip(constraints, multiplier_bases, strict=True):
        for basis_mono in mb:
            for c_mono in g:
                identity_monos.add(tuple(sorted(basis_mono + c_mono)))

    return {
        "nvars": nvars,
        "gram_basis_size": n,
        "gram_upper_tri_entries": n * (n + 1) // 2,
        "n_identity_monomials": len(identity_monos),
        "n_multiplier_vars": sum(len(mb) for mb in multiplier_bases),
        "n_constraints": len(constraints),
    }

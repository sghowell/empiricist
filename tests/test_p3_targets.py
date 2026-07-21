"""Numeric + exact self-tests for the P3 certificate targets (M20c Task 4).

These are the WARRANT that `p3_targets.py` builds the intended polynomials: the
unitarity constraints must vanish at real interferometer unitaries, and the
objective must equal exactly 1/2 at the standard BSM (with its unambiguity
constraints vanishing there). A bug here would let the SDP certify a vacuous or
wrong bound. No cvxpy dependency: these run in the fast suite.
"""

from fractions import Fraction

import numpy as np

from empiricist.certificates.p3_targets import (
    STANDARD_ASSIGNMENT,
    measure_sdp,
    real_orthogonal_target,
    restrict_to_real,
    standard_assignment_objective,
    unambiguity_constraints,
    unitarity_constraints,
)
from empiricist.domain.p3.interferometer import Mesh, mesh_unitary
from empiricist.domain.p3.known_schemes import standard_bsm
from empiricist.domain.p3.poly import eval_poly, var_x, var_y

M = 4


def _float_values(u: np.ndarray, m: int) -> dict[int, float]:
    values: dict[int, float] = {}
    for i in range(m):
        for j in range(m):
            values[var_x(i, j, m)] = float(u[i, j].real)
            values[var_y(i, j, m)] = float(u[i, j].imag)
    return values


def _identity_frac_values(m: int) -> dict[int, Fraction]:
    values: dict[int, Fraction] = {}
    for i in range(m):
        for j in range(m):
            values[var_x(i, j, m)] = Fraction(1) if i == j else Fraction(0)
            values[var_y(i, j, m)] = Fraction(0)
    return values


def _sqrt2_scaled_frac_values(u: np.ndarray, m: int) -> dict[int, Fraction]:
    """Exact `Fraction` values for sqrt(2)*U, asserting each scaled entry is an
    integer (true for the standard BSM, whose entries are all +-1/sqrt(2))."""
    scaled = u * np.sqrt(2)
    values: dict[int, Fraction] = {}
    for i in range(m):
        for j in range(m):
            for part, idx in ((scaled[i, j].real, var_x(i, j, m)),
                              (scaled[i, j].imag, var_y(i, j, m))):
                rounded = round(part)
                assert abs(part - rounded) < 1e-9, (i, j, part)
                values[idx] = Fraction(int(rounded))
    return values


def _random_4mode_mesh(rng: np.random.Generator) -> Mesh:
    els = []
    for _ in range(int(rng.integers(2, 10))):
        i, j = sorted(rng.choice(4, size=2, replace=False).tolist())
        els.append(("bs", i, j, float(rng.uniform(0, np.pi)), float(rng.uniform(0, 2 * np.pi))))
    els.append(("phase", int(rng.integers(0, 4)), float(rng.uniform(0, 2 * np.pi))))
    return Mesh(n_modes=4, elements=els)


# ---------------------------------------------------------------------------
# Unitarity constraints.
# ---------------------------------------------------------------------------


def test_unitarity_constraint_count_and_degree():
    cons = unitarity_constraints(M)
    assert len(cons) == M * M  # 16 for m=4
    for g in cons:
        assert max(len(mono) for mono in g) == 2
        for coef in g.values():
            assert isinstance(coef, Fraction)


def test_unitarity_vanishes_at_identity_exact():
    values = _identity_frac_values(M)
    for g in unitarity_constraints(M):
        val = eval_poly(g, values)
        assert isinstance(val, Fraction)
        assert val == 0


def test_unitarity_vanishes_at_random_meshes_numeric():
    rng = np.random.default_rng(20260720)
    cons = unitarity_constraints(M)
    for _ in range(20):
        u = mesh_unitary(_random_4mode_mesh(rng))
        values = _float_values(u, M)
        for g in cons:
            assert abs(eval_poly(g, values)) < 1e-9


# ---------------------------------------------------------------------------
# Objective.
# ---------------------------------------------------------------------------


def test_objective_is_degree_four_homogeneous_fractions():
    obj = standard_assignment_objective(M)
    assert obj
    degrees = {len(mono) for mono in obj}
    assert degrees == {4}  # homogeneous degree 4
    for coef in obj.values():
        assert isinstance(coef, Fraction)


def test_objective_at_standard_bsm_is_half_numeric():
    u = mesh_unitary(standard_bsm().mesh)
    values = _float_values(u, M)
    assert abs(eval_poly(standard_assignment_objective(M), values) - 0.5) < 1e-10


def test_objective_at_standard_bsm_is_half_exact():
    # Homogeneous degree 4: objective(sqrt2*U) = 4 * objective(U) = 4*(1/2) = 2,
    # computed entirely in exact rational arithmetic on the integer matrix.
    u = mesh_unitary(standard_bsm().mesh)
    values = _sqrt2_scaled_frac_values(u, M)
    scaled = eval_poly(standard_assignment_objective(M), values)
    assert isinstance(scaled, Fraction)
    assert scaled == Fraction(2)
    assert scaled / 4 == Fraction(1, 2)


# ---------------------------------------------------------------------------
# Unambiguity constraints.
# ---------------------------------------------------------------------------


def test_unambiguity_constraint_count_and_degree():
    cons = unambiguity_constraints(M)
    n_assigned = sum(len(pats) for pats in STANDARD_ASSIGNMENT.values())
    assert len(cons) == n_assigned * 3  # 4 assigned patterns * 3 other Bell states
    for g in cons:
        assert max(len(mono) for mono in g) == 4


def test_unambiguity_vanishes_at_standard_bsm_exact():
    u = mesh_unitary(standard_bsm().mesh)
    values = _sqrt2_scaled_frac_values(u, M)
    for g in unambiguity_constraints(M):
        val = eval_poly(g, values)
        assert isinstance(val, Fraction)
        assert val == 0


# ---------------------------------------------------------------------------
# Real-orthogonal restriction.
# ---------------------------------------------------------------------------


def test_restrict_to_real_drops_imaginary_and_remaps():
    # y-variable (odd index) monomial vanishes; x-variable (even) remaps k -> k//2.
    poly = {(var_x(0, 1, M),): Fraction(3), (var_y(0, 1, M),): Fraction(5),
            (var_x(1, 0, M), var_y(2, 2, M)): Fraction(7)}
    out = restrict_to_real(poly)
    assert out == {(var_x(0, 1, M) // 2,): Fraction(3)}


def test_real_orthogonal_target_shapes_and_bound():
    obj, cons, variables = real_orthogonal_target(M)
    assert len(variables) == M * M  # 16 contiguous x-variables
    assert obj
    # All indices are in the contiguous 0..15 range.
    for mono in obj:
        assert all(0 <= idx < M * M for idx in mono)
    for g in cons:
        assert g  # no zero-polynomial constraints survive
        for mono in g:
            assert all(0 <= idx < M * M for idx in mono)
    # 10 orthogonality (m diagonal + C(m,2) off-diag real; imaginary rows drop)
    # + 12 unambiguity, none of which collapse to zero.
    assert len(cons) == (M + M * (M - 1) // 2) + 12

    # The standard BSM is real orthogonal; its objective is still exactly 1/2.
    u = mesh_unitary(standard_bsm().mesh)
    xvals = {i * M + j: Fraction(int(round(u[i, j].real * np.sqrt(2))))
             for i in range(M) for j in range(M)}
    scaled = eval_poly(obj, xvals)
    assert scaled == Fraction(2)  # 4 * (1/2), degree-4 homogeneous


# ---------------------------------------------------------------------------
# SDP sizing (decision-gate instrument).
# ---------------------------------------------------------------------------


def test_measure_sdp_full_u4_sizes():
    obj = standard_assignment_objective(M)
    cons = unitarity_constraints(M) + unambiguity_constraints(M)
    variables = tuple(
        f"{part}{i}{j}" for i in range(M) for j in range(M) for part in ("x", "y")
    )
    info = measure_sdp(obj, cons, variables, degree=2)
    assert info["nvars"] == 32
    assert info["gram_basis_size"] == 1 + 32 + 32 * 33 // 2  # 561
    assert info["n_constraints"] == 16 + 12


def test_measure_sdp_real_orthogonal_sizes():
    obj, cons, variables = real_orthogonal_target(M)
    info = measure_sdp(obj, cons, variables, degree=2)
    assert info["nvars"] == 16
    assert info["gram_basis_size"] == 1 + 16 + 16 * 17 // 2  # 153

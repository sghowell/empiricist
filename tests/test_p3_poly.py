from fractions import Fraction

import numpy as np
import pytest

from empiricist.domain.p3.engine_fock import FockEngine
from empiricist.domain.p3.engine_permanent import PermanentEngine
from empiricist.domain.p3.fock import patterns
from empiricist.domain.p3.interferometer import Mesh, mesh_unitary
from empiricist.domain.p3.known_schemes import standard_bsm
from empiricist.domain.p3.poly import eval_poly, prob_poly, var_x, var_y
from empiricist.domain.p3.scheme import BELL_LABELS, bell_input_states


def _values_for(u: np.ndarray, m: int) -> dict[int, float]:
    values: dict[int, float] = {}
    for i in range(m):
        for j in range(m):
            values[var_x(i, j, m)] = float(u[i, j].real)
            values[var_y(i, j, m)] = float(u[i, j].imag)
    return values


def _random_4mode_mesh(rng: np.random.Generator) -> Mesh:
    n_modes = 4
    els = []
    for _ in range(int(rng.integers(1, 10))):
        i, j = sorted(rng.choice(n_modes, size=2, replace=False).tolist())
        els.append(("bs", i, j, float(rng.uniform(0, np.pi)), float(rng.uniform(0, 2 * np.pi))))
    els.append(("phase", int(rng.integers(0, n_modes)), float(rng.uniform(0, 2 * np.pi))))
    return Mesh(n_modes=n_modes, elements=els)


def _assert_mesh_cross_validates(mesh: Mesh, engine) -> None:
    """The core F3 warrant: for every Bell label and every 2-photon output
    pattern, the polynomial (scaled) must reproduce the engine's probability
    to 1e-10, treating a missing pattern key as probability 0.0."""
    u = mesh_unitary(mesh)
    values = _values_for(u, mesh.n_modes)
    bell_states = bell_input_states(mesh.n_modes, {})
    for label in BELL_LABELS:
        dist = engine.output_distribution(mesh, bell_states[label])
        for pattern in patterns(2, mesh.n_modes):
            poly, scale = prob_poly(mesh.n_modes, label, pattern)
            got = float(scale) * eval_poly(poly, values)
            expected = dist.get(pattern, 0.0)
            assert abs(got - expected) < 1e-10, (label, pattern, got, expected)


def test_coefficients_are_exact_fractions_and_poly_is_degree_four():
    poly, scale = prob_poly(4, "phi+", (2, 0, 0, 0))
    assert isinstance(scale, Fraction)
    assert poly, "expected a non-trivial polynomial for this pattern/Bell pair"
    for mono, coef in poly.items():
        assert isinstance(coef, Fraction)
        assert len(mono) <= 4
    assert max(len(mono) for mono in poly) == 4


def test_cross_validates_against_permanent_engine_standard_bsm_and_random_meshes():
    engine = PermanentEngine()
    _assert_mesh_cross_validates(standard_bsm().mesh, engine)
    rng = np.random.default_rng(20260720)
    for _ in range(20):
        _assert_mesh_cross_validates(_random_4mode_mesh(rng), engine)


def test_cross_validates_against_fock_engine_standard_bsm():
    _assert_mesh_cross_validates(standard_bsm().mesh, FockEngine())


def test_raises_not_implemented_for_three_photon_pattern():
    with pytest.raises(NotImplementedError):
        prob_poly(4, "phi+", (1, 1, 1, 0))


def test_identity_unitary_hand_pin_phi_plus_correlated_pattern():
    """U = identity (empty mesh): Pr[(1,0,1,0) | phi+] = 1/2 exactly."""
    m = 4
    pattern = (1, 0, 1, 0)
    poly, scale = prob_poly(m, "phi+", pattern)

    float_values = {}
    for i in range(m):
        for j in range(m):
            float_values[var_x(i, j, m)] = 1.0 if i == j else 0.0
            float_values[var_y(i, j, m)] = 0.0
    got = scale * eval_poly(poly, float_values)
    assert abs(got - 0.5) < 1e-15

    # Pure-Q path: Fraction-valued evaluation, no floats anywhere.
    frac_values = {}
    for i in range(m):
        for j in range(m):
            frac_values[var_x(i, j, m)] = Fraction(1) if i == j else Fraction(0)
            frac_values[var_y(i, j, m)] = Fraction(0)
    exact = eval_poly(poly, frac_values)
    assert isinstance(exact, Fraction)
    assert scale * exact == Fraction(1, 2)

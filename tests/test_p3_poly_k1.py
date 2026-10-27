"""Exact k=1 Bell amplitudes (M27b Task 2): the input layer of the moment certificates.

The warrant, as for the k=0 `prob_poly` (M20c's F3 discipline): evaluated at random
unitaries, the exact polynomials must reproduce BOTH float engines -- probabilities for every
Bell state and every 3-photon pattern, and the CROSS terms A_B * conj(A_B') too (the moment
identity uses them), recovered from the engines through superposition inputs
(|in_B> + e^{i phi}|in_B'>)/sqrt2 at phi = 0 and pi/2.
"""
from __future__ import annotations

import cmath
import math
from fractions import Fraction

import numpy as np
import pytest

from empiricist.domain.p3.engine_fock import FockEngine
from empiricist.domain.p3.engine_permanent import PermanentEngine
from empiricist.domain.p3.fock import patterns
from empiricist.domain.p3.interferometer import Mesh, mesh_unitary
from empiricist.domain.p3.poly import bell_amp_poly, eval_poly, prob_poly, var_x, var_y
from empiricist.domain.p3.scheme import BELL_LABELS, bell_input_states


def _values_for(u: np.ndarray, m: int) -> dict[int, float]:
    values: dict[int, float] = {}
    for i in range(m):
        for j in range(m):
            values[var_x(i, j, m)] = float(u[i, j].real)
            values[var_y(i, j, m)] = float(u[i, j].imag)
    return values


def _random_mesh(rng: np.random.Generator, m: int) -> Mesh:
    els = []
    for _ in range(int(rng.integers(m, 3 * m))):
        i, j = sorted(rng.choice(m, size=2, replace=False).tolist())
        els.append(("bs", i, j, float(rng.uniform(0, np.pi)), float(rng.uniform(0, 2 * np.pi))))
    for i in range(m):
        els.append(("phase", i, float(rng.uniform(0, 2 * np.pi))))
    return Mesh(n_modes=m, elements=els)


def _amp(m: int, label: str, pattern: tuple[int, ...], values: dict[int, float]) -> complex:
    """The physical amplitude <n|out_B>, rebuilt from the exact pieces."""
    (re, im), scale = bell_amp_poly(m, label, pattern, ancilla_mode=4)
    return complex(eval_poly(re, values), eval_poly(im, values)) * math.sqrt(scale)


def _ancilla(m: int) -> dict[tuple[int, ...], complex]:
    pat = tuple(1 if a == 0 else 0 for a in range(m - 4))
    return {pat: 1.0 + 0.0j}


@pytest.mark.parametrize("m", [5, 6])
@pytest.mark.parametrize("engine", [PermanentEngine(), FockEngine()], ids=["perm", "fock"])
def test_probabilities_cross_validate_against_both_engines(m, engine):
    rng = np.random.default_rng(20261026 + m)
    for _ in range(4 if m == 5 else 2):
        mesh = _random_mesh(rng, m)
        values = _values_for(mesh_unitary(mesh), m)
        states = bell_input_states(m, _ancilla(m))
        for label in BELL_LABELS:
            dist = engine.output_distribution(mesh, states[label])
            for pattern in patterns(3, m):
                got = abs(_amp(m, label, pattern, values)) ** 2
                assert abs(got - dist.get(pattern, 0.0)) < 1e-10, (label, pattern)


def test_cross_terms_cross_validate_through_superposition_inputs():
    """A_B conj(A_B') is not visible in any single Bell distribution; the engines see it in
    Pr[n | (in_B + e^{i phi} in_B')/sqrt2]
        = (|A_B|^2 + |A_B'|^2)/2 + Re(e^{-i phi} A_B conj(A_B'))."""
    m = 5
    rng = np.random.default_rng(77)
    engine = PermanentEngine()
    for _ in range(3):
        mesh = _random_mesh(rng, m)
        values = _values_for(mesh_unitary(mesh), m)
        states = bell_input_states(m, _ancilla(m))
        for b1 in BELL_LABELS:
            for b2 in BELL_LABELS:
                if b1 >= b2:
                    continue
                for phi in (0.0, math.pi / 2):
                    ph = cmath.exp(1j * phi)
                    sup: dict[tuple[int, ...], complex] = {}
                    for pat, a in states[b1].items():
                        sup[pat] = sup.get(pat, 0) + a / math.sqrt(2)
                    for pat, a in states[b2].items():
                        sup[pat] = sup.get(pat, 0) + ph * a / math.sqrt(2)
                    dist = engine.output_distribution(mesh, sup)
                    for pattern in patterns(3, m):
                        a1 = _amp(m, b1, pattern, values)
                        a2 = _amp(m, b2, pattern, values)
                        expected = abs(a1 + ph * a2) ** 2 / 2
                        got = dist.get(pattern, 0.0)
                        assert abs(got - expected) < 1e-10, (b1, b2, phi, pattern)


def test_k0_mode_reproduces_prob_poly_exactly():
    """With ancilla_mode=None the amplitude is the k=0 one: scale*(re^2+im^2) == prob_poly."""
    from empiricist.certificates.core import poly_add, poly_mul, poly_scale

    for pattern in [(1, 1, 0, 0), (2, 0, 0, 0), (0, 1, 1, 0)]:
        for label in BELL_LABELS:
            (re, im), scale = bell_amp_poly(4, label, pattern, ancilla_mode=None)
            p, s = prob_poly(4, label, pattern)
            lhs = poly_scale(poly_add(poly_mul(re, re), poly_mul(im, im)), scale)
            rhs = poly_scale(p, s)
            assert lhs == rhs


def test_scale_is_exact_and_coefficients_are_integers():
    (re, im), scale = bell_amp_poly(5, "psi-", (2, 1, 0, 0, 0), ancilla_mode=4)
    assert scale == Fraction(1, 2 * 2)  # 1 / (2 * n!) with n! = 2
    for p in (re, im):
        for mono, c in p.items():
            assert isinstance(c, Fraction) and c.denominator == 1
            assert len(mono) == 3


def test_rejects_bad_arguments():
    with pytest.raises(ValueError):
        bell_amp_poly(5, "phi+", (1, 1, 1, 0, 0), ancilla_mode=2)  # ancilla on a signal mode
    with pytest.raises(ValueError):
        bell_amp_poly(5, "phi+", (1, 1, 0, 0, 0), ancilla_mode=4)  # 2 photons, k=1 needs 3
    with pytest.raises(ValueError):
        bell_amp_poly(5, "chi", (1, 1, 1, 0, 0), ancilla_mode=4)

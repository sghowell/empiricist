"""M27b Task 3: the one-body unambiguous-discrimination (USD) lemma certificate.

Lemma. For unit alpha, beta in C^2, real s_A, s_B, c, and any real lambda_B, if
    D - Lambda = W W^dagger   with   D = s_A |a><a| (x) I + s_B I (x) |b><b| + c I,
                                     Lambda = sum_B lambda_B |B><B|  (B the four Bell states),
then sum_B lambda_B <= s_A + s_B + 4c.

`core.check_certificate` certifies the algebra; these tests carry the caller's half of the
contract (core.py's docstring): the constraint polynomials vanish EXACTLY on the intended
variety, the objective is the intended functional, the Bell projectors are the repo's Bell
states, and plausible corruptions of the certificate are rejected.
"""
from __future__ import annotations

import json
import math
from dataclasses import replace
from fractions import Fraction

import numpy as np
import pytest

from empiricist.certificates.core import check_certificate, poly_add
from empiricist.certificates.p3_moment import (
    BELL_SQRT2,
    ONE_BODY_USD_DATA,
    one_body_usd_certificate,
    one_body_usd_variables,
)
from empiricist.certificates.verifier import certificate_from_json, certificate_to_json
from empiricist.domain.p3.poly import eval_poly
from empiricist.domain.p3.scheme import BELL_LABELS, bell_input_states


@pytest.fixture(scope="module")
def cert():
    return one_body_usd_certificate()


def _point(rng, *, psd: bool = True):
    """A random point of the intended variety: unit alpha, beta; D - Lambda = W W^dagger."""
    def unit():
        v = rng.normal(size=2) + 1j * rng.normal(size=2)
        return v / np.linalg.norm(v)

    a, b = unit(), unit()
    sA, sB, c = rng.uniform(0, 1, size=3)
    D = (sA * np.kron(np.outer(a, a.conj()), np.eye(2))
         + sB * np.kron(np.eye(2), np.outer(b, b.conj())) + c * np.eye(4))
    bell = np.array(BELL_SQRT2, dtype=float) / math.sqrt(2)
    # Lambda: a random Bell-diagonal matrix scaled to sit below D
    lam = rng.uniform(0, 1, size=4)
    L = sum(lam[k] * np.outer(bell[k], bell[k]) for k in range(4))
    t = 1.0
    while np.linalg.eigvalsh(D - t * L).min() < 0:
        t *= 0.9
    lam = t * lam
    L = t * L
    w, V = np.linalg.eigh(D - L)
    W = V @ np.diag(np.sqrt(np.clip(w, 0, None)))
    names = one_body_usd_variables()
    vals: dict[int, float] = {}
    for idx, name in enumerate(names):
        vals[idx] = _value(name, a, b, sA, sB, c, lam, W)
    return vals, (a, b, sA, sB, c, lam, W)


def _value(name, a, b, sA, sB, c, lam, W):
    part = {"re": lambda z: z.real, "im": lambda z: z.imag}
    if name.startswith("alpha"):
        j, p = int(name[5]), name.split("_")[1]
        return float(part[p](a[j]))
    if name.startswith("beta"):
        j, p = int(name[4]), name.split("_")[1]
        return float(part[p](b[j]))
    if name == "sA":
        return float(sA)
    if name == "sB":
        return float(sB)
    if name == "c":
        return float(c)
    if name.startswith("lam"):
        return float(lam[BELL_LABELS.index(name[4:])])
    if name.startswith("W"):
        r, s, p = int(name[1]), int(name[2]), name.split("_")[1]
        return float(part[p](W[r, s]))
    raise AssertionError(name)


def test_certificate_passes_the_exact_checker(cert):
    res = check_certificate(cert)
    assert res.ok, res
    assert cert.bound == 0


def test_pinned_json_matches_the_builder(cert):
    stored = certificate_from_json(json.loads(ONE_BODY_USD_DATA.read_text()))
    assert certificate_to_json(stored) == certificate_to_json(cert)


def test_bell_projectors_are_the_repo_bell_states():
    """BELL_SQRT2[k] / sqrt2 is the k-th label's dual-rail state read as two qubits
    (rail 0/1 of qubit A -> |0>/|1>, rail 2/3 of qubit B -> |0>/|1>)."""
    states = bell_input_states(4, {})
    for k, label in enumerate(BELL_LABELS):
        vec = np.zeros(4, dtype=complex)
        for occ, amp in states[label].items():
            qa = 0 if occ[0] == 1 else 1
            qb = 0 if occ[2] == 1 else 1
            vec[2 * qa + qb] = amp
        assert np.allclose(vec, np.array(BELL_SQRT2[k], dtype=float) / math.sqrt(2))


def test_constraints_vanish_on_the_intended_variety(cert):
    rng = np.random.default_rng(5)
    for _ in range(20):
        vals, _ = _point(rng)
        for g in cert.constraints:
            assert abs(eval_poly(g, vals)) < 1e-10


def test_objective_is_sum_lambda_minus_bound_functional(cert):
    rng = np.random.default_rng(6)
    for _ in range(5):
        vals, (a, b, sA, sB, c, lam, W) = _point(rng)
        assert abs(eval_poly(cert.objective, vals) - (lam.sum() - sA - sB - 4 * c)) < 1e-12


def test_constraints_detect_a_point_off_the_variety(cert):
    """A non-unit alpha, or W W^dagger != D - Lambda, makes some constraint non-zero."""
    rng = np.random.default_rng(7)
    vals, _ = _point(rng)
    names = one_body_usd_variables()
    bumped = dict(vals)
    bumped[names.index("alpha0_re")] += 0.1
    assert max(abs(eval_poly(g, bumped)) for g in cert.constraints) > 1e-3
    bumped = dict(vals)
    bumped[names.index("W01_im")] += 0.1
    assert max(abs(eval_poly(g, bumped)) for g in cert.constraints) > 1e-3


def test_bound_is_tight_at_the_aligned_configuration():
    """alpha = beta = |0>, s_A = s_B = s: Lambda = diag(c, c, c+s, c+s) sits below D with
    sum = 2s + 4c = s_A + s_B + 4c -- the lemma cannot be improved."""
    s, c = 0.3, 0.2
    a = np.array([1, 0], dtype=complex)
    P0 = np.outer(a, a)
    D = s * np.kron(P0, np.eye(2)) + s * np.kron(np.eye(2), P0) + c * np.eye(4)
    bell = np.array(BELL_SQRT2, dtype=float) / math.sqrt(2)
    lam = [c, c, c + s, c + s]  # phi+, phi-, psi+, psi-
    L = sum(lam[k] * np.outer(bell[k], bell[k]) for k in range(4))
    assert np.linalg.eigvalsh(D - L).min() > -1e-12
    assert math.isclose(sum(lam), 2 * s + 4 * c)


def test_mutations_are_rejected(cert):
    # bound functional weakened on the ancilla term: 4c -> 3c
    names = one_body_usd_variables()
    ic = names.index("c")
    obj = dict(cert.objective)
    obj[(ic,)] = Fraction(-3)
    assert not check_certificate(replace(cert, objective=obj)).ok
    # a constraint dropped (with its multiplier)
    assert not check_certificate(
        replace(cert, constraints=cert.constraints[1:], multipliers=cert.multipliers[1:])
    ).ok
    # a multiplier perturbed
    mult = list(cert.multipliers)
    mult[3] = poly_add(mult[3], {(): Fraction(1, 7)})
    assert not check_certificate(replace(cert, multipliers=tuple(mult))).ok


def test_non_maximally_entangled_projector_breaks_the_identity():
    """The lemma uses only that each |B> has maximally mixed marginals; replacing phi+ by
    the product state |00> must break the certificate's identity."""
    good = one_body_usd_certificate()
    assert check_certificate(good).ok
    projectors = [
        [[Fraction(u * v, 2) for v in vec] for u in vec] for vec in BELL_SQRT2
    ]
    projectors[0] = [[Fraction(int(r == c == 0)) for c in range(4)] for r in range(4)]
    cert_bad = one_body_usd_certificate(bell_projectors=projectors)
    assert not check_certificate(cert_bad).ok

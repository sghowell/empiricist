"""M27b Task 4: the exact moment-bound checker (the trust side of the instance claims).

The checker PASSes a payload {k, m, claimed_p_avg_bound, lemma_certificate} iff
  (a) the lemma certificate passes core.check_certificate and IS the canonical one-body USD
      lemma (same variables, objective, constraints, bound);
  (b) for every output mode i and Bell pair (B, B') the two polynomial identities hold:
      (I1) sum_n n_i A_B(n) conj(A_B'(n)) == sum_{j,l} U_ij conj(U_il) H_jl^{BB'}(U^dag U)
      (I2) sum_{j,l} U_ij conj(U_il) H_jl^{BB'}(I) == <B'| O_A(i)(x)I + I(x)O_B(i) + c_i I |B>;
  (c) claimed_p_avg_bound >= (k + 1)/(k + 2).
"""
from __future__ import annotations

import json
import math
from dataclasses import replace
from fractions import Fraction

import numpy as np
import pytest

from empiricist.certificates.core import SOSCertificate
from empiricist.certificates.p3_moment import ONE_BODY_USD_DATA, one_body_usd_certificate
from empiricist.certificates.p3_moment_check import (
    MomentCheck,
    check_moment_bound,
    moment_identities,
    one_body_matrix,
)
from empiricist.certificates.verifier import certificate_to_json
from empiricist.domain.p3.poly import eval_poly, var_x, var_y


def _payload(k: int, m: int, bound: str, lemma=None) -> dict:
    return {
        "checker": "p3_moment_bound",
        "k": k,
        "m": m,
        "claimed_p_avg_bound": bound,
        "lemma_certificate": lemma
        if lemma is not None
        else json.loads(ONE_BODY_USD_DATA.read_text()),
    }


@pytest.fixture(scope="module")
def k1m5() -> MomentCheck:
    return moment_identities(1, 5)


def test_identities_hold_at_k0_m4_and_m5():
    res = moment_identities(0, 4)
    assert res.ok, res.detail
    assert res.n_identities == 4 * 16
    res = moment_identities(0, 5)
    assert res.ok, res.detail
    assert res.n_identities == 5 * 16


@pytest.mark.slow
def test_identities_hold_at_k1_m6():
    res = moment_identities(1, 6)
    assert res.ok, res.detail
    assert res.n_identities == 6 * 16


@pytest.mark.slow
def test_identities_hold_at_k1_m5(k1m5):
    assert k1m5.ok, k1m5.detail
    assert k1m5.n_identities == 5 * 16


def test_the_one_body_matrix_matches_the_engines_numerically():
    """Evaluate the (I2) right-hand side at a random unitary and compare with the Gram matrix
    of the conditional states built from float amplitudes (the moment identity, numerically;
    the exact identity is the slow test above)."""
    from empiricist.domain.p3.engine_permanent import _permanent, _submatrix
    from empiricist.domain.p3.fock import factorial_prod, patterns
    from empiricist.domain.p3.scheme import BELL_LABELS, bell_input_states

    m = 5
    rng = np.random.default_rng(3)
    z = rng.normal(size=(m, m)) + 1j * rng.normal(size=(m, m))
    q, r = np.linalg.qr(z)
    u = q * (np.diag(r) / np.abs(np.diag(r)))
    values = {}
    for i in range(m):
        for j in range(m):
            values[var_x(i, j, m)] = float(u[i, j].real)
            values[var_y(i, j, m)] = float(u[i, j].imag)
    states = bell_input_states(m, {(1,): 1.0})
    amps = {}
    for b in BELL_LABELS:
        for s in patterns(3, m):
            a = 0j
            for t, at in states[b].items():
                a += at * _permanent(_submatrix(u, s, t)) / math.sqrt(factorial_prod(s))
            amps[b, s] = a
    for i in range(m):
        for bi, b in enumerate(BELL_LABELS):
            for bpi, bp in enumerate(BELL_LABELS):
                want = sum(s[i] * amps[b, s] * np.conj(amps[bp, s]) for s in patterns(3, m))
                re, im = one_body_matrix(i, bi, bpi, 1, m)
                got = complex(eval_poly(re, values), eval_poly(im, values))
                assert abs(got - want) < 1e-10, (i, b, bp)


@pytest.mark.slow
def test_bound_check_passes_at_two_thirds_for_k1_m5():
    res = check_moment_bound(_payload(1, 5, "2/3"))
    assert res.ok, res.detail
    assert res.bound == Fraction(2, 3)


def test_bound_check_passes_at_one_half_for_k0_m4():
    res = check_moment_bound(_payload(0, 4, "1/2"))
    assert res.ok, res.detail


def test_a_claimed_bound_below_the_theorem_fails():
    res = check_moment_bound(_payload(1, 5, "13/20"))
    assert not res.ok and res.failure == "bound"


def test_a_corrupted_lemma_certificate_fails():
    lemma = json.loads(ONE_BODY_USD_DATA.read_text())
    lemma["bound"] = "-1"
    res = check_moment_bound(_payload(1, 5, "2/3", lemma))
    assert not res.ok and res.failure == "lemma"


def test_a_valid_certificate_of_a_different_statement_fails():
    tiny = SOSCertificate(
        statement="-x0^2 <= 0", variables=("x0",), objective={(0, 0): Fraction(-1)},
        bound=Fraction(0), constraints=(), multipliers=(), gram_basis=((0,),),
        gram=((Fraction(1),),),
    )
    res = check_moment_bound(_payload(1, 5, "2/3", certificate_to_json(tiny)))
    assert not res.ok and res.failure == "lemma"


def test_a_weakened_lemma_statement_fails_even_if_it_checks():
    """A certificate for sum lambda <= s_A + s_B + 5c is TRUE (weaker) and would pass the
    checker, but it is not the canonical lemma, so the bound derivation must refuse it."""
    cert = one_body_usd_certificate()
    names = cert.variables
    ic = names.index("c")
    obj = dict(cert.objective)
    obj[(ic,)] = Fraction(-5)
    weakened = certificate_to_json(replace(cert, objective=obj))
    res = check_moment_bound(_payload(1, 5, "2/3", weakened))
    assert not res.ok and res.failure == "lemma"


def test_unsupported_sizes_and_malformed_payloads_fail_cleanly():
    assert check_moment_bound(_payload(2, 8, "3/4")).failure == "shape"
    assert check_moment_bound(_payload(1, 9, "2/3")).failure == "shape"
    assert check_moment_bound({"k": 1}).failure == "shape"
    assert check_moment_bound(None).failure == "shape"
    assert check_moment_bound(_payload(1, 5, 0.6667)).failure == "shape"  # float bound refused


@pytest.mark.slow
def test_a_dropped_ancilla_term_breaks_identity_I2():
    """With the ancilla's photon number omitted from D_i the identities must fail -- the
    one-body matrix is genuinely S_i + c_i I, and the checker sees the difference."""
    res = moment_identities(1, 5, _drop_ancilla_term=True)
    assert not res.ok

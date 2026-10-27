"""The moment bound is tight row by row on the standard BSM (k=0) and on Grice (k=2).

The theorem's chain (docs/science/2026-10-26-p3-moment-bounds.md): for every output mode i,
tr Lambda_i = sum_{assigned n} n_i Pr[n | f(n)] <= s_A(i) + s_B(i) + 4 c_i, and summing gives
(k + 2) sum_B p_B <= 4 + 4k. On both known optimal schemes every row is an equality, so the
bound (k + 1)/(k + 2) is attained at k = 0 and k = 2. Float engines (both), tolerance 1e-9.
"""
from __future__ import annotations

import numpy as np
import pytest

from empiricist.domain.p3.engine_fock import FockEngine
from empiricist.domain.p3.engine_permanent import PermanentEngine
from empiricist.domain.p3.interferometer import mesh_unitary
from empiricist.domain.p3.known_schemes import grice_boosted_bsm, standard_bsm
from empiricist.domain.p3.scheme import BELL_LABELS, bell_input_states, derive_assignment


def _ancilla_photon_numbers(scheme, u: np.ndarray) -> np.ndarray:
    """c_i = <A| Gamma(U)^dag N_i Gamma(U) |A> = sum_{j,l} conj(U_ij) U_il <A|a_j^dag a_l|A>."""
    m = scheme.n_modes
    rho = np.zeros((m, m), dtype=complex)  # one-body density matrix of the ancilla
    anc = scheme.ancilla or {}
    for pat, amp in anc.items():
        full = (0, 0, 0, 0, *pat)
        for j in range(m):
            for ll in range(m):
                if full[ll] == 0:
                    continue
                # a_j^dag a_l |full>
                q = list(full)
                c = np.sqrt(q[ll])
                q[ll] -= 1
                c *= np.sqrt(q[j] + 1)
                q[j] += 1
                q = tuple(q)
                for pat2, amp2 in anc.items():
                    if (0, 0, 0, 0, *pat2) == q:
                        rho[j, ll] += np.conj(amp2) * c * amp
    return np.real(np.einsum("ij,il,jl->i", np.conj(u), u, rho))


@pytest.mark.parametrize("engine", [PermanentEngine(), FockEngine()], ids=["perm", "fock"])
@pytest.mark.parametrize("make, k, total", [(standard_bsm, 0, 2.0), (grice_boosted_bsm, 2, 3.0)],
                         ids=["standard", "grice"])
def test_every_row_is_tight(engine, make, k, total):
    scheme = make()
    m = scheme.n_modes
    u = mesh_unitary(scheme.mesh)
    states = bell_input_states(m, scheme.ancilla)
    dists = {b: engine.output_distribution(scheme.mesh, states[b]) for b in BELL_LABELS}
    assignment = derive_assignment(dists)
    succ = sum(dists[b].get(n, 0.0) for n, b in assignment.items())
    assert abs(succ - total) < 1e-9
    assert abs(succ - 4 * (k + 1) / (k + 2)) < 1e-9          # the bound is attained
    c = _ancilla_photon_numbers(scheme, u)
    assert abs(c.sum() - k) < 1e-9
    for i in range(m):
        tr_lambda = sum(n[i] * dists[b].get(n, 0.0) for n, b in assignment.items())
        s_a = abs(u[i, 0]) ** 2 + abs(u[i, 1]) ** 2
        s_b = abs(u[i, 2]) ** 2 + abs(u[i, 3]) ** 2
        assert abs(tr_lambda - (s_a + s_b + 4 * c[i])) < 1e-9, (i, tr_lambda)

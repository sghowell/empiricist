"""The P3 deterministic tier: fast evaluator, surrogate, exact lift, optimiser."""
from __future__ import annotations

from fractions import Fraction
from math import pi

import numpy as np
import pytest

from empiricist.domain.p3.engine_permanent import PermanentEngine
from empiricist.domain.p3.exact import Alg, exact_report, witness_from_json
from empiricist.domain.p3.interferometer import mesh_unitary
from empiricist.domain.p3.known_schemes import grice_boosted_bsm, standard_bsm
from empiricist.domain.p3.optimize import (
    FastEvaluator,
    MeshTopology,
    absorb_single_photon_ancilla,
    ancilla_basis,
    ancilla_from_params,
    batched_permanents,
    gauge_fix_to_lattice,
    n_params,
    optimize_scheme,
    params_to_scheme,
    scheme_to_json,
    surrogate,
    to_exact_witness,
    unitary_from_params,
)
from empiricist.domain.p3.scheme import BELL_LABELS, evaluate_scheme
from empiricist.ledger.db import Ledger
from empiricist.search.p3_screen import screen_scheme

SHARP = (0.3, 0.1, 0.03, 0.01, 1e-3, 1e-4, 1e-5)


def test_universal_topology_shape():
    t = MeshTopology.universal(5)
    assert t.n_modes == 5 and len(t.pairs) == 10 and t.n_mesh_params == 20
    assert all(j == i + 1 for i, j in t.pairs)
    with pytest.raises(ValueError):
        MeshTopology.universal(1)


def test_params_to_scheme_round_trips_through_the_mesh_unitary():
    rng = np.random.default_rng(0)
    for k, m in ((0, 4), (1, 5), (2, 6)):
        topo = MeshTopology.universal(m)
        x = rng.uniform(0, 2 * pi, n_params(k, m, topo))
        scheme = params_to_scheme(k, m, x, topo)
        assert np.allclose(mesh_unitary(scheme.mesh), unitary_from_params(topo, x))
        anc = ancilla_from_params(k, m, topo, x)
        assert abs(np.linalg.norm(anc) - 1) < 1e-12
        assert screen_scheme(scheme_to_json(scheme)) == scheme


def test_batched_permanents_match_the_engine_formula():
    rng = np.random.default_rng(1)
    from empiricist.domain.p3.engine_permanent import _permanent

    mats = rng.normal(size=(7, 3, 3)) + 1j * rng.normal(size=(7, 3, 3))
    batch = batched_permanents(mats)
    for i in range(7):
        assert abs(batch[i] - _permanent(mats[i])) < 1e-12
    assert batched_permanents(np.zeros((2, 0, 0))).tolist() == [1, 1]


def test_fast_evaluator_agrees_with_engine_a():
    rng = np.random.default_rng(2)
    for k, m in ((0, 4), (1, 5), (1, 7), (2, 6)):
        topo = MeshTopology.universal(m)
        x = np.concatenate([rng.uniform(0, 2 * pi, topo.n_mesh_params),
                            rng.normal(size=n_params(k, m, topo) - topo.n_mesh_params)])
        ev = FastEvaluator(k, m)
        P = ev.probabilities(unitary_from_params(topo, x), ancilla_from_params(k, m, topo, x))
        rep = evaluate_scheme(params_to_scheme(k, m, x, topo), PermanentEngine())
        for b_i, b in enumerate(BELL_LABELS):
            for s_i, s in enumerate(ev.out_patterns):
                assert abs(P[s_i, b_i] - rep.distributions[b].get(s, 0.0)) < 1e-10
        assert np.allclose(P.sum(axis=0), 1.0)


def test_surrogate_scores_a_leakage_free_scheme_exactly():
    for scheme, p_avg, p_min in ((standard_bsm(), 0.5, 0.0), (grice_boosted_bsm(), 0.75, 0.5)):
        k, m = scheme.n_ancilla_photons, scheme.n_modes
        ev = FastEvaluator(k, m)
        anc = np.array([scheme.ancilla.get(p, 0.0) for p in ancilla_basis(k, m)])
        if k == 0:
            anc = np.ones(1)
        P = ev.probabilities(mesh_unitary(scheme.mesh), anc)
        # Ambiguous patterns are gated by exp(-r/tau): they vanish as tau -> 0, so
        # the surrogate equals the exact assignment metric at small tau and only
        # approximates it at large tau.
        assert surrogate(P, target="p_avg", tau=1e-5) == pytest.approx(p_avg, abs=1e-9)
        assert surrogate(P, target="p_avg", tau=0.3) == pytest.approx(p_avg, abs=0.05)
        assert surrogate(P, target="p_min", tau=1e-5) == pytest.approx(p_min, abs=1e-4)
        assert surrogate(P, target="p_min", tau=1e-5, shaping="log") <= 0.0
    with pytest.raises(ValueError):
        surrogate(np.ones((2, 4)), target="nope", tau=0.1)


def test_gauge_fix_puts_a_rotated_grice_back_on_the_lattice():
    u = mesh_unitary(grice_boosted_bsm().mesh)
    rng = np.random.default_rng(3)
    rotated = u * np.exp(1j * rng.uniform(0, 2 * pi, 8))[:, None]      # row phases
    rotated[:, [0, 1]] *= np.exp(1j * 0.7)                              # qubit A phase
    rotated[:, [2, 3]] *= np.exp(1j * 2.1)                              # qubit B phase
    fixed = gauge_fix_to_lattice(rotated[:, :4], [[0, 1], [2, 3]], seed=0)
    ang = np.angle(fixed[np.abs(fixed) > 1e-9]) / (pi / 12)
    assert np.allclose(ang, np.round(ang), atol=1e-6)


def test_exact_lift_of_lattice_meshes_and_absorbed_ancilla():
    w = to_exact_witness(grice_boosted_bsm())
    assert w is not None and exact_report(w).p_avg == Alg.rational(Fraction(3, 4))
    # k=1: a single-photon ancilla spread over two modes absorbs into one column.
    from empiricist.domain.p3.interferometer import Mesh
    from empiricist.domain.p3.scheme import BellScheme

    s = BellScheme(n_modes=6, n_ancilla_photons=1,
                   ancilla={(1, 0): 1 / np.sqrt(2), (0, 1): 1 / np.sqrt(2)},
                   mesh=Mesh(n_modes=6, elements=(("bs", 0, 2, pi / 4, 0), ("bs", 1, 3, pi / 4, 0),
                                                 ("bs", 3, 4, pi / 4, 0))))
    u = mesh_unitary(s.mesh)
    v, anc = absorb_single_photon_ancilla(u, np.array([1 / np.sqrt(2), 1 / np.sqrt(2)]), 1)
    assert v.shape == (6, 5) and anc.tolist() == [1.0 + 0j]
    w = to_exact_witness(s)
    assert w is not None and w.n_in in (5, 6)
    fl = evaluate_scheme(s, PermanentEngine())
    ex = exact_report(w)
    for b in BELL_LABELS:
        assert abs(ex.success[b].to_float() - fl.success_by_state[b]) < 1e-12


def test_k0_optimiser_recovers_the_standard_bsm_exactly(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    try:
        res = optimize_scheme(0, 4, target="p_avg", restarts=3, seed=0, max_iter=150,
                              tau_schedule=SHARP, ledger=lg)
        best = res[0]
        assert best.exact is not None and best.exact.p_avg == Alg.rational(Fraction(1, 2))
        assert best.metric("p_avg") == pytest.approx(0.5)
        runs = lg.conn.execute("select move, seed from runs").fetchall()
        assert [tuple(r) for r in runs] == [("OPTIMIZE", 0)]
        w = witness_from_json(best.witness_json)
        assert w.n_in == 4 and w.n_ancilla_photons == 0
    finally:
        lg.close()


def test_k0_p_min_is_zero_as_the_theorem_says():
    res = optimize_scheme(0, 4, target="p_min", restarts=2, seed=1, max_iter=100,
                          tau_schedule=SHARP)
    assert all(r.metric("p_min") == pytest.approx(0.0, abs=1e-9) for r in res)


@pytest.mark.slow
def test_k1_m5_p_min_finds_an_exact_witness_above_one_sixteenth():
    res = optimize_scheme(1, 5, target="p_min", restarts=8, seed=0, max_iter=300,
                          tau_schedule=SHARP)
    best = res[0]
    assert best.metric("p_min") >= 1 / 16 - 1e-9
    assert best.exact is not None and best.exact.all_identified
    assert best.exact.p_min >= Alg.rational(Fraction(1, 16))


def test_optimize_rejects_bad_arguments():
    with pytest.raises(ValueError):
        optimize_scheme(0, 4, target="p_max")
    with pytest.raises(ValueError):
        optimize_scheme(0, 4, target="p_avg", restarts=0)

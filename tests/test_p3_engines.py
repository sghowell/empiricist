import numpy as np

from empiricist.domain.p3.interferometer import Mesh, mesh_unitary


def test_engines_reject_noninteger_occupations():
    import pytest

    from empiricist.domain.p3.engine_fock import FockEngine
    from empiricist.domain.p3.engine_permanent import PermanentEngine
    m = Mesh(n_modes=2, elements=[("phase", 0, 0.7)])
    for eng in (PermanentEngine(), FockEngine()):
        with pytest.raises(ValueError):
            eng.output_distribution(m, {(2.0, 0.0): 1.0})


def test_single_bs_unitary():
    # Convention: a†_0 -> c a†_0 + s a†_1, a†_1 -> -s a†_0 + c a†_1 (phi = 0);
    # columns of U are the images of the input modes.
    m = Mesh(n_modes=2, elements=[("bs", 0, 1, np.pi / 4, 0.0)])
    u = mesh_unitary(m)
    c = 1 / np.sqrt(2)
    assert np.allclose(u, np.array([[c, -c], [c, c]]), atol=1e-12)


def test_mesh_unitary_is_unitary_random():
    rng = np.random.default_rng(0)
    for _ in range(20):
        n = int(rng.integers(2, 9))
        els = []
        for _ in range(int(rng.integers(1, 12))):
            i, j = sorted(rng.choice(n, size=2, replace=False).tolist())
            els.append(("bs", i, j, float(rng.uniform(0, np.pi)), float(rng.uniform(0, 2 * np.pi))))
        els.append(("phase", int(rng.integers(0, n)), float(rng.uniform(0, 2 * np.pi)), 0.0, 0.0))
        u = mesh_unitary(Mesh(n_modes=n, elements=els))
        assert np.allclose(u @ u.conj().T, np.eye(n), atol=1e-10)


def test_mesh_rejects_degenerate_and_out_of_range():
    import pytest
    with pytest.raises(ValueError):
        Mesh(n_modes=3, elements=[("bs", 1, 1, 0.3, 0.0)])
    with pytest.raises(ValueError):
        Mesh(n_modes=3, elements=[("bs", 0, -1, 0.3, 0.0)])
    with pytest.raises(ValueError):
        Mesh(n_modes=2, elements=[("bs", 0, 5, 0.3, 0.0)])
    with pytest.raises(ValueError):
        Mesh(n_modes=2, elements=[("spin", 0, 1, 0.3, 0.0)])


def test_mesh_rejects_nonintegral_and_nonfinite():
    import math

    import pytest
    with pytest.raises(ValueError):
        Mesh(n_modes=3, elements=[("bs", 0.7, 1.9, 0.3, 0.0)])
    with pytest.raises(ValueError):
        Mesh(n_modes=3, elements=[("phase", 1.9, 0.5)])
    with pytest.raises(ValueError):
        Mesh(n_modes=2, elements=[("bs", 0, 1, float("nan"), 0.0)])
    with pytest.raises(ValueError):
        Mesh(n_modes=2, elements=[("bs", 0, 1, 0.3, math.inf)])
    with pytest.raises(ValueError):
        Mesh(n_modes=2, elements=[("phase", 0, float("nan"))])
    with pytest.raises(ValueError):
        Mesh(n_modes=2, elements=[("phase", 0, 0.5, 7.7, 8.8)])


def test_mesh_is_immutable_and_hashable():
    m = Mesh(n_modes=2, elements=[("bs", 0, 1, 0.3, 0.1)])
    assert isinstance(m.elements, tuple)
    assert isinstance(hash(m), int)


def test_composition_order_pinned():
    # bs then phase(0, pi/2): U = diag(i, 1) @ [[c,-c],[c,c]] = [[ic, -ic], [c, c]]
    # (the reversed composition gives [[ic, -c], [ic... ]] -- distinct)
    c = 1 / np.sqrt(2)
    m = Mesh(n_modes=2, elements=[("bs", 0, 1, np.pi / 4, 0.0), ("phase", 0, np.pi / 2)])
    u = mesh_unitary(m)
    expected = np.array([[1j * c, -1j * c], [c, c]])
    assert np.allclose(u, expected, atol=1e-12)


def test_hom_dip_engine_a():
    from empiricist.domain.p3.engine_permanent import PermanentEngine
    m = Mesh(n_modes=2, elements=[("bs", 0, 1, np.pi / 4, 0.0)])
    eng = PermanentEngine()
    dist = eng.output_distribution(m, {(1, 1): 1.0})
    assert abs(dist.get((1, 1), 0.0)) < 1e-12          # HOM: no coincidences
    assert abs(dist[(2, 0)] - 0.5) < 1e-12
    assert abs(dist[(0, 2)] - 0.5) < 1e-12
    assert abs(sum(dist.values()) - 1.0) < 1e-12


def test_superposed_input_engine_a():
    from empiricist.domain.p3.engine_permanent import PermanentEngine
    m = Mesh(n_modes=2, elements=[])
    eng = PermanentEngine()
    amp = 1 / np.sqrt(2)
    dist = eng.output_distribution(m, {(1, 0): amp, (0, 1): amp})
    assert abs(dist[(1, 0)] - 0.5) < 1e-12 and abs(dist[(0, 1)] - 0.5) < 1e-12


def test_engine_a_rejects_malformed_inputs():
    import pytest

    from empiricist.domain.p3.engine_permanent import PermanentEngine
    eng = PermanentEngine()
    m2 = Mesh(n_modes=2, elements=[])
    with pytest.raises(ValueError):
        eng.output_distribution(m2, {})
    with pytest.raises(ValueError):
        eng.output_distribution(m2, {(1, 1, 0): 1.0})
    with pytest.raises(ValueError):
        eng.output_distribution(Mesh(n_modes=3, elements=[]), {(1, 1): 1.0})
    with pytest.raises(ValueError):
        eng.output_distribution(m2, {(1, -1): 1.0})
    with pytest.raises(ValueError):
        eng.output_distribution(m2, {(1, 1): 0.5, (2, 0): 0.5, (1, 0): 0.5})  # mixed photon number


def test_engine_a_vacuum_and_multiphoton():
    from empiricist.domain.p3.engine_permanent import PermanentEngine
    eng = PermanentEngine()
    # vacuum passes through
    d0 = eng.output_distribution(Mesh(n_modes=3, elements=[]), {(0, 0, 0): 1.0})
    assert d0 == {(0, 0, 0): 1.0}
    # |2,0> through a balanced BS: textbook 1/4, 1/2, 1/4
    mbs = Mesh(n_modes=2, elements=[("bs", 0, 1, np.pi / 4, 0.0)])
    d2 = eng.output_distribution(mbs, {(2, 0): 1.0})
    assert abs(d2[(2, 0)] - 0.25) < 1e-12
    assert abs(d2[(1, 1)] - 0.5) < 1e-12
    assert abs(d2[(0, 2)] - 0.25) < 1e-12


def test_hom_dip_engine_b():
    from empiricist.domain.p3.engine_fock import FockEngine
    m = Mesh(n_modes=2, elements=[("bs", 0, 1, np.pi / 4, 0.0)])
    dist = FockEngine().output_distribution(m, {(1, 1): 1.0})
    assert abs(dist.get((1, 1), 0.0)) < 1e-12
    assert abs(dist[(2, 0)] - 0.5) < 1e-12
    assert abs(dist[(0, 2)] - 0.5) < 1e-12


def test_engines_agree_fuzz():
    from empiricist.domain.p3.engine_fock import FockEngine
    from empiricist.domain.p3.engine_permanent import PermanentEngine
    from empiricist.domain.p3.fock import patterns
    rng = np.random.default_rng(7)
    for trial in range(30):
        n_modes = int(rng.integers(2, 7))
        n_photons = int(rng.integers(1, 4))
        els = []
        for _ in range(int(rng.integers(1, 10))):
            i, j = sorted(rng.choice(n_modes, size=2, replace=False).tolist())
            els.append(("bs", i, j, float(rng.uniform(0, np.pi)), float(rng.uniform(0, 2 * np.pi))))
        if rng.random() < 0.5:
            els.append(("phase", int(rng.integers(0, n_modes)), float(rng.uniform(0, 2 * np.pi))))
        mesh = Mesh(n_modes=n_modes, elements=els)
        basis = patterns(n_photons, n_modes)
        amps = rng.normal(size=len(basis)) + 1j * rng.normal(size=len(basis))
        amps /= np.linalg.norm(amps)
        state = {b: complex(a) for b, a in zip(basis, amps)}  # noqa: B905 (verbatim spec)
        da = PermanentEngine().output_distribution(mesh, state)
        db = FockEngine().output_distribution(mesh, state)
        keys = set(da) | set(db)
        for k in keys:
            assert abs(da.get(k, 0.0) - db.get(k, 0.0)) < 1e-8, (trial, k)
        assert abs(sum(da.values()) - 1.0) < 1e-9

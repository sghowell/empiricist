import numpy as np

from empiricist.domain.p3.interferometer import Mesh, mesh_unitary


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

import numpy as np

from empiricist.domain.p3.engine_permanent import PermanentEngine
from empiricist.domain.p3.interferometer import Mesh
from empiricist.domain.p3.scheme import (
    BELL_LABELS,
    BellScheme,
    bell_input_states,
    evaluate_scheme,
)


def test_bell_states_are_normalized_two_photon():
    for _label, state in bell_input_states(n_modes=4, ancilla={}).items():
        assert abs(sum(abs(a) ** 2 for a in state.values()) - 1.0) < 1e-12
        assert all(sum(p) == 2 for p in state)


def test_standard_bsm_success_vector():
    # 50:50 BS between corresponding rails: identifies Psi+ and Psi- with certainty,
    # Phi+ / Phi- are mutually ambiguous. Per-B success = (0, 0, 1, 1); avg 1/2; min 0.
    scheme = BellScheme(
        n_modes=4, n_ancilla_photons=0, ancilla={},
        mesh=Mesh(n_modes=4, elements=[("bs", 0, 2, np.pi / 4, 0.0),
                                       ("bs", 1, 3, np.pi / 4, 0.0)]),
    )
    report = evaluate_scheme(scheme, PermanentEngine())
    per_b = report.success_by_state
    assert abs(per_b["phi+"]) < 1e-10 and abs(per_b["phi-"]) < 1e-10
    assert abs(per_b["psi+"] - 1.0) < 1e-10 and abs(per_b["psi-"] - 1.0) < 1e-10
    assert abs(report.p_avg - 0.5) < 1e-10
    assert abs(report.p_min - 0.0) < 1e-10
    assert report.unambiguous


def test_engines_agree_on_standard_bsm():
    from empiricist.domain.p3.engine_fock import FockEngine
    scheme = BellScheme(
        n_modes=4, n_ancilla_photons=0, ancilla={},
        mesh=Mesh(n_modes=4, elements=[("bs", 0, 2, np.pi / 4, 0.0),
                                       ("bs", 1, 3, np.pi / 4, 0.0)]),
    )
    ra = evaluate_scheme(scheme, PermanentEngine())
    rb = evaluate_scheme(scheme, FockEngine())
    for b in BELL_LABELS:
        assert abs(ra.success_by_state[b] - rb.success_by_state[b]) < 1e-10


def test_scheme_validation():
    import pytest
    with pytest.raises(ValueError):
        BellScheme(n_modes=4, n_ancilla_photons=1, ancilla={},
                   mesh=Mesh(n_modes=4, elements=[])).validate()
    with pytest.raises(ValueError):
        BellScheme(n_modes=6, n_ancilla_photons=1, ancilla={(2,): 1.0},
                   mesh=Mesh(n_modes=6, elements=[])).validate()  # wrong photon count
    with pytest.raises(ValueError):
        BellScheme(n_modes=6, n_ancilla_photons=1, ancilla={(1, 0): 0.5},
                   mesh=Mesh(n_modes=6, elements=[])).validate()  # not normalized
    with pytest.raises(ValueError):
        BellScheme(n_modes=5, n_ancilla_photons=1, ancilla={(1, 0): 1.0},
                   mesh=Mesh(n_modes=5, elements=[])).validate()  # pattern length != m-4

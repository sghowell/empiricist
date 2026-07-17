import numpy as np
import pytest

from empiricist.search.p3_screen import (
    MAX_ANCILLA_TERMS,
    MAX_MESH_ELEMENTS,
    MAX_MODES,
    MAX_PHOTONS,
    screen_scheme,
)
from empiricist.search.schemas import ScreenReject


def _bsm_dict(**overrides):
    d = {
        "n_modes": 4,
        "n_ancilla_photons": 0,
        "ancilla": [],
        "mesh": [
            {"kind": "bs", "i": 0, "j": 2, "theta": np.pi / 4, "phi": 0.0},
            {"kind": "bs", "i": 1, "j": 3, "theta": np.pi / 4, "phi": 0.0},
        ],
        "claimed_p_avg": 0.5,
    }
    d.update(overrides)
    return d


def test_screen_accepts_standard_bsm():
    scheme = screen_scheme(_bsm_dict())
    assert scheme.n_modes == 4


def test_screen_rejects_oversize_modes():
    with pytest.raises(ScreenReject):
        screen_scheme(_bsm_dict(n_modes=MAX_MODES + 1))


def test_screen_rejects_photon_dos():
    # a valid-looking but compute-DoS ancilla: photons over cap
    anc = [{"pattern": [MAX_PHOTONS + 1], "re": 1.0, "im": 0.0}]
    with pytest.raises(ScreenReject):
        screen_scheme(_bsm_dict(n_modes=5, n_ancilla_photons=MAX_PHOTONS + 1, ancilla=anc))


def test_screen_rejects_oversize_mesh():
    els = [{"kind": "phase", "i": 0, "j": 0, "theta": 0.1, "phi": 0.0}] * (MAX_MESH_ELEMENTS + 1)
    with pytest.raises(ScreenReject):
        screen_scheme(_bsm_dict(mesh=els))


def test_screen_rejects_oversize_ancilla_terms():
    terms = [{"pattern": [1, 0], "re": 1.0, "im": 0.0}] * (MAX_ANCILLA_TERMS + 1)
    with pytest.raises(ScreenReject):
        screen_scheme(_bsm_dict(n_modes=6, n_ancilla_photons=1, ancilla=terms))


def test_screen_rejects_huge_mode_index():
    el = {"kind": "bs", "i": 10**500, "j": 0, "theta": 0.1, "phi": 0.0}
    with pytest.raises(ScreenReject):
        screen_scheme(_bsm_dict(mesh=[el]))


def test_screen_rejects_invalid_scheme_as_screenreject():
    # validation failures (here: schema-invalid extra field is NOT the screen's job,
    # but a converter-level ValueError IS): unnormalized ancilla
    anc = [{"pattern": [1, 0], "re": 0.5, "im": 0.0}]
    with pytest.raises(ScreenReject):
        screen_scheme(_bsm_dict(n_modes=6, n_ancilla_photons=1, ancilla=anc))

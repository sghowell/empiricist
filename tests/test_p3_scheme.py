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


def test_standard_bsm_has_zero_leakage():
    scheme = BellScheme(
        n_modes=4, n_ancilla_photons=0, ancilla={},
        mesh=Mesh(n_modes=4, elements=[("bs", 0, 2, np.pi / 4, 0.0),
                                       ("bs", 1, 3, np.pi / 4, 0.0)]),
    )
    r = evaluate_scheme(scheme, PermanentEngine())
    assert r.leakage == 0.0
    assert r.unambiguous


def test_near_degenerate_coupling_reports_leakage():
    # The reviewer's exploit: a weak bs(0,1,eps) hides a 2e-12 misidentification
    # below _AMBIG_TOL; the leakage field must expose it and unambiguous must be False.
    # Measured leakage for this placement: 2.0e-12 total (5e-13 on each of 4 patterns).
    eps = 1e-6
    scheme = BellScheme(
        n_modes=4, n_ancilla_photons=0, ancilla={},
        mesh=Mesh(n_modes=4, elements=[("bs", 0, 1, eps, 0.0),
                                       ("bs", 0, 2, np.pi / 4, 0.0),
                                       ("bs", 1, 3, np.pi / 4, 0.0)]),
    )
    r = evaluate_scheme(scheme, PermanentEngine())
    assert r.leakage > 1e-13
    assert not r.unambiguous


def test_vacuum_ancilla_modes_require_explicit_ancilla():
    import pytest
    with pytest.raises(ValueError):
        BellScheme(n_modes=6, n_ancilla_photons=0, ancilla={},
                   mesh=Mesh(n_modes=6, elements=[])).validate()
    # The explicit-vacuum form validates and evaluates: the standard BSM embedded
    # in 6 modes with two idle vacuum ancilla modes gives per-B (0, 0, 1, 1).
    scheme = BellScheme(
        n_modes=6, n_ancilla_photons=0, ancilla={(0, 0): 1.0},
        mesh=Mesh(n_modes=6, elements=[("bs", 0, 2, np.pi / 4, 0.0),
                                       ("bs", 1, 3, np.pi / 4, 0.0)]),
    )
    scheme.validate()
    r = evaluate_scheme(scheme, PermanentEngine())
    assert abs(r.success_by_state["phi+"]) < 1e-10
    assert abs(r.success_by_state["phi-"]) < 1e-10
    assert abs(r.success_by_state["psi+"] - 1.0) < 1e-10
    assert abs(r.success_by_state["psi-"] - 1.0) < 1e-10


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


def _standard_bsm() -> BellScheme:
    return BellScheme(
        n_modes=4, n_ancilla_photons=0, ancilla={},
        mesh=Mesh(n_modes=4, elements=[("bs", 0, 2, np.pi / 4, 0.0),
                                       ("bs", 1, 3, np.pi / 4, 0.0)]),
    )


def test_verify_agreed_pass_and_fail():
    from empiricist.domain.p3.verify import verify_scheme_agreed
    ok = verify_scheme_agreed(_standard_bsm(), claimed_p_avg=0.5)
    assert ok.verdict == "PASS"
    assert abs(ok.report.p_avg - 0.5) < 1e-10
    miss = verify_scheme_agreed(_standard_bsm(), claimed_p_avg=0.75)
    assert miss.verdict == "FAIL"


def test_verify_agreed_leakage_budget():
    from empiricist.domain.p3.verify import verify_scheme_agreed
    eps = 1e-6
    leaky = BellScheme(
        n_modes=4, n_ancilla_photons=0, ancilla={},
        mesh=Mesh(n_modes=4, elements=[("bs", 0, 1, eps, 0.0),
                                       ("bs", 0, 2, np.pi / 4, 0.0),
                                       ("bs", 1, 3, np.pi / 4, 0.0)]),
    )
    # default budget 0.0: the leaky scheme cannot PASS even though p_avg = 0.5
    r0 = verify_scheme_agreed(leaky, claimed_p_avg=0.5)
    assert r0.verdict == "FAIL"
    # declared budget: PASS, and the claim carries its bound
    r1 = verify_scheme_agreed(leaky, claimed_p_avg=0.5, claimed_max_leakage=1e-11)
    assert r1.verdict == "PASS"
    assert r1.report.leakage > 0.0


def test_verify_agreed_result_carries_max_leakage():
    from empiricist.domain.p3.verify import verify_scheme_agreed
    r = verify_scheme_agreed(_standard_bsm(), claimed_p_avg=0.5)
    assert r.verdict == "PASS"
    assert r.leakage == 0.0


def test_verify_agreed_error_on_disagreement(monkeypatch):
    from empiricist.domain.p3 import verify as vmod

    class LyingEngine(vmod.FockEngine):
        def output_distribution(self, mesh, state):
            d = super().output_distribution(mesh, state)
            k = next(iter(d))
            d[k] = d[k] + 0.5  # corrupt one probability
            return d

    monkeypatch.setattr(vmod, "FockEngine", LyingEngine)
    r = vmod.verify_scheme_agreed(_standard_bsm(), claimed_p_avg=0.5)
    assert r.verdict == "ERROR"
    assert "disagree" in r.detail

"""Golden suite — exactly-known physics pins that gate the P3 certification.

Per design decision D4 the published success vectors ARE the spec: these
assertions are pins, not fitted expectations. A regression here means the
physics stack drifted, not that a golden needs loosening.
"""

import numpy as np

from empiricist.domain.p3.interferometer import Mesh
from empiricist.domain.p3.known_schemes import grice_boosted_bsm, standard_bsm
from empiricist.domain.p3.scheme import BellScheme
from empiricist.domain.p3.verify import verify_scheme_agreed


def test_standard_bsm_golden():
    # The textbook linear-optics BSM: psi+/psi- identified with certainty,
    # phi+/phi- mutually ambiguous. Vector (0, 0, 1, 1); p_avg 1/2, p_min 0.
    r = verify_scheme_agreed(standard_bsm(), claimed_p_avg=0.5)
    assert r.verdict == "PASS"
    v = r.report.success_by_state
    assert abs(v["phi+"]) < 1e-10 and abs(v["phi-"]) < 1e-10
    assert abs(v["psi+"] - 1.0) < 1e-10 and abs(v["psi-"] - 1.0) < 1e-10
    assert abs(r.report.p_min - 0.0) < 1e-10
    assert r.leakage == 0.0


def test_grice_boosted_bsm_golden():
    # Grice PRA 84, 042331 (2011): one Bell-pair ancilla resolves phi+/phi-
    # half the time. Published exact vector (1/2, 1/2, 1, 1); p_avg 3/4,
    # p_min 1/2, leakage 0 -- through the full two-engine agreed contract.
    r = verify_scheme_agreed(grice_boosted_bsm(), claimed_p_avg=0.75)
    assert r.verdict == "PASS"
    v = r.report.success_by_state
    assert abs(v["phi+"] - 0.5) < 1e-10 and abs(v["phi-"] - 0.5) < 1e-10
    assert abs(v["psi+"] - 1.0) < 1e-10 and abs(v["psi-"] - 1.0) < 1e-10
    assert abs(r.report.p_avg - 0.75) < 1e-10
    assert abs(r.report.p_min - 0.5) < 1e-10
    assert r.leakage == 0.0
    # p_min is itself a claim the scheme meets.
    r_min = verify_scheme_agreed(
        grice_boosted_bsm(), claimed_p_avg=0.75, claimed_p_min=0.5
    )
    assert r_min.verdict == "PASS"


def test_no_ancilla_ceiling_sanity():
    # The ancilla-free ceiling is p*(0) = 1/2 (Calsamiglia-Lutkenhaus,
    # PRA 63, 020301(R) (2001)); every k=0 scheme must respect it. This pins
    # the EXACT bound the M20 campaign will attack, not merely "no perfect
    # BM". Routed through verify_scheme_agreed so each scheme also gets the
    # cross-engine agreement check for free.
    rng = np.random.default_rng(11)
    for _ in range(10):
        els = []
        for _ in range(int(rng.integers(2, 10))):
            i, j = sorted(rng.choice(4, size=2, replace=False).tolist())
            els.append(("bs", i, j, float(rng.uniform(0, np.pi)), float(rng.uniform(0, 2 * np.pi))))
        scheme = BellScheme(n_modes=4, n_ancilla_photons=0, ancilla={},
                            mesh=Mesh(n_modes=4, elements=els))
        r = verify_scheme_agreed(scheme)
        assert r.verdict == "PASS"
        assert r.report.p_avg <= 0.5 + 1e-9

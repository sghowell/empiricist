"""Exact Q(i, sqrt2) evaluation of octant-angle Bell schemes (the trust side of M21b)."""
from __future__ import annotations

from fractions import Fraction
from math import pi, sqrt

import numpy as np
import pytest

from empiricist.domain.p3.engine_fock import FockEngine
from empiricist.domain.p3.engine_permanent import PermanentEngine
from empiricist.domain.p3.exact import (
    Q8,
    QR,
    ExactUnsupported,
    exact_distributions,
    exact_permanent,
    exact_report,
    exact_unitary,
    snap_octant,
    snap_q8,
    snap_qr,
)
from empiricist.domain.p3.fock import patterns
from empiricist.domain.p3.interferometer import Mesh, mesh_unitary
from empiricist.domain.p3.known_schemes import grice_boosted_bsm, standard_bsm
from empiricist.domain.p3.scheme import BellScheme, evaluate_scheme

F = Fraction
LABELS = ("phi+", "phi-", "psi+", "psi-")


def qr(a, b=0) -> QR:
    return QR(F(a), F(b))


def test_qr_and_q8_arithmetic_is_a_field():
    r2 = qr(0, 1)
    assert r2 * r2 == qr(2)
    z = Q8(qr(F(1, 2)), qr(0, F(1, 2)))  # 1/2 + i*sqrt2/2
    assert z.abs2() == qr(F(1, 4) + F(1, 2))
    assert (z * z.conj()).im.is_zero()
    assert Q8.from_rational(3).to_complex() == 3 + 0j
    assert abs((z * z).to_complex() - z.to_complex() ** 2) < 1e-15
    assert (z - z).is_zero() and (-z + z).is_zero()


def test_qr_exact_ordering():
    assert qr(0, 1) < qr(2)            # sqrt2 < 2
    assert qr(1) < qr(0, 1)            # 1 < sqrt2
    assert qr(3, -2) < qr(0, F(1, 4))  # 3 - 2 sqrt2 = 0.17 < 0.35
    assert qr(-1, 1).sign() == 1 and qr(1, -1).sign() == -1 and qr(0).sign() == 0
    assert qr(7, -5).sign() == -1      # 7 - 5*1.414 < 0


def test_snap_recognises_octant_angles_and_small_field_elements():
    assert snap_octant(pi / 4) == 1 and snap_octant(-pi / 2) == 6 and snap_octant(0.0) == 0
    assert snap_octant(2 * pi) == 0 and snap_octant(7 * pi / 4) == 7
    with pytest.raises(ExactUnsupported):
        snap_octant(0.3)
    assert snap_qr(sqrt(2) / 2) == qr(0, F(1, 2))
    assert snap_qr(0.25) == qr(F(1, 4))
    assert snap_qr(1 + sqrt(2)) == qr(1, 1)
    assert snap_qr(-0.5) == qr(F(-1, 2))
    with pytest.raises(ExactUnsupported):
        snap_qr(0.123456789)
    assert snap_q8(complex(0, sqrt(2) / 2)) == Q8(qr(0), qr(0, F(1, 2)))


def test_exact_unitary_matches_float_unitary_on_octant_meshes():
    rng = np.random.default_rng(3)
    for _ in range(20):
        m = int(rng.integers(2, 7))
        els = []
        for _ in range(int(rng.integers(1, 8))):
            i, j = sorted(rng.choice(m, size=2, replace=False).tolist())
            els.append((
                "bs", i, j,
                float(rng.integers(0, 8)) * pi / 4,
                float(rng.integers(0, 8)) * pi / 4,
            ))
        els.append(("phase", int(rng.integers(0, m)), float(rng.integers(0, 8)) * pi / 4))
        mesh = Mesh(n_modes=m, elements=els)
        exact = exact_unitary(mesh)
        approx = mesh_unitary(mesh)
        for r in range(m):
            for c in range(m):
                assert abs(exact[r][c].to_complex() - approx[r, c]) < 1e-12


def test_exact_permanent_small_cases():
    one, two = Q8.from_rational(1), Q8.from_rational(2)
    assert exact_permanent([[one, two], [two, one]]) == Q8.from_rational(5)  # 1*1 + 2*2
    assert exact_permanent([]) == one
    i = Q8(qr(0), qr(1))
    assert exact_permanent([[i, one], [one, i]]) == Q8.from_rational(0)  # i*i + 1*1 = 0


def test_standard_bsm_and_grice_vectors_are_exact():
    rep = exact_report(standard_bsm())
    assert [rep.success[b] for b in LABELS] == [qr(0), qr(0), qr(1), qr(1)]
    assert rep.p_avg == qr(F(1, 2)) and rep.p_min.is_zero() and not rep.all_identified
    assert len(rep.assignment) == 4  # the four psi patterns; phi patterns stay ambiguous
    g = exact_report(grice_boosted_bsm())
    assert [g.success[b] for b in LABELS] == [qr(F(1, 2)), qr(F(1, 2)), qr(1), qr(1)]
    assert g.p_avg == qr(F(3, 4)) and g.p_min == qr(F(1, 2)) and g.all_identified


def _random_octant_scheme(rng, k: int, m: int) -> BellScheme | None:
    field_vals = [0.0, 1.0, -1.0, 0.5, sqrt(2) / 2, -sqrt(2) / 2]
    els = []
    for _ in range(int(rng.integers(2, 12))):
        i, j = sorted(rng.choice(m, size=2, replace=False).tolist())
        els.append((
            "bs", i, j, float(rng.integers(0, 8)) * pi / 4, float(rng.integers(0, 8)) * pi / 4,
        ))
    anc_pats = patterns(k, m - 4)
    raw = {p: complex(rng.choice(field_vals), rng.choice(field_vals)) for p in anc_pats}
    norm = sqrt(sum(abs(v) ** 2 for v in raw.values()))
    # keep the normalised amplitudes inside the field: allow norms 1, sqrt2, 2, 2 sqrt2
    if norm == 0 or min(abs(norm - c) for c in (1, sqrt(2), 2, 2 * sqrt(2))) > 1e-12:
        return None
    anc = {p: v / norm for p, v in raw.items() if v != 0}
    if k == 0:
        anc = {p: 1.0 + 0j for p in anc_pats}  # the vacuum pattern on the extra modes
    return BellScheme(n_modes=m, n_ancilla_photons=k, ancilla=anc,
                      mesh=Mesh(n_modes=m, elements=els))


def test_exact_distributions_agree_with_both_engines_fuzz():
    rng = np.random.default_rng(11)
    checked = 0
    for _ in range(60):
        k = int(rng.integers(0, 3))
        m = 4 if k == 0 else int(rng.integers(5, 8))
        scheme = _random_octant_scheme(rng, k, m)
        if scheme is None:
            continue
        exact = exact_distributions(scheme)
        for engine in (PermanentEngine(), FockEngine()):
            rep = evaluate_scheme(scheme, engine)
            for b, dist in rep.distributions.items():
                for key in set(dist) | set(exact[b]):
                    ex = exact[b].get(key, qr(0)).to_float()
                    assert abs(ex - dist.get(key, 0.0)) < 1e-12, (k, m, b, key)
        checked += 1
    assert checked >= 15


def test_exact_report_matches_float_report_on_a_k2_octant_scheme():
    rng = np.random.default_rng(5)
    scheme = None
    while scheme is None:
        scheme = _random_octant_scheme(rng, 2, 6)
    ex = exact_report(scheme)
    fl = evaluate_scheme(scheme, PermanentEngine())
    for b in LABELS:
        assert abs(ex.success[b].to_float() - fl.success_by_state[b]) < 1e-12
    assert abs(ex.p_avg.to_float() - fl.p_avg) < 1e-12
    assert abs(ex.p_min.to_float() - fl.p_min) < 1e-12


def test_non_octant_angle_and_off_field_amplitude_are_unsupported():
    bad = BellScheme(n_modes=4, n_ancilla_photons=0, ancilla={},
                     mesh=Mesh(n_modes=4, elements=(("bs", 0, 2, 0.3, 0.0),)))
    with pytest.raises(ExactUnsupported):
        exact_report(bad)
    # 0.6 + 0.8i WOULD be in the field (3/5 + 4i/5); use a genuinely off-field amplitude.
    off = 0.123456789
    anc = BellScheme(n_modes=5, n_ancilla_photons=1,
                     ancilla={(1,): complex(off, sqrt(1 - off * off))},
                     mesh=Mesh(n_modes=5, elements=(("bs", 0, 4, pi / 4, 0.0),)))
    with pytest.raises(ExactUnsupported):
        exact_report(anc)


def test_three_photons_in_one_ancilla_mode_is_unsupported():
    # sqrt(3!) leaves Q(i, sqrt2): refuse rather than approximate.
    s = BellScheme(n_modes=5, n_ancilla_photons=3, ancilla={(3,): 1.0 + 0j},
                   mesh=Mesh(n_modes=5, elements=(("bs", 0, 4, pi / 4, 0.0),)))
    with pytest.raises(ExactUnsupported):
        exact_report(s)


def test_malformed_scheme_is_a_plain_value_error():
    s = BellScheme(n_modes=5, n_ancilla_photons=1, ancilla={(1,): 2.0 + 0j},
                   mesh=Mesh(n_modes=5, elements=()))
    with pytest.raises(ValueError, match="normalized"):
        exact_report(s)

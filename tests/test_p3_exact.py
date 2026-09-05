"""Exact evaluation over Q(i)(sqrt d ...) -- the trust side of M21b."""
from __future__ import annotations

from fractions import Fraction
from math import cos, pi, sin, sqrt

import numpy as np
import pytest

from empiricist.domain.p3.engine_fock import FockEngine
from empiricist.domain.p3.engine_permanent import PermanentEngine
from empiricist.domain.p3.exact import (
    ONE,
    ZERO,
    Alg,
    ExactUnsupported,
    ExactWitness,
    alg_from_json,
    alg_str,
    alg_to_json,
    exact_distributions,
    exact_permanent,
    exact_report,
    exact_unitary,
    is_exact_isometry,
    snap_complex,
    snap_isometry,
    snap_lattice_phase,
    snap_octant,
    snap_rational,
    witness_from_json,
    witness_to_json,
)
from empiricist.domain.p3.fock import patterns
from empiricist.domain.p3.interferometer import Mesh, mesh_unitary
from empiricist.domain.p3.known_schemes import grice_boosted_bsm, standard_bsm
from empiricist.domain.p3.scheme import BellScheme, evaluate_scheme

F = Fraction
LABELS = ("phi+", "phi-", "psi+", "psi-")


def R(x) -> Alg:
    return Alg.rational(F(x))


def test_field_arithmetic():
    s2, s3, s6 = Alg.sqrt_rational(2), Alg.sqrt_rational(3), Alg.sqrt_rational(6)
    assert s2 * s2 == R(2) and s2 * s3 == s6 and s6 * s6 == R(6)
    assert Alg.sqrt_rational(F(1, 6)) * Alg.sqrt_rational(F(1, 6)) == R(F(1, 6))
    assert Alg.sqrt_rational(8) == s2.scale(2)  # sqrt 8 = 2 sqrt 2
    z = R(F(1, 2)) + Alg.rational(0, F(1, 2)) * s2  # 1/2 + i sqrt2/2
    assert z.abs2() == R(F(3, 4))
    assert (z * z.conj()).is_real() and not z.is_real()
    assert abs((z * z).to_complex() - z.to_complex() ** 2) < 1e-15
    assert (z - z).is_zero() and (-z + z).is_zero()
    assert alg_str(R(F(1, 16))) == "1/16" and "sqrt6" in alg_str(s6)


def test_roots_of_unity_are_exact_and_multiplicative():
    for k in range(24):
        z = Alg.root_of_unity_24(k)
        assert z.abs2() == ONE
        assert abs(z.to_complex() - complex(cos(k * pi / 12), sin(k * pi / 12))) < 1e-15
        for j in (1, 5, 7):
            assert Alg.root_of_unity_24(k) * Alg.root_of_unity_24(j) == Alg.root_of_unity_24(k + j)


def test_exact_sign_and_ordering():
    s2 = Alg.sqrt_rational(2)
    assert (R(3) - s2.scale(2)).sign() == 1        # 3 - 2 sqrt2 > 0
    assert (R(7) - s2.scale(5)).sign() == -1       # 7 - 5 sqrt2 < 0
    assert (s2 + Alg.sqrt_rational(3) - Alg.sqrt_rational(10)).sign() == -1
    assert ZERO.sign() == 0 and R(-1) < ZERO < R(1) and s2 < R(2) and R(1) < s2
    with pytest.raises(ValueError):
        Alg.rational(0, 1).sign()


def test_alg_json_round_trip_and_validation():
    x = R(F(1, 6)) + Alg.sqrt_rational(2).scale(F(-3, 8))
    x = x + Alg.rational(0, F(1, 4)) * Alg.sqrt_rational(3)
    assert alg_from_json(alg_to_json(x)) == x
    assert alg_from_json("1/6") == R(F(1, 6)) and alg_from_json(3) == R(3)
    assert alg_to_json(ZERO) == [] and alg_from_json([]) == ZERO
    with pytest.raises(ValueError):
        alg_from_json([[4, "1", "0"]])       # not square-free
    with pytest.raises(ValueError):
        alg_from_json({"a": 1})


def test_snapping_floats_into_the_field():
    assert snap_octant(pi / 4) == 3 and snap_octant(-pi / 2) == 18 and snap_octant(0.0) == 0
    with pytest.raises(ExactUnsupported):
        snap_octant(0.3)
    assert snap_lattice_phase(complex(cos(pi / 6), sin(pi / 6))) == 2
    assert snap_rational(1 / 6) == F(1, 6) and snap_rational(0.25) == F(1, 4)
    with pytest.raises(ExactUnsupported):
        snap_rational(0.123456789)
    z = snap_complex(complex(cos(pi / 12), sin(pi / 12)) / sqrt(6))
    assert z == Alg.sqrt_rational(F(1, 6)) * Alg.root_of_unity_24(1)
    assert snap_complex(1e-12) == ZERO
    with pytest.raises(ExactUnsupported):
        snap_complex(complex(0.6, 0.31))      # off-lattice phase


def test_exact_unitary_matches_float_unitary_on_lattice_meshes():
    rng = np.random.default_rng(3)
    for _ in range(20):
        m = int(rng.integers(2, 7))
        els = []
        for _ in range(int(rng.integers(1, 8))):
            i, j = sorted(rng.choice(m, size=2, replace=False).tolist())
            els.append(("bs", i, j, float(rng.integers(0, 24)) * pi / 12,
                        float(rng.integers(0, 24)) * pi / 12))
        els.append(("phase", int(rng.integers(0, m)), float(rng.integers(0, 24)) * pi / 12))
        mesh = Mesh(n_modes=m, elements=els)
        exact = exact_unitary(mesh)
        approx = mesh_unitary(mesh)
        for r in range(m):
            for c in range(m):
                assert abs(exact[r][c].to_complex() - approx[r, c]) < 1e-12
        assert is_exact_isometry(exact)


def test_exact_permanent_small_cases():
    one, two, i = R(1), R(2), Alg.rational(0, 1)
    assert exact_permanent([[one, two], [two, one]]) == R(5)
    assert exact_permanent([]) == one
    assert exact_permanent([[i, one], [one, i]]) == ZERO  # i*i + 1*1


def test_standard_bsm_and_grice_witnesses_are_exact():
    rep = exact_report(ExactWitness.from_mesh(standard_bsm()))
    assert [rep.success[b] for b in LABELS] == [ZERO, ZERO, ONE, ONE]
    assert rep.p_avg == R(F(1, 2)) and rep.p_min.is_zero() and not rep.all_identified
    assert len(rep.assignment) == 4
    g = exact_report(ExactWitness.from_mesh(grice_boosted_bsm()))
    assert [g.success[b] for b in LABELS] == [R(F(1, 2)), R(F(1, 2)), ONE, ONE]
    assert g.p_avg == R(F(3, 4)) and g.p_min == R(F(1, 2)) and g.all_identified


def _random_lattice_scheme(rng, k: int, m: int) -> BellScheme | None:
    field_vals = [0.0, 1.0, -1.0, 0.5, sqrt(2) / 2, -sqrt(2) / 2, sqrt(3) / 2]
    els = []
    for _ in range(int(rng.integers(2, 12))):
        i, j = sorted(rng.choice(m, size=2, replace=False).tolist())
        els.append(("bs", i, j, float(rng.integers(0, 24)) * pi / 12,
                    float(rng.integers(0, 24)) * pi / 12))
    anc_pats = patterns(k, m - 4)
    raw = {p: complex(rng.choice(field_vals), rng.choice(field_vals)) for p in anc_pats}
    norm2 = sum(abs(v) ** 2 for v in raw.values())
    # normalisation stays in the field iff norm^2 is a small rational (any rational works)
    if norm2 == 0 or abs(norm2 - round(norm2 * 4) / 4) > 1e-12:
        return None
    anc = {p: v / sqrt(norm2) for p, v in raw.items() if v != 0}
    if k == 0:
        anc = {p: 1.0 + 0j for p in anc_pats}
    return BellScheme(n_modes=m, n_ancilla_photons=k, ancilla=anc,
                      mesh=Mesh(n_modes=m, elements=els))


def test_exact_distributions_agree_with_both_engines_fuzz():
    rng = np.random.default_rng(11)
    checked = 0
    for _ in range(80):
        k = int(rng.integers(0, 3))
        m = 4 if k == 0 else int(rng.integers(5, 8))
        scheme = _random_lattice_scheme(rng, k, m)
        if scheme is None:
            continue
        try:
            w = ExactWitness.from_mesh(scheme)
        except ExactUnsupported:
            continue  # an ancilla amplitude outside the small-denominator box
        exact = exact_distributions(w)
        for engine in (PermanentEngine(), FockEngine()):
            rep = evaluate_scheme(scheme, engine)
            for b, dist in rep.distributions.items():
                for key in set(dist) | set(exact[b]):
                    ex = exact[b].get(key, ZERO).to_float()
                    assert abs(ex - dist.get(key, 0.0)) < 1e-12, (k, m, b, key)
        checked += 1
    assert checked >= 15


def test_snap_isometry_recovers_grice_and_rejects_a_random_unitary():
    u = mesh_unitary(grice_boosted_bsm().mesh)
    iso = snap_isometry([list(row) for row in u])
    assert is_exact_isometry(iso)
    rng = np.random.default_rng(1)
    q, _ = np.linalg.qr(rng.normal(size=(5, 5)) + 1j * rng.normal(size=(5, 5)))
    with pytest.raises(ExactUnsupported):
        snap_isometry([list(row) for row in q])
    # on-lattice entries that are NOT orthonormal are refused too
    with pytest.raises(ExactUnsupported, match="isometry"):
        snap_isometry([[1.0, 1.0], [0.0, 0.0]])


def test_witness_json_round_trip_and_validation():
    w = ExactWitness.from_mesh(grice_boosted_bsm())
    data = witness_to_json(w)
    assert witness_from_json(data) == w
    bad = dict(data)
    bad["ancilla"] = [[p, alg_to_json(ONE)] for p, _ in data["ancilla"]]
    with pytest.raises(ValueError, match="normalised"):
        witness_from_json(bad)
    bad = dict(data)
    bad["isometry"] = [row[:3] for row in data["isometry"]]
    with pytest.raises(ValueError):
        witness_from_json(bad)
    with pytest.raises(ValueError, match="malformed"):
        witness_from_json({"n_modes": 4})


def test_unsupported_inputs_refuse_instead_of_approximating():
    with pytest.raises(ExactUnsupported):
        ExactWitness.from_mesh(BellScheme(
            n_modes=4, n_ancilla_photons=0, ancilla={},
            mesh=Mesh(n_modes=4, elements=(("bs", 0, 2, 0.3, 0.0),))))
    off = 0.123456789
    with pytest.raises(ExactUnsupported):
        ExactWitness.from_mesh(BellScheme(
            n_modes=5, n_ancilla_photons=1, ancilla={(1,): complex(off, sqrt(1 - off * off))},
            mesh=Mesh(n_modes=5, elements=(("bs", 0, 4, pi / 4, 0.0),))))
    w = ExactWitness(n_modes=5, n_ancilla_photons=3,
                     isometry=tuple(tuple(row) for row in exact_unitary(
                         Mesh(n_modes=5, elements=(("bs", 0, 4, pi / 4, 0.0),)))),
                     ancilla={(3,): ONE})
    with pytest.raises(ExactUnsupported):
        exact_report(w)


def test_witness_caps_and_radicand_cap_refuse_fast():
    import time

    from empiricist.domain.p3.exact import MAX_EXACT_MODES, MAX_EXACT_PHOTONS, MAX_RADICAND
    from empiricist.search.p3_screen import MAX_MODES, MAX_PHOTONS

    assert MAX_EXACT_MODES == MAX_MODES and MAX_EXACT_PHOTONS == MAX_PHOTONS
    big = {"n_modes": 400, "n_ancilla_photons": 0,
           "isometry": [[alg_to_json(ONE if r == c else ZERO) for c in range(4)]
                        for r in range(400)],
           "ancilla": []}
    t = time.perf_counter()
    with pytest.raises(ValueError, match="cap"):
        witness_from_json(big)
    assert time.perf_counter() - t < 1.0
    with pytest.raises(ValueError, match="radicand"):
        alg_from_json([[MAX_RADICAND * 10 + 7, "1", "0"]])
    w = witness_to_json(ExactWitness.from_mesh(grice_boosted_bsm()))
    w["n_ancilla_photons"] = 9
    with pytest.raises(ValueError):
        witness_from_json(w)


def test_bell_labels_match_the_scheme_module():
    from empiricist.domain.p3 import exact, scheme

    assert exact.BELL_LABELS == scheme.BELL_LABELS


def test_exact_module_does_not_import_numpy():
    import subprocess
    import sys

    code = ("import sys; import empiricist.domain.p3.exact; "
            "print('numpy' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"

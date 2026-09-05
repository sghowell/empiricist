"""P3ExactVerifier + its golden suite (the exact-witness trust boundary)."""
from __future__ import annotations

import json
from fractions import Fraction

import pytest

from empiricist.domain.p3.exact import Alg, ExactWitness, alg_to_json, witness_to_json
from empiricist.domain.p3.known_schemes import grice_boosted_bsm, standard_bsm
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Verdict
from empiricist.verifiers.p3_exact import P3ExactVerifier
from empiricist.verifiers.p3_exact_goldens import (
    P3_EXACT_GOLDEN_SUITE,
    certify_p3_exact,
    p3_exact_suite_hash,
)


def _vec(pp, pm, sp, sm):
    return {
        "phi+": Alg.rational(Fraction(pp)),
        "phi-": Alg.rational(Fraction(pm)),
        "psi+": Alg.rational(Fraction(sp)),
        "psi-": Alg.rational(Fraction(sm)),
    }


GRICE = witness_to_json(ExactWitness.from_mesh(grice_boosted_bsm()))
STD = witness_to_json(ExactWitness.from_mesh(standard_bsm()))


def test_verifier_pass_and_mismatch_details():
    v = P3ExactVerifier()
    ok = v.verify(GRICE, claimed_success=_vec("1/2", "1/2", 1, 1))
    assert ok.verdict is Verdict.PASS
    assert ok.details["p_min"] == alg_to_json(Alg.rational(Fraction(1, 2)))
    assert ok.details["p_avg"] == alg_to_json(Alg.rational(Fraction(3, 4)))
    assert ok.details["all_identified"] is True and ok.details["k"] == 2
    bad = v.verify(GRICE, claimed_success=_vec("1/4", "1/2", 1, 1))
    assert bad.verdict is Verdict.FAIL and "phi+: 1/2 != 1/4" in bad.details["detail"]


def test_verifier_all_identified_teeth_and_invalid_inputs():
    v = P3ExactVerifier()
    r = v.verify(STD, claimed_success=_vec(0, 0, 1, 1), require_all_identified=True)
    assert r.verdict is Verdict.FAIL and "never identified" in r.details["detail"]
    partial = v.verify(STD, claimed_success={"phi+": Alg.rational(0)})
    assert partial.verdict is Verdict.FAIL and partial.details.get("invalid") is True
    assert v.verify(None, claimed_success=_vec(0, 0, 1, 1)).details.get("invalid") is True
    scaled = json.loads(json.dumps(GRICE))
    scaled["isometry"][0][0] = [
        [d, str(Fraction(a) * 2), b] for d, a, b in scaled["isometry"][0][0]
    ]
    assert v.verify(scaled, claimed_success=_vec("1/2", "1/2", 1, 1)).details["invalid"] is True


def test_verifier_accepts_irrational_exact_claims():
    from math import pi

    from empiricist.domain.p3.exact import exact_report
    from empiricist.domain.p3.interferometer import Mesh
    from empiricist.domain.p3.scheme import BellScheme

    s = BellScheme(n_modes=4, n_ancilla_photons=0, ancilla={},
                   mesh=Mesh(n_modes=4, elements=(("bs", 0, 2, pi / 6, pi / 12),
                                                 ("bs", 1, 3, 3 * pi / 4, 0.0))))
    w = ExactWitness.from_mesh(s)
    rep = exact_report(w)
    r = P3ExactVerifier().verify(witness_to_json(w), claimed_success=dict(rep.success))
    assert r.verdict is Verdict.PASS


def test_golden_suite_shape_and_stable_hash():
    verdicts = [e for _, _, e in P3_EXACT_GOLDEN_SUITE]
    assert verdicts.count(Verdict.PASS) == 4 and verdicts.count(Verdict.FAIL) == 6
    assert len(p3_exact_suite_hash()) == 64 and p3_exact_suite_hash() == p3_exact_suite_hash()


def test_golden_suite_catches_a_checker_without_witness_validation(tmp_path, monkeypatch):
    """Mutation: drop the isometry / normalisation checks. The doubled-Grice and
    un-normalised-ancilla cases claim exactly what such a checker computes, so it
    PASSes them and loses its stamp."""
    import empiricist.domain.p3.exact as exact_mod

    lg = Ledger(tmp_path / "ledger.db")
    try:
        assert certify_p3_exact(lg, P3ExactVerifier()).verdict is Verdict.PASS
        monkeypatch.setattr(exact_mod.ExactWitness, "validate", lambda self: None)
        assert certify_p3_exact(lg, P3ExactVerifier()).verdict is Verdict.FAIL
    finally:
        lg.close()


def test_golden_suite_catches_a_checker_without_input_factorials(tmp_path, monkeypatch):
    """Mutation: 1/sqrt(t!) -> 1. The |2,0> ancilla case claims the true vector
    (0, 0, 1, 1); the mutant computes (0, 0, 2, 2) and fails certification."""
    import empiricist.domain.p3.exact as exact_mod

    lg = Ledger(tmp_path / "ledger.db")
    try:
        monkeypatch.setattr(exact_mod, "_inverse_sqrt_factorials", lambda pattern: exact_mod.ONE)
        assert certify_p3_exact(lg, P3ExactVerifier()).verdict is Verdict.FAIL
    finally:
        lg.close()


def test_verify_is_total_over_claims_and_reports_machinery_errors(monkeypatch):
    v = P3ExactVerifier()
    r = v.verify(GRICE, claimed_success={"phi+": "1/2", "phi-": "1/2", "psi+": "1", "psi-": "1"})
    assert r.verdict is Verdict.FAIL and r.details["invalid"] is True
    r = v.verify(GRICE, claimed_success=dict.fromkeys(("phi+", "phi-", "psi+", "psi-"), 1))
    assert r.verdict is Verdict.FAIL and r.details["invalid"] is True
    import empiricist.verifiers.p3_exact as mod

    def boom(witness):
        raise RuntimeError("machinery")

    monkeypatch.setattr(mod, "exact_report", boom)
    r = v.verify(GRICE, claimed_success=_vec("1/2", "1/2", 1, 1))
    assert r.verdict is Verdict.ERROR and "machinery" in r.details["error"]


def test_certify_p3_exact_stamps_pass_and_rejects_a_verifier_without_teeth(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    try:
        v = P3ExactVerifier()
        assert len(v.binary_hash) == 64
        cert = certify_p3_exact(lg, v)
        assert cert.verdict is Verdict.PASS
        assert lg.get_certification(v.name, v.version, v.binary_hash).golden_suite_hash == (
            p3_exact_suite_hash()
        )

        class _AlwaysPass(P3ExactVerifier):
            def verify(self, witness_json, *, claimed_success, require_all_identified=False):
                from empiricist.verifiers.base import VerifierResult

                return VerifierResult(verdict=Verdict.PASS, details={})

        assert certify_p3_exact(lg, _AlwaysPass()).verdict is Verdict.FAIL
    finally:
        lg.close()


def test_verify_never_raises_on_garbage():
    v = P3ExactVerifier()
    for garbage in (None, 5, "x", [], {"isometry": "nope"}):
        r = v.verify(garbage, claimed_success=_vec(0, 0, 1, 1))
        assert r.verdict is Verdict.FAIL
    with pytest.raises(TypeError):
        v.verify(GRICE)  # claimed_success is keyword-required

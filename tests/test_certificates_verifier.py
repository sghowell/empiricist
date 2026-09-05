"""SOSCertificateVerifier + its golden suite (the CERTIFIED tier's trust boundary)."""
from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

from empiricist.certificates.core import SOSCertificate
from empiricist.certificates.goldens import (
    SOS_GOLDEN_SUITE,
    certify_sos,
    load_k0_golden,
    sos_suite_hash,
)
from empiricist.certificates.verifier import (
    SOSCertificateVerifier,
    certificate_from_json,
    certificate_to_json,
)
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Verdict


def _tiny(bound="0", gram=((Fraction(1),),), objective=None) -> SOSCertificate:
    # -x0^2 <= 0 with Q = [[1]]:  0 - (-x0^2) = x0^2 = b^T Q b, b = (x0)
    return SOSCertificate(
        statement="tiny",
        variables=("x0",),
        objective={(0, 0): Fraction(-1)} if objective is None else objective,
        bound=Fraction(bound),
        constraints=(),
        multipliers=(),
        gram_basis=((0,),),
        gram=gram,
    )


def test_verifier_passes_the_k0_golden():
    r = SOSCertificateVerifier().verify(load_k0_golden())
    assert r.verdict is Verdict.PASS
    assert r.details["failure"] == "" and r.details["bound"] == "1/2"
    assert r.details["gram_dim"] == 128


def test_verifier_fails_identity_psd_and_shape_mutants():
    v = SOSCertificateVerifier()
    assert v.verify(_tiny()).verdict is Verdict.PASS
    assert v.verify(_tiny(bound="-1")).details["failure"] == "identity"
    # x0^2 <= 0 with Q = [[-1]]: identity holds, Gram is not PSD
    psd = _tiny(objective={(0, 0): Fraction(1)}, gram=((Fraction(-1),),))
    assert v.verify(psd).details["failure"] == "psd"
    assert v.verify(replace(_tiny(), gram=())).details["failure"] == "shape"
    assert v.verify(None).verdict is Verdict.FAIL  # never raises


def test_json_round_trip_is_exact():
    cert = load_k0_golden()
    data = certificate_to_json(cert)
    assert certificate_from_json(data) == cert
    assert data["bound"] == "1/2"
    assert all(isinstance(v, str) for row in data["gram"] for v in row)


def test_from_json_rejects_malformed_shapes():
    import pytest

    for bad in (None, {}, {"statement": "s"}, {**certificate_to_json(_tiny()), "gram": "x"}):
        with pytest.raises(ValueError, match="malformed certificate JSON"):
            certificate_from_json(bad)


def test_from_json_refuses_floats():
    import pytest

    data = certificate_to_json(_tiny())
    data["bound"] = 0.5
    with pytest.raises(ValueError, match="malformed certificate JSON"):
        certificate_from_json(data)
    data = certificate_to_json(_tiny())
    data["gram"] = [[1.0]]
    with pytest.raises(ValueError, match="malformed certificate JSON"):
        certificate_from_json(data)


def test_binary_hash_covers_the_ingest_module():
    from empiricist.certificates import verifier as v

    assert "ingest.py" in v._HASHED_SOURCE_FILES


def test_suite_has_teeth_and_a_stable_hash():
    verdicts = [e for _, e in SOS_GOLDEN_SUITE]
    assert verdicts.count(Verdict.PASS) == 2 and verdicts.count(Verdict.FAIL) == 3
    assert len(sos_suite_hash()) == 64 and sos_suite_hash() == sos_suite_hash()


def test_binary_hash_is_hex_and_stable():
    v = SOSCertificateVerifier()
    assert len(v.binary_hash) == 64 and v.binary_hash == v.binary_hash


def test_certify_sos_stamps_pass(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    try:
        v = SOSCertificateVerifier()
        cert = certify_sos(lg, v)
        assert cert.verdict is Verdict.PASS
        stamp = lg.get_certification(v.name, v.version, v.binary_hash)
        assert stamp.golden_suite_hash == sos_suite_hash()
    finally:
        lg.close()


def test_certify_sos_fails_a_verifier_that_cannot_fail(tmp_path):
    class _AlwaysPass(SOSCertificateVerifier):
        def verify(self, cert):
            from empiricist.verifiers.base import VerifierResult

            return VerifierResult(verdict=Verdict.PASS, details={})

    lg = Ledger(tmp_path / "ledger.db")
    try:
        assert certify_sos(lg, _AlwaysPass()).verdict is Verdict.FAIL
    finally:
        lg.close()

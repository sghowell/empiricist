"""Tests for the verifier certification-stamp store (spec §7, F3)."""

import pytest

from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Certification, Verdict


@pytest.fixture()
def ledger(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    yield lg
    lg.close()


STAMP = Certification(
    verifier="stab_fusion", verifier_version="1.0", binary_hash="abc123",
    golden_suite_hash="suite777", verdict=Verdict.PASS,
)


def test_uncertified_by_default(ledger):
    assert not ledger.is_certified("stab_fusion", "1.0", "abc123")


def test_certify_then_is_certified(ledger):
    ledger.add_certification(STAMP)
    assert ledger.is_certified("stab_fusion", "1.0", "abc123")


def test_fail_stamp_does_not_certify(ledger):
    ledger.add_certification(
        Certification(
            verifier="enum_fusion", verifier_version="1.0", binary_hash="xyz",
            golden_suite_hash="suite777", verdict=Verdict.FAIL,
        )
    )
    assert not ledger.is_certified("enum_fusion", "1.0", "xyz")


def test_certification_is_version_and_binary_specific(ledger):
    ledger.add_certification(STAMP)
    assert not ledger.is_certified("stab_fusion", "1.1", "abc123")
    assert not ledger.is_certified("stab_fusion", "1.0", "other")


def test_recertify_replaces_stamp(ledger):
    ledger.add_certification(STAMP)
    ledger.add_certification(
        Certification(
            verifier="stab_fusion", verifier_version="1.0", binary_hash="abc123",
            golden_suite_hash="suite999", verdict=Verdict.FAIL,
        )
    )
    assert not ledger.is_certified("stab_fusion", "1.0", "abc123")


def test_get_certification_roundtrips_full_stamp(ledger):
    ledger.add_certification(STAMP)
    got = ledger.get_certification("stab_fusion", "1.0", "abc123")
    assert got is not None
    assert got.golden_suite_hash == "suite777" and got.verdict == Verdict.PASS


def test_get_certification_missing_returns_none(ledger):
    assert ledger.get_certification("nope", "0", "0") is None


def test_error_and_timeout_verdicts_do_not_certify(ledger):
    for verdict in (Verdict.ERROR, Verdict.TIMEOUT):
        ledger.add_certification(
            Certification(
                verifier="v", verifier_version="1", binary_hash=verdict.value,
                golden_suite_hash="s", verdict=verdict,
            )
        )
        assert not ledger.is_certified("v", "1", verdict.value)


def test_recertify_pass_to_pass_updates_suite_hash(ledger):
    ledger.add_certification(STAMP)
    ledger.add_certification(
        Certification(
            verifier="stab_fusion", verifier_version="1.0", binary_hash="abc123",
            golden_suite_hash="suite888", verdict=Verdict.PASS,
        )
    )
    got = ledger.get_certification("stab_fusion", "1.0", "abc123")
    assert got.golden_suite_hash == "suite888" and ledger.is_certified(
        "stab_fusion", "1.0", "abc123"
    )

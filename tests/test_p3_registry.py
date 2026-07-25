"""P3SchemeVerifier + its own certification suite (M19 Task 8): wires the P3
two-engine agreed-verdict contract (`verify_scheme_agreed`) into the harness's
certification-stamp discipline (spec §7, F3), the same way M8 wired `LeanVerifier`
in via `certify_with_suite` rather than the fusion-specific `Registry.certify()`/
`Registry.verify()` (whose `verify(construction)` single-argument shape
`verify_scheme_agreed`'s `(scheme, *, claimed_p_min, claimed_p_avg,
claimed_max_leakage)` does not fit)."""

from __future__ import annotations

import pytest

from empiricist.domain.p3.known_schemes import grice_boosted_bsm, standard_bsm
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Verdict
from empiricist.verifiers.base import VerifierResult
from empiricist.verifiers.p3_goldens import P3_GOLDEN_SUITE, certify_p3, p3_suite_hash
from empiricist.verifiers.p3_scheme import P3SchemeVerifier
from empiricist.verifiers.registry import certify_with_suite


@pytest.fixture()
def ledger(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    yield lg
    lg.close()


@pytest.fixture()
def verifier():
    return P3SchemeVerifier()


# -- Discoverability / protocol shape ---------------------------------------


def test_name_version_applicable(verifier):
    assert verifier.name == "p3_scheme_agreed"
    assert verifier.version == "1.0"
    assert verifier.applicable("p3_scheme") is True
    assert verifier.applicable("construction") is False
    assert verifier.applicable("lean") is False


def test_binary_hash_is_stable_and_hex(verifier):
    h1 = verifier.binary_hash
    h2 = P3SchemeVerifier().binary_hash
    assert h1 == h2
    assert len(h1) == 64
    int(h1, 16)  # hex digest -- raises ValueError if not


def test_binary_hash_changes_if_a_hashed_file_changes(verifier, tmp_path, monkeypatch):
    """Tampering with any of the hashed p3 source files must mint a new identity
    (mirrors LeanVerifier/stab_fusion: binary_hash pins the exact trusted code)."""
    import empiricist.verifiers.p3_scheme as p3_scheme_mod

    fake_dir = tmp_path / "fake_p3"
    fake_dir.mkdir()
    for name in p3_scheme_mod._HASHED_SOURCE_FILES:
        (fake_dir / name).write_text("placeholder")
    monkeypatch.setattr(p3_scheme_mod, "_P3_DIR", fake_dir)
    baseline = P3SchemeVerifier().binary_hash

    (fake_dir / "verify.py").write_text("placeholder-changed")
    assert P3SchemeVerifier().binary_hash != baseline


# -- Golden suite teeth -------------------------------------------------------


def test_golden_suite_contains_a_must_fail_case():
    """A suite that cannot fail certifies nothing (spec §7 mutation-resistance)."""
    assert any(expected is Verdict.FAIL for _, _, expected in P3_GOLDEN_SUITE)


def test_golden_suite_covers_both_invalid_mechanisms():
    """Two independent must-fail mechanisms are exercised: a malformed CLAIM and a
    malformed SCHEME, not one repeated case."""
    from empiricist.verifiers.p3_scheme import P3SchemeVerifier as _V

    v = _V()
    verdicts = [
        v.verify(scheme, **kwargs).verdict
        for scheme, kwargs, expected in P3_GOLDEN_SUITE
        if expected is Verdict.FAIL
    ]
    assert all(verdict == Verdict.FAIL for verdict in verdicts)


def test_golden_suite_covers_positive_near_threshold_leakage(verifier):
    """Certification must exercise a well-formed scheme whose sub-threshold
    wrong-label mass violates the default zero-leakage claim."""
    results = [
        verifier.verify(scheme, **kwargs)
        for scheme, kwargs, expected in P3_GOLDEN_SUITE
        if expected is Verdict.FAIL
    ]
    leaky = [result for result in results if result.details.get("leakage", 0.0) > 0.0]
    assert len(leaky) == 1
    assert leaky[0].verdict is Verdict.FAIL
    assert "leakage" in leaky[0].details["detail"]


@pytest.mark.parametrize("bad_verdict", [Verdict.ERROR, Verdict.TIMEOUT])
def test_generic_certification_rejects_error_or_timeout_for_must_fail_case(
    ledger, bad_verdict
):
    """The generic Lean/P3 path also requires exact negative-case verdicts."""

    class ScriptedVerifier:
        name = f"scripted-{bad_verdict.value.lower()}"
        version = "1.0"
        binary_hash = bad_verdict.value.lower() * 8

    outcomes = iter((Verdict.PASS, bad_verdict))

    def run(_verifier, _case):
        return VerifierResult(verdict=next(outcomes))

    cert = certify_with_suite(
        ledger,
        ScriptedVerifier(),
        [("positive", Verdict.PASS), ("negative", Verdict.FAIL)],
        run,
        golden_suite_hash="suite",
    )
    assert cert.verdict is Verdict.FAIL


# -- Certification: registration + hash mechanics -----------------------------


def test_certify_p3_passes_on_the_live_suite(ledger, verifier):
    cert = certify_p3(ledger, verifier)
    assert cert.verdict == Verdict.PASS
    assert cert.verifier == "p3_scheme_agreed"
    assert cert.verifier_version == "1.0"
    assert cert.binary_hash == verifier.binary_hash
    assert cert.golden_suite_hash == p3_suite_hash()


def test_get_certification_lookup_returns_the_stamp(ledger, verifier):
    certify_p3(ledger, verifier)
    got = ledger.get_certification(verifier.name, verifier.version, verifier.binary_hash)
    assert got is not None
    assert got.verdict == Verdict.PASS
    assert got.golden_suite_hash == p3_suite_hash()
    assert ledger.is_certified(verifier.name, verifier.version, verifier.binary_hash)


def test_stamp_is_binary_hash_specific(ledger, verifier):
    """Tampering with the verifier's code must invalidate its stamp (same
    discipline as test_verifiers.py's stab_fusion equivalent)."""
    certify_p3(ledger, verifier)

    class Tampered(P3SchemeVerifier):
        @property
        def binary_hash(self):
            return "0" * 64

    assert not ledger.is_certified("p3_scheme_agreed", "1.0", Tampered().binary_hash)


def test_recertify_replaces_stamp_on_suite_change(ledger, verifier):
    certify_p3(ledger, verifier)
    from empiricist.ledger.models import Certification

    ledger.add_certification(
        Certification(
            verifier=verifier.name, verifier_version=verifier.version,
            binary_hash=verifier.binary_hash, golden_suite_hash="stale-suite-hash",
            verdict=Verdict.PASS,
        )
    )
    got = ledger.get_certification(verifier.name, verifier.version, verifier.binary_hash)
    assert got.golden_suite_hash == "stale-suite-hash"
    assert got.golden_suite_hash != p3_suite_hash()


# -- verify() verdict mapping --------------------------------------------------


def test_standard_bsm_verifies_pass(verifier):
    res = verifier.verify(standard_bsm(), claimed_p_avg=0.5)
    assert res.verdict == Verdict.PASS
    assert res.details["p3_verdict"] == "PASS"
    assert res.details["p_avg"] == pytest.approx(0.5, abs=1e-9)


def test_grice_boosted_bsm_verifies_pass_with_both_claims(verifier):
    res = verifier.verify(grice_boosted_bsm(), claimed_p_avg=0.75, claimed_p_min=0.5)
    assert res.verdict == Verdict.PASS
    assert res.details["p_min"] == pytest.approx(0.5, abs=1e-9)


def test_false_claim_is_honest_fail_not_invalid(verifier):
    res = verifier.verify(standard_bsm(), claimed_p_avg=0.9)
    assert res.verdict == Verdict.FAIL
    assert res.details["p3_verdict"] == "FAIL"
    assert not res.details["detail"].startswith("invalid:")


def test_invalid_claim_maps_to_fail_with_invalid_prefix(verifier):
    """A malformed CLAIM (negative leakage budget): verify_scheme_agreed reports
    INVALID; P3SchemeVerifier maps it to FAIL (no Verdict.INVALID exists) with the
    detail prefixed so a ledger reader can tell it apart from an honest miss."""
    res = verifier.verify(standard_bsm(), claimed_max_leakage=-1.0)
    assert res.verdict == Verdict.FAIL
    assert res.details["p3_verdict"] == "INVALID"
    assert res.details["detail"].startswith("invalid:")


def test_invalid_scheme_maps_to_fail_with_invalid_prefix(verifier):
    """A malformed SCHEME (mesh/scheme mode mismatch): same INVALID->FAIL mapping,
    exercised through the OTHER screening branch (scheme.validate(), not the claim
    finiteness guard)."""
    from empiricist.domain.p3.interferometer import Mesh
    from empiricist.domain.p3.scheme import BellScheme

    bad = BellScheme(n_modes=4, n_ancilla_photons=0, ancilla={},
                      mesh=Mesh(n_modes=5, elements=()))
    res = verifier.verify(bad)
    assert res.verdict == Verdict.FAIL
    assert res.details["p3_verdict"] == "INVALID"
    assert res.details["detail"].startswith("invalid:")


def test_engine_exception_is_error_verdict_not_crash(verifier, monkeypatch):
    """verify() is total: an engine raise on a VALIDATED scheme becomes an ERROR
    verdict with the message in details, never a crash (mirrors
    stab_fusion/enum_fusion's own never-raise discipline, one layer up)."""
    import empiricist.domain.p3.verify as p3_verify_mod

    def boom(*a, **k):
        raise RuntimeError("engine exploded")

    monkeypatch.setattr(p3_verify_mod, "evaluate_scheme", boom)
    res = verifier.verify(standard_bsm(), claimed_p_avg=0.5)
    assert res.verdict == Verdict.ERROR
    assert "error" in res.details
    assert "engine exploded" in res.details["error"]


def test_verify_never_raises_on_unexpected_wrapper_exception(verifier, monkeypatch):
    """Defense-in-depth: even if something ABOVE verify_scheme_agreed's own total
    contract throws (e.g. a bug in this wrapper's own call), verify() must still
    report ERROR rather than propagate."""
    import empiricist.verifiers.p3_scheme as p3_scheme_mod

    def boom(*a, **k):
        raise RuntimeError("wrapper-level bug")

    monkeypatch.setattr(p3_scheme_mod, "verify_scheme_agreed", boom)
    res = verifier.verify(standard_bsm(), claimed_p_avg=0.5)
    assert res.verdict == Verdict.ERROR
    assert "wrapper-level bug" in res.details["error"]

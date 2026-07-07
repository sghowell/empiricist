"""Verifier protocol + certification-gated registry (spec §7, F3)."""

import pytest

from empiricist.domain.p5.construction import Construction, FusionOp
from empiricist.domain.p5.graphstate import GraphState
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Verdict
from empiricist.verifiers.enum_fusion import EnumFusionVerifier
from empiricist.verifiers.goldens import P5_GOLDEN_SUITE, suite_hash
from empiricist.verifiers.registry import Registry, UncertifiedVerifierError
from empiricist.verifiers.stab_fusion import StabFusionVerifier

P4 = Construction(resources=2, steps=(FusionOp(a=2, b=4),),
                  target=GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)]))
WRONG = Construction(resources=2, steps=(FusionOp(a=2, b=4),),
                     target=GraphState(n=4, edges=[(0, 1), (0, 2), (0, 3)]))


@pytest.fixture()
def registry(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    yield Registry(lg)
    lg.close()


def test_verify_refused_without_certification(registry):
    v = StabFusionVerifier()
    with pytest.raises(UncertifiedVerifierError):
        registry.verify(v, P4)


def test_certify_then_verify_pass(registry):
    v = StabFusionVerifier()
    stamp = registry.certify(v)
    assert stamp.verdict == Verdict.PASS
    assert stamp.golden_suite_hash == suite_hash()
    res = registry.verify(v, P4)
    assert res.verdict == Verdict.PASS
    assert "lc_orbit_key" in res.details


def test_wrong_target_fails_verification(registry):
    v = StabFusionVerifier()
    registry.certify(v)
    assert registry.verify(v, WRONG).verdict == Verdict.FAIL


def test_both_verifiers_certify_and_agree(registry):
    a, b = StabFusionVerifier(), EnumFusionVerifier()
    assert registry.certify(a).verdict == Verdict.PASS
    assert registry.certify(b).verdict == Verdict.PASS
    from empiricist.verifiers.registry import verify_agreed
    res = verify_agreed(registry, P4)
    assert res.verdict == Verdict.PASS
    assert res.details["stab_fusion_key"] == res.details["enum_fusion_key"]


def test_agreement_fails_on_wrong_target(registry):
    registry.certify(StabFusionVerifier())
    registry.certify(EnumFusionVerifier())
    from empiricist.verifiers.registry import verify_agreed
    assert verify_agreed(registry, WRONG).verdict == Verdict.FAIL


def test_golden_suite_contains_a_must_fail_case():
    """A suite that cannot fail certifies nothing (spec §7 mutation-resistance)."""
    assert any(expected is False for _, expected in P5_GOLDEN_SUITE)


def test_stamp_is_binary_hash_specific(registry):
    """Tampering with the verifier's code must invalidate its stamp."""
    v = StabFusionVerifier()
    registry.certify(v)
    class Tampered(StabFusionVerifier):
        @property
        def binary_hash(self):
            return "0" * 64
    with pytest.raises(UncertifiedVerifierError):
        registry.verify(Tampered(), P4)


def test_engine_error_is_error_verdict_not_crash(registry):
    v = StabFusionVerifier()
    registry.certify(v)
    bad = Construction(resources=2, steps=(FusionOp(a=0, b=0),),
                       target=GraphState(n=4, edges=[]))
    res = registry.verify(v, bad)
    assert res.verdict == Verdict.ERROR and "error" in res.details

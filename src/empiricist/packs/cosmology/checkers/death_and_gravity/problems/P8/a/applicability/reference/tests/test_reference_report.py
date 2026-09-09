import copy
import json

import pytest
from p8a_reference import verify


@pytest.fixture(scope="module")
def replay():
    return verify.build_report()


def test_prior_a2_and_a1_replay_unchanged():
    assert verify.prior_checks() == verify.PRIOR_SHA


def test_new_certificate_replays_without_writing(replay):
    before = verify.REPORT.read_bytes()
    verify.validate_report(json.loads(before), replay)
    assert verify.REPORT.read_bytes() == before


@pytest.mark.parametrize("field,value", [
    ("status", "NEW_COSMOLOGICAL_SINGULARITY_THEOREM"),
    ("source_sha256", {}),
    ("prior_A2_sha256", "changed"),
    ("not_established", []),
    ("verification_boundary", []),
])
def test_changed_sources_or_overclaims_rejected(replay, field, value):
    changed = copy.deepcopy(replay)
    changed[field] = value
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(changed, replay)


def test_zeroed_or_sign_flipped_reference_rejected(replay):
    for value in ("0", "-hbar/(5120*pi**2*t**4)"):
        changed = copy.deepcopy(replay)
        changed["reference_stress_and_state_derivation"]["reference_stress"]["EED_FK"] = value
        with pytest.raises(ValueError, match="differs"):
            verify.validate_report(changed, replay)


def test_silent_see_promotion_rejected(replay):
    changed = copy.deepcopy(replay)
    changed["scope"]["reference_state_SEE_solution_established"] = True
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(changed, replay)


def test_nonzero_derivation_residual_rejected():
    with pytest.raises(ValueError, match="Nonzero"):
        verify.verified_residuals({"residuals": {"wrong_EED_sign": 1}})

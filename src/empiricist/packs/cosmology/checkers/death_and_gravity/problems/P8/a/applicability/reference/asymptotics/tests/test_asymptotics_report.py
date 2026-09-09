"""A.4 replay checks with a repository-unique pytest module name."""

import copy
import json

import pytest
from p8a_asymptotics import verify


@pytest.fixture(scope="module")
def replay():
    return verify.build_report()


def test_prior_a3_a2_a1_replay_unchanged():
    assert verify.prior_checks() == verify.PRIOR_SHA


def test_new_certificate_replays_without_writing(replay):
    before = verify.REPORT.read_bytes()
    verify.validate_report(json.loads(before), replay)
    assert verify.REPORT.read_bytes() == before


@pytest.mark.parametrize("field,value", [
    ("status", "NEW_COSMOLOGICAL_SINGULARITY_THEOREM"),
    ("source_sha256", {}),
    ("prior_A3_sha256", "changed"),
    ("verification_boundary", []),
    ("not_established", []),
])
def test_changed_hashes_or_overclaims_rejected(replay, field, value):
    changed = copy.deepcopy(replay)
    changed[field] = value
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(changed, replay)


@pytest.mark.parametrize("field", [
    "finite_slab_SEE_incompatibility_established",
    "new_incompleteness_theorem_established",
    "all_state_pointwise_nonnegative_EED_at_all_times_established",
    "uniform_over_states_rate_or_positive_onset_time_established",
    "other_traceful_or_quantum_sources_included",
])
def test_scope_expansion_rejected(replay, field):
    changed = copy.deepcopy(replay)
    changed["scope"][field] = True
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(changed, replay)


def test_zeroed_reference_coefficient_rejected(replay):
    changed = copy.deepcopy(replay)
    changed["EED_scaling_and_SEE_derivation"]["universal_proper_EED_coefficient"] = "0"
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(changed, replay)


def test_omitted_mixed_data_control_rejected(replay):
    changed = copy.deepcopy(replay)
    changed["two_variable_Cauchy_benchmark"]["omitted_mixed_data_control_is_nonzero"] = False
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(changed, replay)


def test_nonzero_residual_rejected():
    with pytest.raises(ValueError, match="Nonzero"):
        verify.verified_residuals({"residuals": {"bad_chain_rule": 1}})

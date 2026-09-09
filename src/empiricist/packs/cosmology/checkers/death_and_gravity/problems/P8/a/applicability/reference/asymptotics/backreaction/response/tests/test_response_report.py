import copy
import json

import pytest
from p8a_response import verify


@pytest.fixture(scope="module")
def replay():
    return verify.build_report()


def test_prior_a5_and_all_dependencies_replay_unchanged():
    assert verify.prior_checks() == verify.PRIOR_SHA


def test_new_certificate_replays_without_writing(replay):
    before = verify.REPORT.read_bytes()
    verify.validate_report(json.loads(before), replay)
    assert verify.REPORT.read_bytes() == before


@pytest.mark.parametrize("field,value", [
    ("status", "EXACT_SEE_SOLUTION"), ("prior_A5_sha256", "changed"),
    ("source_sha256", {}), ("verification_boundary", []),
])
def test_hash_and_scope_tampering_rejected(replay, field, value):
    changed = copy.deepcopy(replay)
    changed[field] = value
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(changed, replay)


@pytest.mark.parametrize("field", [
    "arbitrary_preparation_norm_tuples_certified_automatically",
    "finite_epsilon_RSET_remainder_bound", "uniform_parameter_interval_response_bound",
    "numerical_cubic_residual_remainder_bound", "exact_SEE_solution_or_stability_theorem",
    "quantitative_perturbed_QSEI_or_all_sampler_bound", "cosmological_focusing_or_P8a_completion",
])
def test_unearned_promotion_rejected(replay, field):
    changed = copy.deepcopy(replay)
    changed["scope"][field] = True
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(changed, replay)


def test_coarse_actual_norm_bound_cannot_be_changed(replay):
    changed = copy.deepcopy(replay)
    changed["specific_smooth_preparation"]["exact_independent_bounds"]["response_constants"]["density"] = "1"
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(changed, replay)


def test_nonzero_identity_rejected():
    with pytest.raises(ValueError, match="Nonzero"):
        verify.verified_residuals({"wrong_kernel_constant": 1})

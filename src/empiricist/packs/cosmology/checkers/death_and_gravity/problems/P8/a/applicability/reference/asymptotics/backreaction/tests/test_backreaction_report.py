import copy
import json

import pytest
from p8a_backreaction import verify


@pytest.fixture(scope="module")
def replay():
    return verify.build_report()


def test_prior_a4_and_all_dependencies_replay_unchanged():
    assert verify.prior_checks() == verify.PRIOR_SHA


def test_new_certificate_replays_without_writing(replay):
    before = verify.REPORT.read_bytes()
    verify.validate_report(json.loads(before), replay)
    assert verify.REPORT.read_bytes() == before


@pytest.mark.parametrize("field,value", [
    ("status", "EXACT_SEE_SOLUTION"), ("prior_A4_sha256", "changed"),
    ("source_sha256", {}), ("verification_boundary", []), ("not_established", []),
])
def test_source_hash_or_boundary_tampering_rejected(replay, field, value):
    changed = copy.deepcopy(replay)
    changed[field] = value
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(changed, replay)


@pytest.mark.parametrize("field", [
    "surrogate_source_identified_with_actual_RSET",
    "surrogate_all_order_completion_uniquely_fixed_by_first_order_SEE",
    "independent_order_zero_curvature_squared_couplings_allowed",
    "numerical_actual_RSET_response_bound_derived",
    "nearby_exact_SEE_solution_or_stability_theorem_established",
    "QSEI_on_perturbed_metric_quantitatively_calibrated",
    "fixed_h_QSEI_smoothness_promoted_from_diagonal_stress_alone",
    "uniform_all_h_H2_QSEI_bound_established",
    "physical_singularity_at_surrogate_zero_established",
])
def test_unearned_physical_promotion_rejected(replay, field):
    changed = copy.deepcopy(replay)
    changed["scope"][field] = True
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(changed, replay)


def test_synthetic_response_cannot_be_relabelled_as_physical(replay):
    changed = copy.deepcopy(replay)
    changed["finite_slab_arithmetic_example"]["synthetic_response_inputs_are_claimed_actual_quantum_bounds"] = True
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(changed, replay)


def test_nonzero_residual_rejected():
    with pytest.raises(ValueError, match="Nonzero"):
        verify.verified_residuals({"residuals": {"wrong_integrated_equation": 192}})

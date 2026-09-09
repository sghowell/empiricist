import copy
import json

import pytest
from p8a_remainder import verify


@pytest.fixture(scope="module")
def replay():
    return verify.build_report()


def test_remainder_new_certificate_replays_without_writing(replay):
    before = verify.REPORT.read_bytes()
    verify.validate_report(json.loads(before), replay)
    assert verify.REPORT.read_bytes() == before
    assert replay["prior_A6_sha256"] == verify.PRIOR_SHA


def test_remainder_reserved_independent_audit_is_source_pinned(replay):
    assert "tests/test_remainder_gelfand_dikii_audit.py" in replay["source_sha256"]
    assert "src/p8a_remainder/independent.py" in replay["source_sha256"]


@pytest.mark.parametrize("field,value", [("status", "EXACT_SEE_SOLUTION"),
    ("prior_A6_sha256", "changed"), ("source_sha256", {}), ("verification_boundary", [])])
def test_remainder_hash_and_scope_tampering_rejected(replay, field, value):
    changed = copy.deepcopy(replay)
    changed[field] = value
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(changed, replay)


@pytest.mark.parametrize("field", ["absolute_RSET_scheme_independence",
    "unconstrained_supplied_jet_bounds_automatically_certified", "Born_functional_claimed_positive_state",
    "A6_epsilon_linear_formula_has_same_error_without_clock_comparison",
    "A6_second_order_corrected_metric_jets_certified_here", "finite_amplitude_SEE_solution_shadowing_or_stability",
    "quantitative_perturbed_QSEI_or_all_sampler_bound", "all_geodesic_focusing_or_P8a_completion"])
def test_remainder_unearned_promotion_rejected(replay, field):
    changed = copy.deepcopy(replay)
    changed["scope"][field] = True
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(changed, replay)


def test_remainder_finite_bound_cannot_be_changed(replay):
    changed = copy.deepcopy(replay)
    changed["independently_replayed_uniform_bounds"]["stress_error_constants"]["density"] = "1"
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(changed, replay)


def test_remainder_prior_certificate_hash_tampering_rejected(tmp_path, monkeypatch):
    changed = tmp_path/"changed.json"
    changed.write_text("{}")
    monkeypatch.setattr(verify.prior, "REPORT", changed)
    with pytest.raises(ValueError, match="Pinned A.6"):
        verify.prior_checks()


def test_remainder_nonzero_identity_and_lost_negative_control_rejected():
    with pytest.raises(ValueError, match="Nonzero"):
        verify.verified_residuals({"wrong": 1})
    with pytest.raises(ValueError, match="vanished"):
        verify.verified_exclusion("wrong", 0)

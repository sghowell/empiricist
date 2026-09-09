import copy
import json

import pytest
from p8a_radiation import verify


def test_prior_A1_checkpoint_is_unchanged_and_replays():
    assert verify.prior_checks() == verify.PRIOR_SHA


def test_pinned_report_is_read_only_and_replays():
    before = verify.REPORT.read_bytes()
    verify.validate_report(json.loads(before), verify.build_report())
    assert verify.REPORT.read_bytes() == before


@pytest.mark.parametrize("field,value", [("status", "NEW_COSMOLOGICAL_SINGULARITY_THEOREM"),
                                        ("source_sha256", {}),
                                        ("not_established", [])])
def test_changed_sources_and_overclaims_rejected(field, value):
    actual = verify.build_report()
    changed = copy.deepcopy(actual)
    changed[field] = value
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(changed, actual)


def test_silently_removing_reference_state_is_rejected():
    actual = verify.build_report()
    changed = copy.deepcopy(actual)
    changed["scope"]["renormalized_reference_EED"] = "ZERO"
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(changed, actual)
    with pytest.raises(ValueError, match="Nonzero"):
        verify.verified_residuals({"residuals": {"wrong_sign": 1}})

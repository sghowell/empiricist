import copy
import json

import pytest
from p8a import verify


def test_independent_FLINT_exact_integrals_and_geometric_tail():
    result = verify.independent_checks()
    assert all(value == "0" for row in result["finite_sum_plus_remainder_residuals"] for value in row)


def test_pinned_report_replays_read_only():
    before = verify.REPORT.read_bytes()
    verify.validate_report(json.loads(before), verify.build_report())
    assert verify.REPORT.read_bytes() == before


@pytest.mark.parametrize("field,value", [("status", "REALISTIC_FIELD_P8A_COMPLETE"),
                                        ("source_sha256", {}),
                                        ("support_coverage", {"strict_containment": False}),
                                        ("not_established", [])])
def test_changed_sources_coverage_or_overclaim_rejected(field, value):
    actual = verify.build_report()
    altered = copy.deepcopy(actual)
    altered[field] = value
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(altered, actual)


def test_nonzero_algebra_and_misstated_threshold_rejected():
    with pytest.raises(ValueError, match="Nonzero"):
        verify.require_zero({"bad": 1})
    actual = verify.build_report()
    altered = copy.deepcopy(actual)
    altered["validated_enclosures"]["optimized_threshold"]["upper"] = "4"
    with pytest.raises(ValueError, match="differs"):
        verify.validate_report(altered, actual)

from copy import deepcopy
from fractions import Fraction

import pytest
from p8 import candidate_cert, rational_candidates
from p8.verify_all import build_reports, check_reports, validate_report


def test_complete_persisted_chain_replays():
    reports = check_reports()
    assert len(reports) == 6
    classification = reports["classification.json"]
    assert classification["minimal_supports"] == {"M0": ["C", "D"], "M1": ["CD"]}
    assert len(classification["rows"]) == 16
    assert classification["not_established"]


@pytest.mark.parametrize("name", ("s1-derived-action.json", "a25-regression.json", "witness-C.json",
                                  "witness-D.json", "witness-CD_matter.json", "classification.json"))
def test_each_modified_report_is_rejected(name):
    current = build_reports()[name]
    altered = deepcopy(current)
    altered["scope"] = "UV-complete cosmology (invalid scope expansion)"
    with pytest.raises(ValueError, match="differs from exact replay"):
        validate_report(name, altered, current)


def test_saved_Arb_endpoints_retain_strict_signs_and_chart_conditions():
    for tile in build_reports()["a25-regression.json"]["tiles"]:
        for key in ("a", "J", "P", "J_minus_P"):
            assert 0 < Fraction(tile["bounds"][key][0]) <= Fraction(tile["bounds"][key][1])
        if tile["chart"] == "unitary":
            lo, hi = map(Fraction, tile["bounds"]["Theta"])
            assert lo > 0 or hi < 0
        else:
            assert Fraction(tile["bounds"]["Lambda"][1]) < 0
            assert Fraction(tile["bounds"]["Theta_dot"][0]) > 0


def test_changed_operator_support_is_not_silently_inherited(monkeypatch):
    result = deepcopy(rational_candidates.reconstruct("C"))
    result["A3"] = rational_candidates.X
    monkeypatch.setattr(rational_candidates, "reconstruct", lambda _: result)
    with pytest.raises(ValueError, match="support"):
        candidate_cert.build("C")

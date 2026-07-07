"""Tests for pydantic role-output schemas and their JSON-schema export."""

import pytest
from pydantic import ValidationError

from empiricist.llm.schemas import ConjectureOut, CritiqueOut, json_schema_for


def test_conjecture_out_validates_a_wellformed_object():
    obj = ConjectureOut(
        family="path", closed_form="N-3", predicted_values={"3": 0, "4": 1},
        confidence=0.7,
    )
    assert obj.family == "path" and obj.predicted_values["4"] == 1


def test_conjecture_out_rejects_missing_field():
    with pytest.raises(ValidationError):
        ConjectureOut(family="path", closed_form="N-3")  # missing predicted_values


def test_critique_out_gap_or_no_gap():
    gap = CritiqueOut(verdict="GAP", location="lemma 2, line 5",
                      detail="unjustified step", edges_checked=[])
    nogap = CritiqueOut(verdict="NO_GAP_FOUND", location=None, detail=None,
                        edges_checked=["l1->l2", "l2->l3"])
    assert gap.verdict == "GAP" and nogap.verdict == "NO_GAP_FOUND"


def test_critique_out_rejects_bad_verdict():
    with pytest.raises(ValidationError):
        CritiqueOut(verdict="MAYBE", location=None, detail=None, edges_checked=[])


def test_json_schema_for_produces_cli_ready_dict():
    schema = json_schema_for(ConjectureOut)
    assert schema["type"] == "object"
    assert "family" in schema["properties"]
    # additionalProperties must be false so the CLI enforces a closed shape.
    assert schema.get("additionalProperties") is False


def test_json_schema_is_json_serializable():
    import json
    json.dumps(json_schema_for(CritiqueOut))  # must not raise

"""Tests for `formalize/schemas.py`'s `LeanModuleOut` (M18): the Formalizer's
structured output. Schema-valid guarantees SHAPE only (spec §5.2) -- these
tests check round-trip + CLI-schema readiness + adversarial rejection, never
that a `module_source` actually compiles (that's `LeanVerifier`'s job)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from empiricist.formalize.schemas import LeanModuleOut
from empiricist.llm.schemas import json_schema_for

_MODULE_SOURCE = (
    "import Mathlib\n"
    "namespace Empiricist\n"
    "theorem loop_smoke : True := trivial\n"
    "end Empiricist\n"
)


def test_round_trip_with_notes():
    out = LeanModuleOut(
        module_source=_MODULE_SOURCE, decl="Empiricist.loop_smoke", notes="trivial smoke"
    )
    dumped = out.model_dump(mode="json")
    restored = LeanModuleOut.model_validate(dumped)
    assert restored == out
    assert restored.module_source == _MODULE_SOURCE
    assert restored.decl == "Empiricist.loop_smoke"
    assert restored.notes == "trivial smoke"


def test_notes_defaults_to_empty_string():
    out = LeanModuleOut(module_source=_MODULE_SOURCE, decl="Empiricist.loop_smoke")
    assert out.notes == ""


def test_json_schema_is_cli_ready():
    schema = json_schema_for(LeanModuleOut)
    # additionalProperties:false -> the CLI enforces a closed shape (spec §5.2).
    assert schema["additionalProperties"] is False
    # JSON-serializable (a --json-schema argv value must round-trip through
    # json.dumps without error).
    json.dumps(schema)
    assert set(schema["required"]) == {"module_source", "decl"}
    assert "notes" not in schema["required"]
    props = schema["properties"]
    assert props["module_source"]["type"] == "string"
    assert props["decl"]["type"] == "string"
    assert props["notes"]["type"] == "string"


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        LeanModuleOut.model_validate({
            "module_source": _MODULE_SOURCE,
            "decl": "Empiricist.loop_smoke",
            "bogus_extra_field": True,
        })


def test_missing_required_field_rejected():
    with pytest.raises(ValidationError):
        LeanModuleOut.model_validate({"decl": "Empiricist.loop_smoke"})
    with pytest.raises(ValidationError):
        LeanModuleOut.model_validate({"module_source": _MODULE_SOURCE})

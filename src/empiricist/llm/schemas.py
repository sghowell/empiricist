"""Pydantic output schemas per role + JSON-schema export for `--json-schema`.

Schemas guarantee SHAPE only, never mathematical truth (spec §5.2): a
schema-valid Conjecture can still be false — the verifiers decide truth.
Keep schemas free of numeric bounds / recursion (unsupported by the CLI
json-schema path); use additionalProperties:false for a closed shape.

Domain-specific schemas that belong to a problem (e.g. the P5 fusion
Construction) live with that problem's package; these are the cross-role
schemas the LLM layer needs to function and be tested.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class _Closed(BaseModel):
    """Base: forbid unspecified fields so the exported schema is closed."""

    model_config = ConfigDict(extra="forbid")


class ConjectureOut(_Closed):
    family: str
    closed_form: str
    predicted_values: dict[str, int]
    confidence: float


class CritiqueOut(_Closed):
    verdict: Literal["GAP", "NO_GAP_FOUND"]
    location: str | None
    detail: str | None
    edges_checked: list[str]


def json_schema_for(model: type[BaseModel]) -> dict[str, Any]:
    """The model's JSON schema, ready to pass to `claude --json-schema`.

    pydantic emits `additionalProperties: false` for extra='forbid' models,
    which is what makes the CLI enforce a closed object.
    """
    return model.model_json_schema()

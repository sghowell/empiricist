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


# -- P3 (Bell-measurement schemes): the Constructor's structured output --------
# `BellSchemeOut` is the model-facing shape for a linear-optical Bell scheme:
# the interferometer mesh, an optional ancilla input state, and the claims the
# model is making about it. `MeshElement`/`AncillaTerm` are `_Closed`
# sub-models rather than bare tuples: pydantic handles nested models more
# precisely than untyped tuples, and the JSON a model emits reads more clearly
# with named fields. `MeshElement` covers BOTH mesh element kinds via unused
# fields (`j`/`phi` ignored for "phase"; `theta` doubles as `alpha`) rather
# than a discriminated union -- the same CLI-schema-safe, flat-tagged
# convention `search/schemas.py` documents for its `StepOut`.
# `domain.p3.scheme.scheme_from_out` converts a validated `BellSchemeOut` into
# a `BellScheme`. Per the M4 discipline this schema guarantees SHAPE only --
# `verify_scheme_agreed` is the sole arbiter of physics truth.
class MeshElement(_Closed):
    kind: Literal["bs", "phase"]
    i: int
    j: int = 0            # unused for "phase"
    theta: float = 0.0    # alpha for "phase"
    phi: float = 0.0      # unused for "phase"


class AncillaTerm(_Closed):
    pattern: list[int]
    re: float
    im: float


class BellSchemeOut(_Closed):
    n_modes: int
    n_ancilla_photons: int
    ancilla: list[AncillaTerm]      # [] means no ancilla (4-mode schemes only)
    mesh: list[MeshElement]
    claimed_p_min: float | None = None
    claimed_p_avg: float | None = None
    claimed_max_leakage: float = 0.0
    notes: str = ""


def json_schema_for(model: type[BaseModel]) -> dict[str, Any]:
    """The model's JSON schema, ready to pass to `claude --json-schema`.

    pydantic emits `additionalProperties: false` for extra='forbid' models,
    which is what makes the CLI enforce a closed object.
    """
    return model.model_json_schema()

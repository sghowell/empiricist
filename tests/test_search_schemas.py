"""Tests for the Searcher's construction schema + millisecond screen gate
(M6 T2, spec §4/§9): ConstructionOut/StepOut shape, `to_construction`'s
ScreenReject discipline, and CLI-readiness of the exported JSON schema.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.construction import FusionOp, LocalComplement, apply_construction
from empiricist.domain.p5.fusion_stim import StimEngine
from empiricist.domain.p5.graphstate import GraphState
from empiricist.llm.schemas import json_schema_for
from empiricist.search.schemas import ConstructionOut, ScreenReject, StepOut, to_construction

# -- valid round-trips ---------------------------------------------------------


def test_p4_construction_round_trips_and_verifies_on_stim_engine():
    out = ConstructionOut(
        resources=2,
        steps=[StepOut(op="fuse", args=[2, 4])],
        target_n=4,
        target_edges=[[0, 1], [1, 2], [2, 3]],
    )
    c = to_construction(out)
    assert c.resources == 2
    assert c.steps == (FusionOp(a=2, b=4),)
    assert c.fusion_count == 1

    result = apply_construction(c, StimEngine())
    assert lc_orbit_key(result) == lc_orbit_key(c.target)


def test_lc_step_converts_to_local_complement():
    out = ConstructionOut(
        resources=1,
        steps=[StepOut(op="lc", args=[1])],
        target_n=3,
        target_edges=[[0, 1], [0, 2]],
    )
    c = to_construction(out)
    assert c.steps == (LocalComplement(v=1),)
    assert c.fusion_count == 0


def test_mixed_fuse_and_lc_steps_convert_in_order():
    out = ConstructionOut(
        resources=2,
        steps=[
            StepOut(op="lc", args=[0]),
            StepOut(op="fuse", args=[2, 4]),
        ],
        target_n=4,
        target_edges=[[0, 1], [1, 2], [2, 3]],
    )
    c = to_construction(out)
    assert c.steps == (LocalComplement(v=0), FusionOp(a=2, b=4))


def test_duplicate_target_edge_is_normalized_not_rejected():
    # GraphState dedups its edge set; a duplicate listing is not, by itself,
    # evidence of a malformed graph, so to_construction tolerates it.
    out = ConstructionOut(
        resources=2,
        steps=[StepOut(op="fuse", args=[2, 4])],
        target_n=4,
        target_edges=[[0, 1], [1, 2], [2, 3], [1, 2]],  # (1,2) listed twice
    )
    c = to_construction(out)
    assert c.target == GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    assert len(c.target.edges) == 3


# -- adversarial rejects: each a distinct reason -------------------------------


def test_negative_qubit_in_fuse_rejected():
    out = ConstructionOut(
        resources=2, steps=[StepOut(op="fuse", args=[-1, 2])],
        target_n=4, target_edges=[[0, 1]],
    )
    with pytest.raises(ScreenReject) as exc:
        to_construction(out)
    assert "non-negative" in exc.value.reason


def test_negative_qubit_in_lc_rejected():
    out = ConstructionOut(
        resources=1, steps=[StepOut(op="lc", args=[-2])],
        target_n=3, target_edges=[[0, 1]],
    )
    with pytest.raises(ScreenReject) as exc:
        to_construction(out)
    assert "non-negative" in exc.value.reason


def test_fuse_self_pair_rejected():
    out = ConstructionOut(
        resources=2, steps=[StepOut(op="fuse", args=[2, 2])],
        target_n=4, target_edges=[[0, 1]],
    )
    with pytest.raises(ScreenReject) as exc:
        to_construction(out)
    assert "distinct" in exc.value.reason


def test_fuse_with_three_args_rejected():
    out = ConstructionOut(
        resources=2, steps=[StepOut(op="fuse", args=[0, 1, 2])],
        target_n=4, target_edges=[[0, 1]],
    )
    with pytest.raises(ScreenReject) as exc:
        to_construction(out)
    assert "fuse requires exactly 2 args" in exc.value.reason


def test_lc_with_two_args_rejected():
    out = ConstructionOut(
        resources=1, steps=[StepOut(op="lc", args=[0, 1])],
        target_n=3, target_edges=[[0, 1]],
    )
    with pytest.raises(ScreenReject) as exc:
        to_construction(out)
    assert "lc requires exactly 1 arg" in exc.value.reason


def test_wrong_size_identity_rejected():
    out = ConstructionOut(
        resources=2, steps=[StepOut(op="fuse", args=[2, 4])],
        target_n=5,  # should be 3*2 - 2*1 = 4
        target_edges=[[0, 1]],
    )
    with pytest.raises(ScreenReject) as exc:
        to_construction(out)
    assert "size identity" in exc.value.reason


def test_out_of_range_edge_rejected():
    out = ConstructionOut(
        resources=2, steps=[StepOut(op="fuse", args=[2, 4])],
        target_n=4, target_edges=[[0, 4]],  # 4 is out of range for n=4
    )
    with pytest.raises(ScreenReject) as exc:
        to_construction(out)
    assert "out of range" in exc.value.reason


def test_zero_resources_rejected():
    out = ConstructionOut(resources=0, steps=[], target_n=0, target_edges=[])
    with pytest.raises(ScreenReject) as exc:
        to_construction(out)
    assert "resources" in exc.value.reason


def test_self_loop_edge_rejected():
    out = ConstructionOut(
        resources=1, steps=[], target_n=3, target_edges=[[1, 1]],
    )
    with pytest.raises(ScreenReject) as exc:
        to_construction(out)
    assert "self-loop" in exc.value.reason


# -- pydantic-level shape enforcement ------------------------------------------


def test_construction_out_rejects_extra_fields():
    with pytest.raises(ValidationError):
        ConstructionOut(
            resources=1, steps=[], target_n=0, target_edges=[], bogus=True,
        )


def test_step_out_rejects_extra_fields():
    with pytest.raises(ValidationError):
        StepOut(op="fuse", args=[0, 1], bogus=True)


def test_step_out_rejects_bad_op():
    with pytest.raises(ValidationError):
        StepOut(op="frobnicate", args=[0, 1])


# -- CLI-readiness of the exported json schema ---------------------------------


def test_json_schema_top_level_is_closed():
    schema = json_schema_for(ConstructionOut)
    assert schema["type"] == "object"
    assert schema.get("additionalProperties") is False
    for field in ("resources", "steps", "target_n", "target_edges"):
        assert field in schema["properties"]


def test_json_schema_nested_step_out_appears_via_defs_and_is_also_closed():
    schema = json_schema_for(ConstructionOut)
    defs = schema.get("$defs", {})
    assert "StepOut" in defs
    step_schema = defs["StepOut"]
    assert step_schema.get("additionalProperties") is False
    assert "op" in step_schema["properties"]
    assert "args" in step_schema["properties"]
    # steps: list[StepOut] is wired via $ref, not an inline duplicate.
    assert schema["properties"]["steps"]["items"]["$ref"] == "#/$defs/StepOut"


def test_json_schema_is_json_serializable():
    json.dumps(json_schema_for(ConstructionOut))  # must not raise

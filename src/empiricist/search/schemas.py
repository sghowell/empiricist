"""The Searcher's construction schema + millisecond screen gate (M6 T2,
spec §4/§9).

`ConstructionOut` is the flat, tagged-union-free shape the Searcher role
emits: each step carries `op` (a `Literal["fuse", "lc"]`) plus a single
flat `args: list[int]`, rather than a discriminated Pydantic union --
the CLI's `--json-schema` path (verified in M4, `llm/schemas.py`'s
docstring) does not reliably support oneOf/anyOf-of-objects, so a flat
tagged form is the CLI-schema-safe convention used throughout this layer.
Reuses `llm.schemas._Closed` (`extra="forbid"`) so both `ConstructionOut`
and `StepOut` export a closed shape.

Nesting itself IS fine: `StepOut` appears in `ConstructionOut`'s exported
schema via `$defs` + a `$ref` (not inlined), and pydantic emits
`additionalProperties: false` BOTH at the top level and inside the nested
`$defs` entry. Verified empirically here (`tests/test_search_schemas.py`'s
CLI-readiness tests: `json.dumps` on the schema must not raise, the
top-level object and the `$defs.StepOut` object must both be closed) and
consistent with the M4 finding that `claude --json-schema` tolerates the
extra `$defs`/`$ref` machinery pydantic emits for nested models -- it only
requires a valid, closed-at-every-object-level JSON Schema.

`to_construction` is the SCREEN tier: the millisecond gate (spec §4) that
runs BEFORE the expensive certified `verify_agreed` call. It converts a
schema-valid (but not yet semantically valid) `ConstructionOut` into a
domain `Construction`, or raises `ScreenReject` with a human-readable
`.reason` for every possible malformed shape -- a raw `ValueError` /
`IndexError` escaping this function would be a bug in the screen, since
the whole point of this tier is that model output is NEVER trusted and
NEVER allowed to crash the search loop. Downstream domain validation
(`GraphState`'s self-loop/out-of-range checks, `Construction`'s qubit-count
identity) is still exercised for defense in depth, but always through a
`try`/`except` that re-wraps as `ScreenReject`.

Duplicate target edges are NOT rejected: `GraphState`'s own constructor
normalizes the edge set (dedup via `frozenset`), so a duplicate listing is
tolerated as a no-op, not treated as a screen failure (see
`test_duplicate_target_edge_is_normalized_not_rejected`).
"""

from __future__ import annotations

from typing import Literal

from empiricist.domain.p5.construction import Construction, FusionOp, LocalComplement
from empiricist.domain.p5.graphstate import GraphState
from empiricist.llm.schemas import _Closed


class StepOut(_Closed):
    op: Literal["fuse", "lc"]
    args: list[int]


class ConstructionOut(_Closed):
    resources: int
    steps: list[StepOut]
    target_n: int
    target_edges: list[list[int]]


class ScreenReject(Exception):
    """Raised by `to_construction` for any semantically invalid
    `ConstructionOut` -- the millisecond screen tier (spec §4) gating entry
    to the expensive certified `verify_agreed` call. Every rejection path
    in `to_construction` raises this with a `.reason`; none let a raw
    exception escape."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def to_construction(out: ConstructionOut) -> Construction:
    if out.resources < 1:
        raise ScreenReject(f"resources must be >= 1, got {out.resources}")

    steps: list[FusionOp | LocalComplement] = []
    for i, step in enumerate(out.steps):
        if step.op == "fuse":
            if len(step.args) != 2:
                raise ScreenReject(
                    f"step {i}: fuse requires exactly 2 args, got {len(step.args)}"
                )
            a, b = step.args
            if a < 0 or b < 0:
                raise ScreenReject(
                    f"step {i}: fuse args must be non-negative, got ({a}, {b})"
                )
            if a == b:
                raise ScreenReject(
                    f"step {i}: fuse requires 2 distinct qubits, got ({a}, {b})"
                )
            steps.append(FusionOp(a=a, b=b))
        else:  # "lc" (the only other Literal value pydantic allows)
            if len(step.args) != 1:
                raise ScreenReject(
                    f"step {i}: lc requires exactly 1 arg, got {len(step.args)}"
                )
            (v,) = step.args
            if v < 0:
                raise ScreenReject(f"step {i}: lc arg must be non-negative, got {v}")
            steps.append(LocalComplement(v=v))

    for edge in out.target_edges:
        if len(edge) != 2:
            raise ScreenReject(f"target edge must be a pair, got {edge!r}")
        a, b = edge
        if a < 0 or b < 0 or a >= out.target_n or b >= out.target_n:
            raise ScreenReject(
                f"target edge {edge!r} out of range for target_n={out.target_n}"
            )
        if a == b:
            raise ScreenReject(f"target edge {edge!r} is a self-loop")

    fusion_count = sum(1 for s in steps if isinstance(s, FusionOp))
    expected_n = 3 * out.resources - 2 * fusion_count
    if out.target_n != expected_n:
        raise ScreenReject(
            f"size identity violated: target_n={out.target_n} != "
            f"3*resources - 2*fusion_count = {expected_n} "
            f"(resources={out.resources}, fusions={fusion_count})"
        )

    try:
        target = GraphState(n=out.target_n, edges=[tuple(e) for e in out.target_edges])
    except ValueError as exc:
        raise ScreenReject(f"invalid target graph: {exc}") from exc

    try:
        return Construction(resources=out.resources, steps=tuple(steps), target=target)
    except ValueError as exc:
        raise ScreenReject(f"invalid construction: {exc}") from exc

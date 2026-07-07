"""The Construction artifact (spec Appendix E): a resource recipe + fusion
schedule + target graph state.

A Construction consumes `resources` disjoint GHZ3 stars (the fixed
`build_workspace` layout) and applies `steps` fusions in order; each fusion
removes exactly 2 qubits, so the final qubit count is pinned exactly by
`resources` and `len(steps)`: `3*resources - 2*len(steps)`. This identity is
validated at construction time (fail loudly on a malformed recipe, rather
than silently on a mismatched target during `apply_construction`).

`apply_construction` is engine-agnostic: it drives any object implementing
the shared (state_from_graph, fuse, to_graphstate) triple (engines A/B's
public interface, spec D6/§8.3) and returns the resulting GraphState. Whether
that result actually matches `target`'s LC orbit is a verification question
for the callers in `verifiers/` (M5b Task 4), not something Construction
itself decides.

LocalClifford steps from spec Appendix E are OMITTED in v0: our identity is
the LC orbit (spec D5), under which a LocalClifford is a no-op by
definition -- it changes no lc_orbit_key. Construction therefore only models
the FusionOp steps, which are the only steps that can change the orbit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from empiricist.domain.p5.graphstate import GraphState


@dataclass(frozen=True)
class FusionOp:
    """One construction step: fuse (destructively Bell-measure) qubits a, b."""

    a: int
    b: int


@dataclass(frozen=True)
class Construction:
    """A resource recipe: `resources` GHZ3 stars (the workspace, see
    `build_workspace`), `steps` fusions applied in order, and the `target`
    graph state the recipe is claimed to produce (up to LC orbit).

    Validates the qubit-count identity `target.n == 3*resources -
    2*len(steps)` at construction time; raises ValueError if it doesn't hold.
    """

    resources: int
    steps: tuple[FusionOp, ...]
    target: GraphState

    def __post_init__(self) -> None:
        object.__setattr__(self, "steps", tuple(self.steps))
        expected_n = 3 * self.resources - 2 * len(self.steps)
        if self.target.n != expected_n:
            raise ValueError(
                f"target.n={self.target.n} does not match "
                f"3*resources - 2*len(steps) = {expected_n} "
                f"(resources={self.resources}, fusions={len(self.steps)})"
            )

    @property
    def fusion_count(self) -> int:
        return len(self.steps)


def build_workspace(resources: int) -> GraphState:
    """The fixed workspace: `resources` disjoint GHZ3 stars, star i centered
    at qubit 3i with leaves 3i+1, 3i+2."""
    edges = []
    for i in range(resources):
        c = 3 * i
        edges += [(c, c + 1), (c, c + 2)]
    return GraphState(n=3 * resources, edges=edges)


def apply_construction(c: Construction, engine: Any) -> GraphState:
    """Run `c`'s recipe on `engine`: build the workspace, apply each fusion
    step in order, extract and return the resulting graph state.

    `engine` is any object implementing the shared (state_from_graph, fuse,
    to_graphstate) triple -- engines A (stim) and B (GF2 bitmask) both
    qualify, independently.
    """
    state = engine.state_from_graph(build_workspace(c.resources))
    for step in c.steps:
        state = engine.fuse(state, step.a, step.b)
    return engine.to_graphstate(state)

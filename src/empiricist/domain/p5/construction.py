"""The Construction artifact (spec Appendix E): a resource recipe + fusion
schedule + target graph state.

A Construction consumes `resources` disjoint GHZ3 stars (the fixed
`build_workspace` layout) and applies `steps` in order; each FusionOp removes
exactly 2 qubits, so the final qubit count is pinned exactly by `resources`
and the number of FusionOp steps: `3*resources - 2*fusion_count`. This
identity is validated at construction time (fail loudly on a malformed
recipe, rather than silently on a mismatched target during
`apply_construction`). LocalComplement steps don't change the qubit count
(they're free single-qubit-neighborhood rewrites), so they don't enter the
size formula.

`apply_construction` is engine-agnostic: it drives any object implementing
the shared (state_from_graph, fuse, to_graphstate) triple (engines A/B's
public interface, spec D6/§8.3) and returns the resulting GraphState. Whether
that result actually matches `target`'s LC orbit is a verification question
for the callers in `verifiers/` (M5b Task 4), not something Construction
itself decides.

M5c A1 CORRECTION (the M5b premise below was FALSE): M5b's construction.py
claimed LocalClifford steps were no-ops because "our identity is the LC
orbit, under which a LocalClifford is a no-op by definition." That's true of
a LocalClifford applied to the FINAL state, but false mid-schedule: a free
tau_v on a qubit that is SUBSEQUENTLY FUSED changes which observable the
fusion measures relative to the pre-tau graph, and so can change the
reachable orbit (verified: from n=6 up, some true F=N-3 orbits are NOT
expressible as pure-FusionOp Constructions on the star workspace). Hence
`LocalComplement` is now a first-class step type alongside `FusionOp`, and
`apply_construction` replays it (see below).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.localcomp import local_complement


@dataclass(frozen=True)
class FusionOp:
    """One construction step: fuse (destructively Bell-measure) qubits a, b."""

    a: int
    b: int


@dataclass(frozen=True)
class LocalComplement:
    """One construction step: apply tau_v (Bouchet local complementation) to
    qubit v of the CURRENT workspace state -- a free operation (it changes no
    lc_orbit_key on its own) but NOT a no-op for the construction as a whole:
    a subsequent FusionOp involving v or one of v's (pre-tau) neighbors
    measures a different observable than it would have without the tau, and
    so can reach a different final orbit (the A1 finding -- see module
    docstring). Doesn't change the qubit count."""

    v: int


@dataclass(frozen=True)
class Construction:
    """A resource recipe: `resources` GHZ3 stars (the workspace, see
    `build_workspace`), `steps` (FusionOp | LocalComplement) applied in
    order, and the `target` graph state the recipe is claimed to produce (up
    to LC orbit).

    Validates the qubit-count identity `target.n == 3*resources -
    2*fusion_count` at construction time (counting only FusionOp steps --
    LocalComplement steps don't change the qubit count); raises ValueError if
    it doesn't hold.
    """

    resources: int
    steps: tuple[FusionOp | LocalComplement, ...]
    target: GraphState

    def __post_init__(self) -> None:
        object.__setattr__(self, "steps", tuple(self.steps))
        n_fusions = sum(1 for s in self.steps if isinstance(s, FusionOp))
        expected_n = 3 * self.resources - 2 * n_fusions
        if self.target.n != expected_n:
            raise ValueError(
                f"target.n={self.target.n} does not match "
                f"3*resources - 2*fusion_count = {expected_n} "
                f"(resources={self.resources}, fusions={n_fusions})"
            )

    @property
    def fusion_count(self) -> int:
        return sum(1 for s in self.steps if isinstance(s, FusionOp))


def build_workspace(resources: int) -> GraphState:
    """The fixed workspace: `resources` disjoint GHZ3 stars, star i centered
    at qubit 3i with leaves 3i+1, 3i+2."""
    edges = []
    for i in range(resources):
        c = 3 * i
        edges += [(c, c + 1), (c, c + 2)]
    return GraphState(n=3 * resources, edges=edges)


def apply_local_complement(engine: Any, state: Any, local_v: int) -> Any:
    """Apply tau_v to `state`'s qubit at LOCAL position `local_v` (i.e. the
    same indexing `engine.to_graphstate` uses: local position i is always
    `state.active[i]` for both engines -- see `apply_construction`'s
    docstring for why).

    Implementation: extract `state`'s current graph, apply the proven
    graph-level rewrite (`localcomp.local_complement`, spec Sec 8.2), and
    re-embed a FRESH engine state for the result via `state_from_graph`. This
    is engine-agnostic (uses only the shared state_from_graph/to_graphstate
    pair) and exact whenever the extraction has no representative ambiguity
    relative to the physical qubit basis -- true immediately after
    `state_from_graph` (see `test_engine_local_complement_matches_graph_rule`
    in tests/test_p5_construction.py) and empirically confirmed for the
    merge-then-tau-then-merge schedules exercised in
    `test_construction_with_lc_steps_verifies` (both independent engines
    agree on the resulting orbit).

    Returns a state whose OWN `active` is `tuple(range(k))` (the fresh
    `state_from_graph` convention) -- callers juggling a qubit-id map across
    multiple LocalComplement steps (like `apply_construction`) must
    re-derive it after calling this (old local id -> its position in the
    PRE-call `state.active`, i.e. `to_graphstate`'s own relabeling).
    """
    graph = engine.to_graphstate(state)
    return engine.state_from_graph(local_complement(graph, local_v))


def apply_construction(c: Construction, engine: Any) -> GraphState:
    """Run `c`'s recipe on `engine`: build the workspace, apply each step
    (FusionOp or LocalComplement) in order, extract and return the resulting
    graph state.

    `engine` is any object implementing the shared (state_from_graph, fuse,
    to_graphstate) triple -- engines A (stim) and B (GF2 bitmask) both
    qualify, independently.

    All step qubit ids (`FusionOp.a/.b`, `LocalComplement.v`) are ORIGINAL
    `build_workspace` qubit ids, valid for the WHOLE schedule (matching the
    existing goldens, which reference a workspace qubit by its original id
    even after earlier fusions removed other qubits -- `engine.fuse` never
    relabels). A LocalComplement step, however, is replayed via
    `apply_local_complement`, which DOES relabel (it rebuilds a fresh engine
    state via `state_from_graph`, whose `active` convention is
    `tuple(range(k))`) -- so `apply_construction` maintains `id_map`
    (original workspace id -> current engine-local id) and re-derives it
    after every LocalComplement step: `to_graphstate`'s output vertex i is
    always the PRE-call `state.active[i]` (both engines never permute
    columns/bit-positions out of `active` order), so the old-local-id ->
    new-local-id map is exactly `old_active.index`.
    """
    state = engine.state_from_graph(build_workspace(c.resources))
    id_map = {i: i for i in range(3 * c.resources)}
    for step in c.steps:
        if isinstance(step, LocalComplement):
            old_active = state.active
            local_v = old_active.index(id_map[step.v])
            state = apply_local_complement(engine, state, local_v)
            active_set = set(old_active)
            id_map = {
                orig: old_active.index(local)
                for orig, local in id_map.items()
                if local in active_set
            }
        else:
            state = engine.fuse(state, id_map[step.a], id_map[step.b])
    return engine.to_graphstate(state)

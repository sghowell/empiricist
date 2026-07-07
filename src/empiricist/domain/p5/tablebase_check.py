"""The SECOND, INDEPENDENT re-derivation of the Tier-0 all-merge reachability
partition (M5c Task 3, the F3 discipline): reproduces the same per-n
reachable-orbit partition as `tablebase.tier0_search`, but built to disagree
with it if either implementation has a bug, not to agree by construction --
every design axis the plan calls out is deliberately DIFFERENT here:

- **traversal**: a size-layered WORKLIST -- a plain growing `list` plus an
  integer index pointer -- not `tablebase.py`'s `collections.deque` 0-1 BFS.
  Same asymptotic behavior (each cert is enqueued once, processed once), but
  a structurally distinct mechanism: no queue class, no popleft, just "keep
  scanning until the pointer catches the list's tail" (a fixpoint-by-worklist,
  which is also what the plan's Task 3 text names as the alternative to a
  deque).
- **tau-closure**: driven directly against a per-size `dict[cert, GraphState]`
  by that same worklist (not a separate BFS-to-closure phase wrapping a
  queue-of-events).
- **the merge move itself**: instead of trusting `moves.merge_fresh_ghz3`'s
  closed-form disjoint-fusion graph rewrite, `merge_via_engine` below builds
  the ACTUAL disjoint union (blob) + (fresh GHZ3 star) as a `GraphState` and
  runs GF2Engine's REAL fusion measurement (`state_from_graph` / `fuse` /
  `to_graphstate`) on it. This is not merely a different code path for the
  same formula -- it exercises the certified stabilizer physics directly,
  where the closed form is a rewrite RULE that physics was used to justify
  (see `moves.py`'s docstring and `test_merge_rule_matches_both_engines_
  fuzz`). Re-deriving reachability by calling the engine on every single
  merge, instead of trusting the same rewrite rule a second time, is the
  entire point of this module -- genuine move-IMPLEMENTATION independence,
  not just a different traversal shell around the same rule.
- **orbit bookkeeping**: `_OrbitUnionFind` below is array-based (dense
  integer ids, union-by-size, full path compression over an int array),
  structurally unrelated to `tablebase.UnionFind`'s `dict[bytes, bytes]`
  parent-pointer-with-splitting scheme.

**INDEPENDENCE GUARD** (enforced by
`tests/test_p5_tablebase_check.py::test_tablebase_check_does_not_import_
tablebase_or_moves_merge` via `ast`-parsing `inspect.getsource` of this
module -- not a substring scan, so this docstring is free to discuss both by
name without tripping a false positive): this module must never import
`empiricist.domain.p5.tablebase` (the implementation it re-derives) or
`empiricist.domain.p5.moves` at all (in particular never
`moves.merge_fresh_ghz3`, the closed form it independently re-implements via
the engine instead).

What this module legitimately DOES share with `tablebase.py`: `GraphState`
(the value type), `iso_certificate` (McKay canonical labeling -- a true
isomorphism invariant, not an algorithmic choice under test here), and
`local_complement` (Bouchet local complementation, spec Sec 8.2 -- the graph
rewrite tau itself, not the SEARCH that walks it). Per the plan's trust
architecture, the shared canonicalizer is an acknowledged, narrowed SPOF
covered by other means (engine agreement, golden suites), not something this
module's independence claim is about -- its claim is specifically about the
SEARCH ALGORITHM and the MERGE MOVE.

What this module deliberately does NOT provide: witness `Construction`s, the
Adcock/geng cross-check, or unreachable-orbit materialization -- none of
those are its job. Its entire contract is: per-n reachable-orbit COUNTS and
a partition of iso-certificates into orbits, re-derived from scratch. The
agreement test computes each side's canonical orbit FINGERPRINT itself (the
min iso-certificate over each representative's full LC orbit, i.e.
`canonical.lc_orbit_key`) -- per the plan: "compute the tau-closure of one
representative per orbit... in the TEST, not in either implementation."
Neither this module nor `tablebase.py` is trusted to hand out orbit ids that
are comparable to the other's; the test is the referee.
"""

from __future__ import annotations

from dataclasses import dataclass

from empiricist.domain.p5.canonical import iso_certificate
from empiricist.domain.p5.fusion_gf2 import GF2Engine
from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.localcomp import local_complement

# The unique n=3 connected orbit (GHZ3) -- an unavoidable MATHEMATICAL
# constant shared with tablebase.py's own seed, not shared CODE or a search
# choice: any n=3 connected representative is a valid seed (there is exactly
# one connected orbit on 3 vertices), so this is not where independence lives.
_SEED = GraphState(n=3, edges=[(0, 1), (1, 2), (0, 2)])


class _OrbitUnionFind:
    """A from-scratch union-find over iso-certificate keys.

    Structurally DIFFERENT from `tablebase.UnionFind` (dict[bytes, bytes]
    parent pointers with path splitting): this one assigns each newly-seen
    certificate a dense integer id and does union-by-size with full path
    compression over a plain `list[int]`. Same abstract job (orbit-id
    assignment via unioning `cert(g) ~ cert(tau_v(g))`), independently coded.
    """

    def __init__(self) -> None:
        self._id_of: dict[bytes, int] = {}
        self._cert_of: list[bytes] = []
        self._parent: list[int] = []
        self._size: list[int] = []

    def add(self, cert: bytes) -> int:
        idx = self._id_of.get(cert)
        if idx is not None:
            return idx
        idx = len(self._parent)
        self._id_of[cert] = idx
        self._cert_of.append(cert)
        self._parent.append(idx)
        self._size.append(1)
        return idx

    def _find(self, i: int) -> int:
        root = i
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[i] != root:
            self._parent[i], i = root, self._parent[i]
        return root

    def union(self, cert_a: bytes, cert_b: bytes) -> None:
        ra, rb = self._find(self.add(cert_a)), self._find(self.add(cert_b))
        if ra == rb:
            return
        if self._size[ra] < self._size[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        self._size[ra] += self._size[rb]

    def root_cert(self, cert: bytes) -> bytes:
        """The representative certificate for `cert`'s component (a stable,
        arbitrary-but-deterministic member: whichever cert first created the
        root id)."""
        idx = self._id_of.get(cert)
        if idx is None:
            raise KeyError(cert.hex())
        return self._cert_of[self._find(idx)]


def _fresh_ghz3_union(gs: GraphState) -> tuple[GraphState, int, int]:
    """`gs` disjoint-union a fresh GHZ3 star, appended as the 3
    highest-numbered new vertices (center, leaf1, leaf2) -- no edges shared
    with `gs`. Returns the combined GraphState plus the fresh star's
    (center, leaf1) ids (leaf2 is `center + 1`... no: leaf2 is not needed by
    callers directly, only center/leaf1 -- see `merge_via_engine`)."""
    base = gs.n
    center, leaf1, leaf2 = base, base + 1, base + 2
    edges = set(gs.edges) | {(center, leaf1), (center, leaf2)}
    return GraphState(n=gs.n + 3, edges=edges), center, leaf1


def merge_via_engine(gs: GraphState, a: int, role: str) -> GraphState:
    """The independent merge move: fuse blob qubit `a` with a fresh GHZ3
    star's `role` qubit ("center" | "leaf") by actually building the
    disjoint union and running GF2Engine's REAL fusion measurement -- NOT
    `moves.merge_fresh_ghz3`'s trusted closed-form rewrite (see module
    docstring for why this is the genuine move-implementation independence
    the F3 discipline demands).
    """
    if role not in ("center", "leaf"):
        raise ValueError(f"role must be 'center' or 'leaf', got {role!r}")
    union_gs, center, leaf1 = _fresh_ghz3_union(gs)
    b = center if role == "center" else leaf1
    engine = GF2Engine()
    state = engine.state_from_graph(union_gs)
    state = engine.fuse(state, a, b)
    return engine.to_graphstate(state)


@dataclass(frozen=True)
class CheckOrbit:
    """One orbit this independent search reached at a given size."""

    orbit_id: str  # hex root cert, from THIS module's own union-find
    size: int
    representative: GraphState


@dataclass
class CheckResult:
    """The independent re-derivation's per-n reachable-orbit partition."""

    n_max: int
    reachable: dict[int, list[CheckOrbit]]
    visited_count: dict[int, int]  # distinct connected graphs visited, per size

    def reachable_count(self, n: int) -> int:
        return len(self.reachable.get(n, []))


def independent_reachability_search(n_max: int) -> CheckResult:
    """Re-derive, from scratch, the Tier-0 all-merge reachable-orbit
    partition for sizes 3..n_max. See the module docstring for exactly how
    this differs from `tablebase.tier0_search` at every design point the
    plan calls out (traversal, tau-closure mechanism, merge implementation,
    union-find).
    """
    if n_max < 3:
        raise ValueError(f"n_max must be >= 3, got {n_max}")

    seed_cert = iso_certificate(_SEED)
    layers: dict[int, dict[bytes, GraphState]] = {3: {seed_cert: _SEED}}
    uf = _OrbitUnionFind()
    uf.add(seed_cert)

    reachable: dict[int, list[CheckOrbit]] = {}
    visited_count: dict[int, int] = {}

    for n in range(3, n_max + 1):
        layer = layers.setdefault(n, {})

        # tau-closure via a size-layered WORKLIST: a plain growing list plus
        # an index pointer -- NOT collections.deque, NOT a queue-of-events
        # BFS. Seed the worklist with everything already in this layer
        # (including merge-discovered graphs carried over from the previous
        # iteration); keep scanning until the pointer catches the list's
        # tail, appending newly-discovered tau-images as they turn up.
        worklist: list[bytes] = list(layer.keys())
        pos = 0
        while pos < len(worklist):
            cert = worklist[pos]
            pos += 1
            g = layer[cert]
            for v in range(g.n):
                h = local_complement(g, v)
                hc = iso_certificate(h)
                if hc not in layer:
                    layer[hc] = h
                    worklist.append(hc)
                uf.union(cert, hc)

        # 1-cost merges to the next layer -- via the engine-backed merge
        # (merge_via_engine), never the closed form.
        if n < n_max:
            next_layer = layers.setdefault(n + 1, {})
            for g in layer.values():
                for a in range(g.n):
                    for role in ("center", "leaf"):
                        h = merge_via_engine(g, a, role)
                        hc = iso_certificate(h)
                        if hc not in next_layer:
                            next_layer[hc] = h

        roots: dict[bytes, bytes] = {}
        for cert in layer:
            roots.setdefault(uf.root_cert(cert), cert)
        reachable[n] = [
            CheckOrbit(orbit_id=root.hex(), size=n, representative=layer[rep])
            for root, rep in roots.items()
        ]
        visited_count[n] = len(layer)

    return CheckResult(n_max=n_max, reachable=reachable, visited_count=visited_count)

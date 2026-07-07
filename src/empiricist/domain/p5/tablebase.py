"""The Tier-0 tablebase (M5c Task 2): the all-merge reachability BFS to n=9
-- the harness's first novel-science dataset (no published GHZ3 table exists
past n=8).

**L3 (all-merge is cap-free and depth-fixed)** says an all-merge schedule's
component size grows monotonically 3 -> 4 -> ... -> N, one fusion per size
increment, so Tier-0 is pure *reachability*: which size-N connected orbits
does the (M1)-only search (merge_fresh_ghz3, both roles, every qubit) reach?
Reached orbits have F = N-3 (exact); unreached orbits have F >= N (L2).

**Search structure.** States are single connected graphs up to isomorphism
(dedup key = `iso_certificate`, NEVER `lc_orbit_key` -- see the A4 note
below). The BFS is organized by SIZE LAYER (L3: depth == size - 3 always, so
size-layered IS depth-layered): within a layer, close under the 0-cost tau
moves (`local_complements`) FIRST, then generate the 1-cost merge moves to
the next layer.

**A2 (CORRECTNESS-CRITICAL, not an optimization):** the intra-layer tau
closure is not a nicety -- skipping it UNDERCOUNTS reachable orbits. A pure-
fusion enumeration (merges only, no local complementation) finds only 7
reachable orbits at n=6 where the true count (with tau closure) is 8: some
merge targets are only reachable by first applying a free tau to a qubit
that is SUBSEQUENTLY fused (the same physical fact as the Construction-layer
A1 finding -- a tau on a soon-to-be-fused qubit changes what the fusion
measures). The tau closure must run to completion on every size layer BEFORE
any merge is generated from that layer, or reachable orbits get silently
dropped. Never prune or skip it.

**Orbit assignment.** Orbits fall out of the search for free: union-find
over iso-certificates, unioning `cert(g) ~ cert(tau_v(g))` for every visited
g and every v. Because each layer's tau closure is exhaustive (a full BFS
over the 0-edges starting from every merge-discovered graph at that size),
every member of a reachable orbit that exists as a connected graph on that
many vertices gets visited -- so the reachable union-find components are
TRUE, COMPLETE LC orbits, not partial ones.

**A4 (guard):** this module never calls `lc_orbit_key` (which walks a whole
LC orbit via BFS and is exactly what we're avoiding in the hot loop -- an
orbit can be enormous, and calling it per-candidate would make the search
re-derive, from scratch, on every single state, what union-find gives us for
free). `grep -n lc_orbit_key tablebase.py` should find nothing outside this
comment. Orbit ids are union-find roots, hex-encoded cert bytes.

**A3 (the real Adcock cross-check at n=8,9).** `enumerate_connected_orbits`
independently derives the FULL orbit partition of ALL connected graphs on n
vertices (not just the reachable ones) so that `unreachable := enumerated -
reachable` is a real set difference, never a tautological subtraction of
`some_known_total - reachable`. For n <= 7 this enumerates all connected
LABELED graphs via itertools edge-subsets (iso-deduped by certificate,
reusing the M5a golden-test approach); for n = 8, 9 that's combinatorially
infeasible (2^28, 2^36 labeled graphs), so it shells out to nauty's `geng -c
n` (streams graph6-encoded connected graphs up to isomorphism directly --
11117 lines at n=8, 261080 at n=9, both under a tenth of a second) THROUGH
`executor.runner.execute()` -- the harness's one audited subprocess path
(spec §6 names "enumerator" explicitly; this module never calls `subprocess`
directly, see `tests/test_no_bare_subprocess.py`) -- and parses each line
with `networkx.from_graph6_bytes`. Local complementation providably
preserves connectivity (Bouchet), so every tau-image of an enumerated graph
is itself connected and must already be present in the same enumerated
population -- asserted, not assumed.
"""

from __future__ import annotations

import asyncio
import itertools
import shutil
import time
from collections import deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

import networkx as nx

from empiricist.domain.p5.canonical import iso_certificate
from empiricist.domain.p5.construction import Construction, FusionOp, LocalComplement
from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.localcomp import local_complement
from empiricist.domain.p5.moves import intra_fuse, merge_fresh_ghz3
from empiricist.executor.runner import ExecSpec, execute

# geng's stdout at n=9 is ~2.1MB (261080 graph6 lines); give real headroom
# above that (execute()'s default capture_cap is 64KiB -- tuned for verifier
# argv/errors, not a bulk enumerator stream) rather than tune it exactly to
# n=9 and re-tune again the next time n_max grows.
_GENG_CAPTURE_CAP = 32 * 1024 * 1024

# The GHZ3 representative the search seeds from: the triangle K3 (one of the
# two labelings -- star and triangle -- of the unique n=3 connected orbit;
# either is a valid seed since they're tau-connected, but build_workspace(1)
# literally IS the star, so `witness()` prepends a single LocalComplement(0)
# to turn the workspace's star into this seed -- see `_ROOT_CORRECTION`).
SEED = GraphState(n=3, edges=[(0, 1), (1, 2), (0, 2)])

_GENG_CANDIDATES = ("geng", "nauty-geng")

Move = tuple  # ("tau", v: int) | ("merge", a: int, role: str)


class UnionFind:
    """Plain union-find over `bytes` keys (iso-certificates). No path
    compression tricks beyond the standard ones -- this is not the hot loop
    (the hot loop is the BFS's neighbor generation; union-find operations are
    O(visited states), not O(visited states * orbit size))."""

    def __init__(self) -> None:
        self._parent: dict[bytes, bytes] = {}

    def add(self, x: bytes) -> None:
        self._parent.setdefault(x, x)

    def find(self, x: bytes) -> bytes:
        self.add(x)
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[x] != root:
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a: bytes, b: bytes) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb

    def __contains__(self, x: bytes) -> bool:
        return x in self._parent


@dataclass(frozen=True)
class ReachableOrbit:
    """One orbit the Tier-0 search reached at a given size."""

    orbit_id: str  # hex union-find root -- A4: never a lc_orbit_key
    size: int
    depth: int  # fusion count == size - 3 (L3, asserted)
    representative_cert: bytes
    representative: GraphState


@dataclass(frozen=True)
class OrbitEnumeration:
    """The A3 real Adcock cross-check for one size n: the full orbit
    partition of ALL connected graphs on n vertices, independent of what the
    Tier-0 BFS reached."""

    n: int
    method: str  # "geng" | "itertools"
    graph_count: int  # distinct connected iso classes on n vertices
    orbit_count: int  # distinct LC orbits among them (must equal Adcock[n])
    _uf: UnionFind = field(repr=False)
    _reps: dict[bytes, GraphState] = field(repr=False)

    def orbit_root(self, cert: bytes) -> bytes:
        if cert not in self._reps:
            raise KeyError(
                f"cert {cert.hex()} is not among the enumerated n={self.n} connected graphs"
            )
        return self._uf.find(cert)

    def all_orbit_roots(self) -> set[bytes]:
        return {self._uf.find(c) for c in self._reps}

    def representative_of_root(self, root: bytes) -> GraphState:
        for c, g in self._reps.items():
            if self._uf.find(c) == root:
                return g
        raise KeyError(f"no enumerated graph maps to orbit root {root.hex()}")

    def representatives_by_root(self) -> dict[bytes, GraphState]:
        """One representative GraphState per orbit root, for EVERY orbit in
        this enumeration -- a single O(graph_count) pass (grouping by
        union-find root, keeping the smallest iso-certificate member per
        root) rather than `graph_count` iterations per queried root
        (`representative_of_root` called once per root, as Tier-0 used to
        do only for n<=7, costs O(orbit_count * graph_count); at n=9's
        261,080 enumerated graphs and up to 336 unreachable orbits that's
        tens of millions of comparisons for no reason). The "smallest
        iso-certificate" tiebreak makes the choice deterministic and
        independent of geng's/itertools's arbitrary enumeration order."""
        best: dict[bytes, bytes] = {}
        for c in self._reps:
            root = self._uf.find(c)
            if root not in best or c < best[root]:
                best[root] = c
        return {root: self._reps[c] for root, c in best.items()}


@dataclass
class Tier0Result:
    """The Tier-0 all-merge reachability table, sizes 3..n_max."""

    n_max: int
    reachable: dict[int, list[ReachableOrbit]]
    unreachable_count: dict[int, int]
    unreachable_representatives: dict[int, list[GraphState]]  # materialized for every n
    total_orbit_count: dict[int, int]  # from enumerate_connected_orbits -- the Adcock recheck
    method: dict[int, str]  # "geng" | "itertools" per n
    visited_state_count: dict[int, int]  # total distinct connected graphs visited, per size
    elapsed_seconds: dict[int, float]  # wall time for the reachable BFS itself, per size
    # Internal, needed by witness(); not part of the public reporting surface.
    _visited: dict[bytes, GraphState] = field(repr=False)
    _parent: dict[bytes, tuple[bytes, Move] | None] = field(repr=False)
    _depth: dict[bytes, int] = field(repr=False)

    def reachable_count(self, n: int) -> int:
        return len(self.reachable.get(n, []))

    def _witness_prefix(
        self, cert: bytes
    ) -> tuple[list[FusionOp | LocalComplement], dict[int, int], int]:
        """Walk the BFS parent chain from the seed to `cert`, returning the
        Construction steps built so far, the id_map (BFS-local id in
        `cert`'s OWN graph -> original build_workspace id), and the
        resource_counter -- i.e. everything `witness()` needs to finish
        building a Construction, AND everything `tier1_search` needs to
        append ONE more step (an intra fusion at `cert`'s own BFS-local
        qubit ids) after reaching a Tier-0 all-merge state. Extracted from
        `witness()` so both can share this bookkeeping exactly (a second,
        drifted copy of this logic would be a correctness risk, not an
        independence feature -- Tier-1 lives in this same module, so there's
        no F3 boundary to preserve here, unlike tablebase_check.py).

        THE FIDDLY PART: the BFS relabels qubits at every merge
        (`merge_fresh_ghz3`'s compacting relabel), but `apply_construction`'s
        FusionOp steps reference ORIGINAL, whole-schedule workspace ids
        (engine.fuse never relabels -- see construction.py). So this method
        maintains its own `id_map`: BFS-local id (in the CURRENT node's
        GraphState) -> original build_workspace id, updated at every step:

        - A "tau" move doesn't relabel or resize anything (Bouchet local
          complementation only toggles edges within one vertex's
          neighborhood) -- id_map is unchanged; just translate `v` through it
          into a LocalComplement step.
        - A "merge" move consumes BFS-local qubit `a`; every other BFS-local
          id `q < a` keeps its id, every `q > a` shifts down by one (mirrors
          merge_fresh_ghz3's own `compact` relabeling exactly); the two
          surviving fresh qubits get the new BFS-local ids `old_size - 1` and
          `old_size`, mapped to the new resource's ORIGINAL workspace ids
          (center = 3*i, leaves = 3*i+1, 3*i+2 for the i-th merge, matching
          `build_workspace`) according to which role fused: role="center"
          fuses the original center (both leaves survive, symmetric, mapped
          arbitrarily-but-consistently to leaf1/leaf2); role="leaf" fuses
          leaf1 (center + leaf2 survive).

        The seed is the TRIANGLE, but `build_workspace(1)` is the STAR (same
        vertex ids 0,1,2) -- one is not the other syntactically, but they are
        LC-equivalent (`tau_0(star) == triangle`), so every witness is
        prefixed with a single `LocalComplement(v=0)` root-correction step.

        Acceptance criterion (per the plan): this method's ONLY warrant is
        that its output PASSES `verify_agreed` -- both independent engines
        replaying these exact steps must land in `cert`'s LC orbit. Any
        bookkeeping bug here is caught by that check, not by inspection.
        """
        if cert not in self._parent:
            raise KeyError(f"cert {cert.hex()} was not visited by this Tier-0 search")

        chain: list[bytes] = []
        cur: bytes | None = cert
        while cur is not None:
            chain.append(cur)
            parent_info = self._parent[cur]
            cur = parent_info[0] if parent_info is not None else None
        chain.reverse()  # chain[0] is the seed cert

        steps: list[FusionOp | LocalComplement] = [LocalComplement(v=0)]  # root correction
        id_map: dict[int, int] = {0: 0, 1: 1, 2: 2}
        resource_counter = 1  # resource 0 == the seed; next merge introduces resource 1, 2, ...

        for i in range(1, len(chain)):
            prev_cert, cur_cert = chain[i - 1], chain[i]
            parent_info = self._parent[cur_cert]
            assert parent_info is not None and parent_info[0] == prev_cert
            move = parent_info[1]
            prev_graph = self._visited[prev_cert]

            if move[0] == "tau":
                _, v_bfs = move
                steps.append(LocalComplement(v=id_map[v_bfs]))
                # id_map unchanged: tau neither relabels nor resizes.
            else:
                _, a_bfs, role = move
                old_size = prev_graph.n
                compact = {q: (q if q < a_bfs else q - 1) for q in range(old_size) if q != a_bfs}
                new_id_map = {
                    compact[q_old]: orig for q_old, orig in id_map.items() if q_old != a_bfs
                }
                survivor1_bfs, survivor2_bfs = old_size - 1, old_size
                center_id = 3 * resource_counter
                leaf1_id = 3 * resource_counter + 1
                leaf2_id = 3 * resource_counter + 2
                if role == "center":
                    new_id_map[survivor1_bfs] = leaf1_id
                    new_id_map[survivor2_bfs] = leaf2_id
                    fused_b = center_id
                else:
                    new_id_map[survivor1_bfs] = center_id
                    new_id_map[survivor2_bfs] = leaf2_id
                    fused_b = leaf1_id
                steps.append(FusionOp(a=id_map[a_bfs], b=fused_b))
                id_map = new_id_map
                resource_counter += 1

        return steps, id_map, resource_counter

    def witness(self, cert: bytes) -> Construction:
        """The full Construction witnessing `cert`'s reachability: `_witness_
        prefix`'s steps as-is, targeting `cert`'s own graph.

        Acceptance criterion (per the plan): this method's ONLY warrant is
        that its output PASSES `verify_agreed` -- both independent engines
        replaying these exact steps must land in `cert`'s LC orbit. Any
        bookkeeping bug in `_witness_prefix` is caught by that check, not by
        inspection.
        """
        steps, _id_map, resource_counter = self._witness_prefix(cert)
        target = self._visited[cert]
        return Construction(resources=resource_counter, steps=tuple(steps), target=target)


def tier0_search(
    n_max: int,
    *,
    on_progress: Callable[[str], None] | None = None,
) -> Tier0Result:
    """The Tier-0 all-merge reachability BFS, seeded from K3, up to size
    `n_max`, plus the A3 real-Adcock cross-check for every size 3..n_max.

    See the module docstring for the algorithm and the A2/A3/A4 amendments.
    """
    if n_max < 3:
        raise ValueError(f"n_max must be >= 3, got {n_max}")

    def log(msg: str) -> None:
        if on_progress is not None:
            on_progress(msg)

    seed_cert = iso_certificate(SEED)
    visited: dict[bytes, GraphState] = {seed_cert: SEED}
    parent: dict[bytes, tuple[bytes, Move] | None] = {seed_cert: None}
    depth: dict[bytes, int] = {seed_cert: 0}
    uf = UnionFind()
    uf.add(seed_cert)
    by_size: dict[int, list[bytes]] = {3: [seed_cert]}

    reachable: dict[int, list[ReachableOrbit]] = {}
    unreachable_count: dict[int, int] = {}
    unreachable_representatives: dict[int, list[GraphState]] = {}
    total_orbit_count: dict[int, int] = {}
    method: dict[int, str] = {}
    visited_state_count: dict[int, int] = {}
    elapsed_seconds: dict[int, float] = {}

    for n in range(3, n_max + 1):
        t0 = time.monotonic()
        frontier = list(by_size.get(n, []))

        # A2: close this size layer under tau (the 0-cost moves) BEFORE
        # generating ANY merge from it -- CORRECTNESS-CRITICAL, see module
        # docstring. Standard BFS-to-closure: repeat until no new tau-images
        # appear for this size.
        worklist: deque[bytes] = deque(frontier)
        while worklist:
            cert = worklist.popleft()
            g = visited[cert]
            for v in range(g.n):
                h = local_complement(g, v)
                hc = iso_certificate(h)
                if hc not in visited:
                    visited[hc] = h
                    parent[hc] = (cert, ("tau", v))
                    depth[hc] = depth[cert]
                    uf.add(hc)
                    by_size.setdefault(n, []).append(hc)
                    worklist.append(hc)
                uf.union(cert, hc)

        layer = by_size.get(n, [])
        for c in layer:
            assert depth[c] == n - 3, f"L3 violated: size={n} depth={depth[c]} cert={c.hex()}"

        # Now generate the 1-cost merges to size n+1 (only if we're not done).
        if n < n_max:
            for cert in layer:
                g = visited[cert]
                for a in range(g.n):
                    for role in ("center", "leaf"):
                        h = merge_fresh_ghz3(g, a, role)
                        hc = iso_certificate(h)
                        if hc not in visited:
                            visited[hc] = h
                            parent[hc] = (cert, ("merge", a, role))
                            depth[hc] = depth[cert] + 1
                            uf.add(hc)
                            by_size.setdefault(n + 1, []).append(hc)

        # Summarize this size's reachable orbits (union-find components
        # restricted to this layer's visited certs).
        roots: dict[bytes, bytes] = {c: uf.find(c) for c in layer}
        orbit_reps: dict[bytes, bytes] = {}
        for c, root in roots.items():
            orbit_reps.setdefault(root, c)
        reachable[n] = [
            ReachableOrbit(
                orbit_id=root.hex(),
                size=n,
                depth=n - 3,
                representative_cert=rep,
                representative=visited[rep],
            )
            for root, rep in orbit_reps.items()
        ]
        visited_state_count[n] = len(layer)
        elapsed_seconds[n] = time.monotonic() - t0
        log(
            f"n={n}: {len(layer)} connected graphs visited, "
            f"{len(reachable[n])} reachable orbits ({elapsed_seconds[n]:.2f}s)"
        )

        # A3: the real Adcock cross-check -- enumerate ALL connected graphs
        # on n vertices independently and mark which of THEIR orbits contain
        # a reachable representative; unreachable := enumerated - reachable
        # (never total - reachable by subtraction alone).
        t_enum0 = time.monotonic()
        enum = enumerate_connected_orbits(n)
        method[n] = enum.method
        total_orbit_count[n] = enum.orbit_count
        reachable_roots: set[bytes] = set()
        for c in layer:
            reachable_roots.add(enum.orbit_root(c))
        assert len(reachable_roots) == len(reachable[n]), (
            f"n={n}: Tier-0's own union-find found {len(reachable[n])} reachable orbits "
            f"but the independent full-population enumeration maps them to "
            f"{len(reachable_roots)} distinct orbits -- the two orbit derivations disagree"
        )
        unreachable_count[n] = enum.orbit_count - len(reachable_roots)
        # M5c Task 4: materialize a representative for EVERY unreachable
        # orbit at EVERY n (not just n<=7) -- build_dataset needs a real
        # representative graph for every "open" row across the full n=3..9
        # range. `representatives_by_root` is a single O(graph_count) pass
        # over the enumeration already computed above (for the A3 cross-
        # check), so this costs nothing extra at n=8,9 scale.
        all_roots = enum.all_orbit_roots()
        reps_by_root = enum.representatives_by_root()
        unreachable_representatives[n] = [
            reps_by_root[root] for root in sorted(all_roots - reachable_roots)
        ]
        log(
            f"n={n}: Adcock cross-check ({enum.method}) -- {enum.orbit_count} total orbits, "
            f"{len(reachable_roots)} reachable, {unreachable_count[n]} unreachable "
            f"({time.monotonic() - t_enum0:.2f}s)"
        )

    return Tier0Result(
        n_max=n_max,
        reachable=reachable,
        unreachable_count=unreachable_count,
        unreachable_representatives=unreachable_representatives,
        total_orbit_count=total_orbit_count,
        method=method,
        visited_state_count=visited_state_count,
        elapsed_seconds=elapsed_seconds,
        _visited=visited,
        _parent=parent,
        _depth=depth,
    )


def _find_geng() -> str | None:
    for name in _GENG_CANDIDATES:
        path = shutil.which(name)
        if path:
            return path
    return None


def _run_geng(n: int, geng_path: str) -> bytes:
    """Spawn `geng -c n` through the harness's one audited subprocess path
    (`executor.runner.execute()` -- spec §6 names "enumerator" explicitly
    among the subprocesses that must go through `runner.py`; this module
    never spawns a subprocess directly, see
    tests/test_no_bare_subprocess.py). geng is a trusted, deterministic,
    read-only-of-its-arguments local tool (no network, no filesystem
    writes -- same trust class as the `claude` CLI transport), so it runs
    under the default sandbox (SANDBOX_EXEC) with a scrubbed env; the only
    override needed is `capture_cap` (geng's stdout can run into the
    megabytes at n=9, well past the 64KiB default tuned for verifier
    output)."""
    spec = ExecSpec(
        argv=[geng_path, "-c", str(n)],
        move="ENUMERATE",
        capture_cap=_GENG_CAPTURE_CAP,
    )
    result = asyncio.run(execute(spec))
    if result.exit_code != 0:
        raise RuntimeError(
            f"geng -c {n} exited {result.exit_code}: {result.stderr[:2000]}"
        )
    if result.output_truncated:
        raise RuntimeError(
            f"geng -c {n} output was truncated at capture_cap={_GENG_CAPTURE_CAP} bytes "
            "-- raise _GENG_CAPTURE_CAP for this n"
        )
    return result.stdout.encode("utf-8")


def _geng_connected_graphs(n: int, geng_path: str) -> Iterator[GraphState]:
    raw = _run_geng(n, geng_path)
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        g = nx.from_graph6_bytes(line)
        yield GraphState(n=g.number_of_nodes(), edges=list(g.edges()))


def _itertools_connected_graphs(n: int) -> Iterator[GraphState]:
    """All connected simple graphs on n LABELED vertices (small n only --
    2^C(n,2) labeled graphs, infeasible past n=7). Iso-dedup happens in the
    caller via iso_certificate; this just needs to hit every iso class at
    least once, which enumerating every labeling trivially does."""
    verts = list(range(n))
    all_edges = list(itertools.combinations(verts, 2))
    for r in range(max(n - 1, 0), len(all_edges) + 1):
        for es in itertools.combinations(all_edges, r):
            g = nx.Graph()
            g.add_nodes_from(verts)
            g.add_edges_from(es)
            if n <= 1 or nx.is_connected(g):
                yield GraphState(n=n, edges=list(es))


def enumerate_connected_orbits(n: int) -> OrbitEnumeration:
    """The A3 real Adcock cross-check for size n: enumerate ALL connected
    graphs on n vertices up to isomorphism, then union-find them into LC
    orbits by unioning `cert(g) ~ cert(tau_v(g))` for every g and every v --
    the same relation the Tier-0 search's own union-find uses, but over the
    FULL population instead of just the reachable subset.

    Uses nauty's `geng -c n` (streamed graph6, parsed via
    `networkx.from_graph6_bytes`) when available -- exact and fast even at
    n=8 (11117 graphs) and n=9 (261080 graphs). Falls back to itertools
    edge-subset enumeration for n <= 7 if geng isn't on PATH (slow past
    n=6-7, but still exact); raises for n >= 8 without geng, since 2^28+
    labeled graphs is not a real fallback (install nauty: `brew install
    nauty`, or your platform's package for `geng`/`nauty-geng`).
    """
    geng_path = _find_geng()
    if geng_path is not None:
        graphs = _geng_connected_graphs(n, geng_path)
        method = "geng"
    elif n <= 7:
        graphs = _itertools_connected_graphs(n)
        method = "itertools"
    else:
        raise RuntimeError(
            f"enumerate_connected_orbits(n={n}): geng/nauty-geng not found on PATH, and "
            f"itertools enumeration of all labeled graphs on {n} vertices "
            f"(2^{n * (n - 1) // 2}) is infeasible. Install nauty to get `geng` "
            "(`brew install nauty` on macOS) for an exact n=8/9 Adcock cross-check."
        )

    uf = UnionFind()
    reps: dict[bytes, GraphState] = {}
    for g in graphs:
        c = iso_certificate(g)
        if c not in reps:
            reps[c] = g
            uf.add(c)

    for c, g in reps.items():
        for v in range(g.n):
            h = local_complement(g, v)
            hc = iso_certificate(h)
            if hc not in reps:
                raise AssertionError(
                    f"enumerate_connected_orbits(n={n}): tau_{v} of an enumerated connected "
                    f"graph produced a certificate not in the enumerated population -- local "
                    "complementation should preserve connectivity (Bouchet), so this means "
                    "either the enumeration missed a connected graph or LC broke connectivity"
                )
            uf.union(c, hc)

    orbit_count = len({uf.find(c) for c in reps})
    return OrbitEnumeration(
        n=n,
        method=method,
        graph_count=len(reps),
        orbit_count=orbit_count,
        _uf=uf,
        _reps=reps,
    )


@dataclass(frozen=True)
class Tier1Orbit:
    """One orbit Tier-1 resolves EXACTLY at F = N: reached via an all-merge
    (f_i=0) schedule to size N+2 followed by ONE intra fusion (f_i=1) landing
    back at size N -- and confirmed NOT already reachable at Tier-0 (F = N-3)."""

    orbit_id: str  # hex root, in the enumerate_connected_orbits(n) root space
    size: int
    f_value: int  # == size, exact (L2 + L4)
    representative_cert: bytes
    representative: GraphState
    # Everything witness() needs to rebuild the schedule: the size-(n+2)
    # all-merge state this orbit was reached FROM, and the intra-fusion pair
    # (in that source graph's own BFS-local coordinates).
    _source_cert: bytes = field(repr=False)
    _a: int = field(repr=False)
    _b: int = field(repr=False)


@dataclass
class Tier1Result:
    """The Tier-1 (f_i <= 1) resolution: per-n orbits with F = N exactly that
    Tier-0's all-merge-only search (f_i = 0) did not reach."""

    n_max: int
    transient_max: int  # n_max + 2 -- L4's bounded transient for f_i <= 1
    tier0: Tier0Result  # the underlying all-merge search, extended to transient_max
    newly_resolved: dict[int, list[Tier1Orbit]]

    def resolved_count(self, n: int) -> int:
        return len(self.newly_resolved.get(n, []))

    def witness(self, orbit: Tier1Orbit) -> Construction:
        """merges -> one intra: replay Tier-0's own path to `orbit`'s size-
        (n+2) source state (via the SAME `_witness_prefix` bookkeeping
        `Tier0Result.witness` uses -- see that method's docstring for the
        id_map mechanics), then append ONE more FusionOp for the intra pair
        that reached this orbit. Resources are unchanged by an intra fusion
        (it consumes no new GHZ3 star); fusion_count increases by 1, giving
        exactly F = (m - 3) + 1 = (n + 2 - 3) + 1 = n, per L2/L4.
        """
        steps, id_map, resource_counter = self.tier0._witness_prefix(orbit._source_cert)
        steps = [*steps, FusionOp(a=id_map[orbit._a], b=id_map[orbit._b])]
        return Construction(
            resources=resource_counter, steps=tuple(steps), target=orbit.representative
        )


def tier1_search(
    n_max: int = 7,
    *,
    on_progress: Callable[[str], None] | None = None,
) -> Tier1Result:
    """L4 (bounded transient for f_i <= 1): grow purely by merges (f_i = 0)
    to size <= n_max + 2, then apply EXACTLY ONE intra fusion (f_i = 1) from
    EVERY visited graph of size m = n + 2, over every qubit pair, landing
    back at size n. Depth bookkeeping: (m - 3) merges + 1 intra = (n + 2 - 3)
    + 1 = n fusions total -- so any size-n orbit reached this way that
    Tier-0 (f_i = 0, F = n - 3) did NOT reach has F = n EXACTLY (L2 + L4:
    the ladder is {n-3, n, n+3, ...}, and this witnesses n directly).

    A2's analogue for Tier-1: intra-fusing from every visited size-m graph
    (not just one representative per orbit) is CORRECTNESS-critical, not
    exhaustive-for-safety's-sake -- a tau applied to a qubit that is
    subsequently intra-fused changes the fusion's observable (the same A1/A2
    fact from Task 1/Tier-0), so skipping members of the size-m tau-closure
    would silently undercount which size-n orbits Tier-1 can reach.

    Orbit identity for "already reached at Tier-0?" and "which orbit did
    this land in?" is arbitrated by `enumerate_connected_orbits(n)` (the SAME
    independent, geng/itertools-backed full-population union-find Tier-0's
    own A3 cross-check uses) -- never by comparing Tier-0's BFS union-find
    roots to a separately-computed Tier-1 union-find (two different
    union-find structures are not comparable by root value alone).

    `n_max` defaults to 7 (transient <= 9, matching Tier-0's own validated
    range); n <= 6 is fast, n = 7's transient (m = 9) is the same scale as
    Tier-0's own @slow n=9 case.
    """
    if n_max < 3:
        raise ValueError(f"n_max must be >= 3, got {n_max}")
    transient_max = n_max + 2

    def log(msg: str) -> None:
        if on_progress is not None:
            on_progress(msg)

    t0 = tier0_search(transient_max, on_progress=on_progress)

    by_size: dict[int, list[tuple[bytes, GraphState]]] = {}
    for cert, g in t0._visited.items():
        by_size.setdefault(g.n, []).append((cert, g))

    newly_resolved: dict[int, list[Tier1Orbit]] = {}
    for n in range(3, n_max + 1):
        m = n + 2
        t_start = time.monotonic()
        enum_n = enumerate_connected_orbits(n)
        t0_roots = {enum_n.orbit_root(o.representative_cert) for o in t0.reachable[n]}

        found: dict[bytes, Tier1Orbit] = {}
        for g_cert, g in by_size.get(m, []):
            for a in range(g.n):
                for b in range(a + 1, g.n):
                    h = intra_fuse(g, a, b)
                    assert h.n == n, (
                        f"intra_fuse must remove exactly 2 qubits: m={m} a={a} b={b} "
                        f"produced n={h.n}, expected {n}"
                    )
                    if not nx.is_connected(h.to_networkx()):
                        continue  # a disconnected/product result witnesses no connected orbit
                    hc = iso_certificate(h)
                    root = enum_n.orbit_root(hc)
                    if root in t0_roots or root in found:
                        continue
                    found[root] = Tier1Orbit(
                        orbit_id=root.hex(),
                        size=n,
                        f_value=n,
                        representative_cert=hc,
                        representative=h,
                        _source_cert=g_cert,
                        _a=a,
                        _b=b,
                    )
        newly_resolved[n] = list(found.values())
        still_open = enum_n.orbit_count - len(t0_roots) - len(found)
        log(
            f"n={n}: Tier-1 (f_i=1, transient m={m}) resolves {len(found)} new orbit(s) "
            f"at F={n} ({still_open} still open) ({time.monotonic() - t_start:.2f}s)"
        )

    return Tier1Result(
        n_max=n_max, transient_max=transient_max, tier0=t0, newly_resolved=newly_resolved
    )

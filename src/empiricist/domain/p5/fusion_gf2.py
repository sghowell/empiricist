"""Engine B: fusion on a pure-Python GF(2) bitmask stabilizer tableau.

Independent of engine A by construction (F3): no tableau-simulator library, no
array library -- every generator is a plain `(x_bits, z_bits)` pair of Python
ints, bit `j` of each field meaning "this generator carries an X (resp. Z) on
the qubit currently living at position j". All linear algebra (rank, row
reduction, the local-Hadamard search) is hand-rolled bitmask Gaussian
elimination.

Physics (signs ignored throughout -- a documented simplification: sign flips
are Pauli corrections, i.e. local Cliffords, invisible to the LC orbit):

- Graph state |G>: generator for vertex v is X_v * prod_{u in N(v)} Z_u, i.e.
  `x_bits = 1 << v`, `z_bits = OR(1 << u for u in N(v))`.
- Two Paulis (x1, z1), (x2, z2) anticommute iff
  `popcount(x1 & z2) + popcount(x2 & z1)` is odd (the symplectic form).
- Measuring an observable P against a stabilizer generating set: collect the
  generators that anticommute with P. None anticommuting -> the outcome is
  already determined (P is, signs ignored, already IN the group) and the
  state is UNCHANGED -- a legitimate no-op branch, reachable when an
  intra-component fusion's observable is already stabilized by the state.
  Otherwise pick one anticommuting generator as the pivot, fold it (XOR)
  into every *other* anticommuting generator, then overwrite the pivot slot
  with P itself.
- Fusion of active qubits (a, b) measures the ratified commuting pair
  `{X_a Z_b, Z_a X_b}` (spec D6: NOT `{X_a X_b, Z_a Z_b}` -- the two
  conventions differ by a free Hadamard on one fusion qubit and thus give the
  same LC orbit, but `{XZ, ZX}` is the one whose bit bookkeeping matches the
  graph rule used by the goldens here). The two operators commute, so the
  second measurement never disturbs the first's group membership. After both
  updates the sign-free group contains B1 = X_a Z_b AND B2 = Z_a X_b --
  whether each outcome was random (B_i literally replaced a generator) or
  deterministic (B_i was already a group element) -- so (a, b) holds a Bell
  state disentangled from the rest.
- Removal of (a, b) -- the general elimination, correct in ALL cases (it
  does NOT assume the measured observables sit in the generator list): each
  generator projects to a 4-bit BLOCK (x_a, z_a, x_b, z_b). Every group
  element commutes with B1 and B2, and the symplectic form then pins every
  block to satisfy `x_a == z_b` and `x_b == z_a`: the block space has rank
  exactly 2 (it contains B1's and B2's own blocks). GF(2)-eliminate on the
  block bits: keep (up to) 2 pivot generators with independent nonzero
  blocks, XOR them into every other generator, leaving all others
  block-free, i.e. with ZERO x and z bits at both a and b. Block rank > 2 is
  impossible if the pair is disentangled -- assert. The 2 pivots may still
  carry support outside {a, b}; multiplying by B1/B2 (pure-block group
  elements) shows each pivot's outside part lies in the group's zero-block
  subgroup, which the block-free generators span exactly -- so reducing each
  pivot's outside part against the block-free rows must reach exactly zero
  (assert; failure means the disentanglement premise, and hence the
  measurement update, is wrong). Drop the two pivots (they generate the
  isolated Bell pair) and compact bit positions a, b out of every remaining
  generator, shifting higher bit positions down so the k = n - 2 survivors
  live on qubits 0..k-1.
- Postselection: because signs are ignored there is no impossible branch to
  fall back from -- the deterministic update above already *is* the (+1, +1)
  branch up to a Pauli frame, and that frame is invisible to the LC orbit.
- Graph extraction (Van den Nest): with k generators over k qubits, while the
  GF(2) rank of the X-side is below k, there is some qubit j at which
  swapping the x/z bits of every generator (a free local Hadamard) raises the
  rank; apply it. Once the X-side has full rank, Gauss-Jordan row-reduce
  (XOR-combining whole generator rows) until row i reads `x_bits == 1 << i`
  for every i. Row i's z_bits is then the adjacency row of vertex i (the
  diagonal bit, if set, is a free S gate -- drop it). Because every pair of
  rows must commute, `bit j of row i` and `bit i of row j` are provably equal
  -- the resulting adjacency is symmetric by construction.
"""

from __future__ import annotations

from dataclasses import dataclass

from empiricist.domain.p5.graphstate import GraphState


@dataclass(frozen=True)
class GF2State:
    """A stabilizer tableau: `k` independent generators over `k` active
    qubits, plus the original vertex id each current bit position holds.

    `generators[i]` and `active[i]` are NOT tied to each other by position --
    `active` only tracks "bit position j holds original qubit active[j]";
    the generator list is an unordered spanning set for the stabilizer group
    (row order carries no meaning; `to_graphstate` is what recovers the
    per-qubit correspondence via row reduction).
    """

    generators: tuple[tuple[int, int], ...]
    active: tuple[int, ...]


def _parity(bits: int) -> int:
    return bin(bits).count("1") & 1


def _anticommute(x1: int, z1: int, x2: int, z2: int) -> bool:
    return (_parity(x1 & z2) + _parity(x2 & z1)) % 2 == 1


def _measure(generators: list[tuple[int, int]], xp: int, zp: int) -> list[tuple[int, int]]:
    """Update `generators` for measuring Pauli (xp, zp).

    No anticommuting generator -> the outcome is already determined, i.e.
    (xp, zp) is (signs ignored) already in the group: return the list
    UNCHANGED (a valid no-op branch -- the caller's removal step never
    assumes the observable landed in the generator list). Otherwise fold the
    first anticommuting generator into every other anticommuting one and
    overwrite it with (xp, zp)."""
    anticommuting = [i for i, (xg, zg) in enumerate(generators) if _anticommute(xg, zg, xp, zp)]
    if not anticommuting:
        return list(generators)
    pivot_idx = anticommuting[0]
    xg0, zg0 = generators[pivot_idx]
    new_generators = list(generators)
    for i in anticommuting[1:]:
        xi, zi = new_generators[i]
        new_generators[i] = (xi ^ xg0, zi ^ zg0)
    new_generators[pivot_idx] = (xp, zp)
    return new_generators


def _reduce_vector(basis: dict[int, int], v: int) -> int:
    """Reduce bit-vector `v` against `basis` (a reduced GF(2) basis keyed by
    highest set bit); return the residual (0 iff v is in the span)."""
    while v:
        lead = v.bit_length() - 1
        if lead not in basis:
            return v
        v ^= basis[lead]
    return 0


def _basis_insert(basis: dict[int, int], v: int) -> None:
    """Insert `v` into the reduced basis if independent (no-op otherwise)."""
    residual = _reduce_vector(basis, v)
    if residual:
        basis[residual.bit_length() - 1] = residual


def _compact_bits(bits: int, lo: int, hi: int) -> int:
    """Delete bit positions lo < hi from `bits`, shifting higher bits down."""
    below = bits & ((1 << lo) - 1)
    between = (bits >> (lo + 1)) & ((1 << (hi - lo - 1)) - 1)
    above = bits >> (hi + 1)
    return below | (between << lo) | (above << (hi - 1))


def _gf2_rank(vectors: list[int]) -> int:
    """Rank over GF(2) of a set of bitmask row vectors, via a bitmask
    reduced-basis accumulation (each newly-independent vector is kept keyed
    by its highest set bit)."""
    pivots: dict[int, int] = {}
    rank = 0
    for v in vectors:
        cur = v
        while cur:
            hi_bit = cur.bit_length() - 1
            if hi_bit not in pivots:
                pivots[hi_bit] = cur
                rank += 1
                break
            cur ^= pivots[hi_bit]
    return rank


def _ensure_full_x_rank(generators: list[tuple[int, int]], k: int) -> list[tuple[int, int]]:
    """Apply local Hadamards (x/z bit swaps at one qubit, across every
    generator) until the X-side of the tableau has full rank k."""
    gens = list(generators)
    rank = _gf2_rank([x for x, _ in gens])
    attempts = 0
    while rank < k:
        attempts += 1
        if attempts > 4 * k + 16:
            raise AssertionError("extraction: X-rank stuck below k -- measurement bug upstream")
        progressed = False
        for j in range(k):
            mask = 1 << j
            trial_xs = []
            for x, z in gens:
                zb = 1 if (z & mask) else 0
                trial_xs.append((x & ~mask) | (mask if zb else 0))
            trial_rank = _gf2_rank(trial_xs)
            if trial_rank > rank:
                new_gens = []
                for x, z in gens:
                    xb = 1 if (x & mask) else 0
                    zb = 1 if (z & mask) else 0
                    new_x = (x & ~mask) | (mask if zb else 0)
                    new_z = (z & ~mask) | (mask if xb else 0)
                    new_gens.append((new_x, new_z))
                gens = new_gens
                rank = trial_rank
                progressed = True
                break
        if not progressed:
            raise AssertionError("extraction: no single-qubit Hadamard raises X-rank")
    return gens


def _row_reduce_to_identity(generators: list[tuple[int, int]], k: int) -> list[tuple[int, int]]:
    """Gauss-Jordan eliminate (full-rank) generators so row i has
    x_bits == 1 << i for every i."""
    rows = list(generators)
    for col in range(k):
        mask = 1 << col
        pivot_row = next((r for r in range(col, k) if rows[r][0] & mask), None)
        if pivot_row is None:
            raise AssertionError(f"extraction: X-side not full rank at column {col}")
        rows[col], rows[pivot_row] = rows[pivot_row], rows[col]
        xcol, zcol = rows[col]
        for r in range(k):
            if r != col and (rows[r][0] & mask):
                xr, zr = rows[r]
                rows[r] = (xr ^ xcol, zr ^ zcol)
    return rows


class GF2Engine:
    """Engine B: fusion on a pure-Python GF(2) bitmask stabilizer tableau.

    Same public triple as engine A -- `state_from_graph` / `fuse` /
    `to_graphstate` -- implemented independently on a genuinely different
    data structure (int bitmask generator pairs, no external tableau or
    array library).
    """

    def state_from_graph(self, gs: GraphState) -> GF2State:
        generators = []
        for v in range(gs.n):
            x = 1 << v
            z = 0
            for u in gs.neighbors(v):
                z |= 1 << u
            generators.append((x, z))
        return GF2State(generators=tuple(generators), active=tuple(range(gs.n)))

    def fuse(self, state: GF2State, a: int, b: int) -> GF2State:
        """Destructive fusion measurement of {X_a Z_b, Z_a X_b} on ACTIVE
        qubits a, b. Functional: never mutates `state`; returns a fresh
        GF2State with a, b removed from the active set."""
        if a == b:
            raise ValueError(f"cannot fuse a qubit with itself: {a}")
        if a not in state.active or b not in state.active:
            raise ValueError(
                f"fuse requires active qubits, got a={a}, b={b}, active={state.active}"
            )

        pa = state.active.index(a)
        pb = state.active.index(b)

        gens = _measure(list(state.generators), 1 << pa, 1 << pb)  # B1 = X_a Z_b
        gens = _measure(gens, 1 << pb, 1 << pa)  # B2 = Z_a X_b
        # Either measurement may have been deterministic (no-op): B1, B2 are
        # in the sign-free group regardless, so (a, b) is now a Bell pair
        # disentangled from the rest -- the general elimination below removes
        # it without assuming B1/B2 sit in the generator list.

        def block(x: int, z: int) -> int:
            return (
                (((x >> pa) & 1) << 3)
                | (((z >> pa) & 1) << 2)
                | (((x >> pb) & 1) << 1)
                | ((z >> pb) & 1)
            )

        # Eliminate on the 4-bit (a, b)-block: up to 2 pivots with independent
        # nonzero blocks; XOR them into everything else -> all others block-free.
        block_pivots: dict[int, tuple[int, int, int]] = {}  # lead block bit -> (block, x, z)
        cleared: list[tuple[int, int]] = []
        for x, z in gens:
            beta = block(x, z)
            while beta:
                lead = beta.bit_length() - 1
                if lead not in block_pivots:
                    break
                pbeta, px, pz = block_pivots[lead]
                beta ^= pbeta
                x ^= px
                z ^= pz
            if beta:
                if len(block_pivots) == 2:
                    raise AssertionError(
                        f"fusion({a}, {b}): (a, b)-block rank > 2 -- the pair is not "
                        "disentangled; the measurement update is wrong"
                    )
                block_pivots[beta.bit_length() - 1] = (beta, x, z)
            else:
                cleared.append((x, z))
        if len(block_pivots) != 2:
            raise AssertionError(
                f"fusion({a}, {b}): (a, b)-block rank {len(block_pivots)} != 2 -- "
                "the group lacks an independent Bell-pair stabilizer pair; "
                "the measurement update is wrong"
            )

        # The 2 pivots' support OUTSIDE {a, b} must lie in the span of the
        # block-free generators (they equal pure Bell stabilizers times
        # zero-block group elements) -- assert it reduces to exactly zero.
        nbits = len(state.active)
        outside_mask = ~((1 << pa) | (1 << pb))
        basis: dict[int, int] = {}
        for x, z in cleared:
            _basis_insert(basis, x | (z << nbits))
        for _, px, pz in block_pivots.values():
            residual = _reduce_vector(basis, (px & outside_mask) | ((pz & outside_mask) << nbits))
            if residual:
                raise AssertionError(
                    f"fusion({a}, {b}): pivot support outside the fused pair does not "
                    "vanish -- the pair is not disentangled; the measurement update is wrong"
                )

        lo, hi = (pa, pb) if pa < pb else (pb, pa)
        new_generators = tuple(
            (_compact_bits(x, lo, hi), _compact_bits(z, lo, hi)) for x, z in cleared
        )
        new_active = tuple(q for i, q in enumerate(state.active) if i not in (pa, pb))
        return GF2State(generators=new_generators, active=new_active)

    def to_graphstate(self, state: GF2State) -> GraphState:
        """LC-equivalent graph extraction over the active qubits, relabelled
        0..k-1 in `state.active` order."""
        k = len(state.active)
        if k == 0:
            return GraphState(n=0, edges=[])

        gens = _ensure_full_x_rank(list(state.generators), k)
        gens = _row_reduce_to_identity(gens, k)

        edges = []
        for i in range(k):
            zi = gens[i][1]
            for j in range(i + 1, k):
                bit_i_j = (zi >> j) & 1
                bit_j_i = (gens[j][1] >> i) & 1
                assert bit_i_j == bit_j_i, f"extraction: asymmetric adjacency at ({i}, {j})"
                if bit_i_j:
                    edges.append((i, j))
        return GraphState(n=k, edges=edges)

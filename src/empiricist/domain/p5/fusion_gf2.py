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
  already determined, state unchanged. Otherwise pick one anticommuting
  generator as the pivot, fold it (XOR) into every *other* anticommuting
  generator, then overwrite the pivot slot with P itself.
- Fusion of active qubits (a, b) measures the ratified commuting pair
  `{X_a Z_b, Z_a X_b}` (spec D6: NOT `{X_a X_b, Z_a Z_b}` -- the two
  conventions differ by a free Hadamard on one fusion qubit and thus give the
  same LC orbit, but `{XZ, ZX}` is the one whose bit bookkeeping matches the
  graph rule used by the goldens here). Both measured operators always
  commute with each other, so measuring the second can never disturb the
  generator that now holds the first (that generator's row is provably never
  in the second measurement's anticommuting set). After both measurements,
  every *other* generator in the group must commute with both pivots, which
  forces (by the same symplectic-form identity) `x_a(g) == z_b(g)` and
  `x_b(g) == z_a(g)` for every such g -- so XORing by the X_aZ_b pivot when
  `x_a(g)` is set, and by the Z_aX_b pivot when `x_b(g)` is set, always fully
  clears both the X and Z support at a and b simultaneously. The two pivot
  rows are then dropped (they now describe an isolated Bell pair on a, b) and
  bit positions a, b are compacted out of every remaining generator, shifting
  higher bit positions down so the k = n - 2 survivors live on qubits
  0..k-1.
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


def _measure(
    generators: list[tuple[int, int]], xp: int, zp: int
) -> tuple[list[tuple[int, int]], int | None]:
    """Update `generators` for measuring Pauli (xp, zp); return (new list,
    index of the row now holding (xp, zp)), or (unchanged list, None) if the
    outcome was already determined (no anticommuting generator)."""
    anticommuting = [i for i, (xg, zg) in enumerate(generators) if _anticommute(xg, zg, xp, zp)]
    if not anticommuting:
        return list(generators), None
    pivot_idx = anticommuting[0]
    xg0, zg0 = generators[pivot_idx]
    new_generators = list(generators)
    for i in anticommuting[1:]:
        xi, zi = new_generators[i]
        new_generators[i] = (xi ^ xg0, zi ^ zg0)
    new_generators[pivot_idx] = (xp, zp)
    return new_generators, pivot_idx


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

        gens, pivot1_idx = _measure(list(state.generators), 1 << pa, 1 << pb)
        gens, pivot2_idx = _measure(gens, 1 << pb, 1 << pa)
        if pivot1_idx is None or pivot2_idx is None:
            raise AssertionError(
                f"fusion({a}, {b}) was deterministic (Bell pair already fixed) -- "
                "unexpected for a freshly active pair; measurement update is wrong"
            )

        pivot1 = gens[pivot1_idx]
        pivot2 = gens[pivot2_idx]

        cleared: list[tuple[int, int]] = []
        for i, (x, z) in enumerate(gens):
            if i == pivot1_idx or i == pivot2_idx:
                continue
            if (x >> pa) & 1:
                x ^= pivot1[0]
                z ^= pivot1[1]
            if (x >> pb) & 1:
                x ^= pivot2[0]
                z ^= pivot2[1]
            assert not ((x >> pa) & 1 or (z >> pa) & 1 or (x >> pb) & 1 or (z >> pb) & 1), (
                f"fusion({a}, {b}): Bell pair not disentangled, residual support at {pa}, {pb}"
            )
            cleared.append((x, z))

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

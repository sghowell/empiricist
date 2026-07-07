"""Engine A: fusion on a stim TableauSimulator (destructive Bell measurement).

Physics (spec D6, plan header): a fusion on qubits (a, b) is the destructive
measurement of a commuting Bell-basis pair on (a, b). We postselect the
(+1, +1) branch WLOG -- the four outcomes differ only by Pauli corrections,
which are local Cliffords, invisible to the LC-orbit identity. If the +1
branch of an observable is impossible (the state is already deterministically
-1, which happens for intra-component fusions), we postselect -1 instead --
same LC orbit either way. After both measurements, qubits a,b hold a Bell pair
disentangled from the rest and are dropped from the active set (the stim
tableau itself never shrinks -- qubits are never physically removed, only
marked inactive).

**Which commuting pair, exactly (verified against the golden facts):** the
plan header names {X_a X_b, Z_a Z_b}. Empirically, measuring THAT pair on the
GHZ3(0;1,2) + GHZ3(3;4,5) golden (fusing leaves 2,4) yields a 4-qubit STAR
(all four postselection branches agree -- confirmed by exhaustive sweep, by
independent hand-derivation of the post-measurement stabilizer generators via
the standard anticommuting-generator update rule, and by literally applying a
physical `sim.h(0)` and re-extracting), which is a DIFFERENT LC orbit than the
golden's required P4. Sweeping the other two commuting Bell-classifying pairs
found the fix: {X_a Z_b, Z_a X_b} (equivalently: apply a Hadamard to ONE of
the two fusion qubits before measuring the "plain" {X_aX_b, Z_aZ_b} pair --
X_aZ_b = H_b (X_aX_b) H_b, Z_aX_b = H_b (Z_aZ_b) H_b) reproduces P4 for that
golden AND the complete-bipartite disjoint-fusion golden. This pair is
symmetric in (a, b) (swapping a<->b just reorders the two observables), still
commuting (verified: X_aZ_b and Z_aX_b anticommute at both qubits, an even
total, so they commute), and still partitions the 2-qubit space into 4
orthogonal maximally-entangled states -- a Bell-like basis, just rotated by a
local Hadamard on one qubit relative to the "plain" XX/ZZ Bell basis. Per the
plan's own instruction ("the goldens are the arbiter... fix the code"), this
implementation measures {X_a Z_b, Z_a X_b}.

Sign convention for `postselect_observable`, VERIFIED EMPIRICALLY (ad hoc
probe against the installed stim 1.16, not checked into the test suite):
preparing |0> (a +1 eigenstate of Z) and calling
`sim.postselect_observable(Z, desired_value=False)` succeeds and leaves
`peek_observable_expectation(Z) == +1`; calling it with `desired_value=True`
on |1> (a -1 eigenstate of Z) also succeeds, leaving expectation -1.
Attempting `desired_value=False` on |1> raises ValueError ("impossible to
postselect into the +1 eigenstate"). So: desired_value=False <-> +1 branch,
desired_value=True <-> -1 branch, matching stim's own docstring exactly.
Hence: try desired_value=False (+1) first, fall back to desired_value=True
(-1) if stim raises ValueError on the impossible branch.

Extraction (stabilizer tableau -> LC-equivalent graph, Van den Nest): the
post-fusion state factorizes as (active-qubit graph state) tensor (a bunch of
disentangled Bell pairs on now-inactive qubits). `sim.canonical_stabilizers()`
returns n_total independent generators for the full (never-shrunk) tableau;
because of the tensor factorization these MUST split cleanly into exactly
(n_total - k) generators supported entirely on inactive qubits and k
generators supported entirely on the k active qubits (this was verified
empirically across the golden scenarios below -- canonical_stabilizers()
already produces a clean split in every case tried). We still assert the
split and fall back to an explicit GF(2) row-elimination (using the inactive
columns as pivots) if it doesn't hold, since the fallback is cheap and turns a
silent physics bug into a loud one instead.

Once we have the k x k [X | Z] block restricted to active qubits (columns
relabelled 0..k-1 in `active` order), we complete the X-block to full GF(2)
rank via H-swaps (X/Z column swaps -- a free local Clifford) if needed, invert
it, and read off the adjacency A = X^-1 Z (mod 2); the diagonal (S-gate
artifacts, also local Cliffords) is zeroed. `GraphState.from_adjacency`
validates symmetry -- an asymmetric A here would mean the extraction is wrong.

Signs are ignored throughout (documented simplification, spec D6): sign flips
are Pauli corrections = local Cliffords, invisible to the LC orbit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import stim

from empiricist.domain.p5.graphstate import GraphState


@dataclass(frozen=True)
class StimState:
    """A stim TableauSimulator plus the tuple of currently-active (global,
    never-relabelled) qubit indices. The simulator is mutated in place by
    `fuse` (postselection collapses it); the frozen wrapper only tracks which
    qubits are still "live" after Bell-pair qubits are dropped."""

    sim: stim.TableauSimulator
    active: tuple[int, ...]


class StimEngine:
    """Engine A: fusion on a stim TableauSimulator. Tracks (sim, active qubit ids)."""

    def state_from_graph(self, gs: GraphState) -> StimState:
        sim = stim.TableauSimulator()
        gs.apply_state_prep(sim)
        return StimState(sim=sim, active=tuple(range(gs.n)))

    def fuse(self, state: StimState, a: int, b: int) -> StimState:
        """Destructive Bell measurement {X_aZ_b, Z_aX_b} on ACTIVE qubits a,b
        (see module docstring for why this pair, not the naive {X_aX_b,
        Z_aZ_b}, is the one that reproduces the golden facts). Postselects +1
        (falls back to -1 if forced); removes a,b from active."""
        if a == b:
            raise ValueError(f"cannot fuse a qubit with itself: got a=b={a}")
        active_set = set(state.active)
        if a not in active_set or b not in active_set:
            raise ValueError(
                f"fuse requires both qubits active; active={state.active}, "
                f"got a={a}, b={b}"
            )
        n_total = state.sim.num_qubits
        _postselect_pair(state.sim, n_total, a, "X", b, "Z")
        _postselect_pair(state.sim, n_total, a, "Z", b, "X")
        new_active = tuple(q for q in state.active if q != a and q != b)
        return StimState(sim=state.sim, active=new_active)

    def to_graphstate(self, state: StimState) -> GraphState:
        """LC-equivalent graph extraction over the active qubits (relabelled 0..k-1)."""
        active = list(state.active)
        k = len(active)
        if k == 0:
            return GraphState(n=0, edges=[])

        n_total = state.sim.num_qubits
        stabs = state.sim.canonical_stabilizers()
        assert len(stabs) == n_total, (
            f"expected {n_total} canonical stabilizer generators, got {len(stabs)}"
        )

        split = _fast_split(stabs, n_total, active)
        Xk, Zk = split if split is not None else _force_split_gf2(stabs, n_total, active)

        Xk, Zk = _rank_complete(Xk, Zk)
        Xinv = _gf2_inverse(Xk)
        A = (Xinv @ Zk) % 2
        np.fill_diagonal(A, 0)
        return GraphState.from_adjacency(A)


def _postselect_pair(
    sim: stim.TableauSimulator, n_total: int, a: int, pauli_a: str, b: int, pauli_b: str
) -> None:
    """Postselect the two-qubit observable `pauli_a`_a `pauli_b`_b to +1
    (falling back to -1 if the +1 branch is impossible -- an
    already-deterministic intra-component state)."""
    obs = stim.PauliString(n_total)
    obs[a] = pauli_a
    obs[b] = pauli_b
    try:
        sim.postselect_observable(obs, desired_value=False)  # +1 eigenstate
    except ValueError:
        sim.postselect_observable(obs, desired_value=True)  # -1 eigenstate fallback


def _fast_split(
    stabs: list[stim.PauliString], n_total: int, active: list[int]
) -> tuple[np.ndarray, np.ndarray] | None:
    """Try to split canonical_stabilizers() directly into active-only-support
    rows. Returns (Xk, Zk) k x k uint8 arrays (columns/rows ordered to match
    `active`) if every generator is cleanly active-only or inactive-only;
    None if any generator has mixed support or the counts don't match
    (signals the caller to fall back to explicit GF(2) elimination)."""
    active_set = set(active)
    k = len(active)
    xs_rows: list[np.ndarray] = []
    zs_rows: list[np.ndarray] = []
    inactive_count = 0
    for ps in stabs:
        xs, zs = ps.to_numpy()
        support = set(np.flatnonzero(xs | zs).tolist())
        if support <= active_set:
            xs_rows.append(xs[active].astype(np.uint8))
            zs_rows.append(zs[active].astype(np.uint8))
        elif support.isdisjoint(active_set):
            inactive_count += 1
        else:
            return None  # mixed support -- canonical form didn't split cleanly
    if len(xs_rows) != k or inactive_count != n_total - k:
        return None
    return np.array(xs_rows, dtype=np.uint8), np.array(zs_rows, dtype=np.uint8)


def _force_split_gf2(
    stabs: list[stim.PauliString], n_total: int, active: list[int]
) -> tuple[np.ndarray, np.ndarray]:
    """Fallback: force the active/inactive split via GF(2) row elimination,
    using the inactive-qubit columns as pivots. Because the post-fusion state
    is a genuine tensor product (active-qubit graph state) x (Bell pairs on
    inactive qubits), the stabilizer vector space is the direct sum of an
    inactive-only subspace (dim n_total - k) and an active-only subspace (dim
    k); eliminating every inactive column leaves exactly k rows with zero
    inactive-column support -- those are our active-only generators."""
    active_set = set(active)
    inactive = [q for q in range(n_total) if q not in active_set]
    k = len(active)

    xs_all = np.array([ps.to_numpy()[0] for ps in stabs], dtype=np.uint8)
    zs_all = np.array([ps.to_numpy()[1] for ps in stabs], dtype=np.uint8)
    M = np.concatenate([xs_all, zs_all], axis=1)  # (n_total, 2*n_total): [X | Z]

    used = np.zeros(n_total, dtype=bool)
    inactive_cols = inactive + [n_total + q for q in inactive]
    for col in inactive_cols:
        candidates = np.flatnonzero((~used) & (M[:, col] == 1))
        if candidates.size == 0:
            continue
        pivot = candidates[0]
        used[pivot] = True
        rows_to_clear = np.flatnonzero((M[:, col] == 1) & (np.arange(n_total) != pivot))
        for r in rows_to_clear:
            M[r, :] ^= M[pivot, :]

    free_rows = np.flatnonzero(~used)
    if free_rows.size != k:
        raise AssertionError(
            f"GF(2) split failed: expected {k} active-support generators after "
            f"eliminating inactive columns, got {free_rows.size} -- the post-fusion "
            "state does not factorize as expected (extraction bug or physics bug)"
        )
    active_cols = active + [n_total + q for q in active]
    other_cols = [c for c in range(2 * n_total) if c not in set(active_cols)]
    if not np.all(M[np.ix_(free_rows, other_cols)] == 0):
        raise AssertionError(
            "GF(2) split failed to fully isolate active-qubit support after "
            "eliminating all inactive columns"
        )
    sub = M[np.ix_(free_rows, active_cols)]
    return sub[:, :k].copy(), sub[:, k:].copy()


def _gf2_rank(M: np.ndarray) -> int:
    M = (M.copy() % 2).astype(np.uint8)
    rows, cols = M.shape
    rank = 0
    for col in range(cols):
        pivot_row = None
        for r in range(rank, rows):
            if M[r, col]:
                pivot_row = r
                break
        if pivot_row is None:
            continue
        M[[rank, pivot_row]] = M[[pivot_row, rank]]
        for r in range(rows):
            if r != rank and M[r, col]:
                M[r, :] ^= M[rank, :]
        rank += 1
    return rank


def _rank_complete(Xk: np.ndarray, Zk: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """While rank_GF2(X) < k, find a qubit column j where swapping the X/Z
    columns (applying H at j -- a free local Clifford) increases the rank,
    and swap. Terminates: a stabilizer generator matrix has full [X|Z] rank,
    so some sequence of H-swaps always drives the X-block to full rank."""
    Xk = Xk.copy()
    Zk = Zk.copy()
    k = Xk.shape[0]
    current_rank = _gf2_rank(Xk)
    while current_rank < k:
        swapped = False
        for j in range(k):
            trial = Xk.copy()
            trial[:, j] = Zk[:, j]
            trial_rank = _gf2_rank(trial)
            if trial_rank > current_rank:
                Xk[:, j], Zk[:, j] = Zk[:, j].copy(), Xk[:, j].copy()
                current_rank = trial_rank
                swapped = True
                break
        if not swapped:
            raise AssertionError(
                "rank completion stalled: no H-swap increases X-block rank -- "
                "shouldn't happen for a valid stabilizer generator set"
            )
    return Xk, Zk


def _gf2_inverse(X: np.ndarray) -> np.ndarray:
    """Gauss-Jordan inverse of a full-rank k x k GF(2) matrix."""
    k = X.shape[0]
    aug = np.concatenate([X.copy() % 2, np.eye(k, dtype=np.uint8)], axis=1).astype(np.uint8)
    rank = 0
    for col in range(k):
        pivot_row = None
        for r in range(rank, k):
            if aug[r, col]:
                pivot_row = r
                break
        if pivot_row is None:
            raise AssertionError(f"X-block not invertible over GF(2) at column {col}")
        aug[[rank, pivot_row]] = aug[[pivot_row, rank]]
        for r in range(k):
            if r != rank and aug[r, col]:
                aug[r, :] ^= aug[rank, :]
        rank += 1
    return aug[:, k:]

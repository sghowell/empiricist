"""GraphState: an undirected simple graph and its equivalent quantum views.

|G> is the graph state stabilized by { X_v * prod_{u in N(v)} Z_u }_v (spec §8.2).
Three equivalent representations, all derivable from the edge set:
  - a GF(2) adjacency matrix (numpy uint8),
  - the stabilizer generators (stim.PauliString, one per vertex),
  - the stim state-prep circuit (H on every qubit, then CZ per edge).
Frozen/hashable so it can be a dict key and set member.

Verified against the installed stim 1.16 API (see tests/test_p5_graphstate.py):
`stim.PauliString(n)` allocates an all-identity string; per-qubit Pauli type is
set via item assignment `ps[v] = "X"` and read back as an int (0=I,1=X,2=Y,3=Z),
and `ps.pauli_indices("X")` lists the qubits carrying that Pauli type.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import stim


@dataclass(frozen=True)
class GraphState:
    n: int
    edges: frozenset[tuple[int, int]] = field(default_factory=frozenset)

    def __init__(self, n: int, edges) -> None:
        norm: set[tuple[int, int]] = set()
        for a, b in edges:
            if a == b:
                raise ValueError(f"self-loop not allowed: ({a}, {b})")
            if not (0 <= a < n and 0 <= b < n):
                raise ValueError(f"edge out of range for n={n}: ({a}, {b})")
            norm.add((a, b) if a < b else (b, a))
        object.__setattr__(self, "n", n)
        object.__setattr__(self, "edges", frozenset(norm))

    def adjacency(self) -> np.ndarray:
        """The GF(2) adjacency matrix: symmetric, zero diagonal, uint8-valued."""
        A = np.zeros((self.n, self.n), dtype=np.uint8)
        for a, b in self.edges:
            A[a, b] = A[b, a] = 1
        return A

    def neighbors(self, v: int) -> frozenset[int]:
        return frozenset(b if a == v else a for a, b in self.edges if v in (a, b))

    def stabilizers(self) -> list[stim.PauliString]:
        """One generator per vertex v: X_v * prod_{u in N(v)} Z_u."""
        stabs = []
        for v in range(self.n):
            ps = stim.PauliString(self.n)
            ps[v] = "X"
            for u in self.neighbors(v):
                ps[u] = "Z"
            stabs.append(ps)
        return stabs

    def apply_state_prep(self, sim: stim.TableauSimulator) -> None:
        """Prepare |G> on `sim`: H on every qubit, then CZ on every edge."""
        sim.set_num_qubits(self.n)
        for q in range(self.n):
            sim.h(q)
        for a, b in sorted(self.edges):
            sim.cz(a, b)

    @classmethod
    def from_adjacency(cls, A: np.ndarray) -> GraphState:
        n = A.shape[0]
        edges = [(i, j) for i in range(n) for j in range(i + 1, n) if A[i, j]]
        return cls(n=n, edges=edges)

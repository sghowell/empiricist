# src/empiricist/domain/p3/engine_permanent.py
"""Engine A: detection-pattern distributions via matrix permanents.

For input Fock state |T> and output |S> (equal total photon number n),
  <S| U_hat |T> = Per(U[S, T]) / sqrt(prod_i s_i! * prod_j t_j!)
where U[S, T] repeats column j of U t_j times and row i s_i times. Inputs are
finite Fock superpositions; amplitudes add linearly before squaring.
Independence: this engine is the ONLY code that forms U or a permanent.
"""

from __future__ import annotations

import numpy as np

from .fock import factorial_prod, patterns
from .interferometer import Mesh, mesh_unitary

FockState = dict[tuple[int, ...], complex]


def _permanent(a: np.ndarray) -> complex:
    """Ryser's formula (n <= ~12 here)."""
    n = a.shape[0]
    if n == 0:
        return 1.0 + 0.0j
    total = 0.0 + 0.0j
    for mask in range(1, 1 << n):
        col_sum = np.zeros(n, dtype=np.complex128)
        bits = 0
        for j in range(n):
            if mask & (1 << j):
                col_sum += a[:, j]
                bits += 1
        total += (-1) ** bits * np.prod(col_sum)
    return ((-1) ** n) * total


def _submatrix(
    u: np.ndarray, out_pattern: tuple[int, ...], in_pattern: tuple[int, ...]
) -> np.ndarray:
    rows = [i for i, s in enumerate(out_pattern) for _ in range(s)]
    cols = [j for j, t in enumerate(in_pattern) for _ in range(t)]
    return u[np.ix_(rows, cols)]


class PermanentEngine:
    name = "permanent"

    def output_distribution(
        self, mesh: Mesh, input_state: FockState
    ) -> dict[tuple[int, ...], float]:
        u = mesh_unitary(mesh)
        n_photons = sum(next(iter(input_state)))
        for pat in input_state:
            if sum(pat) != n_photons:
                raise ValueError("input superposition mixes photon numbers")
        out: dict[tuple[int, ...], float] = {}
        for s in patterns(n_photons, mesh.n_modes):
            amp = 0.0 + 0.0j
            for t, a_t in input_state.items():
                if a_t == 0:
                    continue
                per = _permanent(_submatrix(u, s, t))
                amp += a_t * per / np.sqrt(factorial_prod(s) * factorial_prod(t))
            p = abs(amp) ** 2
            if p > 1e-15:
                out[s] = float(p)
        return out

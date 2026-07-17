# src/empiricist/domain/p3/engine_fock.py
"""Engine B: detection-pattern distributions by direct Fock-basis evolution.

Independence constraint (absolute — this is the trust warrant for the whole
pair of engines): this module NEVER forms the mode unitary and NEVER computes
a permanent. Each mesh element is applied directly as an operator on the
photon-number-sector Fock basis, element by element, in order. It imports
ONLY `.fock` (basis order/helpers) and the `Mesh` type from `.interferometer`
(never `mesh_unitary`, never `engine_permanent`).

CONVENTION (mirrors interferometer.py's normative docstring, implemented here
independently, from scratch, on creation operators):

    bs(i, j, theta, phi):   a†_i -> cos(theta) a†_i + e^{i phi} sin(theta) a†_j
                            a†_j -> -e^{-i phi} sin(theta) a†_i + cos(theta) a†_j
    phase(i, alpha):        a†_i -> e^{i alpha} a†_i

For a two-mode occupation |n1, n2>, expand
  (c a†_i + e^{i phi} s a†_j)^{n1} (-e^{-i phi} s a†_i + c a†_j)^{n2} |0,0> / sqrt(n1! n2!)
by binomials: term (k1, k2) contributes
  C(n1,k1) C(n2,k2) c^{k1} (e^{i phi} s)^{n1-k1} (-e^{-i phi} s)^{k2} c^{n2-k2}
to (p, q) = (k1+k2, n1-k1+n2-k2), scaled by sqrt(p! q!) / sqrt(n1! n2!) to
restore normalized-Fock-state amplitudes.
"""

from __future__ import annotations

from math import comb, factorial, sqrt

import numpy as np

from .fock import patterns  # noqa: F401  (basis order; used by callers/tests)
from .interferometer import Mesh

FockState = dict[tuple[int, ...], complex]


def _bs_two_mode(n1: int, n2: int, theta: float, phi: float) -> dict[tuple[int, int], complex]:
    """Image of |n1, n2> under bs(theta, phi), as {(p, q): amplitude}."""
    c, s = np.cos(theta), np.sin(theta)
    e_pos, e_neg = np.exp(1j * phi), np.exp(-1j * phi)
    out: dict[tuple[int, int], complex] = {}
    for k1 in range(n1 + 1):
        for k2 in range(n2 + 1):
            coeff = (
                comb(n1, k1) * comb(n2, k2)
                * (c ** k1) * ((e_pos * s) ** (n1 - k1))
                * ((-e_neg * s) ** k2) * (c ** (n2 - k2))
            )
            p, q = k1 + k2, (n1 - k1) + (n2 - k2)
            norm = sqrt(factorial(p) * factorial(q)) / sqrt(factorial(n1) * factorial(n2))
            out[(p, q)] = out.get((p, q), 0.0 + 0.0j) + coeff * norm
    return out


class FockEngine:
    name = "fock"

    def output_distribution(
        self, mesh: Mesh, input_state: FockState
    ) -> dict[tuple[int, ...], float]:
        """Assumes a normalized input amplitude vector; probabilities are
        reported as computed (a non-normalized input yields a non-normalized
        distribution)."""
        if not input_state:
            raise ValueError("empty input_state")
        for pat in input_state:
            if len(pat) != mesh.n_modes:
                raise ValueError(
                    f"input pattern {pat!r} has {len(pat)} modes, mesh has {mesh.n_modes}"
                )
            if any((not isinstance(n, int)) or n < 0 for n in pat):
                raise ValueError(f"occupations must be non-negative integers, got {pat!r}")
        n_photons = sum(next(iter(input_state)))
        for pat in input_state:
            if sum(pat) != n_photons:
                raise ValueError("input superposition mixes photon numbers")

        state: FockState = {tuple(k): complex(v) for k, v in input_state.items()}
        for el in mesh.elements:
            if el[0] == "bs":
                _, i, j, theta, phi = el
                i, j = int(i), int(j)
                nxt: FockState = {}
                for pat, amp in state.items():
                    if amp == 0:
                        continue
                    for (p, q), coeff in _bs_two_mode(pat[i], pat[j], theta, phi).items():
                        new = list(pat)
                        new[i], new[j] = p, q
                        key = tuple(new)
                        nxt[key] = nxt.get(key, 0.0 + 0.0j) + amp * coeff
                state = nxt
            elif el[0] == "phase":
                _, i, alpha = el[0], el[1], el[2]
                i = int(i)
                state = {
                    pat: amp * np.exp(1j * float(alpha) * pat[i]) for pat, amp in state.items()
                }
            else:
                raise ValueError(f"unknown mesh element kind {el[0]!r}")

        out: dict[tuple[int, ...], float] = {}
        for pat, amp in state.items():
            p = float(abs(amp) ** 2)
            # prune threshold; the cross-engine comparator must treat missing
            # keys as 0.0 (union-of-keys), never compare key sets
            if p > 1e-15:
                out[pat] = p
        return out

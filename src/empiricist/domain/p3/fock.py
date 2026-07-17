"""Fock-basis combinatorics for the P3 linear-optics domain.

A detection pattern is a tuple (n_0, ..., n_{m-1}) of photon counts summing to
the total photon number. `patterns` enumerates the full n-photon sector in a
deterministic lexicographic order shared by both engines.
"""

from __future__ import annotations

from functools import cache
from math import factorial


@cache
def patterns(n_photons: int, n_modes: int) -> list[tuple[int, ...]]:
    """All (n_0..n_{m-1}) with sum == n_photons, lexicographically sorted."""
    if n_modes == 1:
        return [(n_photons,)]
    out: list[tuple[int, ...]] = []
    for first in range(n_photons + 1):
        for rest in patterns(n_photons - first, n_modes - 1):
            out.append((first, *rest))
    return out


def pattern_index(pattern: tuple[int, ...]) -> int:
    """Index of `pattern` within patterns(sum(pattern), len(pattern))."""
    return patterns(sum(pattern), len(pattern)).index(pattern)


def factorial_prod(pattern: tuple[int, ...]) -> int:
    out = 1
    for n in pattern:
        out *= factorial(n)
    return out

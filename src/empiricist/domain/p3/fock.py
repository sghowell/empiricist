"""Fock-basis combinatorics for the P3 linear-optics domain.

A detection pattern is a tuple (n_0, ..., n_{m-1}) of photon counts summing to
the total photon number. `patterns` enumerates the full n-photon sector in a
deterministic lexicographic order shared by both engines.
"""

from __future__ import annotations

from functools import cache
from math import factorial


@cache
def patterns(n_photons: int, n_modes: int) -> tuple[tuple[int, ...], ...]:
    """All (n_0..n_{m-1}) with sum == n_photons, lexicographically sorted."""
    if n_photons < 0 or n_modes < 0:
        raise ValueError("n_photons and n_modes must be nonnegative")
    if n_modes == 0:
        return ((),) if n_photons == 0 else ()
    out: list[tuple[int, ...]] = []
    for first in range(n_photons + 1):
        for rest in patterns(n_photons - first, n_modes - 1):
            out.append((first, *rest))
    return tuple(out)


@cache
def _index_map(n_photons: int, n_modes: int) -> dict[tuple[int, ...], int]:
    return {p: i for i, p in enumerate(patterns(n_photons, n_modes))}


def pattern_index(pattern: tuple[int, ...]) -> int:
    """Index of `pattern` within patterns(sum(pattern), len(pattern))."""
    return _index_map(sum(pattern), len(pattern))[pattern]


def factorial_prod(pattern: tuple[int, ...]) -> int:
    out = 1
    for n in pattern:
        out *= factorial(n)
    return out

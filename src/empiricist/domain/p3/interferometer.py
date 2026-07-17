"""Beamsplitter-mesh parametrization of a passive linear-optical interferometer.

A `Mesh` is an ordered list of elementary passive elements acting on creation
operators a†_0 .. a†_{m-1}. Because every element is unitary, any composition
is unitary by construction — no separate unitarity check is ever needed.

CONVENTION (normative — a second engine implements this same convention
independently; do not change it without updating both):

    bs(i, j, theta, phi):   a†_i -> cos(theta) a†_i + e^{i phi} sin(theta) a†_j
                            a†_j -> -e^{-i phi} sin(theta) a†_i + cos(theta) a†_j
    phase(i, alpha):        a†_i -> e^{i alpha} a†_i

`mesh_unitary` composes elements IN ORDER into the m x m mode unitary U with
a†_i -> Sum_j U[j, i] a†_j (columns are images of input modes).

This module is intentionally self-contained: it must never share code with
the future permanent-independent Engine B that consumes a `Mesh` directly,
beyond this convention definition itself.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# element: ("bs", i, j, theta, phi) or ("phase", i, alpha, 0.0, 0.0)
Element = tuple[str, int, int | float, float, float]


def _index(x: object, el: tuple) -> int:
    xf = float(x)  # type: ignore[arg-type]
    if not xf.is_integer():
        raise ValueError(f"mode index must be integral, got {x!r} in {el!r}")
    return int(xf)


def _angle(x: object, el: tuple) -> float:
    xf = float(x)  # type: ignore[arg-type]
    if not math.isfinite(xf):
        raise ValueError(f"angle must be finite, got {x!r} in {el!r}")
    return xf


@dataclass(frozen=True)
class Mesh:
    """Validated, immutable mesh. Numeric strings in element entries are
    coerced via float() (JSON-adjacent leniency)."""

    n_modes: int
    elements: tuple[Element, ...] = ()

    def __post_init__(self) -> None:
        if self.n_modes < 1:
            raise ValueError("n_modes must be >= 1")
        normalized: list[Element] = []
        for el in self.elements:
            el = tuple(el)
            kind = el[0]
            if kind == "bs":
                if len(el) != 5:
                    raise ValueError(f"bs element needs 5 entries, got {el!r}")
                i, j = _index(el[1], el), _index(el[2], el)
                if i == j:
                    raise ValueError(f"beamsplitter needs distinct modes, got i == j == {i}")
                if not (0 <= i < self.n_modes and 0 <= j < self.n_modes):
                    raise ValueError(f"mode index out of range in {el!r}")
                normalized.append(("bs", i, j, _angle(el[3], el), _angle(el[4], el)))
            elif kind == "phase":
                if len(el) not in (3, 5):
                    raise ValueError(f"phase element needs 3 (or padded 5) entries, got {el!r}")
                if len(el) == 5 and not (el[3] == 0.0 and el[4] == 0.0):
                    raise ValueError(f"phase element padding must be 0.0, got {el!r}")
                i = _index(el[1], el)
                if not (0 <= i < self.n_modes):
                    raise ValueError(f"mode index out of range in {el!r}")
                normalized.append(("phase", i, _angle(el[2], el), 0.0, 0.0))
            else:
                raise ValueError(f"unknown mesh element kind {kind!r}")
        object.__setattr__(self, "elements", tuple(normalized))


def _element_unitary(n: int, el: Element) -> np.ndarray:
    u = np.eye(n, dtype=np.complex128)
    kind = el[0]
    if kind == "bs":
        _, i, j, theta, phi = el
        i, j = int(i), int(j)
        c, s = np.cos(theta), np.sin(theta)
        u[i, i] = c
        u[j, i] = np.exp(1j * phi) * s
        u[i, j] = -np.exp(-1j * phi) * s
        u[j, j] = c
    elif kind == "phase":
        _, i, alpha = el[0], el[1], el[2]
        u[int(i), int(i)] = np.exp(1j * float(alpha))
    else:
        raise ValueError(f"unknown mesh element kind {kind!r}")
    return u


def mesh_unitary(mesh: Mesh) -> np.ndarray:
    u = np.eye(mesh.n_modes, dtype=np.complex128)
    for el in mesh.elements:
        u = _element_unitary(mesh.n_modes, el) @ u
    return u

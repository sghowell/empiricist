"""Standard interpretation of small ZX diagrams (M24c Task 1).

`matrix(d)` is the linear map of a ground, well-formed diagram as a dense
`2^outputs x 2^inputs` complex matrix, computed by tensor contraction of the spider
tensors: a Z spider of degree n and phase a (in units of pi) is the tensor with entry 1
at (0,...,0), e^{i pi a} at (1,...,1) and 0 elsewhere (the scalar 1 + e^{i pi a} at
n = 0); an X spider is the same tensor with a Hadamard on every leg; a Hadamard edge is
the Hadamard matrix on that edge; a boundary vertex is the identity between its wire
and the external index. Row and column indices are big-endian in the output and input
order (outputs[0] is the most significant bit).

This is exact in spirit only: complex128 with a fixed tolerance after normalisation.
Budgets (boundary wires, vertex count, spider degree, open indices during contraction)
raise `SemanticsError` so a verifier reports ERROR rather than guessing.
"""
from __future__ import annotations

import math
from fractions import Fraction

import numpy as np

from empiricist.packs.zx.diagram import Diagram

MAX_BOUNDARY_WIRES = 6
MAX_VERTICES = 64
MAX_DEGREE = 16
MAX_OPEN_INDICES = 20
TOLERANCE = 1e-9

HADAMARD = np.array([[1, 1], [1, -1]], dtype=complex) / math.sqrt(2)


class SemanticsError(Exception):
    """The diagram cannot be evaluated here (ill-formed, non-ground or over budget)."""


def boundary_wires(d: Diagram) -> int:
    return len(d.inputs) + len(d.outputs)


def spider_tensor(kind: str, phase: Fraction, degree: int) -> np.ndarray:
    """The tensor of a `kind` spider with `degree` legs and phase `phase` (units of pi)."""
    if degree > MAX_DEGREE:
        raise SemanticsError(f"spider degree {degree} exceeds the budget {MAX_DEGREE}")
    e = np.exp(1j * math.pi * float(phase))
    if degree == 0:
        t = np.array(1 + e, dtype=complex)
    else:
        t = np.zeros((2,) * degree, dtype=complex)
        t[(0,) * degree] = 1
        t[(1,) * degree] = e
    if kind == "X":
        for axis in range(degree):
            t = np.moveaxis(np.tensordot(t, HADAMARD, axes=([axis], [0])), -1, axis)
    elif kind != "Z":
        raise SemanticsError(f"no tensor for vertex kind {kind!r}")
    return t


def _einsum2(a: np.ndarray, la: list[int], b: np.ndarray, lb: list[int],
             out: list[int]) -> np.ndarray:
    remap = {lab: i for i, lab in enumerate(dict.fromkeys(la + lb))}
    return np.einsum(a, [remap[x] for x in la], b, [remap[x] for x in lb],
                     [remap[x] for x in out])


def _trace_repeats(t: np.ndarray, labels: list[int]) -> tuple[np.ndarray, list[int]]:
    """Contract labels that occur twice on one operand (self-loops)."""
    uniq = list(dict.fromkeys(labels))
    if len(uniq) == len(labels):
        return t, labels
    keep = [x for x in uniq if labels.count(x) == 1]
    remap = {lab: i for i, lab in enumerate(uniq)}
    return np.einsum(t, [remap[x] for x in labels], [remap[x] for x in keep]), keep


def _contract_all(operands: list[tuple[np.ndarray, list[int]]],
                  external: list[int]) -> np.ndarray:
    ops = [_trace_repeats(t, labels) for t, labels in operands]
    ext = set(external)
    while len(ops) > 1:
        best = None
        for i in range(len(ops)):
            for j in range(i + 1, len(ops)):
                li, lj = ops[i][1], ops[j][1]
                shared = set(li) & set(lj)
                union = set(li) | set(lj)
                cost = (0 if shared else 1, len(union) - len(shared))
                if best is None or cost < best[0]:
                    best = (cost, i, j)
        assert best is not None
        _, i, j = best
        (ta, la), (tb, lb) = ops[i], ops[j]
        shared = set(la) & set(lb)
        out = [x for x in dict.fromkeys(la + lb) if x not in shared or x in ext]
        if len(out) > MAX_OPEN_INDICES:
            raise SemanticsError(
                f"contraction needs {len(out)} open indices, over the budget {MAX_OPEN_INDICES}"
            )
        result = _einsum2(ta, la, tb, lb, out)
        ops = [op for k, op in enumerate(ops) if k not in (i, j)] + [(result, out)]
    if not ops:
        return np.array(1, dtype=complex)
    t, labels = ops[0]
    if set(labels) != ext or len(labels) != len(external):
        raise SemanticsError("contraction left unexpected open indices")
    return np.einsum(t, [labels.index(x) for x in labels], [labels.index(x) for x in external])


def matrix(d: Diagram) -> np.ndarray:
    """The `2^len(outputs) x 2^len(inputs)` matrix of a ground, well-formed diagram."""
    problems = d.well_formedness_problems()
    if problems:
        raise SemanticsError("diagram is not well-formed: " + "; ".join(problems))
    if boundary_wires(d) > MAX_BOUNDARY_WIRES:
        raise SemanticsError(
            f"{boundary_wires(d)} boundary wires exceed the budget {MAX_BOUNDARY_WIRES}"
        )
    if len(d.vertices) > MAX_VERTICES:
        raise SemanticsError(f"{len(d.vertices)} vertices exceed the budget {MAX_VERTICES}")
    n_edges = len(d.edges)
    external = [2 * n_edges + j for j in range(boundary_wires(d))]
    position = {v: j for j, v in enumerate(d.outputs + d.inputs)}

    def end_label(edge_index: int, v: int, seen_ends: dict[int, int]) -> int:
        u, w, h = d.edges[edge_index]
        if not h:
            return 2 * edge_index
        n = seen_ends.get(edge_index, 0)
        seen_ends[edge_index] = n + 1
        if u == w:                        # a Hadamard self-loop: ends 2e and 2e+1
            return 2 * edge_index + n
        return 2 * edge_index if v == u else 2 * edge_index + 1

    operands: list[tuple[np.ndarray, list[int]]] = []
    for e, (_, _, h) in enumerate(d.edges):
        if h:
            operands.append((HADAMARD, [2 * e, 2 * e + 1]))
    for v, kind, phase in d.vertices:
        seen: dict[int, int] = {}
        legs = [end_label(e, v, seen) for e in d.incident(v)]
        if kind == "B":
            operands.append((np.eye(2, dtype=complex), [external[position[v]], legs[0]]))
        else:
            assert isinstance(phase, Fraction)
            operands.append((spider_tensor(kind, phase, len(legs)), legs))
    try:
        t = _contract_all(operands, external)
    except MemoryError as exc:
        raise SemanticsError("out of memory during contraction") from exc
    return np.asarray(t, dtype=complex).reshape(2 ** len(d.outputs), 2 ** len(d.inputs))


def equal_up_to_scalar(a: np.ndarray, b: np.ndarray, tol: float = TOLERANCE) -> bool:
    """True iff `b = c * a` for some complex `c`, or both are (numerically) zero."""
    a = np.asarray(a, dtype=complex)
    b = np.asarray(b, dtype=complex)
    if a.shape != b.shape:
        return False
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na <= tol and nb <= tol:
        return True
    if na <= tol or nb <= tol:
        return False
    ah, bh = a / na, b / nb
    lam = np.vdot(ah, bh)
    return float(np.linalg.norm(bh - lam * ah)) <= tol


__all__ = [
    "HADAMARD", "MAX_BOUNDARY_WIRES", "MAX_DEGREE", "MAX_OPEN_INDICES", "MAX_VERTICES",
    "TOLERANCE", "SemanticsError", "boundary_wires", "equal_up_to_scalar", "matrix",
    "spider_tensor",
]

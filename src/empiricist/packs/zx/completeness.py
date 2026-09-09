"""Bounded completeness against the semantic oracle (M25a Task 2).

A rewrite system is *complete* for a class of diagrams when semantically equal diagrams
of the class (equal linear maps up to a non-zero scalar) reduce to the same normal
form. This module decides that on an explicitly bounded class C(w, v, e) of stabilizer
diagrams: every well-formed diagram with at most `w` boundary wires (inputs then
outputs, every split), at most `v` interior spiders (Z or X, phases in the fragment's
set) and at most `e` edges counted with multiplicity (plain or Hadamard, self-loops and
parallel edges allowed), enumerated up to isomorphism (canonical dedup, smallest first).

Each diagram is reduced deterministically: the first applicable rule in the given
order, its first matching in `find_matchings` order, until no rule applies; the normal
form is the canonical form of the result. Diagrams are grouped by semantic class --
wire signature and matrix up to scalar, with every zero matrix of a signature in one
class -- and the system passes iff every class has exactly one normal form. A failure
is a *witness*: two enumerated diagrams that are semantically equal but reduce to
different normal forms (the smallest such pair in enumeration order, found as soon as
a class shows its second normal form, so a FAIL does not reduce the whole class).

Budgets raise `CompletenessError` -- more than `max_diagrams` diagrams in the class,
or a reduction running past `max_steps` -- because undecided is not a verdict.
Diagrams over the semantic budget are skipped and counted. A PASS says exactly: on
the stated class, with these rules in this order, semantically equal diagrams share a
normal form. Scalars count: the 0-wire diagrams of the class form two semantic
classes (zero and non-zero), so a passing system needs rules for closed components.
"""
from __future__ import annotations

import itertools
import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from fractions import Fraction

import numpy as np

from empiricist.packs.zx import semantics
from empiricist.packs.zx.diagram import Diagram, Edge
from empiricist.packs.zx.rewrite import RewriteError, apply, find_matchings
from empiricist.packs.zx.rules import PHASES_CLIFFORD, Rule

DEFAULT_MAX_WIRES = 2
DEFAULT_MAX_VERTICES = 3
DEFAULT_MAX_EDGES = 6
DEFAULT_MAX_STEPS = 200
DEFAULT_MAX_DIAGRAMS = 20000
KEY_DECIMALS = 6
PIVOT_SLACK = 1e-6


class CompletenessError(Exception):
    """A budget was exhausted: the question is undecided, not answered."""


@dataclass(frozen=True)
class Witness:
    a: Diagram
    b: Diagram
    normal_form_a: Diagram
    normal_form_b: Diagram

    @property
    def inputs(self) -> int:
        return len(self.a.inputs)

    @property
    def outputs(self) -> int:
        return len(self.a.outputs)


@dataclass
class CompletenessReport:
    diagrams: int = 0
    skipped: int = 0
    classes: int = 0
    reduced: int = 0
    normal_forms: int = 0
    steps_max: int = 0
    failure: Witness | None = None
    seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return self.failure is None


# ----------------------------------------------------------------------------- enumeration


def _boundary_attachments(w: int, interior: tuple[int, ...]) -> Iterator[list[Edge]]:
    """Every way to give each boundary vertex 0..w-1 exactly one edge end: to an interior
    vertex, or to a later boundary vertex, plain or Hadamard."""
    def rec(pending: tuple[int, ...]) -> Iterator[list[Edge]]:
        if not pending:
            yield []
            return
        b, rest = pending[0], pending[1:]
        for v in interior:
            for h in (False, True):
                for tail in rec(rest):
                    yield [(b, v, h), *tail]
        for i, b2 in enumerate(rest):
            others = rest[:i] + rest[i + 1:]
            for h in (False, True):
                for tail in rec(others):
                    yield [(b, b2, h), *tail]
    yield from rec(tuple(range(w)))


def enumerate_diagrams(phases: tuple[Fraction, ...], max_wires: int, max_vertices: int,
                       max_edges: int, max_diagrams: int) -> list[Diagram]:
    """Every well-formed diagram of C(max_wires, max_vertices, max_edges) over `phases`,
    up to isomorphism, in canonical form, smallest first (wires, then spiders, then
    edges). Raises `CompletenessError` past `max_diagrams`."""
    labels = [(kind, p) for kind in ("Z", "X") for p in phases]
    seen: set[str] = set()
    out: list[Diagram] = []
    for w in range(max_wires + 1):
        for n_in in range(w + 1):
            inputs, outputs = tuple(range(n_in)), tuple(range(n_in, w))
            for v in range(max_vertices + 1):
                interior = tuple(range(w, w + v))
                types: list[Edge] = [(i, j, h) for i in interior for j in interior if i <= j
                                     for h in (False, True)]
                for labelling in itertools.combinations_with_replacement(range(len(labels)), v):
                    verts: dict[int, tuple[str, Fraction]] = {b: ("B", Fraction(0))
                                                              for b in range(w)}
                    for x, li in zip(interior, labelling, strict=True):
                        verts[x] = labels[li]
                    for attached in _boundary_attachments(w, interior):
                        budget = max_edges - len(attached)
                        if budget < 0:
                            continue
                        for k in range(budget + 1):
                            for combo in itertools.combinations_with_replacement(types, k):
                                d = Diagram.build(verts, [*attached, *combo], inputs, outputs)
                                d = d.relabel_canonical()
                                key = d.canonical_json()
                                if key in seen:
                                    continue
                                seen.add(key)
                                out.append(d)
                                if len(out) > max_diagrams:
                                    raise CompletenessError(
                                        f"the class has more than max_diagrams = {max_diagrams}"
                                        " diagrams"
                                    )
    return out


# ----------------------------------------------------------------------------- normal forms


def _step(d: Diagram, rules: Mapping[str, Rule]) -> Diagram | None:
    for rule in rules.values():
        for m in find_matchings(d, rule):
            try:
                return apply(d, rule, m)
            except RewriteError:
                continue
    return None


def reduce(d: Diagram, rules: Mapping[str, Rule], max_steps: int) -> tuple[Diagram, int]:
    """(normal form, steps): the first applicable rule in `rules` order, its first
    matching, until none applies; raises `CompletenessError` past `max_steps`."""
    current = d
    steps = 0
    while True:
        nxt = _step(current, rules)
        if nxt is None:
            return current.relabel_canonical(), steps
        steps += 1
        if steps > max_steps:
            raise CompletenessError(
                f"reducing a diagram does not terminate within max_steps = {max_steps}"
            )
        current = nxt


def normal_form(d: Diagram, rules: Mapping[str, Rule], max_steps: int) -> Diagram:
    return reduce(d, rules, max_steps)[0]


# ----------------------------------------------------------------------------- semantic classes


def semantic_key(m: np.ndarray, tol: float = semantics.TOLERANCE) -> tuple:
    """A hashable key equal for matrices equal up to a non-zero scalar (and for all
    negligible ones): the matrix scaled so that its first entry of maximal magnitude
    is 1, rounded. Bucket, then confirm with `equal_up_to_scalar`."""
    flat = np.asarray(m, dtype=complex).ravel()
    if flat.size == 0:
        return ("empty",)
    mags = np.abs(flat)
    top = float(mags.max())
    if top <= tol:
        return ("zero",)
    pivot = int(np.argmax(mags >= top * (1 - PIVOT_SLACK)))
    scaled = flat / flat[pivot]
    return ("nonzero",) + tuple(
        (round(float(z.real), KEY_DECIMALS) + 0.0, round(float(z.imag), KEY_DECIMALS) + 0.0)
        for z in scaled
    )


# ----------------------------------------------------------------------------- the check


def check(rules: Mapping[str, Rule], *, phases: tuple[Fraction, ...] = PHASES_CLIFFORD,
          max_wires: int = DEFAULT_MAX_WIRES, max_vertices: int = DEFAULT_MAX_VERTICES,
          max_edges: int = DEFAULT_MAX_EDGES, max_steps: int = DEFAULT_MAX_STEPS,
          max_diagrams: int = DEFAULT_MAX_DIAGRAMS) -> CompletenessReport:
    """Enumerate the class, group it by semantic class, reduce its diagrams in order and
    stop at the first class with two normal forms. `classes` counts every class of the
    judged diagrams; `reduced`, `normal_forms` and `steps_max` cover the diagrams
    reduced before the verdict (all of them on a pass)."""
    t0 = time.perf_counter()
    rep = CompletenessReport()
    diagrams = enumerate_diagrams(phases, max_wires, max_vertices, max_edges, max_diagrams)
    rep.diagrams = len(diagrams)
    keys: list[tuple | None] = []
    representative: dict[tuple, np.ndarray] = {}
    for d in diagrams:
        try:
            m = semantics.matrix(d)
        except semantics.SemanticsError:
            rep.skipped += 1
            keys.append(None)
            continue
        key: tuple = (len(d.inputs), len(d.outputs), *semantic_key(m))
        while key in representative and not semantics.equal_up_to_scalar(
                representative[key], m, semantics.TOLERANCE):
            key = (*key, "#")            # a rounding collision: a fresh bucket
        representative.setdefault(key, m)
        keys.append(key)
    rep.classes = len(representative)
    first_by_class: dict[tuple, dict[str, tuple[Diagram, Diagram]]] = {}
    normal_forms: set[str] = set()
    for d, key in zip(diagrams, keys, strict=True):
        if key is None:
            continue
        nf, steps = reduce(d, rules, max_steps)
        rep.reduced += 1
        rep.steps_max = max(rep.steps_max, steps)
        nf_key = nf.canonical_json()
        normal_forms.add(nf_key)
        rep.normal_forms = len(normal_forms)
        seen = first_by_class.setdefault(key, {})
        if nf_key not in seen:
            seen[nf_key] = (d, nf)
            if len(seen) == 2:
                (a, nfa), (b, nfb) = seen.values()
                rep.failure = Witness(a, b, nfa, nfb)
                break
    rep.seconds = time.perf_counter() - t0
    return rep


__all__ = [
    "DEFAULT_MAX_DIAGRAMS", "DEFAULT_MAX_EDGES", "DEFAULT_MAX_STEPS", "DEFAULT_MAX_VERTICES",
    "DEFAULT_MAX_WIRES", "KEY_DECIMALS", "CompletenessError", "CompletenessReport", "Witness",
    "check", "enumerate_diagrams", "normal_form", "reduce", "semantic_key",
]

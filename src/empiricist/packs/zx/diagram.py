"""ZX diagrams as open multigraphs (M24c Task 1).

A `Diagram` is a finite multigraph whose vertices are Z spiders, X spiders or boundary
vertices (`B`), whose edges are plain or Hadamard, and whose boundary vertices are
ordered as inputs then outputs. Phases are in units of pi: a ground phase is a
`Fraction` reduced modulo 2 (the Clifford+T fragment has denominators dividing 4); a
rule pattern may carry a `PhaseExpr`, a linear expression `c + sum k_i * v_i` over
named variables, in the same place.

"Only topology matters": a diagram is an undirected graph, so wire bending, swaps, cups
and caps have no representation of their own, and a Hadamard box on a wire is a
Hadamard edge. Self-loops and parallel edges are allowed (spider fusion produces them);
the semantics module gives them their standard meaning.

The canonical form (`relabel_canonical`) fixes the boundary vertices by position and
orders the interior by colour refinement followed by individualisation, so two
diagrams are isomorphic (as open graphs with the same boundary order, kinds, phases
and edge types) iff their canonical forms are equal. This module is pure Python with
no dependencies beyond the standard library and is part of every verifier's trust
boundary.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from fractions import Fraction
from functools import cached_property
from typing import Any

KINDS: tuple[str, ...] = ("Z", "X", "B")
SPIDER_KINDS: tuple[str, ...] = ("Z", "X")
Edge = tuple[int, int, bool]

CANONICAL_SEARCH_BUDGET = 20_000


class CanonicalFormError(Exception):
    """The canonical-labelling search exceeded its budget."""


# ----------------------------------------------------------------------------- phases

_TERMS = re.compile(r"([+-]?)([^+-]+)")
_TERM = re.compile(r"^(?P<num>\d+(?:/\d+)?)?\*?(?P<var>[A-Za-z_][A-Za-z0-9_]*)?$")


@dataclass(frozen=True)
class PhaseExpr:
    """A linear phase expression `const + sum coeff * var`, const in [0, 2) in units of
    pi and integer coefficients; used by rule patterns. A constant expression is never
    represented here: `PhaseExpr.parse` and `substitute` return a plain `Fraction`."""

    const: Fraction
    terms: tuple[tuple[str, int], ...]

    @staticmethod
    def make(const: Fraction | int, terms: Mapping[str, int]) -> PhaseExpr | Fraction:
        clean = tuple(sorted((v, int(k)) for v, k in terms.items() if int(k) != 0))
        c = Fraction(const) % 2
        if not clean:
            return c
        return PhaseExpr(c, clean)

    @staticmethod
    def parse(text: str) -> PhaseExpr | Fraction:
        s = str(text).replace(" ", "")
        if not s:
            raise ValueError("empty phase")
        const = Fraction(0)
        coeffs: dict[str, int] = {}
        pos = 0
        for m in _TERMS.finditer(s):
            if m.start() != pos:
                raise ValueError(f"cannot parse phase {text!r}")
            pos = m.end()
            sign = -1 if m.group(1) == "-" else 1
            term = m.group(2)
            tm = _TERM.match(term)
            if tm is None or (tm.group("num") is None and tm.group("var") is None):
                raise ValueError(f"cannot parse phase term {term!r} in {text!r}")
            num, var = tm.group("num"), tm.group("var")
            if var is None:
                const += sign * Fraction(num)
            else:
                if num is not None and "/" in num:
                    raise ValueError(f"fractional coefficient in phase term {term!r}")
                coeffs[var] = coeffs.get(var, 0) + sign * (int(num) if num else 1)
        if pos != len(s):
            raise ValueError(f"cannot parse phase {text!r}")
        return PhaseExpr.make(const, coeffs)

    def variables(self) -> frozenset[str]:
        return frozenset(v for v, _ in self.terms)

    def substitute(self, bindings: Mapping[str, Fraction | int]) -> PhaseExpr | Fraction:
        const = self.const
        rest: dict[str, int] = {}
        for v, k in self.terms:
            if v in bindings:
                const += k * Fraction(bindings[v])
            else:
                rest[v] = k
        return PhaseExpr.make(const, rest)

    def __str__(self) -> str:
        parts: list[str] = []
        if self.const != 0:
            parts.append(str(self.const))
        for v, k in self.terms:
            mag = "" if abs(k) == 1 else str(abs(k))
            parts.append(("-" if k < 0 else "+") + mag + v)
        out = "".join(parts)
        return out[1:] if out.startswith("+") else out


Phase = Fraction | PhaseExpr


def as_phase(value: Any) -> Phase:
    """Coerce an int, Fraction, string or PhaseExpr to a phase (Fraction mod 2)."""
    if isinstance(value, bool):
        raise ValueError(f"bad phase {value!r}")
    if isinstance(value, PhaseExpr):
        return PhaseExpr.make(value.const, dict(value.terms))
    if isinstance(value, (int, Fraction)):
        return Fraction(value) % 2
    if isinstance(value, str):
        return PhaseExpr.parse(value)
    raise ValueError(f"bad phase {value!r}")


def phase_str(p: Phase) -> str:
    return str(p)


# ----------------------------------------------------------------------------- diagrams


def _check_id(v: Any) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise ValueError(f"vertex id must be a non-negative int, got {v!r}")
    return v


@dataclass(frozen=True)
class Diagram:
    vertices: tuple[tuple[int, str, Phase], ...]
    edges: tuple[Edge, ...]
    inputs: tuple[int, ...] = ()
    outputs: tuple[int, ...] = ()

    # -- construction -------------------------------------------------------------------

    def __post_init__(self) -> None:
        verts: list[tuple[int, str, Phase]] = []
        seen: set[int] = set()
        for item in self.vertices:
            v, kind, phase = item
            v = _check_id(v)
            if v in seen:
                raise ValueError(f"duplicate vertex id {v}")
            seen.add(v)
            if kind not in KINDS:
                raise ValueError(f"vertex {v}: kind must be one of {KINDS}, got {kind!r}")
            verts.append((v, kind, as_phase(phase)))
        verts.sort(key=lambda t: t[0])
        edges: list[Edge] = []
        for item in self.edges:
            u, w, h = item
            u, w = _check_id(u), _check_id(w)
            if u not in seen or w not in seen:
                raise ValueError(f"edge ({u}, {w}) references a missing vertex")
            edges.append((min(u, w), max(u, w), bool(h)))
        edges.sort()
        ins = tuple(_check_id(v) for v in self.inputs)
        outs = tuple(_check_id(v) for v in self.outputs)
        for v in ins + outs:
            if v not in seen:
                raise ValueError(f"boundary list references a missing vertex {v}")
        object.__setattr__(self, "vertices", tuple(verts))
        object.__setattr__(self, "edges", tuple(edges))
        object.__setattr__(self, "inputs", ins)
        object.__setattr__(self, "outputs", outs)

    @classmethod
    def build(
        cls,
        vertices: Mapping[int, tuple[str, Any]],
        edges: Iterable[tuple[int, int, bool]],
        inputs: Iterable[int] = (),
        outputs: Iterable[int] = (),
    ) -> Diagram:
        return cls(
            tuple((v, kind, phase) for v, (kind, phase) in vertices.items()),
            tuple(edges), tuple(inputs), tuple(outputs),
        )

    # -- lookups ------------------------------------------------------------------------

    @cached_property
    def _index(self) -> dict[int, tuple[str, Phase]]:
        return {v: (k, p) for v, k, p in self.vertices}

    @cached_property
    def _incident(self) -> dict[int, tuple[int, ...]]:
        inc: dict[int, list[int]] = {v: [] for v in self._index}
        for i, (u, w, _) in enumerate(self.edges):
            inc[u].append(i)
            inc[w].append(i)          # a self-loop is listed twice: it has two ends
        return {v: tuple(e) for v, e in inc.items()}

    @property
    def vertex_ids(self) -> tuple[int, ...]:
        return tuple(v for v, _, _ in self.vertices)

    @property
    def interior(self) -> tuple[int, ...]:
        return tuple(v for v, k, _ in self.vertices if k in SPIDER_KINDS)

    @property
    def boundary(self) -> tuple[int, ...]:
        return tuple(v for v, k, _ in self.vertices if k == "B")

    @property
    def max_id(self) -> int:
        return max((v for v, _, _ in self.vertices), default=-1)

    def has_vertex(self, v: int) -> bool:
        return v in self._index

    def kind(self, v: int) -> str:
        return self._index[v][0]

    def phase(self, v: int) -> Phase:
        return self._index[v][1]

    def vertex_data(self, v: int) -> tuple[str, Phase]:
        return self._index[v]

    def incident(self, v: int) -> tuple[int, ...]:
        """Indices into `edges` of the edges at `v`; a self-loop appears twice."""
        return self._incident[v]

    def degree(self, v: int) -> int:
        return len(self._incident[v])

    def other_end(self, edge_index: int, v: int) -> int:
        u, w, _ = self.edges[edge_index]
        return w if u == v else u

    def neighbours(self, v: int) -> tuple[int, ...]:
        return tuple(self.other_end(e, v) for e in self._incident[v])

    def edges_between(self, u: int, w: int) -> tuple[int, ...]:
        a, b = min(u, w), max(u, w)
        return tuple(i for i in self._incident[u] if self.edges[i][:2] == (a, b))

    def is_ground(self) -> bool:
        return all(isinstance(p, Fraction) for _, _, p in self.vertices)

    def variables(self) -> frozenset[str]:
        out: set[str] = set()
        for _, _, p in self.vertices:
            if isinstance(p, PhaseExpr):
                out |= p.variables()
        return frozenset(out)

    # -- derived diagrams ---------------------------------------------------------------

    def substitute(self, bindings: Mapping[str, Fraction | int]) -> Diagram:
        verts = tuple(
            (v, k, p.substitute(bindings) if isinstance(p, PhaseExpr) else p)
            for v, k, p in self.vertices
        )
        return Diagram(verts, self.edges, self.inputs, self.outputs)

    def with_phase(self, v: int, phase: Any) -> Diagram:
        verts = tuple((w, k, as_phase(phase) if w == v else p) for w, k, p in self.vertices)
        return Diagram(verts, self.edges, self.inputs, self.outputs)

    def relabel(self, mapping: Mapping[int, int]) -> Diagram:
        m = dict(mapping)
        for v in self.vertex_ids:
            m.setdefault(v, v)
        if len(set(m[v] for v in self.vertex_ids)) != len(self.vertices):
            raise ValueError("relabelling is not injective")
        return Diagram(
            tuple((m[v], k, p) for v, k, p in self.vertices),
            tuple((m[u], m[w], h) for u, w, h in self.edges),
            tuple(m[v] for v in self.inputs), tuple(m[v] for v in self.outputs),
        )

    # -- well-formedness ----------------------------------------------------------------

    def well_formedness_problems(self) -> list[str]:
        problems: list[str] = []
        listed: dict[int, int] = {}
        for role, ids in (("input", self.inputs), ("output", self.outputs)):
            for v in ids:
                if self.kind(v) != "B":
                    problems.append(f"{role} {v} is not a boundary vertex")
                listed[v] = listed.get(v, 0) + 1
        for v, n in listed.items():
            if n > 1:
                problems.append(f"boundary vertex {v} is listed {n} times")
        for v, k, p in self.vertices:
            if k == "B":
                if self.degree(v) != 1:
                    problems.append(f"boundary vertex {v} has degree {self.degree(v)}, expected 1")
                if v not in listed:
                    problems.append(f"boundary vertex {v} is neither an input nor an output")
                if p != 0:
                    problems.append(f"boundary vertex {v} carries a phase {p}")
            else:
                if isinstance(p, PhaseExpr):
                    problems.append(f"vertex {v} has a non-ground phase {p}")
                elif p.denominator not in (1, 2, 4):
                    problems.append(f"vertex {v} phase {p} is outside the pi/4 fragment")
        return problems

    def is_well_formed(self) -> bool:
        return not self.well_formedness_problems()

    # -- JSON ---------------------------------------------------------------------------

    def to_json(self) -> dict[str, Any]:
        return {
            "vertices": [[v, k, phase_str(p)] for v, k, p in self.vertices],
            "edges": [[u, w, h] for u, w, h in self.edges],
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
        }

    def canonical_json(self) -> str:
        return json.dumps(self.to_json(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, obj: Any) -> Diagram:
        if not isinstance(obj, dict):
            raise ValueError("a diagram is a JSON object")
        try:
            verts = obj["vertices"]
            edges = obj["edges"]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"diagram is missing {exc}") from None
        if not isinstance(verts, list) or not isinstance(edges, list):
            raise ValueError("diagram vertices and edges must be lists")
        vs: list[tuple[int, str, Phase]] = []
        for item in verts:
            if not isinstance(item, list) or len(item) != 3:
                raise ValueError(f"bad vertex entry {item!r}")
            vs.append((item[0], item[1], item[2]))
        es: list[Edge] = []
        for item in edges:
            if not isinstance(item, list) or len(item) != 3 or not isinstance(item[2], bool):
                raise ValueError(f"bad edge entry {item!r}")
            es.append((item[0], item[1], item[2]))
        ins = obj.get("inputs", [])
        outs = obj.get("outputs", [])
        if not isinstance(ins, list) or not isinstance(outs, list):
            raise ValueError("diagram inputs and outputs must be lists")
        return cls(tuple(vs), tuple(es), tuple(ins), tuple(outs))

    # -- canonical form -----------------------------------------------------------------

    def _initial_colours(self) -> dict[int, tuple]:
        position = {v: i for i, v in enumerate(self.inputs + self.outputs)}
        colours: dict[int, tuple] = {}
        for v, k, p in self.vertices:
            if k == "B":
                colours[v] = (0, position.get(v, len(position)), phase_str(p), self.degree(v))
            else:
                colours[v] = (1, k, phase_str(p), self.degree(v))
        return colours

    def _rank(self, keys: dict[int, Any]) -> dict[int, int]:
        distinct = sorted(set(keys.values()))
        rank = {k: i for i, k in enumerate(distinct)}
        return {v: rank[keys[v]] for v in keys}

    def _refine(self, colour: dict[int, int]) -> dict[int, int]:
        while True:
            keys = {
                v: (colour[v], tuple(sorted(
                    (self.edges[e][2], colour[self.other_end(e, v)]) for e in self.incident(v)
                )))
                for v in colour
            }
            new = self._rank(keys)
            if len(set(new.values())) == len(set(colour.values())):
                return new
            colour = new

    def relabel_canonical(self) -> Diagram:
        """A deterministic relabelling with boundary vertices first (inputs then outputs,
        in order) such that isomorphic diagrams relabel to equal diagrams."""
        if not self.vertices:
            return self
        colour = self._refine(self._rank(self._initial_colours()))
        best: tuple[str, Diagram] | None = None
        budget = [CANONICAL_SEARCH_BUDGET]

        def leaf(col: dict[int, int]) -> None:
            nonlocal best
            budget[0] -= 1
            if budget[0] < 0:
                raise CanonicalFormError("canonical labelling search budget exceeded")
            order = sorted(col, key=lambda v: col[v])
            cand = self.relabel({v: i for i, v in enumerate(order)})
            key = cand.canonical_json()
            if best is None or key < best[0]:
                best = (key, cand)

        def search(col: dict[int, int]) -> None:
            cells: dict[int, list[int]] = {}
            for v, c in col.items():
                cells.setdefault(c, []).append(v)
            target = min((c for c, vs in cells.items() if len(vs) > 1), default=None)
            if target is None:
                leaf(col)
                return
            for v in sorted(cells[target]):
                split = {u: 2 * col[u] + (0 if u == v else 1) for u in col}
                search(self._refine(self._rank(split)))

        search(colour)
        assert best is not None
        return best[1]


def isomorphic(a: Diagram, b: Diagram) -> bool:
    """Equal as open graphs: same boundary order, kinds, phases, edges and edge types."""
    if len(a.vertices) != len(b.vertices) or len(a.edges) != len(b.edges):
        return False
    if len(a.inputs) != len(b.inputs) or len(a.outputs) != len(b.outputs):
        return False
    return a.relabel_canonical() == b.relabel_canonical()


__all__ = [
    "CANONICAL_SEARCH_BUDGET", "KINDS", "SPIDER_KINDS", "CanonicalFormError", "Diagram",
    "Edge", "Phase", "PhaseExpr", "as_phase", "isomorphic", "phase_str",
]

"""Matching and rewriting (M24c Task 2).

A `Matching` sends every LHS vertex of a rule to a host vertex. It is valid when

* interior LHS vertices go injectively to host spiders of the same kind;
* interface (`B`) LHS vertices go to host vertices outside the image of the interior
  vertices (the identification condition: a rule never rewires a vertex it deletes);
  several interface vertices may share a host vertex, which may itself be a boundary
  vertex or a spider;
* every LHS edge (p, q, h) is matched to a distinct host edge (m(p), m(q), h): the edge
  map is determined up to the choice among identical parallel edges, which does not
  change the result;
* a non-star interior vertex has no host legs beyond the matched ones; a star vertex's
  further legs are its residual legs, each sent to one of the rule's targets (the first
  by default, or as the matching's `split` says);
* the LHS phase expressions, with variables taken from the matching's `phases` and
  otherwise solved from host phases (a variable with coefficient +-1), equal the host
  phases syntactically -- a host with symbolic phases (critical pairs) matches only
  what holds for every instantiation.

`apply` deletes the interior image and the matched edges, adds the RHS interior with
fresh ids and its edges (interface vertices resolve through the matching), and
re-attaches the residual legs with the target's flip applied per end (an edge between
two flipped ends, or a self-loop on a flipped vertex, keeps its type). Host boundary
ids never change, so rewriting commutes with the canonical form's boundary order.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from empiricist.packs.zx.diagram import Diagram, Phase, PhaseExpr, as_phase
from empiricist.packs.zx.rules import Rule

DEFAULT_SPLIT = 0


class RewriteError(Exception):
    """A matching does not fit the host, or the rule cannot be applied through it."""


@dataclass(frozen=True)
class Matching:
    vertices: Mapping[int, int]
    phases: Mapping[str, Any] = field(default_factory=dict)
    split: Mapping[tuple[int, int], int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            verts = {int(k): int(v) for k, v in dict(self.vertices).items()}
            phases = {str(k): as_phase(v) for k, v in dict(self.phases).items()}
            split = {(int(e), int(s)): int(t) for (e, s), t in dict(self.split).items()}
        except (TypeError, ValueError) as exc:
            raise ValueError(f"bad matching: {exc}") from None
        object.__setattr__(self, "vertices", verts)
        object.__setattr__(self, "phases", phases)
        object.__setattr__(self, "split", split)

    def to_json(self) -> dict[str, Any]:
        return {
            "vertices": {str(k): v for k, v in sorted(self.vertices.items())},
            "phases": {k: str(v) for k, v in sorted(self.phases.items())},
            "split": [[e, s, t] for (e, s), t in sorted(self.split.items())],
        }

    @classmethod
    def from_json(cls, obj: Any) -> Matching:
        if not isinstance(obj, dict) or not isinstance(obj.get("vertices"), dict):
            raise ValueError("a matching is an object with a `vertices` map")
        try:
            verts = {int(k): v for k, v in obj["vertices"].items()}
        except ValueError as exc:
            raise ValueError(f"bad matching vertex key: {exc}") from None
        phases = obj.get("phases", {})
        split_obj = obj.get("split", [])
        if not isinstance(phases, dict) or not isinstance(split_obj, list):
            raise ValueError("matching phases must be an object and split a list")
        split: dict[tuple[int, int], int] = {}
        for item in split_obj:
            if not isinstance(item, list) or len(item) != 3:
                raise ValueError(f"bad split entry {item!r}")
            split[(item[0], item[1])] = item[2]
        return cls(verts, phases, split)


@dataclass(frozen=True)
class MatchInfo:
    vertex_map: dict[int, int]
    edge_map: dict[int, int]                       # LHS edge index -> host edge index
    bindings: dict[str, Phase]
    residual: dict[int, tuple[int, ...]]           # star -> host edge indices
    targets: dict[tuple[int, int], tuple[int, bool]]   # (host edge, star) -> (rhs target, flip)


def _solve_bindings(host: Diagram, rule: Rule, m: Mapping[int, int],
                    explicit: Mapping[str, Phase]) -> dict[str, Phase]:
    bindings: dict[str, Phase] = dict(explicit)
    lhs = rule.lhs
    exprs = [(u, lhs.phase(u)) for u in lhs.interior if isinstance(lhs.phase(u), PhaseExpr)]
    progress = True
    while progress:
        progress = False
        for u, expr in exprs:
            assert isinstance(expr, PhaseExpr)
            rest = expr.substitute(bindings)
            if isinstance(rest, Fraction):
                continue
            # a name already bound is a host variable of the same name, not a rule variable
            free = [(v, k) for v, k in rest.terms if v not in bindings]
            if len(free) == 1 and abs(free[0][1]) == 1:
                v, k = free[0]
                # host = rest.const + k * v  =>  v = k * (host - rest.const)
                value = k * (host.phase(m[u]) - rest.const)
                if isinstance(value, Fraction):
                    value = value % 2
                bindings[v] = value
                progress = True
    for u, expr in exprs:
        assert isinstance(expr, PhaseExpr)
        rest = expr.substitute(bindings)
        if isinstance(rest, PhaseExpr):
            free = sorted(rest.variables() - host.variables())
            if free:
                raise RewriteError(
                    f"unbound phase variable(s) {', '.join(free)} at LHS vertex {u}: "
                    "give them in matching.phases"
                )
    return bindings


def check_matching(host: Diagram, rule: Rule, matching: Matching) -> MatchInfo:
    """Validate `matching` for `rule` on `host`; raise `RewriteError` naming the first
    violated condition."""
    lhs = rule.lhs
    m = dict(matching.vertices)
    missing = [u for u in lhs.vertex_ids if u not in m]
    if missing:
        raise RewriteError(f"matching is missing LHS vertices {missing}")
    extra = [u for u in m if not lhs.has_vertex(u)]
    if extra:
        raise RewriteError(f"matching names vertices {extra} that are not in the LHS")
    for u, v in m.items():
        if not host.has_vertex(v):
            raise RewriteError(f"no host vertex {v} (image of LHS vertex {u})")
    interior = lhs.interior
    images = [m[u] for u in interior]
    if len(set(images)) != len(images):
        raise RewriteError("matching is not injective on interior vertices")
    image_set = set(images)
    for u in interior:
        if host.kind(m[u]) != lhs.kind(u):
            raise RewriteError(f"kind mismatch: LHS vertex {u} is {lhs.kind(u)}, host vertex "
                               f"{m[u]} is {host.kind(m[u])}")
    for b in lhs.boundary:
        if m[b] in image_set:
            raise RewriteError(f"identification condition: interface vertex {b} lands on the "
                               f"matched interior vertex {m[b]}")
    # phases
    bindings = _solve_bindings(host, rule, m, matching.phases)
    for u in interior:
        expected = lhs.phase(u)
        if isinstance(expected, PhaseExpr):
            expected = expected.substitute(bindings)
        if expected != host.phase(m[u]):
            raise RewriteError(f"phase mismatch at LHS vertex {u}: pattern {expected}, host "
                               f"{host.phase(m[u])}")
    # edges: count per signature, greedy assignment among identical host edges
    used: set[int] = set()
    edge_map: dict[int, int] = {}
    for i, (p, q, h) in enumerate(lhs.edges):
        a, b = sorted((m[p], m[q]))
        cands = [e for e in host.edges_between(a, b)
                 if host.edges[e][2] == h and e not in used]
        if not cands:
            raise RewriteError(f"LHS edge ({p}, {q}, {'H' if h else 'plain'}) has no unmatched "
                               f"host edge between {a} and {b}")
        used.add(cands[0])
        edge_map[i] = cands[0]
    # residual legs
    residual: dict[int, tuple[int, ...]] = {}
    targets: dict[tuple[int, int], tuple[int, bool]] = {}
    stars = rule.stars
    for u in interior:
        legs = sorted(set(host.incident(m[u])) - used)
        if legs and u not in stars:
            raise RewriteError(f"LHS vertex {u} is not a star but host vertex {m[u]} has "
                               f"extra legs {legs}")
        if u in stars:
            residual[u] = tuple(legs)
            opts = rule.targets(u)
            for e in legs:
                chosen = matching.split.get((e, u))
                if chosen is None:
                    targets[(e, u)] = opts[DEFAULT_SPLIT]
                else:
                    hit = [t for t in opts if t[0] == chosen]
                    if not hit:
                        raise RewriteError(f"split sends host edge {e} at star {u} to {chosen}, "
                                           f"not one of its targets {[t for t, _ in opts]}")
                    targets[(e, u)] = hit[0]
    for (e, s) in matching.split:
        if s not in stars or e not in residual.get(s, ()):
            raise RewriteError(f"split entry for host edge {e} at LHS vertex {s} does not name "
                               "a residual leg of a star")
    return MatchInfo(m, edge_map, bindings, residual, targets)


def apply(host: Diagram, rule: Rule, matching: Matching) -> Diagram:
    """Rewrite `host` through `matching`; raise `RewriteError` if it does not fit."""
    info = check_matching(host, rule, matching)
    m, rhs = info.vertex_map, rule.rhs
    removed_vertices = {m[u] for u in rule.lhs.interior}
    removed_edges = set(info.edge_map.values())
    for e, (a, b, _) in enumerate(host.edges):
        if a in removed_vertices or b in removed_vertices:
            removed_edges.add(e)
    fresh: dict[int, int] = {}
    nxt = host.max_id + 1
    for r in rhs.interior:
        fresh[r] = nxt
        nxt += 1
    for b in rhs.boundary:
        fresh[b] = m[b]
    unbound = rhs.variables() - set(info.bindings) - host.variables()
    if unbound:
        raise RewriteError(f"unbound phase variable(s) {', '.join(sorted(unbound))} on the RHS: "
                           "give them in matching.phases")
    verts: dict[int, tuple[str, Phase]] = {
        v: host.vertex_data(v) for v in host.vertex_ids if v not in removed_vertices
    }
    for r in rhs.interior:
        kind, phase = rhs.vertex_data(r)
        if isinstance(phase, PhaseExpr):
            phase = phase.substitute(info.bindings)
        verts[fresh[r]] = (kind, phase)
    edges: list[tuple[int, int, bool]] = [
        e for i, e in enumerate(host.edges) if i not in removed_edges
    ]
    edges += [(fresh[p], fresh[q], h) for p, q, h in rhs.edges]
    star_of = {m[s]: s for s in rule.stars}
    seen: set[int] = set()
    for legs in info.residual.values():
        for e in legs:
            if e in seen:
                continue
            seen.add(e)
            a, b, h = host.edges[e]
            ends = []
            for z in (a, b):
                if z in star_of:
                    target, flip = info.targets[(e, star_of[z])]
                    ends.append((fresh[target], flip))
                else:
                    ends.append((z, False))
            (x, fx), (y, fy) = ends
            edges.append((x, y, h ^ fx ^ fy))
    return Diagram.build(verts, edges, inputs=host.inputs, outputs=host.outputs)


def find_matchings(host: Diagram, rule: Rule) -> list[Matching]:
    """Every valid matching of `rule` in `host`, with default leg splits and phases solved
    from the host (rules whose LHS phases cannot be solved that way yield none)."""
    lhs = rule.lhs
    interior = sorted(lhs.interior, key=lambda v: (-lhs.degree(v), v))
    order = interior + list(lhs.boundary)
    interior_set = set(interior)
    stars = rule.stars
    assignment: dict[int, int] = {}
    results: list[Matching] = []

    def lhs_neighbours(u: int) -> list[tuple[int, bool]]:
        return [(lhs.other_end(e, u), lhs.edges[e][2]) for e in lhs.incident(u)]

    def candidates(u: int) -> Iterator[int]:
        images = {assignment[w] for w in assignment if w in interior_set}
        if u in interior_set:
            for v in host.interior:
                if v in images or host.kind(v) != lhs.kind(u):
                    continue
                if (host.degree(v) < lhs.degree(u)) if u in stars else (
                    host.degree(v) != lhs.degree(u)
                ):
                    continue
                lp = lhs.phase(u)
                if isinstance(lp, Fraction) and host.phase(v) != lp:
                    continue
                ok = True
                for w, h in lhs_neighbours(u):
                    if w in assignment and not any(
                        host.edges[e][2] == h for e in host.edges_between(v, assignment[w])
                    ):
                        ok = False
                        break
                if ok:
                    yield v
        else:
            (w, h), = lhs_neighbours(u)
            if w in assignment:
                base = assignment[w]
                pool = {host.other_end(e, base) for e in host.incident(base)
                        if host.edges[e][2] == h}
            else:
                pool = set(host.vertex_ids)
            for v in sorted(pool):
                if v not in images:
                    yield v

    def rec(i: int) -> None:
        if i == len(order):
            m = Matching(vertices=dict(assignment))
            try:
                check_matching(host, rule, m)
            except RewriteError:
                return
            results.append(m)
            return
        u = order[i]
        for v in list(candidates(u)):
            assignment[u] = v
            rec(i + 1)
            del assignment[u]

    rec(0)
    return results


def successors(host: Diagram, rules: Mapping[str, Rule]) -> Iterator[tuple[str, Matching, Diagram]]:
    """Every one-step rewrite of `host` by any of `rules` (forward direction)."""
    for name, rule in rules.items():
        for m in find_matchings(host, rule):
            yield name, m, apply(host, rule, m)


__all__ = [
    "DEFAULT_SPLIT", "MatchInfo", "Matching", "RewriteError", "apply", "check_matching",
    "find_matchings", "successors",
]

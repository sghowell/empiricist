"""Critical pairs and joinability (M24c Task 3).

An overlap of two rules is a minimal diagram G that both LHSs match while sharing an
item both rewrites delete (a spider, or a matched edge); the critical pair is the two
results. `overlaps(r1, r2)` builds every gluing of L2 onto L1: each L2 vertex is
identified with an L1 vertex (same kind; an L2 spider may also take the place of an L1
context vertex, which then becomes that spider) or is fresh, each L2 edge is an L1
edge or fresh, and phases are unified symbolically (a variable with unit coefficient
is solved; anything else is grounded over the fragment's phases). Star vertices of
either rule may carry up to `star_legs` further context legs of each type -- an
honest but finite stand-in for "any number of legs", recorded in the report.

`joinable(a, b, rules, depth)` searches both sides breadth-first, forward direction
only, up to `depth` steps each, comparing canonical forms; a symbolic failure is
retried on every ground instance of the pair's variables (a case split), so a pair is
non-joinable only with a concrete witness. Budgets raise `CriticalPairError`.

Soundness note. A PASS from `check` says: every enumerated critical pair is joinable
within the depth. The enumeration is complete for rules without star vertices; for
star rules it covers the residual-leg configurations up to `star_legs` per star, and
the critical-pair lemma for such rules (joinability transferring to every number of
residual legs) is not established here -- see the plan's outcome section.
"""
from __future__ import annotations

import itertools
import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from fractions import Fraction

from empiricist.packs.zx.diagram import Diagram, Phase, PhaseExpr
from empiricist.packs.zx.rewrite import Matching, RewriteError, apply, check_matching, successors
from empiricist.packs.zx.rules import PHASES_CLIFFORD, PHASES_CLIFFORD_T, Rule

DEFAULT_MAX_NODES = 4000
DEFAULT_MAX_INSTANCES = 4096


class CriticalPairError(Exception):
    """A search budget was exhausted: the question is undecided, not answered."""


@dataclass(frozen=True)
class Overlap:
    rule1: str
    rule2: str
    host: Diagram
    m1: Matching
    m2: Matching
    result1: Diagram
    result2: Diagram

    @property
    def key(self) -> tuple[str, str, str]:
        r = sorted((self.result1.relabel_canonical().canonical_json(),
                    self.result2.relabel_canonical().canonical_json()))
        return (self.host.relabel_canonical().canonical_json(), r[0], r[1])

    def to_json(self) -> dict:
        return {"rule1": self.rule1, "rule2": self.rule2, "host": self.host.to_json(),
                "matching1": self.m1.to_json(), "matching2": self.m2.to_json(),
                "result1": self.result1.to_json(), "result2": self.result2.to_json()}


@dataclass(frozen=True)
class JoinReport:
    joinable: bool
    depth: int | None = None
    instances: int = 0
    reason: str = ""


@dataclass
class CheckReport:
    depth: int
    star_legs: int
    pairs: int = 0
    overlaps: int = 0
    joined: int = 0
    case_splits: int = 0
    failure: tuple[Overlap, JoinReport] | None = None
    failures: list[tuple[Overlap, JoinReport]] = field(default_factory=list)
    seconds: float = 0.0
    per_pair: dict[tuple[str, str], int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.failure is None


# ----------------------------------------------------------------------------- variables


def rename_apart(rule: Rule, suffix: str) -> Rule:
    subst = {v: PhaseExpr.make(0, {v + suffix: 1}) for v in rule.variables()}
    return Rule(rule.name, rule.lhs.substitute(subst), rule.rhs.substitute(subst),
                rule.residual, rule.reference)


def forget_variable_names(d: Diagram) -> Diagram:
    """Rename a diagram's variables to a, b, c, ... in order of first appearance by
    vertex id, so hosts from different runs can be compared."""
    names: dict[str, str] = {}
    for v in d.vertex_ids:
        p = d.phase(v)
        if isinstance(p, PhaseExpr):
            for var in sorted(p.variables()):
                if var not in names:
                    names[var] = chr(ord("a") + len(names))
    return d.substitute({old: PhaseExpr.make(0, {new: 1}) for old, new in names.items()})


def _unify(constraints: list[tuple[Phase, Phase]]) -> tuple[dict[str, Phase], list[Phase]] | None:
    """Solve e1 = e2 (mod 2) pairs; return (substitution, unsolved equations) or None
    when a constraint is contradictory."""
    subst: dict[str, Phase] = {}
    eqs: list[Phase] = [(a - b) if isinstance(a, PhaseExpr) or isinstance(b, PhaseExpr)
                        else (a - b) % 2 for a, b in constraints]
    pending = list(eqs)
    leftover: list[Phase] = []
    progress = True
    while progress:
        progress = False
        nxt: list[Phase] = []
        for eq in pending:
            e = eq.substitute(subst) if isinstance(eq, PhaseExpr) else eq
            if isinstance(e, Fraction):
                if e % 2 != 0:
                    return None
                continue
            unit = [(v, k) for v, k in e.terms if abs(k) == 1]
            if unit:
                v, k = unit[0]
                # e = c + k v + rest = 0  =>  v = -k (c + rest)
                rest = PhaseExpr.make(e.const, {w: c for w, c in e.terms if w != v})
                value = (-k) * rest if isinstance(rest, PhaseExpr) else ((-k) * rest) % 2
                subst = {w: (x.substitute({v: value}) if isinstance(x, PhaseExpr) else x)
                         for w, x in subst.items()}
                subst[v] = value
                progress = True
            else:
                nxt.append(e)
        pending = nxt
    leftover = pending
    return subst, leftover


def _ground_solutions(leftover: list[Phase], phases: tuple[Fraction, ...],
                      max_instances: int) -> Iterator[dict[str, Phase]]:
    variables: list[str] = sorted({v for e in leftover if isinstance(e, PhaseExpr)
                                   for v in e.variables()})
    if not variables:
        yield {}
        return
    if len(phases) ** len(variables) > max_instances:
        raise CriticalPairError(
            f"grounding {len(variables)} variables over {len(phases)} phases exceeds the "
            f"budget of {max_instances} instances"
        )
    for values in itertools.product(phases, repeat=len(variables)):
        binding = dict(zip(variables, values, strict=True))
        if all((e.substitute(binding) if isinstance(e, PhaseExpr) else e) % 2 == 0
               for e in leftover):
            yield dict(binding)


# ----------------------------------------------------------------------------- overlaps


def _bfs_order(d: Diagram) -> list[int]:
    order: list[int] = []
    seen: set[int] = set()
    interior_first = list(d.interior) + list(d.boundary)
    for start in interior_first:
        if start in seen:
            continue
        queue = [start]
        seen.add(start)
        while queue:
            v = queue.pop(0)
            order.append(v)
            for w in sorted(set(d.neighbours(v))):
                if w not in seen:
                    seen.add(w)
                    queue.append(w)
    # interior vertices before boundary ones keeps the identification condition simple
    return [v for v in order if d.kind(v) != "B"] + [v for v in order if d.kind(v) == "B"]


def _pair_overlaps(r1: Rule, r2: Rule, same_rule: bool, star_legs: int,
                   phases: tuple[Fraction, ...], max_instances: int) -> Iterator[Overlap]:
    L1, L2 = r1.lhs, r2.lhs
    stars1 = r1.stars
    l1_interior, l1_boundary = set(L1.interior), set(L1.boundary)
    l2_interior = set(L2.interior)
    order = _bfs_order(L2)
    fresh_base = L1.max_id + 1

    assign: dict[int, int] = {}        # L2 vertex -> G vertex id (existing or fresh)
    fresh_ids: dict[int, int] = {}     # L2 vertex -> its fresh id (when fresh)

    def is_fresh(u: int) -> bool:
        return u in fresh_ids

    def l2_interior_image_at(g: int) -> int | None:
        for u, gv in assign.items():
            if gv == g and u in l2_interior:
                return u
        return None

    def fresh_edge_allowed_at(g: int) -> bool:
        if g >= fresh_base:
            return True
        if g in stars1:
            return True
        if g in l1_boundary and l2_interior_image_at(g) is not None:
            return True
        return False

    def edge_feasible(u: int, gu: int, p: int, gp: int, h: bool) -> bool:
        """Can L2 edge (u, p, h) be realised with u -> gu and p -> gp?"""
        both_existing = gu < fresh_base and gp < fresh_base
        if both_existing:
            a, b = min(gu, gp), max(gu, gp)
            if any(L1.edges[e][2] == h for e in L1.edges_between(a, b)):
                return True
        return fresh_edge_allowed_at(gu) and fresh_edge_allowed_at(gp)

    def vertex_options(u: int) -> Iterator[int]:
        used_by_interior = {gv for w, gv in assign.items() if w in l2_interior}
        used_any = set(assign.values())
        opts: list[int] = []
        if u in l2_interior:
            for v in L1.interior:
                if v in used_any or L1.kind(v) != L2.kind(u):
                    continue
                p1, p2 = L1.phase(v), L2.phase(u)
                if isinstance(p1, Fraction) and isinstance(p2, Fraction) and p1 != p2:
                    continue
                opts.append(v)
            for c in L1.boundary:
                if c not in used_any:
                    opts.append(c)
        else:
            # an interface vertex lands on an L1 vertex (not a matched spider) or on its
            # own fresh context vertex; never on another fresh context (degree 2)
            for g in L1.vertex_ids:
                if g not in used_by_interior:
                    opts.append(g)
        for g in opts:
            assign[u] = g
            ok = all(edge_feasible(u, g, p, assign[p], L2.edges[e][2])
                     for e in set(L2.incident(u))
                     for p in [L2.other_end(e, u)] if p in assign and p != u)
            del assign[u]
            if ok:
                yield g
        # fresh
        fid = fresh_base + len(fresh_ids)
        fresh_ids[u] = fid
        assign[u] = fid
        ok = all(edge_feasible(u, fid, p, assign[p], L2.edges[e][2])
                 for e in set(L2.incident(u))
                 for p in [L2.other_end(e, u)] if p in assign and p != u)
        del assign[u]
        del fresh_ids[u]
        if ok:
            yield -1

    def search(i: int) -> Iterator[dict[int, int]]:
        if i == len(order):
            yield dict(assign)
            return
        u = order[i]
        for g in list(vertex_options(u)):
            if g == -1:
                fid = fresh_base + len(fresh_ids)
                fresh_ids[u] = fid
                assign[u] = fid
                yield from search(i + 1)
                del assign[u]
                del fresh_ids[u]
            else:
                assign[u] = g
                yield from search(i + 1)
                del assign[u]

    def edge_assignments(vmap: dict[int, int]) -> Iterator[list[int | None]]:
        """Per L2 edge: an L1 edge index, or None for a fresh edge."""
        def rec(i: int, used: set[int], acc: list[int | None]) -> Iterator[list[int | None]]:
            if i == len(L2.edges):
                yield list(acc)
                return
            p, q, h = L2.edges[i]
            gp, gq = vmap[p], vmap[q]
            if gp < fresh_base and gq < fresh_base:
                a, b = min(gp, gq), max(gp, gq)
                for e in L1.edges_between(a, b):
                    if L1.edges[e][2] == h and e not in used:
                        acc.append(e)
                        yield from rec(i + 1, used | {e}, acc)
                        acc.pop()
            if all(g >= fresh_base or g in stars1 or (g in l1_boundary and any(
                    vmap[w] == g for w in l2_interior)) for g in (gp, gq)):
                acc.append(None)
                yield from rec(i + 1, used, acc)
                acc.pop()
        yield from rec(0, set(), [])

    seen_keys: set[tuple[str, str, str]] = set()

    for vmap in search(0):
        # criticality needs a shared spider or a shared edge; check the spider part now
        shared_vertex = any(vmap[u] in l1_interior for u in l2_interior)
        for emap in edge_assignments(vmap):
            shared_edge = any(e is not None for e in emap)
            if not (shared_vertex or shared_edge):
                continue
            if same_rule and all(vmap.get(u) == u for u in L2.vertex_ids) and all(
                    e == i for i, e in enumerate(emap)):
                continue      # the same rewrite step twice
            # build G
            verts: dict[int, tuple[str, Phase]] = {v: L1.vertex_data(v) for v in L1.vertex_ids}
            constraints: list[tuple[Phase, Phase]] = []
            for u in L2.vertex_ids:
                g = vmap[u]
                if g >= fresh_base:
                    verts[g] = L2.vertex_data(u)
                elif u in l2_interior:
                    if g in l1_boundary:
                        verts[g] = L2.vertex_data(u)
                    else:
                        constraints.append((L1.phase(g), L2.phase(u)))
            edges: list[tuple[int, int, bool]] = list(L1.edges)
            for (p, q, h), e in zip(L2.edges, emap, strict=True):
                if e is None:
                    edges.append((vmap[p], vmap[q], h))
            solved = _unify(constraints)
            if solved is None:
                continue
            subst, leftover = solved
            for ground in _ground_solutions(leftover, phases, max_instances):
                full = dict(subst)
                full.update(ground)
                full = {v: (x.substitute(ground) if isinstance(x, PhaseExpr) else x)
                        for v, x in full.items()}
                outs = sorted(v for v, (k, _) in verts.items() if k == "B")
                base = Diagram.build(verts, edges, inputs=(), outputs=outs).substitute(full)
                m1_phases = {v: full.get(v, PhaseExpr.make(0, {v: 1})) for v in r1.variables()}
                m2_phases = {v: full.get(v, PhaseExpr.make(0, {v: 1})) for v in r2.variables()}
                m1 = Matching({v: v for v in L1.vertex_ids}, m1_phases)
                m2 = Matching(dict(vmap), m2_phases)
                for host in _with_star_legs(base, r1, m1, r2, m2, star_legs):
                    try:
                        check_matching(host, r1, m1)
                        check_matching(host, r2, m2)
                        res1 = apply(host, r1, m1)
                        res2 = apply(host, r2, m2)
                    except RewriteError:
                        continue
                    ov = Overlap(r1.name, r2.name, host, m1, m2, res1, res2)
                    k = ov.key
                    if k in seen_keys:
                        continue
                    seen_keys.add(k)
                    yield ov


def _with_star_legs(base: Diagram, r1: Rule, m1: Matching, r2: Rule, m2: Matching,
                    star_legs: int) -> Iterator[Diagram]:
    """`base` and its variants with up to `star_legs` extra context legs of each type on
    every vertex that is a star for each rule matching it as a spider."""
    if star_legs <= 0:
        yield base
        return
    eligible: list[int] = []
    for g in base.interior:
        roles: list[bool] = []
        for rule, m in ((r1, m1), (r2, m2)):
            for u, gv in m.vertices.items():
                if gv == g and rule.lhs.kind(u) != "B":
                    roles.append(u in rule.stars)
        if roles and all(roles):
            eligible.append(g)
    leg_sets: list[tuple[bool, ...]] = [()]
    for n in range(1, star_legs + 1):
        leg_sets += [tuple(c) for c in itertools.combinations_with_replacement((False, True), n)]
    for choice in itertools.product(leg_sets, repeat=len(eligible)):
        verts = {v: base.vertex_data(v) for v in base.vertex_ids}
        edges = list(base.edges)
        nxt = base.max_id + 1
        for g, legs in zip(eligible, choice, strict=True):
            for h in legs:
                verts[nxt] = ("B", Fraction(0))
                edges.append((g, nxt, h))
                nxt += 1
        outs = sorted(v for v, (k, _) in verts.items() if k == "B")
        yield Diagram.build(verts, edges, inputs=(), outputs=outs)


def overlaps(r1: Rule, r2: Rule, *, star_legs: int = 1,
             phases: tuple[Fraction, ...] = PHASES_CLIFFORD_T,
             max_instances: int = DEFAULT_MAX_INSTANCES) -> list[Overlap]:
    """The critical overlaps of `r1` and `r2` (variables renamed apart)."""
    a = rename_apart(r1, "_1")
    b = rename_apart(r2, "_2")
    return list(_pair_overlaps(a, b, r1.name == r2.name, star_legs, phases, max_instances))


# ----------------------------------------------------------------------------- joinability


def _bfs_join(a: Diagram, b: Diagram, rules: Mapping[str, Rule], depth: int,
              max_nodes: int) -> JoinReport:
    ca, cb = a.relabel_canonical(), b.relabel_canonical()
    seen_a = {ca.canonical_json(): ca}
    seen_b = {cb.canonical_json(): cb}
    if ca == cb:
        return JoinReport(True, 0)
    frontiers = [[ca], [cb]]
    seen = [seen_a, seen_b]
    for d in range(1, depth + 1):
        for side in (0, 1):
            new: list[Diagram] = []
            for x in frontiers[side]:
                for _, _, y in successors(x, rules):
                    cy = y.relabel_canonical()
                    key = cy.canonical_json()
                    if key not in seen[side]:
                        seen[side][key] = cy
                        new.append(cy)
                if len(seen[side]) > max_nodes:
                    raise CriticalPairError(
                        f"joinability search exceeded {max_nodes} diagrams on one side"
                    )
            frontiers[side] = new
            if seen[0].keys() & seen[1].keys():
                return JoinReport(True, d)
        if not frontiers[0] and not frontiers[1]:
            break
    return JoinReport(False, None, 0, f"no common diagram within depth {depth}")


def joinable(a: Diagram, b: Diagram, rules: Mapping[str, Rule], depth: int, *,
             phases: tuple[Fraction, ...] = PHASES_CLIFFORD_T,
             max_nodes: int = DEFAULT_MAX_NODES,
             max_instances: int = DEFAULT_MAX_INSTANCES) -> JoinReport:
    """Joinable within `depth` forward steps on each side; a symbolic failure is retried
    on every ground instance of the pair's variables."""
    rep = _bfs_join(a, b, rules, depth, max_nodes)
    if rep.joinable:
        return rep
    variables = sorted(a.variables() | b.variables())
    if not variables or not phases:
        return rep
    if len(phases) ** len(variables) > max_instances:
        raise CriticalPairError(
            f"case split over {len(variables)} variables and {len(phases)} phases exceeds "
            f"the budget of {max_instances} instances"
        )
    worst = 0
    count = 0
    for values in itertools.product(phases, repeat=len(variables)):
        binding = dict(zip(variables, values, strict=True))
        count += 1
        r = _bfs_join(a.substitute(binding), b.substitute(binding), rules, depth, max_nodes)
        if not r.joinable:
            desc = ", ".join(f"{v}={binding[v]}" for v in variables)
            return JoinReport(False, None, count, f"not joinable at instance {desc}: {r.reason}")
        worst = max(worst, r.depth or 0)
    return JoinReport(True, worst, count, "joinable by case split")


# ----------------------------------------------------------------------------- the check


def check(rules: Mapping[str, Rule], depth: int, *, star_legs: int = 1,
          phases: tuple[Fraction, ...] = PHASES_CLIFFORD_T,
          max_nodes: int = DEFAULT_MAX_NODES,
          max_instances: int = DEFAULT_MAX_INSTANCES,
          max_failures: int | None = 1, budget_as_failure: bool = False) -> CheckReport:
    """Every critical pair of every (unordered) pair of rules, joinable within `depth`
    or the first that is not (`max_failures=None` collects them all). A joinability
    budget exhaustion raises `CriticalPairError` -- undecided is not a verdict -- unless
    `budget_as_failure`, which records it as a failure (for surveys)."""
    t0 = time.perf_counter()
    rep = CheckReport(depth=depth, star_legs=star_legs)
    names = sorted(rules)
    for i, n1 in enumerate(names):
        for n2 in names[i:]:
            rep.pairs += 1
            ovs = overlaps(rules[n1], rules[n2], star_legs=star_legs, phases=phases,
                           max_instances=max_instances)
            rep.per_pair[(n1, n2)] = len(ovs)
            for o in ovs:
                rep.overlaps += 1
                try:
                    j = joinable(o.result1, o.result2, rules, depth, phases=phases,
                                 max_nodes=max_nodes, max_instances=max_instances)
                except CriticalPairError as exc:
                    if not budget_as_failure:
                        raise
                    j = JoinReport(False, None, 0, f"undecided: {exc}")
                if j.instances:
                    rep.case_splits += 1
                if not j.joinable:
                    rep.failures.append((o, j))
                    if rep.failure is None:
                        rep.failure = (o, j)
                    if max_failures is not None and len(rep.failures) >= max_failures:
                        rep.seconds = time.perf_counter() - t0
                        return rep
                    continue
                rep.joined += 1
    rep.seconds = time.perf_counter() - t0
    return rep


__all__ = [
    "DEFAULT_MAX_INSTANCES", "DEFAULT_MAX_NODES", "PHASES_CLIFFORD", "PHASES_CLIFFORD_T",
    "CheckReport", "CriticalPairError", "JoinReport", "Overlap", "check",
    "forget_variable_names", "joinable", "overlaps", "rename_apart",
]

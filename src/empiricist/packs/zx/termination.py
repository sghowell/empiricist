"""Termination certificates (M24c Task 3).

A certificate is an ordered list of measure components; the measure of a diagram is
the tuple of their values, compared lexicographically. Every component is a sum of
local weights -- over spiders (by kind) and over edges (by type, self-loop or not) --
so a rule's effect can be computed once, symbolically, for every host: the pattern's
own vertices and edges contribute fixed amounts, and each residual leg of a star
vertex contributes by category (its edge type, whether its other end is another star
or the context, and which target it goes to). A rule *decreases* the measure when the
components, in order, are weakly decreasing for every leg configuration up to and
including the first that is strictly decreasing for every one -- a sufficient
condition for a strict lexicographic decrease on every instance, and the whole of
what `check` certifies: PASS iff every rule decreases. Phase-dependent components are
not offered (patterns are symbolic in their phases).
"""
from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction

from empiricist.packs.zx.diagram import Diagram
from empiricist.packs.zx.rules import Rule


class TerminationError(Exception):
    """A malformed certificate (unknown or empty component list)."""


def _vertex_weight(name: str, kind: str) -> int:
    if name == "vertices":
        return 1
    if name == "z_vertices":
        return int(kind == "Z")
    if name == "x_vertices":
        return int(kind == "X")
    return 0


def _phase_weight_bounds(name: str, phase) -> tuple[int, int]:
    """Contribution of a spider's phase to a phase-aware component, as an interval: exact
    on a ground phase, [0, 1] on a symbolic one (the rule must decrease for every grounding,
    so the LHS is credited with the lower bound and the RHS charged with the upper)."""
    if name not in PHASE_COMPONENTS:
        return (0, 0)
    if isinstance(phase, Fraction):
        if name == "phase_vertices":
            w = int(phase != 0)
        else:  # pi_vertices
            w = int(phase == 1)
        return (w, w)
    return (0, 1)


def _edge_weight(name: str, hadamard: bool, loop: bool) -> int:
    if name == "edges":
        return 1
    if name == "hadamard_edges":
        return int(hadamard)
    if name == "plain_edges":
        return int(not hadamard)
    if name == "self_loops":
        return int(loop)
    return 0


PHASE_COMPONENTS: tuple[str, ...] = ("phase_vertices", "pi_vertices")
COMPONENTS: tuple[str, ...] = (
    "vertices", "z_vertices", "x_vertices", "edges", "hadamard_edges", "plain_edges",
    "self_loops", *PHASE_COMPONENTS,
)


def validate_components(components: Sequence[str]) -> list[str]:
    comps = list(components)
    if not comps:
        raise TerminationError("a measure needs at least one component")
    for c in comps:
        if c not in COMPONENTS:
            raise TerminationError(f"unknown measure component {c!r}; known: {COMPONENTS}")
    return comps


def measure_bounds(
    d: Diagram, components: Sequence[str]
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """(lower, upper) bounds of the measure over every grounding of `d`'s symbolic phases;
    equal for structural components and for ground diagrams."""
    comps = validate_components(components)
    lo: list[int] = []
    hi: list[int] = []
    for c in comps:
        total_lo = total_hi = 0
        for _, k, phase in d.vertices:
            if k == "B":
                continue
            w = _vertex_weight(c, k)
            p_lo, p_hi = _phase_weight_bounds(c, phase)
            total_lo += w + p_lo
            total_hi += w + p_hi
        e = sum(_edge_weight(c, h, u == v) for u, v, h in d.edges)
        lo.append(total_lo + e)
        hi.append(total_hi + e)
    return tuple(lo), tuple(hi)


def measure(d: Diagram, components: Sequence[str]) -> tuple[int, ...]:
    """The exact measure of a diagram; a phase-aware component on a symbolic phase has no
    exact value (use `measure_bounds`)."""
    lo, hi = measure_bounds(d, components)
    if lo != hi:
        raise TerminationError(
            "the measure is not exact on a symbolic phase; use measure_bounds"
        )
    return lo


@dataclass(frozen=True)
class RuleDecrease:
    rule: str
    decreases: bool
    component: str | None
    detail: str
    lhs: tuple[int, ...] = ()
    rhs: tuple[int, ...] = ()


@dataclass
class TerminationReport:
    components: list[str]
    rules: list[RuleDecrease] = field(default_factory=list)
    failure: RuleDecrease | None = None

    @property
    def ok(self) -> bool:
        return self.failure is None


def _leg_diffs(rule: Rule, c: str) -> list[tuple[int, str]]:
    """(LHS - RHS) of one residual leg's contribution to `c`, per category."""
    diffs: list[tuple[int, str]] = []
    stars = sorted(rule.stars)
    for s in stars:
        for h in (False, True):
            lhs = _edge_weight(c, h, False)
            for t, flip in rule.targets(s):
                rhs = _edge_weight(c, h ^ flip, False)
                diffs.append((lhs - rhs, f"leg of star {s} ({'H' if h else 'plain'}) to "
                                         f"context, carried to {t}"))
    for s1, s2 in itertools.combinations_with_replacement(stars, 2):
        for h in (False, True):
            lhs = _edge_weight(c, h, s1 == s2)
            for (t1, f1), (t2, f2) in itertools.product(rule.targets(s1), rule.targets(s2)):
                rhs = _edge_weight(c, h ^ f1 ^ f2, t1 == t2)
                diffs.append((lhs - rhs, f"leg between stars {s1} and {s2} "
                                         f"({'H' if h else 'plain'}), carried to {t1}, {t2}"))
    return diffs


def check_rule(rule: Rule, components: Sequence[str]) -> RuleDecrease:
    comps = validate_components(components)
    lhs_lo, lhs_hi = measure_bounds(rule.lhs, comps)
    rhs_lo, rhs_hi = measure_bounds(rule.rhs, comps)
    lhs, rhs = lhs_lo, rhs_hi   # the conservative pair: credit the LHS least, charge the RHS most
    for c, l_val, r_val, l_hi, r_lo in zip(comps, lhs, rhs, lhs_hi, rhs_lo, strict=True):
        base = l_val - r_val
        bad_leg = next(((d, why) for d, why in _leg_diffs(rule, c) if d < 0), None)
        if base < 0:
            symbolic = (l_hi != l_val) or (r_lo != r_val)
            why = (f"{c} may increase for some grounding of the symbolic phases "
                   f"(LHS in [{l_val}, {l_hi}], RHS in [{r_lo}, {r_val}])"
                   if symbolic else f"{c} increases on the pattern ({l_val} -> {r_val})")
            return RuleDecrease(rule.name, False, c, why, lhs, rhs)
        if bad_leg is not None:
            return RuleDecrease(rule.name, False, c,
                                f"{c} increases on a residual {bad_leg[1]}", lhs, rhs)
        if base > 0:
            return RuleDecrease(rule.name, True, c,
                                f"{c} strictly decreases ({l_val} -> {r_val})", lhs, rhs)
    return RuleDecrease(rule.name, False, None,
                        "the measure ties on this rule for some instance", lhs, rhs)


def check(rules: Mapping[str, Rule], components: Sequence[str]) -> TerminationReport:
    comps = validate_components(components)
    rep = TerminationReport(comps)
    for name in sorted(rules):
        verdict = check_rule(rules[name], comps)
        rep.rules.append(verdict)
        if not verdict.decreases and rep.failure is None:
            rep.failure = verdict
    return rep


__all__ = [
    "COMPONENTS", "RuleDecrease", "TerminationError", "TerminationReport", "check",
    "check_rule", "measure", "validate_components",
]

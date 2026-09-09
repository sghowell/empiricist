"""Rule soundness against the semantic oracle (M25a Task 1).

A rule is *sound* when its two sides denote the same linear map up to a non-zero scalar
on every instance. This module decides that on a bounded, explicitly stated class of
instances: every rule variable grounded over a fragment's phases (all combinations),
and every star vertex carrying 0..`star_legs` residual context legs, each plain or
Hadamard, as a multiset (the legs of one star are interchangeable) -- all combinations
across stars. An instance is the LHS pattern itself as a host (its interface vertices
become boundary vertices, listed as outputs, plus one boundary vertex per residual
leg); the rule is applied through the identity matching; both diagrams are evaluated
with `semantics.matrix` and compared with `equal_up_to_scalar`.

Instances over the semantic budget (more than `semantics.MAX_BOUNDARY_WIRES` wires, or
any other `SemanticsError`) are skipped and counted, never judged. `check` stops at the
first instance that is not an equation; it raises `SoundnessError` when the enumeration
would exceed `max_instances` (before doing any work) or when a rule has no judged
instance at all -- undecided is not a verdict. A PASS therefore says exactly: every
judged instance of every rule, on the stated class, is an equation up to scalar. The
enumeration is exhaustive for the class; it says nothing about more residual legs or
phases outside the fragment.
"""
from __future__ import annotations

import itertools
import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from fractions import Fraction

import numpy as np

from empiricist.packs.zx import semantics
from empiricist.packs.zx.diagram import Diagram
from empiricist.packs.zx.rewrite import Matching, apply
from empiricist.packs.zx.rules import PHASES_CLIFFORD_T, Rule

DEFAULT_MAX_INSTANCES = 4096
DIFFERENCE_TOLERANCE = 1e-6

Bindings = dict[str, Fraction]
Legs = dict[int, tuple[bool, ...]]


class SoundnessError(Exception):
    """The question is undecided: a budget would be exceeded, or a rule has no judged
    instance."""


@dataclass(frozen=True)
class RuleFailure:
    rule: str
    bindings: Bindings
    legs: Legs
    host: Diagram
    result: Diagram
    entry: tuple[int, int] | None
    lhs_value: complex
    rhs_value: complex
    reason: str


@dataclass
class SoundnessReport:
    rules: list[str]
    star_legs: int
    instances: int = 0
    skipped: int = 0
    failure: RuleFailure | None = None
    per_rule: dict[str, dict[str, int]] = field(default_factory=dict)
    seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return self.failure is None


# ----------------------------------------------------------------------------- instances


def leg_configurations(star_legs: int) -> list[tuple[bool, ...]]:
    """Every multiset of 0..`star_legs` residual legs, each plain (False) or Hadamard."""
    out: list[tuple[bool, ...]] = [()]
    for n in range(1, star_legs + 1):
        out += [tuple(c) for c in itertools.combinations_with_replacement((False, True), n)]
    return out


def instance(rule: Rule, bindings: Mapping[str, Fraction], legs: Mapping[int, tuple[bool, ...]]
             ) -> Diagram:
    """The LHS pattern as a concrete host: variables bound, every star vertex given the
    extra boundary legs in `legs` (Hadamard flags per star), all boundaries as outputs."""
    lhs = rule.lhs.substitute(bindings)
    verts = {v: lhs.vertex_data(v) for v in lhs.vertex_ids}
    edges = list(lhs.edges)
    nxt = lhs.max_id + 1
    for star in sorted(legs):
        for h in legs[star]:
            verts[nxt] = ("B", Fraction(0))
            edges.append((star, nxt, h))
            nxt += 1
    outs = sorted(v for v, (k, _) in verts.items() if k == "B")
    return Diagram.build(verts, edges, inputs=(), outputs=outs)


def identity_matching(rule: Rule, bindings: Mapping[str, Fraction]) -> Matching:
    return Matching(vertices={v: v for v in rule.lhs.vertex_ids}, phases=dict(bindings))


def instance_count(rule: Rule, phases: tuple[Fraction, ...], star_legs: int) -> int:
    return len(phases) ** len(rule.variables()) * len(leg_configurations(star_legs)) ** len(
        rule.stars)


def instances_of(rule: Rule, phases: tuple[Fraction, ...], star_legs: int
                 ) -> Iterator[tuple[Bindings, Legs, Diagram]]:
    """(bindings, legs, host) for every instance of `rule` on the class: bindings
    outermost (variables in name order, phases in the given order), then leg
    configurations across the stars (in id order)."""
    names = sorted(rule.variables())
    stars = sorted(rule.stars)
    configs = leg_configurations(star_legs)
    for values in itertools.product(phases, repeat=len(names)):
        bindings: Bindings = dict(zip(names, values, strict=True))
        for choice in itertools.product(configs, repeat=len(stars)):
            legs: Legs = dict(zip(stars, choice, strict=True))
            yield bindings, legs, instance(rule, bindings, legs)


# ----------------------------------------------------------------------------- judging


def first_difference(a: np.ndarray, b: np.ndarray, tol: float = DIFFERENCE_TOLERANCE
                     ) -> tuple[tuple[int, int], complex, complex] | None:
    """The first entry (row-major) at which `a` and `b` differ once both are scaled so
    that `a`'s first non-negligible entry is matched by `b`'s, with the two scaled
    values there; None when no entry differs by more than `tol`."""
    a = np.asarray(a, dtype=complex)
    b = np.asarray(b, dtype=complex)
    if a.shape != b.shape:
        return (0, 0), complex(a.flat[0]) if a.size else 0j, complex(b.flat[0]) if b.size else 0j
    scale = max(float(np.max(np.abs(a))), float(np.max(np.abs(b))), 1.0) if a.size else 1.0
    small = tol * scale
    za, zb = np.abs(a) <= small, np.abs(b) <= small
    if za.all() and zb.all():
        return None
    if za.all() or zb.all():
        nz = np.argwhere(~(zb if za.all() else za))[0]
        i, j = int(nz[0]), int(nz[1])
        return (i, j), complex(a[i, j]), complex(b[i, j])
    p = np.argwhere(~za)[0]
    pi, pj = int(p[0]), int(p[1])
    an = a / a[pi, pj]
    if zb[pi, pj]:
        return (pi, pj), 1 + 0j, complex(b[pi, pj] / np.max(np.abs(b)))
    bn = b / b[pi, pj]
    diff = np.abs(an - bn) > tol * max(1.0, float(np.max(np.abs(an))), float(np.max(np.abs(bn))))
    hits = np.argwhere(diff)
    if len(hits) == 0:
        return None
    i, j = int(hits[0][0]), int(hits[0][1])
    return (i, j), complex(an[i, j]), complex(bn[i, j])


def _tidy(z: complex) -> str:
    """A complex number with numerical dust (below 1e-9) removed, for messages."""
    re = 0.0 if abs(z.real) < 1e-9 else z.real
    im = 0.0 if abs(z.imag) < 1e-9 else z.imag
    if im == 0:
        return f"{re:.6g}"
    return f"{re:.6g}{im:+.6g}j"


def judge(rule: Rule, bindings: Bindings, legs: Legs, host: Diagram
          ) -> tuple[bool | None, Diagram | None, RuleFailure | None]:
    """(equal, result, failure): equal is None when the instance is over the semantic
    budget (skipped)."""
    if semantics.boundary_wires(host) > semantics.MAX_BOUNDARY_WIRES:
        return None, None, None
    result = apply(host, rule, identity_matching(rule, bindings))
    try:
        ma, mb = semantics.matrix(host), semantics.matrix(result)
    except semantics.SemanticsError:
        return None, result, None
    if semantics.equal_up_to_scalar(ma, mb, semantics.TOLERANCE):
        return True, result, None
    diff = first_difference(ma, mb)
    if diff is None:
        entry, va, vb = None, 0j, 0j
        reason = (f"the two sides differ beyond tolerance {semantics.TOLERANCE} but no single "
                  f"entry differs by more than {DIFFERENCE_TOLERANCE}")
    else:
        entry, va, vb = diff
        reason = (f"after scaling, entry {list(entry)} is {_tidy(va)} on the LHS and "
                  f"{_tidy(vb)} on the RHS")
    return False, result, RuleFailure(rule.name, bindings, legs, host, result, entry, va, vb,
                                      reason)


def check(rules: Mapping[str, Rule], *, phases: tuple[Fraction, ...] = PHASES_CLIFFORD_T,
          star_legs: int = 1, max_instances: int = DEFAULT_MAX_INSTANCES) -> SoundnessReport:
    """Every rule (in name order) on every instance of the class, stopping at the first
    instance that is not an equation up to scalar. Raises `SoundnessError` when the
    class has more than `max_instances` instances in total, or when some rule has no
    judged instance and no rule failed."""
    t0 = time.perf_counter()
    names = sorted(rules)
    rep = SoundnessReport(rules=names, star_legs=star_legs)
    total = sum(instance_count(rules[n], phases, star_legs) for n in names)
    if total > max_instances:
        raise SoundnessError(
            f"the class has {total} instances over {len(names)} rules, more than the budget "
            f"of {max_instances}"
        )
    for name in names:
        rule = rules[name]
        judged = skipped = 0
        for bindings, legs, host in instances_of(rule, phases, star_legs):
            equal, _, failure = judge(rule, bindings, legs, host)
            if equal is None:
                skipped += 1
                continue
            judged += 1
            if failure is not None:
                rep.failure = failure
                break
        rep.per_rule[name] = {"instances": judged, "skipped": skipped}
        rep.instances += judged
        rep.skipped += skipped
        if rep.failure is not None:
            break
    rep.seconds = time.perf_counter() - t0
    if rep.failure is None:
        unjudged = [n for n in names if rep.per_rule[n]["instances"] == 0]
        if unjudged:
            raise SoundnessError(
                "unjudgeable: every instance of " + ", ".join(unjudged)
                + " is over the semantic budget"
            )
    return rep


__all__ = [
    "DEFAULT_MAX_INSTANCES", "DIFFERENCE_TOLERANCE", "Bindings", "Legs", "RuleFailure",
    "SoundnessError", "SoundnessReport", "check", "first_difference", "identity_matching",
    "instance", "instance_count", "instances_of", "judge", "leg_configurations",
]

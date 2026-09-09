"""Rewrite rules and the rule library (M24c Task 2).

A `Rule` is a pair of patterns, `lhs` and `rhs`: diagrams over the same interface (their
`B` vertices, listed as outputs in id order, each of degree 1 on both sides) whose
spider phases may be `PhaseExpr`s over shared variables. Interface vertices stand for
"whatever the context attaches here"; a matching sends them to any host vertex.

Variable arity is the `residual` map: an LHS interior vertex listed there is a *star*
vertex, allowed to carry host legs beyond the pattern's own (the residual legs); those
legs are re-attached to the listed RHS target(s), with the Hadamard flag toggled when
the target's `flip` is set (colour change). Several targets mean a matching must say
which target each leg goes to (the reverse of fusion splits legs between two spiders);
the first target is the default. Non-star vertices match host vertices of exactly
their pattern degree. `reversed()` swaps the sides and inverts the residual map, so
every rule is usable in both directions.

The library is the Jeandel-Perdrix-Vilmart Clifford+T axiomatisation (JPV18: E. Jeandel,
S. Perdrix, R. Vilmart, "A Complete Axiomatisation of the ZX-Calculus for Clifford+T
Quantum Mechanics", LICS 2018, arXiv:1705.11151, Figure 1), read up to non-zero scalars
(the scalar sub-diagrams JPV carry for exactness are dropped, except where a rule's
scalar part can vanish), plus the rules the graph model itself needs: the identity rule
in its Hadamard-leg variants (a Hadamard box is an edge here) and self-loop removal
(fusion of parallel edges produces loops). Colour-swapped twins carry the suffix `_x`
(JPV: "all of these rules also hold ... with the colours red and green swapped"). Every
rule is checked semantically on concrete instances in the test suite; the decoding of
(C) and (BW) is from the paper's TikZ source, where a wire drawn straight through a
node passes through it.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from empiricist.packs.zx.diagram import Diagram

Residual = tuple[tuple[int, tuple[tuple[int, bool], ...]], ...]

# the ground phases of the two fragments the library speaks about (units of pi)
PHASES_CLIFFORD_T: tuple[Fraction, ...] = tuple(Fraction(k, 4) for k in range(8))
PHASES_CLIFFORD: tuple[Fraction, ...] = tuple(Fraction(k, 2) for k in range(4))


@dataclass(frozen=True)
class Rule:
    name: str
    lhs: Diagram
    rhs: Diagram
    residual: Residual = ()
    reference: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("a rule needs a name")
        res: list[tuple[int, tuple[tuple[int, bool], ...]]] = []
        for item in self.residual:
            star, targets = item
            res.append((int(star), tuple((int(t), bool(f)) for t, f in targets)))
        res.sort()
        object.__setattr__(self, "residual", tuple(res))
        if set(self.lhs.boundary) != set(self.rhs.boundary):
            raise ValueError(f"rule {self.name}: LHS and RHS interfaces differ")
        for side, d in (("LHS", self.lhs), ("RHS", self.rhs)):
            if d.inputs or d.outputs != tuple(sorted(d.boundary)):
                raise ValueError(
                    f"rule {self.name}: {side} must list its interface as outputs in id order"
                )
            for b in d.boundary:
                if d.degree(b) != 1:
                    raise ValueError(f"rule {self.name}: {side} interface vertex {b} has degree "
                                     f"{d.degree(b)}, expected 1")
        lhs_int, rhs_int = set(self.lhs.interior), set(self.rhs.interior)
        seen: set[int] = set()
        for star, targets in self.residual:
            if star not in lhs_int:
                raise ValueError(f"rule {self.name}: star {star} is not an LHS interior vertex")
            if star in seen:
                raise ValueError(f"rule {self.name}: star {star} listed twice")
            seen.add(star)
            if not targets:
                raise ValueError(f"rule {self.name}: star {star} has no residual target")
            for t, _ in targets:
                if t not in rhs_int:
                    raise ValueError(f"rule {self.name}: residual target {t} is not an RHS "
                                     "interior vertex")

    @property
    def stars(self) -> frozenset[int]:
        return frozenset(s for s, _ in self.residual)

    @property
    def interface(self) -> tuple[int, ...]:
        return self.lhs.outputs

    def targets(self, star: int) -> tuple[tuple[int, bool], ...]:
        for s, t in self.residual:
            if s == star:
                return t
        return ()

    def variables(self) -> frozenset[str]:
        return self.lhs.variables() | self.rhs.variables()

    def reversed(self) -> Rule:
        rev: dict[int, list[tuple[int, bool]]] = {}
        for star, targets in self.residual:
            for t, flip in targets:
                rev.setdefault(t, []).append((star, flip))
        return Rule(self.name, self.rhs, self.lhs,
                    tuple((t, tuple(v)) for t, v in rev.items()), self.reference)

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "lhs": self.lhs.to_json(),
            "rhs": self.rhs.to_json(),
            "residual": [[s, [[t, f] for t, f in targets]] for s, targets in self.residual],
            "reference": self.reference,
        }

    @classmethod
    def from_json(cls, obj: Any) -> Rule:
        if not isinstance(obj, dict):
            raise ValueError("a rule is a JSON object")
        try:
            name, lhs, rhs = obj["name"], obj["lhs"], obj["rhs"]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"rule is missing {exc}") from None
        residual_obj = obj.get("residual", [])
        if not isinstance(residual_obj, list):
            raise ValueError("rule residual must be a list")
        residual: list[tuple[int, tuple[tuple[int, bool], ...]]] = []
        for item in residual_obj:
            if not isinstance(item, list) or len(item) != 2 or not isinstance(item[1], list):
                raise ValueError(f"bad residual entry {item!r}")
            targets = []
            for t in item[1]:
                if not isinstance(t, list) or len(t) != 2 or not isinstance(t[1], bool):
                    raise ValueError(f"bad residual target {t!r}")
                targets.append((int(t[0]), t[1]))
            residual.append((int(item[0]), tuple(targets)))
        ref = obj.get("reference", "")
        if not isinstance(ref, str) or not isinstance(name, str):
            raise ValueError("rule name and reference must be strings")
        return cls(name, Diagram.from_json(lhs), Diagram.from_json(rhs), tuple(residual), ref)


# ----------------------------------------------------------------------------- the library

JPV = "JPV18 (arXiv:1705.11151, Fig. 1)"


def _pat(vertices: Mapping[int, tuple[str, Any]], edges: list[tuple[int, int, bool]]) -> Diagram:
    outs = sorted(v for v, (k, _) in vertices.items() if k == "B")
    return Diagram.build(vertices, edges, inputs=(), outputs=outs)


def _plain(*pairs: tuple[int, int]) -> list[tuple[int, int, bool]]:
    return [(u, v, False) for u, v in pairs]


def swap_colours(rule: Rule, name: str, reference: str | None = None) -> Rule:
    """The colour-swapped twin of a rule (Z <-> X on both sides)."""
    def swap(d: Diagram) -> Diagram:
        verts = tuple((v, {"Z": "X", "X": "Z"}.get(k, k), p) for v, k, p in d.vertices)
        return Diagram(verts, d.edges, d.inputs, d.outputs)
    ref = reference if reference is not None else rule.reference + ", colours swapped"
    return Rule(name, swap(rule.lhs), swap(rule.rhs), rule.residual, ref)


def _library() -> dict[str, Rule]:
    B = ("B", 0)
    rules: list[Rule] = []

    # (S1) spider fusion: two Z spiders joined by a plain edge fuse, legs carried over
    rules.append(Rule(
        "fusion",
        _pat({0: ("Z", "a"), 1: ("Z", "b")}, _plain((0, 1))),
        _pat({0: ("Z", "a+b")}, []),
        residual=((0, ((0, False),)), (1, ((0, False),))),
        reference=f"{JPV} (S1) spider fusion",
    ))
    rules.append(swap_colours(rules[-1], "fusion_x"))

    # (S2) identity: a degree-2 phase-0 spider is a wire; with Hadamard legs it is a
    # Hadamard box (one H leg) or two cancelling boxes (two H legs)
    for kind in ("Z", "X"):
        k = kind.lower()
        rules.append(Rule(
            f"identity_{k}",
            _pat({0: B, 1: (kind, 0), 2: B}, _plain((0, 1), (1, 2))),
            _pat({0: B, 2: B}, _plain((0, 2))),
            reference=f"{JPV} (S2) identity" + (", colours swapped" if kind == "X" else ""),
        ))
        rules.append(Rule(
            f"identity_{k}_h",
            _pat({0: B, 1: (kind, 0), 2: B}, [(0, 1, True), (1, 2, False)]),
            _pat({0: B, 2: B}, [(0, 2, True)]),
            reference=f"{JPV} (S2) identity with one Hadamard leg (a Hadamard box is an edge "
                      "in this graph model)",
        ))
        rules.append(Rule(
            f"identity_{k}_hh",
            _pat({0: B, 1: (kind, 0), 2: B}, [(0, 1, True), (1, 2, True)]),
            _pat({0: B, 2: B}, _plain((0, 2))),
            reference=f"{JPV} (S2) identity with two Hadamard legs: H.H = I",
        ))

    # (H) colour change: an X spider is a Z spider with every leg toggled
    rules.append(Rule(
        "colour_change",
        _pat({0: ("X", "a")}, []),
        _pat({0: ("Z", "a")}, []),
        residual=((0, ((0, True),)),),
        reference=f"{JPV} (H) colour change; the reverse direction is its colour-swapped twin",
    ))

    # (B1) copy: an X(0) state copies through a Z(0) spider with two other legs
    rules.append(Rule(
        "copy",
        _pat({0: ("X", 0), 1: ("Z", 0), 2: B, 3: B}, _plain((0, 1), (1, 2), (1, 3))),
        _pat({4: ("X", 0), 5: ("X", 0), 2: B, 3: B}, _plain((4, 2), (5, 3))),
        reference=f"{JPV} (B1) copy",
    ))
    rules.append(swap_colours(rules[-1], "copy_x"))

    # (B2) bialgebra: K_{2,2} of two Z(0) and two X(0), one leg each, is one Z(0)-X(0) pair
    # with the Z carrying the former X legs and the X the former Z legs
    rules.append(Rule(
        "bialgebra",
        _pat({0: ("Z", 0), 1: ("Z", 0), 2: ("X", 0), 3: ("X", 0), 4: B, 5: B, 6: B, 7: B},
             _plain((0, 2), (0, 3), (1, 2), (1, 3), (0, 4), (1, 5), (2, 6), (3, 7))),
        _pat({8: ("Z", 0), 9: ("X", 0), 4: B, 5: B, 6: B, 7: B},
             _plain((8, 9), (8, 6), (8, 7), (9, 4), (9, 5))),
        reference=f"{JPV} (B2) bialgebra",
    ))

    # (K) pi-commutation on a wire: Z(a) then X(pi) is X(pi) then Z(-a)
    rules.append(Rule(
        "pi_commute",
        _pat({0: B, 1: ("Z", "a"), 2: ("X", 1), 3: B}, _plain((0, 1), (1, 2), (2, 3))),
        _pat({0: B, 4: ("X", 1), 5: ("Z", "-a"), 3: B}, _plain((0, 4), (4, 5), (5, 3))),
        reference=f"{JPV} (K) pi-commutation, colours swapped relative to the figure",
    ))
    rules.append(swap_colours(rules[-1], "pi_commute_x", reference=f"{JPV} (K) as drawn"))

    # pi-copy: X(pi) on one leg of a Z(a) spider with two other legs copies to those legs
    # and negates the phase ((K) pushed through (S1); the (K1)-style form of Backens 2014)
    rules.append(Rule(
        "pi_copy",
        _pat({0: B, 1: ("X", 1), 2: ("Z", "a"), 3: B, 4: B},
             _plain((0, 1), (1, 2), (2, 3), (2, 4))),
        _pat({0: B, 5: ("Z", "-a"), 6: ("X", 1), 7: ("X", 1), 3: B, 4: B},
             _plain((0, 5), (5, 6), (5, 7), (6, 3), (7, 4))),
        reference=f"{JPV} (K) lifted through (S1) to a spider with two further legs "
                  "(the pi-copy form of Backens 2014)",
    ))
    rules.append(swap_colours(rules[-1], "pi_copy_x"))

    # Hopf: a Z and an X spider joined by two parallel plain edges are disconnected
    rules.append(Rule(
        "hopf",
        _pat({0: ("Z", "a"), 1: ("X", "b")}, _plain((0, 1), (0, 1))),
        _pat({0: ("Z", "a"), 1: ("X", "b")}, []),
        residual=((0, ((0, False),)), (1, ((1, False),))),
        reference="Hopf law (Coecke-Duncan 2011), derivable from (B1), (B2), (S1) in JPV18",
    ))
    # graph-like Hopf: two parallel Hadamard edges between Z spiders cancel
    rules.append(Rule(
        "hopf_h",
        _pat({0: ("Z", "a"), 1: ("Z", "b")}, [(0, 1, True), (0, 1, True)]),
        _pat({0: ("Z", "a"), 1: ("Z", "b")}, []),
        residual=((0, ((0, False),)), (1, ((1, False),))),
        reference="Hopf law in graph-like form (hopf composed with (H))",
    ))

    # (EU) Euler decomposition of the Hadamard: H = Z(pi/2) X(pi/2) Z(pi/2) up to scalar
    rules.append(Rule(
        "euler",
        _pat({0: B, 1: B}, [(0, 1, True)]),
        _pat({0: B, 2: ("Z", "1/2"), 3: ("X", "1/2"), 4: ("Z", "1/2"), 1: B},
             _plain((0, 2), (2, 3), (3, 4), (4, 1))),
        reference=f"{JPV} (EU) Euler decomposition, scalar-free form",
    ))
    rules.append(swap_colours(rules[-1], "euler_x"))

    # (SUP) supplementarity: Z(a) and Z(a+pi) states into an X(0) with one further leg
    # give an X(0) state times the scalar Z(2a+pi), kept as JPV draw it (a spider joined
    # to the X(0) by two edges) because it vanishes at a = 0
    rules.append(Rule(
        "supp",
        _pat({0: ("Z", "a"), 1: ("Z", "a+1"), 2: ("X", 0), 3: B}, _plain((0, 2), (1, 2), (2, 3))),
        _pat({3: B, 4: ("X", 0), 5: ("Z", "2a+1")}, _plain((4, 3), (4, 5), (4, 5))),
        reference=f"{JPV} (SUP) supplementarity",
    ))
    rules.append(swap_colours(rules[-1], "supp_x"))

    # (E) the scalar Z(pi/4)-X(-pi/4) is the empty diagram
    rules.append(Rule(
        "e_scalar",
        _pat({0: ("Z", "1/4"), 1: ("X", "-1/4")}, _plain((0, 1))),
        _pat({}, []),
        reference=f"{JPV} (E) (a scalar rule: trivial up to scalar)",
    ))

    # (C) commutation of controls: the diagram is symmetric under exchanging its two outer
    # wires when the control phase c is negated (three-parameter rule)
    def c_side(sign: int, b_left: int, b_right: int) -> Diagram:
        return _pat(
            {10: ("X", f"{-sign}c"), 11: ("Z", "a"), 6: ("X", 0), 2: ("Z", "a"), 7: ("Z", 0),
             3: ("X", 1), 1: ("Z", "b"), 5: ("Z", "b"), 13: ("Z", 0), 8: ("X", f"{sign}c"),
             100: B, 101: B, 102: B, 103: B},
            _plain((b_left, 10), (10, 11), (10, 13), (11, 6), (11, 8), (6, 7), (6, 2), (7, 103),
                   (7, 3), (3, 5), (3, 1), (5, b_right), (5, 8), (13, 101), (13, 8)),
        )
    rules.append(Rule(
        "commute_controls", c_side(1, 100, 102), c_side(-1, 102, 100),
        reference=f"{JPV} (C) commutation of controls, decoded from the TikZ source",
    ))

    # (BW): a phase-pi/4-decorated wire equals a short Clifford+T chain
    rules.append(Rule(
        "bw",
        _pat({100: B, 101: B, 0: ("Z", 0), 4: ("X", 0), 6: ("Z", "-1/2"), 14: ("X", 0),
              10: ("Z", 0), 1: ("X", 0), 2: ("Z", "1/4"), 3: ("Z", "1/4"), 5: ("Z", "1/4"),
              13: ("Z", "1/4"), 12: ("X", 0), 9: ("Z", "1/4"), 8: ("Z", "1/4")},
             _plain((100, 0), (0, 4), (4, 6), (6, 14), (14, 10), (10, 101), (0, 1), (1, 2),
                    (1, 3), (4, 5), (14, 13), (10, 12), (12, 9), (12, 8))),
        _pat({100: B, 101: B, 24: ("Z", 0), 18: ("X", 1), 25: ("Z", "1/4"), 19: ("X", "1/2"),
              23: ("X", 1), 22: ("Z", "1/4"), 17: ("Z", "1/4"), 20: ("Z", "1/4")},
             _plain((100, 24), (24, 18), (18, 25), (25, 19), (19, 101), (24, 23), (23, 22),
                    (23, 17), (18, 20))),
        reference=f"{JPV} (BW), decoded from the TikZ source",
    ))

    # graph-model rules: self-loops (fusion of parallel edges produces them)
    for kind in ("Z", "X"):
        k = kind.lower()
        rules.append(Rule(
            f"loop_{k}",
            _pat({0: (kind, "a")}, _plain((0, 0))),
            _pat({0: (kind, "a")}, []),
            residual=((0, ((0, False),)),),
            reference="graph model: a plain self-loop is a fused wire, (S1)/(S3) in JPV18",
        ))
        rules.append(Rule(
            f"loop_{k}_h",
            _pat({0: (kind, "a")}, [(0, 0, True)]),
            _pat({0: (kind, "a+1")}, []),
            residual=((0, ((0, False),)),),
            reference="graph model: a Hadamard self-loop adds pi ((S1), (EU), (K) in JPV18)",
        ))

    out = {r.name: r for r in rules}
    assert len(out) == len(rules), "duplicate rule name"
    return out


RULES: dict[str, Rule] = _library()

CLIFFORD_RULES: tuple[str, ...] = (
    "fusion", "fusion_x", "identity_z", "identity_x", "identity_z_h", "identity_x_h",
    "identity_z_hh", "identity_x_hh", "colour_change", "copy", "copy_x", "bialgebra",
    "pi_commute", "pi_commute_x", "pi_copy", "pi_copy_x", "hopf", "hopf_h", "euler", "euler_x",
    "loop_z", "loop_x", "loop_z_h", "loop_x_h",
)
CLIFFORD_T_RULES: tuple[str, ...] = CLIFFORD_RULES + (
    "supp", "supp_x", "e_scalar", "commute_controls", "bw",
)


def rule_table() -> list[dict[str, Any]]:
    """One row per library rule, for documentation."""
    return [
        {
            "name": r.name,
            "reference": r.reference,
            "lhs_vertices": len(r.lhs.interior),
            "rhs_vertices": len(r.rhs.interior),
            "interface": len(r.interface),
            "stars": sorted(r.stars),
            "variables": sorted(r.variables()),
            "fragment": "Clifford" if r.name in CLIFFORD_RULES else "Clifford+T",
        }
        for r in RULES.values()
    ]


__all__ = [
    "CLIFFORD_RULES", "CLIFFORD_T_RULES", "JPV", "PHASES_CLIFFORD", "PHASES_CLIFFORD_T", "RULES",
    "Residual", "Rule", "rule_table", "swap_colours",
]

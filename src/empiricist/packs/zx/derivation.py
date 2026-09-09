"""Derivations and their replay (M24c Task 2).

A derivation is a start diagram, a list of steps (rule name, matching, direction) and a
claimed end diagram. `replay` applies the steps in order and reports the diagram
reached, the first step that does not apply (with the reason), and whether the reached
diagram is canonically equal to the claimed end. It never raises on a bad derivation:
a fault in the payload is a failed step, and only a fault in the machinery propagates.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from empiricist.packs.zx.diagram import Diagram, isomorphic
from empiricist.packs.zx.rewrite import Matching, RewriteError, apply
from empiricist.packs.zx.rules import Rule

DIRECTIONS = ("->", "<-")


@dataclass(frozen=True)
class Step:
    rule: str
    matching: Matching
    direction: str = "->"

    def to_json(self) -> dict[str, Any]:
        return {"rule": self.rule, "matching": self.matching.to_json(),
                "direction": self.direction}

    @classmethod
    def from_json(cls, obj: Any) -> Step:
        if not isinstance(obj, dict):
            raise ValueError("a step is a JSON object")
        rule = obj.get("rule")
        if not isinstance(rule, str):
            raise ValueError("step rule must be a string")
        direction = obj.get("direction", "->")
        if not isinstance(direction, str):
            raise ValueError("step direction must be a string")
        return cls(rule, Matching.from_json(obj.get("matching")), direction)


@dataclass(frozen=True)
class Derivation:
    start: Diagram
    steps: tuple[Step, ...]
    end: Diagram

    def to_json(self) -> dict[str, Any]:
        return {"start": self.start.to_json(), "steps": [s.to_json() for s in self.steps],
                "end": self.end.to_json()}

    @classmethod
    def from_json(cls, obj: Any) -> Derivation:
        if not isinstance(obj, dict):
            raise ValueError("a derivation is a JSON object")
        for key in ("start", "steps", "end"):
            if key not in obj:
                raise ValueError(f"derivation is missing {key!r}")
        if not isinstance(obj["steps"], list):
            raise ValueError("derivation steps must be a list")
        return cls(Diagram.from_json(obj["start"]),
                   tuple(Step.from_json(s) for s in obj["steps"]),
                   Diagram.from_json(obj["end"]))


@dataclass(frozen=True)
class ReplayResult:
    reached: Diagram
    steps_applied: int
    failed_step: int | None
    reason: str | None
    end_matches: bool

    @property
    def ok(self) -> bool:
        return self.failed_step is None and self.end_matches


def replay(derivation: Derivation, rules: Mapping[str, Rule]) -> ReplayResult:
    current = derivation.start
    for i, step in enumerate(derivation.steps):
        rule = rules.get(step.rule)
        if rule is None:
            return ReplayResult(current, i, i, f"unknown rule {step.rule!r}", False)
        if step.direction not in DIRECTIONS:
            return ReplayResult(current, i, i, f"bad direction {step.direction!r}", False)
        if step.direction == "<-":
            rule = rule.reversed()
        try:
            current = apply(current, rule, step.matching)
        except RewriteError as exc:
            return ReplayResult(current, i, i, f"{step.rule} does not apply: {exc}", False)
    return ReplayResult(current, len(derivation.steps), None, None,
                        isomorphic(current, derivation.end))


__all__ = ["DIRECTIONS", "Derivation", "ReplayResult", "Step", "replay"]

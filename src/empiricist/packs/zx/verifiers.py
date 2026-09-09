"""The four `zx` pack verifiers (M24c Task 3).

Each judges the bytes of one committed evidence file, a JSON object:

* `zx_derivation`  {"start", "end", "steps": [{"rule", "matching", "direction"}], "rules"?}
  PASS iff every step applies in order and the diagram reached is canonically equal to
  `end`; FAIL names the first step that does not apply, or reports the end mismatch.
  Rule names come from the pack library; `rules` may add inline rules under new names.
* `zx_semantic_equal`  {"a", "b"}
  PASS iff the two diagrams' matrices are equal up to a non-zero scalar (both zero
  counts as equal); FAIL otherwise; ERROR above the evaluation budget (6 wires).
* `zx_critical_pairs`  {"rules": [names or inline rules], "depth", "star_legs"?,
  "fragment"?, "max_nodes"?, "max_instances"?}
  PASS iff every enumerated critical pair of the (oriented) rules is joinable within
  `depth` forward steps on each side; FAIL names the first that is not, with the
  overlap and both results; ERROR when a search budget runs out (undecided).
* `zx_termination`  {"rules": [...], "measure": [components]}
  PASS iff every rule strictly decreases the lexicographic measure for every instance
  (symbolic check over residual legs); FAIL names the first rule that does not.

`verify_bytes` is total: a malformed payload, an ill-formed diagram, an unknown rule
or component, or an exhausted budget is an ERROR verdict with the reason, never a
raised exception. Goldens are the JSON files under `goldens/`, listed per verifier in
`GOLDENS` with their expected verdicts; each suite carries near-miss FAIL cases.
"""
from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from empiricist.ledger.models import Verdict
from empiricist.packs import BytesFileVerifier, GoldenCase
from empiricist.packs.zx import (
    critical_pairs,
    derivation,
    diagram,
    rewrite,
    rules,
    semantics,
    termination,
)
from empiricist.packs.zx.diagram import Diagram
from empiricist.packs.zx.rules import RULES, Rule
from empiricist.verifiers.base import VerifierResult, module_source_hash

GOLDEN_DIR = Path(__file__).resolve().parent / "goldens"
MAX_DEPTH = 12
MAX_STAR_LEGS = 3
FRAGMENTS = {"clifford+t": critical_pairs.PHASES_CLIFFORD_T,
             "clifford": critical_pairs.PHASES_CLIFFORD}

GOLDENS: dict[str, tuple[tuple[str, Verdict], ...]] = {
    "zx_derivation": (
        ("zx_derivation__fuse_then_identity", Verdict.PASS),
        ("zx_derivation__euler_there_and_back", Verdict.PASS),
        ("zx_derivation__cnot_squared_is_identity", Verdict.PASS),
        ("zx_derivation__wrong_vertex_in_step_2", Verdict.FAIL),
        ("zx_derivation__end_off_by_one_phase", Verdict.FAIL),
        ("zx_derivation__last_step_missing", Verdict.FAIL),
    ),
    "zx_semantic_equal": (
        ("zx_semantic_equal__cnot_two_forms", Verdict.PASS),
        ("zx_semantic_equal__hadamard_euler", Verdict.PASS),
        ("zx_semantic_equal__bialgebra_instance", Verdict.PASS),
        ("zx_semantic_equal__euler_wrong_sign", Verdict.FAIL),
        ("zx_semantic_equal__t_vs_t_dagger", Verdict.FAIL),
        ("zx_semantic_equal__cnot_control_swapped", Verdict.FAIL),
    ),
    "zx_critical_pairs": (
        ("zx_critical_pairs__fusion_identity_depth1", Verdict.PASS),
        ("zx_critical_pairs__fusions_colour_change_depth2", Verdict.PASS),
        ("zx_critical_pairs__fusion_x_colour_change_depth2", Verdict.FAIL),
        ("zx_critical_pairs__fusions_colour_change_depth1", Verdict.FAIL),
    ),
    "zx_termination": (
        ("zx_termination__clifford_core_vertices_edges", Verdict.PASS),
        ("zx_termination__hadamard_first", Verdict.PASS),
        ("zx_termination__colour_change_ties", Verdict.FAIL),
        ("zx_termination__hopf_vertices_only", Verdict.FAIL),
    ),
}


class PayloadError(Exception):
    """The evidence cannot be judged: malformed, ill-formed or out of scope."""


def _load_payload(payload: bytes) -> dict[str, Any]:
    try:
        obj = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PayloadError(f"payload is not JSON: {exc}") from None
    if not isinstance(obj, dict):
        raise PayloadError("payload must be a JSON object")
    return obj


def _diagram(obj: Any, what: str) -> Diagram:
    if obj is None:
        raise PayloadError(f"payload is missing {what!r}")
    try:
        d = Diagram.from_json(obj)
    except ValueError as exc:
        raise PayloadError(f"{what}: {exc}") from None
    problems = d.well_formedness_problems()
    if problems:
        raise PayloadError(f"{what} is not well-formed: " + "; ".join(problems))
    return d


def _rulebook(spec: Any, *, extend_library: bool) -> dict[str, Rule]:
    """Rules named from the library or given inline. With `extend_library` the result
    is the whole library plus the inline rules (which may not shadow a library name);
    otherwise exactly the listed rules."""
    if spec is None and extend_library:
        spec = []
    if not isinstance(spec, list) or (not spec and not extend_library):
        raise PayloadError("'rules' must be a non-empty list of rule names or inline rules")
    out: dict[str, Rule] = dict(RULES) if extend_library else {}
    for item in spec:
        if isinstance(item, str):
            if extend_library:
                raise PayloadError(f"inline rule entries must be objects, got name {item!r}")
            rule = RULES.get(item)
            if rule is None:
                raise PayloadError(f"unknown rule {item!r}")
        elif isinstance(item, dict):
            try:
                rule = Rule.from_json(item)
            except ValueError as exc:
                raise PayloadError(f"bad inline rule: {exc}") from None
            if extend_library and rule.name in RULES:
                raise PayloadError(f"inline rule {rule.name!r} shadows a library rule")
        else:
            raise PayloadError(f"bad rule entry {item!r}")
        if rule.name in out and not (extend_library and rule.name in RULES):
            raise PayloadError(f"rule {rule.name!r} listed twice")
        out[rule.name] = rule
    return out


def _int(obj: dict[str, Any], key: str, default: int | None, lo: int, hi: int) -> int:
    val = obj.get(key, default)
    if isinstance(val, bool) or not isinstance(val, int):
        raise PayloadError(f"{key!r} must be an integer" + ("" if default is None else
                                                            f" (default {default})"))
    if not lo <= val <= hi:
        raise PayloadError(f"{key!r} must be between {lo} and {hi}, got {val}")
    return val


class _ZXVerifier(BytesFileVerifier):
    name = ""
    version = "1"
    engines: tuple[ModuleType, ...] = ()

    @property
    def binary_hash(self) -> str:
        return module_source_hash(sys.modules[__name__], *self.engines)

    def golden_suite(self) -> list[GoldenCase]:
        return [
            GoldenCase(label, (GOLDEN_DIR / f"{label}.json").read_bytes(), expected)
            for label, expected in GOLDENS[self.name]
        ]

    def verify_bytes(self, payload: bytes) -> VerifierResult:
        try:
            return self._verify(_load_payload(payload))
        except PayloadError as exc:
            return VerifierResult(Verdict.ERROR, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - total: a machinery fault is an ERROR
            return VerifierResult(Verdict.ERROR, {"error": f"{type(exc).__name__}: {exc}"})

    def _verify(self, obj: dict[str, Any]) -> VerifierResult:
        raise NotImplementedError


class ZXDerivationVerifier(_ZXVerifier):
    name = "zx_derivation"
    engines = (diagram, rules, rewrite, derivation)

    def _verify(self, obj: dict[str, Any]) -> VerifierResult:
        rulebook = _rulebook(obj.get("rules"), extend_library=True)
        _diagram(obj.get("start"), "start")
        _diagram(obj.get("end"), "end")
        try:
            d = derivation.Derivation.from_json(obj)
        except ValueError as exc:
            raise PayloadError(str(exc)) from None
        for i, step in enumerate(d.steps):
            if step.rule not in rulebook:
                raise PayloadError(f"step {i}: unknown rule {step.rule!r}")
            if step.direction not in derivation.DIRECTIONS:
                raise PayloadError(f"step {i}: bad direction {step.direction!r}")
        r = derivation.replay(d, rulebook)
        n = len(d.steps)
        if r.failed_step is not None:
            return VerifierResult(Verdict.FAIL, {
                "detail": f"step {r.failed_step} of {n} does not apply: {r.reason}",
                "failed_step": r.failed_step, "reason": r.reason, "steps": n,
            })
        if not r.end_matches:
            return VerifierResult(Verdict.FAIL, {
                "detail": f"all {n} steps apply but reach a diagram that is not the claimed end",
                "failed_step": None, "reason": "end mismatch", "steps": n,
                "reached": r.reached.relabel_canonical().to_json(),
            })
        return VerifierResult(Verdict.PASS, {
            "detail": f"{n} steps replayed; the claimed end is reached", "steps": n,
        })


class ZXSemanticEqualVerifier(_ZXVerifier):
    name = "zx_semantic_equal"
    engines = (diagram, semantics)

    def _verify(self, obj: dict[str, Any]) -> VerifierResult:
        a = _diagram(obj.get("a"), "a")
        b = _diagram(obj.get("b"), "b")
        wires = (len(a.inputs), len(a.outputs))
        if wires != (len(b.inputs), len(b.outputs)):
            return VerifierResult(Verdict.FAIL, {
                "detail": f"wire counts differ: a has {wires}, b has "
                          f"{(len(b.inputs), len(b.outputs))} (inputs, outputs)",
            })
        try:
            ma, mb = semantics.matrix(a), semantics.matrix(b)
        except semantics.SemanticsError as exc:
            raise PayloadError(f"cannot evaluate: {exc}") from None
        equal = semantics.equal_up_to_scalar(ma, mb, semantics.TOLERANCE)
        return VerifierResult(Verdict.PASS if equal else Verdict.FAIL, {
            "detail": ("equal up to a scalar" if equal else "not equal up to any scalar")
                      + f" on {wires[0]} inputs and {wires[1]} outputs",
            "inputs": wires[0], "outputs": wires[1], "tolerance": semantics.TOLERANCE,
        })


class ZXCriticalPairsVerifier(_ZXVerifier):
    name = "zx_critical_pairs"
    engines = (diagram, rules, rewrite, critical_pairs)

    def _verify(self, obj: dict[str, Any]) -> VerifierResult:
        rulebook = _rulebook(obj.get("rules"), extend_library=False)
        depth = _int(obj, "depth", None, 0, MAX_DEPTH)
        star_legs = _int(obj, "star_legs", 1, 0, MAX_STAR_LEGS)
        max_nodes = _int(obj, "max_nodes", critical_pairs.DEFAULT_MAX_NODES, 1, 10 ** 6)
        max_instances = _int(obj, "max_instances", critical_pairs.DEFAULT_MAX_INSTANCES, 1,
                             10 ** 6)
        fragment = obj.get("fragment", "clifford+t")
        if fragment not in FRAGMENTS:
            raise PayloadError(f"'fragment' must be one of {sorted(FRAGMENTS)}")
        try:
            rep = critical_pairs.check(rulebook, depth, star_legs=star_legs,
                                       phases=FRAGMENTS[fragment], max_nodes=max_nodes,
                                       max_instances=max_instances)
        except critical_pairs.CriticalPairError as exc:
            raise PayloadError(f"undecided: {exc}") from None
        common = {"depth": depth, "star_legs": star_legs, "fragment": fragment,
                  "pairs": rep.pairs, "overlaps": rep.overlaps, "case_splits": rep.case_splits,
                  "rules": sorted(rulebook)}
        if rep.failure is not None:
            o, j = rep.failure
            return VerifierResult(Verdict.FAIL, {
                "detail": f"a critical pair of {o.rule1} and {o.rule2} is not joinable within "
                          f"depth {depth}: {j.reason}",
                "rule1": o.rule1, "rule2": o.rule2, "reason": j.reason,
                "overlap": o.to_json(), **common,
            })
        return VerifierResult(Verdict.PASS, {
            "detail": f"all {rep.overlaps} critical pairs of {rep.pairs} rule pairs are joinable "
                      f"within depth {depth} (star vertices with up to {star_legs} context "
                      f"legs of each type; {rep.case_splits} by case split)",
            **common,
        })


class ZXTerminationVerifier(_ZXVerifier):
    name = "zx_termination"
    engines = (diagram, rules, termination)

    def _verify(self, obj: dict[str, Any]) -> VerifierResult:
        rulebook = _rulebook(obj.get("rules"), extend_library=False)
        measure = obj.get("measure")
        if not isinstance(measure, list) or not all(isinstance(c, str) for c in measure):
            raise PayloadError("'measure' must be a list of component names")
        try:
            rep = termination.check(rulebook, measure)
        except termination.TerminationError as exc:
            raise PayloadError(str(exc)) from None
        if rep.failure is not None:
            f = rep.failure
            return VerifierResult(Verdict.FAIL, {
                "detail": f"rule {f.rule} does not decrease the measure: {f.detail}",
                "rule": f.rule, "component": f.component, "reason": f.detail,
                "measure": list(measure), "rules": sorted(rulebook),
            })
        return VerifierResult(Verdict.PASS, {
            "detail": f"every one of {len(rulebook)} rules strictly decreases the lexicographic "
                      f"measure ({', '.join(measure)}) on every instance",
            "measure": list(measure), "rules": sorted(rulebook),
            "deciding": {r.rule: r.component for r in rep.rules},
        })


VERIFIERS: dict[str, type[_ZXVerifier]] = {
    v.name: v for v in (ZXDerivationVerifier, ZXSemanticEqualVerifier, ZXCriticalPairsVerifier,
                        ZXTerminationVerifier)
}


def golden_labels(name: str) -> Sequence[str]:
    return [label for label, _ in GOLDENS[name]]


__all__ = [
    "FRAGMENTS", "GOLDENS", "GOLDEN_DIR", "MAX_DEPTH", "MAX_STAR_LEGS", "VERIFIERS",
    "PayloadError", "ZXCriticalPairsVerifier", "ZXDerivationVerifier",
    "ZXSemanticEqualVerifier", "ZXTerminationVerifier", "golden_labels",
]

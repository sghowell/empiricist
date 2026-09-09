"""The P6 completion campaign (M25b): a model proposes rewrite systems, the pack certifies,
the ledger records.

A candidate is a `SystemOut` -- rules (library names used left-to-right, `{"reverse":
name}` for a library rule turned around, full rule JSON for a new rule, or the name of a
rule an earlier candidate introduced), a termination measure and a joinability depth.
`evaluate` certifies it in cost order with the pack's own verifiers on evidence payloads
written under `claims/evidence/p6/cand_<id>/`: soundness, termination, local confluence at
the stated depth and residual arity, then bounded completeness on every class in turn,
stopping at the first verdict that is not PASS. A candidate is *serious* when its rules are
all sound and its measure orients every rule; only then are claims minted -- a PASS is a
VERIFIED_N claim over the stated class, a non-joinable pair or an incompleteness witness a
REFUTED claim -- and every level is set by `promote` on the verifier's own verdict, never by
anything the model said. An unsound rule or an un-orientable measure is the model's error
(fed back, never a claim); ERROR (a budget) is undecided (fed back, never recorded).

`<id>` is the first 10 hex digits of the sha256 of the canonical rule JSON, so the same rule
set proposed twice, in any order, is one candidate; payloads list the rules in a canonical
order (library order, then inline rules by name), which is the order the completeness
checker applies them in. The prompt is the playbook: the goal, the formulation's semantics,
the library, the measure components (read from the termination module, so a new component
appears by itself), the four checks and their budgets, the seed system with its measured
outcome, and the compact history of every prior candidate with its witness -- fresh context
every round, never a transcript. `run_campaign` drives rounds of `k` nonce-diversified
proposals through the model client, stops on a system passing every check on every class
or on a budget, and logs every round to `run_dir/campaign.jsonl` (from which a resumed run
rebuilds its history).
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from empiricist.claims.model import claim_path, load_claim
from empiricist.claims.promote import PromotionRefused, formulate, promote
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Verdict, now_iso
from empiricist.llm.client import LLMClient
from empiricist.llm.models import LLMResult
from empiricist.llm.roles import ROLES
from empiricist.packs.zx import termination
from empiricist.packs.zx.rules import CLIFFORD_RULES, RULES, Rule
from empiricist.packs.zx.verifiers import (
    MAX_CLASS_EDGES,
    MAX_CLASS_VERTICES,
    MAX_CLASS_WIRES,
    MAX_SOUND_STAR_LEGS,
    VERIFIERS,
)
from empiricist.verifiers.base import VerifierResult

PROBLEM = "P6"
FORMULATION = "p6-zx-v1"
FRAGMENT = "clifford"
EVIDENCE_ROOT = "claims/evidence/p6"
ROLE = "proposer"
MAX_PROPOSED_DEPTH = 6
DEFAULT_STAR_LEGS = 2
DEFAULT_MAX_NODES = 20000
DEFAULT_MAX_INSTANCES = 40000
DEFAULT_MAX_DIAGRAMS = 1_000_000
DEFAULT_MAX_STEPS = 200
DEFAULT_CLASSES: tuple[tuple[int, int, int], ...] = ((2, 2, 4), (2, 2, 6))
PROMPT_BUDGET = 40_000
LOG_NAME = "campaign.jsonl"

Class = tuple[int, int, int]


class InvalidSystem(ValueError):
    """A proposal that cannot be evaluated: an unknown rule name, a malformed inline rule,
    a duplicated name. The model's error, fed back as such."""


# ----------------------------------------------------------------------------- the schema


class SystemOut(BaseModel):
    """One candidate rewrite system, the model's whole output (shape only: the verifiers
    decide everything else)."""

    model_config = ConfigDict(extra="forbid")

    rules: list[str | dict[str, Any]]
    measure: list[str]
    depth: int
    rationale: str

    @field_validator("rules")
    @classmethod
    def _rules(cls, v: list[str | dict[str, Any]]) -> list[str | dict[str, Any]]:
        if not v:
            raise ValueError("a system needs at least one rule")
        return v

    @field_validator("measure")
    @classmethod
    def _measure(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("a measure needs at least one component")
        return v

    @field_validator("depth")
    @classmethod
    def _depth(cls, v: int) -> int:
        if not 1 <= v <= MAX_PROPOSED_DEPTH:
            raise ValueError(f"depth must be between 1 and {MAX_PROPOSED_DEPTH}")
        return v


# ----------------------------------------------------------------------------- the seed

R0CORE: tuple[str, ...] = (
    "fusion", "fusion_x", "identity_z", "identity_x", "identity_z_h", "identity_x_h",
    "identity_z_hh", "identity_x_hh", "loop_z", "loop_x", "loop_z_h", "loop_x_h",
)


def _scalar_rule(kind: str, phase: str, tag: str) -> dict[str, Any]:
    return {
        "name": f"scalar_{kind.lower()}_{tag}",
        "lhs": {"vertices": [[0, kind, phase]], "edges": [], "inputs": [], "outputs": []},
        "rhs": {"vertices": [], "edges": [], "inputs": [], "outputs": []},
        "residual": [],
        "reference": f"a non-zero 0-leg spider ({kind}({phase} pi) = 1 + e^(i {phase} pi)) is "
                     "the empty diagram up to scalar",
    }


SEED_INLINE_RULES: tuple[dict[str, Any], ...] = tuple(
    _scalar_rule(kind, phase, tag)
    for kind in ("Z", "X") for phase, tag in (("0", "0"), ("1/2", "1_2"), ("3/2", "3_2"))
)

SEED = SystemOut(
    rules=[*R0CORE, *SEED_INLINE_RULES],
    measure=["vertices", "edges"],
    depth=4,
    rationale="R0core (fusion, identity removal with 0/1/2 Hadamard legs, self-loop removal) "
              "plus the six scalar eliminations R1 needed: the graph-like normalisation core "
              "with non-zero scalars removed.",
)


# ----------------------------------------------------------------------------- rules


def is_library(rule: Rule) -> bool:
    return RULES.get(rule.name) == rule


def reversed_rule(name: str) -> Rule:
    base = RULES[name]
    rev = base.reversed()
    return Rule(f"{name}_rev", rev.lhs, rev.rhs, rev.residual, f"{base.reference} (reversed)")


def resolve_rules(system: SystemOut, known: Mapping[str, Rule] | None = None) -> list[Rule]:
    """The rules a proposal names, in the model's order: library names forward, `known`
    names (rules earlier candidates introduced), `{"reverse": name}` and full rule JSON.
    Raises `InvalidSystem`."""
    known = known or {}
    out: list[Rule] = []
    seen: set[str] = set()
    for i, item in enumerate(system.rules):
        if isinstance(item, str):
            if item in RULES:
                rule = RULES[item]
            elif item in known:
                rule = known[item]
            else:
                raise InvalidSystem(f"rule {i}: unknown rule name {item!r}")
        elif isinstance(item, dict) and set(item) == {"reverse"}:
            name = item["reverse"]
            if not isinstance(name, str) or name not in RULES:
                raise InvalidSystem(f"rule {i}: cannot reverse unknown library rule {name!r}")
            rule = reversed_rule(name)
        elif isinstance(item, dict):
            try:
                rule = Rule.from_json(item)
            except ValueError as exc:
                raise InvalidSystem(f"rule {i}: bad inline rule: {exc}") from None
            if rule.name in RULES and not is_library(rule):
                raise InvalidSystem(
                    f"rule {i}: inline rule {rule.name!r} shadows a library rule; use another "
                    "name"
                )
        else:
            raise InvalidSystem(f"rule {i}: entries are names, {{\"reverse\": name}} or rule JSON")
        if rule.name in seen:
            raise InvalidSystem(f"rule {rule.name!r} is listed twice")
        seen.add(rule.name)
        out.append(rule)
    return out


def canonical_rule_json(rule: Rule) -> str:
    obj = rule.to_json()
    obj.pop("reference", None)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def candidate_id(system: SystemOut, known: Mapping[str, Rule] | None = None) -> str:
    """First 10 hex digits of the sha256 over the sorted canonical rule JSON: the same
    rule set in any order is one candidate."""
    rules = resolve_rules(system, known)
    blob = json.dumps(sorted(canonical_rule_json(r) for r in rules), separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:10]


def canonical_order(rules: Sequence[Rule]) -> list[Rule]:
    """Library rules in library order, then inline rules by name: the payload order, and
    the order the completeness checker applies rules in."""
    lib = [r for r in rules if is_library(r)]
    lib.sort(key=lambda r: list(RULES).index(r.name))
    inline = sorted((r for r in rules if not is_library(r)), key=lambda r: r.name)
    return [*lib, *inline]


def rules_payload(rules: Sequence[Rule]) -> list[str | dict[str, Any]]:
    return [r.name if is_library(r) else r.to_json() for r in canonical_order(rules)]


def register(registry: dict[str, Rule], keys: dict[str, str], rules: Sequence[Rule]) -> list[str]:
    """Add a candidate's inline rules to the registry of rules usable by name in later
    proposals (the first rule to take a name keeps it; a different rule with the same name
    is keyed `name~<hash>`). Returns the display names of `rules` in canonical order."""
    names: list[str] = []
    for r in canonical_order(rules):
        if is_library(r):
            names.append(r.name)
            continue
        canon = canonical_rule_json(r)
        if canon not in keys:
            key = r.name
            if key in registry or key in RULES:
                key = f"{r.name}~{hashlib.sha256(canon.encode()).hexdigest()[:4]}"
            registry[key] = r
            keys[canon] = key
        names.append(keys[canon])
    return names


# ----------------------------------------------------------------------------- classes


def class_tag(cls: Class) -> str:
    return "c" + "".join(str(x) for x in cls)


def class_name(cls: Class) -> str:
    return f"C({cls[0]}, {cls[1]}, {cls[2]})"


def parse_classes(text: str) -> list[Class]:
    """`"2,2,4;2,2,6"` -> [(2, 2, 4), (2, 2, 6)], each within the verifier's limits."""
    out: list[Class] = []
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        nums = [int(x) for x in part.split(",")]
        if len(nums) != 3:
            raise ValueError(f"a class is w,v,e; got {part!r}")
        w, v, e = nums
        if not (0 <= w <= MAX_CLASS_WIRES and 0 <= v <= MAX_CLASS_VERTICES
                and 0 <= e <= MAX_CLASS_EDGES):
            raise ValueError(
                f"class {part!r} is outside the verifier's limits (wires <= {MAX_CLASS_WIRES}, "
                f"vertices <= {MAX_CLASS_VERTICES}, edges <= {MAX_CLASS_EDGES})"
            )
        out.append((w, v, e))
    if not out:
        raise ValueError("at least one class is needed")
    return out


# ----------------------------------------------------------------------------- payloads


def _payload_file(repo: Path, rel: str, obj: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Write `obj` at `repo/rel` unless a file is already there (a claim may lock it: the
    same candidate re-evaluated reuses the payload its claims rest on). Returns the object
    on disk and whether this call created the file."""
    path = repo / rel
    if path.exists():
        return json.loads(path.read_text("utf-8")), False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return obj, True


def payload_specs(
    cid: str, system: SystemOut, classes: Sequence[Class], *,
    star_legs: int = DEFAULT_STAR_LEGS, max_nodes: int = DEFAULT_MAX_NODES,
    max_instances: int = DEFAULT_MAX_INSTANCES, max_diagrams: int = DEFAULT_MAX_DIAGRAMS,
    max_steps: int = DEFAULT_MAX_STEPS, known: Mapping[str, Rule] | None = None,
) -> list[tuple[str, str, Class | None, str, dict[str, Any]]]:
    """The evaluation plan: (step name, verifier, class or None, repository-relative
    evidence path, payload) per check, in cost order."""
    rules = rules_payload(resolve_rules(system, known))
    base = f"{EVIDENCE_ROOT}/cand_{cid}"
    specs: list[tuple[str, str, Class | None, str, dict[str, Any]]] = [
        ("sound", "zx_rule_sound", None, f"{base}/rules_sound_k{star_legs}.json",
         {"fragment": FRAGMENT, "star_legs": star_legs, "max_instances": max_instances,
          "rules": rules}),
        ("terminates", "zx_termination", None,
         f"{base}/termination_{'_'.join(system.measure)}.json",
         {"rules": rules, "measure": list(system.measure)}),
        (f"locally_confluent_d{system.depth}_k{star_legs}", "zx_critical_pairs", None,
         f"{base}/cp_depth{system.depth}_arity{star_legs}.json",
         {"fragment": FRAGMENT, "depth": system.depth, "star_legs": star_legs,
          "max_nodes": max_nodes, "rules": rules}),
    ]
    for cls in classes:
        specs.append((f"complete_{class_tag(cls)}", "zx_completeness", cls,
                      f"{base}/completeness_{class_tag(cls)}.json",
                      {"fragment": FRAGMENT, "max_wires": cls[0], "max_vertices": cls[1],
                       "max_edges": cls[2], "max_steps": max_steps, "max_diagrams": max_diagrams,
                       "rules": rules}))
    return specs


def write_payloads(
    repo: Path | str, cid: str, system: SystemOut, classes: Sequence[Class], **budgets: Any,
) -> dict[str, str]:
    """One evidence file per check under `claims/evidence/p6/cand_<cid>/` (budgets as for
    `payload_specs`); returns step name -> repository-relative path."""
    repo = Path(repo)
    out: dict[str, str] = {}
    for name, _verifier, _cls, rel, obj in payload_specs(cid, system, classes, **budgets):
        _payload_file(repo, rel, obj)
        out[name] = rel
    return out


# ----------------------------------------------------------------------------- evaluation


@dataclass
class Step:
    name: str                       # the claim suffix
    verifier: str
    verdict: str                    # PASS | FAIL | ERROR
    detail: str
    evidence: str
    witness: dict[str, Any] | None = None
    claim: str | None = None
    level: str | None = None
    n: int | None = None
    seconds: float = 0.0
    problem: str | None = None      # a minting refusal or an already-minted claim

    @property
    def passed(self) -> bool:
        return self.verdict == Verdict.PASS.value


@dataclass
class Evaluation:
    cid: str | None
    system: dict[str, Any] | None
    rules: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    serious: bool = False
    success: bool = False
    claims: list[str] = field(default_factory=list)
    skipped: str | None = None      # why nothing ran: no artifact, invalid schema, duplicate
    round: int = 0
    slot: int = 0
    seconds: float = 0.0

    @property
    def failed_step(self) -> Step | None:
        return next((s for s in self.steps if not s.passed), None)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> Evaluation:
        steps = [Step(**s) for s in obj.get("steps", [])]
        return cls(**{**obj, "steps": steps})


def _witness(verifier: str, r: VerifierResult) -> dict[str, Any] | None:
    d = r.details
    if r.verdict is Verdict.ERROR:
        return {"error": str(d.get("error") or d.get("detail") or "")}
    if r.verdict is Verdict.PASS:
        return None
    if verifier == "zx_rule_sound":
        return {k: d.get(k) for k in ("rule", "bindings", "legs", "reason", "entry",
                                      "lhs_value", "rhs_value", "instance", "result")}
    if verifier == "zx_termination":
        return {k: d.get(k) for k in ("rule", "component", "reason")}
    if verifier == "zx_critical_pairs":
        o = d.get("overlap") or {}
        return {"rule1": d.get("rule1"), "rule2": d.get("rule2"), "reason": d.get("reason"),
                "host": o.get("host"), "result1": o.get("result1"), "result2": o.get("result2")}
    if verifier == "zx_completeness":
        return {k: d.get(k) for k in ("inputs", "outputs", "a", "b", "normal_form_a",
                                      "normal_form_b")}
    return {"detail": str(d.get("detail") or "")}


def _count(verifier: str, r: VerifierResult) -> int | None:
    d = r.details
    if verifier == "zx_rule_sound":
        return int(d.get("instances", 0))
    if verifier == "zx_termination":
        return len(d.get("rules", []))
    if verifier == "zx_critical_pairs":
        return int(d.get("overlaps", 0))
    if verifier == "zx_completeness":
        return int(d.get("diagrams", 0)) - int(d.get("skipped", 0))
    return None


def describe_system(rules: Sequence[Rule], evidence: str) -> str:
    ordered = canonical_order(rules)
    names = ", ".join(r.name for r in ordered)
    inline = [r.name for r in ordered if not is_library(r)]
    s = f"the {len(ordered)}-rule system {{{names}}} (library rules oriented left-to-right"
    if inline:
        s += (f"; the inline rules {', '.join(inline)} are given by their JSON in "
              f"{evidence}")
    return s + ")"


def _statement(step: str, rules: Sequence[Rule], payload: dict[str, Any], evidence: str,
               r: VerifierResult | None, *, cls: Class | None = None) -> str:
    sysd = describe_system(rules, evidence)
    d = r.details if r is not None else {}
    passed = r is not None and r.verdict is Verdict.PASS
    if step == "sound":
        k = payload["star_legs"]
        text = (f"Each rule of {sysd} is a semantic equation up to a non-zero scalar on every "
                f"stabilizer instance with up to {k} residual legs of each type per star vertex "
                f"(formulation {FORMULATION}, section 3), checked exhaustively within "
                f"max_instances = {payload['max_instances']}")
        if passed:
            text += f": {d.get('instances')} instances judged, {d.get('skipped')} skipped."
        return text + ("" if passed else ".")
    if step == "terminates":
        m = ", ".join(payload["measure"])
        return (f"{sysd[0].upper()}{sysd[1:]} is terminating under the lexicographic measure "
                f"({m}) (formulation {FORMULATION}, section 3): every one of its "
                f"{len(rules)} rules strictly decreases the measure on every instance, checked "
                "symbolically over every residual-leg category.")
    if step.startswith("locally_confluent"):
        depth, k = payload["depth"], payload["star_legs"]
        text = (f"{sysd[0].upper()}{sysd[1:]} is locally confluent within depth {depth} at "
                f"residual arity <= {k} over the stabilizer phases (formulation {FORMULATION}, "
                f"section 3): every critical overlap of every pair of its rules, with star "
                f"vertices carrying up to {k} context legs of each type, is joinable within "
                f"{depth} forward steps on each side (search budget max_nodes = "
                f"{payload['max_nodes']})")
        if passed:
            text += (f": {d.get('overlaps')} critical pairs over {d.get('pairs')} rule pairs, "
                     f"{d.get('case_splits')} by case split")
        return text + "."
    assert cls is not None
    w, v, e = cls
    text = (f"{sysd[0].upper()}{sysd[1:]}, applied first-applicable in the listed order, is "
            f"complete for the class {class_name(cls)} of stabilizer diagrams (at most {w} "
            f"boundary wires, {v} interior spiders, {e} edges; formulation {FORMULATION}, "
            f"section 3) within max_steps = {payload['max_steps']} and max_diagrams = "
            f"{payload['max_diagrams']}: every diagram of the class reduces to a normal form "
            "and semantically equal diagrams share one")
    if passed:
        text += (f": {d.get('diagrams')} diagrams ({d.get('skipped')} skipped over the semantic "
                 f"budget), {d.get('classes')} semantic classes, one normal form each, at most "
                 f"{d.get('steps_max')} steps")
    return text + "."


def _mint(repo: Path, cid: str, step: Step, statement: str, notes: str,
          now: str | None) -> None:
    """Formulate `P6.cand_<cid>_<step>` and promote it on the verifier's verdict (PASS ->
    VERIFIED_N, FAIL -> REFUTED); an existing claim is left as it is."""
    claim_id = f"{PROBLEM}.cand_{cid}_{step.name}"
    step.claim = claim_id
    level = "VERIFIED_N" if step.verdict == Verdict.PASS.value else "REFUTED"
    if claim_path(repo, claim_id).exists():
        existing = load_claim(claim_path(repo, claim_id))
        step.level = existing.level
        step.problem = "already minted"
        return
    try:
        formulate(repo, claim_id=claim_id, problem=PROBLEM, formulation_version=FORMULATION,
                  kind="statement", statement=statement, notes=notes, now=now)
        claim = promote(repo, claim_id=claim_id, level=level, verifier=step.verifier,
                        evidence_path=step.evidence, now=now,
                        n=step.n if level == "VERIFIED_N" else None,
                        coverage="exhaustive" if level == "VERIFIED_N" else None)
    except PromotionRefused as exc:
        step.problem = str(exc)
        return
    step.level = claim.level


def evaluate(
    repo: Path | str, system: SystemOut, *, classes: Sequence[Class],
    star_legs: int = DEFAULT_STAR_LEGS, max_nodes: int = DEFAULT_MAX_NODES,
    max_instances: int = DEFAULT_MAX_INSTANCES, max_diagrams: int = DEFAULT_MAX_DIAGRAMS,
    max_steps: int = DEFAULT_MAX_STEPS, registry: dict[str, Rule] | None = None,
    keys: dict[str, str] | None = None, now: str | None = None,
) -> Evaluation:
    """Certify one candidate in cost order and mint its claims (see the module docstring).
    `registry` resolves the names of rules earlier candidates introduced and, with `keys`,
    receives this candidate's inline rules for later proposals."""
    repo = Path(repo)
    t0 = time.perf_counter()
    if not 0 <= star_legs <= MAX_SOUND_STAR_LEGS:
        raise ValueError(f"star_legs must be 0..{MAX_SOUND_STAR_LEGS}")
    reg = registry if registry is not None else {}
    ks = keys if keys is not None else {}
    try:
        rules = resolve_rules(system, reg)
        cid = candidate_id(system, reg)
    except InvalidSystem as exc:
        return Evaluation(cid=None, system=system.model_dump(), skipped=str(exc),
                          seconds=time.perf_counter() - t0)
    names = register(reg, ks, rules)
    ev = Evaluation(cid=cid, system=system.model_dump(), rules=names)
    plan = payload_specs(cid, system, classes, star_legs=star_legs, max_nodes=max_nodes,
                         max_instances=max_instances, max_diagrams=max_diagrams,
                         max_steps=max_steps, known=reg)
    results: dict[str, VerifierResult] = {}
    on_disk: dict[str, dict[str, Any]] = {}
    created: list[Path] = []
    for name, verifier, _cls, rel, obj in plan:
        # Each payload is written when its check runs, so a candidate that stops early
        # leaves no files for checks that never happened.
        on_disk[name], fresh = _payload_file(repo, rel, obj)
        if fresh:
            created.append(repo / rel)
        t1 = time.perf_counter()
        r = VERIFIERS[verifier](repo).run(rel)
        results[name] = r
        detail = str(r.details.get("detail") or r.details.get("error") or "")
        step = Step(name=name, verifier=verifier, verdict=r.verdict.value, detail=detail,
                    evidence=rel, witness=_witness(verifier, r), n=_count(verifier, r),
                    seconds=time.perf_counter() - t1)
        ev.steps.append(step)
        if name == "terminates" and step.passed:
            ev.serious = True          # all rules sound, every rule oriented
        if ev.serious:
            # Claims for every step judged so far without one: the sound and terminates
            # passes the moment the candidate turns serious, then each verdict as it lands.
            for s in ev.steps:
                if s.claim is not None or s.verdict == Verdict.ERROR.value:
                    continue
                step_cls = next(c for n, _, c, _, _ in plan if n == s.name)
                statement = _statement(s.name, rules, on_disk[s.name], s.evidence,
                                       results[s.name], cls=step_cls)
                notes = (f"Minted by the P6 completion campaign (M25b) for candidate "
                         f"cand_{cid}. Verifier: {s.detail}")
                if s.witness and s.verdict == Verdict.FAIL.value:
                    notes += " Witness: " + json.dumps(s.witness, separators=(",", ":"))
                _mint(repo, cid, s, statement, notes, now)
                if s.level is not None:
                    ev.claims.append(s.claim)
        if not step.passed:
            break
    if not ev.serious:
        # The model's error, not a fact about a system: the witness is the record (in the
        # evaluation and the campaign log), the payloads are not evidence of anything.
        for p in created:
            p.unlink(missing_ok=True)
        if created and not any(created[0].parent.iterdir()):
            created[0].parent.rmdir()
    ev.success = ev.serious and all(s.passed for s in ev.steps) and len(ev.steps) == len(plan)
    ev.seconds = time.perf_counter() - t0
    return ev


# ----------------------------------------------------------------------------- the prompt

COMPONENT_NOTES: dict[str, str] = {
    "vertices": "interior spiders",
    "z_vertices": "Z spiders",
    "x_vertices": "X spiders",
    "edges": "edges (with multiplicity, self-loops included)",
    "hadamard_edges": "Hadamard edges",
    "plain_edges": "plain edges",
    "self_loops": "self-loops",
    "phase_vertices": "spiders with a non-zero phase (a symbolic phase counts as [0, 1]: a "
                      "decrease is claimed only when it holds for every grounding)",
    "pi_vertices": "spiders with phase exactly pi (symbolic phases as for phase_vertices)",
}

SEMANTICS = (
    "A diagram is a finite open multigraph: vertices of kind Z (green spider), X (red spider) "
    "or B (boundary, degree 1, listed as inputs and outputs); every spider has a phase in "
    "units of pi (the stabilizer set is 0, 1/2, 1, 3/2); edges are plain or Hadamard, with "
    "self-loops and parallel edges allowed. Diagrams denote matrices by the standard ZX "
    "interpretation and are semantically equal when their matrices agree up to a non-zero "
    "scalar (the zero matrix equals only the zero matrix). A rule is a pair of patterns lhs, "
    "rhs over a shared interface (their B vertices, degree 1 on both sides, listed as outputs "
    "in id order) whose spider phases may be linear expressions in shared variables, plus a "
    "residual map: an LHS interior vertex listed there is a star, allowed to carry host legs "
    "beyond the pattern's own, re-attached to its RHS target with the Hadamard flag toggled "
    "when the target's flip is set. A matching is injective on spiders, maps kinds to kinds, "
    "sends interface vertices anywhere except onto a deleted spider, maps LHS edges to "
    "distinct host edges of the same type, requires a non-star spider's host image to have "
    "exactly the pattern degree, and solves LHS phases for variables with unit coefficient. "
    "A step applies one rule of the system, forward, at one matching. Scalars count: a "
    "zero-leg spider is a scalar (Z(0), Z(1/2), Z(3/2) and the X twins are non-zero; Z(1) and "
    "X(1) are the zero scalar, so any diagram containing one is the zero map) and completeness "
    "needs the non-zero ones removed and every zero diagram of a wire signature reduced to one "
    "normal form."
)


def _compact(obj: Any) -> str:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)


def _outcome_line(ev: Evaluation) -> str:
    if ev.skipped:
        return f"not evaluated: {ev.skipped}"
    if ev.success:
        return "PASSED every check on every class"
    f = ev.failed_step
    if f is None:
        return "no verdict"
    kind = ("UNDECIDED (budget)" if f.verdict == Verdict.ERROR.value
            else "FAILED" if ev.serious or f.name not in ("sound", "terminates")
            else "REJECTED (not serious)")
    passed = [s.name for s in ev.steps if s.passed]
    return (f"{kind} at {f.name} [{f.verifier}]" + (f" after passing {', '.join(passed)}"
                                                    if passed else ""))


def _render_candidate(ev: Evaluation, *, detail: bool) -> str:
    head = f"### round {ev.round} slot {ev.slot}"
    if ev.cid:
        head += f" -- cand_{ev.cid}"
    lines = [head, _outcome_line(ev)]
    if ev.system is not None and ev.rules:
        lines.append(f"rules: {', '.join(ev.rules)}")
        lines.append(f"measure: {', '.join(ev.system['measure'])}; depth: {ev.system['depth']}")
    elif ev.system is not None:
        lines.append("rules as sent: " + _compact(ev.system.get("rules"))[:600])
    f = ev.failed_step
    if f is not None:
        lines.append(f"{f.name}: {f.detail}")
        if detail and f.witness:
            lines.append("witness: " + _compact(f.witness))
    for s in ev.steps:
        if s.claim and s.level:
            lines.append(f"claim {s.claim} -> {s.level}")
    return "\n".join(lines)


def _render_seed(seed: SystemOut, seed_eval: Evaluation | None, seed_names: list[str]) -> str:
    lines = ["## The seed (known good)",
             f"rules: {', '.join(seed_names)}",
             f"measure: {', '.join(seed.measure)}; depth: {seed.depth}",
             f"why: {seed.rationale}"]
    inline = [r for r in resolve_rules(seed) if not is_library(r)]
    if inline:
        lines.append("its inline rules (usable by name):")
        lines.extend(f"{r.name}: {_compact(r.to_json())}" for r in inline)
    if seed_eval is not None and seed_eval.steps:
        lines.append("measured outcome: " + _outcome_line(seed_eval))
        for s in seed_eval.steps:
            lines.append(f"- {s.name}: {s.verdict} -- {s.detail}")
            if s.witness and s.verdict != Verdict.PASS.value:
                lines.append("  witness: " + _compact(s.witness))
    else:
        lines.append("ledger facts: sound at arity <= 2, terminating under (vertices, edges), "
                     "locally confluent within depth 4 at arity <= 2 (2388 critical pairs), "
                     "incomplete for C(2, 1, 2): Z(0) and X(0) with a Hadamard self-loop both "
                     "reduce to a zero scalar (Z(1), X(1)) and stay distinct normal forms.")
    lines.append("also in the ledger: the 24 JPV Clifford rules oriented left-to-right are not "
                 "locally confluent (bialgebra against colour_change, depth 5); adding hopf_h "
                 "to R0core breaks local confluence (hopf_h against identity_z_hh at b=0, depths "
                 "4 and 6); R1 = R0core minus fusion plus colour_change, the six scalar rules, "
                 "two Hadamard-on-a-state rules (a Z(1/2) state with a Hadamard leg is the "
                 "Z(3/2) state with a plain leg, and back) and zero absorption (Z(1) next to a "
                 "Hadamard wire equals Z(1) next to a plain wire) is complete for C(2, 1, 2) "
                 "but zero absorption is not joinable with loop_x_h at depth 4.")
    return "\n".join(lines)


def build_prompt(
    history: Sequence[Evaluation], seed: SystemOut, classes: Sequence[Class], nonce: str, *,
    round_no: int = 1, star_legs: int = DEFAULT_STAR_LEGS, max_nodes: int = DEFAULT_MAX_NODES,
    max_instances: int = DEFAULT_MAX_INSTANCES, max_diagrams: int = DEFAULT_MAX_DIAGRAMS,
    max_steps: int = DEFAULT_MAX_STEPS, max_bytes: int = PROMPT_BUDGET,
) -> str:
    """The playbook for one round: fresh context, the compact history, never a transcript.
    Rendered at decreasing levels of detail until it fits `max_bytes`."""
    registry: dict[str, Rule] = {}
    keys: dict[str, str] = {}
    seed_rules = resolve_rules(seed)
    seed_cid = candidate_id(seed)
    seed_names = register(registry, keys, seed_rules)
    seed_eval = next((e for e in history if e.cid == seed_cid and e.steps), None)
    prior = [e for e in history if e is not seed_eval]
    for e in prior:                     # rebuild the registry in order
        if e.system is not None and not e.skipped:
            try:
                register(registry, keys, resolve_rules(SystemOut.model_validate(e.system),
                                                       registry))
            except (InvalidSystem, ValidationError):
                continue
    cls_text = ", ".join(class_name(c) for c in classes)
    comps = "\n".join(f"- {c}: {COMPONENT_NOTES.get(c, 'see the pack')}"
                      for c in termination.COMPONENTS)
    library = "\n".join(f"{n}: {_compact(RULES[n].to_json())}" for n in CLIFFORD_RULES)
    fixed = [
        f"[nonce {nonce}]",
        f"# P6 completion campaign, round {round_no}: propose one rewrite system",
        "## Goal\n"
        "Problem 6 (ii)(a) asks whether a finite, terminating, confluent rewrite system exists "
        "that is complete for the stabilizer fragment of the ZX-calculus. This campaign attacks "
        f"it bottom-up in the zx pack's own model (formulation {FORMULATION}): you propose a "
        "finite rule set with a termination measure and a joinability depth, and the harness "
        "certifies soundness, termination, local confluence at bounded residual arity and "
        f"completeness on bounded classes, in that order. The target is a system that passes "
        f"all four checks on every class in {cls_text}; every pass becomes a VERIFIED_N claim, "
        "every non-joinable pair or incompleteness witness a REFUTED claim, and the first "
        "failure of each candidate comes back to you as an exact witness.",
        "## The model (formulation p6-zx-v1, sections 1-2)\n" + SEMANTICS,
        "## The library: the 24 Clifford rules, each used left-to-right as written\n" + library
        + "\n\nTo use a library rule turned around write {\"reverse\": \"<name>\"}: the harness "
        "swaps the sides, inverts the residual map and names it <name>_rev. To add a rule give "
        "its full JSON: {\"name\": str, \"lhs\": diagram, \"rhs\": diagram, \"residual\": "
        "[[star, [[target, flip], ...]], ...], \"reference\": str (why it is sound)}. A diagram "
        "is {\"vertices\": [[id, kind, phase]], \"edges\": [[u, v, hadamard]], \"inputs\": [], "
        "\"outputs\": [interface ids in order]} with kind Z, X or B, phases as reduced "
        "fractions of pi (\"0\", \"1/2\", \"1\", \"3/2\") or linear expressions in variables "
        "(\"a\", \"a+b\", \"-a\", \"a+1\"); patterns list their interface as outputs in id order "
        "and every rule's name must be new (a library name is reserved). A rule an earlier "
        "candidate introduced may be reused by the name shown below.",
        "## Measure components (a measure is a lexicographic tuple of these)\n" + comps
        + "\nA rule is oriented when the components, in order, weakly decrease for every "
        "residual-leg configuration up to the first that strictly decreases for every one "
        "(checked symbolically per rule): a rule whose effect on a component depends on its "
        "residual legs must already decrease an earlier component. Every rule of the system "
        "must be oriented by the one measure.",
        "## The four checks, in cost order (the first verdict that is not PASS ends the "
        "evaluation)\n"
        f"1. zx_rule_sound: every rule is an equation up to a non-zero scalar on every "
        f"stabilizer grounding with up to {star_legs} residual legs of each type per star "
        f"(max_instances = {max_instances}). A FAIL is your error: no claim, the rule and the "
        "instance come back.\n"
        "2. zx_termination: every rule strictly decreases your measure on every instance. A "
        "FAIL is your error: no claim, the rule and the component come back.\n"
        f"3. zx_critical_pairs: every critical overlap of every rule pair, with stars carrying "
        f"up to {star_legs} context legs of each type, is joinable within your depth "
        f"(1..{MAX_PROPOSED_DEPTH}) forward steps per side (max_nodes = {max_nodes}). PASS -> "
        "VERIFIED_N; a non-joinable "
        "pair -> REFUTED with the overlap and both results; over budget -> undecided.\n"
        f"4. zx_completeness, for each class in order ({cls_text}): every diagram of the class "
        "reduces (first applicable rule, canonical rule order: library order then inline rules "
        f"by name) within max_steps = {max_steps} and semantically equal diagrams share one "
        f"normal form (max_diagrams = {max_diagrams}). PASS -> VERIFIED_N; a witness pair -> "
        "REFUTED; over budget -> undecided.\n"
        "Claims are minted only for a serious candidate (all rules sound, every rule oriented). "
        "Nothing you write changes a level: only the verifiers do.",
    ]
    seed_text = _render_seed(seed, seed_eval, seed_names)
    task = (
        "## Your task\n"
        "Propose ONE system that addresses the last failure without breaking the earlier "
        "passes (keep what passed; change what failed; a smaller step you can defend beats a "
        "large one you cannot). Emit exactly one SystemOut JSON object: {\"rules\": [<library "
        "name> | {\"reverse\": <library name>} | <rule JSON> | <name of a rule proposed "
        "earlier>], \"measure\": [<components in order>], \"depth\": int 1.."
        f"{MAX_PROPOSED_DEPTH}, \"rationale\": str (why every rule is sound, why the measure "
        "orients every rule, how the last witness is now handled; under 600 characters)}.\n"
        f"nonce: {nonce}"
    )

    def render(detail_last: int, registry_all: bool) -> str:
        parts = [*fixed, seed_text]
        if prior:
            n = len(prior)
            rendered = [_render_candidate(e, detail=(i >= n - detail_last))
                        for i, e in enumerate(prior)]
            parts.append("## Prior candidates (oldest first)\n" + "\n\n".join(rendered))
        used: set[str] = set()
        if not registry_all:
            for e in prior[-max(detail_last, 1):]:
                used.update(e.rules)
        inline = [(k, r) for k, r in registry.items()
                  if k not in seed_names and (registry_all or k in used)]
        if inline:
            parts.append("## Inline rules proposed so far (usable by name)\n"
                         + "\n".join(f"{k}: {_compact(r.to_json())}" for k, r in inline))
        parts.append(task)
        return "\n\n".join(parts)

    for detail_last, registry_all in ((6, True), (3, True), (3, False), (1, False), (0, False)):
        text = render(detail_last, registry_all)
        if len(text.encode("utf-8")) <= max_bytes:
            return text
    return text


# ----------------------------------------------------------------------------- the loop


@dataclass
class CampaignReport:
    rounds: int
    stop_reason: str                # success | budget | rounds | transport_stall
    spent_usd: float
    claims: list[str]
    success: Evaluation | None
    history: list[Evaluation]


def parse_proposal(result: LLMResult | None) -> SystemOut | str:
    """The proposal a model result carries, or the reason it carries none."""
    if result is None or not result.has_artifact:
        return "no artifact (the model produced no schema-valid output)"
    try:
        return SystemOut.model_validate(result.parsed)
    except ValidationError as exc:
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(x) for x in first.get("loc", ()))
        return f"invalid schema: {first.get('msg', str(exc))}" + (f" at {loc}" if loc else "")


def load_history(run_dir: Path | str) -> list[Evaluation]:
    path = Path(run_dir) / LOG_NAME
    if not path.is_file():
        return []
    out: list[Evaluation] = []
    for line in path.read_text("utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("event") in ("seed", "candidate"):
            out.append(Evaluation.from_json(obj["evaluation"]))
    return out


def _log(run_dir: Path, event: str, **fields: Any) -> None:
    with (Path(run_dir) / LOG_NAME).open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now_iso(), "event": event, **fields}, sort_keys=True,
                           separators=(",", ":")) + "\n")


async def run_campaign(
    client: LLMClient, repo: Path | str, run_dir: Path | str, *, max_rounds: int,
    max_cost: float, k: int = 2, classes: Sequence[Class] = DEFAULT_CLASSES,
    seed: SystemOut = SEED, star_legs: int = DEFAULT_STAR_LEGS,
    max_nodes: int = DEFAULT_MAX_NODES, max_instances: int = DEFAULT_MAX_INSTANCES,
    max_diagrams: int = DEFAULT_MAX_DIAGRAMS, max_steps: int = DEFAULT_MAX_STEPS,
    max_empty_rounds: int = 2, now: str | None = None,
) -> CampaignReport:
    """Rounds of `k` proposals until a candidate passes every check on every class, the
    recorded spend in the run directory's ledger reaches `max_cost`, or `max_rounds` rounds
    have run. The seed is evaluated first (no model call) unless the log already has it;
    a duplicate rule set is fed back as such, never re-evaluated. A transport that returns
    no artifact from every call of `max_empty_rounds` consecutive rounds (hung or
    rate-limited calls) stops the run with `transport_stall` rather than spending the round
    budget on nothing."""
    repo, run_dir = Path(repo), Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    role = ROLES[ROLE]
    budgets = dict(star_legs=star_legs, max_nodes=max_nodes, max_instances=max_instances,
                   max_diagrams=max_diagrams, max_steps=max_steps)
    history = load_history(run_dir)
    registry: dict[str, Rule] = {}
    keys: dict[str, str] = {}
    register(registry, keys, resolve_rules(seed))
    for e in history:
        if e.system is not None and not e.skipped:
            try:
                register(registry, keys, resolve_rules(SystemOut.model_validate(e.system),
                                                       registry))
            except (InvalidSystem, ValidationError):
                continue
    seed_cid = candidate_id(seed)
    by_cid: dict[str, Evaluation] = {e.cid: e for e in history if e.cid}
    claims: list[str] = [c for e in history for c in e.claims]
    ledger = Ledger(run_dir / "ledger.db")
    rounds = max((e.round for e in history), default=0)
    stop = "rounds"
    empty_rounds = 0
    winner: Evaluation | None = next((e for e in history if e.success), None)
    try:
        if winner is not None:
            stop = "success"
        while winner is None:
            spent = ledger.spent().cost_usd
            if spent >= max_cost:
                stop = "budget"
                break
            if rounds >= max_rounds:
                stop = "rounds"
                break
            if seed_cid not in by_cid:
                ev = evaluate(repo, seed, classes=classes, registry=registry, keys=keys,
                              now=now, **budgets)
                by_cid[seed_cid] = ev
                history.append(ev)
                claims.extend(ev.claims)
                _log(run_dir, "seed", round=0, evaluation=ev.to_json())
            rounds += 1
            prompts = [build_prompt(history, seed, classes, uuid.uuid4().hex, round_no=rounds,
                                    **budgets) for _ in range(k)]
            results = await client.complete_many(role, prompts, schema=SystemOut, ledger=ledger)
            artifacts = 0
            for slot in range(k):
                result = results[slot] if slot < len(results) else None
                proposal = parse_proposal(result)
                if not (isinstance(proposal, str) and proposal.startswith("no artifact")):
                    artifacts += 1
                if isinstance(proposal, str):
                    ev = Evaluation(cid=None, system=None, skipped=proposal)
                else:
                    try:
                        cid = candidate_id(proposal, registry)
                    except InvalidSystem as exc:
                        cid = None
                        ev = Evaluation(cid=None, system=proposal.model_dump(),
                                        skipped=str(exc))
                    if cid is not None and cid in by_cid:
                        prev = by_cid[cid]
                        ev = Evaluation(
                            cid=cid, system=proposal.model_dump(),
                            rules=list(prev.rules),
                            skipped=f"duplicate of cand_{cid} (round {prev.round} slot "
                                    f"{prev.slot}: {_outcome_line(prev)}); propose a "
                                    "different rule set",
                        )
                    elif cid is not None:
                        ev = evaluate(repo, proposal, classes=classes, registry=registry,
                                      keys=keys, now=now, **budgets)
                        if ev.cid:
                            by_cid[ev.cid] = ev
                ev.round, ev.slot = rounds, slot
                history.append(ev)
                claims.extend(ev.claims)
                _log(run_dir, "candidate", round=rounds, slot=slot, evaluation=ev.to_json())
                if ev.success and winner is None:
                    winner = ev
            spent = ledger.spent().cost_usd
            _log(run_dir, "round", round=rounds, spent_usd=spent, proposals=k,
                 evaluated=sum(1 for e in history if e.round == rounds and not e.skipped),
                 claims_total=len(claims), success=winner is not None)
            if winner is not None:
                stop = "success"
            empty_rounds = empty_rounds + 1 if artifacts == 0 else 0
            if winner is None and empty_rounds >= max_empty_rounds:
                stop = "transport_stall"
                break
        spent = ledger.spent().cost_usd
        _log(run_dir, "stop", reason=stop, rounds=rounds, spent_usd=spent, claims=len(claims),
             winner=winner.cid if winner else None, empty_rounds=empty_rounds)
    finally:
        ledger.close()
    return CampaignReport(rounds=rounds, stop_reason=stop, spent_usd=spent, claims=claims,
                          success=winner, history=history)


__all__ = [
    "DEFAULT_CLASSES", "DEFAULT_MAX_DIAGRAMS", "DEFAULT_MAX_INSTANCES", "DEFAULT_MAX_NODES",
    "DEFAULT_MAX_STEPS", "DEFAULT_STAR_LEGS", "EVIDENCE_ROOT", "FORMULATION", "LOG_NAME",
    "MAX_PROPOSED_DEPTH", "PROBLEM", "PROMPT_BUDGET", "R0CORE", "ROLE", "SEED",
    "SEED_INLINE_RULES", "CampaignReport", "Class", "Evaluation", "InvalidSystem", "Step",
    "SystemOut", "build_prompt", "candidate_id", "canonical_order", "canonical_rule_json",
    "class_name", "class_tag", "describe_system", "evaluate", "is_library", "load_history",
    "parse_classes", "parse_proposal", "payload_specs", "register", "resolve_rules",
    "reversed_rule", "rules_payload", "run_campaign", "write_payloads",
]

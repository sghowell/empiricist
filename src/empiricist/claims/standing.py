"""Standing (charter section 3, absorbed from Lem v3's evidence graph): CURRENT, STALE,
CHALLENGED, SUPERSEDED, derived -- never stored as truth -- from the lock, the
dependency DAG, review receipts and `supersedes`.

- SUPERSEDED: a newer claim names this one in `supersedes` (the row is kept).
- CHALLENGED: a receipt on this claim carries a blocking finding that no later receipt on
  the same claim closes (a receipt cannot close itself, cannot close a receipt of another
  claim, and cannot predate the receipt it closes).
- STALE: an evidence or dependency file's hash differs from the lock, the registry holds
  a newer certified version of a verifier named in the evidence, or a dependency is
  anything but CURRENT (STALE, CHALLENGED, SUPERSEDED, or REFUTED). CURRENT means "every
  dependency is CURRENT" (charter), so non-CURRENT propagates forward as STALE.
- Otherwise CURRENT. Reported precedence when several apply: SUPERSEDED, CHALLENGED, STALE.
`registry_newer` is injected; `check` defaults it to the committed registry.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from empiricist.claims.model import (
    ClaimFile,
    ClaimSchemaError,
    EvidenceEntry,
    Standing,
    is_path_dependency,
    validate_stamp,
)

RECEIPTS_DIRNAME = "receipts"
Dimension = Literal[
    "evidence_support", "assumption_explicitness", "internal_consistency",
    "ledger_consistency", "confidence_calibration", "decision_soundness",
]


class ClaimGraphError(ValueError):
    """The dependency graph is not a DAG over known claim ids."""


def statement_sha256(statement: str) -> str:
    """What a receipt binds to: the exact statement text reviewed."""
    return hashlib.sha256(statement.encode("utf-8")).hexdigest()


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: Dimension
    severity: Literal["note", "warning", "blocking"]
    text: str


class Receipt(BaseModel):
    """One reviewer sample (charter section 3): what was reviewed (statement and evidence
    hashes), the findings per dimension, and the verdict. `closes` names an earlier
    receipt on the same claim whose blocking issue this one resolves."""

    model_config = ConfigDict(extra="forbid")

    id: str
    claim_id: str
    reviewer: str  # model family or human
    statement_sha256: str
    evidence_sha256: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    verdict: Literal["PASS", "REVISE", "BLOCK"]
    closes: str | None = None
    created: str

    @field_validator("created")
    @classmethod
    def _created(cls, v: str) -> str:
        return validate_stamp(v, "created")

    @model_validator(mode="after")
    def _not_self_closing(self) -> Receipt:
        if self.closes == self.id:
            raise ValueError("a receipt cannot close itself")
        return self

    @property
    def blocking(self) -> bool:
        return any(f.severity == "blocking" for f in self.findings)


def receipts_dir(repo: Path | str) -> Path:
    return Path(repo) / RECEIPTS_DIRNAME


def load_receipts(repo: Path | str) -> dict[str, Receipt]:
    out: dict[str, Receipt] = {}
    d = receipts_dir(repo)
    if not d.is_dir():
        return out
    for path in sorted(d.glob("*.json")):
        try:
            r = Receipt.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError) as exc:
            raise ClaimSchemaError(f"{path}: malformed receipt: {exc}") from exc
        if r.id != path.stem:
            raise ClaimSchemaError(f"{path}: receipt id {r.id!r} does not match the filename")
        out[r.id] = r
    return out


def save_receipt(repo: Path | str, receipt: Receipt) -> Path:
    d = receipts_dir(repo)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{receipt.id}.json"
    path.write_text(
        json.dumps(receipt.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def dependency_graph(claims: dict[str, ClaimFile]) -> dict[str, list[str]]:
    """claim id -> claim-id dependencies (path dependencies are the lock's business).
    Unknown ids raise ClaimGraphError."""
    graph: dict[str, list[str]] = {}
    for cid, claim in claims.items():
        deps = [d for d in claim.depends_on if not is_path_dependency(d)]
        for d in deps:
            if d not in claims:
                raise ClaimGraphError(f"{cid} depends on unknown claim {d!r}")
        for s in claim.supersedes:
            if s not in claims:
                raise ClaimGraphError(f"{cid} supersedes unknown claim {s!r}")
        graph[cid] = deps
    return graph


def find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    """A dependency cycle as a list of ids (first == last), or None."""
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = 1
        stack.append(node)
        for nxt in graph.get(node, ()):
            if state.get(nxt, 0) == 1:
                return stack[stack.index(nxt):] + [nxt]
            if state.get(nxt, 0) == 0:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        state[node] = 2
        return None

    for node in graph:
        if state.get(node, 0) == 0:
            found = visit(node)
            if found:
                return found
    return None


def topological_order(graph: dict[str, list[str]]) -> list[str]:
    """Dependencies before dependents; raises ClaimGraphError on a cycle."""
    cycle = find_cycle(graph)
    if cycle:
        raise ClaimGraphError("dependency cycle: " + " -> ".join(cycle))
    order: list[str] = []
    seen: set[str] = set()

    def visit(node: str) -> None:
        if node in seen:
            return
        seen.add(node)
        for d in graph.get(node, ()):
            visit(d)
        order.append(node)

    for node in sorted(graph):
        visit(node)
    return order


def open_blocking_receipts(claim: ClaimFile, receipts: dict[str, Receipt]) -> list[str]:
    """Ids of blocking receipts on `claim` that no later receipt on the same claim closes."""
    mine = {r.id: r for r in receipts.values() if r.claim_id == claim.id}
    closed: set[str] = set()
    for r in mine.values():
        target = mine.get(r.closes) if r.closes else None
        if target is not None and target.id != r.id and r.created >= target.created:
            closed.add(target.id)
    return sorted(rid for rid, r in mine.items() if r.blocking and rid not in closed)


def compute_standing(
    claims: dict[str, ClaimFile],
    lock_mismatches: dict[str, list[str]],
    receipts: dict[str, Receipt] | None = None,
    registry_newer: Callable[[EvidenceEntry], bool] | None = None,
) -> dict[str, Standing]:
    receipts = receipts or {}
    graph = dependency_graph(claims)
    order = topological_order(graph)
    superseded = {s for c in claims.values() for s in c.supersedes}
    noncurrent: set[str] = set()
    out: dict[str, Standing] = {}
    for cid in order:
        claim = claims[cid]
        is_stale = bool(lock_mismatches.get(cid))
        if registry_newer is not None:
            # Only the LATEST PASS per (path, verifier) is the claim's live warrant: a
            # reverify supersedes the entry an older binary produced.
            latest: dict[tuple[str, str], EvidenceEntry] = {}
            for e in claim.evidence:
                if e.verdict == "PASS":
                    latest[(e.path, e.verifier)] = e
            is_stale = is_stale or any(registry_newer(e) for e in latest.values())
        for d in graph[cid]:
            if d in noncurrent or claims[d].level == "REFUTED":
                is_stale = True
        if cid in superseded:
            out[cid] = "SUPERSEDED"
        elif open_blocking_receipts(claim, receipts):
            out[cid] = "CHALLENGED"
        elif is_stale:
            out[cid] = "STALE"
        else:
            out[cid] = "CURRENT"
        if out[cid] != "CURRENT":
            noncurrent.add(cid)
    return out

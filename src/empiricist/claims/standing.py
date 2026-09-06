"""Standing (charter section 3, absorbed from Lem v3's evidence graph): CURRENT, STALE,
CHALLENGED, SUPERSEDED, derived -- never stored as truth -- from the lock, the
dependency DAG, review receipts and `supersedes`.

- SUPERSEDED: a newer claim names this one in `supersedes` (the row is kept).
- CHALLENGED: a receipt with a blocking finding exists that no later receipt closes.
- STALE: an evidence or dependency file's hash differs from the lock, the registry holds
  a newer certified version of a verifier named in the evidence, or a dependency is
  STALE, SUPERSEDED, or REFUTED; STALE propagates forward along `depends_on`.
- Otherwise CURRENT. Reported precedence when several apply: SUPERSEDED, CHALLENGED, STALE.
`registry_newer` is injected (M22b wires the SQLite registry); `check` passes None.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from empiricist.claims.model import (
    ClaimFile,
    ClaimSchemaError,
    EvidenceEntry,
    Standing,
    is_path_dependency,
)

RECEIPTS_DIRNAME = "receipts"
Dimension = Literal[
    "evidence_support", "assumption_explicitness", "internal_consistency",
    "ledger_consistency", "confidence_calibration", "decision_soundness",
]


class ClaimGraphError(ValueError):
    """The dependency graph is not a DAG over known claim ids."""


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: Dimension
    severity: Literal["note", "warning", "blocking"]
    text: str


class Receipt(BaseModel):
    """One reviewer sample (charter section 3): what was reviewed (statement and evidence
    hashes), the findings per dimension, and the verdict. `closes` names an earlier
    receipt whose blocking issue this one resolves."""

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
    """Ids of blocking receipts on `claim` that no receipt closes."""
    mine = [r for r in receipts.values() if r.claim_id == claim.id or r.id in claim.receipts]
    closed = {r.closes for r in mine if r.closes}
    return sorted(r.id for r in mine if r.blocking and r.id not in closed)


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
    stale: set[str] = set()
    out: dict[str, Standing] = {}
    for cid in order:
        claim = claims[cid]
        is_stale = bool(lock_mismatches.get(cid))
        if registry_newer is not None:
            is_stale = is_stale or any(
                e.verdict == "PASS" and registry_newer(e) for e in claim.evidence
            )
        for d in graph[cid]:
            if d in stale or d in superseded or claims[d].level == "REFUTED":
                is_stale = True
        if is_stale:
            stale.add(cid)
        if cid in superseded:
            out[cid] = "SUPERSEDED"
        elif open_blocking_receipts(claim, receipts):
            out[cid] = "CHALLENGED"
        elif is_stale:
            out[cid] = "STALE"
        else:
            out[cid] = "CURRENT"
    return out

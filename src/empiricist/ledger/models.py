"""Ledger model types: statuses, verdicts, rows, and Pareto dominance.

The status lattice is per-claim epistemic strength (spec §4.1), not a
conveyor belt: dataset artifacts enter directly at VERIFIED_N. REFUTED
is terminal. Statuses change only alongside evidence rows (spec §4.2).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from blake3 import blake3


class Status(StrEnum):
    REFUTED = "REFUTED"
    HEURISTIC = "HEURISTIC"
    CONJECTURED = "CONJECTURED"
    VERIFIED_N = "VERIFIED_N"
    CERTIFIED = "CERTIFIED"
    FORMALIZED = "FORMALIZED"

    @property
    def rank(self) -> int:
        """Epistemic strength for comparisons. NEVER order Status with < / max():
        StrEnum compares by string value, which is not epistemic order."""
        return _STATUS_RANK[self]


# REFUTED is terminal, not "weakest": rank orders the live lattice only.
_STATUS_RANK = {
    Status.REFUTED: -1,
    Status.HEURISTIC: 0,
    Status.CONJECTURED: 1,
    Status.VERIFIED_N: 2,
    Status.CERTIFIED: 3,
    Status.FORMALIZED: 4,
}


class Verdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class Budget:
    wall_s: float | None = None
    tokens: int | None = None
    rss_mb: float | None = None


@dataclass(frozen=True)
class Artifact:
    id: str                      # blake3 of canonical content
    kind: str                    # statement|dataset|construction|certificate|proof_dag|lean|report
    problem: str                 # P1..P10 | shared
    title: str
    content_path: str            # CAS digest
    status: Status
    substatus: str | None = None  # PROVED_DRAFT | EXTERNAL | None
    status_n: int | None = None   # iff VERIFIED_N
    coverage: str | None = None   # 'exhaustive' | 'sampled' | None
    created_at: str = field(default_factory=now_iso)
    run_id: str | None = None
    problem_version: str = "legacy"


@dataclass(frozen=True)
class EvidenceRow:
    artifact_id: str
    verifier: str
    verifier_version: str
    binary_hash: str
    verdict: Verdict
    details: dict[str, Any] = field(default_factory=dict)
    log_path: str | None = None
    wall_s: float | None = None
    created_at: str = field(default_factory=now_iso)
    claim_id: str | None = None
    run_id: str | None = None
    golden_suite_hash: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", dict(self.details))


@dataclass(frozen=True)
class Claim:
    """Canonical identity for the exact claim an evidence row checked."""

    id: str
    artifact_id: str
    problem: str
    problem_version: str
    statement: str
    family: str | None = None
    metric: str | None = None
    scope: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        object.__setattr__(self, "scope", dict(self.scope))

    @classmethod
    def create(
        cls,
        *,
        artifact_id: str,
        problem: str,
        problem_version: str,
        statement: str,
        family: str | None = None,
        metric: str | None = None,
        scope: dict[str, Any] | None = None,
    ) -> Claim:
        canonical_scope = dict(scope or {})
        identity = {
            "artifact_id": artifact_id,
            "family": family,
            "metric": metric,
            "problem": problem,
            "problem_version": problem_version,
            "scope": canonical_scope,
            "statement": statement,
        }
        try:
            encoded = json.dumps(
                identity,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"claim identity is not canonical JSON: {exc}") from exc
        return cls(
            id=blake3(encoded).hexdigest(),
            artifact_id=artifact_id,
            problem=problem,
            problem_version=problem_version,
            statement=statement,
            family=family,
            metric=metric,
            scope=canonical_scope,
        )


@dataclass(frozen=True)
class Run:
    run_id: str
    move: str
    role: str | None = None
    model: str | None = None
    argv: str | None = None
    seed: int | None = None
    config_hash: str | None = None
    env_fingerprint: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cache_read: int = 0
    cost_usd: float = 0.0
    peak_rss_mb: float | None = None
    exit_code: int | None = None
    started: str = field(default_factory=now_iso)
    ended: str | None = None
    wall_s: float | None = None
    provider: str | None = None
    reasoning_mode: str | None = None
    reasoning_effort: str | None = None
    auth_route: str | None = None
    request_digest: str | None = None
    response_digest: str | None = None


@dataclass(frozen=True)
class Gate:
    id: str
    kind: str                    # REDUCE|PROOF_CAMPAIGN|ACCEPT_DRAFT|RELEASE
    artifact_id: str
    state: str                   # pending|approved|rejected
    opened_at: str
    resolved_at: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class Certification:
    verifier: str
    verifier_version: str
    binary_hash: str
    golden_suite_hash: str
    verdict: Verdict
    stamped_at: str = field(default_factory=now_iso)
    run_id: str | None = None


def dominates(a: list[float], b: list[float]) -> bool:
    """True iff objective vector `a` Pareto-dominates `b` (minimizing)."""
    if len(a) != len(b):
        raise ValueError(f"objective vectors differ in length: {len(a)} vs {len(b)}")
    return all(x <= y for x, y in zip(a, b, strict=True)) and any(
        x < y for x, y in zip(a, b, strict=True)
    )

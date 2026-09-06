"""`check` (charter section 4): recompute hashes against the lock, validate schemas and the
DAG, propagate STALE, and exit non-zero on any level without matching evidence or any
CURRENT claim resting on a non-CURRENT one. Runs NO verifiers, so it belongs in
pre-commit and CI. Also flags a committed `CLAIMS.md` that differs from the render.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from empiricist.claims.lock import mismatches, read_lock
from empiricist.claims.model import ClaimSchemaError, EvidenceEntry, Standing, load_all
from empiricist.claims.render import claims_md_path, render_claims_md
from empiricist.claims.standing import (
    ClaimGraphError,
    compute_standing,
    dependency_graph,
    find_cycle,
    is_path_dependency,
    load_receipts,
)

BLOCKING_CODES = frozenset({
    "schema_error", "graph_error", "lock_mismatch", "elevated_without_pass",
    "current_on_noncurrent", "claims_md_stale", "stored_standing_differs",
})
TABLE_IMPORT_VERIFIER = "table-import"


class CheckIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    claim_id: str | None = None
    detail: str


class CheckReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: int
    issues: list[CheckIssue] = Field(default_factory=list)
    standings: dict[str, Standing] = Field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not any(i.code in BLOCKING_CODES for i in self.issues)

    @property
    def blocking(self) -> list[CheckIssue]:
        return [i for i in self.issues if i.code in BLOCKING_CODES]


def check(
    repo: Path | str,
    *,
    registry_newer: Callable[[EvidenceEntry], bool] | None = None,
) -> CheckReport:
    repo = Path(repo)
    issues: list[CheckIssue] = []
    try:
        claims = load_all(repo)
    except ClaimSchemaError as exc:
        return CheckReport(claims=0, issues=[CheckIssue(code="schema_error", detail=str(exc))])
    try:
        receipts = load_receipts(repo)
    except ClaimSchemaError as exc:
        return CheckReport(
            claims=len(claims), issues=[CheckIssue(code="schema_error", detail=str(exc))]
        )
    try:
        graph = dependency_graph(claims)
        cycle = find_cycle(graph)
        if cycle:
            raise ClaimGraphError("dependency cycle: " + " -> ".join(cycle))
    except ClaimGraphError as exc:
        return CheckReport(
            claims=len(claims), issues=[CheckIssue(code="graph_error", detail=str(exc))]
        )

    lock = read_lock(repo)
    mism = mismatches(repo, claims, lock)
    for cid, reasons in sorted(mism.items()):
        issues.append(CheckIssue(code="lock_mismatch", claim_id=cid, detail="; ".join(reasons)))
    standings = compute_standing(claims, mism, receipts, registry_newer)

    for cid in sorted(claims):
        c = claims[cid]
        if c.rank > 0 and not any(e.verdict == "PASS" for e in c.evidence):
            issues.append(CheckIssue(
                code="elevated_without_pass", claim_id=cid,
                detail=f"level {c.level} has no PASS evidence entry",
            ))
        if c.level == "REFUTED" and not any(e.verdict == "FAIL" for e in c.evidence):
            issues.append(CheckIssue(
                code="refuted_without_fail", claim_id=cid,
                detail="REFUTED without a FAIL evidence entry",
            ))
        if any(e.verifier == TABLE_IMPORT_VERIFIER for e in c.evidence):
            issues.append(CheckIssue(
                code="imported_unverified", claim_id=cid,
                detail=(
                    "evidence imported from a legacy table; not re-verified by a "
                    "registered verifier"
                ),
            ))
        if standings[cid] == "CURRENT":
            for d in c.depends_on:
                if not is_path_dependency(d) and standings.get(d) != "CURRENT":
                    issues.append(CheckIssue(
                        code="current_on_noncurrent", claim_id=cid,
                        detail=f"depends on {d} which is {standings.get(d)}",
                    ))
        if c.standing != standings[cid]:
            issues.append(CheckIssue(
                code="stored_standing_differs", claim_id=cid,
                detail=f"file says {c.standing}, derived {standings[cid]} (run `claims report`)",
            ))
    md = claims_md_path(repo)
    if md.is_file() and md.read_text(encoding="utf-8") != render_claims_md(claims, standings):
        issues.append(
            CheckIssue(code="claims_md_stale", detail=f"{md.name} differs from the render")
        )
    return CheckReport(claims=len(claims), issues=issues, standings=standings)


def refresh_repo(repo: Path | str, *, registry_newer=None) -> CheckReport:
    """Write derived standings back into the claim files and re-render CLAIMS.md
    (the `report` command). Schema/graph errors are returned, not written around."""
    from empiricist.claims.model import save_claim
    from empiricist.claims.render import write_claims_md

    repo = Path(repo)
    report = check(repo, registry_newer=registry_newer)
    if any(i.code in ("schema_error", "graph_error") for i in report.issues):
        return report
    claims = load_all(repo)
    for cid, st in report.standings.items():
        if claims[cid].standing != st:
            save_claim(repo, claims[cid].model_copy(update={"standing": st}))
    claims = load_all(repo)
    write_claims_md(repo, claims, report.standings)
    return check(repo, registry_newer=registry_newer)

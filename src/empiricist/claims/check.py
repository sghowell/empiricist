"""`check` (charter section 4): recompute hashes against the lock, validate schemas, the DAG
and the receipts, propagate STALE, and exit non-zero on any level without matching
evidence (a PASS from a real verifier above HEURISTIC, a FAIL for REFUTED), any CURRENT
claim resting on a non-CURRENT one, or a receipt that no longer matches the statement it
reviewed. Runs NO verifiers and writes nothing, so it belongs in pre-commit and CI. Also
flags a committed `CLAIMS.md` that differs from the render, or that is not rendered
output at all.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from empiricist.claims.lock import mismatches, read_lock
from empiricist.claims.model import (
    TABLE_IMPORT_VERIFIER,
    ClaimSchemaError,
    EvidenceEntry,
    Standing,
    level_cap,
    load_all,
)
from empiricist.claims.render import claims_md_path, is_rendered, render_claims_md
from empiricist.claims.standing import (
    ClaimGraphError,
    compute_standing,
    dependency_graph,
    find_cycle,
    is_path_dependency,
    load_receipts,
    statement_sha256,
)

BLOCKING_CODES = frozenset({
    "schema_error", "graph_error", "lock_mismatch", "elevated_without_pass",
    "refuted_without_fail", "current_on_noncurrent", "claims_md_stale", "claims_md_legacy",
    "stored_standing_differs", "receipt_missing", "receipt_stale", "receipt_orphan",
    "too_few_claims", "evidence_unidentified", "verifier_declaration_error",
})


def drifted_verifiers(repo: Path | str) -> tuple[set[str], list[tuple[str, str]]]:
    """Command verifiers whose declaration or hashed inputs on disk no longer match their
    registry stamp (their evidence is STALE until `certify-verifier` + `reverify`), plus
    (name, error) for declarations that do not load. Pure: hashing only."""
    from empiricist.claims.command_verifier import declared_verifiers
    from empiricist.claims.registry import read_registry

    reg = read_registry(repo)
    verifiers, errors = declared_verifiers(repo)
    drifted: set[str] = set()
    for name, v in verifiers.items():
        s = reg.stamps.get(name)
        if s is None:
            continue
        try:
            current = v.binary_hash
        except ClaimSchemaError as exc:
            errors.append((name, str(exc)))
            continue
        if s.version != v.version or s.binary_hash != current:
            drifted.add(name)
    return drifted, errors


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


def _real_pass(e: EvidenceEntry) -> bool:
    return e.verdict == "PASS" and e.verifier != TABLE_IMPORT_VERIFIER


def check(
    repo: Path | str,
    *,
    registry_newer: Callable[[EvidenceEntry], bool] | None = None,
    min_claims: int = 0,
) -> CheckReport:
    repo = Path(repo)
    issues: list[CheckIssue] = []
    try:
        claims = load_all(repo)
    except ClaimSchemaError as exc:
        return CheckReport(claims=0, issues=[CheckIssue(code="schema_error", detail=str(exc))])
    if len(claims) < min_claims:
        issues.append(CheckIssue(
            code="too_few_claims", detail=f"{len(claims)} claim(s), expected at least {min_claims}"
        ))
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
    if registry_newer is None:
        from empiricist.claims.registry import registry_newer as _from_registry

        drifted, decl_errors = drifted_verifiers(repo)
        for name, err in decl_errors:
            issues.append(CheckIssue(code="verifier_declaration_error", detail=f"{name}: {err}"))
        for name in sorted(drifted):
            issues.append(CheckIssue(
                code="verifier_drift",
                detail=(
                    f"command verifier {name}: declaration or inputs changed since its stamp; "
                    "its evidence is STALE until `certify-verifier` and `reverify`"
                ),
            ))
        registry_newer = _from_registry(repo, drifted=drifted)
    standings = compute_standing(claims, mism, receipts, registry_newer)

    for cid in sorted(claims):
        c = claims[cid]
        if c.rank > 0 and not any(_real_pass(e) for e in c.evidence):
            issues.append(CheckIssue(
                code="elevated_without_pass", claim_id=cid,
                detail=f"level {c.level} has no PASS evidence entry from a verifier",
            ))
        for e in c.evidence:
            if e.verdict == "PASS" and e.verifier != TABLE_IMPORT_VERIFIER and not e.binary_hash:
                issues.append(CheckIssue(
                    code="evidence_unidentified", claim_id=cid,
                    detail=f"PASS from {e.verifier} on {e.path} names no binary_hash",
                ))
                break
        if c.level == "REFUTED" and not any(e.verdict == "FAIL" for e in c.evidence):
            issues.append(CheckIssue(
                code="refuted_without_fail", claim_id=cid,
                detail="REFUTED without a FAIL evidence entry",
            ))
        if c.legacy_pending:
            issues.append(CheckIssue(
                code="imported_unverified", claim_id=cid,
                detail=(
                    f"imported from a legacy table at {c.legacy_level}; held at {c.level} "
                    "until `promote` re-verifies it"
                ),
            ))
        for rid in c.receipts:
            r = receipts.get(rid)
            if r is None:
                issues.append(CheckIssue(
                    code="receipt_missing", claim_id=cid, detail=f"receipt {rid} is not on disk"
                ))
            elif r.claim_id != cid:
                issues.append(CheckIssue(
                    code="receipt_stale", claim_id=cid,
                    detail=f"receipt {rid} belongs to {r.claim_id}",
                ))
            elif r.statement_sha256 != statement_sha256(c.statement):
                issues.append(CheckIssue(
                    code="receipt_stale", claim_id=cid,
                    detail=f"receipt {rid} reviewed a different statement",
                ))
        cap, limiting = level_cap(c, claims)
        if c.rank > cap and limiting is not None:
            issues.append(CheckIssue(
                code="level_inversion", claim_id=cid,
                detail=(
                    f"level {c.level} is above dependency {limiting} at "
                    f"{claims[limiting].level}; promote refuses to widen this (a human "
                    "receipt may waive level_inversion)"
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
    for rid in sorted(receipts):
        if receipts[rid].claim_id not in claims:
            issues.append(CheckIssue(
                code="receipt_orphan", claim_id=None,
                detail=f"receipt {rid} names unknown claim {receipts[rid].claim_id!r}",
            ))
    md = claims_md_path(repo)
    if md.is_file():
        text = md.read_text(encoding="utf-8")
        if not is_rendered(text):
            issues.append(CheckIssue(
                code="claims_md_legacy",
                detail=(
                    f"{md.name} is not rendered output; import it, then run "
                    "`claims report --force` once to replace it"
                ),
            ))
        elif text != render_claims_md(claims, standings):
            issues.append(
                CheckIssue(code="claims_md_stale", detail=f"{md.name} differs from the render")
            )
    return CheckReport(claims=len(claims), issues=issues, standings=standings)


def refresh_repo(
    repo: Path | str, *, registry_newer=None, force: bool = False
) -> CheckReport:
    """Write derived standings back into the claim files and re-render CLAIMS.md (the
    `report` command). Schema/graph errors are returned, not written around; a legacy
    (non-rendered) CLAIMS.md is replaced only with `force`."""
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
    write_claims_md(repo, claims, report.standings, force=force)
    return check(repo, registry_newer=registry_newer)

"""`review` (charter section 4): write a review receipt for a claim -- a recorded human
review here; the model reviewer (fresh context, bounty framing, two samples for elevated
promotions) is `review_with_model` in the same module (Task 3).

A receipt binds to what was reviewed: the sha256 of the claim's statement and of its
evidence files at review time. `promote` accepts a receipt only for the same statement
and with no blocking finding; `check` flags a receipt whose statement no longer matches.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from empiricist.claims.check import refresh_repo
from empiricist.claims.lock import committed_file, sha256_file
from empiricist.claims.model import LEVEL_RANK, load_all
from empiricist.claims.standing import (
    Finding,
    Receipt,
    load_receipts,
    new_receipt_id,
    save_receipt,
    statement_sha256,
)


class ReviewRefused(Exception):
    """The review could not be recorded; the message says why."""


def parse_finding(text: str) -> Finding:
    """`dimension:severity:free text` -> Finding (CLI form)."""
    parts = text.split(":", 2)
    if len(parts) != 3:
        raise ReviewRefused(f"finding {text!r} must be dimension:severity:text")
    dim, sev, body = (x.strip() for x in parts)
    try:
        return Finding(dimension=dim, severity=sev, text=body)  # type: ignore[arg-type]
    except ValueError as exc:
        raise ReviewRefused(f"finding {text!r}: {exc}") from exc


def evidence_hashes(repo: Path, claim) -> list[str]:
    out: list[str] = []
    for path in dict.fromkeys(e.path for e in claim.evidence):
        f = committed_file(repo, path)
        if f is not None:
            out.append(sha256_file(f))
    return sorted(out)


def _now(now: str | None) -> str:
    return now or datetime.now(UTC).isoformat(timespec="seconds")


def record_human_review(
    repo: Path | str,
    *,
    claim_id: str,
    reviewer: str,
    verdict: str,
    findings: list[Finding] | None = None,
    closes: str | None = None,
    target_level: str | None = None,
    now: str | None = None,
) -> Receipt:
    """Write `receipts/<id>.json` for a human review and refresh the derived standings."""
    repo = Path(repo)
    claims = load_all(repo)
    if claim_id not in claims:
        raise ReviewRefused(f"claim {claim_id!r} does not exist")
    if target_level is not None and target_level not in LEVEL_RANK:
        raise ReviewRefused(f"unknown level {target_level!r}")
    claim = claims[claim_id]
    receipts = load_receipts(repo)
    if closes is not None:
        target = receipts.get(closes)
        if target is None or target.claim_id != claim_id:
            raise ReviewRefused(f"{closes!r} is not a receipt of {claim_id}")
    created = _now(now)
    rid = new_receipt_id(claim_id, reviewer, created, set(receipts))
    try:
        receipt = Receipt(
            id=rid, claim_id=claim_id, reviewer=reviewer,
            statement_sha256=statement_sha256(claim.statement),
            evidence_sha256=evidence_hashes(repo, claim),
            findings=list(findings or []), verdict=verdict,  # type: ignore[arg-type]
            closes=closes, created=created, target_level=target_level,  # type: ignore[arg-type]
        )
    except ValueError as exc:
        raise ReviewRefused(str(exc)) from exc
    save_receipt(repo, receipt)
    refresh_repo(repo)
    return receipt

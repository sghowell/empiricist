"""`formulate`, `promote`, `reverify`, `demote` -- the one promotion path (charter section 4).

`promote` is the only way a level rises, in both modes. It checks the verifier's stamp in
the committed registry, runs the verifier on the evidence, requires PASS, requires a
matching receipt for elevated promotions of `statement` claims, requires every
dependency CURRENT, then writes the evidence entry, the lock, the level, and the rendered
table -- or refuses with a reason (`PromotionRefused`). Nothing here trusts a caller's
verdict: the verifier runs inside `promote`.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from empiricist.claims.check import check, refresh_repo
from empiricist.claims.command_verifier import load_command_verifier
from empiricist.claims.lock import mismatches, read_lock, refresh_lock_entries, write_lock
from empiricist.claims.model import (
    LEVEL_RANK,
    ClaimFile,
    ClaimSchemaError,
    EvidenceEntry,
    claim_path,
    is_path_dependency,
    load_all,
    load_claim,
    save_claim,
    validate_repo_relative,
)
from empiricist.claims.registry import current_stamp, registry_newer
from empiricist.claims.standing import load_receipts
from empiricist.ledger.models import Verdict

ELEVATED = frozenset({"CERTIFIED", "FORMALIZED"})


class PromotionRefused(Exception):
    """`promote`/`demote` refused; the message is the reason recorded nowhere else."""


def _today(now: str | None) -> str:
    return now or datetime.now(UTC).date().isoformat()


def _stamp_iso(now: str | None) -> str:
    return now or datetime.now(UTC).isoformat(timespec="seconds")


def statement_sha256(statement: str) -> str:
    return hashlib.sha256(statement.encode("utf-8")).hexdigest()


def formulate(
    repo: Path | str,
    *,
    claim_id: str,
    problem: str,
    formulation_version: str,
    kind: str,
    statement: str,
    depends_on: list[str] | None = None,
    notes: str = "",
    now: str | None = None,
) -> ClaimFile:
    """Freeze a statement as a HEURISTIC claim file. Refuses an existing id."""
    repo = Path(repo)
    if claim_path(repo, claim_id).exists():
        raise PromotionRefused(f"claim {claim_id!r} already exists; promote it instead")
    claim = ClaimFile(
        id=claim_id, problem=problem, formulation_version=formulation_version, kind=kind,
        statement=statement, level="HEURISTIC", depends_on=list(depends_on or []),
        notes=notes, updated=_today(now),
    )
    existing = load_all(repo)
    for d in claim.depends_on:
        if not is_path_dependency(d) and d not in existing:
            raise PromotionRefused(f"dependency {d!r} is not a known claim")
    save_claim(repo, claim)
    refresh_repo(repo, registry_newer=registry_newer(repo))
    return load_claim(claim_path(repo, claim_id))


def _resolve_verifier(repo: Path, verifier: Any):
    if isinstance(verifier, str):
        return load_command_verifier(repo, verifier)
    return verifier


def promote(
    repo: Path | str,
    *,
    claim_id: str,
    level: str,
    verifier: Any,
    evidence_path: str,
    receipt_id: str | None = None,
    n: int | None = None,
    coverage: str | None = None,
    substatus: str | None = None,
    now: str | None = None,
    run_id: str | None = None,
) -> ClaimFile:
    """Raise `claim_id` to `level` on the strength of `verifier` run on `evidence_path`.

    `verifier` is a command-verifier name (declared under `claims/verifiers/`) or any
    object with `name`, `version`, `binary_hash` and `run(evidence_path) -> VerifierResult`.
    """
    repo = Path(repo)
    if level not in LEVEL_RANK:
        raise PromotionRefused(f"unknown level {level!r}")
    try:
        validate_repo_relative(evidence_path)
    except ValueError as exc:
        raise PromotionRefused(str(exc)) from exc
    claims = load_all(repo)
    if claim_id not in claims:
        raise PromotionRefused(f"claim {claim_id!r} does not exist; formulate it first")
    claim = claims[claim_id]
    if level != "REFUTED" and LEVEL_RANK[level] < claim.rank:
        raise PromotionRefused(
            f"{claim_id} is {claim.level}; a level only goes down through demote"
        )
    if claim.level == "REFUTED":
        raise PromotionRefused(f"{claim_id} is REFUTED (terminal)")
    v = _resolve_verifier(repo, verifier)
    stamp = current_stamp(repo, v.name)
    if stamp is None or stamp.version != v.version or stamp.binary_hash != v.binary_hash:
        raise PromotionRefused(
            f"verifier {v.name} v{v.version} [{v.binary_hash[:12]}] has no current stamp in "
            "claims/verifiers.json; certify it first"
        )
    # Dependencies must be CURRENT (derived now, not read from the files).
    report = check(repo, registry_newer=registry_newer(repo))
    if any(i.code in ("schema_error", "graph_error") for i in report.issues):
        raise PromotionRefused("repository does not check: " + report.issues[0].detail)
    for d in claim.depends_on:
        if not is_path_dependency(d) and report.standings.get(d) != "CURRENT":
            raise PromotionRefused(
                f"dependency {d} is {report.standings.get(d)}; only CURRENT claims can be "
                "built on"
            )
    if not (repo / evidence_path).is_file():
        raise PromotionRefused(f"evidence {evidence_path} is not a committed file")
    # Receipt for elevated statement claims.
    receipt = None
    if level in ELEVATED and claim.kind == "statement":
        if receipt_id is None:
            raise PromotionRefused(
                f"promotion of a statement claim to {level} requires a review receipt"
            )
        receipts = load_receipts(repo)
        receipt = receipts.get(receipt_id)
        if receipt is None or receipt.claim_id != claim_id:
            raise PromotionRefused(f"receipt {receipt_id!r} is not a receipt for {claim_id}")
        if receipt.statement_sha256 != statement_sha256(claim.statement):
            raise PromotionRefused(f"receipt {receipt_id} reviewed a different statement")
        if receipt.blocking or receipt.verdict == "BLOCK":
            raise PromotionRefused(f"receipt {receipt_id} has a blocking finding")
    # The verifier runs HERE; the caller's opinion of the evidence is not evidence.
    result = v.run(evidence_path)
    want = Verdict.FAIL if level == "REFUTED" else Verdict.PASS
    note = f"argv={result.details.get('argv')} cwd={result.details.get('cwd')}"
    if run_id:
        note += f" run={run_id}"
    entry = EvidenceEntry(
        path=evidence_path, verifier=v.name, version=v.version, verdict=result.verdict.value,
        stamped=_stamp_iso(now), binary_hash=v.binary_hash,
        golden_suite_hash=stamp.golden_suite_hash, note=note,
    )
    if result.verdict is not want:
        # Record the honest outcome without moving the level.
        claim = claim.model_copy(update={"evidence": [*claim.evidence, entry]})
        save_claim(repo, claim)
        lock = refresh_lock_entries(repo, claim, read_lock(repo))
        write_lock(repo, lock)
        refresh_repo(repo, registry_newer=registry_newer(repo))
        raise PromotionRefused(
            f"verifier {v.name} returned {result.verdict.value}, not {want.value}: "
            f"{result.details.get('detail') or result.details.get('error') or ''}".strip()
        )
    update: dict[str, Any] = {
        "level": level, "evidence": [*claim.evidence, entry], "updated": _today(now),
        "n": n if level == "VERIFIED_N" else None,
        "coverage": coverage if level == "VERIFIED_N" else None,
        "substatus": substatus,
    }
    if receipt is not None and receipt_id not in claim.receipts:
        update["receipts"] = [*claim.receipts, receipt_id]
    try:
        claim = claim.model_copy(update=update)
        ClaimFile.model_validate(claim.model_dump())
    except (ValueError, ClaimSchemaError) as exc:
        raise PromotionRefused(f"resulting claim is invalid: {exc}") from exc
    save_claim(repo, claim)
    lock = refresh_lock_entries(repo, claim, read_lock(repo))
    write_lock(repo, lock)
    refresh_repo(repo, registry_newer=registry_newer(repo))
    return load_claim(claim_path(repo, claim_id))


def reverify(
    repo: Path | str,
    *,
    claim_id: str | None = None,
    verifiers: dict[str, Any] | None = None,
    now: str | None = None,
) -> dict[str, str]:
    """Re-run every PASS evidence entry's verifier for the named claim, or for every
    STALE claim. Command verifiers are resolved by name from `claims/verifiers/`;
    `verifiers` supplies objects for other names. Returns id -> outcome text; a
    claim returns to CURRENT only when every entry passes again."""
    repo = Path(repo)
    newer = registry_newer(repo)
    claims = load_all(repo)
    lock = read_lock(repo)
    if claim_id:
        targets = [claim_id]
    else:
        # Only claims STALE for their own reasons (lock drift, newer verifier) have
        # anything to re-run; propagated staleness clears when its source does.
        own = set(mismatches(repo, claims, lock))
        own |= {c.id for c in claims.values()
                if any(e.verdict == "PASS" and newer(e) for e in c.evidence)}
        targets = sorted(own)
    outcomes: dict[str, str] = {}
    for cid in targets:
        if cid not in claims:
            outcomes[cid] = "unknown claim"
            continue
        claim = claims[cid]
        fresh: list[EvidenceEntry] = []
        failed = False
        for e in claim.evidence:
            if e.verdict != "PASS":
                continue
            v = (verifiers or {}).get(e.verifier)
            if v is None:
                try:
                    v = load_command_verifier(repo, e.verifier)
                except ClaimSchemaError:
                    outcomes[cid] = f"no verifier available for {e.verifier}"
                    failed = True
                    break
            stamp = current_stamp(repo, v.name)
            if stamp is None or stamp.binary_hash != v.binary_hash:
                outcomes[cid] = f"verifier {v.name} has no current stamp"
                failed = True
                break
            r = v.run(e.path)
            fresh.append(EvidenceEntry(
                path=e.path, verifier=v.name, version=v.version, verdict=r.verdict.value,
                stamped=_stamp_iso(now), binary_hash=v.binary_hash,
                golden_suite_hash=stamp.golden_suite_hash,
                note=f"reverify; argv={r.details.get('argv')}",
            ))
            if r.verdict is not Verdict.PASS:
                failed = True
        if fresh:
            claim = claim.model_copy(update={"evidence": [*claim.evidence, *fresh],
                                             "updated": _today(now)})
            save_claim(repo, claim)
            if not failed:
                lock = refresh_lock_entries(repo, claim, lock)
        outcomes.setdefault(cid, "re-verified" if fresh and not failed else "still failing")
    write_lock(repo, lock)
    refresh_repo(repo, registry_newer=registry_newer(repo))
    return outcomes


def demote(
    repo: Path | str,
    *,
    claim_id: str,
    level: str,
    receipt_id: str,
    reason: str,
    now: str | None = None,
) -> ClaimFile:
    """Lower a level; the reason lives in a receipt (charter section 3)."""
    repo = Path(repo)
    claims = load_all(repo)
    if claim_id not in claims:
        raise PromotionRefused(f"claim {claim_id!r} does not exist")
    claim = claims[claim_id]
    if level not in LEVEL_RANK or LEVEL_RANK[level] >= claim.rank:
        raise PromotionRefused(f"demote must lower the level ({claim.level} -> {level})")
    receipts = load_receipts(repo)
    if receipt_id not in receipts or receipts[receipt_id].claim_id != claim_id:
        raise PromotionRefused(f"receipt {receipt_id!r} is not a receipt for {claim_id}")
    update: dict[str, Any] = {
        "level": level, "updated": _today(now),
        "notes": (claim.notes + "\n" if claim.notes else "") + f"demoted to {level}: {reason}",
        "n": None if level != "VERIFIED_N" else claim.n,
        "coverage": None if level != "VERIFIED_N" else claim.coverage,
        "substatus": None,
    }
    if receipt_id not in claim.receipts:
        update["receipts"] = [*claim.receipts, receipt_id]
    save_claim(repo, claim.model_copy(update=update))
    refresh_repo(repo, registry_newer=registry_newer(repo))
    return load_claim(claim_path(repo, claim_id))

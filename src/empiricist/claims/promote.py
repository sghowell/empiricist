"""`formulate`, `promote`, `reverify`, `demote` -- the one promotion path (charter section 4).

`promote` is the only way a level rises, in both modes. It checks the verifier's stamp in
the committed registry (version, binary hash AND fixtures), requires the claim itself
and every dependency to be CURRENT (STALE goes through `reverify`, CHALLENGED through a
closing receipt), requires every file the lock will cover to be a committed regular
file, requires a matching receipt for elevated promotions of `statement` claims and for
refutations of anything at CONJECTURED or above, runs the verifier on the evidence,
requires PASS (a declared FAIL exit for REFUTED), then writes the lock, the evidence
entry, the level, and the rendered table -- or refuses with a reason
(`PromotionRefused`). Nothing here trusts a caller's verdict: the verifier runs inside
`promote`.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from empiricist.claims.check import check, drifted_verifiers, refresh_repo
from empiricist.claims.command_verifier import golden_suite_hash, load_command_verifier
from empiricist.claims.lock import (
    committed_file,
    lock_paths_for,
    mismatches,
    read_lock,
    refresh_lock_entries,
    sha256_file,
    write_lock,
)
from empiricist.claims.model import (
    LEVEL_RANK,
    ClaimFile,
    ClaimSchemaError,
    EvidenceEntry,
    claim_path,
    is_path_dependency,
    level_cap,
    load_all,
    load_claim,
    revalidate,
    save_claim,
    validate_repo_relative,
)
from empiricist.claims.registry import current_stamp, registry_newer
from empiricist.claims.standing import (
    load_receipts,
    open_blocking_receipts,
    statement_sha256,
)
from empiricist.ledger.models import Verdict

ELEVATED = frozenset({"CERTIFIED", "FORMALIZED"})


class PromotionRefused(Exception):
    """`promote`/`demote`/`formulate` refused; the message is the reason."""


def _today(now: str | None) -> str:
    return now or datetime.now(UTC).date().isoformat()


def _stamp_iso(now: str | None) -> str:
    return now or datetime.now(UTC).isoformat(timespec="seconds")


def _committed_or_refuse(repo: Path, path: str, what: str) -> Path:
    f = committed_file(repo, path)
    if f is None:
        raise PromotionRefused(
            f"{what} {path} is not a committed regular file (missing, a symlink, or outside "
            "the repository)"
        )
    return f


def _evidence_hashes(repo: Path, paths: list[str]) -> set[str]:
    out: set[str] = set()
    for p in dict.fromkeys(paths):
        f = committed_file(repo, p)
        if f is not None:
            out.add(sha256_file(f))
    return out


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
    """Freeze a statement as a HEURISTIC claim file (path dependencies are locked now).
    Refuses an existing id or an unknown claim dependency."""
    repo = Path(repo)
    if claim_path(repo, claim_id).exists():
        raise PromotionRefused(f"claim {claim_id!r} already exists; promote it instead")
    try:
        claim = ClaimFile(
            id=claim_id, problem=problem, formulation_version=formulation_version, kind=kind,
            statement=statement, level="HEURISTIC", depends_on=list(depends_on or []),
            notes=notes, updated=_today(now),
        )
    except ValueError as exc:
        raise PromotionRefused(f"invalid claim: {exc}") from exc
    existing = load_all(repo)
    for d in claim.depends_on:
        if is_path_dependency(d):
            _committed_or_refuse(repo, d, "dependency")
        elif d not in existing:
            raise PromotionRefused(f"dependency {d!r} is not a known claim")
    lock = refresh_lock_entries(repo, claim, read_lock(repo))
    save_claim(repo, claim)
    write_lock(repo, lock)
    refresh_repo(repo)
    return load_claim(claim_path(repo, claim_id))


def _resolve_verifier(repo: Path, verifier: Any):
    if isinstance(verifier, str):
        return load_command_verifier(repo, verifier)
    return verifier


def _require_current_stamp(repo: Path, v: Any):
    stamp = current_stamp(repo, v.name)
    if stamp is None or stamp.version != v.version or stamp.binary_hash != v.binary_hash:
        raise PromotionRefused(
            f"verifier {v.name} v{v.version} [{v.binary_hash[:12]}] has no current stamp in "
            "claims/verifiers.json; certify it first"
        )
    spec = getattr(v, "spec", None)
    if spec is not None and golden_suite_hash(repo, spec) != stamp.golden_suite_hash:
        raise PromotionRefused(
            f"verifier {v.name}: its fixtures changed since certification; run "
            "certify-verifier again"
        )
    return stamp


def _note(result, run_id: str | None) -> str:
    d = result.details
    note = (
        f"argv={d.get('argv')} cwd={d.get('cwd')} exit={d.get('exit_code')} "
        f"env_sha256={d.get('env_sha256')}"
    )
    if result.verdict is not Verdict.PASS:
        why = d.get("error") or d.get("detail") or d.get("stderr_tail") or ""
        note += f" reason={str(why)[-300:]!r}"
    if run_id:
        note += f" run={run_id}"
    return note


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
        evidence_path = validate_repo_relative(evidence_path)
    except ValueError as exc:
        raise PromotionRefused(str(exc)) from exc
    claims = load_all(repo)
    if claim_id not in claims:
        raise PromotionRefused(f"claim {claim_id!r} does not exist; formulate it first")
    claim = claims[claim_id]
    if claim.level == "REFUTED":
        raise PromotionRefused(f"{claim_id} is REFUTED (terminal)")
    if level != "REFUTED" and LEVEL_RANK[level] < claim.rank:
        raise PromotionRefused(
            f"{claim_id} is {claim.level}; a level only goes down through demote"
        )
    v = _resolve_verifier(repo, verifier)
    stamp = _require_current_stamp(repo, v)
    # The claim and everything it rests on must be CURRENT (derived now, not read
    # from the files); STALE returns to CURRENT only through reverify.
    report = check(repo)
    if any(i.code in ("schema_error", "graph_error") for i in report.issues):
        raise PromotionRefused("repository does not check: " + report.issues[0].detail)
    own = report.standings.get(claim_id)
    if own == "CHALLENGED":
        open_ids = open_blocking_receipts(claim, load_receipts(repo))
        raise PromotionRefused(
            f"{claim_id} is CHALLENGED by blocking receipt(s) {', '.join(open_ids)}; a later "
            "receipt must close them first"
        )
    if own == "SUPERSEDED":
        raise PromotionRefused(f"{claim_id} is SUPERSEDED; promote the superseding claim")
    for d in claim.depends_on:
        if not is_path_dependency(d) and report.standings.get(d) != "CURRENT":
            raise PromotionRefused(
                f"dependency {d} is {report.standings.get(d)}; only CURRENT claims can be "
                "built on"
            )
    own = report.standings.get(claim_id)
    if own == "CHALLENGED":
        open_ids = open_blocking_receipts(claim, load_receipts(repo))
        raise PromotionRefused(
            f"{claim_id} is CHALLENGED by blocking receipt(s) {', '.join(open_ids)}; a later "
            "receipt must close them first"
        )
    if own == "SUPERSEDED":
        raise PromotionRefused(f"{claim_id} is SUPERSEDED; promote the superseding claim")
    if own == "STALE":
        reasons = mismatches(repo, {claim_id: claim}).get(claim_id, [])
        raise PromotionRefused(
            f"{claim_id} is STALE ({'; '.join(reasons) or 'a newer verifier is stamped'}); "
            "run reverify first"
        )
    # Levels are capped by dependencies (charter section 3): a claim may not rise above
    # the lowest level among the claims it depends on unless a human receipt waives it.
    cap, limiting = level_cap(claim, claims)
    if level != "REFUTED" and LEVEL_RANK[level] > cap and limiting is not None:
        waived = False
        if receipt_id is not None:
            r = load_receipts(repo).get(receipt_id)
            waived = (
                r is not None and r.claim_id == claim_id
                and r.statement_sha256 == statement_sha256(claim.statement)
                and "level_inversion" in r.waivers
            )
        if not waived:
            raise PromotionRefused(
                f"{level} is above dependency {limiting} at {claims[limiting].level}; re-earn "
                "the dependency first, or pass a human receipt that waives level_inversion"
            )
    # Everything the lock will cover must be a committed file BEFORE anything runs.
    _committed_or_refuse(repo, evidence_path, "evidence")
    for p in lock_paths_for(claim):
        _committed_or_refuse(repo, p, "locked path")
    # Receipts: elevated statement promotions, and refutations of anything established.
    receipt = None
    needs_receipt = (level in ELEVATED and claim.kind == "statement") or (
        level == "REFUTED" and claim.rank >= LEVEL_RANK["CONJECTURED"]
    )
    if needs_receipt:
        if receipt_id is None:
            what = (
                f"refuting a {claim.level} claim (REFUTED is terminal)" if level == "REFUTED"
                else f"promotion of a statement claim to {level}"
            )
            raise PromotionRefused(f"{what} requires a review receipt")
        receipts = load_receipts(repo)
        receipt = receipts.get(receipt_id)
        if receipt is None or receipt.claim_id != claim_id:
            raise PromotionRefused(f"receipt {receipt_id!r} is not a receipt for {claim_id}")
        if receipt.statement_sha256 != statement_sha256(claim.statement):
            raise PromotionRefused(f"receipt {receipt_id} reviewed a different statement")
        if not receipt.usable:
            raise PromotionRefused(
                f"receipt {receipt_id} records a sample that produced no review; it warrants "
                "nothing (re-run review)"
            )
        if receipt.blocking or receipt.verdict == "BLOCK":
            raise PromotionRefused(f"receipt {receipt_id} has a blocking finding")
        # Charter F4: the bar is "a receipt with no blocking issue". A REVISE receipt
        # (warnings, no blocker) warrants the promotion; its findings stay on record for
        # the author and are counted in the claim notes.
        if receipt.evidence_sha256:
            now_hashes = _evidence_hashes(repo, [*(e.path for e in claim.evidence), evidence_path])
            if set(receipt.evidence_sha256) != now_hashes:
                raise PromotionRefused(
                    f"receipt {receipt_id} reviewed different evidence (files changed or "
                    "added since the review)"
                )
    # The verifier runs HERE; the caller's opinion of the evidence is not evidence.
    result = v.run(evidence_path)
    want = Verdict.FAIL if level == "REFUTED" else Verdict.PASS
    entry = EvidenceEntry(
        path=evidence_path, verifier=v.name, version=v.version, verdict=result.verdict.value,
        stamped=_stamp_iso(now), binary_hash=v.binary_hash,
        golden_suite_hash=stamp.golden_suite_hash, note=_note(result, run_id),
    )
    if result.verdict is not want:
        # Record the honest outcome without moving the level.
        claim = claim.model_copy(update={"evidence": [*claim.evidence, entry]})
        lock = refresh_lock_entries(repo, claim, read_lock(repo))
        save_claim(repo, claim)
        write_lock(repo, lock)
        refresh_repo(repo)
        why = result.details.get("error") or result.details.get("detail") or ""
        raise PromotionRefused(
            f"verifier {v.name} returned {result.verdict.value}, not {want.value}: {why}".strip()
        )
    update: dict[str, Any] = {
        "level": level, "evidence": [*claim.evidence, entry], "updated": _today(now),
        "n": n if level == "VERIFIED_N" else None,
        "coverage": coverage if level == "VERIFIED_N" else None,
        "substatus": substatus,
    }
    if receipt is not None and receipt_id not in claim.receipts:
        update["receipts"] = [*claim.receipts, receipt_id]
    if receipt is not None and receipt.verdict == "REVISE":
        n_warn = sum(1 for f in receipt.findings if f.severity == "warning")
        update["notes"] = (claim.notes + "\n" if claim.notes else "") + (
            f"promoted to {level} on receipt {receipt_id} (REVISE: {n_warn} open warning(s) "
            "for the author, no blocking finding)"
        )
    if claim.legacy_level is not None and (
        level == claim.legacy_level
        or (claim.legacy_level != "REFUTED" and LEVEL_RANK[level] >= LEVEL_RANK[claim.legacy_level])
    ):
        update["legacy_level"] = None  # the legacy table's level has been re-earned
    try:
        claim = revalidate(claim.model_copy(update=update))
    except (ValueError, ClaimSchemaError) as exc:
        raise PromotionRefused(f"resulting claim is invalid: {exc}") from exc
    # Lock first, then the claim file: a lock failure must not leave a raised level behind.
    try:
        lock = refresh_lock_entries(repo, claim, read_lock(repo))
    except FileNotFoundError as exc:
        raise PromotionRefused(str(exc)) from exc
    save_claim(repo, claim)
    write_lock(repo, lock)
    refresh_repo(repo)
    return load_claim(claim_path(repo, claim_id))


def _latest_pass(claim: ClaimFile) -> list[EvidenceEntry]:
    latest: dict[tuple[str, str], EvidenceEntry] = {}
    for e in claim.evidence:
        if e.verdict == "PASS":
            latest[(e.path, e.verifier)] = e
    return list(latest.values())


def reverify(
    repo: Path | str,
    *,
    claim_id: str | None = None,
    verifiers: dict[str, Any] | None = None,
    now: str | None = None,
) -> dict[str, str]:
    """Re-run the latest PASS entry per (path, verifier) for the named claim, or for every
    claim that is STALE for its own reasons (lock drift, newer or changed verifier).
    A claim with no PASS entries (a legacy import, a HEURISTIC claim) is re-locked as its
    files are now. Command verifiers are resolved by name from `claims/verifiers/`;
    `verifiers` supplies objects for other names. Returns id -> outcome; a claim returns
    to CURRENT only when every entry passes again."""
    repo = Path(repo)
    drifted, _errors = drifted_verifiers(repo)
    newer = registry_newer(repo, drifted=drifted)
    claims = load_all(repo)
    lock = read_lock(repo)
    if claim_id:
        targets = [claim_id]
    else:
        own = set(mismatches(repo, claims, lock))
        own |= {c.id for c in claims.values() if any(newer(e) for e in _latest_pass(c))}
        targets = sorted(own)
    outcomes: dict[str, str] = {}
    for cid in targets:
        if cid not in claims:
            outcomes[cid] = "unknown claim"
            continue
        claim = claims[cid]
        passes = _latest_pass(claim)
        if not passes:
            try:
                lock = refresh_lock_entries(repo, claim, lock)
            except FileNotFoundError as exc:
                outcomes[cid] = f"cannot lock: {exc}"
                continue
            outcomes[cid] = "re-locked"
            continue
        fresh: list[EvidenceEntry] = []
        failed = False
        error: str | None = None
        for e in passes:
            v = (verifiers or {}).get(e.verifier)
            if v is None:
                try:
                    v = load_command_verifier(repo, e.verifier)
                except ClaimSchemaError:
                    outcomes[cid] = f"no verifier available for {e.verifier}"
                    failed = True
                    break
            try:
                stamp = _require_current_stamp(repo, v)
            except PromotionRefused as exc:
                outcomes[cid] = (
                    f"verifier {v.name} has no current stamp"
                    if "no current stamp" in str(exc) else str(exc)
                )
                failed = True
                break
            r = v.run(e.path)
            fresh.append(EvidenceEntry(
                path=e.path, verifier=v.name, version=v.version, verdict=r.verdict.value,
                stamped=_stamp_iso(now), binary_hash=v.binary_hash,
                golden_suite_hash=stamp.golden_suite_hash,
                note="reverify; " + _note(r, None),
            ))
            if r.verdict is Verdict.ERROR:
                failed = True
                error = str(r.details.get("error") or r.details.get("detail") or "error")
            elif r.verdict is not Verdict.PASS:
                failed = True
        if fresh:
            claim = claim.model_copy(update={"evidence": [*claim.evidence, *fresh],
                                             "updated": _today(now)})
            save_claim(repo, claim)
            if not failed:
                lock = refresh_lock_entries(repo, claim, lock)
        if cid not in outcomes:
            if not failed:
                outcomes[cid] = "re-verified"
            else:
                outcomes[cid] = f"verifier error: {error}" if error else "still failing"
    write_lock(repo, lock)
    refresh_repo(repo)
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
    """Lower a level; the reason lives in a receipt (charter section 3). REFUTED is not
    a demotion: it is reached through `promote` with FAIL evidence and a receipt."""
    repo = Path(repo)
    claims = load_all(repo)
    if claim_id not in claims:
        raise PromotionRefused(f"claim {claim_id!r} does not exist")
    claim = claims[claim_id]
    if level == "REFUTED":
        raise PromotionRefused(
            "REFUTED is reached through promote with FAIL evidence and a receipt, not demote"
        )
    if level not in LEVEL_RANK or LEVEL_RANK[level] >= claim.rank:
        raise PromotionRefused(f"demote must lower the level ({claim.level} -> {level})")
    receipts = load_receipts(repo)
    receipt = receipts.get(receipt_id)
    if receipt is None or receipt.claim_id != claim_id:
        raise PromotionRefused(f"receipt {receipt_id!r} is not a receipt for {claim_id}")
    if receipt.statement_sha256 != statement_sha256(claim.statement):
        raise PromotionRefused(f"receipt {receipt_id} reviewed a different statement")
    if not receipt.usable:
        raise PromotionRefused(f"receipt {receipt_id} records a sample that produced no review")
    update: dict[str, Any] = {
        "level": level, "updated": _today(now),
        "notes": (claim.notes + "\n" if claim.notes else "") + f"demoted to {level}: {reason}",
        "n": None if level != "VERIFIED_N" else claim.n,
        "coverage": None if level != "VERIFIED_N" else claim.coverage,
        "substatus": None,
    }
    if receipt_id not in claim.receipts:
        update["receipts"] = [*claim.receipts, receipt_id]
    save_claim(repo, revalidate(claim.model_copy(update=update)))
    refresh_repo(repo)
    return load_claim(claim_path(repo, claim_id))

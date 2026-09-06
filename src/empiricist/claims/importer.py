"""One-time importers (charter section 3: "existing tables are imported once").

(a) `import_ledger`: from an Empiricist v0 SQLite ledger + CAS. Every artifact at
    CONJECTURED or above (or REFUTED) that carries a canonical claim row becomes a claim
    file; its CAS content is written under `claims/evidence/` (the committed evidence
    file the lock hashes); PASS/FAIL evidence rows become evidence entries carrying the
    verifier identity. Idempotent: re-running rewrites the same files.
(b) `import_table`: from a legacy `CLAIMS.md` table (`id | problem | statement | level |
    evidence | updated`). Each row becomes a claim file with `verifier = "table-import"`
    evidence entries for the evidence paths that exist in the repository; paths that do
    not exist are kept in `notes` and reported. `check` flags every such claim as
    `imported_unverified` until a registered verifier re-verifies it (M22b).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from empiricist.claims.lock import Lock, read_lock, refresh_lock_entries, write_lock
from empiricist.claims.model import ClaimFile, EvidenceEntry, claims_dir, load_all, save_claim
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Status
from empiricist.store import Store

EVIDENCE_DIRNAME = "evidence"
TABLE_IMPORT_VERIFIER = "table-import"
_LEVELS = {"REFUTED", "HEURISTIC", "CONJECTURED", "VERIFIED_N", "CERTIFIED", "FORMALIZED"}
_KIND_BY_ARTIFACT_KIND = {
    "lean": "statement", "certificate": "statement", "statement": "statement",
    "dataset": "dataset", "construction": "construction", "proof_dag": "statement",
}
_EXT_BY_ARTIFACT_KIND = {"lean": "lean"}


@dataclass
class ImportReport:
    written: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)   # "<artifact/row>: reason"
    missing_paths: dict[str, list[str]] = field(default_factory=dict)


def _slug(text: str, limit: int = 60) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", text.strip()).strip("_")
    return (s[:limit] or "claim").rstrip("._-") or "claim"


def _unique_id(base: str, taken: set[str]) -> str:
    cid, n = base, 2
    while cid in taken:
        cid = f"{base}_{n}"
        n += 1
    taken.add(cid)
    return cid


def import_ledger(
    run_dir: Path | str,
    repo: Path | str,
    *,
    min_status: Status = Status.CONJECTURED,
    id_prefix: str | None = None,
) -> ImportReport:
    """Materialise claim files from a v0 ledger. The CAS blob of each artifact becomes the
    committed evidence file; the artifact id (blake3 of that content) stays visible in the
    claim's notes so the two records can be joined."""
    run_dir, repo = Path(run_dir), Path(repo)
    ledger = Ledger(run_dir / "ledger.db")
    store = Store(run_dir / "store")
    report = ImportReport()
    try:
        existing = load_all(repo)
        # a re-import must map each artifact to the id it got last time: notes carry it
        by_artifact = {
            _artifact_id_from_notes(c.notes): cid for cid, c in existing.items()
            if _artifact_id_from_notes(c.notes)
        }
        taken = set(existing)
        lock = read_lock(repo)
        for art in ledger.find_artifacts():
            if art.status is not Status.REFUTED and art.status.rank < min_status.rank:
                continue
            claims = ledger.claims_for(art.id)
            if not claims:
                report.skipped.append(f"{art.id[:12]}: no canonical claim row")
                continue
            canonical = claims[-1]
            kind = _KIND_BY_ARTIFACT_KIND.get(art.kind)
            if kind is None:
                report.skipped.append(f"{art.id[:12]}: artifact kind {art.kind!r} not importable")
                continue
            ext = _EXT_BY_ARTIFACT_KIND.get(art.kind, "json")
            ev_rel = f"{claims_dir(repo).name}/{EVIDENCE_DIRNAME}/{art.id[:16]}.{ext}"
            ev_path = repo / ev_rel
            ev_path.parent.mkdir(parents=True, exist_ok=True)
            ev_path.write_bytes(store.get(art.content_path))
            entries = []
            for row in ledger.evidence_for(art.id):
                if row.verdict.value not in ("PASS", "FAIL", "ERROR"):
                    continue
                entries.append(EvidenceEntry(
                    path=ev_rel, verifier=row.verifier, version=row.verifier_version,
                    verdict=row.verdict.value, stamped=row.created_at,
                    binary_hash=row.binary_hash, golden_suite_hash=row.golden_suite_hash,
                    note=f"claim {row.claim_id[:12]}" if row.claim_id else "",
                ))
            if art.id in by_artifact:
                cid = by_artifact[art.id]
            else:
                prefix = id_prefix or art.problem
                base = f"{prefix}.{_slug(canonical.family or art.title)}"
                cid = _unique_id(base, taken)
            claim = ClaimFile(
                id=cid, problem=art.problem, formulation_version=art.problem_version,
                kind=kind, statement=canonical.statement, level=art.status.value,
                substatus=art.substatus if art.substatus == "PROVED_DRAFT" else None,
                n=art.status_n if art.status is Status.VERIFIED_N else None,
                coverage=art.coverage if art.status is Status.VERIFIED_N else None,
                evidence=entries,
                notes=f"artifact {art.id}; title: {art.title}",
                updated=art.created_at[:10],
            )
            save_claim(repo, claim)
            lock = refresh_lock_entries(repo, claim, lock)
            report.written.append(cid)
        write_lock(repo, lock)
    finally:
        ledger.close()
    return report


def _artifact_id_from_notes(notes: str) -> str | None:
    m = re.match(r"artifact ([0-9a-f]{64})", notes or "")
    return m.group(1) if m else None


_ROW_RE = re.compile(r"^\|(.*)\|\s*$")


def parse_claims_table(text: str) -> list[dict[str, str]]:
    """Rows of a `| id | problem | statement | level | evidence | updated |` table."""
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for line in text.splitlines():
        m = _ROW_RE.match(line.strip())
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue  # the separator row
        if len(cells) != len(header):
            continue
        rows.append(dict(zip(header, cells, strict=True)))
    return rows


def _split_level(cell: str) -> tuple[str, str]:
    """`CERTIFIED (why ...)` -> ("CERTIFIED", "why ..."); `CONJEC...` prefixes tolerated."""
    token = cell.strip().split()[0].strip("*`") if cell.strip() else ""
    level = next((lv for lv in _LEVELS if token.upper().startswith(lv)), "")
    rest = cell.strip()[len(token):].strip(" ()") if level else cell.strip()
    return level, rest


def import_table(
    table_path: Path | str,
    repo: Path | str,
    *,
    problem_default: str = "unknown",
    formulation_version: str = "legacy-table",
) -> ImportReport:
    repo = Path(repo)
    text = Path(table_path).read_text(encoding="utf-8")
    report = ImportReport()
    existing = load_all(repo)
    taken = set(existing)
    lock = read_lock(repo)
    for row in parse_claims_table(text):
        rid = row.get("id", "").strip("`* ")
        if not rid:
            report.skipped.append("row without id")
            continue
        level, level_note = _split_level(row.get("level", ""))
        if not level:
            report.skipped.append(f"{rid}: unrecognised level {row.get('level', '')!r}")
            continue
        cid = rid if rid in existing else _unique_id(_slug(rid, 120), taken)
        paths = [p.strip() for p in row.get("evidence", "").split(";") if p.strip()]
        present = [p for p in paths if (repo / p).is_file() and not Path(p).is_absolute()]
        missing = [p for p in paths if p not in present]
        if missing:
            report.missing_paths[cid] = missing
        updated = row.get("updated", "").strip() or "1970-01-01"
        verdict = "FAIL" if level == "REFUTED" else "PASS"
        entries = [
            EvidenceEntry(path=p, verifier=TABLE_IMPORT_VERIFIER, version="1",
                          verdict=verdict, stamped=updated, note="imported from CLAIMS.md")
            for p in present
        ]
        notes = "imported from CLAIMS.md"
        if level_note:
            notes += f"; level note: {level_note}"
        if missing:
            notes += "; evidence not found in repo: " + "; ".join(missing)
        claim = ClaimFile(
            id=cid, problem=row.get("problem", "").strip() or problem_default,
            formulation_version=formulation_version, kind="statement",
            statement=row.get("statement", "").strip() or "(no statement)", level=level,
            evidence=entries, notes=notes, updated=updated,
        )
        save_claim(repo, claim)
        lock = refresh_lock_entries(repo, claim, lock)
        report.written.append(cid)
    write_lock(repo, lock)
    return report


__all__ = [
    "ImportReport", "Lock", "import_ledger", "import_table", "parse_claims_table",
]

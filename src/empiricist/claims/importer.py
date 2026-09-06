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
MAX_DIRECTORY_FILES = 200   # a directory evidence reference expands to at most this many files
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
    """Unique among `taken` CASE-INSENSITIVELY: claim ids are filenames, and a
    case-insensitive filesystem (macOS) would otherwise merge two claims."""
    lowered = {t.lower() for t in taken}
    cid, n = base, 2
    while cid.lower() in lowered:
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
            canonical = claims[-1] if claims else None
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
                family = canonical.family if canonical and canonical.family else art.title
                cid = _unique_id(f"{prefix}.{_slug(family)}", taken)
            if canonical is not None:
                statement = canonical.statement
                notes = f"artifact {art.id}; title: {art.title}"
            else:
                # Pre-hardening artifact (no canonical claim row): the title is the
                # only statement on record; say so.
                statement = art.title
                notes = (f"artifact {art.id}; title: {art.title}; no canonical claim row "
                         "(pre-hardening record; statement is the artifact title)")
            claim = ClaimFile(
                id=cid, problem=art.problem, formulation_version=art.problem_version,
                kind=kind, statement=statement, level=art.status.value,
                substatus=art.substatus if art.substatus == "PROVED_DRAFT" else None,
                n=art.status_n if art.status is Status.VERIFIED_N else None,
                coverage=art.coverage if art.status is Status.VERIFIED_N else None,
                evidence=entries,
                notes=notes,
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
_PROBLEM_DIR_RE = re.compile(r"^(P\d+)")
_AS_REF_RE = re.compile(r"^(?:as|=|see|cf\.?)\s+([A-Za-z0-9._:-]+)$", re.IGNORECASE)


def _problem_dir(problem_cell: str) -> str | None:
    """`P9(b), ...` -> `problems/P9` (the repository layout used by death_and_gravity)."""
    m = _PROBLEM_DIR_RE.match(problem_cell.strip())
    return f"problems/{m.group(1)}" if m else None


def resolve_evidence_cell(
    repo: Path, cell: str, problem_cell: str, *, known_ids: set[str] | None = None
) -> tuple[list[str], list[str], list[str]]:
    """Turn a legacy evidence cell into (existing repo-relative paths, claim-id
    dependencies, unresolved fragments). Fragments are split on `;`; each is tried
    verbatim, then relative to the problem directory, then as a glob (`*`), with
    brace alternatives expanded; a trailing ` §...`/`(...)` qualifier is dropped;
    `as <id>` / `= <id>` / `CLAIMS <id>, <id>` become dependencies."""
    repo = Path(repo)
    known_ids = known_ids or set()
    present: list[str] = []
    depends: list[str] = []
    missing: list[str] = []
    pdir = _problem_dir(problem_cell)

    def add_present(rel: str) -> None:
        if rel not in present:
            present.append(rel)

    fragments: list[str] = []
    for raw in (f.strip() for f in cell.split(";")):
        if not raw:
            continue
        # `a.py, b.py` inside one fragment: split when every piece looks like a path
        pieces = [x.strip() for x in raw.split(",")] if ", " in raw else [raw]
        if len(pieces) > 1 and all(("/" in x or "." in x) and " " not in x for x in pieces):
            fragments.extend(pieces)
        else:
            fragments.append(raw)
    for raw in fragments:
        frag = re.sub(r"\s+(§|\(v\d|\(v\d|\().*$", "", raw).strip()
        m = _AS_REF_RE.match(frag)
        if m and m.group(1) in known_ids:
            depends.append(m.group(1))
            continue
        if frag.upper().startswith("CLAIMS "):
            ids = [t.strip(" ,") for t in frag[7:].split(",")]
            found = [t for t in ids if t in known_ids]
            depends.extend(found)
            if len(found) == len(ids):
                continue
        candidates = _expand_braces(frag)
        resolved_any = False
        for cand in candidates:
            for base in ([""] if pdir is None else ["", pdir + "/"]):
                rel = (base + cand).lstrip("./")
                if Path(rel).is_absolute() or ".." in Path(rel).parts:
                    continue
                if "*" in rel:
                    hits = sorted(str(h.relative_to(repo)) for h in repo.glob(rel) if h.is_file())
                    if hits:
                        for h in hits:
                            add_present(h)
                        resolved_any = True
                        break
                elif (repo / rel).is_file():
                    add_present(rel)
                    resolved_any = True
                    break
                elif (repo / rel).is_dir():
                    # a directory reference means every committed file under it
                    files = sorted(
                        str(h.relative_to(repo)) for h in (repo / rel).rglob("*")
                        if h.is_file() and "__pycache__" not in h.parts
                        and not h.name.startswith(".")
                    )
                    if files and len(files) <= MAX_DIRECTORY_FILES:
                        for h in files:
                            add_present(h)
                        resolved_any = True
                        break
            if resolved_any:
                break
        if not resolved_any:
            missing.append(raw)
    return present, list(dict.fromkeys(depends)), missing


def _expand_braces(frag: str) -> list[str]:
    m = re.search(r"\{([^{}]*)\}", frag)
    if not m:
        return [frag]
    out: list[str] = []
    for alt in m.group(1).split(","):
        out.extend(_expand_braces(frag[:m.start()] + alt.strip() + frag[m.end():]))
    return out


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
    rows = parse_claims_table(text)
    known_ids = {r.get("id", "").strip("`* ") for r in rows} | set(existing)
    for row in rows:
        rid = row.get("id", "").strip("`* ")
        if not rid:
            report.skipped.append("row without id")
            continue
        level, level_note = _split_level(row.get("level", ""))
        if not level:
            report.skipped.append(f"{rid}: unrecognised level {row.get('level', '')!r}")
            continue
        cid = rid if rid in existing else _unique_id(_slug(rid, 120), taken)
        problem_cell = row.get("problem", "").strip() or problem_default
        present, depends, missing = resolve_evidence_cell(
            repo, row.get("evidence", ""), problem_cell, known_ids=known_ids,
        )
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
            notes += "; evidence not resolved in repo: " + "; ".join(missing)
        claim = ClaimFile(
            id=cid, problem=problem_cell,
            formulation_version=formulation_version, kind="statement",
            statement=row.get("statement", "").strip() or "(no statement)", level=level,
            depends_on=[d for d in depends if d != cid],
            evidence=entries, notes=notes, updated=updated,
        )
        save_claim(repo, claim)
        lock = refresh_lock_entries(repo, claim, lock)
        report.written.append(cid)
    # A row whose evidence is literally another claim's ("as P9b-0", "= P9b-0") inherits
    # that claim's evidence paths: the same files, recorded as such.
    written = load_all(repo)
    for cid in list(report.written):
        claim = written[cid]
        if claim.evidence or not claim.depends_on:
            continue
        inherited: list[EvidenceEntry] = []
        for dep in claim.depends_on:
            for e in written.get(dep, ClaimFile.model_construct(evidence=[])).evidence:
                inherited.append(
                    e.model_copy(update={"note": f"inherited from {dep} (as recorded)"})
                )
        if inherited:
            claim = claim.model_copy(update={"evidence": inherited})
            save_claim(repo, claim)
            lock = refresh_lock_entries(repo, claim, lock)
    write_lock(repo, lock)
    return report


__all__ = [
    "ImportReport", "Lock", "import_ledger", "import_table", "parse_claims_table",
    "resolve_evidence_cell",
]

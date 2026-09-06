"""One-time importers (charter section 3: "existing tables are imported once").

(a) `import_ledger`: from an Empiricist v0 SQLite ledger + CAS. Every artifact at
    CONJECTURED or above (or REFUTED) becomes a claim file; its CAS content is written
    under `claims/evidence/` (the committed evidence file the lock hashes); PASS/FAIL/ERROR
    evidence rows become evidence entries carrying the verifier identity. The artifact id
    is kept in `source` so a re-import updates the same file (idempotent) and never
    touches the human-owned fields (`depends_on`, `supersedes`, `receipts`, `notes`) or
    lowers a level.
(b) `import_table`: from a legacy `CLAIMS.md` table (`id | problem | statement | level |
    evidence | updated`). Levels are earned, so each row enters at HEURISTIC with the
    table's level in `legacy_level`; the evidence paths that exist in the repository
    become IMPORTED entries (locked, never counted as PASS); paths that do not exist are
    kept in `notes` and reported. `promote` with a certified verifier re-earns the level.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from empiricist.claims.lock import Lock, read_lock, refresh_lock_entries, write_lock
from empiricist.claims.model import (
    LEVEL_RANK,
    TABLE_IMPORT_VERIFIER,
    ClaimFile,
    ClaimSchemaError,
    EvidenceEntry,
    Source,
    claims_dir,
    load_all,
    revalidate,
    save_claim,
)
from empiricist.claims.render import claims_md_path, is_rendered
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Status, Verdict
from empiricist.store import Store

EVIDENCE_DIRNAME = "evidence"
MAX_DIRECTORY_FILES = 200   # a directory evidence reference expands to at most this many files
_LEVEL_ORDER = ("REFUTED", "HEURISTIC", "CONJECTURED", "VERIFIED_N", "CERTIFIED", "FORMALIZED")
_KIND_BY_ARTIFACT_KIND = {
    "lean": "statement", "certificate": "statement", "statement": "statement",
    "dataset": "dataset", "construction": "construction", "proof_dag": "statement",
}
_EXT_BY_ARTIFACT_KIND = {"lean": "lean"}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class ImportReport:
    written: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)   # "<artifact/row>: reason"
    missing_paths: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    stamped: list[str] = field(default_factory=list)   # "<verifier> <version>" newly stamped


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


def _ledger_ref(claim: ClaimFile) -> str | None:
    """The v0 artifact a claim was imported from: `source`, or (older files) the notes."""
    if claim.source is not None and claim.source.kind == "ledger":
        return claim.source.ref
    m = re.match(r"artifact ([0-9a-f]{64})", claim.notes or "")
    return m.group(1) if m else None


def _stamp_registry_from_ledger(
    ledger: Ledger, repo: Path, entries: list[EvidenceEntry], report: ImportReport
) -> None:
    """Carry the ledger's current PASS certifications for the verifiers named in
    `entries` into `claims/verifiers.json`, never downgrading a stamp the registry
    already holds (newest version wins; same version keeps the registry's hash)."""
    from empiricist.claims.registry import _version_key, read_registry, stamp

    best: dict[str, tuple[tuple, str, str, str]] = {}
    for e in entries:
        if e.binary_hash is None or e.golden_suite_hash is None:
            continue
        cert = ledger.get_certification(e.verifier, e.version, e.binary_hash)
        if cert is None or cert.verdict is not Verdict.PASS:
            continue
        key = _version_key(e.version)
        if e.verifier not in best or key > best[e.verifier][0]:
            best[e.verifier] = (key, e.version, e.binary_hash, cert.golden_suite_hash)
    if not best:
        return
    reg = read_registry(repo)
    for name, (key, version, binary_hash, suite) in best.items():
        cur = reg.stamps.get(name)
        if cur is not None and _version_key(cur.version) >= key:
            continue
        stamp(repo, name=name, version=version, binary_hash=binary_hash,
              golden_suite_hash=suite, declaration="ledger certification")
        report.stamped.append(f"{name} {version}")


def materialize_artifacts(
    ledger: Ledger,
    store: Store,
    repo: Path | str,
    *,
    artifact_ids: list[str] | None = None,
    min_status: Status = Status.CONJECTURED,
    id_prefix: str | None = None,
) -> ImportReport:
    """Materialise claim files for the given artifacts (default: every artifact) of an
    open v0 ledger. Idempotent; the batch loop calls this after each ingest transaction
    and `import_ledger` calls it for a whole run directory."""
    repo = Path(repo)
    report = ImportReport()
    existing = load_all(repo)
    by_artifact = {_ledger_ref(c): cid for cid, c in existing.items() if _ledger_ref(c)}
    taken = set(existing)
    lock = read_lock(repo)
    if artifact_ids is None:
        artifacts = ledger.find_artifacts()
    else:
        artifacts = [ledger.get_artifact(a) for a in artifact_ids]
    stamped_entries: list[EvidenceEntry] = []
    for art in artifacts:
        if art.status is not Status.REFUTED and art.status.rank < min_status.rank:
            report.skipped.append(f"{art.id[:12]}: {art.status.value} is below {min_status.value}")
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
        stamped_entries.extend(entries)
        if canonical is not None:
            statement = canonical.statement
            notes = f"artifact {art.id}; title: {art.title}"
        else:
            # Pre-hardening artifact (no canonical claim row): the title is the
            # only statement on record; say so.
            statement = art.title
            notes = (f"artifact {art.id}; title: {art.title}; no canonical claim row "
                     "(pre-hardening record; statement is the artifact title)")
        derived = dict(
            problem=art.problem, formulation_version=art.problem_version, kind=kind,
            statement=statement, level=art.status.value,
            substatus=art.substatus if art.substatus == "PROVED_DRAFT" else None,
            n=art.status_n if art.status is Status.VERIFIED_N else None,
            coverage=art.coverage if art.status is Status.VERIFIED_N else None,
            evidence=entries, updated=art.created_at[:10],
            source=Source(kind="ledger", ref=art.id),
        )
        if art.id in by_artifact:
            prev = existing[by_artifact[art.id]]
            if art.status is not Status.REFUTED and prev.rank > LEVEL_RANK[art.status.value]:
                # a level recorded in the repo (a receipted demote, a later promotion)
                # is never lowered by a re-import; REFUTED always wins
                for k in ("level", "substatus", "n", "coverage"):
                    derived[k] = getattr(prev, k)
            claim = revalidate(prev.model_copy(update=derived))
        else:
            prefix = id_prefix or art.problem
            family = canonical.family if canonical and canonical.family else art.title
            cid = _unique_id(f"{prefix}.{_slug(family)}", taken)
            claim = ClaimFile(id=cid, notes=notes, **derived)
        save_claim(repo, claim)
        existing[claim.id] = claim
        by_artifact[art.id] = claim.id
        lock = refresh_lock_entries(repo, claim, lock)
        report.written.append(claim.id)
    write_lock(repo, lock)
    _stamp_registry_from_ledger(ledger, repo, stamped_entries, report)
    return report


def import_ledger(
    run_dir: Path | str,
    repo: Path | str,
    *,
    min_status: Status = Status.CONJECTURED,
    id_prefix: str | None = None,
) -> ImportReport:
    """Materialise claim files from a v0 run directory. The CAS blob of each artifact
    becomes the committed evidence file; the artifact id (blake3 of that content) is
    the `source`; the ledger's PASS certifications stamp `claims/verifiers.json`."""
    run_dir = Path(run_dir)
    ledger = Ledger(run_dir / "ledger.db")
    store = Store(run_dir / "store")
    try:
        return materialize_artifacts(
            ledger, store, repo, min_status=min_status, id_prefix=id_prefix
        )
    finally:
        ledger.close()


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


def parse_claims_table(text: str, *, dropped: list[str] | None = None) -> list[dict[str, str]]:
    """Rows of a `| id | problem | statement | level | evidence | updated |` table.

    A row with MORE cells than the header has unescaped `|` characters in its prose;
    the surplus is re-joined into the `statement` column (`|x| < 0.1` survives). A row
    with fewer cells is dropped and, when `dropped` is given, reported there."""
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for lineno, line in enumerate(text.splitlines(), 1):
        m = _ROW_RE.match(line.strip())
        if not m:
            continue
        raw = m.group(1).split("|")
        if header is None:
            header = [c.strip().lower() for c in raw]
            continue
        if all(set(c.strip()) <= set("-: ") for c in raw):
            continue  # the separator row
        if len(raw) > len(header):
            extra = len(raw) - len(header)
            si = header.index("statement") if "statement" in header else 0
            raw = raw[:si] + ["|".join(raw[si:si + extra + 1])] + raw[si + extra + 1:]
        cells = [c.strip() for c in raw]
        if len(cells) != len(header):
            if dropped is not None:
                dropped.append(f"line {lineno}: {len(cells)} cells, expected {len(header)}")
            continue
        rows.append(dict(zip(header, cells, strict=True)))
    return rows


def _split_level(cell: str) -> tuple[str, str]:
    """`CERTIFIED (why ...)` -> ("CERTIFIED", "why ..."); `**FORMALIZED**` -> ("FORMALIZED",
    ""); `VERIFIED_N (n=2000)` -> ("VERIFIED_N", "n=2000"). A truncated level of at least
    five letters (`CONJEC...`) is tolerated."""
    stripped = cell.strip().replace("*", "").replace("`", "").strip()
    if not stripped:
        return "", ""
    token = re.split(r"[\s(]", stripped, maxsplit=1)[0].strip(".")
    up = token.upper()
    level = next(
        (lv for lv in _LEVEL_ORDER
         if up == lv or up.startswith(lv) or (len(up) >= 5 and lv.startswith(up))),
        "",
    )
    rest = stripped[len(token):].strip(" ().") if level else stripped
    return level, rest


def import_table(
    table_path: Path | str,
    repo: Path | str,
    *,
    problem_default: str = "unknown",
    formulation_version: str = "legacy-table",
) -> ImportReport:
    repo, table_path = Path(repo), Path(table_path)
    text = table_path.read_text(encoding="utf-8")
    report = ImportReport()
    if is_rendered(text):
        report.warnings.append(f"{table_path} is already rendered output; nothing to import")
        return report
    if table_path.resolve() == claims_md_path(repo).resolve():
        report.warnings.append(
            "the legacy table is the repository's CLAIMS.md; run `claims report --force` "
            "once to replace it with the rendered ledger"
        )
    existing = load_all(repo)
    taken = set(existing)
    lock = read_lock(repo)
    dropped: list[str] = []
    rows = parse_claims_table(text, dropped=dropped)
    report.skipped.extend(f"row dropped: {d}" for d in dropped)
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
        updated_raw = row.get("updated", "").strip()
        updated = updated_raw if _DATE_RE.match(updated_raw) else "1970-01-01"
        entries = [
            EvidenceEntry(path=p, verifier=TABLE_IMPORT_VERIFIER, version="1",
                          verdict="IMPORTED", stamped=updated, note="imported from CLAIMS.md")
            for p in present
        ]
        notes = "imported from CLAIMS.md"
        if level_note:
            notes += f"; level note: {level_note}"
        if updated_raw and updated != updated_raw:
            notes += f"; updated: {updated_raw}"
        if missing:
            notes += "; evidence not resolved in repo: " + "; ".join(missing)
        legacy = None if level == "HEURISTIC" else level
        source = Source(kind="table", ref=rid)
        try:
            if cid in existing:
                prev = existing[cid]
                if legacy is not None and legacy != "REFUTED" and prev.rank >= LEVEL_RANK[legacy]:
                    legacy = None
                if legacy == "REFUTED" and prev.level == "REFUTED":
                    legacy = None
                kept = [e for e in prev.evidence if e.verdict != "IMPORTED"]
                deps = list(dict.fromkeys(prev.depends_on + [d for d in depends if d != cid]))
                claim = revalidate(prev.model_copy(update={
                    "evidence": kept + entries, "legacy_level": legacy, "source": source,
                    "depends_on": deps,
                }))
            else:
                claim = ClaimFile(
                    id=cid, problem=problem_cell,
                    formulation_version=formulation_version, kind="statement",
                    statement=row.get("statement", "").strip() or "(no statement)",
                    level="HEURISTIC", legacy_level=legacy,
                    depends_on=[d for d in depends if d != cid],
                    evidence=entries, notes=notes, updated=updated, source=source,
                )
            save_claim(repo, claim)
        except (ValueError, ClaimSchemaError) as exc:
            report.skipped.append(f"{rid}: {exc}")
            continue
        lock = refresh_lock_entries(repo, claim, lock)
        report.written.append(cid)
    # A row whose evidence is literally another claim's ("as P9b-0", "= P9b-0") inherits
    # that claim's IMPORTED evidence paths: the same files, recorded as such.
    written = load_all(repo)
    for cid in list(report.written):
        claim = written[cid]
        if claim.evidence or not claim.depends_on:
            continue
        inherited: list[EvidenceEntry] = []
        for dep in claim.depends_on:
            for e in written.get(dep, ClaimFile.model_construct(evidence=[])).evidence:
                if e.verdict == "IMPORTED":
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
    "ImportReport", "Lock", "import_ledger", "import_table", "materialize_artifacts",
    "parse_claims_table", "resolve_evidence_cell",
]

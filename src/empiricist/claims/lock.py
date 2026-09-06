"""`claims.lock.json`: sha256 of every evidence file and path dependency at promotion
time, plus the verifier identity that produced each evidence entry (charter section 3).
Only committed, repo-relative files are hashed. `mismatches` is what turns a silent
edit into STALE (charter F6).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from empiricist.claims.model import ClaimFile, ClaimSchemaError, is_path_dependency

LOCK_FILENAME = "claims.lock.json"


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class LockEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sha256: str
    verifier: dict[str, str | None] | None = None  # name, version, binary_hash, golden_suite_hash


class Lock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    files: dict[str, LockEntry] = Field(default_factory=dict)  # repo-relative path -> entry


def lock_path(repo: Path | str) -> Path:
    return Path(repo) / LOCK_FILENAME


def read_lock(repo: Path | str) -> Lock:
    p = lock_path(repo)
    if not p.is_file():
        return Lock()
    try:
        return Lock.model_validate(json.loads(p.read_text(encoding="utf-8")))
    except (ValueError, ValidationError) as exc:
        raise ClaimSchemaError(f"{p}: malformed lock: {exc}") from exc


def write_lock(repo: Path | str, lock: Lock) -> Path:
    p = lock_path(repo)
    data = lock.model_dump(mode="json")
    data["files"] = dict(sorted(data["files"].items()))
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def lock_paths_for(claim: ClaimFile) -> list[str]:
    """Every path this claim's standing depends on: evidence files and path dependencies."""
    paths = [e.path for e in claim.evidence]
    paths += [d for d in claim.depends_on if is_path_dependency(d)]
    return list(dict.fromkeys(paths))


def refresh_lock_entries(repo: Path | str, claim: ClaimFile, lock: Lock) -> Lock:
    """(Re)hash the claim's paths now. Evidence paths carry the verifier identity of
    the LAST evidence entry naming that path; dependency paths carry none."""
    repo = Path(repo)
    files = dict(lock.files)
    verifier_for: dict[str, dict[str, str | None]] = {}
    for e in claim.evidence:
        verifier_for[e.path] = {
            "name": e.verifier, "version": e.version,
            "binary_hash": e.binary_hash, "golden_suite_hash": e.golden_suite_hash,
        }
    for path in lock_paths_for(claim):
        full = repo / path
        if not full.is_file():
            raise FileNotFoundError(f"{claim.id}: cannot lock missing file {path}")
        files[path] = LockEntry(sha256=sha256_file(full), verifier=verifier_for.get(path))
    return Lock(version=lock.version, files=files)


def mismatches(
    repo: Path | str, claims: dict[str, ClaimFile], lock: Lock | None = None
) -> dict[str, list[str]]:
    """claim id -> reasons (`unlocked:<path>`, `missing:<path>`, `changed:<path>`)."""
    repo = Path(repo)
    lock = read_lock(repo) if lock is None else lock
    out: dict[str, list[str]] = {}
    for cid, claim in claims.items():
        reasons: list[str] = []
        for path in lock_paths_for(claim):
            entry = lock.files.get(path)
            full = repo / path
            if entry is None:
                reasons.append(f"unlocked:{path}")
            elif not full.is_file():
                reasons.append(f"missing:{path}")
            elif sha256_file(full) != entry.sha256:
                reasons.append(f"changed:{path}")
        if reasons:
            out[cid] = reasons
    return out

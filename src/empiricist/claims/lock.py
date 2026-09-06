"""`claims.lock.json`: sha256 of every evidence file and path dependency at promotion
time, plus the identity of every verifier whose evidence names each path (charter
section 3). Only committed, repo-relative regular files are hashed: symlinks and paths
that resolve outside the repository are refused, because a referee cannot audit bytes
that are not in the checkout. `mismatches` is what turns a silent edit -- of the file OR
of a claim's recorded verifier identity -- into STALE (charter F6).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from empiricist.claims.model import ClaimFile, ClaimSchemaError, EvidenceEntry, is_path_dependency

LOCK_FILENAME = "claims.lock.json"
LOCK_VERSION = 2


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class VerifierIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    binary_hash: str | None = None
    golden_suite_hash: str | None = None


class LockEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sha256: str
    # verifier name -> identity behind the LAST evidence entry naming this path
    verifiers: dict[str, VerifierIdentity] = Field(default_factory=dict)


class Lock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = LOCK_VERSION
    files: dict[str, LockEntry] = Field(default_factory=dict)  # repo-relative path -> entry


def lock_path(repo: Path | str) -> Path:
    return Path(repo) / LOCK_FILENAME


def _migrate_v1(data: dict[str, Any]) -> dict[str, Any]:
    """v1 kept one `verifier: {name, ...}` per path; v2 keys identities by name."""
    for entry in data.get("files", {}).values():
        v = entry.pop("verifier", None)
        entry.setdefault("verifiers", {})
        if v and v.get("name"):
            entry["verifiers"][v["name"]] = {
                k: v.get(k) for k in ("version", "binary_hash", "golden_suite_hash")
            }
    data["version"] = LOCK_VERSION
    return data


def read_lock(repo: Path | str) -> Lock:
    p = lock_path(repo)
    if not p.is_file():
        return Lock()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("version") == 1:
            data = _migrate_v1(data)
        return Lock.model_validate(data)
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


def committed_file(repo: Path | str, path: str) -> Path | None:
    """The regular file at `repo/path` if it is not a symlink and resolves inside the
    repository; None otherwise (missing, symlink, outside, or not a regular file)."""
    repo = Path(repo)
    full = repo / path
    if full.is_symlink():
        return None
    try:
        resolved = full.resolve(strict=True)
    except OSError:
        return None
    if not resolved.is_relative_to(repo.resolve()) or not resolved.is_file():
        return None
    return full


def identity_of(e: EvidenceEntry) -> VerifierIdentity:
    return VerifierIdentity(
        version=e.version, binary_hash=e.binary_hash, golden_suite_hash=e.golden_suite_hash
    )


def _last_identities(claim: ClaimFile) -> dict[str, dict[str, VerifierIdentity]]:
    """path -> verifier name -> identity of the last evidence entry with that (path, name)."""
    out: dict[str, dict[str, VerifierIdentity]] = {}
    for e in claim.evidence:
        out.setdefault(e.path, {})[e.verifier] = identity_of(e)
    return out


def refresh_lock_entries(repo: Path | str, claim: ClaimFile, lock: Lock) -> Lock:
    """(Re)hash the claim's paths now. Verifier identities recorded by OTHER claims on a
    shared path are kept; this claim's identities overwrite its own verifier names."""
    repo = Path(repo)
    files = dict(lock.files)
    idents = _last_identities(claim)
    for path in lock_paths_for(claim):
        full = committed_file(repo, path)
        if full is None:
            raise FileNotFoundError(
                f"{claim.id}: cannot lock {path} (missing, a symlink, or outside the repository)"
            )
        verifiers = dict(files[path].verifiers) if path in files else {}
        verifiers.update(idents.get(path, {}))
        files[path] = LockEntry(sha256=sha256_file(full), verifiers=verifiers)
    return Lock(version=LOCK_VERSION, files=files)


def mismatches(
    repo: Path | str, claims: dict[str, ClaimFile], lock: Lock | None = None
) -> dict[str, list[str]]:
    """claim id -> reasons: `unlocked:<path>`, `missing:<path>`, `outside:<path>` (symlink
    or resolves outside the repo), `changed:<path>`, `verifier_unlocked:<path>:<name>`,
    `verifier_changed:<path>:<name>`."""
    repo = Path(repo)
    lock = read_lock(repo) if lock is None else lock
    out: dict[str, list[str]] = {}
    for cid, claim in claims.items():
        reasons: list[str] = []
        idents = _last_identities(claim)
        for path in lock_paths_for(claim):
            entry = lock.files.get(path)
            if entry is None:
                reasons.append(f"unlocked:{path}")
                continue
            full = repo / path
            committed = committed_file(repo, path)
            if committed is None:
                reasons.append(f"missing:{path}" if not full.exists() else f"outside:{path}")
            elif sha256_file(committed) != entry.sha256:
                reasons.append(f"changed:{path}")
            for name, ident in idents.get(path, {}).items():
                locked = entry.verifiers.get(name)
                if locked is None:
                    reasons.append(f"verifier_unlocked:{path}:{name}")
                elif locked != ident:
                    reasons.append(f"verifier_changed:{path}:{name}")
        if reasons:
            out[cid] = reasons
    return out

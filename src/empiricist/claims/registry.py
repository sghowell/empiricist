"""The committed verifier registry of a research repository: `claims/verifiers.json`.

v0's registry rule stands (charter section 5): a verifier may produce evidence only
while it holds a PASS stamp for its exact (name, version, binary_hash) against the
golden suite it was certified with. In a research repository the stamps are committed
next to the claims, so `check` can decide staleness without a SQLite ledger: a claim
whose evidence names an older version (or the same version with a different binary
hash) of a verifier the registry now stamps is STALE until `reverify` re-runs it.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from empiricist.claims.model import ClaimSchemaError, EvidenceEntry, claims_dir

REGISTRY_FILENAME = "verifiers.json"


def _version_key(version: str) -> tuple:
    parts = []
    for piece in version.replace("-", ".").split("."):
        parts.append((0, int(piece)) if piece.isdigit() else (1, piece))
    return tuple(parts)


class VerifierStamp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    binary_hash: str
    golden_suite_hash: str
    stamped: str
    declaration: str | None = None  # repo-relative path of a command-verifier declaration


class Registry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    stamps: dict[str, VerifierStamp] = Field(default_factory=dict)  # name -> current stamp


def registry_path(repo: Path | str) -> Path:
    return claims_dir(repo) / REGISTRY_FILENAME


def read_registry(repo: Path | str) -> Registry:
    p = registry_path(repo)
    if not p.is_file():
        return Registry()
    try:
        return Registry.model_validate(json.loads(p.read_text(encoding="utf-8")))
    except (ValueError, ValidationError) as exc:
        raise ClaimSchemaError(f"{p}: malformed registry: {exc}") from exc


def write_registry(repo: Path | str, registry: Registry) -> Path:
    p = registry_path(repo)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = registry.model_dump(mode="json")
    data["stamps"] = dict(sorted(data["stamps"].items()))
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def stamp(
    repo: Path | str,
    *,
    name: str,
    version: str,
    binary_hash: str,
    golden_suite_hash: str,
    declaration: str | None = None,
    now: str | None = None,
) -> VerifierStamp:
    """Record (replace) the current PASS stamp of a verifier."""
    reg = read_registry(repo)
    s = VerifierStamp(
        name=name, version=version, binary_hash=binary_hash,
        golden_suite_hash=golden_suite_hash,
        stamped=now or datetime.now(UTC).isoformat(timespec="seconds"),
        declaration=declaration,
    )
    reg.stamps[name] = s
    write_registry(repo, reg)
    return s


def current_stamp(repo: Path | str, name: str) -> VerifierStamp | None:
    return read_registry(repo).stamps.get(name)


def is_current(repo: Path | str, *, name: str, version: str, binary_hash: str) -> bool:
    s = current_stamp(repo, name)
    return s is not None and s.version == version and s.binary_hash == binary_hash


def registry_newer(repo: Path | str) -> Callable[[EvidenceEntry], bool]:
    """The predicate `compute_standing` needs: True iff the registry's current stamp for
    the entry's verifier is a NEWER version, or the same version under a different
    binary hash, than the one that produced the evidence. Unknown verifiers (e.g.
    `table-import`) are never newer."""
    reg = read_registry(repo)

    def newer(entry: EvidenceEntry) -> bool:
        s = reg.stamps.get(entry.verifier)
        if s is None:
            return False
        if _version_key(s.version) > _version_key(entry.version):
            return True
        return (
            s.version == entry.version
            and entry.binary_hash is not None
            and s.binary_hash != entry.binary_hash
        )

    return newer

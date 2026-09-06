"""Claim files: the schema (charter section 3) and a deterministic YAML codec.

One file per claim at `<repo>/claims/<id>.yaml`. The schema is closed (unknown
keys are errors), ids are filename-safe, evidence and dependency paths are
repo-relative (no absolute paths, no `..`), and the VERIFIED_N-specific fields
(`n`, `coverage`) are allowed only at that level. A dependency string that
contains a `/` is a repo-relative PATH (a data manifest); anything else is a
claim id.
"""
from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

Level = Literal["REFUTED", "HEURISTIC", "CONJECTURED", "VERIFIED_N", "CERTIFIED", "FORMALIZED"]
Standing = Literal["CURRENT", "STALE", "CHALLENGED", "SUPERSEDED"]
Kind = Literal["statement", "dataset", "construction"]
Verdict = Literal["PASS", "FAIL", "ERROR"]

LEVEL_RANK: dict[str, int] = {
    "REFUTED": -1, "HEURISTIC": 0, "CONJECTURED": 1, "VERIFIED_N": 2, "CERTIFIED": 3,
    "FORMALIZED": 4,
}
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,120}$")
CLAIMS_DIRNAME = "claims"


class ClaimSchemaError(ValueError):
    """A claim file (or receipt) violates the schema; the message names the file."""


def is_path_dependency(dep: str) -> bool:
    return "/" in dep


def validate_repo_relative(path: str) -> str:
    p = PurePosixPath(path)
    if not path or path != path.strip() or "\\" in path:
        raise ValueError(f"path {path!r} must be a clean forward-slash path")
    if p.is_absolute() or any(part in ("..", "") for part in p.parts):
        raise ValueError(f"path {path!r} must be repo-relative without '..'")
    return path


class EvidenceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    verifier: str
    version: str
    verdict: Verdict
    stamped: str
    binary_hash: str | None = None
    golden_suite_hash: str | None = None
    note: str = ""

    @field_validator("path")
    @classmethod
    def _path(cls, v: str) -> str:
        return validate_repo_relative(v)


class ClaimFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    problem: str
    formulation_version: str
    kind: Kind
    statement: str
    level: Level
    substatus: Literal["PROVED_DRAFT"] | None = None
    n: int | None = None
    coverage: Literal["exhaustive", "sampled"] | None = None
    standing: Standing = "CURRENT"
    depends_on: list[str] = Field(default_factory=list)
    supersedes: list[str] = Field(default_factory=list)
    evidence: list[EvidenceEntry] = Field(default_factory=list)
    receipts: list[str] = Field(default_factory=list)
    notes: str = ""
    updated: str

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        if not _ID_RE.match(v):
            raise ValueError(f"id {v!r} is not filename-safe ([A-Za-z0-9._:-], <= 121 chars)")
        return v

    @field_validator("depends_on", "supersedes")
    @classmethod
    def _deps(cls, v: list[str]) -> list[str]:
        for dep in v:
            if is_path_dependency(dep):
                validate_repo_relative(dep)
            elif not _ID_RE.match(dep):
                raise ValueError(f"dependency {dep!r} is neither a claim id nor a repo path")
        if len(set(v)) != len(v):
            raise ValueError("duplicate entries")
        return v

    @model_validator(mode="after")
    def _level_fields(self) -> ClaimFile:
        if self.level == "VERIFIED_N":
            if self.n is None:
                raise ValueError("VERIFIED_N requires `n`")
        elif self.n is not None or self.coverage is not None:
            raise ValueError("`n` and `coverage` are VERIFIED_N-only fields")
        if self.id in self.depends_on or self.id in self.supersedes:
            raise ValueError("a claim cannot depend on or supersede itself")
        return self

    @property
    def rank(self) -> int:
        return LEVEL_RANK[self.level]


def claims_dir(repo: Path | str) -> Path:
    return Path(repo) / CLAIMS_DIRNAME


def claim_path(repo: Path | str, claim_id: str) -> Path:
    return claims_dir(repo) / f"{claim_id}.yaml"


def dump_claim(claim: ClaimFile) -> str:
    """Deterministic YAML: sorted keys, block style, unicode kept, trailing newline."""
    data = claim.model_dump(mode="json")
    return yaml.safe_dump(data, sort_keys=True, allow_unicode=True, default_flow_style=False)


def _format_validation_error(where: str, exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", ())) or "<root>"
        parts.append(f"{loc}: {err.get('msg')}")
    return f"{where}: " + "; ".join(parts)


def parse_claim(text: str, *, where: str = "<claim>") -> ClaimFile:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ClaimSchemaError(f"{where}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ClaimSchemaError(f"{where}: a claim file must be a YAML mapping")
    try:
        return ClaimFile.model_validate(data)
    except ValidationError as exc:
        raise ClaimSchemaError(_format_validation_error(where, exc)) from exc


def load_claim(path: Path | str) -> ClaimFile:
    path = Path(path)
    claim = parse_claim(path.read_text(encoding="utf-8"), where=str(path))
    if claim.id != path.stem:
        raise ClaimSchemaError(f"{path}: id {claim.id!r} does not match the filename")
    return claim


def save_claim(repo: Path | str, claim: ClaimFile) -> Path:
    path = claim_path(repo, claim.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_claim(claim), encoding="utf-8")
    return path


def load_all(repo: Path | str) -> dict[str, ClaimFile]:
    """Every `claims/*.yaml`, keyed by id; the first defect raises ClaimSchemaError."""
    out: dict[str, ClaimFile] = {}
    d = claims_dir(repo)
    if not d.is_dir():
        return out
    for path in sorted(d.glob("*.yaml")):
        claim = load_claim(path)
        if claim.id in out:  # pragma: no cover - filenames are unique on disk
            raise ClaimSchemaError(f"{path}: duplicate claim id {claim.id!r}")
        out[claim.id] = claim
    return out

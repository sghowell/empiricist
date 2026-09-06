"""Claim files: the schema (charter section 3) and a deterministic YAML codec.

One file per claim at `<repo>/claims/<id>.yaml`. The schema is closed (unknown keys and
duplicate keys are errors), ids are filename-safe, evidence and dependency paths are
canonical repo-relative POSIX paths (no absolute paths, no `..`, no `./`), dates are
ISO, and the VERIFIED_N-specific fields (`n`, `coverage`) are allowed only at that
level. A dependency string that contains a `/` is a repo-relative PATH (a data
manifest); anything else is a claim id.

Levels are earned. A claim imported from a legacy table enters at HEURISTIC with the
table's level kept in `legacy_level` (rendered "not re-earned") until `promote` reaches
it; its evidence entries carry the verdict IMPORTED, which never counts as PASS.
"""
from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

Level = Literal["REFUTED", "HEURISTIC", "CONJECTURED", "VERIFIED_N", "CERTIFIED", "FORMALIZED"]
Standing = Literal["CURRENT", "STALE", "CHALLENGED", "SUPERSEDED"]
Kind = Literal["statement", "dataset", "construction"]
Verdict = Literal["PASS", "FAIL", "ERROR", "IMPORTED"]

LEVEL_RANK: dict[str, int] = {
    "REFUTED": -1, "HEURISTIC": 0, "CONJECTURED": 1, "VERIFIED_N": 2, "CERTIFIED": 3,
    "FORMALIZED": 4,
}
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,120}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_STAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ].+)?$")
CLAIMS_DIRNAME = "claims"
TABLE_IMPORT_VERIFIER = "table-import"


class ClaimSchemaError(ValueError):
    """A claim file (or receipt) violates the schema; the message names the file."""


def is_path_dependency(dep: str) -> bool:
    return "/" in dep


def validate_repo_relative(path: str) -> str:
    """Return the canonical form of a repo-relative POSIX path, or raise ValueError."""
    if not path or path != path.strip() or "\\" in path:
        raise ValueError(f"path {path!r} must be a clean forward-slash path")
    p = PurePosixPath(path)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"path {path!r} must be repo-relative without '..'")
    canonical = str(p)
    if canonical in (".", ""):
        raise ValueError(f"path {path!r} names no file")
    return canonical


def validate_date(value: str, what: str = "date") -> str:
    if not _DATE_RE.match(value):
        raise ValueError(f"{what} {value!r} must be an ISO date (YYYY-MM-DD)")
    return value


def validate_stamp(value: str, what: str = "timestamp") -> str:
    if not _STAMP_RE.match(value):
        raise ValueError(f"{what} {value!r} must be an ISO date or date-time")
    return value


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

    @field_validator("stamped")
    @classmethod
    def _stamped(cls, v: str) -> str:
        return validate_stamp(v, "stamped")


class Source(BaseModel):
    """Where an imported claim came from: the join key a re-import uses."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["ledger", "table"]
    ref: str  # ledger artifact id (blake3 hex) or the legacy table's row id


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
    legacy_level: Level | None = None
    source: Source | None = None
    notes: str = ""
    updated: str

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        if not _ID_RE.match(v):
            raise ValueError(f"id {v!r} is not filename-safe ([A-Za-z0-9._:-], <= 121 chars)")
        return v

    @field_validator("updated")
    @classmethod
    def _updated(cls, v: str) -> str:
        return validate_date(v, "updated")

    @field_validator("depends_on", "supersedes")
    @classmethod
    def _deps(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for dep in v:
            if is_path_dependency(dep):
                canonical = validate_repo_relative(dep)
                if not is_path_dependency(canonical):
                    raise ValueError(f"path dependency {dep!r} must name a file in a directory")
                out.append(canonical)
            elif not _ID_RE.match(dep):
                raise ValueError(f"dependency {dep!r} is neither a claim id nor a repo path")
            else:
                out.append(dep)
        if len(set(out)) != len(out):
            raise ValueError("duplicate entries")
        return out

    @field_validator("receipts")
    @classmethod
    def _receipts(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("duplicate receipt ids")
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

    @property
    def legacy_pending(self) -> bool:
        """True while a legacy table's level has not been re-earned through `promote`."""
        if self.legacy_level is None or self.legacy_level == self.level:
            return False
        if self.legacy_level == "REFUTED":
            return True
        return self.rank < LEVEL_RANK[self.legacy_level]


def claims_dir(repo: Path | str) -> Path:
    return Path(repo) / CLAIMS_DIRNAME


def claim_path(repo: Path | str, claim_id: str) -> Path:
    return claims_dir(repo) / f"{claim_id}.yaml"


def dump_claim(claim: ClaimFile) -> str:
    """Deterministic YAML: sorted keys, block style, unicode kept, trailing newline."""
    data = claim.model_dump(mode="json")
    return yaml.safe_dump(data, sort_keys=True, allow_unicode=True, default_flow_style=False)


class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys (PyYAML silently keeps the last)."""

    def construct_mapping(self, node: Any, deep: bool = False) -> dict[Any, Any]:
        seen: set[Any] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                dup = key in seen
            except TypeError as exc:
                raise yaml.constructor.ConstructorError(
                    None, None, f"unhashable mapping key {key!r}", key_node.start_mark
                ) from exc
            if dup:
                raise yaml.constructor.ConstructorError(
                    None, None, f"duplicate key {key!r}", key_node.start_mark
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def load_yaml_strict(text: str) -> Any:
    return yaml.load(text, Loader=_StrictLoader)  # noqa: S506 - SafeLoader subclass


def _format_validation_error(where: str, exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", ())) or "<root>"
        parts.append(f"{loc}: {err.get('msg')}")
    return f"{where}: " + "; ".join(parts)


def parse_claim(text: str, *, where: str = "<claim>") -> ClaimFile:
    try:
        data = load_yaml_strict(text)
    except yaml.YAMLError as exc:
        raise ClaimSchemaError(f"{where}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ClaimSchemaError(f"{where}: a claim file must be a YAML mapping")
    try:
        return ClaimFile.model_validate(data)
    except ValidationError as exc:
        raise ClaimSchemaError(_format_validation_error(where, exc)) from exc


def revalidate(claim: ClaimFile) -> ClaimFile:
    """Re-run the schema on a claim built with `model_copy` (which does not validate)."""
    return ClaimFile.model_validate(claim.model_dump(mode="json"))


def load_claim(path: Path | str) -> ClaimFile:
    path = Path(path)
    claim = parse_claim(path.read_text(encoding="utf-8"), where=str(path))
    if claim.id != path.stem:
        raise ClaimSchemaError(f"{path}: id {claim.id!r} does not match the filename")
    return claim


def save_claim(repo: Path | str, claim: ClaimFile) -> Path:
    """Write `claims/<id>.yaml`. Refuses when a DIFFERENT id already owns the same
    filename case-insensitively (a case-insensitive filesystem would silently merge
    the two claims)."""
    path = claim_path(repo, claim.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    for other in path.parent.glob("*.yaml"):
        if other.stem != claim.id and other.stem.lower() == claim.id.lower():
            raise ClaimSchemaError(
                f"{path}: id {claim.id!r} collides case-insensitively with existing claim "
                f"{other.stem!r}"
            )
    path.write_text(dump_claim(claim), encoding="utf-8")
    return path


def load_all(repo: Path | str) -> dict[str, ClaimFile]:
    """Every `claims/*.yaml`, keyed by id; the first defect raises ClaimSchemaError."""
    out: dict[str, ClaimFile] = {}
    d = claims_dir(repo)
    if not d.is_dir():
        return out
    lowered: dict[str, str] = {}
    for path in sorted(d.glob("*.yaml")):
        claim = load_claim(path)
        if claim.id.lower() in lowered:
            raise ClaimSchemaError(
                f"{path}: claim id {claim.id!r} collides case-insensitively with "
                f"{lowered[claim.id.lower()]!r}"
            )
        lowered[claim.id.lower()] = claim.id
        out[claim.id] = claim
    return out

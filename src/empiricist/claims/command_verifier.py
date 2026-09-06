"""The generic command verifier (charter section 4): a declared command with hashed
inputs and golden PASS and FAIL fixtures, which makes an existing `verify.py --check`
or pytest suite admissible evidence in a research repository.

Declaration `claims/verifiers/<name>.yaml`:

    name: p8a_remainder_replay
    version: "1"
    argv: [".venv/bin/python", "-m", "p8a_remainder.verify", "--check"]  # {evidence} allowed
    cwd: "."                                        # repo-relative
    env: {PYTHONPATH: "problems/P8/a/src:..."}      # values are used verbatim
    inputs: ["problems/P8/a/.../src/p8a_remainder"] # files or directories hashed into binary_hash
    fixtures: {pass: ["<evidence path>"], fail: ["<evidence path>"]}
    timeout_s: 1800

Identity: `binary_hash` = sha256 over the declaration bytes and every input file (sorted
paths, each path + content), so editing the checked code or the declaration invalidates
the stamp. Certification runs every PASS fixture (exit 0 required) and every FAIL
fixture (non-zero exit required; a suite that cannot fail certifies nothing) and stamps
the registry with `golden_suite_hash` = sha256 over the fixture names and contents.

Trust posture: the command runs through the executor with `SandboxMode.NONE` and the
parent environment (a research repository's own venv is the point), which is why the
exact argv, cwd and env keys are written into the evidence note. Batch mode's sandbox
argument is untouched: this verifier is an interactive-mode instrument.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import time
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from empiricist.claims.lock import sha256_file
from empiricist.claims.model import ClaimSchemaError, claims_dir, validate_repo_relative
from empiricist.claims.registry import VerifierStamp, stamp
from empiricist.executor.runner import ExecSpec, execute
from empiricist.executor.sandbox import SandboxMode
from empiricist.ledger.models import Verdict
from empiricist.verifiers.base import VerifierResult

VERIFIERS_DIRNAME = "verifiers"
EVIDENCE_PLACEHOLDER = "{evidence}"
EVIDENCE_ENV = "EMPIRICIST_EVIDENCE"
MAX_INPUT_FILES = 5000


class Fixtures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passing: list[str] = Field(default_factory=list, alias="pass")
    failing: list[str] = Field(default_factory=list, alias="fail")


class CommandVerifierSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    version: str
    argv: list[str]
    cwd: str = "."
    env: dict[str, str] = Field(default_factory=dict)
    inputs: list[str] = Field(default_factory=list)
    fixtures: Fixtures
    timeout_s: float = 600.0

    def model_post_init(self, __context: Any) -> None:
        if not self.argv:
            raise ValueError("argv must not be empty")
        if self.cwd != ".":
            validate_repo_relative(self.cwd)
        for p in self.inputs + self.fixtures.passing + self.fixtures.failing:
            validate_repo_relative(p)
        if not self.fixtures.passing or not self.fixtures.failing:
            raise ValueError("a command verifier needs at least one PASS and one FAIL fixture")


def verifiers_dir(repo: Path | str) -> Path:
    return claims_dir(repo) / VERIFIERS_DIRNAME


def declaration_path(repo: Path | str, name: str) -> Path:
    return verifiers_dir(repo) / f"{name}.yaml"


def _input_files(repo: Path, inputs: list[str]) -> list[Path]:
    files: list[Path] = []
    for rel in inputs:
        p = repo / rel
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files.extend(
                f for f in sorted(p.rglob("*"))
                if f.is_file() and "__pycache__" not in f.parts and not f.name.startswith(".")
            )
        else:
            raise ClaimSchemaError(f"command verifier input {rel!r} does not exist")
    if len(files) > MAX_INPUT_FILES:
        raise ClaimSchemaError(
            f"command verifier inputs expand to {len(files)} files (> {MAX_INPUT_FILES})"
        )
    return sorted(set(files))


class CommandVerifier:
    """A declared command; `run` is total (never raises for an evidence path)."""

    def __init__(
        self, repo: Path | str, spec: CommandVerifierSpec, declaration_bytes: bytes
    ) -> None:
        self.repo = Path(repo).resolve()
        self.spec = spec
        self._declaration_bytes = declaration_bytes

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def version(self) -> str:
        return self.spec.version

    @property
    def binary_hash(self) -> str:
        h = hashlib.sha256()
        h.update(self._declaration_bytes)
        for f in _input_files(self.repo, self.spec.inputs):
            rel = str(f.relative_to(self.repo))
            h.update(rel.encode("utf-8"))
            h.update(b"\0")
            h.update(sha256_file(f).encode("ascii"))
            h.update(b"\n")
        return h.hexdigest()

    def argv_for(self, evidence_rel: str) -> list[str]:
        return [a.replace(EVIDENCE_PLACEHOLDER, evidence_rel) for a in self.spec.argv]

    def run(self, evidence_rel: str, *, timeout_s: float | None = None) -> VerifierResult:
        """PASS iff the command exits 0 on this evidence path (repo-relative)."""
        try:
            validate_repo_relative(evidence_rel)
        except ValueError as exc:
            return VerifierResult(
                verdict=Verdict.FAIL, details={"invalid": True, "detail": str(exc)}
            )
        if not (self.repo / evidence_rel).exists():
            return VerifierResult(
                verdict=Verdict.FAIL, details={"invalid": True, "detail": f"missing {evidence_rel}"}
            )
        argv = self.argv_for(evidence_rel)
        env = dict(self.spec.env)
        env[EVIDENCE_ENV] = evidence_rel
        spec = ExecSpec(
            argv=argv, move="VERIFY", cwd=self.repo / self.spec.cwd, env_extra=env,
            env_passthrough=True, sandbox=SandboxMode.NONE,
            timeout_s=timeout_s or self.spec.timeout_s, rss_mb=None,
        )
        started = time.monotonic()
        try:
            res = asyncio.run(execute(spec, ledger=None))
        except Exception as exc:  # noqa: BLE001 - total
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={"error": f"{type(exc).__name__}: {exc}", "argv": argv},
            )
        details: dict[str, Any] = {
            "argv": argv, "cwd": str(self.spec.cwd), "env_keys": sorted(env),
            "exit_code": res.exit_code, "wall_s": round(time.monotonic() - started, 3),
            "timed_out": bool(res.timed_out),
            "stdout_tail": res.stdout[-2000:], "stderr_tail": res.stderr[-2000:],
        }
        if res.timed_out:
            return VerifierResult(verdict=Verdict.ERROR, details={**details, "error": "timeout"})
        return VerifierResult(
            verdict=Verdict.PASS if res.exit_code == 0 else Verdict.FAIL, details=details
        )


def load_command_verifier(repo: Path | str, name: str) -> CommandVerifier:
    path = declaration_path(repo, name)
    if not path.is_file():
        raise ClaimSchemaError(f"no command verifier declaration at {path}")
    raw = path.read_bytes()
    try:
        data = yaml.safe_load(raw)
        spec = CommandVerifierSpec.model_validate(data)
    except (yaml.YAMLError, ValidationError, ValueError) as exc:
        raise ClaimSchemaError(f"{path}: invalid declaration: {exc}") from exc
    if spec.name != name:
        raise ClaimSchemaError(f"{path}: declaration name {spec.name!r} does not match {name!r}")
    return CommandVerifier(repo, spec, raw)


def golden_suite_hash(repo: Path | str, spec: CommandVerifierSpec) -> str:
    repo = Path(repo)
    h = hashlib.sha256()
    for kind, paths in (("pass", spec.fixtures.passing), ("fail", spec.fixtures.failing)):
        for rel in sorted(paths):
            h.update(f"{kind}:{rel}\0".encode())
            f = repo / rel
            h.update(sha256_file(f).encode("ascii") if f.is_file() else b"<missing>")
            h.update(b"\n")
    return h.hexdigest()


def certify_command_verifier(repo: Path | str, name: str) -> tuple[VerifierStamp | None, list[str]]:
    """Run every fixture; stamp the registry iff every PASS fixture passes and every
    FAIL fixture fails. Returns (stamp or None, the list of fixture failures)."""
    repo = Path(repo)
    v = load_command_verifier(repo, name)
    problems: list[str] = []
    for rel in v.spec.fixtures.passing:
        r = v.run(rel)
        if r.verdict is not Verdict.PASS:
            why = r.details.get("detail") or r.details.get("error") or ""
            problems.append(f"pass fixture {rel}: {r.verdict.value} {why}".strip())
    for rel in v.spec.fixtures.failing:
        r = v.run(rel)
        if r.verdict is not Verdict.FAIL:
            problems.append(f"fail fixture {rel}: {r.verdict.value} (must FAIL)")
    if problems:
        return None, problems
    s = stamp(
        repo, name=v.name, version=v.version, binary_hash=v.binary_hash,
        golden_suite_hash=golden_suite_hash(repo, v.spec),
        declaration=str(declaration_path(repo, name).relative_to(repo)),
    )
    return s, []


__all__ = [
    "CommandVerifier", "CommandVerifierSpec", "Fixtures", "certify_command_verifier",
    "declaration_path", "golden_suite_hash", "load_command_verifier", "verifiers_dir",
    "EVIDENCE_ENV", "EVIDENCE_PLACEHOLDER", "os",
]

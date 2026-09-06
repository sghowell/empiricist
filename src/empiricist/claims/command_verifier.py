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

from empiricist.claims.lock import committed_file, sha256_file
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
    # Exit codes that mean "checked and FAILED"; any other non-zero exit is an ERROR
    # (crash, usage error, missing dependency) and never mints a FAIL -- or a REFUTED.
    fail_exit_codes: list[int] = Field(default_factory=lambda: [1])

    def model_post_init(self, __context: Any) -> None:
        if not self.argv:
            raise ValueError("argv must not be empty")
        if 0 in self.fail_exit_codes or not self.fail_exit_codes:
            raise ValueError("fail_exit_codes must be non-empty and must not contain 0")
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

    def evidence_arg(self, evidence_rel: str) -> str:
        """The evidence path as the command sees it: relative to the declared cwd, and
        never option-shaped (a file named `--help` is passed as `./--help`)."""
        rel = os.path.relpath(self.repo / evidence_rel, self.repo / self.spec.cwd)
        return f"./{rel}" if rel.startswith("-") else rel

    def argv_for(self, evidence_rel: str) -> list[str]:
        arg = self.evidence_arg(evidence_rel)
        return [a.replace(EVIDENCE_PLACEHOLDER, arg) for a in self.spec.argv]

    def env_for(self, evidence_rel: str) -> dict[str, str]:
        env = dict(self.spec.env)
        env[EVIDENCE_ENV] = self.evidence_arg(evidence_rel)
        return env

    def uncovered_inputs(self) -> list[str]:
        """Repo-relative things the command executes that `inputs` does not hash: an argv
        entry that is a file in the repo, and every repo-relative PYTHONPATH entry."""
        covered = [Path(i) for i in self.spec.inputs]

        def is_covered(rel: str) -> bool:
            p = Path(rel)
            return any(p == c or c in p.parents for c in covered)

        out: list[str] = []
        for a in self.spec.argv:
            # interpreters and tools outside the repo (absolute) or inside a hidden
            # directory (.venv) are environment, not checked source
            if EVIDENCE_PLACEHOLDER in a or a.startswith(("-", "/")):
                continue
            rel = os.path.normpath(os.path.join(self.spec.cwd, a))
            if rel.startswith("..") or any(part.startswith(".") for part in Path(rel).parts):
                continue
            full = self.repo / rel
            if full.is_file() and not full.is_symlink() and not is_covered(rel):
                out.append(rel)
        for entry in self.spec.env.get("PYTHONPATH", "").split(":"):
            entry = entry.strip()
            if not entry or entry.startswith("/"):
                continue
            rel = os.path.normpath(entry)
            if (self.repo / rel).exists() and not is_covered(rel):
                out.append(rel)
        return sorted(set(out))

    def run(self, evidence_rel: str, *, timeout_s: float | None = None) -> VerifierResult:
        """PASS iff the command exits 0 on this evidence path (repo-relative)."""
        try:
            validate_repo_relative(evidence_rel)
        except ValueError as exc:
            return VerifierResult(
                verdict=Verdict.FAIL, details={"invalid": True, "detail": str(exc)}
            )
        if committed_file(self.repo, evidence_rel) is None:
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"invalid": True,
                         "detail": f"{evidence_rel} is not a committed regular file"},
            )
        argv = self.argv_for(evidence_rel)
        env = self.env_for(evidence_rel)
        env_digest = hashlib.sha256(
            "\n".join(f"{k}={v}" for k, v in sorted(env.items())).encode()
        ).hexdigest()
        # Whitelist environment (PATH/HOME/TMPDIR/LANG + the declaration's own): the
        # agent's shell never reaches the checker, so a PYTHONPATH or sitecustomize in
        # the parent process cannot change a verdict.
        spec = ExecSpec(
            argv=argv, move="VERIFY", cwd=self.repo / self.spec.cwd, env_extra=env,
            env_passthrough=False, sandbox=SandboxMode.NONE,
            timeout_s=timeout_s or self.spec.timeout_s, rss_mb=None,
        )
        started = time.monotonic()
        try:
            res = _run_blocking(execute(spec, ledger=None))
        except Exception as exc:  # noqa: BLE001 - total
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={"error": f"{type(exc).__name__}: {exc}", "argv": argv},
            )
        details: dict[str, Any] = {
            "argv": argv, "cwd": str(self.spec.cwd), "env_keys": sorted(env),
            "env_sha256": env_digest,
            "exit_code": res.exit_code, "wall_s": round(time.monotonic() - started, 3),
            "timed_out": bool(res.timed_out),
            "stdout_tail": res.stdout[-2000:], "stderr_tail": res.stderr[-2000:],
        }
        if res.timed_out:
            return VerifierResult(verdict=Verdict.ERROR, details={**details, "error": "timeout"})
        if res.exit_code == 0:
            return VerifierResult(verdict=Verdict.PASS, details=details)
        if res.exit_code in self.spec.fail_exit_codes:
            return VerifierResult(verdict=Verdict.FAIL, details=details)
        return VerifierResult(
            verdict=Verdict.ERROR,
            details={**details, "error": f"exit {res.exit_code} is not a declared FAIL code "
                     f"{self.spec.fail_exit_codes}"},
        )


def _run_blocking(coro):
    """`asyncio.run` from sync code, also when called from inside a running event loop
    (batch loops are async and call `promote` in-process): then run it in a worker."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


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
            f = committed_file(repo, rel)
            h.update(sha256_file(f).encode("ascii") if f is not None else b"<missing>")
            h.update(b"\n")
    return h.hexdigest()


def certify_command_verifier(
    repo: Path | str, name: str, *, allow_downgrade: bool = False
) -> tuple[VerifierStamp | None, list[str]]:
    """Run every fixture; stamp the registry iff every fixture is a committed file, the
    inputs cover what the command executes, every PASS fixture passes and every FAIL
    fixture genuinely fails (a missing or unreadable fixture certifies nothing).
    Returns (stamp or None, the list of problems)."""
    repo = Path(repo)
    v = load_command_verifier(repo, name)
    problems: list[str] = []
    try:
        binary_hash = v.binary_hash
    except ClaimSchemaError as exc:
        return None, [str(exc)]
    for rel in v.spec.fixtures.passing + v.spec.fixtures.failing:
        if committed_file(repo, rel) is None:
            problems.append(f"fixture {rel} is not a committed regular file")
    for rel in v.uncovered_inputs():
        problems.append(f"{rel} is executed but not listed in inputs (its edits would not "
                        "change binary_hash)")
    if problems:
        return None, problems
    for rel in v.spec.fixtures.passing:
        r = v.run(rel)
        if r.verdict is not Verdict.PASS:
            why = r.details.get("detail") or r.details.get("error") or ""
            problems.append(f"pass fixture {rel}: {r.verdict.value} {why}".strip())
    for rel in v.spec.fixtures.failing:
        r = v.run(rel)
        if r.verdict is not Verdict.FAIL or r.details.get("invalid"):
            why = r.details.get("detail") or r.details.get("error") or ""
            problems.append(
                f"fail fixture {rel}: {r.verdict.value} (must FAIL through the command) {why}"
                .strip()
            )
    if problems:
        return None, problems
    try:
        s = stamp(
            repo, name=v.name, version=v.version, binary_hash=binary_hash,
            golden_suite_hash=golden_suite_hash(repo, v.spec),
            declaration=str(declaration_path(repo, name).relative_to(repo)),
            allow_downgrade=allow_downgrade,
        )
    except ValueError as exc:
        return None, [str(exc)]
    return s, []


__all__ = [
    "CommandVerifier", "CommandVerifierSpec", "Fixtures", "certify_command_verifier",
    "declaration_path", "golden_suite_hash", "load_command_verifier", "verifiers_dir",
    "EVIDENCE_ENV", "EVIDENCE_PLACEHOLDER",
]

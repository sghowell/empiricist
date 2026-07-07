"""execute(): one audited path for every subprocess Empiricist runs.

Per spec §6: start_new_session (own pgid), scrubbed environment, darwin-safe
rlimits, sandbox seam, RSS watchdog, wall-clock timeout with killpg, bounded
output capture, and one runs row per execution when a Ledger is provided.
The finish path tolerates RunAlreadyFinishedError (crash-resume race, M1-2).
"""

from __future__ import annotations

import asyncio
import shlex
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import mkdtemp

from empiricist.config import env_fingerprint
from empiricist.executor.limits import ResourceLimits, make_preexec
from empiricist.executor.sandbox import SandboxMode, sandbox_wrap
from empiricist.executor.watchdog import RssWatchdog, kill_process_group
from empiricist.ledger.db import Ledger, RunAlreadyFinishedError
from empiricist.ledger.models import Run

_CAPTURE_CAP = 64 * 1024  # bytes kept per stream; full logs go to CAS later


@dataclass(frozen=True)
class ExecSpec:
    argv: list[str]
    move: str
    role: str | None = None
    run_id: str | None = None
    cwd: Path | None = None            # default: fresh mkdtemp per run
    env_extra: dict[str, str] = field(default_factory=dict)
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    rss_mb: float | None = None
    timeout_s: float = 600.0
    sandbox: SandboxMode = SandboxMode.SANDBOX_EXEC
    seed: int | None = None
    config_hash: str | None = None


@dataclass(frozen=True)
class ExecResult:
    run_id: str
    exit_code: int
    stdout: str
    stderr: str
    wall_s: float
    peak_rss_mb: float
    timed_out: bool
    rss_killed: bool
    output_truncated: bool
    workdir: Path


def scrub_env(workdir: Path, extra: dict[str, str]) -> dict[str, str]:
    """Whitelist-only environment: no API keys, no SSH agent, no user dotfiles."""
    env = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(workdir),
        "TMPDIR": str(workdir),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    env.update(extra)
    return env


def _decode_capped(raw: bytes) -> tuple[str, bool]:
    truncated = len(raw) > _CAPTURE_CAP
    return raw[:_CAPTURE_CAP].decode("utf-8", errors="replace"), truncated


async def execute(spec: ExecSpec, *, ledger: Ledger | None = None) -> ExecResult:
    run_id = spec.run_id or uuid.uuid4().hex
    # Resolve up front: mkdtemp under $TMPDIR yields /var/... (a symlink to
    # /private/var/...); the child's getcwd() canonicalizes, and sandbox.py's
    # profile_for() also resolves — so cwd/HOME/TMPDIR and the SBPL profile must
    # all agree on the one canonical path.
    workdir = (spec.cwd or Path(mkdtemp(prefix="empiricist-run-"))).resolve()
    argv = sandbox_wrap(spec.argv, workdir=workdir, mode=spec.sandbox)
    env = scrub_env(workdir, spec.env_extra)

    if ledger is not None:
        ledger.start_run(
            Run(
                run_id=run_id,
                move=spec.move,
                role=spec.role,
                argv=shlex.join(spec.argv),
                seed=spec.seed,
                config_hash=spec.config_hash,
                env_fingerprint=env_fingerprint(),
            )
        )

    t0 = time.monotonic()
    proc = await asyncio.create_subprocess_exec(
        *argv,
        cwd=workdir,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
        preexec_fn=make_preexec(spec.limits),
    )
    watchdog = RssWatchdog(proc.pid, spec.rss_mb)
    watch_task = asyncio.create_task(watchdog.run())

    timed_out = False
    try:
        stdout_raw, stderr_raw = await asyncio.wait_for(
            proc.communicate(), timeout=spec.timeout_s
        )
    except TimeoutError:
        timed_out = True
        # Stop the watchdog BEFORE reaping: once we reap, the pid is free to be
        # reused, and a still-polling dog could measure/kill an unrelated pid
        # (the reuse hazard the watchdog guards, closed on both sides).
        watchdog.stop()
        await watch_task
        kill_process_group(proc.pid)
        stdout_raw, stderr_raw = await proc.communicate()
    else:
        watchdog.stop()
        await watch_task

    wall_s = time.monotonic() - t0
    exit_code = proc.returncode if proc.returncode is not None else -1
    stdout, trunc_out = _decode_capped(stdout_raw)
    stderr, trunc_err = _decode_capped(stderr_raw)

    if ledger is not None:
        try:
            ledger.finish_run(
                run_id,
                exit_code=exit_code,
                wall_s=wall_s,
                peak_rss_mb=watchdog.peak_mb,
            )
        except RunAlreadyFinishedError:
            pass  # crash-resume race: reconcile_orphans got there first (M1-2)

    return ExecResult(
        run_id=run_id,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        wall_s=wall_s,
        peak_rss_mb=watchdog.peak_mb,
        timed_out=timed_out,
        rss_killed=watchdog.killed,
        output_truncated=trunc_out or trunc_err,
        workdir=workdir,
    )

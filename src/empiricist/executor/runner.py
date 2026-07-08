"""execute(): one audited path for every subprocess Empiricist runs.

Per spec §6: start_new_session (own pgid), scrubbed environment, darwin-safe
rlimits, sandbox seam, RSS watchdog, wall-clock timeout with killpg, bounded
output capture, and one runs row per execution when a Ledger is provided.
The finish path tolerates RunAlreadyFinishedError (crash-resume race, M1-2).
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import shlex
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import mkdtemp

from empiricist.config import env_fingerprint
from empiricist.executor.limits import ResourceLimits, make_preexec
from empiricist.executor.sandbox import SandboxMode, sandbox_wrap
from empiricist.executor.watchdog import (
    RssWatchdog,
    kill_process_group,
    reap_process_group,
)
from empiricist.ledger.db import Ledger, RunAlreadyFinishedError
from empiricist.ledger.models import Run

_CAPTURE_CAP = 64 * 1024  # bytes kept per stream; full logs go to CAS later

# Distinct from watchdog kills (-9) and the ledger's ORPHANED_EXIT_CODE (-999):
# marks a run whose subprocess never actually started (spawn raised).
SPAWN_FAILED_EXIT_CODE = -998

# Returned when a subprocess's returncode is somehow unavailable after reaping.
UNKNOWN_EXIT_CODE = -997


class DuplicateRunError(Exception):
    """A run_id already exists in the ledger (caller-supplied collision)."""


@dataclass(frozen=True)
class ExecSpec:
    argv: list[str]
    move: str
    role: str | None = None
    run_id: str | None = None
    cwd: Path | None = None            # default: fresh mkdtemp per run
    env_extra: dict[str, str] = field(default_factory=dict)
    env_passthrough: bool = False   # True: inherit the full parent env (TRUSTED
                                    # subprocesses only, e.g. the claude CLI which
                                    # needs real HOME/PATH/keychain for auth)
    capture_cap: int = _CAPTURE_CAP  # per-stream stdout/stderr byte cap
    # Safe-by-default ceilings (opt-out): bound a runaway leak/write without
    # breaking legit harness code. M4/M5/M6 tune per-move.
    limits: ResourceLimits = field(
        default_factory=lambda: ResourceLimits(fsize_mb=1024)
    )
    rss_mb: float | None = 4096.0
    timeout_s: float = 600.0
    drain_grace_s: float = 10.0  # max wait for post-kill pipe EOF before abandoning
    sandbox: SandboxMode = SandboxMode.SANDBOX_EXEC
    # SANDBOX_EXEC only: deny process-fork/exec* (except this spec's own argv[0]),
    # so an untrusted subprocess cannot spawn a persistent child. Used by the Lean
    # compile gate (closes the M8 5th-break detached-child TOCTOU at the source).
    deny_subprocess: bool = False
    seed: int | None = None
    config_hash: str | None = None


@dataclass(frozen=True)
class ExecResult:
    run_id: str
    exit_code: int
    stdout: str
    stderr: str
    wall_s: float
    peak_rss_mb: float | None
    timed_out: bool
    rss_killed: bool
    output_truncated: bool
    workdir: Path
    drain_abandoned: bool = False


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


def _decode_capped(raw: bytes, cap: int) -> tuple[str, bool]:
    truncated = len(raw) > cap
    return raw[:cap].decode("utf-8", errors="replace"), truncated


async def execute(spec: ExecSpec, *, ledger: Ledger | None = None) -> ExecResult:
    run_id = spec.run_id or uuid.uuid4().hex
    # Resolve up front: mkdtemp under $TMPDIR yields /var/... (a symlink to
    # /private/var/...); the child's getcwd() canonicalizes, and sandbox.py's
    # profile_for() also resolves — so cwd/HOME/TMPDIR and the SBPL profile must
    # all agree on the one canonical path.
    workdir = (spec.cwd or Path(mkdtemp(prefix="empiricist-run-"))).resolve()
    # NOTE (M5): workdir cleanup is deferred to M5/CAS wiring (runs keep their
    # dir for now); and the full-buffer-before-truncation OOM risk (communicate()
    # reads the whole stream before _decode_capped) is deferred until
    # model-authored code lands (D11) — both v0-acceptable: v0 executed code is
    # harness-authored.
    argv = sandbox_wrap(
        spec.argv, workdir=workdir, mode=spec.sandbox,
        deny_subprocess=spec.deny_subprocess,
    )
    if spec.env_passthrough and spec.sandbox is not SandboxMode.NONE:
        raise ValueError(
            "env_passthrough=True requires sandbox=NONE: the full parent env "
            "(secrets) must never enter a sandboxed/untrusted subprocess"
        )
    if spec.env_passthrough:
        env = {**os.environ, **spec.env_extra}  # trusted: full inherit + overrides
    else:
        env = scrub_env(workdir, spec.env_extra)

    if ledger is not None:
        try:
            ledger.start_run(
                Run(
                    run_id=run_id, move=spec.move, role=spec.role,
                    argv=shlex.join(spec.argv), seed=spec.seed,
                    config_hash=spec.config_hash, env_fingerprint=env_fingerprint(),
                )
            )
        except sqlite3.IntegrityError as e:
            raise DuplicateRunError(run_id) from e

    t0 = time.monotonic()
    proc: asyncio.subprocess.Process | None = None
    watchdog: RssWatchdog | None = None
    watch_task: asyncio.Task | None = None

    def _peak() -> float | None:
        return watchdog.peak_mb if (watchdog is not None and watchdog.sampled) else None

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv, cwd=workdir, env=env,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            start_new_session=True, preexec_fn=make_preexec(spec.limits),
        )
        watchdog = RssWatchdog(proc.pid, spec.rss_mb)
        watch_task = asyncio.create_task(watchdog.run())
        comm_task = asyncio.create_task(proc.communicate())

        timed_out = False
        drain_abandoned = False
        try:
            # shield keeps comm_task alive across a wait_for timeout, so the bytes
            # it already read are NOT discarded (a plain double-communicate loses them).
            stdout_raw, stderr_raw = await asyncio.wait_for(
                asyncio.shield(comm_task), timeout=spec.timeout_s
            )
            watchdog.stop()
            await watch_task
            # Normal completion: communicate() reaped the group LEADER, but a
            # detached same-group child (untrusted compile-time spawn, no setsid)
            # can outlive it and keep acting after execute() returns — the M8
            # 5th-break olean-swap TOCTOU depended on exactly such a survivor. Reap
            # the whole group by pgid so NO straggler survives any execute() call.
            reap_process_group(proc.pid)
        except TimeoutError:
            timed_out = True
            # stop+await the watchdog BEFORE kill+reap (PID-reuse interlock),
            # then resume the SAME comm_task to collect the pre-timeout output.
            watchdog.stop()
            await watch_task
            kill_process_group(proc.pid)
            try:
                # Bounded: the normal case (group killed -> EOF) completes fast and
                # preserves the pre-timeout bytes (FIX A). But a descendant that
                # setsid()/daemonized while holding our stdout escapes the group
                # kill, so EOF never comes -> we must NOT wait forever. The
                # wall-clock bound has to hold even against a pipe-holding escapee.
                stdout_raw, stderr_raw = await asyncio.wait_for(
                    comm_task, timeout=spec.drain_grace_s
                )
            except TimeoutError:
                drain_abandoned = True
                comm_task.cancel()
                with contextlib.suppress(BaseException):
                    await comm_task
                stdout_raw, stderr_raw = b"", b""
    except BaseException:
        # Spawn failure or any mid-flight error: contain the child, close the run
        # row with a real failure code (never leave it open -> ORPHANED), re-raise.
        if watchdog is not None:
            watchdog.stop()
        if watch_task is not None:
            with contextlib.suppress(BaseException):
                await watch_task
        if proc is not None and proc.returncode is None:
            kill_process_group(proc.pid)
            with contextlib.suppress(BaseException):
                await proc.wait()
        if ledger is not None:
            with contextlib.suppress(RunAlreadyFinishedError, KeyError):
                ledger.finish_run(
                    run_id, exit_code=SPAWN_FAILED_EXIT_CODE,
                    wall_s=time.monotonic() - t0, peak_rss_mb=_peak(),
                )
        raise

    wall_s = time.monotonic() - t0
    exit_code = proc.returncode if proc.returncode is not None else UNKNOWN_EXIT_CODE
    stdout, trunc_out = _decode_capped(stdout_raw, spec.capture_cap)
    stderr, trunc_err = _decode_capped(stderr_raw, spec.capture_cap)
    peak = _peak()

    if ledger is not None:
        with contextlib.suppress(RunAlreadyFinishedError):
            ledger.finish_run(
                run_id, exit_code=exit_code, wall_s=wall_s, peak_rss_mb=peak,
            )

    return ExecResult(
        run_id=run_id, exit_code=exit_code, stdout=stdout, stderr=stderr,
        wall_s=wall_s, peak_rss_mb=peak, timed_out=timed_out,
        rss_killed=watchdog.killed, output_truncated=trunc_out or trunc_err,
        workdir=workdir, drain_abandoned=drain_abandoned,
    )

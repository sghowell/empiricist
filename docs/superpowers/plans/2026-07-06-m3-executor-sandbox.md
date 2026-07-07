# Empiricist M3: Executor + darwin sandbox — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every subprocess Empiricist runs (verifiers, enumerators, solvers, model calls) goes through one audited executor: darwin-safe resource limits, a `sandbox-exec` deny-network/FS-confine seam, a psutil RSS watchdog (the *only* working memory bound on macOS), and a `runs` row per execution.

**Architecture:** `executor/limits.py` (preexec rlimits — deliberately no `RLIMIT_AS`), `executor/sandbox.py` (the `sandbox_wrap()` seam: NONE | SANDBOX_EXEC | CONTAINER-flag), `executor/watchdog.py` (async RSS poller, SIGKILL-the-pgid on breach), `executor/runner.py` (`execute(spec)`: async subprocess w/ `start_new_session`, env-scrub, wall-clock timeout → killpg, bounded output capture, optional Ledger runs-row wiring). Tests exercise *real* processes — real CPU/FSIZE kills, real sandbox denials, real memory breaches — no mocks.

**Tech Stack:** Python 3.11 asyncio + stdlib `resource`/`signal`/`tempfile`, `psutil` (new dep), macOS `/usr/bin/sandbox-exec` (present on this box; smoke-tested).

**Reference:** spec §6 + D8 (docs/superpowers/specs/2026-07-06-empiricist-harness-design.md). Carried-forward contracts from M1–2: executor cleanup must tolerate `RunAlreadyFinishedError` (crash-resume race); `ORPHANED_EXIT_CODE = -999` is reserved by `reconcile_orphans` (a timeout/RSS SIGKILL surfaces as `-9`, distinct by design); every run must record argv, env fingerprint, wall, peak RSS.

**Branch:** `feat/m3-executor-sandbox` off `feat/m1-2-scaffold-ledger` (stacked; rebase onto main after the M1–2 PR merges).

**Darwin-only tests:** sandbox tests are guarded `@pytest.mark.skipif(sys.platform != "darwin", ...)`. Limits/watchdog/runner tests are POSIX-generic.

---

### Task 1: Branch, psutil dep, executor package skeleton

**Files:**
- Modify: `pyproject.toml`
- Create: `src/empiricist/executor/__init__.py`

- [ ] **Step 1: Create branch**

```bash
git switch feat/m1-2-scaffold-ledger && git switch -c feat/m3-executor-sandbox
```

- [ ] **Step 2: Add psutil**

In `pyproject.toml` change the dependencies list to:

```toml
dependencies = [
    "blake3>=1.0",
    "psutil>=6.0",
]
```

- [ ] **Step 3: Package init**

`src/empiricist/executor/__init__.py`:

```python
"""The executor: sandboxed subprocess execution with total provenance.

The model never gets a shell (spec §6). Everything Empiricist runs —
verifiers, enumerators, solvers, model CLI calls — flows through
runner.execute(), which applies darwin-safe resource limits, the
sandbox seam, the RSS watchdog, and emits one runs row per execution.
"""
```

- [ ] **Step 4: Lock, sync, verify**

```bash
uv lock && uv sync
uv run python -c "import psutil; print(psutil.__version__)"
uv run pytest -q
```

Expected: psutil version prints; 79 passed.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock src/empiricist/executor/__init__.py
git commit -m "feat: executor package skeleton + psutil dependency"
```

---

### Task 2: Resource limits (`executor/limits.py`)

**Files:**
- Create: `src/empiricist/executor/limits.py`
- Test: `tests/test_limits.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_limits.py`:

```python
"""Tests for darwin-safe rlimits. Real child processes, real signals."""

import signal
import subprocess
import sys

from empiricist.executor.limits import ResourceLimits, make_preexec


def run_py(code: str, limits: ResourceLimits, timeout: float = 30.0):
    return subprocess.run(
        [sys.executable, "-I", "-S", "-c", code],
        preexec_fn=make_preexec(limits),
        capture_output=True,
        timeout=timeout,
    )


def test_cpu_limit_kills_busy_loop():
    res = run_py("while True: pass", ResourceLimits(cpu_s=1))
    assert res.returncode == -signal.SIGXCPU


def test_fsize_limit_kills_big_write(tmp_path):
    code = (
        f"open({str(tmp_path / 'big')!r}, 'wb').write(b'x' * (8 * 1024 * 1024))"
    )
    res = run_py(code, ResourceLimits(fsize_mb=1))
    # Python may surface EFBIG as OSError before the signal delivery kills it;
    # either way the write must not succeed.
    assert res.returncode != 0
    assert (tmp_path / "big").stat().st_size <= 1024 * 1024


def test_core_dumps_disabled():
    res = run_py(
        "import resource; s, h = resource.getrlimit(resource.RLIMIT_CORE);"
        " print(s, h)",
        ResourceLimits(),
    )
    assert res.stdout.strip() == b"0 0"


def test_nofile_applied():
    res = run_py(
        "import resource; print(resource.getrlimit(resource.RLIMIT_NOFILE)[0])",
        ResourceLimits(nofile=64),
    )
    assert res.stdout.strip() == b"64"


def test_no_rlimit_as_is_set():
    """RLIMIT_AS is a silent no-op on macOS (spec D8): the module must not
    pretend to bound memory via rlimits — that is the watchdog's job."""
    import inspect

    from empiricist.executor import limits as mod

    assert "RLIMIT_AS" not in inspect.getsource(mod)


def test_ok_process_unaffected():
    res = run_py("print('fine')", ResourceLimits(cpu_s=5, fsize_mb=1))
    assert res.returncode == 0 and res.stdout.strip() == b"fine"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_limits.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/empiricist/executor/limits.py`**

```python
"""Darwin-safe rlimits applied in the child via preexec_fn.

RLIMIT_AS is DELIBERATELY absent: macOS silently ignores it (verified in
the research sweep; spec D8), so a naive "memory rlimit" would be a false
sense of safety. Memory is bounded by the psutil RSS watchdog instead.
"""

from __future__ import annotations

import resource
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceLimits:
    cpu_s: int | None = None        # RLIMIT_CPU: SIGXCPU on breach
    fsize_mb: int | None = None     # RLIMIT_FSIZE: EFBIG/SIGXFSZ on breach
    nofile: int = 256               # RLIMIT_NOFILE
    # core dumps are always disabled: model-proposed code must not leave
    # memory images on disk.


def make_preexec(limits: ResourceLimits) -> Callable[[], None]:
    """Build the preexec_fn. Runs in the forked child before exec —
    keep it async-signal-safe: setrlimit only, no allocation-heavy work."""

    def _apply() -> None:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_NOFILE, (limits.nofile, limits.nofile))
        if limits.cpu_s is not None:
            resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_s, limits.cpu_s))
        if limits.fsize_mb is not None:
            nbytes = limits.fsize_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_FSIZE, (nbytes, nbytes))

    return _apply
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_limits.py -v`
Expected: 6 PASS (the CPU test takes ~1 s)

- [ ] **Step 5: Commit**

```bash
git add src/empiricist/executor/limits.py tests/test_limits.py
git commit -m "feat: darwin-safe child rlimits (CPU/FSIZE/CORE=0/NOFILE; no RLIMIT_AS)"
```

---

### Task 3: Sandbox seam (`executor/sandbox.py`)

**Files:**
- Create: `src/empiricist/executor/sandbox.py`
- Test: `tests/test_sandbox.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_sandbox.py`:

```python
"""Tests for the sandbox seam. Darwin-only: exercises real sandbox-exec."""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from empiricist.executor.sandbox import SandboxMode, sandbox_wrap

darwin_only = pytest.mark.skipif(
    sys.platform != "darwin", reason="sandbox-exec is macOS-only"
)


@pytest.fixture()
def workdir(tmp_path):
    return tmp_path


def run_sandboxed(code: str, workdir: Path, timeout: float = 30.0):
    argv = sandbox_wrap(
        [sys.executable, "-I", "-S", "-c", code],
        workdir=workdir,
        mode=SandboxMode.SANDBOX_EXEC,
    )
    return subprocess.run(argv, capture_output=True, timeout=timeout, cwd=workdir)


def test_none_mode_is_passthrough(workdir):
    argv = ["echo", "hi"]
    assert sandbox_wrap(argv, workdir=workdir, mode=SandboxMode.NONE) == argv


def test_container_mode_is_v01_flag(workdir):
    with pytest.raises(NotImplementedError):
        sandbox_wrap(["echo"], workdir=workdir, mode=SandboxMode.CONTAINER)


@darwin_only
def test_network_denied(workdir):
    res = run_sandboxed(
        "import socket; socket.create_connection(('1.1.1.1', 80), timeout=3)",
        workdir,
    )
    assert res.returncode != 0
    assert b"denied" in res.stderr.lower() or b"error" in res.stderr.lower()


@darwin_only
def test_localhost_also_denied(workdir):
    res = run_sandboxed(
        "import socket; s = socket.socket(); s.connect(('127.0.0.1', 22))",
        workdir,
    )
    assert res.returncode != 0


@darwin_only
def test_write_outside_workdir_denied(workdir):
    outside = Path(tempfile.mkdtemp(prefix="empiricist-outside-"))
    target = outside / "escape.txt"
    res = run_sandboxed(
        f"open({str(target)!r}, 'w').write('escaped')",
        workdir,
    )
    assert res.returncode != 0
    assert not target.exists()


@darwin_only
def test_write_inside_workdir_allowed(workdir):
    res = run_sandboxed(
        f"open({str(workdir / 'ok.txt')!r}, 'w').write('fine')",
        workdir,
    )
    assert res.returncode == 0, res.stderr
    assert (workdir / "ok.txt").read_text() == "fine"


@darwin_only
def test_reads_still_allowed(workdir):
    res = run_sandboxed("print(open('/etc/hosts').readline() != '')", workdir)
    assert res.returncode == 0 and b"True" in res.stdout


def test_workdir_with_unsafe_chars_rejected(tmp_path):
    bad = tmp_path / 'evil")(allow default'
    bad.mkdir()
    with pytest.raises(ValueError):
        sandbox_wrap(["echo"], workdir=bad, mode=SandboxMode.SANDBOX_EXEC)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_sandbox.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/empiricist/executor/sandbox.py`**

```python
"""The sandbox seam (spec §6, D8): one function wraps an argv for isolation.

v0 backend: /usr/bin/sandbox-exec with a generated SBPL profile — deny all
network, deny file writes outside the per-run workdir. Deprecated by Apple
but functional; it is defense-in-depth, not the primary safety argument
(the model never gets a shell, and all v0 verifier code is harness-authored).
The CONTAINER mode is the flagged v0.1 upgrade path (Apple `container`
microVM) for hostile CERTIFIED-tier runs.
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path

# SBPL string literals cannot escape arbitrary bytes portably; mkdtemp paths
# are [A-Za-z0-9_./-] so anything else is rejected rather than quoted.
_SAFE_PATH = re.compile(r"[A-Za-z0-9_./-]+\Z")

_PROFILE = """\
(version 1)
(allow default)
(deny network*)
(deny file-write*)
(allow file-write*
  (subpath "{workdir}")
  (literal "/dev/null"))
"""


class SandboxMode(StrEnum):
    NONE = "none"                  # trusted harness code / tests only
    SANDBOX_EXEC = "sandbox-exec"  # v0 default for anything model-adjacent
    CONTAINER = "container"        # v0.1: Apple container microVM (flagged)


def profile_for(workdir: Path) -> str:
    resolved = str(workdir.resolve())
    if not _SAFE_PATH.fullmatch(resolved):
        raise ValueError(f"workdir path unsafe for SBPL literal: {resolved!r}")
    return _PROFILE.format(workdir=resolved)


def sandbox_wrap(
    argv: list[str], *, workdir: Path, mode: SandboxMode
) -> list[str]:
    """Wrap argv for execution under the chosen isolation mode."""
    if mode is SandboxMode.NONE:
        return list(argv)
    if mode is SandboxMode.SANDBOX_EXEC:
        return ["/usr/bin/sandbox-exec", "-p", profile_for(workdir), *argv]
    raise NotImplementedError(
        "container isolation is the flagged v0.1 upgrade path (spec D8)"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_sandbox.py -v`
Expected: 9 PASS on darwin (2 pass + 7 darwin-only). If `test_network_denied` is slow, that's the 3 s socket timeout — acceptable.

- [ ] **Step 5: Commit**

```bash
git add src/empiricist/executor/sandbox.py tests/test_sandbox.py
git commit -m "feat: sandbox-exec seam (deny network, FS-confine to workdir)"
```

---

### Task 4: RSS watchdog (`executor/watchdog.py`)

**Files:**
- Create: `src/empiricist/executor/watchdog.py`
- Test: `tests/test_watchdog.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_watchdog.py`:

```python
"""Tests for the psutil RSS watchdog — the only working memory bound on macOS."""

import asyncio
import signal
import sys

from empiricist.executor.watchdog import RssWatchdog


async def spawn_py(code: str):
    return await asyncio.create_subprocess_exec(
        sys.executable, "-I", "-S", "-c", code,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )


def test_breach_kills_process_group():
    async def scenario():
        # Allocate ~300 MB then idle; watchdog capped at 64 MB must kill it.
        proc = await spawn_py(
            "x = bytearray(300 * 1024 * 1024)\n"
            "import time; time.sleep(60)"
        )
        dog = RssWatchdog(proc.pid, rss_mb=64.0)
        task = asyncio.create_task(dog.run())
        rc = await asyncio.wait_for(proc.wait(), timeout=30)
        dog.stop()
        await task
        return rc, dog

    rc, dog = asyncio.run(scenario())
    assert rc == -signal.SIGKILL
    assert dog.killed is True
    assert dog.peak_mb > 64.0


def test_normal_process_untouched_and_peak_recorded():
    async def scenario():
        proc = await spawn_py(
            "x = bytearray(32 * 1024 * 1024)\nprint('ok')"
        )
        dog = RssWatchdog(proc.pid, rss_mb=512.0)
        task = asyncio.create_task(dog.run())
        rc = await asyncio.wait_for(proc.wait(), timeout=30)
        dog.stop()
        await task
        return rc, dog

    rc, dog = asyncio.run(scenario())
    assert rc == 0
    assert dog.killed is False
    assert dog.peak_mb > 0.0


def test_no_limit_only_observes():
    async def scenario():
        proc = await spawn_py("x = bytearray(64 * 1024 * 1024)\nprint('ok')")
        dog = RssWatchdog(proc.pid, rss_mb=None)
        task = asyncio.create_task(dog.run())
        rc = await asyncio.wait_for(proc.wait(), timeout=30)
        dog.stop()
        await task
        return rc, dog

    rc, dog = asyncio.run(scenario())
    assert rc == 0 and dog.killed is False and dog.peak_mb > 0.0


def test_already_dead_process_is_a_noop():
    async def scenario():
        proc = await spawn_py("pass")
        await proc.wait()
        dog = RssWatchdog(proc.pid, rss_mb=1.0)
        await dog.run()  # must return promptly, not raise
        return dog

    dog = asyncio.run(scenario())
    assert dog.killed is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_watchdog.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/empiricist/executor/watchdog.py`**

```python
"""Parent-side RSS watchdog (spec D8).

RLIMIT_AS is silently ignored on macOS, so this poll-and-SIGKILL loop is
the only working memory bound short of a VM. It measures the whole process
group (root + recursive children) and records peak RSS for the runs row.
"""

from __future__ import annotations

import asyncio
import os
import signal

import psutil


def kill_process_group(pid: int) -> None:
    """SIGKILL the process group; quiet if it is already gone."""
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _rss_bytes(proc: psutil.Process) -> int:
    total = 0
    try:
        total += proc.memory_info().rss
        for child in proc.children(recursive=True):
            try:
                total += child.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        raise psutil.NoSuchProcess(proc.pid) from None
    return total


class RssWatchdog:
    """Poll a process group's RSS; SIGKILL on breach; record the peak."""

    def __init__(
        self, pid: int, rss_mb: float | None, *, poll_s: float = 0.05
    ) -> None:
        self._pid = pid
        self._rss_mb = rss_mb
        self._poll_s = poll_s
        self._stopped = False
        self.peak_mb: float = 0.0
        self.killed: bool = False

    def stop(self) -> None:
        self._stopped = True

    async def run(self) -> None:
        try:
            proc = psutil.Process(self._pid)
        except psutil.NoSuchProcess:
            return
        while not self._stopped:
            try:
                rss = _rss_bytes(proc)
            except psutil.NoSuchProcess:
                return
            self.peak_mb = max(self.peak_mb, rss / (1024 * 1024))
            if self._rss_mb is not None and self.peak_mb > self._rss_mb:
                self.killed = True
                kill_process_group(self._pid)
                return
            await asyncio.sleep(self._poll_s)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_watchdog.py -v`
Expected: 4 PASS (a few seconds — real allocations)

- [ ] **Step 5: Commit**

```bash
git add src/empiricist/executor/watchdog.py tests/test_watchdog.py
git commit -m "feat: psutil RSS watchdog (poll pgid, SIGKILL on breach, peak recording)"
```

---

### Task 5: Runner (`executor/runner.py`)

**Files:**
- Create: `src/empiricist/executor/runner.py`
- Test: `tests/test_runner.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_runner.py`:

```python
"""Tests for execute(): real subprocesses, provenance, timeout/kill paths."""

import asyncio
import signal
import sys

import pytest

from empiricist.executor.limits import ResourceLimits
from empiricist.executor.runner import ExecSpec, execute
from empiricist.executor.sandbox import SandboxMode
from empiricist.ledger.db import Ledger


def run(spec: ExecSpec, ledger=None):
    return asyncio.run(execute(spec, ledger=ledger))


def py_spec(code: str, **kw):
    defaults = dict(
        argv=[sys.executable, "-I", "-S", "-c", code],
        move="TEST",
        sandbox=SandboxMode.NONE,
        timeout_s=30.0,
    )
    defaults.update(kw)
    return ExecSpec(**defaults)


def test_happy_path_captures_output_and_times():
    res = run(py_spec("print('out'); import sys; print('err', file=sys.stderr)"))
    assert res.exit_code == 0
    assert res.stdout.strip() == "out" and res.stderr.strip() == "err"
    assert res.wall_s > 0 and not res.timed_out and not res.rss_killed


def test_nonzero_exit_propagates():
    res = run(py_spec("raise SystemExit(3)"))
    assert res.exit_code == 3


def test_timeout_kills_process_group():
    res = run(py_spec("import time; time.sleep(60)", timeout_s=1.0))
    assert res.timed_out is True
    assert res.exit_code == -signal.SIGKILL
    assert res.wall_s < 10


def test_rss_breach_flagged():
    res = run(
        py_spec(
            "x = bytearray(300 * 1024 * 1024)\nimport time; time.sleep(60)",
            rss_mb=64.0,
            timeout_s=30.0,
        )
    )
    assert res.rss_killed is True
    assert res.exit_code == -signal.SIGKILL
    assert res.peak_rss_mb > 64.0


def test_env_is_scrubbed():
    res = run(py_spec("import os; print(sorted(os.environ))"))
    leaked = {"ANTHROPIC_API_KEY", "AWS_SECRET_ACCESS_KEY", "SSH_AUTH_SOCK"}
    listed = set(eval(res.stdout.strip()))  # list of env var names
    assert not (leaked & listed)
    assert "PATH" in listed and "HOME" in listed and "TMPDIR" in listed


def test_child_runs_in_own_process_group():
    res = run(py_spec("import os; print(os.getpgid(0) == os.getpid())"))
    assert res.stdout.strip() == "True"


def test_workdir_is_fresh_and_home():
    res = run(py_spec("import os; print(os.getcwd() == os.environ['HOME'])"))
    assert res.stdout.strip() == "True"


def test_output_truncation():
    res = run(py_spec("print('x' * (2 * 1024 * 1024))"))
    assert res.exit_code == 0
    assert len(res.stdout) <= 64 * 1024 + 100
    assert res.output_truncated is True


def test_limits_are_applied():
    res = run(py_spec("while True: pass", limits=ResourceLimits(cpu_s=1)))
    assert res.exit_code == -signal.SIGXCPU


def test_ledger_wiring_records_run(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    res = run(py_spec("print('hi')", move="ENUMERATE", role="toolless"), ledger=lg)
    row = lg.get_run(res.run_id)
    assert row.move == "ENUMERATE" and row.role == "toolless"
    assert row.exit_code == 0 and row.ended is not None
    assert row.wall_s > 0 and row.peak_rss_mb is not None
    assert row.argv and "print" in row.argv
    assert row.env_fingerprint and "python" in row.env_fingerprint
    lg.close()


def test_ledger_wiring_records_failure(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    res = run(py_spec("import time; time.sleep(60)", timeout_s=1.0), ledger=lg)
    row = lg.get_run(res.run_id)
    assert row.exit_code == -signal.SIGKILL and row.ended is not None
    lg.close()


@pytest.mark.skipif(sys.platform != "darwin", reason="sandbox-exec is macOS-only")
def test_sandboxed_execution_end_to_end():
    res = run(
        py_spec(
            "import socket\n"
            "try:\n"
            "    socket.create_connection(('1.1.1.1', 80), timeout=3)\n"
            "    print('NETWORK-ESCAPED')\n"
            "except OSError:\n"
            "    print('confined')\n",
            sandbox=SandboxMode.SANDBOX_EXEC,
        )
    )
    assert res.exit_code == 0
    assert res.stdout.strip() == "confined"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_runner.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/empiricist/executor/runner.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_runner.py -v`
Expected: 12 PASS (several seconds: real timeouts, real allocations)

Note: `asyncio.wait_for` raises `TimeoutError` (Python ≥3.11 alias of `asyncio.TimeoutError`) — the `except TimeoutError` above is correct on 3.11.

- [ ] **Step 5: Full suite + lint**

Run: `uv run pytest && uv run ruff check src tests`
Expected: 79 + 6 + 9 + 4 + 12 = 110 passed (darwin), no lint errors.

- [ ] **Step 6: Commit**

```bash
git add src/empiricist/executor/runner.py tests/test_runner.py
git commit -m "feat: audited subprocess runner (scrub/limits/sandbox/watchdog/runs rows)"
```

---

### Task 6: Closeout — full verification, push

**Files:** none new

- [ ] **Step 1: Full suite + lint**

Run: `uv run pytest -v && uv run ruff check src tests`
Expected: 110 passed on darwin, lint clean.

- [ ] **Step 2: Containment smoke (manual)**

```bash
uv run python - <<'EOF'
import asyncio, sys
from empiricist.executor.runner import ExecSpec, execute
from empiricist.executor.sandbox import SandboxMode

spec = ExecSpec(
    argv=[sys.executable, "-I", "-S", "-c",
          "import urllib.request\n"
          "try:\n"
          "    urllib.request.urlopen('http://example.com', timeout=3)\n"
          "    print('ESCAPED')\n"
          "except Exception as e:\n"
          "    print('confined:', type(e).__name__)"],
    move="SMOKE", sandbox=SandboxMode.SANDBOX_EXEC, timeout_s=30.0,
)
res = asyncio.run(execute(spec))
assert "confined" in res.stdout and "ESCAPED" not in res.stdout, res
print("containment smoke OK:", res.stdout.strip())
EOF
```

Expected: `containment smoke OK: confined: URLError`

- [ ] **Step 3: Push**

```bash
git push -u origin feat/m3-executor-sandbox
```

PR (manual or `gh` if authenticated): base `feat/m1-2-scaffold-ledger` (stacked) or `main` after M1–2 merges. Title: "M3: executor + darwin sandbox".

---

## Plan self-review (done at write time)

- **Spec coverage (§6/D8):** runner w/ runs rows ✅ (T5); sandbox seam + deny-network + FS-confine ✅ (T3); darwin rlimits w/o RLIMIT_AS ✅ (T2, incl. a test that pins the *absence*); psutil watchdog + peak RSS ✅ (T4); env-scrub + `python -I -S` ✅ (T5); start_new_session + killpg on timeout ✅ (T4/T5); container upgrade path as flagged NotImplementedError ✅ (T3); M1–2 carried contracts (RunAlreadyFinishedError tolerance, sentinel non-collision) ✅ (T5).
- **Placeholder scan:** none.
- **Type consistency:** `ResourceLimits`/`make_preexec` (T2) match T5's usage; `SandboxMode`/`sandbox_wrap` (T3) match T5; `RssWatchdog(pid, rss_mb)`/`.peak_mb`/`.killed`/`kill_process_group` (T4) match T5; `Ledger.start_run/finish_run/get_run` and `Run` fields match M1–2's landed API (verified against the actual code, incl. `RunAlreadyFinishedError` and `env_fingerprint()`).
- **Known judgment calls, for reviewers:** `preexec_fn` with asyncio is safe here (single-threaded event loop at spawn time); output capture is capped at 64 KiB per stream with full logs deferred to CAS wiring (M5+); `test_env_is_scrubbed` uses `eval` on trusted test output (own subprocess).

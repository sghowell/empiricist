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
    # sleep so the child outlives one watchdog poll (0.1s): peak_rss_mb is None
    # until the dog takes a sample (FIX D), and a bare print() exits in ~10ms.
    res = run(
        py_spec(
            "print('hi')\nimport time; time.sleep(0.3)",
            move="ENUMERATE",
            role="toolless",
        ),
        ledger=lg,
    )
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


def test_timeout_preserves_partial_output():
    res = run(py_spec(
        "import sys, time\n"
        "print('MARKER-BEFORE-HANG', flush=True)\n"
        "time.sleep(60)\n",
        timeout_s=1.0,
    ))
    assert res.timed_out is True
    assert "MARKER-BEFORE-HANG" in res.stdout  # output before the hang is NOT lost


def test_spawn_failure_closes_run_row_and_reraises(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    spec = ExecSpec(argv=["/nonexistent/empiricist-binary"], move="TEST",
                    sandbox=SandboxMode.NONE, run_id="spawnfail")
    with pytest.raises(FileNotFoundError):
        asyncio.run(execute(spec, ledger=lg))
    row = lg.get_run("spawnfail")
    from empiricist.executor.runner import SPAWN_FAILED_EXIT_CODE
    assert row.ended is not None and row.exit_code == SPAWN_FAILED_EXIT_CODE
    lg.close()


def test_default_spec_has_conservative_resource_envelope():
    spec = ExecSpec(argv=["true"], move="TEST")
    assert spec.rss_mb is not None and spec.rss_mb > 0
    assert spec.limits.fsize_mb is not None
    assert spec.sandbox is SandboxMode.SANDBOX_EXEC


def test_duplicate_run_id_raises_typed(tmp_path):
    from empiricist.executor.runner import DuplicateRunError
    lg = Ledger(tmp_path / "ledger.db")
    run(py_spec("print('one')", run_id="dup"), ledger=lg)
    with pytest.raises(DuplicateRunError):
        run(py_spec("print('two')", run_id="dup"), ledger=lg)
    lg.close()


def test_timeout_hard_bounds_even_if_child_escapes_group():
    # A child double-forks a setsid() grandchild that inherits stdout and sleeps
    # holding the pipe open. The group kill can't reach it, so the drain would
    # hang forever without the bound. drain_grace_s=1.0 forces abandonment.
    import time
    code = (
        "import os, sys, time\n"
        "if os.fork() == 0:\n"
        "    os.setsid()\n"           # grandchild escapes the process group
        "    time.sleep(120)\n"       # ...holding the inherited stdout fd
        "else:\n"
        "    print('PARENT', flush=True)\n"
        "    time.sleep(120)\n"
    )
    t0 = time.monotonic()
    res = run(py_spec(code, timeout_s=1.0, drain_grace_s=1.0))
    elapsed = time.monotonic() - t0
    assert res.timed_out is True
    assert res.drain_abandoned is True
    assert elapsed < 15.0  # bounded: ~timeout_s + drain_grace_s, NOT forever
    # best-effort: kill the escaped grandchild so it doesn't linger for the suite
    import subprocess
    subprocess.run(["pkill", "-f", "os.setsid"], capture_output=True)


def test_normal_timeout_still_preserves_output_and_does_not_abandon():
    res = run(py_spec(
        "import time\nprint('KEPT', flush=True)\ntime.sleep(60)\n",
        timeout_s=1.0, drain_grace_s=10.0,
    ))
    assert res.timed_out is True and res.drain_abandoned is False
    assert "KEPT" in res.stdout   # FIX A intact for the common (group-killed) case


@pytest.mark.skipif(sys.platform != "darwin", reason="sandbox-exec is macOS-only")
def test_sandbox_exec_path_propagates_limits_env_and_workdir():
    from empiricist.executor.limits import ResourceLimits
    res = run(ExecSpec(
        argv=[sys.executable, "-I", "-S", "-c",
              "import os, resource\n"
              "print(resource.getrlimit(resource.RLIMIT_NOFILE)[0])\n"
              "print('ANTHROPIC_API_KEY' in os.environ)\n"
              "print(os.getcwd() == os.environ['HOME'])\n"],
        move="TEST", sandbox=SandboxMode.SANDBOX_EXEC,
        limits=ResourceLimits(nofile=48), timeout_s=30.0,
    ))
    assert res.exit_code == 0, res.stderr
    nofile, leaked, cwd_is_home = res.stdout.split()
    assert nofile == "48"          # rlimit propagated THROUGH sandbox-exec
    assert leaked == "False"       # env scrubbed
    assert cwd_is_home == "True"   # workdir applied


def test_env_passthrough_inherits_parent_env(monkeypatch):
    monkeypatch.setenv("EMPIRICIST_PROBE_VAR", "leaked-through")
    res = run(py_spec(
        "import os; print(os.environ.get('EMPIRICIST_PROBE_VAR', 'MISSING'))",
        env_passthrough=True,
    ))
    assert res.stdout.strip() == "leaked-through"


def test_default_still_scrubs_parent_env(monkeypatch):
    monkeypatch.setenv("EMPIRICIST_PROBE_VAR", "should-not-leak")
    res = run(py_spec("import os; print(os.environ.get('EMPIRICIST_PROBE_VAR', 'MISSING'))"))
    assert res.stdout.strip() == "MISSING"  # scrub is the default


def test_capture_cap_is_configurable():
    small = run(py_spec("print('y' * 5000)", capture_cap=1000))
    assert small.output_truncated is True and len(small.stdout) <= 1000 + 50
    big = run(py_spec("print('y' * 5000)", capture_cap=1_000_000))
    assert big.output_truncated is False and "yyyy" in big.stdout


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

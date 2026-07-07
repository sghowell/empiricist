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
def test_network_denied_with_eperm(workdir):
    # Must be denied by the SANDBOX (EPERM / "operation not permitted"),
    # not merely fail for some other reason — otherwise the test passes
    # even if sandbox-exec silently no-ops.
    res = run_sandboxed(
        "import socket\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 80), timeout=5)\n"
        "    print('ESCAPED')\n"
        "except PermissionError:\n"
        "    print('EPERM')\n"
        "except OSError as e:\n"
        "    print('OTHER', e.errno)\n",
        workdir,
    )
    assert res.returncode == 0 and res.stdout.strip() == b"EPERM", res.stdout + res.stderr


@darwin_only
def test_network_denied_differs_from_unsandboxed_baseline(workdir):
    # Differential: the same connect that the sandbox turns into EPERM must
    # NOT be EPERM without the sandbox (proves the control is doing the work).
    code = (
        "import socket\n"
        "try:\n"
        "    socket.create_connection(('127.0.0.1', 9), timeout=2)\n"
        "    print('CONNECTED')\n"
        "except PermissionError:\n"
        "    print('EPERM')\n"
        "except OSError:\n"
        "    print('REFUSED_OR_OTHER')\n"
    )
    baseline = subprocess.run(
        [sys.executable, "-I", "-S", "-c", code],
        capture_output=True,
        timeout=30,
        cwd=workdir,
    )
    assert baseline.stdout.strip() != b"EPERM"  # no sandbox: not an EPERM
    sandboxed = run_sandboxed(code, workdir)
    assert sandboxed.stdout.strip() == b"EPERM"  # sandbox: EPERM


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


@darwin_only
def test_signal_to_outside_process_denied(workdir):
    import time

    victim = subprocess.Popen(
        [sys.executable, "-I", "-S", "-c", "import time; time.sleep(30)"]
    )
    try:
        res = run_sandboxed(
            f"import os, signal\n"
            f"try:\n"
            f"    os.kill({victim.pid}, signal.SIGKILL); print('KILLED')\n"
            f"except PermissionError:\n"
            f"    print('EPERM')\n",
            workdir,
        )
        assert res.stdout.strip() == b"EPERM", res.stdout + res.stderr
        time.sleep(0.5)
        assert victim.poll() is None  # victim still alive
    finally:
        victim.kill()
        victim.wait()


@darwin_only
def test_sibling_path_extension_denied(workdir):
    # subpath is component-boundary-safe: a sibling whose NAME extends the
    # workdir path must NOT be writable.
    sibling = workdir.parent / (workdir.name + "SIBLING")
    sibling.mkdir()
    res = run_sandboxed(f"open({str(sibling / 'x')!r}, 'w').write('escaped')", workdir)
    assert res.returncode != 0 and not (sibling / "x").exists()


@darwin_only
def test_symlink_escape_from_inside_workdir_denied(workdir):
    outside = Path(tempfile.mkdtemp(prefix="empiricist-outside-"))
    link = workdir / "link"
    link.symlink_to(outside)
    res = run_sandboxed(f"open({str(link / 'escape')!r}, 'w').write('escaped')", workdir)
    assert res.returncode != 0 and not (outside / "escape").exists()


def test_workdir_with_unsafe_chars_rejected(tmp_path):
    bad = tmp_path / 'evil")(allow default'
    bad.mkdir()
    with pytest.raises(ValueError):
        sandbox_wrap(["echo"], workdir=bad, mode=SandboxMode.SANDBOX_EXEC)

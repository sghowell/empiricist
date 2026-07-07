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

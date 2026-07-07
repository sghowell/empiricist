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


def test_preexec_closure_is_precomputed():
    """Fork-safety: the child-side closure must hold only prebuilt constants
    (no arithmetic/allocation between fork and exec)."""
    fn = make_preexec(ResourceLimits(cpu_s=2, fsize_mb=3, nofile=128))
    cells = {
        v: c.cell_contents
        for v, c in zip(fn.__code__.co_freevars, fn.__closure__, strict=True)
    }
    assert cells["core"] == (0, 0)
    assert cells["nofile"][0] <= 128
    assert cells["cpu"] == (2, 2)
    assert cells["fsize"] == (3 * 1024 * 1024, 3 * 1024 * 1024)


def test_nofile_clamps_to_inherited_hard_limit():
    """An absurd request must clamp to the host's hard limit, not kill the spawn."""
    res = run_py(
        "import resource; print(resource.getrlimit(resource.RLIMIT_NOFILE)[0] > 0)",
        ResourceLimits(nofile=10**9),
    )
    assert res.returncode == 0 and res.stdout.strip() == b"True"

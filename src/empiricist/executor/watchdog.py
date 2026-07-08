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
    """SIGKILL the process group; quiet if gone. Only fires when `pid` is its
    own group leader (getpgid(pid) == pid) — under start_new_session our child
    always is, so this refuses to signal an unrelated group if the pid was
    reaped and reused."""
    try:
        if os.getpgid(pid) == pid:
            os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def reap_process_group(pgid: int) -> None:
    """SIGKILL every process still in group `pgid`, EVEN IF the group leader has
    already exited. This is the normal-completion straggler case: `communicate()`
    reaps the leader, but a detached same-group child (spawned by untrusted
    compile-time code, no `setsid`) can outlive it — the M8 5th break relied on
    exactly such a survivor to swap an olean after the gate returned.
    `kill_process_group` cannot handle this (its `getpgid(leader)==leader` guard
    fails once the leader is reaped), so this signals the pgid directly. Quiet if
    the group is already empty (ESRCH). The small pid-reuse window is bounded by
    calling this immediately after the reap; a reused pid would have to become a
    group leader (pgid==pid) in that window to be mis-hit, which a normal fork
    (inheriting its parent's pgid) does not do."""
    try:
        os.killpg(pgid, signal.SIGKILL)
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
    """Poll a process group's RSS; SIGKILL on breach; record the peak.

    This is a SOFT bound: a process allocating faster than poll_s can overshoot
    the cap between samples (in testing, peak 313 MB against a 64 MB cap). It
    protects against sustained growth, not a single fast mmap. Poll cost scales
    with total system process count via children(recursive=True); tune poll_s
    per-move for cheap moves.
    """

    def __init__(
        self, pid: int, rss_mb: float | None, *, poll_s: float = 0.1
    ) -> None:
        self._pid = pid
        self._rss_mb = rss_mb
        self._poll_s = poll_s
        self._stopped = False
        self.peak_mb: float = 0.0
        self.killed: bool = False
        self.sampled: bool = False

    def stop(self) -> None:
        self._stopped = True

    async def run(self) -> None:
        try:
            proc = psutil.Process(self._pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return
        while not self._stopped:
            if not proc.is_running():   # reaped (or pid reused) -> stop cleanly
                return
            try:
                rss = _rss_bytes(proc)
            except psutil.NoSuchProcess:
                return
            self.peak_mb = max(self.peak_mb, rss / (1024 * 1024))
            self.sampled = True
            if self._rss_mb is not None and self.peak_mb > self._rss_mb:
                self.killed = True
                kill_process_group(self._pid)
                return
            await asyncio.sleep(self._poll_s)

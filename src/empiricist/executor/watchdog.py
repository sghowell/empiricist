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

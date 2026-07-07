"""Darwin-safe rlimits applied in the child via preexec_fn.

The virtual address-space rlimit is DELIBERATELY absent: macOS silently
ignores it (verified in the research sweep; spec D8), so a naive "memory
rlimit" would be a false sense of safety. Memory is bounded by the psutil
RSS watchdog instead.
"""

from __future__ import annotations

import resource
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceLimits:
    cpu_s: int | None = None        # RLIMIT_CPU: SIGXCPU on breach
    # RLIMIT_FSIZE: EFBIG/SIGXFSZ on breach. Bounds EACH regular file, not
    # total disk — aggregate budgets are the workdir's job.
    fsize_mb: int | None = None
    nofile: int = 256               # RLIMIT_NOFILE
    # core dumps are always disabled: model-proposed code must not leave
    # memory images on disk.


def make_preexec(limits: ResourceLimits) -> Callable[[], None]:
    """Build the preexec_fn. Runs in the forked child before exec.

    Everything is precomputed HERE, in the parent: between fork() and exec()
    only async-signal-safe work is safe, so the closure body must be
    setrlimit calls over prebuilt tuples — no arithmetic, no allocation.
    """
    core = (0, 0)
    hard_nofile = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    nofile_cap = (
        limits.nofile
        if hard_nofile == resource.RLIM_INFINITY
        else min(limits.nofile, hard_nofile)
    )
    nofile = (nofile_cap, nofile_cap)
    cpu = None if limits.cpu_s is None else (limits.cpu_s, limits.cpu_s)
    fsize = (
        None
        if limits.fsize_mb is None
        else (limits.fsize_mb * 1024 * 1024, limits.fsize_mb * 1024 * 1024)
    )

    def _apply() -> None:
        resource.setrlimit(resource.RLIMIT_CORE, core)
        resource.setrlimit(resource.RLIMIT_NOFILE, nofile)
        if cpu is not None:
            resource.setrlimit(resource.RLIMIT_CPU, cpu)
        if fsize is not None:
            resource.setrlimit(resource.RLIMIT_FSIZE, fsize)

    return _apply

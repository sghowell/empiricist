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

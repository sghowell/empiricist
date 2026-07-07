"""The sandbox seam (spec §6, D8): one function wraps an argv for isolation.

v0 backend: /usr/bin/sandbox-exec with a generated SBPL profile — deny all
network, deny file writes outside the per-run workdir. Deprecated by Apple
but functional; it is defense-in-depth, not the primary safety argument
(the model never gets a shell, and all v0 verifier code is harness-authored).
The CONTAINER mode is the flagged v0.1 upgrade path (Apple `container`
microVM) for hostile CERTIFIED-tier runs.

Deliberately NOT locked down in v0's (allow default) posture (tracked as
the D8 CONTAINER-tier hardening): mach-lookup (clipboard/IPC egress),
file-read* (on-disk secrets — the host running Empiricist must not hold
secrets the model shouldn't read), and process-fork/exec. The Apple
`container` microVM is the real isolation for CERTIFIED/hostile tiers.
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path

# SBPL string literals cannot escape arbitrary bytes portably; mkdtemp paths
# are [A-Za-z0-9_./-] so anything else is rejected rather than quoted.
_SAFE_PATH = re.compile(r"[A-Za-z0-9_./-]+\Z")

# Signal confinement is the PAIR (deny signal) + (allow signal (target
# same-sandbox)): a run must not SIGKILL the harness or a sibling run, while
# intra-run signaling (the child's own subprocesses inherit the sandbox and
# are same-sandbox) keeps working. NOTE: the seemingly equivalent
# (deny signal (target others)) compiles but denies NOTHING under an
# (allow default) profile on this macOS (26.2/Darwin 25) — verified
# empirically; test_signal_to_outside_process_denied pins the working pair.
_PROFILE = """\
(version 1)
(allow default)
(deny network*)
(deny signal)
(allow signal (target same-sandbox))
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
    # resolve() BEFORE the regex is load-bearing: it collapses ../ and symlinks
    # (so no `..` reaches the subpath literal) and canonicalizes /var -> /private/var
    # (so in-workdir writes match). Do not reorder.
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

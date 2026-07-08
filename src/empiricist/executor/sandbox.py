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

# Hardened variant for running UNTRUSTED elaboration (the Lean compile gate): the
# same net/signal/write posture PLUS a full fork/exec lockdown. `(deny
# process-fork)` and `(deny process-exec*)` stop the untrusted process from
# spawning ANY child (the M8 5th break: a compile-time `#eval`/`run_cmd` spawned a
# DETACHED child that outlived the gate and, via a rename-swap TOCTOU, poisoned the
# checked olean). The one exception is the initial exec of the gate's OWN binary --
# sandbox-exec applies the profile then execs the target, and that exec is itself
# governed by process-exec*, so the target binary path must be explicitly allowed.
# Legitimate Lean elaboration (our scaffold + `import Mathlib`) never shells out,
# so nothing legitimate is lost (verified empirically). `{exec_path}` is the single
# allowed exec target (argv[0] of the wrapped command).
_PROFILE_NO_SUBPROCESS = """\
(version 1)
(allow default)
(deny network*)
(deny signal)
(allow signal (target same-sandbox))
(deny process-fork)
(deny process-exec*)
(allow process-exec* (literal "{exec_path}"))
(deny file-write*)
(allow file-write*
  (subpath "{workdir}")
  (literal "/dev/null"))
"""


class SandboxMode(StrEnum):
    NONE = "none"                  # trusted harness code / tests only
    SANDBOX_EXEC = "sandbox-exec"  # v0 default for anything model-adjacent
    CONTAINER = "container"        # v0.1: Apple container microVM (flagged)


def profile_for(workdir: Path, *, exec_only: Path | None = None) -> str:
    # resolve() BEFORE the regex is load-bearing: it collapses ../ and symlinks
    # (so no `..` reaches the subpath literal) and canonicalizes /var -> /private/var
    # (so in-workdir writes match). Do not reorder.
    resolved = str(workdir.resolve())
    if not _SAFE_PATH.fullmatch(resolved):
        raise ValueError(f"workdir path unsafe for SBPL literal: {resolved!r}")
    if exec_only is None:
        return _PROFILE.format(workdir=resolved)
    # Fork/exec-locked profile: only `exec_only` (resolved to the real binary, so
    # it matches the path the kernel sees when sandbox-exec execs it) may be exec'd.
    exec_path = str(Path(exec_only).resolve())
    if not _SAFE_PATH.fullmatch(exec_path):
        raise ValueError(f"exec path unsafe for SBPL literal: {exec_path!r}")
    return _PROFILE_NO_SUBPROCESS.format(workdir=resolved, exec_path=exec_path)


def sandbox_wrap(
    argv: list[str], *, workdir: Path, mode: SandboxMode, deny_subprocess: bool = False
) -> list[str]:
    """Wrap argv for execution under the chosen isolation mode.

    `deny_subprocess` (SANDBOX_EXEC only) adds the fork/exec lockdown profile,
    permitting only the exec of `argv[0]` (the gate's own binary) — so untrusted
    elaboration cannot spawn a persistent child. Ignored under NONE (trusted)."""
    if mode is SandboxMode.NONE:
        return list(argv)
    if mode is SandboxMode.SANDBOX_EXEC:
        if deny_subprocess and not argv:
            raise ValueError(
                "deny_subprocess requires a non-empty argv (argv[0] is the exec target)"
            )
        exec_only = Path(argv[0]) if deny_subprocess else None
        return ["/usr/bin/sandbox-exec", "-p", profile_for(workdir, exec_only=exec_only), *argv]
    raise NotImplementedError(
        "container isolation is the flagged v0.1 upgrade path (spec D8)"
    )

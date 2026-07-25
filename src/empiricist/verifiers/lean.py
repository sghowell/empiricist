"""LeanVerifier: a real trust gate over the pinned EmpiricistLean project
(M8, spec 10/D7/exit criterion 4).

The FORMALIZED verdict rests on the Lean KERNEL itself, re-checking the compiled
module through `leanchecker` (the standard `lean4checker`, merged into the Lean
toolchain since v4.28.0 and version-matched to our pinned v4.31.0), over a
compile that runs untrusted metaprogramming INSIDE AN OS SANDBOX with a
pinned-trusted import path. The gate is a pipeline over ONE compiled artifact:

    (b)  COMPILE   `lean --root <work> --json -o <olean> <scratch>`  [SANDBOXED,
                   fork/exec DENIED] severity=="error" -> FAIL(diagnostics);
                   `sorry` -> FAIL(sorry)
    (F)  FREEZE    atomic READ-ONLY snapshot of <olean> -> <frozen>/<tok>.olean,
                   OUTSIDE every sandbox-writable workdir. Gates (c)/(d) read the
                   scratch module from THIS frozen file, never from `work`.
    (b2) IMPORTS   `lean --deps <scratch>`   [SANDBOXED, Lever 2 import-trust]
                   any resolved import olean NOT under a pinned-trusted root
                   (and not a trusted EmpiricistLean foundation copy) -> FAIL(import_trust)
    (c)  KERNEL    `leanchecker <Module>`  [SANDBOXED, LEAN_PATH->FROZEN] [ANCHOR]
                   nonzero exit / kernel-mismatch output -> FAIL(kernel_soundness)
    (d)  AXIOMS    compiled `axiom_audit` driver over the FROZEN olean [SANDBOXED,
                   LEAN_PATH->FROZEN] axiom outside whitelist -> FAIL(axioms); the
                   driver also reports the module's TRANSITIVE import closure with
                   RESOLVED PATHS (Lever 2/4 backstop: unknown root, non-Basic
                   EmpiricistLean import, or any import olean path not under a pinned
                   root -> FAIL(import_trust)) and emits the decl's resolved STATEMENT.
    (e)  PASS      records the decl's resolved statement + statement_hash

**Root cause of the 5th break (this fix).** The kernel-checked olean lived INSIDE
the writable ephemeral `work` jail, and BOTH gate (c) and gate (d) re-read
`work/<tok>.olean` off a LEAN_PATH that included `work` -- nothing bound the bytes
across the two gates. A compile-time `#eval`/`run_cmd` spawned a DETACHED child
(stdio -> /dev/null, so the parent's `communicate()` still EOFed) that survived
gate (b) -- `executor/runner.py` only killed the process group on the
timeout/exception branches, not on normal completion. After leanchecker (c) read
the HONEST olean, the child `mv`'d a poison olean over `work/<tok>.olean` before the
axiom_audit driver (d) imported it: (c) kernel-checks honest -> passes; (d) audits
the swapped poison -> PASS on `2 = 3`, axioms=[]. **The fix (load-bearing = FREEZE):**
after (b) compiles the olean, atomically snapshot it into a READ-ONLY dir OUTSIDE
every sandbox-writable workdir and run BOTH (c) and (d) with LEAN_PATH pointed at
that frozen dir. The two gates now read the ONE frozen artifact, so they cannot
diverge -- snapshot honest -> (d) finds no evil, the honest result; snapshot poison
-> (c) kernel-rejects; no split -> no PASS-on-false. A surviving child rewriting
`work/<tok>.olean` is INERT. Defense-in-depth: (i) the untrusted compile runs under
a fork/exec-DENIED sandbox profile so no persistent child can spawn at all;
(ii) `executor/runner.py` reaps the whole process group on NORMAL completion too;
(iii) gate (d)'s import-closure check is PATH-based (each resolved import olean must
sit under a pinned root), not name-based.

**Root cause of the 4th break (this fix).** The predecessor ran the untrusted
compile at `SandboxMode.NONE` in the shared, writable, non-sandboxed project with
the writable build lib on the compile/checker LEAN_PATH. Untrusted `module_source`
runs arbitrary IO at ELABORATION (`#eval`/`initialize`/`run_cmd`), so a compile-
time `#eval` could WRITE a POISON olean (`theorem Poison.boom : False`, built via
`addDeclCore (doCheck := false)`, value `Eq.refl` -> compiles clean,
`collectAxioms=[]`) into `.lake/build/lib/lean/EmpiricistLean/Poison.olean`. The
poison PERSISTED across calls (per-call cleanup only removed `<tok>` files); a
SECOND `verify()` did `import EmpiricistLean.Poison; theorem grandclaim :
(2:Nat)=3 := Poison.boom.elim` -> leanchecker TRUSTS the import (it only replays
the module's OWN added decls) -> PASS on `2=3` with an attacker-chosen statement.
This violated the project non-negotiable "the model never gets a shell": untrusted
Lean got a writable, non-sandboxed environment at elaboration.

**The three independent levers that close the CLASS.**

- LEVER 1 (primary, sandbox the untrusted compile). Every subprocess that touches
  untrusted source -- the compile (b), the import probe (b2), the kernel re-check
  (c), the axiom/statement audit (d) -- runs through `executor.execute()` with
  `SandboxMode.SANDBOX_EXEC` and an EPHEMERAL per-call workdir. Network is denied;
  filesystem WRITES are confined to the ephemeral workdir. A compile-time
  `#eval IO.FS.writeFile "<shared build lib>/…/Poison.olean"` (or the same via a
  spawned `sh` -- descendants inherit the sandbox) is DENIED ("operation not
  permitted"). The toolchain (`~/.elan/…`) and the pinned mathlib/Basic oleans are
  READ-only inputs, which the (allow default) read posture permits; nothing the
  compile can reach is writable except its own ephemeral scratch. Because lake's
  own build-dir writes fight the sandbox, we DO NOT invoke `lake` on the hot path:
  we resolve the pinned toolchain binaries + LEAN_PATH ONCE via `lake env` (trusted,
  unsandboxed, at setup) and invoke `lean`/`leanchecker`/the driver DIRECTLY with an
  explicit `-o <ephemeral>/…` and `LEAN_PATH` at the pinned read-only roots -- so a
  direct binary writes only its `-o` target (in the workdir).

- LEVER 2 (defense-in-depth, import-trust by pinned closure). The compile/checker
  LEAN_PATH is built from ONLY pinned-trusted roots: the pinned mathlib + package
  build libs, the toolchain lib, READ-ONLY copies of our trusted EmpiricistLean
  FOUNDATION oleans (`EmpiricistLean.Basic` + `EmpiricistLean.Foundation`, outside
  any sandbox workdir, so the untrusted compile cannot tamper with them), and the
  ephemeral scratch dir. The writable shared project build lib is NOT on the path,
  so `import EmpiricistLean.Poison` cannot even resolve (compile-time FAIL). On top
  of that, gate (b2) resolves every DIRECT import via `lean --deps` and REQUIRES each
  resolved olean to sit under a pinned-trusted root (or be one of the trusted
  foundation copies); gate (d)'s driver reports the TRANSITIVE closure and the
  harness rejects any import ROOT that is not a pinned-trusted root and any
  `EmpiricistLean.*` import NOT in the trusted set (`_TRUSTED_EMPIRICIST_MODULES` =
  the promoted Fable-authored foundation; a committed-but-non-trusted module such as
  the `NonTrusted` fixture is NOT trusted). So a poison that somehow becomes reachable
  and is imported is rejected (FAIL import_trust) even if Lever 1 had a gap.

- LEVER 3 (hardening, residue sweep + fail-closed). Each call uses a UNIQUE
  ephemeral dir (uuid4), removed in `finally`. After the call we SWEEP the shared
  module + build dirs for any unexpected residue (anything not the pinned
  mathlib/Basic/toolchain set); a stray file means a prior/concurrent call planted
  something -> the result is FAILed closed and logged.

**Why (c) is load-bearing.** collectAxioms-only is UNSOUND against kernel-unchecked
environment injection (`addDeclCore (doCheck := false)`, `skipKernelTC`): a false
type with a clean `Eq.refl` value reports `axioms: []`. `leanchecker` re-checks the
module's own added declarations through the real kernel from its (trusted, pinned)
imports and rejects those injections (proven: `1=2 := Eq.refl` -> "declaration type
mismatch").

**Why (d) IMPORTS the compiled olean (not re-elaborate the source).** The audit must
read the SAME artifact leanchecker checked; a second frontend run whose compile-time
metaprogramming branches on a clock could diverge. The driver `importModules` the one
compiled olean, and carries its result on a fresh unguessable NONCE channel the
untrusted source cannot forge (the driver reads the nonce from a file and DELETES it
before importing; imports run under `IO.FS.withIsolatedStreams`).

`binary_hash` covers this module's own source PLUS the driver source
(`AxiomAudit.lean`), the leanchecker pin manifest (`lean/lean4checker.pin.json`),
the project's `lean-toolchain`, `lake-manifest.json`, and `lakefile.toml` bytes.

Deliberately OUT of the P5 golden suite / `registry.Registry.certify()` flow.
LeanVerifier has its own suite (`verifiers/lean_goldens.py`) and its own certify
path (`registry.certify_with_suite`, additive).
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import os
import shutil
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

from blake3 import blake3

from empiricist.domain.p5 import P5_PROBLEM_VERSION
from empiricist.executor.runner import ExecSpec, execute
from empiricist.executor.sandbox import SandboxMode
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Artifact, Claim, EvidenceRow, Status, Verdict
from empiricist.store import Store
from empiricist.verifiers.base import VerifierResult

# repo_root/lean/EmpiricistLean -- the pinned lake+mathlib project (M8 Task 1).
_DEFAULT_PROJECT_DIR = Path(__file__).resolve().parents[3] / "lean" / "EmpiricistLean"

# The only axioms that don't represent a proof-hygiene violation. Anything
# else -- sorryAx, native_decide's synthesized per-decl axiom, a custom axiom,
# Lean.ofReduceBool, Lean.trustCompiler -- is rejected by a plain membership
# test. These axioms are all KERNEL-VALID, so leanchecker (gate c) accepts them;
# the whitelist (gate d) is the hygiene layer leanchecker does not provide.
_AXIOM_WHITELIST = frozenset({"propext", "Classical.choice", "Quot.sound"})

# The v0 formalization campaign is the P5 GHZ3 resource model frozen by D1 in
# the harness design. Callers formalizing another problem/version must name it
# explicitly rather than silently inheriting P5 provenance.
DEFAULT_LEAN_PROBLEM_VERSION = P5_PROBLEM_VERSION

# The SET of trusted EmpiricistLean.* modules a scratch may import (the trusted
# FOUNDATION): the `Basic` scaffold lemma and the promoted Fable-authored
# `Foundation` fusion lower bound. An EmpiricistLean.* import is TRUSTED iff it is a
# MEMBER of this set; any OTHER EmpiricistLean.* import -- a planted
# `EmpiricistLean.Poison`, or even a committed-but-non-trusted
# `EmpiricistLean.NonTrusted` fixture -- is rejected by the import-trust gate. Adding a future
# trusted-foundation module is a one-line addition here (plus its committed
# source/build entries below); the trusted-lib copy iterates over this set.
_TRUSTED_EMPIRICIST_MODULES = frozenset(
    {"EmpiricistLean.Basic", "EmpiricistLean.Foundation", "EmpiricistLean.LocalComp",
     "EmpiricistLean.FusionRule", "EmpiricistLean.TreeThm",
     "EmpiricistLean.DoubleStar",
     "EmpiricistLean.CenterMerge",
     "EmpiricistLean.TrueTwin",
     "EmpiricistLean.ProducibleExt",
     "EmpiricistLean.DHCharacterization",
     "EmpiricistLean.P3Amplitudes",
     "EmpiricistLean.P3Pauli",
     "EmpiricistLean.P3L1"}
)

# The COMMITTED source modules that legitimately live in the project module dir,
# and their build-product basename prefixes. The residue sweep (Lever 3) flags
# anything OUTSIDE this set as escaped-jail residue (a planted `Poison.olean`, a
# leftover `Scratch_*`). `NonTrusted` is a trivial committed-but-non-trusted fixture
# (the import-trust security test stages its olean to confirm the gate rejects a
# non-trusted EmpiricistLean import); it is NOT a trusted import -- but its committed
# source + built olean must not be mistaken for residue. `Foundation` (the promoted
# Fable-authored fusion lower
# bound) IS a trusted import (it is in `_TRUSTED_EMPIRICIST_MODULES`) whose olean is
# staged into the trusted lib; its committed source belongs here too. The build lib
# stays OFF the restricted LEAN_PATH (Lever 2) and gate (d) still rejects any
# EmpiricistLean import not in the trusted set, so allowlisting the non-trusted
# oleans here does not widen the import-trust surface.
_COMMITTED_SOURCE_FILES = frozenset(
    {
        "Basic.lean",
        "CenterMerge.lean",
        "DHCharacterization.lean",
        "DoubleStar.lean",
        "Foundation.lean",
        "FusionRule.lean",
        "LocalComp.lean",
        "NonTrusted.lean",
        "P3Amplitudes.lean",
        "P3L1.lean",
        "P3Pauli.lean",
        "ProducibleExt.lean",
        "TreeThm.lean",
        "TrueTwin.lean",
    }
)
_COMMITTED_BUILD_PREFIXES = (
    "Basic.", "NonTrusted.", "Foundation.", "LocalComp.", "FusionRule.", "TreeThm.",
    "DoubleStar.", "CenterMerge.", "TrueTwin.", "ProducibleExt.",
    "DHCharacterization.", "P3Amplitudes.", "P3Pauli.", "P3L1."
)

# The framing marker the compiled driver prints its single result line with:
#   AXIOM_AUDIT::<nonce>::{"declFound":...,"axioms":[...],"importRoots":[...],...}
_DRIVER_MARKER = "AXIOM_AUDIT"

# Substrings in leanchecker output that signal a kernel rejection even if (belt
# and braces) the exit code were ever 0. leanchecker exits nonzero on failure;
# these are an extra fail-closed guard on the trust anchor.
_KERNEL_FAIL_MARKERS = (
    "found a problem",
    "uncaught exception",
    "declaration type mismatch",
    "(kernel)",
    "error",
)

_CAPTURE_CAP = 8 * 1024 * 1024  # generous: mathlib error messages can be long

# How many gate-(b)/(d) diagnostic MESSAGES survive into `details["errors"]`
# (surfacing verbosity only -- the verdict is decided by `if errors:`/
# `if driver_errors:` above these caps, so widening this never changes a
# FAIL/PASS outcome). Wide enough that a hole-driven proof's "unsolved goals"
# messages (M18 goal-state feedback, one per `?_`-bearing `by` block) aren't
# silently dropped before `format_feedback` ever sees them; `format_feedback`
# does its own, separate capping of how many it surfaces to the model.
_DIAGNOSTICS_ERROR_CAP = 25


@dataclass(frozen=True)
class _ToolchainConfig:
    """The pinned toolchain facts resolved ONCE (trusted, unsandboxed) via
    `lake env`, so the hot-path gates can invoke `lean`/`leanchecker`/the driver
    DIRECTLY (no `lake`, whose own build-dir writes fight the sandbox) under a
    restricted, pinned read-only LEAN_PATH."""

    lean_bin: Path
    leanchecker_bin: Path
    sysroot: str
    # Pinned read-only import roots (the package build libs + the toolchain lib);
    # the WRITABLE project build lib is deliberately EXCLUDED.
    trusted_roots: tuple[Path, ...]
    # Read-only copies of the trusted EmpiricistLean foundation oleans (one per
    # module in `_TRUSTED_EMPIRICIST_MODULES` -- Basic.olean, Foundation.olean),
    # outside any sandbox workdir. An import resolving to one of THESE exact paths is
    # trusted; any other EmpiricistLean olean is not.
    trusted_oleans: frozenset[Path]
    # The trusted lib dir containing those copies (its `EmpiricistLean/` subdir).
    trusted_lib_dir: Path
    # Distinct top-level module roots reachable via the trusted roots + the lib.
    allowed_roots: frozenset[str]


def parse_driver_result(stdout: str, nonce: str) -> dict[str, Any] | None:
    """Extract the compiled driver's structured result from its stdout.

    Returns the parsed JSON object from the SINGLE line framed
    `AXIOM_AUDIT::<nonce>::<json>`, or None (fail closed) if no such line exists
    or the JSON is malformed. Only a line bearing the EXACT `nonce` is trusted --
    the untrusted source cannot learn the nonce (the driver deletes the nonce file
    before importing), so it cannot forge an accepted line. A None return is
    ALWAYS a FAIL, never a PASS."""
    prefix = f"{_DRIVER_MARKER}::{nonce}::"
    payloads = [
        line[line.index(prefix) + len(prefix):]
        for line in stdout.splitlines()
        if prefix in line
    ]
    if not payloads:
        return None
    try:
        parsed = json.loads(payloads[-1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_compile_diagnostics(stdout: str) -> tuple[list[str], bool]:
    """Parse `lean --json` diagnostics from stdout.

    Returns `(errors, sorry_hit)`: the list of `severity=="error"` message
    bodies, and whether any `sorry` warning is present (`kind=="hasSorry"`, or a
    warning whose data mentions sorry). `sorry` is a WARNING (`lean` exits 0), so
    an exit-code gate is UNSOUND -- this parse is what catches it at compile time
    (the axiom gate's `sorryAx` is the backstop)."""
    errors: list[str] = []
    sorry_hit = False
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line.startswith("{"):
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(d, dict):
            continue
        sev = d.get("severity")
        data = str(d.get("data") or "")
        kind = str(d.get("kind") or "")
        if sev == "error":
            errors.append(data)
        elif kind == "hasSorry" or (sev == "warning" and "sorry" in data.lower()):
            sorry_hit = True
    return errors, sorry_hit


class LeanVerifier:
    """Verifier wrapping the SANDBOXED kernel re-check (`leanchecker`) + compiled
    `axiom_audit` driver over the pinned EmpiricistLean project, with a
    pinned-trusted import path (Levers 1-3). See module docstring for the trust
    model."""

    name = "lean"
    version = "3.3"

    def __init__(self, project_dir: Path | None = None) -> None:
        self._project_dir = project_dir or _DEFAULT_PROJECT_DIR
        self._module_dir = self._project_dir / "EmpiricistLean"
        # The WRITABLE project build lib (where a poison olean would be planted).
        # Deliberately kept OFF the restricted compile/checker LEAN_PATH; swept for
        # residue by Lever 3.
        self._build_lib = self._project_dir / ".lake" / "build" / "lib" / "lean"
        self._driver_src = self._project_dir / "AxiomAudit.lean"
        self._driver_bin = self._project_dir / ".lake" / "build" / "bin" / "axiom_audit"
        # Read-only trusted lib (Basic.olean copy), under .lake (gitignored) but NOT
        # the build lib and NOT any sandbox workdir -> untamperable by the sandbox.
        self._trusted_lib_dir = self._project_dir / ".lake" / "empiricist-trusted-lib"
        # Parent of the per-call READ-ONLY frozen-olean snapshot dirs (M8 v5): under
        # .lake (gitignored), NOT the build lib and NOT any sandbox workdir. The
        # kernel-checked olean is atomically snapshotted into a per-call subdir here,
        # made read-only, and BOTH gate (c) and gate (d) read the scratch module from
        # it -- so a surviving compile-time child rewriting `work/<tok>.olean` is inert.
        self._frozen_lib_dir = self._project_dir / ".lake" / "empiricist-frozen-lib"
        self._pin_manifest = self._project_dir.parent / "lean4checker.pin.json"
        self._cfg: _ToolchainConfig | None = None

    @property
    def binary_hash(self) -> str:
        """blake3 over this module's source + the compiled driver's source
        (AxiomAudit.lean) + the leanchecker pin manifest + the project's
        lean-toolchain, lake-manifest.json, and lakefile.toml bytes + every COMMITTED
        EmpiricistLean source module (Basic/NonTrusted/Foundation/...). The
        committed sources are folded in because their built oleans are allow-listed by
        the residue sweep and the TRUSTED ones are staged onto the
        gate's frozen import path -- so editing any of them changes the trust surface
        and must mint a new verifier identity. Read fresh from disk on every access,
        so any of those changing invalidates an existing certification stamp."""
        hasher = blake3()
        hasher.update(inspect.getsource(sys.modules[__name__]).encode("utf-8"))
        hasher.update(self._driver_src.read_bytes())
        hasher.update(self._pin_manifest.read_bytes())
        hasher.update((self._project_dir / "lean-toolchain").read_bytes())
        hasher.update((self._project_dir / "lake-manifest.json").read_bytes())
        hasher.update((self._project_dir / "lakefile.toml").read_bytes())
        # Committed EmpiricistLean source modules, in a STABLE (sorted) order so the
        # hash is deterministic regardless of the frozenset's iteration order.
        for name in sorted(_COMMITTED_SOURCE_FILES):
            hasher.update((self._module_dir / name).read_bytes())
        return hasher.hexdigest()

    def applicable(self, kind: str) -> bool:
        return kind == "lean"

    def verify(
        self, module_source: str, *, decl: str, timeout_s: float = 600.0
    ) -> VerifierResult:
        """Verify `module_source` compiles error-free, imports only pinned-trusted
        modules, is KERNEL-SOUND (leanchecker), and `decl`'s axiom closure is within
        the whitelist. Total -- never raises: any failure becomes Verdict.ERROR or a
        fail-closed Verdict.FAIL. The per-invocation EPHEMERAL workdir is removed and
        the shared dirs swept for residue in `finally`.

        Wraps `asyncio.run`, so it must NOT be called from a thread with a running
        event loop -- guarded (returns Verdict.ERROR rather than raising)."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass  # no running loop -- the normal, supported case
        else:
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={
                    "error": "LeanVerifier.verify() wraps asyncio.run and cannot be "
                    "called from a running event loop"
                },
            )

        source_hash = blake3(module_source.encode("utf-8")).hexdigest()
        # Per-invocation UNIQUE token (uuid4): two concurrent verify() calls -- even
        # of the SAME source -- get distinct workdir/module/nonce, closing the
        # concurrent-verify nonce-leak window and the cleanup race. `Scratch_` prefix
        # keeps the module a valid Lean identifier for any uuid hex.
        tok = f"Scratch_{uuid.uuid4().hex}"
        # EPHEMERAL per-call workdir = the SANDBOX write jail. The scratch source,
        # its `-o` olean, and the nonce file all live here; NOTHING is written into
        # the shared project. A direct-import poison plant is confined here and
        # removed in finally.
        work = Path(mkdtemp(prefix="empiricist-lean-")).resolve()
        module_name = tok  # top-level module (decoupled from the EmpiricistLean ns)
        scratch_path = work / f"{tok}.lean"
        nonce_path = work / f"{tok}.nonce"
        olean_path = work / f"{tok}.olean"
        # Per-call READ-ONLY frozen-snapshot dir, OUTSIDE `work` (so a sandbox child
        # confined to `work` cannot reach it). Holds the one kernel-input olean both
        # gate (c) and gate (d) read; removed (write bits restored) in `finally`.
        frozen_dir = self._frozen_lib_dir / tok
        # Fresh per call: the attacker cannot predict or read it (the driver deletes
        # the nonce file before importing), so cannot forge a result line.
        nonce = f"AXIOM_AUDIT_{uuid.uuid4().hex}"
        try:
            return asyncio.run(
                self._verify_async(
                    module_source, decl=decl, timeout_s=timeout_s,
                    module_name=module_name, work=work, scratch_path=scratch_path,
                    nonce=nonce, nonce_path=nonce_path, olean_path=olean_path,
                    frozen_dir=frozen_dir, source_hash=source_hash,
                )
            )
        except Exception as exc:
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={"error": f"{type(exc).__name__}: {exc}"},
            )
        finally:
            # Lever 3: remove the whole ephemeral workdir (source, olean, nonce, and
            # any compile-time residue confined there), unconditionally, plus the
            # read-only frozen-snapshot dir (write bits restored first).
            shutil.rmtree(work, ignore_errors=True)
            self._force_rmtree(frozen_dir)

    async def _verify_async(
        self, module_source: str, *, decl: str, timeout_s: float,
        module_name: str, work: Path, scratch_path: Path, nonce: str,
        nonce_path: Path, olean_path: Path, frozen_dir: Path, source_hash: str,
    ) -> VerifierResult:
        build_err = await self._ensure_ready_async()
        if build_err is not None:
            return VerifierResult(verdict=Verdict.ERROR, details={"error": build_err})
        cfg = self._cfg
        assert cfg is not None  # _ensure_ready_async sets it or returns an error

        # Lever 3 (pre): a stray, non-pinned olean already sitting in the shared
        # dirs means a prior/concurrent call escaped its jail -> fail closed BEFORE
        # trusting anything.
        residue = self._sweep_residue()
        if residue:
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"gate": "residue", "unexpected_files": residue[:8]},
            )

        # The scratch file is the UNMODIFIED source -- the harness appends NOTHING.
        scratch_path.write_text(module_source, encoding="utf-8")
        nonce_path.write_text(nonce, encoding="utf-8")
        # Two LEAN_PATHs: `work_env` (writable scratch dir on path) for the untrusted
        # compile/deps over the SOURCE; `frozen_env` (the READ-ONLY snapshot dir on
        # path, NOT `work`) for the two kernel gates over the frozen OLEAN. Both
        # exclude the writable project build lib (Lever 2).
        work_env = {
            **self._lean_env(),
            "LEAN_PATH": self._restricted_lean_path(work, cfg),
            "LEAN_SYSROOT": cfg.sysroot,
        }

        def sandboxed(argv: list[str], move: str, env: dict[str, str]) -> ExecSpec:
            # cwd=work makes `work` the sandbox write jail (executor resolves cwd to
            # the SBPL subpath). env_passthrough=False + SANDBOX_EXEC: no secrets, no
            # network, writes confined to `work`. deny_subprocess: fork/exec DENIED
            # (except this binary), so untrusted elaboration cannot spawn a persistent
            # child (the 5th break's detached olean-swapper).
            return ExecSpec(
                argv=argv, move=move, cwd=work,
                sandbox=SandboxMode.SANDBOX_EXEC, deny_subprocess=True,
                env_passthrough=False, env_extra=env,
                capture_cap=_CAPTURE_CAP, timeout_s=timeout_s,
            )

        # -- Gate (b): SANDBOXED COMPILE to an ephemeral olean, --json diagnostics. -
        compile_res = await execute(
            sandboxed(
                [str(cfg.lean_bin), "--root", str(work), "--json",
                 "-o", str(olean_path), scratch_path.name],
                "LEAN_COMPILE", work_env,
            ),
            ledger=None,
        )
        early = self._exec_guard(compile_res, "lean --json compile")
        if early is not None:
            return early
        errors, sorry_hit = parse_compile_diagnostics(compile_res.stdout)
        if errors:
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"gate": "diagnostics", "errors": errors[:_DIAGNOSTICS_ERROR_CAP]},
            )
        if sorry_hit:
            return VerifierResult(verdict=Verdict.FAIL, details={"gate": "sorry"})
        if not olean_path.exists():
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={
                    "gate": "diagnostics",
                    "reason": "no olean produced",
                    "exit_code": compile_res.exit_code,
                    "stderr_tail": compile_res.stderr[-2000:],
                },
            )

        # -- Gate (F): FREEZE the kernel-input olean (LOAD-BEARING, closes the TOCTOU
        # class). Atomic READ-ONLY snapshot OUTSIDE every sandbox-writable workdir;
        # both kernel gates below read the scratch module from it, so a surviving
        # compile-time child rewriting `work/<tok>.olean` cannot make (c) and (d)
        # diverge. `frozen_env` points LEAN_PATH at the frozen dir (never `work`).
        frozen_olean = self._freeze_olean(olean_path, frozen_dir, module_name)
        frozen_env = {
            **self._lean_env(),
            "LEAN_PATH": self._frozen_lean_path(frozen_dir, cfg),
            "LEAN_SYSROOT": cfg.sysroot,
        }

        # -- Gate (b2): IMPORT-TRUST over DIRECT imports (Lever 2, early). ----------
        deps_res = await execute(
            sandboxed(
                [str(cfg.lean_bin), "--root", str(work), "--deps", scratch_path.name],
                "LEAN_IMPORT_DEPS", work_env,
            ),
            ledger=None,
        )
        early = self._exec_guard(deps_res, "lean --deps")
        if early is not None:
            return early
        untrusted = self._untrusted_import_paths(deps_res.stdout, cfg, work)
        if untrusted:
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"gate": "import_trust", "untrusted_imports": untrusted[:8]},
            )

        # -- Gate (c): KERNEL re-check via leanchecker over the FROZEN olean. -------
        lc_res = await execute(
            sandboxed([str(cfg.leanchecker_bin), module_name], "LEAN_KERNEL_CHECK",
                      frozen_env),
            ledger=None,
        )
        early = self._exec_guard(lc_res, "leanchecker")
        if early is not None:
            return early
        lc_out = f"{lc_res.stdout}\n{lc_res.stderr}"
        kernel_bad = lc_res.exit_code != 0 or any(
            m in lc_out.lower() for m in _KERNEL_FAIL_MARKERS
        )
        if kernel_bad:
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={
                    "gate": "kernel_soundness",
                    "decl": decl,
                    "leanchecker_exit": lc_res.exit_code,
                    "leanchecker_output": lc_out.strip()[-2000:],
                },
            )

        # -- Gate (d): AXIOM SET + IMPORT CLOSURE + STATEMENT over the FROZEN olean. -
        audit_res = await execute(
            sandboxed(
                [str(self._driver_bin), module_name, decl, str(nonce_path)],
                "LEAN_AXIOM_AUDIT", frozen_env,
            ),
            ledger=None,
        )
        early = self._exec_guard(audit_res, "axiom_audit")
        if early is not None:
            return early

        result = parse_driver_result(audit_res.stdout, nonce)
        if result is None:
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={
                    "gate": "driver_result",
                    "decl": decl,
                    "exit_code": audit_res.exit_code,
                    "stdout_tail": audit_res.stdout[-2000:],
                    "stderr_tail": audit_res.stderr[-2000:],
                },
            )

        driver_errors = result.get("errors") or []
        if driver_errors:
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"gate": "diagnostics", "errors": driver_errors[:_DIAGNOSTICS_ERROR_CAP]},
            )

        # Lever 2/4 backstop: the driver's TRANSITIVE import closure must be pinned,
        # by NAME (root) and by RESOLVED PATH (each import olean under a pinned root).
        import_bad = self._untrusted_transitive_imports(
            result, module_name, cfg, frozen_olean
        )
        if import_bad:
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"gate": "import_trust", **import_bad},
            )

        if not result.get("declFound"):
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"gate": "decl_missing", "decl": decl},
            )
        axioms = result.get("axioms") or []
        offending = [a for a in axioms if a not in _AXIOM_WHITELIST]
        if offending:
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"gate": "axioms", "axioms": axioms, "offending_axioms": offending},
            )

        # Lever 3 (post): nothing may have leaked into the shared dirs during the run.
        residue = self._sweep_residue()
        if residue:
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"gate": "residue", "unexpected_files": residue[:8]},
            )

        statement = str(result.get("statement") or "")
        statement_hash = blake3(statement.encode("utf-8")).hexdigest()
        return VerifierResult(
            verdict=Verdict.PASS,
            details={
                "decl": decl,
                "axioms": axioms,
                "statement": statement,
                "statement_hash": statement_hash,
                "toolchain": self._toolchain(),
                "mathlib_commit": self._mathlib_commit(),
                "kernel_checker": "leanchecker (toolchain builtin, pinned)",
                "sandbox": "sandbox-exec (network denied, writes confined to ephemeral workdir)",
                "import_roots": sorted(result.get("importRoots") or []),
                "source_hash": source_hash,
            },
        )

    def _restricted_lean_path(self, work: Path, cfg: _ToolchainConfig) -> str:
        """LEAN_PATH for the untrusted compile/deps gates = pinned read-only roots +
        the trusted foundation lib (Basic + Foundation) + the ephemeral scratch dir.
        The WRITABLE project build lib is EXCLUDED, so a sibling poison olean planted
        there is unreachable (Lever 2)."""
        roots = [*(str(r) for r in cfg.trusted_roots), str(cfg.trusted_lib_dir), str(work)]
        return os.pathsep.join(roots)

    def _frozen_lean_path(self, frozen_dir: Path, cfg: _ToolchainConfig) -> str:
        """LEAN_PATH for the two KERNEL gates (c)/(d) = pinned read-only roots + the
        trusted foundation lib (Basic + Foundation) + the READ-ONLY FROZEN snapshot
        dir (NOT the writable `work`). Both gates resolve the scratch module <tok> from
        the frozen snapshot,
        so a compile-time child rewriting `work/<tok>.olean` cannot reach what they
        check -- the load-bearing half of the 5th-break fix."""
        roots = [*(str(r) for r in cfg.trusted_roots), str(cfg.trusted_lib_dir), str(frozen_dir)]
        return os.pathsep.join(roots)

    def _freeze_olean(self, olean_path: Path, frozen_dir: Path, module_name: str) -> Path:
        """Atomically snapshot the just-compiled, about-to-be-kernel-checked olean
        into a READ-ONLY location OUTSIDE every sandbox-writable workdir -- the SAME
        untamperable-copy pattern used for the trusted Basic.olean (temp + chmod +
        os.replace). Copy to a temp sibling, make it read-only, atomically publish it
        as `<module_name>.olean`, then make the snapshot dir itself non-writable (DiD
        atop the sandbox, which already denies writes outside `work`). Gates (c)/(d)
        read the module from the returned frozen path; a child confined to `work`
        cannot reach it. Returns the resolved frozen olean path."""
        frozen_dir.mkdir(parents=True, exist_ok=True)
        frozen_olean = (frozen_dir / f"{module_name}.olean").resolve()
        tmp = frozen_dir / f".{module_name}.olean.{uuid.uuid4().hex}.tmp"
        shutil.copyfile(olean_path, tmp)
        os.chmod(tmp, 0o444)
        os.replace(tmp, frozen_olean)
        os.chmod(frozen_dir, 0o555)
        return frozen_olean

    @staticmethod
    def _force_rmtree(path: Path) -> None:
        """Remove a tree that may have been made READ-ONLY (the frozen snapshot dir
        and its 0o444 olean): restore write bits on the dir + its entries first so
        removal cannot fail on the read-only file/dir, then remove unconditionally.
        A no-op (suppressed) if the path never materialized."""
        with contextlib.suppress(OSError):
            os.chmod(path, 0o755)
        with contextlib.suppress(OSError):
            for child in path.iterdir():
                with contextlib.suppress(OSError):
                    os.chmod(child, 0o644)
        shutil.rmtree(path, ignore_errors=True)

    def _untrusted_import_paths(
        self, deps_stdout: str, cfg: _ToolchainConfig, work: Path
    ) -> list[str]:
        """Gate (b2): classify each `lean --deps` resolved import olean path. An
        import is TRUSTED iff its olean sits under a pinned read-only root or is one of
        the trusted EmpiricistLean foundation copies (Basic.olean/Foundation.olean).
        A path under the ephemeral workdir (a same-call planted sibling) or anywhere
        else -> UNTRUSTED. Returns the list of untrusted resolved paths (empty == all
        imports pinned)."""
        untrusted: list[str] = []
        for raw in deps_stdout.splitlines():
            line = raw.strip()
            if not line or not line.endswith(".olean"):
                continue
            try:
                p = Path(line).resolve()
            except OSError:
                untrusted.append(line)
                continue
            if p in cfg.trusted_oleans:
                continue
            if any(self._is_under(p, root) for root in cfg.trusted_roots):
                continue
            untrusted.append(str(p))
        return untrusted

    def _untrusted_transitive_imports(
        self, result: dict[str, Any], module_name: str, cfg: _ToolchainConfig,
        frozen_olean: Path,
    ) -> dict[str, Any] | None:
        """Gate (d) backstop: over the driver's TRANSITIVE import closure, reject
        (a) any top-level ROOT that is not pinned-trusted (allowing the scratch's own
        module root), (b) any `EmpiricistLean.*` import NOT in the trusted set
        `_TRUSTED_EMPIRICIST_MODULES` (Basic/Foundation), and (c) [Lever 4] any
        resolved import olean whose PATH is not under a pinned-trusted root (mirroring
        gate b2). The PATH check is the one that catches a planted `Mathlib/Fake.olean`
        a name-only root check would wave through on the `Mathlib` root alone. Returns
        a details dict on violation, else None."""
        roots = result.get("importRoots") or []
        allowed = cfg.allowed_roots | {module_name}
        bad_roots = [r for r in roots if r not in allowed]
        emp = result.get("empiricistImports") or []
        bad_emp = [m for m in emp if m not in _TRUSTED_EMPIRICIST_MODULES]
        # Lever 4: every RESOLVED import olean path must sit under a pinned-trusted
        # root, or be one of the trusted foundation copies, or the frozen scratch
        # olean itself.
        bad_paths: list[str] = []
        for raw in result.get("importPaths") or []:
            if not raw:
                continue  # unresolvable name: the name-based root check still applies
            try:
                p = Path(raw).resolve()
            except OSError:
                bad_paths.append(raw)
                continue
            if p in cfg.trusted_oleans or p == frozen_olean:
                continue
            if any(self._is_under(p, root) for root in cfg.trusted_roots):
                continue
            bad_paths.append(str(p))
        if bad_roots or bad_emp or bad_paths:
            return {
                "reason": "transitive import closure includes non-pinned modules",
                "unexpected_roots": bad_roots[:8],
                "unexpected_empiricist_imports": bad_emp[:8],
                "unexpected_import_paths": bad_paths[:8],
            }
        return None

    def _sweep_residue(self) -> list[str]:
        """Lever 3: scan the shared module source dir and the writable build lib for
        UNEXPECTED files -- anything that is not part of the pinned/committed set.
        A stray olean/lean (e.g. a planted `Poison.olean`, or a leftover `Scratch_*`)
        means a prior/concurrent call escaped its ephemeral jail. Returns the list of
        offending paths (empty == clean)."""
        offenders: list[str] = []
        # Source dir: only the committed modules belong here (Scratch_* used to
        # live here; they now live in the ephemeral workdir, so any Scratch_* here is
        # stale residue).
        for p in self._module_dir.glob("*"):
            if p.name not in _COMMITTED_SOURCE_FILES:
                offenders.append(str(p))
        # Build lib EmpiricistLean subdir: only committed-module build products belong.
        emp_build = self._build_lib / "EmpiricistLean"
        if emp_build.exists():
            for p in emp_build.glob("*"):
                if not p.name.startswith(_COMMITTED_BUILD_PREFIXES):
                    offenders.append(str(p))
        return offenders

    @staticmethod
    def _is_under(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    @staticmethod
    def _exec_guard(res: Any, label: str) -> VerifierResult | None:
        """Map a subprocess timeout / RSS kill to a Verdict.ERROR, else None."""
        if res.timed_out:
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={"error": f"{label} subprocess timed out"},
            )
        if res.rss_killed:
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={"error": f"{label} subprocess killed: RSS watchdog limit exceeded"},
            )
        return None

    async def _ensure_ready_async(self) -> str | None:
        """Build the `axiom_audit` driver + the EmpiricistLean lib once per verifier
        instance (TRUSTED, unsandboxed: the pinned toolchain building harness-authored
        source), then resolve the pinned toolchain config via `lake env` and stage the
        read-only trusted `Basic.olean` copy. Returns None on success, else an error
        string."""
        if self._cfg is not None:
            return None
        build = await execute(
            ExecSpec(
                argv=["lake", "build", "EmpiricistLean", "axiom_audit"],
                move="LEAN_BUILD_DRIVER",
                cwd=self._project_dir,
                sandbox=SandboxMode.NONE,
                env_passthrough=False, env_extra=self._lean_env(),
                capture_cap=_CAPTURE_CAP, timeout_s=600.0,
            ),
            ledger=None,
        )
        if build.timed_out:
            return "axiom_audit driver build timed out"
        if build.exit_code != 0 or not self._driver_bin.exists():
            return (
                f"`lake build EmpiricistLean axiom_audit` rc={build.exit_code}, "
                f"bin_exists={self._driver_bin.exists()}: {build.stderr[-2000:]}"
            )
        try:
            cfg = await self._resolve_toolchain_async()
        except Exception as exc:  # resolution is best-effort; surface as ERROR
            return f"toolchain resolution failed: {type(exc).__name__}: {exc}"
        self._cfg = cfg
        return None

    async def _resolve_toolchain_async(self) -> _ToolchainConfig:
        """Resolve pinned toolchain facts ONCE via `lake env` (trusted, unsandboxed)
        so the hot path can invoke binaries directly under a restricted LEAN_PATH."""
        async def lake_env(*args: str) -> str:
            res = await execute(
                ExecSpec(
                    argv=["lake", "env", *args],
                    move="LEAN_RESOLVE_TOOLCHAIN",
                    cwd=self._project_dir,
                    sandbox=SandboxMode.NONE,
                    env_passthrough=False, env_extra=self._lean_env(),
                    capture_cap=_CAPTURE_CAP, timeout_s=120.0,
                ),
                ledger=None,
            )
            if res.exit_code != 0:
                raise RuntimeError(
                    f"`lake env {' '.join(args)}` rc={res.exit_code}: {res.stderr[-500:]}"
                )
            return res.stdout.strip()

        lean_bin = Path((await lake_env("which", "lean")).splitlines()[-1].strip())
        leanchecker_bin = Path((await lake_env("which", "leanchecker")).splitlines()[-1].strip())
        sysroot = (await lake_env("lean", "--print-prefix")).splitlines()[-1].strip()
        raw_lean_path = await lake_env("printenv", "LEAN_PATH")

        build_lib = self._build_lib.resolve()
        trusted_roots: list[Path] = []
        for entry in raw_lean_path.split(os.pathsep):
            entry = entry.strip()
            if not entry:
                continue
            p = Path(entry).resolve()
            if p == build_lib:  # EXCLUDE the writable project build lib
                continue
            if p not in trusted_roots:
                trusted_roots.append(p)

        # Stage a read-only trusted copy of EVERY trusted-foundation olean
        # (Basic.olean, Foundation.olean), fresh so a rebuild is reflected, outside any
        # sandbox workdir. Iterating `_TRUSTED_EMPIRICIST_MODULES` makes adding a 3rd
        # trusted module a one-liner (add it to the set + its committed source/build
        # entries). Each copy is atomic (temp + os.replace within the same dir) so a
        # concurrent fresh verifier restaging never sees a torn file.
        trusted_oleans: set[Path] = set()
        for module in _TRUSTED_EMPIRICIST_MODULES:
            rel = Path(*module.split(".")).with_suffix(".olean")  # EmpiricistLean/X.olean
            src = self._build_lib / rel
            dst = (self._trusted_lib_dir / rel).resolve()
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.exists():
                tmp_dst = dst.parent / f".{dst.name}.{uuid.uuid4().hex}.tmp"
                shutil.copyfile(src, tmp_dst)
                os.replace(tmp_dst, dst)
            trusted_oleans.add(dst)

        allowed_roots = self._scan_allowed_roots(trusted_roots, self._trusted_lib_dir.resolve())

        return _ToolchainConfig(
            lean_bin=lean_bin, leanchecker_bin=leanchecker_bin, sysroot=sysroot,
            trusted_roots=tuple(trusted_roots), trusted_oleans=frozenset(trusted_oleans),
            trusted_lib_dir=self._trusted_lib_dir.resolve(), allowed_roots=allowed_roots,
        )

    @staticmethod
    def _scan_allowed_roots(trusted_roots: list[Path], trusted_lib_dir: Path) -> frozenset[str]:
        """The set of top-level module roots reachable via the trusted import roots:
        each root dir's immediate subdirs (`Mathlib/` -> `Mathlib`) and top-level
        `*.olean` files (`Init.olean` -> `Init`). Computed once; used to reject any
        transitive import whose root is not pinned-trusted."""
        roots: set[str] = set()
        for d in [*trusted_roots, trusted_lib_dir]:
            if not d.exists():
                continue
            for entry in d.iterdir():
                if entry.is_dir():
                    roots.add(entry.name)
                elif entry.name.endswith(".olean"):
                    roots.add(entry.name[: -len(".olean")])
        return frozenset(roots)

    @staticmethod
    def _lean_env() -> dict[str, str]:
        """The minimal env for elan/lake/lean/leanchecker, passed as
        `ExecSpec.env_extra` (with `env_passthrough=False`).

        Includes ONLY: the parent PATH (with ~/.elan/bin ensured -- to resolve elan
        shims / `lake`), the real HOME (elan's ~/.elan lives there; read-only under
        the sandbox), and any parent `ELAN*` vars. Every secret the parent holds is
        dropped: even under the sandbox, the untrusted compile's IO must not read it."""
        home = os.environ.get("HOME", "")
        path = os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")
        if home:
            elan_bin = str(Path(home) / ".elan" / "bin")
            if elan_bin not in path.split(os.pathsep):
                path = f"{elan_bin}{os.pathsep}{path}"
        env = {"PATH": path, "HOME": home}
        env.update({k: v for k, v in os.environ.items() if k.startswith("ELAN")})
        return env

    def _toolchain(self) -> str:
        return (self._project_dir / "lean-toolchain").read_text(encoding="utf-8").strip()

    def _mathlib_commit(self) -> str | None:
        manifest = json.loads((self._project_dir / "lake-manifest.json").read_text())
        for pkg in manifest.get("packages", []):
            if pkg.get("name") == "mathlib":
                return pkg.get("rev")
        return None


def ingest_lean_artifact(
    ledger: Ledger,
    store: Store,
    module_source: str,
    decl: str,
    *,
    verifier: LeanVerifier | None = None,
    problem: str = "P5",
    problem_version: str = DEFAULT_LEAN_PROBLEM_VERSION,
    run_id: str | None = None,
    timeout_s: float = 600.0,
) -> Artifact:
    """Verify the exact source and atomically record its FORMALIZED claim.

    A caller cannot inject a previously manufactured PASS: this function owns
    both the verifier invocation and the artifact/claim/evidence transaction.
    The verifier must hold a current certification for the exact Lean golden
    suite before it runs and when the transaction commits.
    """
    v = verifier if verifier is not None else LeanVerifier()
    suite_hash = _require_current_lean_certification(ledger, v)
    result = v.verify(module_source, decl=decl, timeout_s=timeout_s)
    if result.verdict is not Verdict.PASS:
        raise ValueError(
            f"ingest_lean_artifact: refusing to ingest decl={decl!r} at FORMALIZED -- "
            f"verifier result was {result.verdict.value}, not PASS "
            f"(details={result.details})"
        )
    return _record_verified_lean_artifact(
        ledger,
        store,
        module_source,
        decl,
        result,
        verifier=v,
        suite_hash=suite_hash,
        problem=problem,
        problem_version=problem_version,
        run_id=run_id,
    )


async def verify_and_ingest_lean_artifact(
    ledger: Ledger,
    store: Store,
    module_source: str,
    decl: str,
    *,
    verifier: LeanVerifier,
    problem: str = "P5",
    problem_version: str = DEFAULT_LEAN_PROBLEM_VERSION,
    run_id: str | None = None,
    timeout_s: float = 600.0,
) -> tuple[VerifierResult, Artifact | None]:
    """Async event-loop-safe version used by ``FormalizeLoop``.

    Lean verification runs in a worker because ``LeanVerifier.verify`` wraps
    ``asyncio.run``. All SQLite reads/writes stay on the owning event-loop
    thread.
    """
    suite_hash = _require_current_lean_certification(ledger, verifier)
    result = await asyncio.to_thread(
        verifier.verify,
        module_source,
        decl=decl,
        timeout_s=timeout_s,
    )
    if result.verdict is not Verdict.PASS:
        return result, None
    artifact = _record_verified_lean_artifact(
        ledger,
        store,
        module_source,
        decl,
        result,
        verifier=verifier,
        suite_hash=suite_hash,
        problem=problem,
        problem_version=problem_version,
        run_id=run_id,
    )
    return result, artifact


def _require_current_lean_certification(ledger: Ledger, verifier: LeanVerifier) -> str:
    # Local import avoids the intentional lean_goldens -> LeanVerifier type
    # dependency becoming a runtime import cycle.
    from empiricist.verifiers.lean_goldens import lean_suite_hash

    suite_hash = lean_suite_hash()
    ledger.require_certification(
        verifier.name,
        verifier.version,
        verifier.binary_hash,
        suite_hash,
    )
    return suite_hash


def _record_verified_lean_artifact(
    ledger: Ledger,
    store: Store,
    module_source: str,
    decl: str,
    result: VerifierResult,
    *,
    verifier: LeanVerifier,
    suite_hash: str,
    problem: str,
    problem_version: str,
    run_id: str | None,
) -> Artifact:
    """Record a PASS produced for these exact bytes; never called by users."""
    if result.verdict is not Verdict.PASS:
        raise ValueError("internal Lean recorder requires PASS")
    statement = result.details.get("statement")
    statement_hash = result.details.get("statement_hash")
    if not isinstance(statement, str) or not statement:
        raise ValueError("Lean PASS omitted the resolved theorem statement")
    expected_statement_hash = blake3(statement.encode("utf-8")).hexdigest()
    if statement_hash != expected_statement_hash:
        raise ValueError("Lean PASS statement_hash does not match its statement")
    if result.details.get("decl") != decl:
        raise ValueError("Lean PASS names a different declaration than the checked claim")

    content = module_source.encode("utf-8")
    digest = store.put(content)
    evidence_run_id = run_id
    if evidence_run_id is not None:
        try:
            ledger.get_run(evidence_run_id)
        except KeyError:
            # Deterministic fake clients do not create run receipts. Real
            # transports do, and their run id remains attached.
            evidence_run_id = None
    artifact = Artifact(
        id=digest,
        kind="lean",
        problem=problem,
        problem_version=problem_version,
        title=decl,
        content_path=digest,
        status=Status.FORMALIZED,
        run_id=evidence_run_id,
    )
    claim = Claim.create(
        artifact_id=artifact.id,
        problem=problem,
        problem_version=problem_version,
        statement=statement,
        family=decl,
        metric="theorem",
        scope={
            "axioms": list(result.details.get("axioms") or ()),
            "decl": decl,
            "statement_hash": statement_hash,
        },
    )
    evidence = EvidenceRow(
        artifact_id=artifact.id,
        claim_id=claim.id,
        run_id=evidence_run_id,
        verifier=verifier.name,
        verifier_version=verifier.version,
        binary_hash=verifier.binary_hash,
        golden_suite_hash=suite_hash,
        verdict=Verdict.PASS,
        details=result.details,
    )
    return ledger.record_claimed_artifact(
        artifact,
        claim,
        evidence,
        expected_golden_suite_hash=suite_hash,
    )

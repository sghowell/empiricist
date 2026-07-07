"""LeanVerifier: a real trust gate over the pinned EmpiricistLean project
(M8, spec 10/D7/exit criterion 4).

The FORMALIZED verdict rests on ONE authority: a COMPILED axiom-audit driver
(`lean/EmpiricistLean/AxiomAudit.lean`, built as the `axiom_audit` lean_exe).
The driver elaborates the submitted source with the real Lean frontend and then
computes the decl's axiom closure from COMPILED code that walks the kernel
environment (`Lean.collectAxioms` -- exactly what `#print axioms` calls
internally), never from a re-elaboratable command.

**Why the old in-band `#print axioms` design was UNSOUND.** The previous verifier
appended `#print axioms <decl>` to the scratch file and parsed its output line.
Two independent adversarial reviews defeated it:

- *Output forgery.* The source printed its own fake
  `'<decl>' depends on axioms: [propext, Classical.choice, Quot.sound]`
  info-diagnostic (via `#eval IO.println` / `run_cmd Lean.logInfo`); a first-match
  parse then certified `1 = 2` backed by `axiom evil : False`.
- *Command redefinition (the fatal one).* The source **redefines the
  `#print axioms` command itself** -- `elab "#print " "axioms" ... => logInfo
  "...clean..."` or `macro_rules | `(#print axioms $n) => ...`. The harness's own
  appended `#print axioms <decl>` then dispatches to the ATTACKER's elaborator and
  emits a fabricated clean axiom line -- nonce-anchored, exactly-one,
  whitelist-clean. Proven end-to-end.

The root cause is general: **any surface the harness re-elaborates in the tainted
environment (`#print`, `#eval`, `run_cmd`, macros) is attacker-shadowable.** The
axiom set MUST be computed by compiled harness code, not by a re-elaboratable
command. That is what the driver does; the harness never re-elaborates anything.

**How the driver's result cannot be forged.** The harness generates a fresh
unguessable nonce, writes it to a file, and passes the file path to the driver.
The driver reads the nonce and DELETES the file BEFORE elaborating the untrusted
source, so compile-time IO can never learn it. The driver elaborates under
`IO.FS.withIsolatedStreams` (so the source's `#eval`/`run_cmd` stdout is captured,
not leaked) and then writes EXACTLY ONE line to real stdout:
`AXIOM_AUDIT::<nonce>::{"declFound":bool,"errors":[...],"axioms":[...]}`. The
harness accepts ONLY a line bearing the exact nonce (`parse_driver_result`); a
source that writes a fake line to `/dev/stdout` and then `IO.Process.exit`s cannot
produce the nonce, so the audit fails closed (verified live). `sorryAx` and
`native_decide`'s synthesized per-decl axioms appear in `axioms` naturally, so the
whitelist membership test catches them.

Gate logic (`_verify_async`): non-empty `errors` -> FAIL(gate=diagnostics);
`declFound` false -> FAIL(gate=decl_missing) (fail closed); any axiom outside
`{propext, Classical.choice, Quot.sound}` -> FAIL(gate=axioms, offending); no valid
nonce-framed result line -> FAIL(gate=driver_result) (fail closed); else PASS.

Runs through `executor.execute()` -- the one audited subprocess path -- with
`sandbox=SandboxMode.NONE` and a MINIMAL scrubbed env (`env_passthrough=False` +
`env_extra` = PATH + HOME + ELAN_* only; see `_lean_env`). The elan TOOLCHAIN is
trusted, but the `module_source` is NOT trusted and runs IO at elaboration
(`#eval`, `initialize`), so a full `env_passthrough=True` would hand the parent's
secrets (ANTHROPIC*/AWS*/*_TOKEN/*_KEY/SSH_AUTH_SOCK) to attacker/model code at
compile time (a reviewer exfiltrated a secret env var through `#eval IO.getEnv`).
Scrubbing to PATH/HOME/ELAN_* keeps elan working and leaves the secrets absent
(regression-tested via an exfil probe). The env scrub is SOUND and load-bearing;
it is kept exactly as before.

`binary_hash` covers this module's own source PLUS the driver source
(`AxiomAudit.lean`), the project's `lean-toolchain`, `lake-manifest.json`, and
`lakefile.toml` bytes, so a `lake update` (mathlib bump), a toolchain bump, a
lakefile/leanOptions edit, OR a change to the compiled audit logic silently mints a
new verifier identity and drops any prior certification stamp.

Deliberately OUT of the P5 golden suite / `registry.Registry.certify()` flow (that
machinery is fusion-verifier-specific). LeanVerifier has its own suite
(`verifiers/lean_goldens.py`) and its own certify path
(`registry.certify_with_suite`, additive).
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from blake3 import blake3

from empiricist.executor.runner import ExecSpec, execute
from empiricist.executor.sandbox import SandboxMode
from empiricist.ledger.db import Ledger
from empiricist.ledger.ingest import ingest_artifact
from empiricist.ledger.models import Artifact, EvidenceRow, Status, Verdict
from empiricist.store import Store
from empiricist.verifiers.base import VerifierResult

# repo_root/lean/EmpiricistLean -- the pinned lake+mathlib project (M8 Task 1).
_DEFAULT_PROJECT_DIR = Path(__file__).resolve().parents[3] / "lean" / "EmpiricistLean"

# The only axioms that don't represent a proof-hygiene violation. Anything
# else -- sorryAx, native_decide's synthesized per-decl axiom, a custom axiom,
# Lean.ofReduceBool, Lean.trustCompiler -- is rejected by a plain membership
# test, so this does NOT need to name every bad axiom up front.
_AXIOM_WHITELIST = frozenset({"propext", "Classical.choice", "Quot.sound"})

# The framing marker the compiled driver prints its single result line with:
#   AXIOM_AUDIT::<nonce>::{"declFound":...,"errors":[...],"axioms":[...]}
_DRIVER_MARKER = "AXIOM_AUDIT"

_CAPTURE_CAP = 8 * 1024 * 1024  # generous: mathlib error messages can be long


def parse_driver_result(stdout: str, nonce: str) -> dict[str, Any] | None:
    """Extract the compiled driver's structured result from its stdout.

    Returns the parsed JSON object from the SINGLE line framed
    `AXIOM_AUDIT::<nonce>::<json>`, or None (fail closed) if no such line exists
    or the JSON is malformed.

    Only a line bearing the EXACT `nonce` is trusted -- this is the whole
    integrity story for the output channel. The untrusted source cannot learn
    the nonce (the driver deletes the nonce file before elaborating the source),
    so it cannot forge an accepted line even by writing directly to `/dev/stdout`
    and calling `IO.Process.exit` (verified live: such an attack yields a line
    with the WRONG nonce, which this rejects). A None return is ALWAYS a FAIL,
    never a PASS -- the audit fails closed.
    """
    prefix = f"{_DRIVER_MARKER}::{nonce}::"
    payloads = [
        line[line.index(prefix) + len(prefix):]
        for line in stdout.splitlines()
        if prefix in line
    ]
    if not payloads:
        return None
    # Only the driver can produce a correct-nonce line, and it produces exactly
    # one; take the last defensively.
    try:
        parsed = json.loads(payloads[-1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


class LeanVerifier:
    """Verifier wrapping the compiled `axiom_audit` driver over the pinned
    EmpiricistLean project. See module docstring for the trust model."""

    name = "lean"
    version = "2.0"

    def __init__(self, project_dir: Path | None = None) -> None:
        self._project_dir = project_dir or _DEFAULT_PROJECT_DIR
        self._module_dir = self._project_dir / "EmpiricistLean"
        self._driver_src = self._project_dir / "AxiomAudit.lean"
        self._driver_bin = self._project_dir / ".lake" / "build" / "bin" / "axiom_audit"
        self._driver_ready = False

    @property
    def binary_hash(self) -> str:
        """blake3 over this module's source + the compiled driver's source
        (AxiomAudit.lean) + the project's lean-toolchain, lake-manifest.json, and
        lakefile.toml bytes: pins the toolchain, the mathlib/dependency pin, the
        leanOptions/lakefile (which govern elaboration AND the exe target), AND
        the compiled audit logic into the verifier's identity (read fresh from
        disk on every access, so any of those changing invalidates an existing
        certification stamp)."""
        hasher = blake3()
        hasher.update(inspect.getsource(sys.modules[__name__]).encode("utf-8"))
        hasher.update(self._driver_src.read_bytes())
        hasher.update((self._project_dir / "lean-toolchain").read_bytes())
        hasher.update((self._project_dir / "lake-manifest.json").read_bytes())
        hasher.update((self._project_dir / "lakefile.toml").read_bytes())
        return hasher.hexdigest()

    def applicable(self, kind: str) -> bool:
        return kind == "lean"

    def verify(
        self, module_source: str, *, decl: str, timeout_s: float = 600.0
    ) -> VerifierResult:
        """Verify `module_source` compiles error-free and `decl`'s axiom closure
        is within the whitelist, via the compiled `axiom_audit` driver. Total --
        never raises: any failure (build/spawn/timeout/malformed output) becomes
        Verdict.ERROR with the message in details["error"], or a fail-closed
        Verdict.FAIL. Scratch/nonce cleanup ALWAYS runs (finally).

        Wraps `asyncio.run`, so it must NOT be called from a thread with a running
        event loop -- guarded (returns Verdict.ERROR rather than raising), keeping
        verify() total. (v0 callers are all synchronous.)"""
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
        scratch_path = self._module_dir / f"Scratch_{source_hash[:12]}.lean"
        # Fresh per call, NOT derived from source: the attacker cannot predict or
        # read it (the driver deletes the nonce file before elaborating), so
        # cannot forge an accepted result line.
        nonce = f"AXIOM_AUDIT_{uuid.uuid4().hex}"
        nonce_path = self._module_dir / f"Scratch_{source_hash[:12]}.nonce"
        try:
            return asyncio.run(
                self._verify_async(
                    module_source, decl=decl, timeout_s=timeout_s,
                    scratch_path=scratch_path, nonce=nonce, nonce_path=nonce_path,
                    source_hash=source_hash,
                )
            )
        except Exception as exc:
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={"error": f"{type(exc).__name__}: {exc}"},
            )
        finally:
            scratch_path.unlink(missing_ok=True)
            nonce_path.unlink(missing_ok=True)  # driver deletes it; belt-and-braces

    async def _verify_async(
        self, module_source: str, *, decl: str, timeout_s: float,
        scratch_path: Path, nonce: str, nonce_path: Path, source_hash: str,
    ) -> VerifierResult:
        build_err = await self._ensure_driver_async()
        if build_err is not None:
            return VerifierResult(verdict=Verdict.ERROR, details={"error": build_err})

        # The scratch file is the UNMODIFIED source -- the harness appends NOTHING
        # (no #print axioms, no #eval probe): there is no re-elaboratable surface
        # for the source to shadow. The driver computes the axiom set from
        # compiled code over the elaborated environment.
        scratch_path.write_text(module_source, encoding="utf-8")
        nonce_path.write_text(nonce, encoding="utf-8")

        exec_result = await execute(
            ExecSpec(
                argv=[
                    "lake", "env", str(self._driver_bin),
                    str(scratch_path), decl, str(nonce_path),
                ],
                move="LEAN_VERIFY",
                cwd=self._project_dir,
                sandbox=SandboxMode.NONE,
                # NOT env_passthrough=True: the SOURCE is untrusted and runs IO at
                # elaboration (#eval / initialize), so compile-time IO must not see
                # the parent's secrets. A minimal scrubbed env (PATH + HOME + ELAN_*
                # only) is enough for elan/lake/lean and leaves
                # ANTHROPIC*/AWS*/*_TOKEN/*_KEY/SSH_AUTH_SOCK absent -- verified by
                # an exfil-probe regression test.
                env_passthrough=False,
                env_extra=self._lean_env(),
                capture_cap=_CAPTURE_CAP,
                timeout_s=timeout_s,
            ),
            ledger=None,
        )
        if exec_result.timed_out:
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={"error": "axiom_audit subprocess timed out", "timeout_s": timeout_s},
            )
        if exec_result.rss_killed:
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={"error": "axiom_audit subprocess killed: RSS watchdog limit exceeded"},
            )

        result = parse_driver_result(exec_result.stdout, nonce)
        if result is None:
            # No trustworthy nonce-framed result line: the driver crashed, was
            # suppressed (source forced an early exit after writing a fake line),
            # or its output was tampered with. Fail closed -- never PASS.
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={
                    "gate": "driver_result",
                    "decl": decl,
                    "exit_code": exec_result.exit_code,
                    "stdout_tail": exec_result.stdout[-2000:],
                    "stderr_tail": exec_result.stderr[-2000:],
                },
            )

        errors = result.get("errors") or []
        if errors:
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"gate": "diagnostics", "errors": errors[:3]},
            )

        if not result.get("declFound"):
            # The decl is absent from the elaborated environment (typo, or it
            # failed to elaborate without a hard error). Fail closed.
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"gate": "decl_missing", "decl": decl},
            )

        axioms = result.get("axioms") or []
        offending = [a for a in axioms if a not in _AXIOM_WHITELIST]
        if offending:
            # Catches sorryAx, native_decide's synthesized axiom, and any custom
            # axiom (e.g. `evil`) the real proof depends on.
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"gate": "axioms", "axioms": axioms, "offending_axioms": offending},
            )

        return VerifierResult(
            verdict=Verdict.PASS,
            details={
                "decl": decl,
                "axioms": axioms,
                "toolchain": self._toolchain(),
                "mathlib_commit": self._mathlib_commit(),
                "source_hash": source_hash,
            },
        )

    async def _ensure_driver_async(self) -> str | None:
        """Build the `axiom_audit` driver once per verifier instance, via the
        audited `executor.execute()` path (no bare subprocess). Incremental `lake
        build` -- a fast no-op when up-to-date, a rebuild if the driver source
        changed. Returns None on success, or an error string on failure so
        `verify()` can ERROR: there is no fallback axiom authority. This is a
        TRUSTED build step (the pinned toolchain building harness-authored source),
        so no untrusted source is elaborated here -- but it still runs through the
        one audited subprocess path with the same scrubbed env."""
        if self._driver_ready:
            return None
        build = await execute(
            ExecSpec(
                argv=["lake", "build", "axiom_audit"],
                move="LEAN_BUILD_DRIVER",
                cwd=self._project_dir,
                sandbox=SandboxMode.NONE,
                env_passthrough=False,
                env_extra=self._lean_env(),
                capture_cap=_CAPTURE_CAP,
                timeout_s=600.0,
            ),
            ledger=None,
        )
        if build.timed_out:
            return "axiom_audit driver build timed out"
        if build.exit_code != 0 or not self._driver_bin.exists():
            return (
                f"`lake build axiom_audit` rc={build.exit_code}, "
                f"bin_exists={self._driver_bin.exists()}: {build.stderr[-2000:]}"
            )
        self._driver_ready = True
        return None

    @staticmethod
    def _lean_env() -> dict[str, str]:
        """The minimal env for elan/lake/lean, passed as `ExecSpec.env_extra`
        (with `env_passthrough=False`, so `execute()`'s `scrub_env` supplies the
        safe base and these override its workdir HOME/PATH).

        Includes ONLY: the parent PATH (with ~/.elan/bin ensured -- to resolve the
        elan shims and pinned toolchain), the real HOME (elan's ~/.elan and lake's
        caches live there), and any parent `ELAN*` vars. Everything else the parent
        holds -- crucially every secret -- is dropped: the untrusted source's
        compile-time IO must not be able to read it. PATH/HOME/ELAN_* are not
        secrets."""
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
    result: VerifierResult,
    *,
    verifier: LeanVerifier | None = None,
) -> Artifact:
    """Ingest `module_source` as a `kind='lean'` P5 artifact at
    `Status.FORMALIZED`, with an evidence row recording the LeanVerifier result.
    Entry status is the caller's claim (same discipline as
    `domain.p5.dataset.ingest_dataset`'s direct VERIFIED_N entry) -- the claim
    being made here is `result`, computed by an actual LeanVerifier run, not
    re-verified.

    `verifier` defaults to a fresh default-project-dir `LeanVerifier()`; pass the
    EXACT instance that produced `result` if it used a non-default `project_dir`,
    so the evidence row's binary_hash always names the verifier that actually ran.

    RAISES ValueError if `result.verdict is not Verdict.PASS`: a FORMALIZED
    artifact backed by anything less than a real PASS (error-free, axiom-clean)
    would be a false FORMALIZED claim -- no artifact and no evidence row are
    created in that case.
    """
    if result.verdict is not Verdict.PASS:
        raise ValueError(
            f"ingest_lean_artifact: refusing to ingest decl={decl!r} at FORMALIZED -- "
            f"verifier result was {result.verdict.value}, not PASS "
            f"(details={result.details})"
        )
    v = verifier if verifier is not None else LeanVerifier()
    art = ingest_artifact(
        ledger, store,
        content=module_source.encode("utf-8"),
        kind="lean",
        problem="P5",
        title=decl,
        status=Status.FORMALIZED,
    )
    ledger.record_evidence(
        EvidenceRow(
            artifact_id=art.id,
            verifier=v.name,
            verifier_version=v.version,
            binary_hash=v.binary_hash,
            verdict=result.verdict,
            details=result.details,
        )
    )
    return art

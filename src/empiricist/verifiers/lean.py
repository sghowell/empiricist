"""LeanVerifier: a real trust gate over the pinned EmpiricistLean project
(M8, spec 10/D7/exit criterion 4).

The FORMALIZED verdict now rests on the Lean KERNEL itself, re-checking the
compiled module through `leanchecker` (the standard `lean4checker`, merged into
the Lean toolchain since v4.28.0 and version-matched to our pinned v4.31.0). The
gate is a pipeline of four checks over ONE compiled artifact:

    (b) COMPILE   `lake env lean --json -o <olean> <scratch>`
                  severity=="error" -> FAIL(diagnostics); `sorry` warning -> FAIL(sorry)
    (c) KERNEL    `lake env leanchecker <Module>`         [THE TRUST ANCHOR]
                  nonzero exit / kernel-mismatch output -> FAIL(kernel_soundness)
    (d) AXIOMS    compiled `axiom_audit` driver over the SAME olean
                  axiom outside whitelist -> FAIL(axioms); also emits the STATEMENT
    (e) PASS      records the decl's resolved statement + statement_hash

**Why (c) is load-bearing — the hole it closes.** The previous verifier trusted a
compiled `collectAxioms` driver as the SOLE authority. That is UNSOUND against
*kernel-unchecked environment injection*: untrusted compile-time metaprogramming
(`run_cmd`/`elab`) can insert a constant with a FALSE type but a clean, axiom-free
value via `(getEnv).addDeclCore (doCheck := false)`, `Environment.add`, or
`set_option debug.skipKernelTC true; addDecl`. `Lean.collectAxioms` walks only the
stored term -> reports `axioms: []` -> a proof of `False` certified FORMALIZED.
Auditing WHICH AXIOMS a term cites is NOT the same as verifying the term was
KERNEL-CHECKED against its stated type. `leanchecker` re-checks the module's own
added declarations through the real kernel starting from its (trusted, pinned
mathlib) imports, so it rejects exactly these injections — proven end-to-end
(a `skipKernelTC` `1=2 := Eq.refl` is re-checked -> "declaration type mismatch").

**Why the axiom driver IMPORTS the compiled olean (not re-elaborate the source).**
Gate (d) must audit the SAME artifact leanchecker checked. If the driver
re-elaborated the source in a second frontend run, a source whose compile-time
metaprogramming branches on a clock / nondeterministic input could make the olean
leanchecker checked (honest branch) diverge from the env the audit sees (evil
branch). The driver `importModules` the one compiled olean, so every gate reads
the same bytes.

**Why the earlier axiom hole was itself real.** Two independent adversarial reviews
also defeated the *in-band* `#print axioms` predecessor (output forgery via
`#eval`/`run_cmd`; and — fatally — REDEFINING the `#print axioms` command). Any
surface the harness re-elaborates in the tainted environment is attacker-
shadowable, so the axiom set is computed by compiled code, and its result is
carried on a nonce-framed channel the untrusted source cannot forge (the driver
reads a fresh unguessable nonce from a file and DELETES it before importing the
module; imports run under `IO.FS.withIsolatedStreams`; only a line bearing the
exact nonce is accepted -> `parse_driver_result` fails closed otherwise).

All subprocesses run through `executor.execute()` -- the one audited path -- with
`sandbox=SandboxMode.NONE` and a MINIMAL scrubbed env (`env_passthrough=False` +
`env_extra` = PATH + HOME + ELAN_* only; see `_lean_env`). The elan TOOLCHAIN is
trusted, but `module_source` is NOT and runs IO at compile time (`#eval`,
`initialize`), so a full passthrough would hand the parent's secrets to
attacker/model code (a reviewer exfiltrated a secret env var through
`#eval IO.getEnv`). Scrubbing to PATH/HOME/ELAN_* keeps elan working and leaves
the secrets absent (regression-tested via an exfil probe). SOUND and load-bearing.

`binary_hash` covers this module's own source PLUS the driver source
(`AxiomAudit.lean`), the leanchecker pin manifest (`lean/lean4checker.pin.json`),
the project's `lean-toolchain`, `lake-manifest.json`, and `lakefile.toml` bytes:
a `lake update` (mathlib bump), a toolchain bump, a lakefile/leanOptions edit, a
change to the compiled audit logic, OR a change to the kernel-checker pin silently
mints a new verifier identity and drops any prior certification stamp.

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
# test, so this does NOT need to name every bad axiom up front. Note: these
# axioms are all KERNEL-VALID, so leanchecker (gate c) accepts them; the
# whitelist (gate d) is the hygiene layer leanchecker does not provide.
_AXIOM_WHITELIST = frozenset({"propext", "Classical.choice", "Quot.sound"})

# The framing marker the compiled driver prints its single result line with:
#   AXIOM_AUDIT::<nonce>::{"declFound":...,"errors":[...],"axioms":[...],"statement":...}
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


def parse_driver_result(stdout: str, nonce: str) -> dict[str, Any] | None:
    """Extract the compiled driver's structured result from its stdout.

    Returns the parsed JSON object from the SINGLE line framed
    `AXIOM_AUDIT::<nonce>::<json>`, or None (fail closed) if no such line exists
    or the JSON is malformed.

    Only a line bearing the EXACT `nonce` is trusted -- this is the whole
    integrity story for the output channel. The untrusted source cannot learn
    the nonce (the driver deletes the nonce file before importing the module),
    so it cannot forge an accepted line even by writing directly to `/dev/stdout`
    and calling `IO.Process.exit`. A None return is ALWAYS a FAIL, never a PASS.
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


def parse_compile_diagnostics(stdout: str) -> tuple[list[str], bool]:
    """Parse `lake env lean --json` diagnostics from stdout.

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
    """Verifier wrapping the kernel re-check (`leanchecker`) + compiled
    `axiom_audit` driver over the pinned EmpiricistLean project. See module
    docstring for the trust model."""

    name = "lean"
    version = "3.0"

    def __init__(self, project_dir: Path | None = None) -> None:
        self._project_dir = project_dir or _DEFAULT_PROJECT_DIR
        self._module_dir = self._project_dir / "EmpiricistLean"
        # Where `lake env lean -o` writes oleans and leanchecker/importModules
        # resolve them (the new module-system layout puts the project's LEAN_PATH
        # root at .lake/build/lib/lean, not .lake/build/lib).
        self._olean_root = self._project_dir / ".lake" / "build" / "lib" / "lean"
        self._driver_src = self._project_dir / "AxiomAudit.lean"
        self._driver_bin = self._project_dir / ".lake" / "build" / "bin" / "axiom_audit"
        self._pin_manifest = self._project_dir.parent / "lean4checker.pin.json"
        self._driver_ready = False

    @property
    def binary_hash(self) -> str:
        """blake3 over this module's source + the compiled driver's source
        (AxiomAudit.lean) + the leanchecker pin manifest + the project's
        lean-toolchain, lake-manifest.json, and lakefile.toml bytes. Pins the
        toolchain (which IS the kernel-checker's version), the mathlib pin, the
        lakefile/leanOptions, the compiled audit logic, AND the leanchecker pin
        into the verifier's identity (read fresh from disk on every access, so
        any of those changing invalidates an existing certification stamp)."""
        hasher = blake3()
        hasher.update(inspect.getsource(sys.modules[__name__]).encode("utf-8"))
        hasher.update(self._driver_src.read_bytes())
        hasher.update(self._pin_manifest.read_bytes())
        hasher.update((self._project_dir / "lean-toolchain").read_bytes())
        hasher.update((self._project_dir / "lake-manifest.json").read_bytes())
        hasher.update((self._project_dir / "lakefile.toml").read_bytes())
        return hasher.hexdigest()

    def applicable(self, kind: str) -> bool:
        return kind == "lean"

    def verify(
        self, module_source: str, *, decl: str, timeout_s: float = 600.0
    ) -> VerifierResult:
        """Verify `module_source` compiles error-free, is KERNEL-SOUND (leanchecker),
        and `decl`'s axiom closure is within the whitelist. Total -- never raises:
        any failure (build/spawn/timeout/malformed output) becomes Verdict.ERROR
        with the message in details["error"], or a fail-closed Verdict.FAIL.
        Per-invocation scratch/nonce/olean cleanup ALWAYS runs (finally).

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
        # Per-invocation UNIQUE token (uuid4), NOT keyed on source_hash: two
        # concurrent verify() calls -- even of the SAME source -- get distinct
        # scratch/nonce/olean paths, closing both the concurrent-verify nonce-leak
        # window and the same-source cleanup race. `Scratch_` prefix keeps the
        # module component a valid Lean identifier for any uuid hex.
        tok = f"Scratch_{uuid.uuid4().hex}"
        module_name = f"EmpiricistLean.{tok}"
        scratch_path = self._module_dir / f"{tok}.lean"
        nonce_path = self._module_dir / f"{tok}.nonce"
        olean_path = self._olean_root / "EmpiricistLean" / f"{tok}.olean"
        # Fresh per call: the attacker cannot predict or read it (the driver
        # deletes the nonce file before importing), so cannot forge a result line.
        nonce = f"AXIOM_AUDIT_{uuid.uuid4().hex}"
        try:
            return asyncio.run(
                self._verify_async(
                    module_source, decl=decl, timeout_s=timeout_s,
                    module_name=module_name, scratch_path=scratch_path,
                    nonce=nonce, nonce_path=nonce_path, olean_path=olean_path,
                    source_hash=source_hash,
                )
            )
        except Exception as exc:
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={"error": f"{type(exc).__name__}: {exc}"},
            )
        finally:
            # Per-invocation cleanup: every artifact this call created, by its
            # unique paths. Unconditional (missing_ok) -- the driver also deletes
            # the nonce, and a gate may have short-circuited before the olean.
            scratch_path.unlink(missing_ok=True)
            nonce_path.unlink(missing_ok=True)
            olean_path.unlink(missing_ok=True)

    async def _verify_async(
        self, module_source: str, *, decl: str, timeout_s: float,
        module_name: str, scratch_path: Path, nonce: str, nonce_path: Path,
        olean_path: Path, source_hash: str,
    ) -> VerifierResult:
        build_err = await self._ensure_driver_async()
        if build_err is not None:
            return VerifierResult(verdict=Verdict.ERROR, details={"error": build_err})

        # The scratch file is the UNMODIFIED source -- the harness appends NOTHING.
        scratch_path.write_text(module_source, encoding="utf-8")
        nonce_path.write_text(nonce, encoding="utf-8")
        olean_path.parent.mkdir(parents=True, exist_ok=True)
        scratch_rel = scratch_path.relative_to(self._project_dir)

        # -- Gate (b): COMPILE to an olean, capturing --json diagnostics. --------
        compile_res = await execute(
            ExecSpec(
                argv=[
                    "lake", "env", "lean", "--json",
                    "-o", str(olean_path), str(scratch_rel),
                ],
                move="LEAN_COMPILE",
                cwd=self._project_dir,
                sandbox=SandboxMode.NONE,
                env_passthrough=False,
                env_extra=self._lean_env(),
                capture_cap=_CAPTURE_CAP,
                timeout_s=timeout_s,
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
                details={"gate": "diagnostics", "errors": errors[:3]},
            )
        if sorry_hit:
            return VerifierResult(verdict=Verdict.FAIL, details={"gate": "sorry"})
        if not olean_path.exists():
            # No error diagnostics but no olean either: fail closed -- we cannot
            # kernel-check a module that did not compile.
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={
                    "gate": "diagnostics",
                    "reason": "no olean produced",
                    "exit_code": compile_res.exit_code,
                    "stderr_tail": compile_res.stderr[-2000:],
                },
            )

        # -- Gate (c): KERNEL re-check via leanchecker (THE TRUST ANCHOR). -------
        lc_res = await execute(
            ExecSpec(
                argv=["lake", "env", "leanchecker", module_name],
                move="LEAN_KERNEL_CHECK",
                cwd=self._project_dir,
                sandbox=SandboxMode.NONE,
                env_passthrough=False,
                env_extra=self._lean_env(),
                capture_cap=_CAPTURE_CAP,
                timeout_s=timeout_s,
            ),
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
            # The injected `1=2 := Eq.refl` (or any kernel-bypass forgery) is
            # re-checked by the real kernel and rejected here. Fail closed.
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={
                    "gate": "kernel_soundness",
                    "decl": decl,
                    "leanchecker_exit": lc_res.exit_code,
                    "leanchecker_output": lc_out.strip()[-2000:],
                },
            )

        # -- Gate (d): AXIOM SET + STATEMENT over the SAME kernel-checked olean. --
        audit_res = await execute(
            ExecSpec(
                argv=[
                    "lake", "env", str(self._driver_bin),
                    module_name, decl, str(nonce_path),
                ],
                move="LEAN_AXIOM_AUDIT",
                cwd=self._project_dir,
                sandbox=SandboxMode.NONE,
                env_passthrough=False,
                env_extra=self._lean_env(),
                capture_cap=_CAPTURE_CAP,
                timeout_s=timeout_s,
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
            # Import errors over a module that compiled + passed the kernel would
            # be anomalous -- fail closed.
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"gate": "diagnostics", "errors": driver_errors[:3]},
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
                "source_hash": source_hash,
            },
        )

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

    async def _ensure_driver_async(self) -> str | None:
        """Build the `axiom_audit` driver once per verifier instance, via the
        audited `executor.execute()` path. Incremental `lake build` -- a fast
        no-op when up-to-date. Returns None on success, or an error string on
        failure. This is a TRUSTED build step (the pinned toolchain building
        harness-authored source)."""
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
        """The minimal env for elan/lake/lean/leanchecker, passed as
        `ExecSpec.env_extra` (with `env_passthrough=False`).

        Includes ONLY: the parent PATH (with ~/.elan/bin ensured -- to resolve the
        elan shims and pinned toolchain, incl. `leanchecker`), the real HOME
        (elan's ~/.elan and lake's caches live there), and any parent `ELAN*`
        vars. Everything else the parent holds -- crucially every secret -- is
        dropped: the untrusted source's compile-time IO must not read it."""
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
    `Status.FORMALIZED`, with an evidence row recording the LeanVerifier result
    (including the resolved `statement` + `statement_hash`: a referee sees WHAT
    was proven, not just a clean axiom set). Entry status is the caller's claim
    (same discipline as `domain.p5.dataset.ingest_dataset`).

    `verifier` defaults to a fresh default-project-dir `LeanVerifier()`; pass the
    EXACT instance that produced `result` if it used a non-default `project_dir`.

    RAISES ValueError if `result.verdict is not Verdict.PASS`: a FORMALIZED
    artifact backed by anything less than a real PASS would be a false FORMALIZED
    claim -- no artifact and no evidence row are created in that case.
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

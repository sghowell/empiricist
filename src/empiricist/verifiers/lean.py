"""LeanVerifier: a real `lake env lean --json` verifier over the pinned
EmpiricistLean project (M8, spec 10/D7/exit criterion 4).

Two gates, both load-bearing:

- **Gate 1 (diagnostics).** ANY diagnostic with `severity == "error"` -> FAIL.
  This is the sound half. The UNSOUND half, empirically confirmed against
  Lean 4.31.0 during M8 Task 1: `lake env lean --json` exits 0 on a clean
  file (empty stdout) -- exactly as it does on a file containing nothing but
  `sorry`. A `sorry` shows up ONLY as a `severity == "warning"` diagnostic
  (`kind == "hasSorry"`, data containing the text "declaration uses sorry"), so exit
  code is UNSOUND as a completeness gate and this verifier never reads it.
  Any warning whose kind is `hasSorry` or whose text mentions "sorry" also
  FAILs gate 1 (the sorry trap) -- other warnings are recorded but allowed.

- **Gate 2 (axiom audit).** Only reached if gate 1 is clean. `#print axioms
  <decl>` is run and its output line -- `'<decl>' depends on axioms: [...]`
  or `'<decl>' does not depend on any axioms` (both shapes confirmed live)
  -- is parsed; every axiom must be in `{propext, Classical.choice,
  Quot.sound}` (the three mathlib/Lean-core axioms that are foundational,
  not proof-hygiene violations). Anything else -- `sorryAx` (confirmed:
  `[sorryAx]`), or `native_decide`'s per-declaration synthesized axiom
  (confirmed live: `[<decl>._native.native_decide.ax_1_1]`, NOT a fixed name
  like `Lean.ofReduceBool` -- the whitelist check is a membership test
  against the fixed-three set, so it catches this regardless of the
  offending axiom's exact/generated name) -- FAILs.

**Implementation deviation from the M8 plan's literal wording, confirmed by
running it:** the plan describes gate 2 as "a second small file importing
the module". That does not work for a scratch module that was never `lake
build`-ed: `import EmpiricistLean.Scratch_xxx` in a probe file fails with
`object file '.../Scratch_xxx.olean' ... does not exist`, because `lake env
lean --json` on a direct file target does not produce `.olean`s -- only
`lake build` does, and running a full incremental build per verify() call
would be far slower and would write scratch artifacts into `.lake/build`.
Instead, the `#print axioms <decl>` command is appended to the END of the
SAME scratch file (after `module_source`) and gates 1+2 run in ONE `lake env
lean --json` subprocess call. Verified against every golden case: Lean
processes commands in a file sequentially, so the axiom print sees whatever
was elaborated earlier in the same file (including a `sorry`-tainted decl,
which still elaborates -- `sorryAx` shows up correctly) -- `#print axioms`
is `severity == "information"`, so it never trips gate 1's error/warning
checks on its own.

Runs through `executor.execute()` -- the one audited subprocess path -- with
`sandbox=SandboxMode.NONE` and `env_passthrough=True`: elan's shim/toolchain
resolution needs the real PATH/HOME, and (per `execute()`'s own invariant)
`env_passthrough` requires `sandbox=NONE` anyway. This is a TRUSTED
toolchain invocation (harness-authored scratch files, like the `claude` CLI
call in `llm/client.py`), not an untrusted/model-adjacent one.

`binary_hash` covers this module's own source PLUS the project's
`lean-toolchain` and `lake-manifest.json` bytes, so a `lake update` (mathlib
bump) or a toolchain bump silently mints a new verifier identity and drops
any prior certification stamp -- exactly the fusion verifiers' binary_hash
discipline (base.py's `module_source_hash`), extended to pin the external
toolchain/dependency graph a Lean verifier also depends on.

Deliberately OUT of the P5 golden suite / `registry.Registry.certify()` flow
(that machinery is fusion-verifier-specific: `Verifier.verify(construction)`
over `domain.p5.construction.Construction`). LeanVerifier has its own suite
(`verifiers/lean_goldens.py`) and its own certify path
(`registry.certify_with_suite`, additive) since its `verify()` takes a Lean
source string + a decl name, not a `Construction`.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import re
import sys
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
# else -- sorryAx, native_decide's synthesized per-decl axiom, a custom
# axiom, Lean.ofReduceBool, Lean.trustCompiler -- is rejected by a plain
# membership test, so this does NOT need to name every bad axiom up front.
_AXIOM_WHITELIST = frozenset({"propext", "Classical.choice", "Quot.sound"})

# Both real, confirmed shapes of `#print axioms <decl>`'s info-diagnostic text:
#   'Empiricist.connected_edge_bound' depends on axioms: [propext, Classical.choice, Quot.sound]
#   'Empiricist.scaffold_true' does not depend on any axioms
#   'Empiricist.nd' depends on axioms: [Empiricist.nd._native.native_decide.ax_1_1]
_AXIOM_DEPENDS_RE = re.compile(r"\A'(?P<decl>.+)' depends on axioms: \[(?P<axioms>.*)\]\Z")
_AXIOM_NONE_RE = re.compile(r"\A'(?P<decl>.+)' does not depend on any axioms\Z")

_CAPTURE_CAP = 8 * 1024 * 1024  # generous: mathlib error messages can be long


def parse_diagnostics(stdout: str) -> list[dict[str, Any]]:
    """Parse `lake env lean --json` stdout: one JSON object per non-empty
    line (confirmed: a clean file's stdout is EMPTY, not `[]` or `{}` --
    this returns `[]` for that case, same as for literally no lines)."""
    diags = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        diags.append(json.loads(line))
    return diags


def parse_axiom_line(diagnostics: list[dict[str, Any]], decl: str) -> list[str] | None:
    """Find the `#print axioms <decl>` info-diagnostic among `diagnostics`
    and return its axiom list (`[]` for the axiom-free shape), or None if no
    diagnostic's `data` matches EITHER real shape for exactly this `decl`."""
    for d in diagnostics:
        data = d.get("data", "")
        m = _AXIOM_DEPENDS_RE.match(data)
        if m and m.group("decl") == decl:
            raw = m.group("axioms").strip()
            return [] if not raw else [a.strip() for a in raw.split(",")]
        m = _AXIOM_NONE_RE.match(data)
        if m and m.group("decl") == decl:
            return []
    return None


def _is_sorry_warning(d: dict[str, Any]) -> bool:
    return d.get("kind") == "hasSorry" or "sorry" in d.get("data", "").lower()


class LeanVerifier:
    """Verifier wrapping `lake env lean --json` over the pinned
    EmpiricistLean project. See module docstring for the two-gate contract."""

    name = "lean"
    version = "1.0"

    def __init__(self, project_dir: Path | None = None) -> None:
        self._project_dir = project_dir or _DEFAULT_PROJECT_DIR
        self._module_dir = self._project_dir / "EmpiricistLean"

    @property
    def binary_hash(self) -> str:
        """blake3 over this module's source + the project's lean-toolchain +
        lake-manifest.json bytes: pins the toolchain/mathlib pin into the
        verifier's identity (read fresh from disk on every access, so a
        `lake update` invalidates any existing certification stamp)."""
        hasher = blake3()
        hasher.update(inspect.getsource(sys.modules[__name__]).encode("utf-8"))
        hasher.update((self._project_dir / "lean-toolchain").read_bytes())
        hasher.update((self._project_dir / "lake-manifest.json").read_bytes())
        return hasher.hexdigest()

    def applicable(self, kind: str) -> bool:
        return kind == "lean"

    def verify(
        self, module_source: str, *, decl: str, timeout_s: float = 600.0
    ) -> VerifierResult:
        """Verify `module_source` compiles sorry-free and `decl`'s axiom
        closure is within the whitelist. Total: never raises -- any failure
        (subprocess spawn, timeout, malformed output) becomes Verdict.ERROR
        with the message in details["error"]. Scratch file cleanup ALWAYS
        runs (finally), regardless of outcome."""
        source_hash = blake3(module_source.encode("utf-8")).hexdigest()
        scratch_path = self._module_dir / f"Scratch_{source_hash[:12]}.lean"
        try:
            return asyncio.run(
                self._verify_async(
                    module_source, decl=decl, timeout_s=timeout_s,
                    scratch_path=scratch_path, source_hash=source_hash,
                )
            )
        except Exception as exc:
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={"error": f"{type(exc).__name__}: {exc}"},
            )
        finally:
            scratch_path.unlink(missing_ok=True)

    async def _verify_async(
        self, module_source: str, *, decl: str, timeout_s: float,
        scratch_path: Path, source_hash: str,
    ) -> VerifierResult:
        # Gates 1+2 in ONE file/subprocess call -- see module docstring for
        # why gate 2 is NOT a separate probe file importing the scratch module.
        scratch_path.write_text(
            f"{module_source}\n\n#print axioms {decl}\n", encoding="utf-8"
        )
        rel = scratch_path.relative_to(self._project_dir)
        exec_result = await execute(
            ExecSpec(
                argv=["lake", "env", "lean", "--json", str(rel)],
                move="LEAN_VERIFY",
                cwd=self._project_dir,
                sandbox=SandboxMode.NONE,
                env_passthrough=True,  # elan needs the real PATH/HOME (trusted toolchain)
                capture_cap=_CAPTURE_CAP,
                timeout_s=timeout_s,
            ),
            ledger=None,
        )
        if exec_result.timed_out:
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={"error": "lean subprocess timed out", "timeout_s": timeout_s},
            )
        if exec_result.rss_killed:
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={"error": "lean subprocess killed: RSS watchdog limit exceeded"},
            )

        diagnostics = parse_diagnostics(exec_result.stdout)

        errors = [d for d in diagnostics if d.get("severity") == "error"]
        if errors:
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={
                    "gate": "diagnostics",
                    "errors": [d.get("data", "") for d in errors[:3]],
                },
            )

        sorry_warnings = [
            d for d in diagnostics if d.get("severity") == "warning" and _is_sorry_warning(d)
        ]
        if sorry_warnings:
            # The exit-code trap: sorry is a WARNING (exit 0), never an error.
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={
                    "gate": "sorry",
                    "warnings": [d.get("data", "") for d in sorry_warnings[:3]],
                },
            )

        other_warnings = [
            d.get("data", "") for d in diagnostics if d.get("severity") == "warning"
        ]

        axioms = parse_axiom_line(diagnostics, decl)
        if axioms is None:
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={
                    "error": f"could not find '#print axioms {decl}' output for decl={decl!r}",
                    "stdout_tail": exec_result.stdout[-2000:],
                },
            )

        offending = [a for a in axioms if a not in _AXIOM_WHITELIST]
        if offending:
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
                "warnings": other_warnings,
            },
        )

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
    `Status.FORMALIZED`, with an evidence row recording the LeanVerifier
    result. Entry status is the caller's claim (same discipline as
    `domain.p5.dataset.ingest_dataset`'s direct VERIFIED_N entry) -- the
    claim being made here is `result`, computed by an actual LeanVerifier
    run, not re-verified.

    `verifier` defaults to a fresh default-project-dir `LeanVerifier()`
    (the v0-only project); pass the EXACT instance that produced `result`
    if it used a non-default `project_dir` (e.g. a test double), so the
    evidence row's binary_hash always names the verifier that actually ran,
    never a different one's identity.

    RAISES ValueError if `result.verdict is not Verdict.PASS`: a FORMALIZED
    artifact backed by anything less than a real PASS (sorry-free,
    axiom-clean) would be a false FORMALIZED claim -- no artifact and no
    evidence row are created in that case.
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

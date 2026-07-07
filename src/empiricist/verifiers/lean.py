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

  **Spoofing defense (security review C1).** The source can print its OWN
  fake `'<decl>' depends on axioms: [propext, Classical.choice, Quot.sound]`
  info-diagnostic (via `#eval IO.println` or `run_cmd Lean.logInfo`) BEFORE
  the appended real `#print axioms` -- a naive first-match parse then
  certifies a `1 = 2` proof backed by a custom `axiom evil : False` with a
  fabricated clean axiom list (the `logInfo` vector genuinely PASSed in
  review). `audit_axiom_lines` closes it: the harness appends
  `#eval IO.println "<fresh-nonce>"` right before the real `#print axioms`,
  and accepts the axiom line only if it is the SINGLE decl-axiom-line in the
  whole stream AND appears strictly after the unpredictable nonce marker.
  A forged line (which the attacker can only place ABOVE the nonce) makes
  the count 2 -> FAIL(gate="axiom_tamper"); the audit fails closed.

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
`sandbox=SandboxMode.NONE` and a MINIMAL scrubbed env (`env_passthrough=False`
+ `env_extra` = PATH + HOME + ELAN_* only; see `_lean_env`). The elan
TOOLCHAIN is trusted (harness-authored scratch files run through the pinned
mathlib, like the `claude` CLI call in `llm/client.py`), and elan's
shim/toolchain resolution genuinely needs the real PATH/HOME -- but the
`module_source` is NOT trusted and runs IO at elaboration (`#eval`,
`initialize`), so a full `env_passthrough=True` would hand the parent's
secrets (ANTHROPIC*/AWS*/*_TOKEN/*_KEY/SSH_AUTH_SOCK) to attacker/model code
at compile time (a reviewer exfiltrated a secret env var through `#eval
IO.getEnv`). Scrubbing to PATH/HOME/ELAN_* keeps elan working and leaves the
secrets absent (regression-tested via an exfil probe).

`binary_hash` covers this module's own source PLUS the project's
`lean-toolchain`, `lake-manifest.json`, and `lakefile.toml` bytes, so a
`lake update` (mathlib bump), a toolchain bump, or a leanOptions/lakefile
edit silently mints a new verifier identity and drops any prior
certification stamp -- exactly the fusion verifiers' binary_hash discipline
(base.py's `module_source_hash`), extended to pin the external
toolchain/dependency/elaboration-options graph a Lean verifier depends on.

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
import os
import re
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


def parse_axiom_data(data: str, decl: str) -> list[str] | None:
    """Parse ONE diagnostic's `data` string as a `#print axioms <decl>`
    line: return its axiom list (`[]` for the axiom-free shape), or None if
    `data` doesn't match EITHER real shape for exactly this `decl`.

    `data` is stripped of surrounding whitespace FIRST -- deliberately, as a
    security measure: an attacker forging a fake axiom line via
    `#eval IO.println` (which appends a trailing newline to the diagnostic's
    `data`) must NOT be able to dodge being counted just because their fake
    line carries whitespace the `#print axioms` output does not. Every
    plausible fake shape parses here so `audit_axiom_lines` can COUNT it and
    trip the tamper gate (see that function)."""
    data = data.strip()
    m = _AXIOM_DEPENDS_RE.match(data)
    if m and m.group("decl") == decl:
        raw = m.group("axioms").strip()
        return [] if not raw else [a.strip() for a in raw.split(",")]
    m = _AXIOM_NONE_RE.match(data)
    if m and m.group("decl") == decl:
        return []
    return None


def audit_axiom_lines(
    diagnostics: list[dict[str, Any]], decl: str, nonce: str
) -> tuple[list[str] | None, dict[str, Any]]:
    """Nonce-anchored, exactly-one axiom-line extraction -- the defense
    against `#print axioms` spoofing (M8 T2 security review C1).

    A submitted `module_source` can emit its OWN fabricated
    `'<decl>' depends on axioms: [propext, Classical.choice, Quot.sound]`
    info-diagnostic (via `#eval IO.println "..."` or
    `run_cmd Lean.logInfo "..."`) BEFORE the harness-appended real
    `#print axioms`. A naive first-match parse would return the CLEAN fake
    list and PASS a proof of `1 = 2` backed by a custom `axiom evil : False`
    (reproduced during review -- the `logInfo` vector genuinely PASSed).
    Two belt-and-suspenders checks close it:

    a. **Nonce anchor.** The harness appends `#eval IO.println "<nonce>"`
       (a fresh uuid4-derived marker the attacker cannot predict) right
       before the real `#print axioms`. The attacker controls only source
       ABOVE that block, so they cannot position any diagnostic after the
       nonce marker. The accepted axiom line MUST appear strictly after the
       diagnostic containing the exact `nonce`.
    b. **Exactly one.** Across the WHOLE diagnostics stream there must be
       exactly ONE line parsing as an axiom line for `decl`. The injection
       produces two (the fake + the real), tripping this even before the
       position check; a same-decl-name collision trips it too.

    Returns `(axioms, info)`: `axioms` is the trustworthy single axiom list
    when BOTH checks pass, else None (tampering / probe suppressed). `info`
    (`nonce_found`, `count`, `lines`) is the evidence recorded on a tamper
    FAIL. A None return is ALWAYS a FAIL, never a PASS -- the audit fails
    closed."""
    anchor = next(
        (i for i, d in enumerate(diagnostics) if nonce in d.get("data", "")), None
    )
    matches = [
        (i, axioms, d.get("data", ""))
        for i, d in enumerate(diagnostics)
        if (axioms := parse_axiom_data(d.get("data", ""), decl)) is not None
    ]
    info = {
        "nonce_found": anchor is not None,
        "count": len(matches),
        "lines": [line for _, _, line in matches],
    }
    if len(matches) != 1:
        return None, info
    idx, axioms, _ = matches[0]
    if anchor is None or idx <= anchor:
        # The single axiom line is at/before the nonce marker (or the marker
        # is missing entirely -- e.g. source `#exit`s before the appended
        # probe runs): not the harness's own trustworthy print.
        return None, info
    return axioms, info


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
        """blake3 over this module's source + the project's lean-toolchain,
        lake-manifest.json, and lakefile.toml bytes: pins the toolchain,
        the mathlib/dependency pin, AND the leanOptions (which govern
        elaboration) into the verifier's identity (read fresh from disk on
        every access, so a `lake update`, a toolchain bump, or a lakefile
        edit invalidates any existing certification stamp)."""
        hasher = blake3()
        hasher.update(inspect.getsource(sys.modules[__name__]).encode("utf-8"))
        hasher.update((self._project_dir / "lean-toolchain").read_bytes())
        hasher.update((self._project_dir / "lake-manifest.json").read_bytes())
        hasher.update((self._project_dir / "lakefile.toml").read_bytes())
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
        runs (finally), regardless of outcome.

        Wraps `asyncio.run`, so it must NOT be called from a thread with a
        running event loop -- that would raise `RuntimeError` inside
        `asyncio.run` (and leak a never-awaited coroutine). Guarded: if a
        loop is already running this returns Verdict.ERROR rather than
        raising, keeping verify() total. (v0 callers are all synchronous:
        registry certification, the dataset/ingest path, the CLI.)"""
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
        # Fresh per call, NOT derived from source: the attacker cannot predict
        # it, so cannot position a forged axiom line after the nonce marker.
        nonce = f"AXIOM_PROBE_{uuid.uuid4().hex[:16]}"
        try:
            return asyncio.run(
                self._verify_async(
                    module_source, decl=decl, timeout_s=timeout_s,
                    scratch_path=scratch_path, source_hash=source_hash, nonce=nonce,
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
        scratch_path: Path, source_hash: str, nonce: str,
    ) -> VerifierResult:
        # Gates 1+2 in ONE file/subprocess call -- see module docstring for
        # why gate 2 is NOT a separate probe file importing the scratch module.
        # The `#eval IO.println "<nonce>"` marker is the anchor for the axiom
        # audit's spoofing defense (audit_axiom_lines): every diagnostic the
        # attacker can emit is ABOVE it, so the real #print axioms output is
        # the only axiom line after it.
        scratch_path.write_text(
            f'{module_source}\n\n#eval IO.println "{nonce}"\n\n#print axioms {decl}\n',
            encoding="utf-8",
        )
        rel = scratch_path.relative_to(self._project_dir)
        exec_result = await execute(
            ExecSpec(
                argv=["lake", "env", "lean", "--json", str(rel)],
                move="LEAN_VERIFY",
                cwd=self._project_dir,
                sandbox=SandboxMode.NONE,
                # NOT env_passthrough=True: the SOURCE is untrusted and runs IO
                # at elaboration (#eval / initialize), so compile-time IO must
                # not see the parent's secrets. A minimal scrubbed env (PATH +
                # HOME + ELAN_* only) is enough for elan/lake/lean and leaves
                # ANTHROPIC*/AWS*/*_TOKEN/*_KEY/SSH_AUTH_SOCK absent -- verified
                # by an exfil-probe regression test. env_passthrough=False makes
                # execute() route through scrub_env, and env_extra overrides its
                # workdir HOME (which would break elan's ~/.elan lookup).
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

        axioms, audit_info = audit_axiom_lines(diagnostics, decl, nonce)
        if axioms is None:
            # Spoofing/tamper (forged axiom line, duplicate print, or the
            # nonce probe suppressed) -- fails closed, never PASS.
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"gate": "axiom_tamper", "decl": decl, **audit_info},
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

    @staticmethod
    def _lean_env() -> dict[str, str]:
        """The minimal env for elan/lake/lean, passed as `ExecSpec.env_extra`
        (with `env_passthrough=False`, so `execute()`'s `scrub_env` supplies
        the safe base and these override its workdir HOME/PATH).

        Includes ONLY: the parent PATH (with ~/.elan/bin ensured -- to resolve
        the elan shims and pinned toolchain), the real HOME (elan's ~/.elan and
        lake's caches live there), and any parent `ELAN*` vars (ELAN_HOME /
        ELAN_TOOLCHAIN relocations). Everything else the parent holds --
        crucially every secret -- is dropped: the untrusted source's
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

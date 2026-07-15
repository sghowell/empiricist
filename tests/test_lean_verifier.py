"""LeanVerifier tests (M8): the SANDBOXED KERNEL-re-check trust gate against REAL
Lean 4.31.0. The gate is a pipeline over one compiled olean, every untrusted step
run under sandbox-exec with a pinned-trusted LEAN_PATH -- compile (`--json`
diagnostics), import-trust (`--deps`, Lever 2), KERNEL re-check (`leanchecker`, the
trust anchor), axiom whitelist + import-closure + statement (the compiled
`axiom_audit` driver over the same olean), then PASS. These tests exercise the
honest PASS (with recorded statement), every must-FAIL golden -- the kernel-unchecked
ENVIRONMENT-INJECTION PoCs (`skipKernelTC`, `addDeclCore (doCheck := false)`,
`Environment.replay`), the earlier axiom-forgery / command-override vectors, and the
4th break's COMPILE-TIME POISON-IMPORT class (plant->harvest end-to-end, sandboxed
write denial, reachable-import rejection, residue sweep) -- the FORMALIZED ingestion
path, the env-scrub exfil regression, per-invocation isolation, and offline
`parse_driver_result` / `parse_compile_diagnostics` tests.

Tests that invoke real lake/lean are marked `slow_lean` and skipped when the
toolchain or the pinned project aren't available. A session-scoped fixture builds
the driver once up front (so a cold cache can't flake a per-case timeout); each
verify() is compile ~2s + leanchecker ~1s + audit ~2s once mathlib oleans warm.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Status, Verdict
from empiricist.store import Store
from empiricist.verifiers.base import VerifierResult
from empiricist.verifiers.lean import (
    LeanVerifier,
    ingest_lean_artifact,
    parse_compile_diagnostics,
    parse_driver_result,
)
from empiricist.verifiers.lean_goldens import LEAN_GOLDEN_SUITE, certify_lean, lean_suite_hash

_PROJECT_DIR = Path(__file__).resolve().parents[1] / "lean" / "EmpiricistLean"
_MODULE_DIR = _PROJECT_DIR / "EmpiricistLean"
# Where `lake env lean -o` writes per-invocation scratch oleans (module layout).
_OLEAN_DIR = _PROJECT_DIR / ".lake" / "build" / "lib" / "lean" / "EmpiricistLean"

_lake_available = (
    shutil.which("lake") is not None
    and shutil.which("lean") is not None
    and (_PROJECT_DIR / "lake-manifest.json").exists()
)

slow_lean = pytest.mark.slow_lean
requires_lake = pytest.mark.skipif(
    not _lake_available, reason="lake/lean toolchain or the pinned project is not available"
)

_GOLDEN_IDS = [
    "sorry_free_true", "sorry_trap", "native_decide", "type_error",
    "spoof_io_println", "spoof_run_cmd", "override_elab", "override_macro",
    "inject_driver_result", "inject_skip_kernel_tc", "inject_add_decl_core",
    "inject_replay", "true_statement", "poison_import", "unexpected_import",
    "compile_time_olean_write", "toctou_olean_swap",
]

# Exploit sources for the Lever 1/2/3 integration tests. `__POISON__` is replaced
# with the absolute shared-build-lib poison path at call time. Single braces are
# Lean record literals; the embedded sh script contains no `"`/`\` so it nests
# cleanly inside the Lean string. (Substituted via str.replace, NOT .format, so the
# Lean `{ … }` record literals are left intact.)
_COMPILE_TIME_WRITE_EXPLOIT = """\
namespace Empiricist
theorem plant_ok : True := trivial
end Empiricist

#eval (do
  let direct := "__POISON__"
  try IO.FS.writeFile direct "poison" catch _ => pure ()
  let sh := "echo poison > __POISON__"
  try
    (do let _ ← IO.Process.output { cmd := "sh", args := #["-c", sh] }; pure ())
  catch _ => pure ()
  : IO Unit)
"""

_POISON_PLANT_CALL1 = """\
namespace Empiricist
theorem plant_ok : True := trivial
end Empiricist

#eval (do
  let _ ← IO.Process.output { cmd := "sh", args := #["-c", "set -e
cat > /tmp/EmpPoisonPlant.lean <<'LEOF'
import Lean
open Lean Elab Command Term Meta
run_cmd liftTermElabM do
  let type  ← instantiateMVars (← elabTerm (← `(False)) none)
  let value ← instantiateMVars (← elabTerm (← `(@Eq.refl Nat 0)) none)
  let decl : Declaration := .thmDecl
    { name := `EmpiricistLean.Poison.boom, levelParams := [],
      type := type, value := value }
  match (← getEnv).addDeclCore (0 : USize) decl none (doCheck := false) with
  | .ok env' => setEnv env'
  | .error _ => pure ()
LEOF
lean -o __POISON__ /tmp/EmpPoisonPlant.lean
"] }
  pure ()
  : IO Unit)
"""


@pytest.fixture(scope="session", autouse=True)
def _warm_lean_toolchain():
    """Build the `axiom_audit` driver ONCE per session, OUTSIDE any per-case
    timeout, so a cold cache can't flake an individual slow_lean case. No-op when
    the toolchain/project is unavailable. `leanchecker` (gate c) ships with the
    pinned toolchain, so it needs no build."""
    if not _lake_available:
        yield
        return
    import asyncio

    asyncio.run(LeanVerifier()._ensure_ready_async())
    yield


@pytest.fixture()
def verifier():
    return LeanVerifier()


@pytest.fixture()
def ledger(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    yield lg
    lg.close()


@pytest.fixture()
def store(tmp_path):
    return Store(tmp_path / "cas")


# -- real-lake goldens (slow_lean) -------------------------------------------


@slow_lean
@requires_lake
@pytest.mark.parametrize("source,decl,expected_pass", LEAN_GOLDEN_SUITE, ids=_GOLDEN_IDS)
def test_golden_case_matches_expected_verdict(verifier, source, decl, expected_pass):
    result = verifier.verify(source, decl=decl, timeout_s=120)
    assert (result.verdict == Verdict.PASS) == expected_pass, result.details


@slow_lean
@requires_lake
def test_sorry_golden_fails_at_the_sorry_gate(verifier):
    """`sorry` is a WARNING (`lean` exits 0), so a naive exit-code gate would PASS
    it. The compile gate parses `--json` diagnostics and catches the `hasSorry`
    warning at compile time (gate=sorry). (`collectAxioms`'s `sorryAx` is the
    backstop had the warning ever been missing.)"""
    source, decl, _ = LEAN_GOLDEN_SUITE[1]
    result = verifier.verify(source, decl=decl, timeout_s=120)
    assert result.verdict == Verdict.FAIL, result.details
    assert result.details["gate"] == "sorry", result.details


@slow_lean
@requires_lake
@pytest.mark.parametrize(
    "case_index,name",
    [(9, "skip_kernel_tc"), (10, "add_decl_core")],
)
def test_kernel_injection_pocs_fail_at_kernel_soundness_gate(verifier, case_index, name):
    """THE soundness fix's teeth. Both PoCs inject a constant with a FALSE type
    (`(1:Nat)=2`) but a clean, axiom-free value (`Eq.refl`) by bypassing the
    kernel (`debug.skipKernelTC` / `addDeclCore (doCheck := false)`). They compile
    with NO diagnostics and `collectAxioms` would see `[]` -- but `leanchecker`
    re-checks the module's added decls through the REAL kernel and rejects the
    `1 = 1 :≠ 1 = 2` mismatch (gate=kernel_soundness). A proof of `False` no longer
    certifies FORMALIZED."""
    source, decl, expected_pass = LEAN_GOLDEN_SUITE[case_index]
    assert expected_pass is False
    result = verifier.verify(source, decl=decl, timeout_s=120)
    assert result.verdict == Verdict.FAIL, result.details
    assert result.details["gate"] == "kernel_soundness", result.details
    assert result.details["leanchecker_exit"] != 0, result.details
    assert "type mismatch" in result.details["leanchecker_output"], result.details


@slow_lean
@requires_lake
def test_environment_replay_injection_rejected_at_compile(verifier):
    """`Environment.replay` of a hand-built false `ConstantInfo` is rejected by the
    kernel already at COMPILE (replay is itself a kernel-checking mechanism), so it
    fails at gate=diagnostics rather than kernel_soundness. Kept to pin that even
    the kernel's own replay refuses the injection."""
    source, decl, expected_pass = LEAN_GOLDEN_SUITE[11]
    assert expected_pass is False
    result = verifier.verify(source, decl=decl, timeout_s=120)
    assert result.verdict == Verdict.FAIL, result.details
    assert result.details["gate"] == "diagnostics", result.details


@slow_lean
@requires_lake
def test_pass_records_resolved_statement(verifier):
    """Provenance hole B: a PASS must record the decl's RESOLVED statement, so a
    referee sees WHAT was proven, not just a clean axiom set. `theorem t : True :=
    trivial` PASSes with details['statement'] == 'True' and a statement_hash."""
    source, decl, expected_pass = LEAN_GOLDEN_SUITE[12]
    assert expected_pass is True
    result = verifier.verify(source, decl=decl, timeout_s=120)
    assert result.verdict == Verdict.PASS, result.details
    assert result.details["statement"] == "True", result.details
    assert result.details["statement_hash"], result.details
    assert result.details["axioms"] == []


@slow_lean
@requires_lake
def test_native_decide_golden_fails_axiom_audit(verifier):
    """native_decide's axiom is a per-declaration SYNTHESIZED name -- the whitelist
    membership test catches it regardless of the exact generated name."""
    source, decl, _ = LEAN_GOLDEN_SUITE[2]
    result = verifier.verify(source, decl=decl, timeout_s=120)
    assert result.verdict == Verdict.FAIL, result.details
    assert result.details["gate"] == "axioms"
    assert result.details["offending_axioms"]
    assert all(
        a not in {"propext", "Classical.choice", "Quot.sound"}
        for a in result.details["offending_axioms"]
    )


@slow_lean
@requires_lake
def test_type_error_golden_fails_diagnostics_gate(verifier):
    source, decl, _ = LEAN_GOLDEN_SUITE[3]
    result = verifier.verify(source, decl=decl, timeout_s=120)
    assert result.verdict == Verdict.FAIL, result.details
    assert result.details["gate"] == "diagnostics"


@slow_lean
@requires_lake
@pytest.mark.parametrize(
    "case_index",
    [4, 5, 6, 7, 8],
    ids=["spoof_io_println", "spoof_run_cmd", "override_elab", "override_macro",
         "inject_driver_result"],
)
def test_axiom_forgery_and_command_override_reveal_the_evil_axiom(verifier, case_index):
    """The soundness fix's teeth. Every vector is a genuine `1 = 2` proof backed by
    `axiom evil : False`, plus an attempt to hide it -- forging the `#print axioms`
    output (`#eval`/`run_cmd`), REDEFINING the `#print axioms` command itself
    (`elab`/`macro_rules`, the vector that certified `1=2` as FORMALIZED under the
    old verifier), or injecting a fake `AXIOM_AUDIT::` driver-result line. The
    compiled driver runs NO `#print axioms`; `collectAxioms` reveals the real
    dependency `Empiricist.evil` (gate=axioms), never the fabricated clean set."""
    source, decl, expected_pass = LEAN_GOLDEN_SUITE[case_index]
    assert expected_pass is False
    result = verifier.verify(source, decl=decl, timeout_s=120)
    assert result.verdict == Verdict.FAIL, result.details
    assert result.details["gate"] == "axioms", result.details
    assert "Empiricist.evil" in result.details["offending_axioms"], result.details


@slow_lean
@requires_lake
def test_secret_env_var_not_visible_to_compile_time_eval(verifier, monkeypatch):
    """I1: the untrusted source runs IO at elaboration. A secret set in the PARENT
    env must NOT reach a Lean `#eval IO.getEnv` (the reviewer's exfil probe). The
    probe compiles clean IFF the var is absent from the child (throws -> gate-1
    error IFF visible), so a PASS here proves the scrub."""
    monkeypatch.setenv("EMPIRICIST_EXFIL_PROBE", "leaked-secret-value")
    source = (
        "namespace Empiricist\n"
        "theorem scaffold_true : 1 + 1 = 2 := rfl\n"
        "end Empiricist\n\n"
        "#eval (do\n"
        '  let v ← IO.getEnv "EMPIRICIST_EXFIL_PROBE"\n'
        '  if v.isSome then throw (IO.userError "SECRET_VISIBLE") '
        "else pure () : IO Unit)\n"
    )
    result = verifier.verify(source, decl="Empiricist.scaffold_true", timeout_s=120)
    # PASS => the #eval did NOT see the secret (it would have thrown -> error).
    assert result.verdict == Verdict.PASS, result.details


@slow_lean
@requires_lake
def test_certify_lean_passes_on_the_live_suite(ledger, verifier):
    cert = certify_lean(ledger, verifier)
    assert cert.verdict == Verdict.PASS
    assert cert.verifier == "lean"
    assert cert.golden_suite_hash == lean_suite_hash()


@slow_lean
@requires_lake
def test_scaffold_lemma_verifies_pass_and_ingests_formalized(ledger, store, verifier):
    """The M8 headline path: the real Basic.lean scaffold lemma
    (`connected_edge_bound`) verifies PASS end-to-end and ingests as the harness's
    first FORMALIZED artifact, with the LeanVerifier evidence row attached."""
    source = (_MODULE_DIR / "Basic.lean").read_text()
    decl = "Empiricist.connected_edge_bound"
    result = verifier.verify(source, decl=decl, timeout_s=120)
    assert result.verdict == Verdict.PASS, result.details
    assert result.details["axioms"] == ["propext", "Classical.choice", "Quot.sound"]
    # Provenance hole B: the resolved statement is recorded on the PASS.
    assert "Fintype.card V - 1 ≤" in result.details["statement"], result.details
    assert result.details["statement_hash"]

    art = ingest_lean_artifact(ledger, store, source, decl, result, verifier=verifier)
    assert art.kind == "lean"
    assert art.problem == "P5"
    assert art.status == Status.FORMALIZED

    fetched = ledger.get_artifact(art.id)
    assert fetched.status == Status.FORMALIZED

    ev = ledger.evidence_for(art.id)
    assert len(ev) == 1
    assert ev[0].verifier == "lean"
    assert ev[0].verifier_version == "3.3"
    assert ev[0].verdict == Verdict.PASS
    assert ev[0].details["decl"] == decl
    assert ev[0].details["mathlib_commit"]
    # The FORMALIZED evidence carries the statement + its hash.
    assert ev[0].details["statement"] == result.details["statement"]
    assert ev[0].details["statement_hash"] == result.details["statement_hash"]

    assert store.get(art.content_path).decode("utf-8") == source


@slow_lean
@requires_lake
def test_ingest_lean_artifact_rejects_non_pass(ledger, store, verifier):
    source, decl, _ = LEAN_GOLDEN_SUITE[1]  # sorry trap: verifies FAIL
    result = verifier.verify(source, decl=decl, timeout_s=120)
    assert result.verdict == Verdict.FAIL
    with pytest.raises(ValueError):
        ingest_lean_artifact(ledger, store, source, decl, result)
    # No partial artifact from a rejected ingest.
    assert ledger.find_artifacts(kind="lean") == []


@slow_lean
@requires_lake
def test_ephemeral_workdirs_cleaned_and_shared_dirs_residue_free(verifier):
    """Lever 3 cleanup: each verify() runs in a UNIQUE ephemeral workdir (system
    tempdir) removed in finally -- no `empiricist-lean-*` dir leaks -- and the SHARED
    project source/build dirs are never written to (no Scratch_*/poison residue),
    across PASS and every FAIL gate in the suite."""
    import tempfile

    tmp_root = Path(tempfile.gettempdir())
    before_tmp = set(tmp_root.glob("empiricist-lean-*"))
    before_src = set(_MODULE_DIR.glob("Scratch_*"))
    before_olean = set(_OLEAN_DIR.glob("Scratch_*")) if _OLEAN_DIR.exists() else set()
    for source, decl, _ in LEAN_GOLDEN_SUITE:
        verifier.verify(source, decl=decl, timeout_s=120)
    assert set(tmp_root.glob("empiricist-lean-*")) == before_tmp  # workdirs removed
    assert set(_MODULE_DIR.glob("Scratch_*")) == before_src  # shared source untouched
    after_olean = set(_OLEAN_DIR.glob("Scratch_*")) if _OLEAN_DIR.exists() else set()
    assert after_olean == before_olean  # shared build lib untouched
    # A clean subsequent verify must not trip the residue gate.
    ok = verifier.verify(
        "namespace Empiricist\ntheorem t : True := trivial\nend Empiricist\n",
        decl="Empiricist.t", timeout_s=120,
    )
    assert ok.verdict == Verdict.PASS, ok.details


@slow_lean
@requires_lake
def test_compile_time_poison_plant_write_is_denied_by_sandbox(verifier):
    """LEVER 1, RAW: the 4th exploit's plant half. A compile-time `#eval` (both a
    direct `IO.FS.writeFile` and a spawned `sh -c`) tries to write a POISON olean
    into the shared build lib. The sandbox DENIES the write (writes confined to the
    ephemeral workdir); the theorem itself is `True`, so verify() legitimately
    PASSes, but the poison file must NEVER materialize."""
    shared_poison = _OLEAN_DIR / "Poison.olean"
    shared_poison.unlink(missing_ok=True)
    src = _COMPILE_TIME_WRITE_EXPLOIT.replace("__POISON__", str(shared_poison))
    result = verifier.verify(src, decl="Empiricist.plant_ok", timeout_s=120)
    assert result.verdict == Verdict.PASS, result.details  # True is true
    assert not shared_poison.exists(), "sandbox failed to deny the compile-time poison write"


@slow_lean
@requires_lake
def test_poison_plant_then_harvest_exploit_fails(verifier):
    """THE 4th break, end-to-end through the real verify(). Call 1 plants a poison
    olean via a compile-time `#eval` sh-spawn; call 2 imports it to harvest a false
    `2 = 3`. With the fix, call 1's write is DENIED (no poison persists) and call 2's
    import is unresolvable/untrusted -> call 2 must NOT PASS. Two calls on ONE
    persistent verifier -- exactly how the harness reuses it."""
    shared_poison = _OLEAN_DIR / "Poison.olean"
    shared_poison.unlink(missing_ok=True)
    call1 = _POISON_PLANT_CALL1.replace("__POISON__", str(shared_poison))
    call2 = (
        "import EmpiricistLean.Poison\nnamespace Empiricist\n"
        "theorem grandclaim : (2 : Nat) = 3 := (EmpiricistLean.Poison.boom).elim\n"
        "end Empiricist\n"
    )
    try:
        verifier.verify(call1, decl="Empiricist.plant_ok", timeout_s=120)
        assert not shared_poison.exists(), "poison persisted across calls (sandbox breach)"
        r2 = verifier.verify(call2, decl="Empiricist.grandclaim", timeout_s=120)
        assert r2.verdict != Verdict.PASS, r2.details  # a false 2=3 must NEVER PASS
    finally:
        shared_poison.unlink(missing_ok=True)


@slow_lean
@requires_lake
def test_toctou_olean_swap_detached_child_cannot_pass(verifier):
    """THE 5th break, end-to-end through the real verify(). An HONEST module whose
    compile-time `run_cmd` spawns a DETACHED child that swaps a `2 = 3` poison olean
    over `work/<tok>.olean` between leanchecker (gate c) and the audit driver
    (gate d). Under the old code this returned PASS on `statement == '2 = 3'` with
    `axioms == []`. It must now NEVER PASS on the false claim: the kernel-input olean
    is FROZEN read-only outside `work` (both gates read the honest snapshot), the
    compile is fork/exec-denied (the spawn is refused), and the executor reaps the
    process group on normal completion. Swept across swap-delays to be sure there is
    no residual window."""
    from empiricist.verifiers.lean_goldens import _TOCTOU_OLEAN_SWAP_SOURCE

    def _delayed_variant(delay: float) -> str:
        # A fixed-delay worker (the reviewer's t2e sweep) rather than the nonce-watch
        # default -- probes the whole gate-c-end -> gate-d-read window directly.
        worker = (
            "t=; while [ x$t = x ]; do "
            "t=$(ls *.olean 2>/dev/null | grep -v poison_stage | head -1); done; "
            "cp poison_stage.olean READY.olean; "
            f"sleep {delay}; mv READY.olean $t"
        )
        return (
            "import Lean\nopen Lean Elab Command Term Meta\n\n"
            "namespace Empiricist\ntheorem honest : True := trivial\nend Empiricist\n\n"
            "run_cmd liftTermElabM do\n"
            "  let ty ← instantiateMVars (← elabTerm (← `((2:Nat)=3)) none)\n"
            "  let vl ← instantiateMVars (← elabTerm (← `(@Eq.refl Nat 2)) none)\n"
            "  let d : Declaration := .thmDecl "
            "{ name := `Empiricist.evil_claim, levelParams := [], type := ty, value := vl }\n"
            "  let env ← getEnv\n"
            "  match env.addDeclCore (0 : USize) d none (doCheck := false) with\n"
            "  | .ok env' =>\n"
            "      Lean.writeModule env' \"poison_stage.olean\"\n"
            "      let worker := \"" + worker + "\"\n"
            "      let _ ← IO.Process.spawn "
            "{ cmd := \"sh\", args := #[\"-c\", worker], "
            "stdout := .null, stderr := .null, stdin := .null }\n"
            "      pure ()\n  | .error _ => pure ()\n"
        )

    # The suite golden (nonce-watch, delay-free) first.
    r = verifier.verify(_TOCTOU_OLEAN_SWAP_SOURCE, decl="Empiricist.evil_claim", timeout_s=120)
    assert r.verdict != Verdict.PASS, r.details
    assert (r.details.get("statement") or "").replace(" ", "") != "2=3", r.details

    # Then a swap-delay sweep across the gate-c -> gate-d window.
    for delay in (0.0, 1.0, 2.0, 3.0, 4.0, 5.0):
        rd = verifier.verify(_delayed_variant(delay), decl="Empiricist.evil_claim", timeout_s=120)
        assert rd.verdict != Verdict.PASS, (delay, rd.details)
        assert (rd.details.get("statement") or "").replace(" ", "") != "2=3", (delay, rd.details)


@slow_lean
@requires_lake
def test_reachable_nonpinned_import_rejected_by_import_trust(verifier):
    """LEVER 2 in isolation (defense-in-depth even if Lever 1 had a gap). Plant a
    poison olean on a TRUSTED root (the read-only Basic lib) so the import RESOLVES,
    then verify a scratch importing it. The import-trust gate rejects a non-`Basic`
    EmpiricistLean import -> FAIL(import_trust), never a PASS on the false claim."""
    import subprocess

    # Force readiness so the toolchain cfg + trusted lib dir exist.
    verifier.verify(
        "namespace Empiricist\ntheorem t : True := trivial\nend Empiricist\n",
        decl="Empiricist.t", timeout_s=120,
    )
    cfg = verifier._cfg
    assert cfg is not None
    poison_src = Path("/tmp/EmpPoisonL2.lean")
    poison_src.write_text(
        "import Lean\nopen Lean Elab Command Term Meta\n"
        "run_cmd liftTermElabM do\n"
        "  let t ← instantiateMVars (← elabTerm (← `(False)) none)\n"
        "  let v ← instantiateMVars (← elabTerm (← `(@Eq.refl Nat 0)) none)\n"
        "  let d : Declaration := .thmDecl { name := `EmpiricistLean.Poison.boom,"
        " levelParams := [], type := t, value := v }\n"
        "  match (← getEnv).addDeclCore (0:USize) d none (doCheck := false) with\n"
        "  | .ok e => setEnv e | .error _ => pure ()\n"
    )
    poison_olean = cfg.trusted_lib_dir / "EmpiricistLean" / "Poison.olean"
    import os as _os

    lp = _os.pathsep.join([*(str(r) for r in cfg.trusted_roots), str(cfg.trusted_lib_dir)])
    try:
        subprocess.run(
            [str(cfg.lean_bin), "-o", str(poison_olean), "--root", "/tmp", str(poison_src)],
            env={**_os.environ, "LEAN_PATH": lp, "LEAN_SYSROOT": cfg.sysroot},
            check=True, capture_output=True,
        )
        assert poison_olean.exists()
        harvest = (
            "import EmpiricistLean.Poison\nnamespace Empiricist\n"
            "theorem grandclaim : (2 : Nat) = 3 := (EmpiricistLean.Poison.boom).elim\n"
            "end Empiricist\n"
        )
        r = verifier.verify(harvest, decl="Empiricist.grandclaim", timeout_s=120)
        assert r.verdict == Verdict.FAIL, r.details
        assert r.details["gate"] == "import_trust", r.details
        assert r.details["untrusted_imports"], r.details
    finally:
        poison_olean.unlink(missing_ok=True)
        poison_src.unlink(missing_ok=True)


@slow_lean
@requires_lake
def test_foundation_is_a_usable_trusted_import(verifier):
    """PROMOTION headline: `EmpiricistLean.Foundation` (the Fable-authored fusion
    lower bound, added to the trusted-foundation SET {Basic, Foundation}) is now a
    USABLE trusted import. A scratch that imports it and specializes
    `Empiricist.fusion_cost_lower_bound` verifies PASS -- proving Foundation's olean is
    staged onto the frozen import path and the import-trust gate accepts it as a
    member of the trusted set (its own axioms clean, a real statement recorded)."""
    source = (
        "import EmpiricistLean.Foundation\n"
        "namespace Empiricist\n"
        "theorem foundation_lb_usable (N g f : Nat) (c : Nat → Nat)\n"
        "    (hN : 3 ≤ N) (hqubits : N + 2 * f = 3 * g)\n"
        "    (h0 : c 0 = g) (hf : c f = 1)\n"
        "    (hstep : ∀ i, i < f → c i ≤ c (i + 1) + 1) :\n"
        "    N - 3 ≤ f :=\n"
        "  fusion_cost_lower_bound N g f c hN hqubits h0 hf hstep\n"
        "end Empiricist\n"
    )
    result = verifier.verify(source, decl="Empiricist.foundation_lb_usable", timeout_s=120)
    assert result.verdict == Verdict.PASS, result.details
    # Foundation was actually imported and accepted as a trusted EmpiricistLean import.
    assert "EmpiricistLean" in result.details["import_roots"], result.details
    # A real statement is recorded (provenance) and the axiom set is within whitelist.
    assert result.details["statement"], result.details
    assert all(
        a in {"propext", "Classical.choice", "Quot.sound"}
        for a in result.details["axioms"]
    ), result.details


@slow_lean
@requires_lake
def test_nontrusted_empiricist_module_still_rejected_by_import_trust(verifier):
    """The whitelist is a PRECISE SET {Basic, Foundation}, NOT "any EmpiricistLean.*".
    Stage the REAL, committed-but-NON-trusted `EmpiricistLean.FamilyUpper` olean onto
    the trusted lib dir (alongside Basic/Foundation) so `import EmpiricistLean.FamilyUpper`
    RESOLVES, then verify a scratch importing it. The import-trust gate rejects it --
    it is not in the trusted set -> FAIL(import_trust) -- even though Foundation, a
    sibling olean in the SAME dir, is accepted. Promotion widened the set to exactly
    {Basic, Foundation}; it did NOT open the door to every EmpiricistLean module."""
    # Force readiness so the toolchain cfg + trusted lib dir exist and are staged.
    verifier.verify(
        "namespace Empiricist\ntheorem t : True := trivial\nend Empiricist\n",
        decl="Empiricist.t", timeout_s=120,
    )
    cfg = verifier._cfg
    assert cfg is not None
    family_src = _OLEAN_DIR / "FamilyUpper.olean"
    assert family_src.exists(), "FamilyUpper.olean not built (run `lake build EmpiricistLean`)"
    staged = cfg.trusted_lib_dir / "EmpiricistLean" / "FamilyUpper.olean"
    shutil.copyfile(family_src, staged)
    try:
        harvest = (
            "import EmpiricistLean.FamilyUpper\n"
            "namespace Empiricist\ntheorem t2 : True := trivial\nend Empiricist\n"
        )
        r = verifier.verify(harvest, decl="Empiricist.t2", timeout_s=120)
        assert r.verdict == Verdict.FAIL, r.details
        assert r.details["gate"] == "import_trust", r.details
        assert r.details["untrusted_imports"], r.details
        assert any("FamilyUpper" in p for p in r.details["untrusted_imports"]), r.details
    finally:
        staged.unlink(missing_ok=True)


@slow_lean
@requires_lake
def test_residue_sweep_fails_closed_on_stray_shared_file(verifier):
    """LEVER 3: a stray, non-pinned olean in the shared build lib (a prior/concurrent
    call that escaped its jail) makes the NEXT verify() FAIL closed at gate=residue,
    rather than trust a possibly-poisoned environment."""
    stray = _OLEAN_DIR / "Stray.olean"
    stray.write_text("junk")
    try:
        r = verifier.verify(
            "namespace Empiricist\ntheorem t : True := trivial\nend Empiricist\n",
            decl="Empiricist.t", timeout_s=120,
        )
        assert r.verdict == Verdict.FAIL, r.details
        assert r.details["gate"] == "residue", r.details
        assert any("Stray.olean" in f for f in r.details["unexpected_files"]), r.details
    finally:
        stray.unlink(missing_ok=True)


@slow_lean
@requires_lake
def test_concurrent_same_source_verifies_do_not_collide(verifier):
    """Reviewer finding C: keying scratch/nonce on source_hash[:12] made two
    concurrent verifies of the SAME source share paths (nonce-leak + cleanup race).
    Per-invocation uuid4 keying makes them independent: running the same source
    twice in parallel threads both PASS and leave no residue."""
    import concurrent.futures

    source, decl, _ = LEAN_GOLDEN_SUITE[0]
    before = set(_MODULE_DIR.glob("Scratch_*"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futs = [pool.submit(verifier.verify, source, decl=decl, timeout_s=120)
                for _ in range(2)]
        results = [f.result() for f in futs]
    assert all(r.verdict == Verdict.PASS for r in results), [r.details for r in results]
    assert set(_MODULE_DIR.glob("Scratch_*")) == before


@slow_lean
@requires_lake
def test_scratch_cleanup_on_error_path(monkeypatch, verifier):
    """finally-cleanup must fire even when the body raises -> ERROR."""
    import empiricist.verifiers.lean as lean_mod

    def boom(*a, **k):
        raise RuntimeError("parser exploded")

    monkeypatch.setattr(lean_mod, "parse_driver_result", boom)
    before = set(_MODULE_DIR.glob("Scratch_*"))
    source, decl, _ = LEAN_GOLDEN_SUITE[0]
    result = verifier.verify(source, decl=decl, timeout_s=120)
    assert result.verdict == Verdict.ERROR
    assert "parser exploded" in result.details["error"]
    after = set(_MODULE_DIR.glob("Scratch_*"))
    assert after == before


def test_ingest_lean_artifact_records_the_given_verifiers_identity(ledger, store):
    """The evidence row's binary_hash must name the EXACT verifier instance that
    produced `result`, not a fresh default-project-dir one. No real lake/lean call
    needed -- the VerifierResult is fabricated directly."""

    class FakeVerifier(LeanVerifier):
        @property
        def binary_hash(self):
            return "f" * 64

    fake = FakeVerifier()
    result = VerifierResult(verdict=Verdict.PASS, details={"decl": "Empiricist.x"})
    art = ingest_lean_artifact(
        ledger, store, "theorem x : True := trivial", "Empiricist.x", result, verifier=fake
    )
    ev = ledger.evidence_for(art.id)
    assert ev[0].binary_hash == "f" * 64
    assert ev[0].binary_hash != LeanVerifier().binary_hash


def test_verify_error_verdict_on_bad_project_dir():
    """Total verify(): a nonexistent project dir must ERROR, never raise -- fails
    at the driver build step (no real lake/lean toolchain needed)."""
    bogus = LeanVerifier(project_dir=Path("/nonexistent/not/a/real/empiricist-lean-project"))
    result = bogus.verify("theorem t : True := trivial", decl="t", timeout_s=30)
    assert result.verdict == Verdict.ERROR
    assert "error" in result.details


# -- fast, offline: identity + suite shape -----------------------------------


def test_identity():
    assert LeanVerifier.name == "lean"
    assert LeanVerifier.version == "3.3"


def test_applicable():
    v = LeanVerifier()
    assert v.applicable("lean") is True
    assert v.applicable("construction") is False


def test_lean_golden_suite_has_both_a_pass_and_must_fail_cases():
    """A suite that can't fail certifies nothing (spec §7 mutation-resistance)."""
    assert any(expected is True for _, _, expected in LEAN_GOLDEN_SUITE)
    assert any(expected is False for _, _, expected in LEAN_GOLDEN_SUITE)


def test_lean_golden_suite_covers_the_command_override_vectors():
    """The soundness fix must be pinned by must-FAIL goldens for BOTH the output
    forgery and the command-redefinition vectors, else a regression could reopen
    the hole and still certify."""
    sources = [src for src, _, _ in LEAN_GOLDEN_SUITE]
    joined = "\n".join(sources)
    assert 'elab "#print " "axioms "' in joined  # elab command override
    assert "macro_rules" in joined  # macro_rules command override
    assert "AXIOM_AUDIT::" in joined  # driver-result output injection
    assert "axiom evil : False" in joined  # each backed by a genuine bad axiom


def test_lean_golden_suite_covers_the_kernel_injection_vectors():
    """The KERNEL-soundness fix must be pinned by must-FAIL goldens for every
    kernel-unchecked environment-injection surface, so a regression that reopened
    the hole could no longer earn a certification stamp."""
    sources = [src for src, _, _ in LEAN_GOLDEN_SUITE]
    joined = "\n".join(sources)
    assert "debug.skipKernelTC" in joined  # PoC-1: skipKernelTC injection
    assert "doCheck := false" in joined  # PoC-2: addDeclCore no-check injection
    assert "Environment.replay" in joined  # PoC-3: replay hand-built constant
    # each injects a false `1 = 2` and derives a proof of False from it
    assert "theorem boom : False" in joined


def test_lean_golden_suite_covers_the_poison_import_vectors():
    """The COMPILE-TIME POISON-IMPORT fix (M8 v4) must be pinned by must-FAIL
    goldens: the poison-import harvest, an unexpected (non-pinned) import, and a
    compile-time-olean-write attempt -- so a regression that dropped the sandbox or
    the import-trust gate could no longer earn a certification stamp."""
    cases = {decl: (src, exp) for src, decl, exp in LEAN_GOLDEN_SUITE}
    joined = "\n".join(src for src, _, _ in LEAN_GOLDEN_SUITE)
    # poison-import HARVEST: imports the planted sibling + derives a false 2 = 3
    assert "import EmpiricistLean.Poison" in joined
    assert "EmpiricistLean.Poison.boom" in joined
    # UNEXPECTED import (a non-pinned module) must be present and must-FAIL
    assert "import Untrusted.Evil" in joined
    # compile-time-olean-WRITE attempt into the shared build lib
    assert "Poison.olean" in joined and "IO.FS.writeFile" in joined
    # all three are must-FAIL
    for decl in ("Empiricist.grandclaim", "Empiricist.one_eq_two"):
        assert decl in cases and cases[decl][1] is False


def test_lean_golden_suite_covers_the_toctou_olean_swap_vector():
    """The gate-c/d TOCTOU olean-swap fix (M8 v5) must be pinned by a must-FAIL
    golden: an honest module whose compile-time `run_cmd` spawns a detached child to
    swap a `2 = 3` poison olean over `work/<tok>.olean` between the kernel gates. A
    regression that dropped the frozen snapshot / fork-exec deny / group-reap could
    otherwise reopen the hole and still earn a certification stamp."""
    cases = {decl: (src, exp) for src, decl, exp in LEAN_GOLDEN_SUITE}
    joined = "\n".join(src for src, _, _ in LEAN_GOLDEN_SUITE)
    # a detached-child spawn that swaps a staged poison olean over the scratch olean
    assert "IO.Process.spawn" in joined
    assert "poison_stage.olean" in joined
    assert "mv READY.olean" in joined
    assert "evil_claim" in joined
    assert "Empiricist.evil_claim" in cases and cases["Empiricist.evil_claim"][1] is False


def test_binary_hash_changes_when_manifest_bytes_differ(monkeypatch):
    """binary_hash pins the toolchain: tampering with lake-manifest.json's bytes
    (as a `lake update` would) must mint a different verifier identity."""
    v = LeanVerifier()
    baseline = v.binary_hash
    original_read_bytes = Path.read_bytes

    def fake_read_bytes(self):
        data = original_read_bytes(self)
        if self.name == "lake-manifest.json":
            return data + b"\n// tampered for test\n"
        return data

    monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)
    assert v.binary_hash != baseline


def test_binary_hash_changes_when_toolchain_bytes_differ(monkeypatch):
    v = LeanVerifier()
    baseline = v.binary_hash
    original_read_bytes = Path.read_bytes

    def fake_read_bytes(self):
        data = original_read_bytes(self)
        if self.name == "lean-toolchain":
            return b"leanprover/lean4:v9.9.9\n"
        return data

    monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)
    assert v.binary_hash != baseline


def test_binary_hash_changes_when_lakefile_bytes_differ(monkeypatch):
    """lakefile.toml's leanOptions + the lean_exe target are part of the verifier's
    contract: editing them must mint a new identity."""
    v = LeanVerifier()
    baseline = v.binary_hash
    original_read_bytes = Path.read_bytes

    def fake_read_bytes(self):
        data = original_read_bytes(self)
        if self.name == "lakefile.toml":
            return data + b"\n# tampered leanOption for test\n"
        return data

    monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)
    assert v.binary_hash != baseline


def test_binary_hash_changes_when_driver_source_bytes_differ(monkeypatch):
    """The compiled audit logic (AxiomAudit.lean) is a trust root, so its bytes
    are pinned into the verifier's identity: any edit mints a new identity and
    drops a prior certification stamp."""
    v = LeanVerifier()
    baseline = v.binary_hash
    original_read_bytes = Path.read_bytes

    def fake_read_bytes(self):
        data = original_read_bytes(self)
        if self.name == "AxiomAudit.lean":
            return data + b"\n-- tampered audit logic\n"
        return data

    monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)
    assert v.binary_hash != baseline


def test_binary_hash_changes_when_leanchecker_pin_bytes_differ(monkeypatch):
    """The kernel re-checker (leanchecker) is THE trust anchor, so its pin
    (`lean4checker.pin.json`) is folded into the verifier's identity: re-pinning
    the checker mints a new identity and drops a prior certification stamp."""
    v = LeanVerifier()
    baseline = v.binary_hash
    original_read_bytes = Path.read_bytes

    def fake_read_bytes(self):
        data = original_read_bytes(self)
        if self.name == "lean4checker.pin.json":
            return data + b"\n"
        return data

    monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)
    assert v.binary_hash != baseline


def test_lean_env_scrubs_secrets_but_keeps_path_home_elan(monkeypatch):
    """I1: the minimal env handed to the untrusted Lean subprocess must carry
    PATH/HOME/ELAN_* (elan needs them) but NOT the parent's secrets."""
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    monkeypatch.setenv("HOME", "/Users/tester")
    monkeypatch.setenv("ELAN_HOME", "/Users/tester/.elan")
    monkeypatch.setenv("ELAN_TOOLCHAIN", "leanprover/lean4:v4.31.0")
    for secret in ("ANTHROPIC_API_KEY", "AWS_SECRET_ACCESS_KEY", "GH_TOKEN",
                   "SOME_API_KEY", "SSH_AUTH_SOCK"):
        monkeypatch.setenv(secret, "SECRET")

    env = LeanVerifier._lean_env()

    assert env["HOME"] == "/Users/tester"
    assert "/Users/tester/.elan/bin" in env["PATH"]  # elan bin ensured on PATH
    assert env["ELAN_HOME"] == "/Users/tester/.elan"
    assert env["ELAN_TOOLCHAIN"] == "leanprover/lean4:v4.31.0"
    for secret in ("ANTHROPIC_API_KEY", "AWS_SECRET_ACCESS_KEY", "GH_TOKEN",
                   "SOME_API_KEY", "SSH_AUTH_SOCK"):
        assert secret not in env


# -- fast, offline: parse_driver_result (the nonce-framed output channel) -----


def _line(nonce: str, payload: str) -> str:
    return f"AXIOM_AUDIT::{nonce}::{payload}"


def test_parse_driver_result_accepts_correct_nonce_line():
    stdout = _line("abc123", '{"declFound":true,"errors":[],"axioms":["propext"]}')
    result = parse_driver_result(stdout, "abc123")
    assert result == {"declFound": True, "errors": [], "axioms": ["propext"]}


def test_parse_driver_result_none_when_no_marker():
    assert parse_driver_result("some unrelated stdout\n", "abc123") is None
    assert parse_driver_result("", "abc123") is None


def test_parse_driver_result_rejects_wrong_nonce():
    """The C2 attack: a source writes a fake driver-result line directly to
    /dev/stdout (bypassing stream isolation) and exits, but cannot know the nonce.
    A line bearing a DIFFERENT nonce must never be accepted -- fail closed."""
    stdout = _line("GUESS", '{"declFound":true,"errors":[],"axioms":[]}')
    assert parse_driver_result(stdout, "the-real-secret-nonce") is None


def test_parse_driver_result_rejects_malformed_json():
    assert parse_driver_result(_line("abc123", "not json at all"), "abc123") is None


def test_parse_driver_result_rejects_non_object_json():
    assert parse_driver_result(_line("abc123", "[1, 2, 3]"), "abc123") is None


def test_parse_compile_diagnostics_detects_error():
    line = ('{"severity":"error","data":"Unknown identifier `x`",'
            '"kind":"lean.unknownIdentifier._namedError"}')
    errors, sorry_hit = parse_compile_diagnostics(line)
    assert errors == ["Unknown identifier `x`"]
    assert sorry_hit is False


def test_parse_compile_diagnostics_detects_sorry_warning():
    line = '{"severity":"warning","data":"declaration uses `sorry`","kind":"hasSorry"}'
    errors, sorry_hit = parse_compile_diagnostics(line)
    assert errors == []
    assert sorry_hit is True


def test_parse_compile_diagnostics_ignores_non_error_non_sorry_warnings():
    line = '{"severity":"warning","data":"unused variable `h`","kind":"linter.unusedVariables"}'
    errors, sorry_hit = parse_compile_diagnostics(line)
    assert errors == []
    assert sorry_hit is False


def test_parse_compile_diagnostics_ignores_noise_and_bad_json():
    stdout = "lake: building\nnot json\n{malformed\n"
    assert parse_compile_diagnostics(stdout) == ([], False)


def test_parse_driver_result_picks_correct_nonce_amid_forged_lines():
    """The forged line (wrong nonce) and noise are ignored; only the genuine
    correct-nonce line is parsed."""
    stdout = "\n".join([
        "lake: some build noise",
        _line("GUESS", '{"declFound":true,"errors":[],"axioms":[]}'),
        "'Empiricist.two' depends on axioms: [propext, Classical.choice, Quot.sound]",
        _line("realnonce", '{"declFound":true,"errors":[],"axioms":["Empiricist.evil"]}'),
    ])
    result = parse_driver_result(stdout, "realnonce")
    assert result == {"declFound": True, "errors": [], "axioms": ["Empiricist.evil"]}

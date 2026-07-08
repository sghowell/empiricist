"""LeanVerifier tests (M8): the KERNEL-re-check trust gate against REAL Lean
4.31.0. The gate is a four-stage pipeline over one compiled olean -- compile
(`--json` diagnostics), KERNEL re-check (`leanchecker`, the trust anchor), axiom
whitelist + statement (the compiled `axiom_audit` driver, importing the same
olean), then PASS. These tests exercise the honest PASS (with recorded statement),
every must-FAIL golden -- including the kernel-unchecked ENVIRONMENT-INJECTION
PoCs (`skipKernelTC`, `addDeclCore (doCheck := false)`, `Environment.replay`) and
the earlier axiom-forgery / command-override vectors -- the FORMALIZED ingestion
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
    "inject_replay", "true_statement",
]


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

    asyncio.run(LeanVerifier()._ensure_driver_async())
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
    assert ev[0].verifier_version == "3.0"
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
def test_scratch_nonce_and_olean_files_cleaned_up_across_pass_fail(verifier):
    """Per-invocation scratch (.lean), nonce, AND compiled olean are all removed in
    finally -- across PASS and every FAIL gate."""
    before_src = set(_MODULE_DIR.glob("Scratch_*"))
    before_olean = set(_OLEAN_DIR.glob("Scratch_*")) if _OLEAN_DIR.exists() else set()
    for source, decl, _ in LEAN_GOLDEN_SUITE:
        verifier.verify(source, decl=decl, timeout_s=120)
    assert set(_MODULE_DIR.glob("Scratch_*")) == before_src
    after_olean = set(_OLEAN_DIR.glob("Scratch_*")) if _OLEAN_DIR.exists() else set()
    assert after_olean == before_olean


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
    assert LeanVerifier.version == "3.0"


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

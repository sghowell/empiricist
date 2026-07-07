"""LeanVerifier tests (M8): the compiled axiom-audit driver contract against
REAL Lean 4.31.0. The trust gate is the `axiom_audit` lean_exe, which elaborates
untrusted source with the real frontend and computes the decl's axiom closure via
compiled `Lean.collectAxioms` (never a re-elaboratable `#print axioms`). These
tests exercise the honest PASS, every must-FAIL golden (including the fatal
`#print axioms` COMMAND-OVERRIDE vectors), the FORMALIZED ingestion path, the
env-scrub exfil regression, and offline `parse_driver_result` nonce tests.

Tests that invoke real lake/lean are marked `slow_lean` and skipped when the
toolchain or the pinned project aren't available. The first `verify()` on a fresh
LeanVerifier builds the driver (incremental `lake build axiom_audit`, ~1-3s cold),
then each audit is ~1-2s once mathlib's oleans are warm.
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
    parse_driver_result,
)
from empiricist.verifiers.lean_goldens import LEAN_GOLDEN_SUITE, certify_lean, lean_suite_hash

_PROJECT_DIR = Path(__file__).resolve().parents[1] / "lean" / "EmpiricistLean"
_MODULE_DIR = _PROJECT_DIR / "EmpiricistLean"

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
    "inject_driver_result",
]


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
def test_sorry_golden_fails_at_the_axioms_gate_via_sorryAx(verifier):
    """`sorry` is a WARNING (`lean` exits 0), so a naive exit-code gate would PASS
    it. The compiled driver's `collectAxioms` reports `sorryAx` as a real axiom
    dependency, caught by the whitelist membership test (gate=axioms)."""
    source, decl, _ = LEAN_GOLDEN_SUITE[1]
    result = verifier.verify(source, decl=decl, timeout_s=120)
    assert result.verdict == Verdict.FAIL, result.details
    assert result.details["gate"] == "axioms"
    assert "sorryAx" in result.details["offending_axioms"]


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

    art = ingest_lean_artifact(ledger, store, source, decl, result, verifier=verifier)
    assert art.kind == "lean"
    assert art.problem == "P5"
    assert art.status == Status.FORMALIZED

    fetched = ledger.get_artifact(art.id)
    assert fetched.status == Status.FORMALIZED

    ev = ledger.evidence_for(art.id)
    assert len(ev) == 1
    assert ev[0].verifier == "lean"
    assert ev[0].verifier_version == "2.0"
    assert ev[0].verdict == Verdict.PASS
    assert ev[0].details["decl"] == decl
    assert ev[0].details["mathlib_commit"]

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
def test_scratch_and_nonce_files_cleaned_up_across_pass_fail(verifier):
    before = set(_MODULE_DIR.glob("Scratch_*"))
    for source, decl, _ in LEAN_GOLDEN_SUITE:
        verifier.verify(source, decl=decl, timeout_s=120)
    after = set(_MODULE_DIR.glob("Scratch_*"))
    assert after == before


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
    assert LeanVerifier.version == "2.0"


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
    """The compiled audit logic (AxiomAudit.lean) is the trust root, so its bytes
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

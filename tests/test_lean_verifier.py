"""LeanVerifier tests (M8 Task 2): the two-gate contract (diagnostics
severity + axiom whitelist audit) against REAL `lake env lean --json`
output, the sorry-trap and native_decide-axiom-audit goldens, the
FORMALIZED scaffold-lemma ingestion path, and offline parser tests pinned
against real captured Lean 4.31.0 JSON-lines output (captured live during
M8 Task 2 against the pinned EmpiricistLean project -- see verifiers/lean.py
for the shapes' provenance).

Tests that invoke real lake/lean are marked `slow_lean` and skipped when the
toolchain or the pinned project aren't available (CI-less boxes, mirroring
`tests/test_sandbox.py`'s `darwin_only` pattern); each takes on the order of
a second once mathlib's oleans are warm (verified: ~1.1-2.3s per call in
this session).
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
    parse_axiom_line,
    parse_diagnostics,
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
@pytest.mark.parametrize(
    "source,decl,expected_pass",
    LEAN_GOLDEN_SUITE,
    ids=["sorry_free_true", "sorry_trap", "native_decide", "type_error"],
)
def test_golden_case_matches_expected_verdict(verifier, source, decl, expected_pass):
    result = verifier.verify(source, decl=decl, timeout_s=120)
    assert (result.verdict == Verdict.PASS) == expected_pass, result.details


@slow_lean
@requires_lake
def test_sorry_golden_fails_at_the_sorry_gate_not_diagnostics(verifier):
    """THE trap golden: sorry is a WARNING (`lake env lean --json` exits 0),
    so a naive exit-code gate would PASS this. Confirm it's caught by the
    sorry gate specifically, not accidentally by the diagnostics gate."""
    source, decl, _ = LEAN_GOLDEN_SUITE[1]
    result = verifier.verify(source, decl=decl, timeout_s=120)
    assert result.verdict == Verdict.FAIL
    assert result.details["gate"] == "sorry"
    assert "sorry" in result.details["warnings"][0]


@slow_lean
@requires_lake
def test_native_decide_golden_fails_axiom_audit(verifier):
    """native_decide's axiom is a per-declaration SYNTHESIZED name (confirmed
    live: `<decl>._native.native_decide.ax_1_1`), not a fixed
    `Lean.ofReduceBool` -- the whitelist membership test catches it anyway."""
    source, decl, _ = LEAN_GOLDEN_SUITE[2]
    result = verifier.verify(source, decl=decl, timeout_s=120)
    assert result.verdict == Verdict.FAIL
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
    assert result.verdict == Verdict.FAIL
    assert result.details["gate"] == "diagnostics"


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
    (`connected_edge_bound`) verifies PASS end-to-end and ingests as the
    harness's first FORMALIZED artifact, with the LeanVerifier evidence row
    attached."""
    source = (_MODULE_DIR / "Basic.lean").read_text()
    decl = "Empiricist.connected_edge_bound"
    result = verifier.verify(source, decl=decl, timeout_s=120)
    assert result.verdict == Verdict.PASS
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
    assert ev[0].verifier_version == "1.0"
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
def test_scratch_files_cleaned_up_across_pass_fail(verifier):
    before = set(_MODULE_DIR.glob("Scratch_*"))
    for source, decl, _ in LEAN_GOLDEN_SUITE:
        verifier.verify(source, decl=decl, timeout_s=120)
    after = set(_MODULE_DIR.glob("Scratch_*"))
    assert after == before


@slow_lean
@requires_lake
def test_scratch_cleanup_on_error_path(monkeypatch, verifier):
    """finally-cleanup must fire even when the body returns ERROR."""
    import empiricist.verifiers.lean as lean_mod

    monkeypatch.setattr(lean_mod, "parse_axiom_line", lambda diags, decl: None)
    before = set(_MODULE_DIR.glob("Scratch_*"))
    source, decl, _ = LEAN_GOLDEN_SUITE[0]
    result = verifier.verify(source, decl=decl, timeout_s=120)
    assert result.verdict == Verdict.ERROR
    after = set(_MODULE_DIR.glob("Scratch_*"))
    assert after == before


def test_ingest_lean_artifact_records_the_given_verifiers_identity(ledger, store):
    """The evidence row's binary_hash must name the EXACT verifier instance
    that produced `result`, not a fresh default-project-dir one (a real gap:
    a caller using a non-default project_dir must not have its evidence
    silently misattributed). No real lake/lean call needed here -- the
    VerifierResult is fabricated directly."""

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
    """Total verify(): a nonexistent project dir must ERROR, never raise --
    doesn't need a real lake/lean toolchain (fails before/at spawn)."""
    bogus = LeanVerifier(project_dir=Path("/nonexistent/not/a/real/empiricist-lean-project"))
    result = bogus.verify("theorem t : True := trivial", decl="t", timeout_s=30)
    assert result.verdict == Verdict.ERROR
    assert "error" in result.details


# -- fast, offline: identity + suite shape -----------------------------------


def test_identity():
    assert LeanVerifier.name == "lean"
    assert LeanVerifier.version == "1.0"


def test_applicable():
    v = LeanVerifier()
    assert v.applicable("lean") is True
    assert v.applicable("construction") is False


def test_lean_golden_suite_has_both_a_pass_and_must_fail_cases():
    """A suite that can't fail certifies nothing (spec §7 mutation-resistance,
    same rationale as P5_GOLDEN_SUITE's _WRONG_TARGET)."""
    assert any(expected is True for _, _, expected in LEAN_GOLDEN_SUITE)
    assert any(expected is False for _, _, expected in LEAN_GOLDEN_SUITE)


def test_binary_hash_changes_when_manifest_bytes_differ(monkeypatch):
    """binary_hash pins the toolchain: tampering with lake-manifest.json's
    bytes (as a `lake update` would) must mint a different verifier identity."""
    v = LeanVerifier()
    baseline = v.binary_hash

    original_read_bytes = Path.read_bytes

    def fake_read_bytes(self):
        data = original_read_bytes(self)
        if self.name == "lake-manifest.json":
            return data + b"\n// tampered for test\n"
        return data

    monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)
    tampered = v.binary_hash
    assert tampered != baseline


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
    tampered = v.binary_hash
    assert tampered != baseline


# -- fast, offline: parsers against REAL captured Lean 4.31.0 output --------
#
# Every line below was captured live (M8 Task 2) via `lake env lean --json`
# against the pinned EmpiricistLean project on this toolchain
# (leanprover/lean4:v4.31.0) -- not fabricated.

_REAL_SORRY_WARNING_LINE = (
    '{"caption":"","data":"declaration uses `sorry`","endPos":{"column":21,"line":3},'
    '"fileName":"EmpiricistLean/Scratch_x.lean","isSilent":false,"keepFullRange":false,'
    '"kind":"hasSorry","pos":{"column":8,"line":3},"severity":"warning"}'
)

_REAL_TYPE_ERROR_LINE = (
    '{"caption":"","data":"Unknown identifier `rfl_this_is_not_a_thing`",'
    '"endPos":{"column":50,"line":3},"fileName":"EmpiricistLean/Scratch_x.lean",'
    '"isSilent":false,"keepFullRange":false,"kind":"lean.unknownIdentifier._namedError",'
    '"pos":{"column":27,"line":3},"severity":"error"}'
)

_REAL_AXIOM_NONE_LINE = (
    '{"caption":"","data":"\'Empiricist.scaffold_true\' does not depend on any axioms",'
    '"endPos":{"column":6,"line":7},"fileName":"EmpiricistLean/Scratch_x.lean",'
    '"isSilent":false,"keepFullRange":false,"kind":"[anonymous]","pos":{"column":0,"line":7},'
    '"severity":"information"}'
)

_REAL_AXIOM_WHITELISTED_LINE = (
    '{"caption":"","data":"\'Empiricist.connected_edge_bound\' depends on axioms: '
    '[propext, Classical.choice, Quot.sound]","endPos":{"column":6,"line":3},'
    '"fileName":"EmpiricistLean/Scratch_x.lean","isSilent":false,"keepFullRange":false,'
    '"kind":"[anonymous]","pos":{"column":0,"line":3},"severity":"information"}'
)

_REAL_AXIOM_NATIVE_DECIDE_LINE = (
    '{"caption":"","data":"\'Empiricist.nd\' depends on axioms: '
    '[Empiricist.nd._native.native_decide.ax_1_1]","endPos":{"column":6,"line":7},'
    '"fileName":"EmpiricistLean/Scratch_x.lean","isSilent":false,"keepFullRange":false,'
    '"kind":"[anonymous]","pos":{"column":0,"line":7},"severity":"information"}'
)

_REAL_AXIOM_SORRY_AX_LINE = (
    '{"caption":"","data":"\'Empiricist.scaffold_true\' depends on axioms: [sorryAx]",'
    '"endPos":{"column":6,"line":7},"fileName":"EmpiricistLean/Scratch_x.lean",'
    '"isSilent":false,"keepFullRange":false,"kind":"[anonymous]","pos":{"column":0,"line":7},'
    '"severity":"information"}'
)


def test_parse_diagnostics_empty_stdout_is_clean():
    """Confirmed live: a clean file's `lake env lean --json` stdout is
    EMPTY (not "[]"), and exit 0 -- exit code is unrelated to this parser."""
    assert parse_diagnostics("") == []


def test_parse_diagnostics_single_line():
    diags = parse_diagnostics(_REAL_SORRY_WARNING_LINE)
    assert len(diags) == 1
    assert diags[0]["severity"] == "warning"
    assert diags[0]["kind"] == "hasSorry"


def test_parse_diagnostics_multiple_lines_and_blank_lines():
    stdout = f"\n{_REAL_SORRY_WARNING_LINE}\n\n{_REAL_AXIOM_SORRY_AX_LINE}\n"
    diags = parse_diagnostics(stdout)
    assert len(diags) == 2
    assert diags[0]["kind"] == "hasSorry"
    assert diags[1]["severity"] == "information"


def test_parse_diagnostics_error_severity():
    diags = parse_diagnostics(_REAL_TYPE_ERROR_LINE)
    assert diags[0]["severity"] == "error"


def test_parse_axiom_line_does_not_depend_on_any_axioms_shape():
    diags = parse_diagnostics(_REAL_AXIOM_NONE_LINE)
    assert parse_axiom_line(diags, "Empiricist.scaffold_true") == []


def test_parse_axiom_line_whitelisted_shape():
    diags = parse_diagnostics(_REAL_AXIOM_WHITELISTED_LINE)
    axioms = parse_axiom_line(diags, "Empiricist.connected_edge_bound")
    assert axioms == ["propext", "Classical.choice", "Quot.sound"]


def test_parse_axiom_line_native_decide_synthesized_axiom_shape():
    diags = parse_diagnostics(_REAL_AXIOM_NATIVE_DECIDE_LINE)
    axioms = parse_axiom_line(diags, "Empiricist.nd")
    assert axioms == ["Empiricist.nd._native.native_decide.ax_1_1"]


def test_parse_axiom_line_sorry_ax_shape():
    diags = parse_diagnostics(_REAL_AXIOM_SORRY_AX_LINE)
    assert parse_axiom_line(diags, "Empiricist.scaffold_true") == ["sorryAx"]


def test_parse_axiom_line_none_when_decl_not_present():
    diags = parse_diagnostics(_REAL_AXIOM_WHITELISTED_LINE)
    assert parse_axiom_line(diags, "Empiricist.some_other_decl") is None


def test_parse_axiom_line_handles_bracketed_empty_list_shape():
    """Defensive: the plan explicitly calls out `depends on axioms: []` as a
    shape to handle even though it wasn't observed for any real decl here
    (mathlib decls always route through the `does not depend` phrasing when
    axiom-free)."""
    line = (
        '{"data":"\'Empiricist.foo\' depends on axioms: []","severity":"information"}'
    )
    diags = parse_diagnostics(line)
    assert parse_axiom_line(diags, "Empiricist.foo") == []

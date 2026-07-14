"""Tests for `formalize/feedback.py`'s `format_feedback` (M18): each
`LeanVerifier` gate (verifiers/lean.py) must map to a concise, actionable
revision message the Formalizer can act on next round."""

from __future__ import annotations

from empiricist.formalize.feedback import format_feedback
from empiricist.ledger.models import Verdict
from empiricist.verifiers.base import VerifierResult


def test_diagnostics_gate_lists_errors():
    result = VerifierResult(
        verdict=Verdict.FAIL,
        details={"gate": "diagnostics", "errors": ["unknown identifier `foo`", "type mismatch"]},
    )
    msg = format_feedback(result)
    assert "Compilation failed" in msg
    assert "unknown identifier `foo`" in msg
    assert "type mismatch" in msg
    assert "truncated" not in msg


def test_diagnostics_gate_caps_and_notes_truncation():
    errors = [f"error {i}" for i in range(20)]
    result = VerifierResult(verdict=Verdict.FAIL, details={"gate": "diagnostics", "errors": errors})
    msg = format_feedback(result)
    for e in errors[:15]:
        assert e in msg
    for e in errors[15:]:
        assert e not in msg
    assert "+5 more errors truncated" in msg


def test_sorry_gate():
    result = VerifierResult(verdict=Verdict.FAIL, details={"gate": "sorry"})
    msg = format_feedback(result)
    assert "sorry" in msg
    assert "every goal must be closed with a real proof" in msg


def test_axioms_gate_lists_offending_and_whitelist():
    result = VerifierResult(
        verdict=Verdict.FAIL,
        details={
            "gate": "axioms",
            "axioms": ["propext", "sorryAx"],
            "offending_axioms": ["sorryAx"],
        },
    )
    msg = format_feedback(result)
    assert "sorryAx" in msg
    assert "propext, Classical.choice, Quot.sound" in msg
    assert "native_decide" in msg


def test_kernel_soundness_gate_includes_leanchecker_output():
    result = VerifierResult(
        verdict=Verdict.FAIL,
        details={
            "gate": "kernel_soundness",
            "leanchecker_output": "declaration type mismatch",
        },
    )
    msg = format_feedback(result)
    assert "kernel re-check REJECTED" in msg
    assert "declaration type mismatch" in msg
    assert "prove it genuinely" in msg


def test_import_trust_gate_lists_untrusted_imports():
    result = VerifierResult(
        verdict=Verdict.FAIL,
        details={"gate": "import_trust", "untrusted_imports": ["/tmp/EmpiricistLean/Poison.olean"]},
    )
    msg = format_feedback(result)
    assert "/tmp/EmpiricistLean/Poison.olean" in msg
    assert "Mathlib.*" in msg
    assert "EmpiricistLean.Basic" in msg


def test_residue_gate_is_generic_retry_message():
    result = VerifierResult(
        verdict=Verdict.FAIL, details={"gate": "residue", "unexpected_files": ["x"]}
    )
    msg = format_feedback(result)
    assert "clean module" in msg


def test_error_verdict():
    result = VerifierResult(
        verdict=Verdict.ERROR,
        details={"error": "lean --json compile subprocess timed out"},
    )
    msg = format_feedback(result)
    assert "Verification errored" in msg
    assert "lean --json compile subprocess timed out" in msg
    assert "self-contained Lean 4 file" in msg


def test_unrecognized_gate_falls_back_to_raw_details():
    result = VerifierResult(
        verdict=Verdict.FAIL, details={"gate": "decl_missing", "decl": "Foo.bar"}
    )
    msg = format_feedback(result)
    assert "decl_missing" in msg
    assert "Foo.bar" in msg

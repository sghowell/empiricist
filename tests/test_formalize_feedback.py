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


def test_diagnostics_gate_surfaces_full_goal_state_for_unsolved_goals():
    """A `?_` hole compiles clean but leaves Lean's own "unsolved goals"
    diagnostic -- the full proof state (hypotheses + `⊢` target) at the hole.
    M18: this must be surfaced IN FULL (never truncated) and clearly labeled
    as the model's remaining goal, not folded into the generic error dump."""
    goal_state = (
        "unsolved goals\ncase left\nn : Nat\nh : n > 0\n⊢ n + 0 = n"
    )
    result = VerifierResult(
        verdict=Verdict.FAIL,
        details={"gate": "diagnostics", "errors": [goal_state]},
    )
    msg = format_feedback(result)
    assert goal_state in msg  # verbatim, not truncated or reworded
    assert "⊢" in msg
    assert "n : Nat" in msg
    assert "h : n > 0" in msg
    assert "REMAINING GOAL" in msg
    assert "more unsolved-goal messages not shown" not in msg  # only one goal: no count-cap notice


def test_diagnostics_gate_mixes_goal_state_and_ordinary_errors():
    goal_state = "unsolved goals\ncase right\nn : Nat\n⊢ n = n"
    ordinary = "unknown identifier `bar`"
    result = VerifierResult(
        verdict=Verdict.FAIL,
        details={"gate": "diagnostics", "errors": [goal_state, ordinary]},
    )
    msg = format_feedback(result)
    assert goal_state in msg
    assert "REMAINING GOAL" in msg
    assert ordinary in msg
    assert "Compilation failed" in msg


def test_diagnostics_gate_never_truncates_a_long_goal_state():
    """Even a goal state far longer than the ordinary per-message handling
    would tolerate must survive verbatim -- cutting hypotheses mid-list would
    show the model a nonsensical, possibly self-contradictory partial state."""
    long_hyps = "\n".join(f"h{i} : n{i} = n{i} + {i}" for i in range(200))
    goal_state = f"unsolved goals\nn : Nat\n{long_hyps}\n⊢ n = n"
    result = VerifierResult(
        verdict=Verdict.FAIL,
        details={"gate": "diagnostics", "errors": [goal_state]},
    )
    msg = format_feedback(result)
    assert goal_state in msg
    assert "h199 : n199 = n199 + 199" in msg  # the tail of the hypothesis list survived


def test_diagnostics_gate_caps_goal_state_count_not_content():
    goals = [f"unsolved goals\ncase c{i}\nn : Nat\n⊢ n = {i}" for i in range(12)]
    result = VerifierResult(verdict=Verdict.FAIL, details={"gate": "diagnostics", "errors": goals})
    msg = format_feedback(result)
    for g in goals[:8]:
        assert g in msg
    for g in goals[8:]:
        assert g not in msg
    assert "+4 more unsolved-goal messages" in msg


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

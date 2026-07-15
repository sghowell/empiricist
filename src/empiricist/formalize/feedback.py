"""Turn a FAIL/ERROR `VerifierResult` from `LeanVerifier.verify()` into a
concise, actionable revision message for the Formalizer's next round.

Maps each gate `verifiers/lean.py` can report on FAIL (`diagnostics`, `sorry`,
`axioms`, `kernel_soundness`, `import_trust`, `residue`) plus the top-level
Verdict.ERROR case (subprocess timeout / malformed module). An unrecognized
gate falls back to a generic dump of `details` rather than silently dropping
information -- the verifier's gate set can grow without this module going
stale-silent.

M18 goal-state feedback (hole-driven proof development): within the
`diagnostics` gate, a message can be Lean's own "unsolved goals" diagnostic --
emitted when the module compiles but leaves a `?_` metavariable (a HOLE, not
`sorry` -- that is a *different* gate, see below) unresolved. That message
IS the Lean proof state (hypotheses + the `⊢` turnstile target) at the hole,
which is exactly what a model developing a hard proof incrementally needs to
see to fill it in on the next round. Those messages are surfaced IN FULL,
never truncated -- cutting a goal state would show the model contradictory
hypotheses cut mid-word, actively harmful. Only the *count* of such messages
is capped (`_GOAL_CAP`); ordinary (non-goal) diagnostics keep the prior
message-count cap (`_ERROR_CAP`).
"""

from __future__ import annotations

from empiricist.ledger.models import Verdict
from empiricist.verifiers.base import VerifierResult

_ERROR_CAP = 15
_GOAL_CAP = 8  # max number of distinct unsolved-goal messages shown (each IN FULL)
_ALLOWED_AXIOMS = "propext, Classical.choice, Quot.sound"

# Lean's own turnstile, printed in every "unsolved goals"/goal-state message
# between the hypothesis list and the target.
_TURNSTILE = "⊢"  # "⊢"


def _is_goal_state_message(msg: str) -> bool:
    """True iff `msg` is (or contains) a Lean goal-state dump -- an
    "unsolved goals" diagnostic (what a `?_` hole produces once the rest of
    the module elaborates cleanly) or any message carrying the `⊢` turnstile.
    Either signal alone is sufficient; real goal-state messages carry both."""
    return "unsolved goals" in msg or _TURNSTILE in msg


def format_feedback(result: VerifierResult) -> str:
    if result.verdict is Verdict.ERROR:
        error = result.details.get("error", "unknown error")
        return (
            f"Verification errored: {error}. (This is usually a timeout or a "
            "malformed module -- ensure the module is a single self-contained "
            "Lean 4 file.)"
        )

    gate = result.details.get("gate")

    if gate == "diagnostics":
        errors = list(result.details.get("errors") or [])
        goal_msgs = [e for e in errors if _is_goal_state_message(e)]
        other_msgs = [e for e in errors if not _is_goal_state_message(e)]

        sections: list[str] = []
        if goal_msgs:
            shown_goals = goal_msgs[:_GOAL_CAP]
            # Each goal state is surfaced VERBATIM and in full -- no per-message
            # truncation -- separated so multiple holes' states don't run together.
            goal_body = "\n\n".join(shown_goals)
            goal_section = (
                "REMAINING GOAL(S) at your holes (fill each `?_` with a real "
                f"proof; nothing here is truncated):\n{goal_body}"
            )
            if len(goal_msgs) > _GOAL_CAP:
                goal_section += (
                    f"\n(+{len(goal_msgs) - _GOAL_CAP} more unsolved-goal "
                    "messages not shown -- resolve the ones above first)"
                )
            sections.append(goal_section)
        if other_msgs:
            shown_other = other_msgs[:_ERROR_CAP]
            other_body = "\n".join(f"- {e}" for e in shown_other)
            other_section = f"Compilation failed. Fix these Lean errors:\n{other_body}"
            if len(other_msgs) > _ERROR_CAP:
                other_section += (
                    f"\n(+{len(other_msgs) - _ERROR_CAP} more errors truncated)"
                )
            sections.append(other_section)
        if not sections:
            # `errors` was present but empty -- fail-safe, should not happen
            # since verify() only sets this gate when `errors` is truthy.
            return "Compilation failed with no diagnostic detail available."
        return "\n\n".join(sections)

    if gate == "sorry":
        return (
            "Proof contains `sorry`/`admit`/incomplete tactic -- every goal "
            "must be closed with a real proof."
        )

    if gate == "axioms":
        offending = ", ".join(result.details.get("offending_axioms") or [])
        return (
            f"Proof depends on forbidden axioms: {offending}. Allowed: "
            f"{_ALLOWED_AXIOMS}. Avoid native_decide / sorryAx / custom axioms."
        )

    if gate == "kernel_soundness":
        checker_out = result.details.get("leanchecker_output", "")
        return (
            f"The kernel re-check REJECTED the proof (leanchecker): "
            f"{checker_out}. A declaration's type does not actually hold -- no "
            "addDeclCore/skipKernelTC tricks; prove it genuinely."
        )

    if gate == "import_trust":
        untrusted = ", ".join(result.details.get("untrusted_imports") or [])
        return (
            f"Imports not allowed: {untrusted}. Import ONLY pinned mathlib "
            "(Mathlib.*) and EmpiricistLean.Basic."
        )

    if gate == "residue":
        return (
            "Unexpected files present -- internal error; retry with a clean "
            "module."
        )

    # Unrecognized gate (e.g. a future addition to verifiers/lean.py) -- never
    # silently drop information.
    return f"Verification failed (gate={gate!r}): {result.details}"

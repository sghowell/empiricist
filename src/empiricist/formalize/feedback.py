"""Turn a FAIL/ERROR `VerifierResult` from `LeanVerifier.verify()` into a
concise, actionable revision message for the Formalizer's next round.

Maps each gate `verifiers/lean.py` can report on FAIL (`diagnostics`, `sorry`,
`axioms`, `kernel_soundness`, `import_trust`, `residue`) plus the top-level
Verdict.ERROR case (subprocess timeout / malformed module). An unrecognized
gate falls back to a generic dump of `details` rather than silently dropping
information -- the verifier's gate set can grow without this module going
stale-silent.
"""

from __future__ import annotations

from empiricist.ledger.models import Verdict
from empiricist.verifiers.base import VerifierResult

_ERROR_CAP = 15
_ALLOWED_AXIOMS = "propext, Classical.choice, Quot.sound"


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
        shown = errors[:_ERROR_CAP]
        body = "\n".join(f"- {e}" for e in shown)
        msg = f"Compilation failed. Fix these Lean errors:\n{body}"
        if len(errors) > _ERROR_CAP:
            msg += f"\n(+{len(errors) - _ERROR_CAP} more errors truncated)"
        return msg

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

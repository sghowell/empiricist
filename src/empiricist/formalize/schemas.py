"""The Formalizer's structured output (M18): a complete, self-contained Lean 4
module plus the fully-qualified declaration name the harness axiom-audits.

Same discipline as `llm/schemas.py`: schema-valid guarantees SHAPE only, never
mathematical truth or even that the module compiles -- `verifiers/lean.py`'s
LeanVerifier decides that. `notes` is provenance for a human/orchestrator
reviewing approach history; the gate never reads it.
"""

from __future__ import annotations

from empiricist.llm.schemas import _Closed


class LeanModuleOut(_Closed):
    module_source: str   # the COMPLETE Lean 4 file (imports + statement + proof)
    decl: str             # fully-qualified name of the theorem to axiom-audit
    notes: str = ""        # optional approach notes -- ignored by the gate

"""The Fable->Lean FORMALIZE loop (M18): the Formalizer proposes a complete
Lean 4 module as structured JSON, the harness runs it through the hardened
`LeanVerifier` gate (verifiers/lean.py), and a FAIL/ERROR becomes a concise,
actionable revision message fed back to the model for the next round. The
model never gets a shell (spec's F1 trust boundary): output reaches the
ledger ONLY through a PASS `verify()` -> `ingest_lean_artifact` (which itself
refuses non-PASS), never by the loop writing or editing Lean itself.
"""

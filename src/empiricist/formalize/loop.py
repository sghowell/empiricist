"""FormalizeLoop (M18, spec "the model never gets a shell"): the Fable ->
Lean formalization cycle.

One round = one Formalizer prompt (goal + context, or the prior attempt +
actionable feedback) -> `client.complete` -> parse the `LeanModuleOut`
(never trusted) -> `LeanVerifier.verify()` (the real trust gate) -> on PASS,
`ingest_lean_artifact` (which itself refuses anything but PASS); on FAIL/ERROR,
`format_feedback` turns the result into the next round's revision prompt.

The loop NEVER writes or edits Lean itself -- it only routes the model's own
output through the verifier. Model output reaches the ledger ONLY via a PASS
`verify()` -> `ingest_lean_artifact` call (the F1 trust boundary); a FAIL never
ingests. Every Formalizer call is billed to the ledger (`ledger=` passed to
`client.complete`), matching the SearchLoop/ConjectureLoop discipline.

Because each `client.complete` call is a FRESH model context (F2: no
cross-call session state, spec §5.4/llm/client.py), `build_prompt` re-states
the goal/context on every round, not just round 1 -- the model has no memory
of earlier rounds unless the prompt carries it forward explicitly.

**THE ASYNCIO TRAP:** `LeanVerifier.verify()` wraps `asyncio.run` and REFUSES
to run inside a running event loop (returns `Verdict.ERROR` with an asyncio
message rather than raising -- see `verifiers/lean.py`'s `verify()` docstring).
Since `FormalizeLoop.run` is itself a coroutine, calling `verify()` directly
would always hit that refusal. It MUST be dispatched to a worker thread via
`asyncio.to_thread`, which is exactly what
`verify_and_ingest_lean_artifact` does while keeping SQLite work on this
event-loop thread.

Faithfulness of the STATEMENT (does the Lean theorem actually say what the
`FormalizeTask.goal` claims?) is NOT checked here -- the loop only certifies
that *some* statement compiles, is kernel-sound, and has a whitelisted axiom
set. `FormalizeReport.recorded_statement` surfaces the verifier-resolved
statement text for exactly this: the calling orchestrator/human reviews it
against the goal before treating the FORMALIZED artifact as faithful (the
same discipline M10-M15 used for their own claims).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from empiricist.formalize.feedback import format_feedback
from empiricist.formalize.schemas import LeanModuleOut
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Verdict
from empiricist.llm.client import LLMClient
from empiricist.llm.roles import ROLES
from empiricist.store import Store
from empiricist.verifiers.lean import (
    DEFAULT_LEAN_PROBLEM_VERSION,
    verify_and_ingest_lean_artifact,
)
from empiricist.verifiers.lean_goldens import lean_suite_hash

_NO_ARTIFACT_FEEDBACK = (
    "No usable output was produced. Emit exactly one JSON object matching the "
    'LeanModuleOut schema: {"module_source": "<complete Lean 4 file>", '
    '"decl": "<fully-qualified theorem name>", "notes": "<optional>"}.'
)


@dataclass(frozen=True)
class FormalizeTask:
    name: str    # short id for the goal (used in run_id / provenance)
    goal: str    # natural-language: WHAT to prove + the intended (informal) statement
    context: str  # available lemmas/defs, import guidance, prior-art, faithfulness constraints
    problem: str = "P5"
    problem_version: str = DEFAULT_LEAN_PROBLEM_VERSION


@dataclass(frozen=True)
class FormalizeReport:
    ok: bool
    rounds: int
    artifact_id: str | None
    final_verdict: str            # "PASS"/"FAIL"/"ERROR"/"NO_ARTIFACT"/"INVALID_JSON"
    final_gate: str | None
    recorded_statement: str | None      # PASS details["statement"] -- review for faithfulness
    recorded_axioms: tuple | None
    decl: str | None
    module_source: str | None
    history: tuple          # per round: (verdict, gate, short feedback)


@dataclass(frozen=True)
class _Round:
    """Internal per-round record. Carries `module_source` (unlike the public
    report's history tuples) so `build_prompt` can show the model its own
    prior attempt verbatim -- necessary because each model call is a fresh
    context with no memory of earlier rounds (F2)."""

    verdict: str
    gate: str | None
    feedback: str
    module_source: str | None = None


class FormalizeLoop:
    def __init__(
        self,
        client: LLMClient,
        ledger: Ledger,
        store: Store,
        verifier: Any,   # LeanVerifier-shaped: .verify(module_source, *, decl, timeout_s=...)
        *,
        max_rounds: int = 12,
    ) -> None:
        if max_rounds < 1:
            raise ValueError("max_rounds must be >= 1")
        self._client = client
        self._ledger = ledger
        self._store = store
        self._verifier = verifier
        self._max_rounds = max_rounds

    def build_prompt(self, task: FormalizeTask, history: list) -> str:
        header = f"Goal: {task.goal}\n\nContext: {task.context}\n\n"
        if not history:
            return header + (
                "Emit a LeanModuleOut: a complete Lean 4 file proving the "
                "statement, with the theorem name in `decl`. Import only "
                "pinned mathlib (Mathlib.*) and EmpiricistLean.Basic. No "
                "sorry, no native_decide. The statement must FAITHFULLY "
                "encode the goal. For a hard proof, you may develop it "
                "incrementally by leaving subgoals as `?_` holes -- the "
                "harness will report the exact Lean goal state at each "
                "unsolved `?_` so you can fill them one at a time across "
                "rounds. Your FINAL accepted proof must have NO holes: a `?_` "
                "or any unsolved goal fails verification."
            )
        last = history[-1]
        prior = (
            f"Your previous attempt:\n```lean\n{last.module_source}\n```\n\n"
            if last.module_source
            else ""
        )
        return header + (
            f"{prior}Revise the module to fix the following. Keep the "
            f"statement faithful.\n{last.feedback}"
        )

    async def run(self, task: FormalizeTask) -> FormalizeReport:
        # Fail before the first (potentially paid) formalizer call if no result
        # could cross the FORMALIZED trust boundary.  The ingestion helper
        # repeats this exact check immediately before verification/commit.
        self._ledger.require_certification(
            self._verifier.name,
            self._verifier.version,
            self._verifier.binary_hash,
            lean_suite_hash(),
        )

        # A task name is a readable provenance component, not a globally unique
        # execution identity. Re-running/resuming the same task must not collide
        # with prior provider receipts, while every round's verifier evidence
        # must still point to the exact receipt that produced its source.
        run_nonce = uuid.uuid4().hex[:8]

        history: list[_Round] = []
        last_decl: str | None = None
        last_module_source: str | None = None

        for round_num in range(1, self._max_rounds + 1):
            rid = f"formalize-{task.name}-{run_nonce}-r{round_num}"
            prompt = self.build_prompt(task, history)
            result = await self._client.complete(
                ROLES["formalizer"], prompt, schema=LeanModuleOut,
                ledger=self._ledger, run_id=rid,
            )

            if result is None or not result.has_artifact:
                history.append(_Round(
                    verdict="NO_ARTIFACT", gate=None,
                    feedback=_NO_ARTIFACT_FEEDBACK,
                ))
                continue

            try:
                out = LeanModuleOut.model_validate(result.parsed)
            except ValidationError as exc:
                history.append(_Round(
                    verdict="INVALID_JSON", gate=None,
                    feedback=(
                        f"Output did not match the LeanModuleOut schema: {exc}. "
                        "Re-emit a single closed JSON object with fields "
                        "module_source, decl, and optional notes."
                    ),
                ))
                continue

            last_decl = out.decl
            last_module_source = out.module_source

            # The helper dispatches only Lean itself to a worker; certification
            # lookup and atomic ledger writes remain on this owning thread.
            vr, art = await verify_and_ingest_lean_artifact(
                self._ledger,
                self._store,
                out.module_source,
                out.decl,
                verifier=self._verifier,
                problem=task.problem,
                problem_version=task.problem_version,
                run_id=rid,
            )

            if vr.verdict is Verdict.PASS:
                if art is None:
                    raise RuntimeError("Lean verifier returned PASS without an artifact")
                history.append(_Round(
                    verdict="PASS", gate=None, feedback="",
                    module_source=out.module_source,
                ))
                return FormalizeReport(
                    ok=True, rounds=round_num, artifact_id=art.id,
                    final_verdict="PASS", final_gate=None,
                    recorded_statement=vr.details.get("statement"),
                    recorded_axioms=tuple(vr.details.get("axioms") or ()),
                    decl=out.decl, module_source=out.module_source,
                    history=tuple((r.verdict, r.gate, r.feedback) for r in history),
                )

            gate = vr.details.get("gate")
            history.append(_Round(
                verdict=vr.verdict.value, gate=gate,
                feedback=format_feedback(vr), module_source=out.module_source,
            ))

        last = history[-1]
        return FormalizeReport(
            ok=False, rounds=self._max_rounds, artifact_id=None,
            final_verdict=last.verdict, final_gate=last.gate,
            recorded_statement=None, recorded_axioms=None,
            decl=last_decl, module_source=last_module_source,
            history=tuple((r.verdict, r.gate, r.feedback) for r in history),
        )

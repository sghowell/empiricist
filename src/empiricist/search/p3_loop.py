"""P3SearchLoop (M20a Task 3): the iterative propose -> screen -> verify ->
ingest/feedback cycle for linear-optical Bell-measurement schemes. Mirrors
`formalize/loop.py`'s `FormalizeLoop` shape exactly (propose -> gate ->
structured feedback -> revise, early stop on target achievement, the model
never gets a shell).

One round = one Searcher prompt (goal + context, or the accumulated feedback
+ best-so-far) -> `client.complete` -> the raw scheme dict (never trusted) ->
`screen_scheme` (the millisecond `ScreenReject` gate, `search/p3_screen.py`)
-> `verify_scheme_agreed` (the real trust gate: two-engine agreement,
`domain/p3/verify.py`) -> on PASS, `ingest_scheme_artifact` (which itself
refuses anything but PASS); on FAIL/INVALID, concrete feedback (the achieved
success vector, p_min/p_avg, leakage, or the screen-reject reason) drives the
next round's revision prompt.

Verdict-to-round-outcome mapping (F3 discipline; see `domain/p3/verify.py`'s
own docstring): PASS ends the loop successfully. FAIL is an honest miss --
feed the achieved vector back and keep going, tracking the best scheme seen
so far by the task's target metric. INVALID is screen-class (a malformed
scheme or a malformed claim, e.g. a non-finite leakage budget) -- skip +
feedback, never an alarm. ERROR is a two-engine DISAGREEMENT or an engine
raise on a validated scheme -- a stop-the-world alarm, never retried: the
loop returns IMMEDIATELY with `f3_alarm=True` and the caller must stop the
campaign. `ScreenReject` (raised by `screen_scheme` before verification is
even attempted -- e.g. an oversize mesh, or a `BellSchemeOut` schema
violation) is the same "skip + feedback" class as INVALID, but recorded as
its own "SCREENED" outcome so the report distinguishes "the model's JSON
didn't even convert" from "it converted but failed physics".

**The role is resolved lazily, not at construction/import time.** Binding
`P3SearchLoop` to `ROLES["p3_searcher"]` eagerly (at `__init__` or import
time) would make every test -- and every import of this module -- depend on
`llm/roles.py` carrying that entry (it landed in M20a Task 4). Instead,
`P3SearchLoop.__init__` accepts an optional `role` parameter defaulting to
`None`; `run()` resolves `ROLES["p3_searcher"]` lazily, only at the point it
actually needs to call `client.complete` (i.e. never in tests that inject a
stub role). Tests inject a duck-typed stand-in for `llm.roles.Role` (only
`.name` matters to `FakeLLMClient`); real campaigns simply omit `role=` and
get `ROLES["p3_searcher"]` for free.

Because each `client.complete` call is a FRESH model context (F2: no
cross-call session state, spec §5.4/llm/client.py), `build_prompt` re-states
the goal/context on every round, carrying forward the LAST round's outcome +
achieved vector and the best-so-far scheme's summary once one exists --
exactly the way `FormalizeLoop.build_prompt` carries forward the last
verifier feedback + prior module source.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any

from empiricist.domain.p3.ingest import ingest_scheme_artifact
from empiricist.domain.p3.verify import verify_scheme_agreed
from empiricist.ledger.db import Ledger
from empiricist.llm.client import LLMClient
from empiricist.llm.roles import ROLES, Role
from empiricist.llm.schemas import BellSchemeOut
from empiricist.search.p3_screen import screen_scheme
from empiricist.search.schemas import ScreenReject
from empiricist.store import Store

_NO_ARTIFACT_FEEDBACK = (
    "No usable output was produced. Emit exactly one JSON object matching the "
    "bell_scheme schema: n_modes, n_ancilla_photons, ancilla (a Fock "
    "superposition on modes 4.. as a list of {pattern, re, im} terms), mesh "
    "(a list of {kind: 'bs'|'phase', i, j, theta, phi} elements), and your "
    "claimed_p_min/claimed_p_avg/claimed_max_leakage."
)

_PROMPT_INSTRUCTIONS = (
    "Emit exactly one JSON object matching the bell_scheme schema: n_modes, "
    "n_ancilla_photons, an ancilla Fock superposition on modes 4.. (list of "
    "{pattern, re, im} terms; [] means no ancilla), a mesh of bs(i, j, theta, "
    "phi) / phase(i, alpha) elements, and your claimed_p_min/claimed_p_avg/"
    "claimed_max_leakage. Dual-rail encoding: qubit A on rails 0,1; qubit B "
    "on rails 2,3."
)


@dataclass(frozen=True)
class P3SearchTask:
    # short id for the goal (a run_id/provenance component). Need NOT be
    # globally fresh: run() mints a per-invocation nonce into every run_id,
    # so re-running the same task never collides on runs rows.
    name: str
    goal: str           # natural-language: WHAT to find, e.g. "a k=0 scheme with p_avg >= 1/2"
    context: str         # domain context block for the prompt (physics background, conventions)
    target_p_min: float | None = None    # claim checked against verify_scheme_agreed
    target_p_avg: float | None = None    # claim checked against verify_scheme_agreed
    max_leakage: float = 0.0             # the declared leakage budget the claim is checked against


@dataclass(frozen=True)
class P3SearchReport:
    ok: bool
    rounds: int
    artifact_id: str | None
    best: dict | None            # best raw scheme JSON seen so far, by the target metric
    best_summary: dict | None    # its success_by_state + p_min + p_avg + leakage
    f3_alarm: bool                # True iff verify_scheme_agreed returned ERROR (stop the world)
    history: list[tuple[str, str]]  # (outcome, detail) per round; outcome in {PASS, FAIL,
    # INVALID, SCREENED, NO_ARTIFACT, ERROR}


@dataclass(frozen=True)
class _Round:
    """Internal per-round record (mirrors `formalize/loop.py`'s `_Round`)."""

    outcome: str
    detail: str


class P3SearchLoop:
    def __init__(
        self,
        client: LLMClient,
        ledger: Ledger,
        store: Store,
        *,
        max_rounds: int = 12,
        role: Role | None = None,
    ) -> None:
        if max_rounds < 1:
            raise ValueError("max_rounds must be >= 1")
        self._client = client
        self._ledger = ledger
        self._store = store
        self._max_rounds = max_rounds
        self._role = role

    def build_prompt(
        self,
        task: P3SearchTask,
        history: list[_Round],
        best_summary: dict | None,
    ) -> str:
        header = f"{task.goal}\n\n{task.context}\n\n"
        if not history:
            return header + _PROMPT_INSTRUCTIONS
        last = history[-1]
        feedback = (
            f"Your previous round outcome was {last.outcome}.\n{last.detail}\n\n"
        )
        best_block = (
            f"Best scheme so far (achieved, has not yet met the target):\n{best_summary}\n\n"
            if best_summary is not None
            else ""
        )
        return header + feedback + best_block + (
            "Revise your scheme -- reason about which detection patterns "
            "distinguish which Bell states before emitting -- and re-emit a "
            "complete bell_scheme JSON object."
        )

    async def run(self, task: P3SearchTask) -> P3SearchReport:
        # Lazy resolution (module docstring): resolved here, not at __init__/
        # import time. Tests inject `role=` and never touch ROLES.
        role = self._role if self._role is not None else ROLES["p3_searcher"]

        # Fresh per-run() nonce (the documented formalize-loop incident: P3
        # campaigns are overnight/killable, and a re-launched run() with the
        # same task.name must never collide with the previous invocation's
        # runs rows -- run_id is UNIQUE in the ledger).
        run_nonce = uuid.uuid4().hex[:8]

        target_metric = "p_min" if task.target_p_min is not None else "p_avg"

        history: list[_Round] = []
        best: dict | None = None
        best_summary: dict[str, Any] | None = None
        best_metric_value: float | None = None

        for round_num in range(1, self._max_rounds + 1):
            rid = f"p3search-{task.name}-{run_nonce}-r{round_num}"
            prompt = self.build_prompt(task, history, best_summary)
            result = await self._client.complete(
                role, prompt, schema=BellSchemeOut,
                ledger=self._ledger, run_id=rid,
            )

            if result is None or not result.has_artifact:
                history.append(_Round("NO_ARTIFACT", _NO_ARTIFACT_FEEDBACK))
                continue

            raw = result.parsed

            try:
                scheme = screen_scheme(raw)
            except ScreenReject as exc:
                history.append(_Round("SCREENED", str(exc)))
                continue

            # Pure, thread-safe function -- dispatched to a worker thread so
            # the event loop stays responsive if run() is ever multiplexed
            # (matches formalize/loop.py's asyncio.to_thread convention).
            r = await asyncio.to_thread(
                verify_scheme_agreed,
                scheme,
                claimed_p_min=task.target_p_min,
                claimed_p_avg=task.target_p_avg,
                claimed_max_leakage=task.max_leakage,
            )

            if r.verdict == "PASS":
                art = ingest_scheme_artifact(
                    self._ledger, self._store, scheme_json=raw, result=r,
                    title=f"P3 scheme: {task.goal[:80]}",
                    run_id=rid,
                    # the CHECKED claim (the task targets handed to
                    # verify_scheme_agreed above, NOT the scheme dict's own
                    # claimed_* fields) -- recorded with the evidence because
                    # the certificate is claim + achievement
                    claimed_p_min=task.target_p_min,
                    claimed_p_avg=task.target_p_avg,
                    claimed_max_leakage=task.max_leakage,
                )
                history.append(_Round("PASS", r.detail))
                return P3SearchReport(
                    ok=True, rounds=round_num, artifact_id=art.id,
                    best=raw,
                    best_summary={
                        "success_by_state": dict(r.report.success_by_state),
                        "p_min": r.report.p_min,
                        "p_avg": r.report.p_avg,
                        "leakage": r.leakage,
                    },
                    f3_alarm=False,
                    history=[(rr.outcome, rr.detail) for rr in history],
                )

            if r.verdict == "FAIL":
                metric_value = r.report.p_min if target_metric == "p_min" else r.report.p_avg
                if best_metric_value is None or metric_value > best_metric_value:
                    best_metric_value = metric_value
                    best = raw
                    best_summary = {
                        "success_by_state": dict(r.report.success_by_state),
                        "p_min": r.report.p_min,
                        "p_avg": r.report.p_avg,
                        "leakage": r.leakage,
                    }
                # Raw floats everywhere, deliberately: r.detail quotes the
                # exact achieved values, and a rounded summary next to it can
                # self-contradict on a near-miss ("p_avg 0.7499999... <
                # claimed 0.75. Achieved ... p_avg=0.75"). Self-consistency
                # beats prettiness; the model handles full precision.
                feedback = (
                    f"FAIL: {r.detail}. Achieved success_by_state="
                    f"{dict(r.report.success_by_state)}, p_min={r.report.p_min}, "
                    f"p_avg={r.report.p_avg}, leakage={r.leakage}."
                )
                history.append(_Round("FAIL", feedback))
                continue

            if r.verdict == "INVALID":
                # Screen-class (module docstring): a malformed scheme or claim
                # that got past screen_scheme but failed verify's own
                # pre-checks. Skip + feedback, never an alarm.
                history.append(_Round("INVALID", r.detail))
                continue

            # r.verdict == "ERROR": two-engine disagreement or an engine raise
            # on a validated scheme -- F3 stop-the-world alarm. Never retried;
            # the caller stops the world.
            history.append(_Round("ERROR", r.detail))
            return P3SearchReport(
                ok=False, rounds=round_num, artifact_id=None,
                best=best, best_summary=best_summary, f3_alarm=True,
                history=[(rr.outcome, rr.detail) for rr in history],
            )

        return P3SearchReport(
            ok=False, rounds=self._max_rounds, artifact_id=None,
            best=best, best_summary=best_summary, f3_alarm=False,
            history=[(rr.outcome, rr.detail) for rr in history],
        )

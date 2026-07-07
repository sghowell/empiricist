"""LLMClient implementations.

ClaudeCodeClient is the default transport: it builds a `claude -p` argv (cost
recipe: replaced system prompt + dropped setting-sources; tools disabled; JSON
output; per-role effort), runs it THROUGH executor.runner.execute() so the model
call is a provenance-recorded, resource-bounded subprocess (the "one audited
path"), parses the envelope, and — if a ledger is given — records a single
complete runs row with full token/cost accounting (execute() itself is run with
ledger=None so there is exactly one row, the richer one).

The model call is the sole legitimate network user, so it runs sandbox=NONE with
env_passthrough=True (the `claude` cmux wrapper needs the real HOME/PATH/keychain
to authenticate — verified: a scrubbed env yields "Not logged in"). The "model
never gets a shell" guarantee comes from `--tools ""`, not the sandbox. claude is
a TRUSTED transport binary; the untrusted thing is the model's *output*, which is
returned as JSON and only ever executed later as harness-verified code.

FakeLLMClient returns scripted results for offline/deterministic downstream tests.
AnthropicAPIClient is a documented metered-billing alternative (stub in v0).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import sqlite3
import uuid
from typing import Any, Protocol

from pydantic import BaseModel

from empiricist.executor.runner import (
    SPAWN_FAILED_EXIT_CODE,
    DuplicateRunError,
    ExecSpec,
    execute,
)
from empiricist.executor.sandbox import SandboxMode
from empiricist.ledger.db import Ledger, RunAlreadyFinishedError
from empiricist.ledger.models import Run, now_iso
from empiricist.llm.models import LLMResult
from empiricist.llm.parse import LLMParseError, parse_envelope
from empiricist.llm.roles import Role
from empiricist.llm.schemas import json_schema_for


class LLMClient(Protocol):
    async def complete(
        self, role: Role, prompt: str, *, session_id: str | None = None,
        system_prompt: str | None = None,
        schema: type[BaseModel] | None = None,
        run_id: str | None = None, ledger: Ledger | None = None,
    ) -> LLMResult | None: ...

    async def complete_many(
        self, role: Role, prompts: list[str], *,
        schema: type[BaseModel] | None = None, ledger: Ledger | None = None,
    ) -> list[LLMResult]: ...


class ClaudeCodeClient:
    def __init__(
        self, *, claude_bin: list[str] | None = None,
        max_concurrency: int = 8, timeout_s: float = 900.0,
        capture_cap: int = 8 * 1024 * 1024,   # model envelopes can be large
    ) -> None:
        self._bin = list(claude_bin) if claude_bin else ["claude"]
        self._max_concurrency = max_concurrency
        # The semaphore is bound to whatever event loop first contends it, so it
        # cannot be shared across asyncio.run() calls; create it lazily per running
        # loop (a client instance is legitimately reused across campaigns/loops).
        self._sem: asyncio.Semaphore | None = None
        self._sem_loop: asyncio.AbstractEventLoop | None = None
        self._timeout_s = timeout_s
        self._capture_cap = capture_cap

    def _sem_for_loop(self) -> asyncio.Semaphore:
        loop = asyncio.get_running_loop()
        if self._sem is None or self._sem_loop is not loop:
            self._sem = asyncio.Semaphore(self._max_concurrency)
            self._sem_loop = loop
        return self._sem

    def build_argv(
        self, role: Role, prompt: str, *, session_id: str,
        system_prompt: str, schema: dict[str, Any] | None,
    ) -> list[str]:
        argv = [
            *self._bin,
            "-p", prompt,
            "--model", role.model,
            "--system-prompt", system_prompt,   # cost recipe: replace default
            "--setting-sources", "",            # cost recipe: drop CLAUDE.md/settings
            "--tools", "",                       # model gets no tools -> no shell
            "--effort", role.effort.value,
            "--output-format", "json",
            "--session-id", session_id,
        ]
        if schema is not None:
            argv += ["--json-schema", json.dumps(schema)]
        return argv

    async def complete(
        self, role: Role, prompt: str, *, session_id: str | None = None,
        system_prompt: str | None = None,
        schema: type[BaseModel] | None = None,
        run_id: str | None = None, ledger: Ledger | None = None,
    ) -> LLMResult | None:
        cli_session_id = str(uuid.uuid4())   # valid UUID (claude requires it) + F2 fresh context
        sys_prompt = system_prompt if system_prompt is not None else role.system_prompt
        schema_dict = json_schema_for(schema) if schema is not None else None
        argv = self.build_argv(
            role, prompt, session_id=cli_session_id, system_prompt=sys_prompt,
            schema=schema_dict,
        )
        started = now_iso()
        rid = run_id or f"sample-{cli_session_id}"
        # Open the runs row BEFORE the call so an in-flight harness crash leaves an
        # orphan row (reconcile_orphans closes it) rather than losing the call
        # silently. execute() runs with ledger=None so there is exactly one row —
        # this richer one, with the token/cost accounting the executor cannot see.
        if ledger is not None:
            try:
                ledger.start_run(Run(
                    run_id=rid, move="SAMPLE", role=role.name, model=role.model,
                    started=started,
                ))
            except sqlite3.IntegrityError as e:
                raise DuplicateRunError(rid) from e
        try:
            async with self._sem_for_loop():
                res = await execute(
                    ExecSpec(
                        argv=argv, move="SAMPLE", role=role.name,
                        sandbox=SandboxMode.NONE,     # model call = sole net user
                        env_passthrough=True,          # trusted CLI needs real HOME/PATH/keychain
                        capture_cap=self._capture_cap, # model envelopes can be large
                        timeout_s=self._timeout_s,
                    ),
                    ledger=None,
                )
        except BaseException:
            if ledger is not None:
                with contextlib.suppress(RunAlreadyFinishedError, KeyError):
                    ledger.finish_run(rid, exit_code=SPAWN_FAILED_EXIT_CODE, wall_s=0.0)
            raise

        result: LLMResult | None = None
        try:
            result = parse_envelope(res.stdout, model=role.model)
        except LLMParseError:
            result = None

        if ledger is not None:
            with contextlib.suppress(RunAlreadyFinishedError):
                ledger.finish_run(
                    rid, exit_code=res.exit_code, wall_s=res.wall_s,
                    peak_rss_mb=res.peak_rss_mb,
                    tokens_in=result.input_tokens if result else 0,
                    tokens_out=result.output_tokens if result else 0,
                    cache_read=result.cache_read_tokens if result else 0,
                    cost_usd=result.cost_usd if result else 0.0,
                )
        return result

    async def complete_many(
        self, role: Role, prompts: list[str], *,
        schema: type[BaseModel] | None = None, ledger: Ledger | None = None,
    ) -> list[LLMResult]:
        # Distinct session_id + nonce per prompt = fresh context + diversity.
        async def one(i: int, p: str) -> LLMResult | None:
            return await self.complete(
                role, p, schema=schema,
                run_id=f"{role.name}-{uuid.uuid4().hex}" if ledger else None,
                ledger=ledger,
            )

        results = await asyncio.gather(*(one(i, p) for i, p in enumerate(prompts)))
        return [r for r in results if r is not None]


class FakeLLMClient:
    """Deterministic, offline. Returns scripted results in order; records calls."""

    def __init__(self, scripted: list[LLMResult]) -> None:
        self._scripted = list(scripted)
        self._i = 0
        self.calls: list[tuple[str, str]] = []  # (role name, prompt)

    async def complete(
        self, role: Role, prompt: str, *, session_id: str | None = None,
        system_prompt: str | None = None,
        schema: type[BaseModel] | None = None,
        run_id: str | None = None, ledger: Ledger | None = None,
    ) -> LLMResult | None:
        self.calls.append((role.name, prompt))
        if self._i >= len(self._scripted):
            return None
        r = self._scripted[self._i]
        self._i += 1
        return r

    async def complete_many(
        self, role: Role, prompts: list[str], *,
        schema: type[BaseModel] | None = None, ledger: Ledger | None = None,
    ) -> list[LLMResult]:
        out = []
        for i, p in enumerate(prompts):
            r = await self.complete(role, p, session_id=f"fake-{i}", schema=schema)
            if r is not None:
                out.append(r)
        return out


class AnthropicAPIClient:
    """Documented metered-billing alternative for high fan-out (deferred, D2/v0.1)."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError(
            "AnthropicAPIClient is the v0.1 metered-billing path (spec D2); "
            "v0 uses ClaudeCodeClient on the subscription."
        )

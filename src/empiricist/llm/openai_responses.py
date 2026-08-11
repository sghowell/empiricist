"""Tool-free OpenAI Responses transport for GPT-5.6.

This is the API-key path, not an attempt to reuse private Codex OAuth
credentials.  The request advertises no tools and asks for strict structured
output, so model output remains data that the harness verifies rather than code
the model can execute.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import math
import os
import sqlite3
import time
import urllib.error
import urllib.request
import uuid
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

from blake3 import blake3
from pydantic import BaseModel, ValidationError

from empiricist.config import env_fingerprint
from empiricist.executor.runner import DuplicateRunError
from empiricist.ledger.db import (
    UNKNOWN_BILLING_EXIT_CODE,
    Ledger,
    RunAlreadyFinishedError,
)
from empiricist.ledger.models import Run, now_iso
from empiricist.llm.models import BillingUnknownError, LLMResult
from empiricist.llm.roles import Role
from empiricist.llm.schemas import json_schema_for
from empiricist.store import Store

_DEFAULT_ENDPOINT = "https://api.openai.com/v1/responses"
_DEFAULT_SERVICE_TIER = "default"
_SUPPORTED_MODELS = frozenset({"gpt-5.6-sol"})
_CALL_FAILED_EXIT_CODE = 1


class OpenAIClientError(RuntimeError):
    """Base error for the Responses transport."""


class OpenAIAuthError(OpenAIClientError):
    """The supported API-key authentication route is not configured."""


class OpenAITransportError(OpenAIClientError):
    """The HTTP request failed or returned an invalid response."""

    def __init__(
        self,
        message: str,
        *,
        receipt: bytes | None = None,
        billing_unknown: bool = False,
    ) -> None:
        super().__init__(message)
        self.receipt = receipt
        self.billing_unknown = billing_unknown


class JSONTransport(Protocol):
    async def post_json(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        *,
        timeout_s: float,
    ) -> dict[str, Any]: ...


class UrllibJSONTransport:
    """Small stdlib HTTP transport; injectable so unit tests stay offline."""

    def __init__(self, *, max_response_bytes: int = 16 * 1024 * 1024) -> None:
        self._max_response_bytes = max_response_bytes

    async def post_json(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        *,
        timeout_s: float,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._post_json_sync, url, headers, payload, timeout_s
        )

    def _post_json_sync(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_s: float,
    ) -> dict[str, Any]:
        body = _canonical_json(payload)
        request = urllib.request.Request(
            url,
            data=body,
            headers={**headers, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as response:
                raw = response.read(self._max_response_bytes + 1)
        except urllib.error.HTTPError as exc:
            raw_detail = exc.read(4096)
            detail = raw_detail.decode("utf-8", errors="replace")
            raise OpenAITransportError(
                f"OpenAI Responses HTTP {exc.code}: {detail}",
                receipt=_canonical_json({
                    "body": detail,
                    "kind": "http_error",
                    "status": exc.code,
                }),
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            message = f"OpenAI Responses request failed: {exc}"
            raise OpenAITransportError(
                message,
                billing_unknown=True,
                receipt=_canonical_json({
                    "kind": "transport_error",
                    "message": message,
                }),
            ) from exc

        if len(raw) > self._max_response_bytes:
            raise OpenAITransportError(
                f"OpenAI response exceeded {self._max_response_bytes} bytes",
                billing_unknown=True,
            )
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OpenAITransportError(
                "OpenAI response was not valid JSON",
                billing_unknown=True,
            ) from exc
        if not isinstance(decoded, dict):
            raise OpenAITransportError(
                "OpenAI response was not a JSON object",
                billing_unknown=True,
            )
        return decoded


@dataclass(frozen=True)
class OpenAIPricing:
    """Explicit rates used only for local budget accounting.

    API responses report tokens, not the billed dollar amount.  Rates are
    therefore operator-supplied instead of silently embedding a price that can
    drift.  With no pricing object, token accounting remains exact and
    ``cost_usd`` is zero.
    """

    input_usd_per_mtok: float
    cached_input_usd_per_mtok: float
    output_usd_per_mtok: float

    def __post_init__(self) -> None:
        if min(
            self.input_usd_per_mtok,
            self.cached_input_usd_per_mtok,
            self.output_usd_per_mtok,
        ) <= 0:
            raise ValueError("OpenAI pricing rates must be greater than zero")
        if not all(
            math.isfinite(rate)
            for rate in (
                self.input_usd_per_mtok,
                self.cached_input_usd_per_mtok,
                self.output_usd_per_mtok,
            )
        ):
            raise ValueError("OpenAI pricing rates must be finite")

    def estimate(
        self,
        *,
        input_tokens: int,
        cached_input_tokens: int,
        cache_write_tokens: int,
        output_tokens: int,
    ) -> float:
        counts = (
            input_tokens,
            cached_input_tokens,
            cache_write_tokens,
            output_tokens,
        )
        if any(
            isinstance(count, bool) or not isinstance(count, int) or count < 0
            for count in counts
        ):
            raise ValueError("OpenAI token counts must be non-negative integers")
        if cached_input_tokens + cache_write_tokens > input_tokens:
            raise ValueError(
                "OpenAI cached and cache-write tokens exceed total input tokens"
            )
        total_input = input_tokens
        cached = cached_input_tokens
        cache_write = cache_write_tokens
        uncached = total_input - cached - cache_write
        # GPT-5.6 billing rules are independent of the operator-supplied base
        # rates: cache writes cost 1.25x uncached input, and requests above
        # 272K input tokens cost 2x input and 1.5x output.
        input_multiplier = 2.0 if total_input > 272_000 else 1.0
        output_multiplier = 1.5 if total_input > 272_000 else 1.0
        cost = (
            input_multiplier
            * (
                uncached * self.input_usd_per_mtok
                + cached * self.cached_input_usd_per_mtok
                + cache_write * 1.25 * self.input_usd_per_mtok
            )
            + output_multiplier
            * output_tokens
            * self.output_usd_per_mtok
        ) / 1_000_000
        if not math.isfinite(cost):
            raise ValueError("calculated OpenAI cost is not finite")
        return cost


class OpenAIResponsesClient:
    """GPT-5.6 Responses implementation of the shared ``LLMClient`` protocol."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "gpt-5.6-sol",
        reasoning_mode: str = "pro",
        endpoint: str = _DEFAULT_ENDPOINT,
        timeout_s: float = 900.0,
        max_output_tokens: int | None = None,
        max_concurrency: int = 8,
        transport: JSONTransport | None = None,
        store: Store | None = None,
        pricing: OpenAIPricing | None = None,
    ) -> None:
        if reasoning_mode not in {"standard", "pro"}:
            raise ValueError("reasoning_mode must be 'standard' or 'pro'")
        if model not in _SUPPORTED_MODELS:
            supported = ", ".join(sorted(_SUPPORTED_MODELS))
            raise ValueError(
                f"unsupported OpenAI model {model!r}; supported model: {supported}"
            )
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        if max_output_tokens is not None and max_output_tokens < 1:
            raise ValueError("max_output_tokens must be >= 1")
        self._api_key = (
            api_key if api_key is not None else os.environ.get("OPENAI_API_KEY")
        )
        self.model = model
        self.reasoning_mode = reasoning_mode
        self._endpoint = endpoint
        self._timeout_s = timeout_s
        self._max_output_tokens = max_output_tokens
        self._max_concurrency = max_concurrency
        self._transport = transport or UrllibJSONTransport()
        self._store = store
        self._pricing = pricing
        self._sem: asyncio.Semaphore | None = None
        self._sem_loop: asyncio.AbstractEventLoop | None = None

    @property
    def has_cost_accounting(self) -> bool:
        return self._pricing is not None

    def _sem_for_loop(self) -> asyncio.Semaphore:
        loop = asyncio.get_running_loop()
        if self._sem is None or self._sem_loop is not loop:
            self._sem = asyncio.Semaphore(self._max_concurrency)
            self._sem_loop = loop
        return self._sem

    def build_request(
        self,
        role: Role,
        prompt: str,
        *,
        system_prompt: str,
        schema: type[BaseModel] | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "store": False,
            "service_tier": _DEFAULT_SERVICE_TIER,
            "reasoning": {
                "mode": self.reasoning_mode,
                "effort": role.effort.value,
            },
            "instructions": system_prompt,
            "input": [{"role": "user", "content": prompt}],
            # This is the load-bearing "model never gets a shell" boundary.
            "tools": [],
            "tool_choice": "none",
            "parallel_tool_calls": False,
        }
        if schema is not None:
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": _schema_name(schema),
                    "strict": True,
                    "schema": _openai_strict_schema(json_schema_for(schema)),
                }
            }
        if self._max_output_tokens is not None:
            payload["max_output_tokens"] = self._max_output_tokens
        return payload

    async def complete(
        self,
        role: Role,
        prompt: str,
        *,
        session_id: str | None = None,
        system_prompt: str | None = None,
        schema: type[BaseModel] | None = None,
        run_id: str | None = None,
        ledger: Ledger | None = None,
    ) -> LLMResult | None:
        del session_id  # accepted for protocol compatibility; every call is stateless
        if not self._api_key:
            raise OpenAIAuthError(
                "OPENAI_API_KEY is required for the supported Responses API route; "
                "Codex subscription OAuth credentials are not reused by the harness"
            )
        if ledger is not None and self._store is None:
            raise OpenAIClientError(
                "ledger-backed OpenAI calls require a Store for retrievable receipts"
            )
        if ledger is not None and self._pricing is None:
            raise OpenAIClientError(
                "ledger-backed OpenAI calls require explicit pricing; "
                "recording an unknown paid cost as zero is not allowed"
            )

        payload = self.build_request(
            role,
            prompt,
            system_prompt=(
                system_prompt if system_prompt is not None else role.system_prompt
            ),
            schema=schema,
        )
        request_bytes = _canonical_json(payload)
        request_digest = _store_or_hash(self._store, request_bytes)
        config_digest = _store_or_hash(
            self._store,
            _canonical_json({
                "billing_rules": {
                    "cache_write_input_multiplier": 1.25,
                    "long_context_input_multiplier": 2.0,
                    "long_context_output_multiplier": 1.5,
                    "long_context_threshold_tokens": 272_000,
                },
                "endpoint": self._endpoint,
                "max_output_tokens": self._max_output_tokens,
                "pricing": (
                    {
                        "cached_input_usd_per_mtok": (
                            self._pricing.cached_input_usd_per_mtok
                        ),
                        "input_usd_per_mtok": self._pricing.input_usd_per_mtok,
                        "output_usd_per_mtok": self._pricing.output_usd_per_mtok,
                    }
                    if self._pricing is not None
                    else None
                ),
            }),
        )
        rid = run_id or f"{role.name}-{uuid.uuid4().hex}"
        started = now_iso()
        if ledger is not None:
            try:
                ledger.start_run(
                    Run(
                        run_id=rid,
                        move="SAMPLE",
                        role=role.name,
                        model=self.model,
                        provider="openai",
                        reasoning_mode=self.reasoning_mode,
                        reasoning_effort=role.effort.value,
                        auth_route="api_key",
                        request_digest=request_digest,
                        config_hash=config_digest,
                        env_fingerprint=env_fingerprint(),
                        started=started,
                    )
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateRunError(rid) from exc

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        began = time.monotonic()
        response_digest: str | None = None
        response_received = False
        accounting_known = False
        finished = False
        try:
            async with self._sem_for_loop():
                transport_task = asyncio.create_task(
                    self._transport.post_json(
                        self._endpoint,
                        headers,
                        payload,
                        timeout_s=self._timeout_s,
                    )
                )
                cancelled: asyncio.CancelledError | None = None
                try:
                    response = await asyncio.shield(transport_task)
                except asyncio.CancelledError as exc:
                    # A to_thread HTTP request keeps running after cancellation.
                    # Await it so a paid response is receipted before propagating
                    # cancellation to the campaign.
                    cancelled = exc
                    response = await transport_task
                response_received = True

            duration_ms = round((time.monotonic() - began) * 1000)
            response_bytes = _canonical_json(response)
            response_digest = _store_or_hash(self._store, response_bytes)
            result = _parse_response(
                response,
                requested_model=self.model,
                schema=schema,
                duration_ms=duration_ms,
                pricing=self._pricing,
            )
            if ledger is not None:
                ledger.finish_run(
                    rid,
                    exit_code=0 if result.ok else _CALL_FAILED_EXIT_CODE,
                    wall_s=duration_ms / 1000,
                    tokens_in=result.input_tokens,
                    tokens_out=result.output_tokens,
                    cache_read=result.cache_read_tokens,
                    cost_usd=result.cost_usd,
                    response_digest=response_digest,
                )
                finished = True
            accounting_known = True
            if cancelled is not None:
                raise cancelled
            return result
        except BaseException as exc:
            billing_unknown = isinstance(exc, BillingUnknownError) or (
                not accounting_known
                and (
                    response_received
                    or (
                        isinstance(exc, OpenAITransportError)
                        and exc.billing_unknown
                    )
                )
            )
            if response_digest is None and self._store is not None:
                receipt = (
                    exc.receipt
                    if isinstance(exc, OpenAITransportError) and exc.receipt is not None
                    else _canonical_json({
                        "error_type": type(exc).__name__,
                        "billing_unknown": billing_unknown,
                        "kind": "local_error",
                        "message": str(exc),
                    })
                )
                response_digest = self._store.put(receipt)
            if ledger is not None and not finished:
                with contextlib.suppress(RunAlreadyFinishedError, KeyError):
                    ledger.finish_run(
                        rid,
                        exit_code=(
                            UNKNOWN_BILLING_EXIT_CODE
                            if billing_unknown
                            else _CALL_FAILED_EXIT_CODE
                        ),
                        wall_s=time.monotonic() - began,
                        response_digest=response_digest,
                    )
            if billing_unknown and not isinstance(exc, BillingUnknownError):
                raise BillingUnknownError(
                    "OpenAI call may have been billed without trustworthy "
                    "usage accounting"
                ) from exc
            raise

    async def complete_many(
        self,
        role: Role,
        prompts: list[str],
        *,
        schema: type[BaseModel] | None = None,
        ledger: Ledger | None = None,
    ) -> list[LLMResult]:
        async def one(prompt: str) -> LLMResult | None:
            return await self.complete(
                role,
                prompt,
                schema=schema,
                run_id=f"{role.name}-{uuid.uuid4().hex}" if ledger else None,
                ledger=ledger,
            )

        tasks = [
            asyncio.create_task(one(prompt))
            for prompt in prompts
        ]
        if not tasks:
            return []
        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_EXCEPTION,
        )
        if any(
            not task.cancelled() and task.exception() is not None
            for task in done
        ):
            # Do not send work still queued behind the semaphore. Cancellation
            # of an already-sent call is handled by complete(), which waits for
            # and receipts its response before finishing.
            for task in pending:
                task.cancel()
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)
        # Every started sibling is awaited first: paid requests must finish and
        # receipt even when one member of the wave has unknown billing.
        unknown = next(
            (
                outcome
                for outcome in outcomes
                if isinstance(outcome, BillingUnknownError)
            ),
            None,
        )
        if unknown is not None:
            raise unknown
        error = next(
            (
                outcome
                for outcome in outcomes
                if isinstance(outcome, Exception)
            ),
            None,
        )
        if error is not None:
            raise error
        cancellation = next(
            (
                outcome
                for outcome in outcomes
                if isinstance(outcome, BaseException)
            ),
            None,
        )
        if cancellation is not None:
            raise cancellation
        return [
            result
            for result in outcomes
            if isinstance(result, LLMResult)
        ]


def _schema_name(schema: type[BaseModel]) -> str:
    name = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in schema.__name__)
    return name[:64] or "empiricist_output"


def _openai_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Produce a strict-compatible schema without changing harness models.

    OpenAI strict schemas require every object to be closed, so arbitrary JSON
    maps cannot be represented directly. On the wire only, maps become arrays
    of closed ``{"key": ..., "value": ...}`` records; the response parser
    converts them back before Pydantic validation.
    """

    def convert(value: Any) -> Any:
        if isinstance(value, list):
            return [convert(child) for child in value]
        if not isinstance(value, dict):
            return value

        source = deepcopy(value)
        source.pop("default", None)
        properties = source.get("properties")
        additional = source.get("additionalProperties")
        if (
            source.get("type") == "object"
            and not isinstance(properties, dict)
            and isinstance(additional, dict)
        ):
            metadata = {
                key: source[key]
                for key in ("title", "description")
                if key in source
            }
            return {
                **metadata,
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                        "value": convert(additional),
                    },
                    "required": ["key", "value"],
                    "additionalProperties": False,
                },
            }

        out = {key: convert(child) for key, child in source.items()}
        converted_properties = out.get("properties")
        if isinstance(converted_properties, dict):
            out["required"] = list(converted_properties)
            out["additionalProperties"] = False
        return out

    return convert(schema)


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise OpenAIClientError(f"value is not canonical JSON: {exc}") from exc


def _store_or_hash(store: Store | None, content: bytes) -> str:
    return store.put(content) if store is not None else blake3(content).hexdigest()


def _required_token_count(
    source: dict[str, Any],
    key: str,
    *,
    context: str,
) -> int:
    value = source.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BillingUnknownError(
            f"OpenAI {context}.{key} must be a non-negative integer"
        )
    return value


def _parse_usage(response: dict[str, Any]) -> tuple[int, int, int, int]:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        raise BillingUnknownError("OpenAI response is missing a usage object")
    input_details = usage.get("input_tokens_details")
    if not isinstance(input_details, dict):
        raise BillingUnknownError(
            "OpenAI usage is missing input_tokens_details"
        )

    input_tokens = _required_token_count(
        usage, "input_tokens", context="usage"
    )
    output_tokens = _required_token_count(
        usage, "output_tokens", context="usage"
    )
    cached_tokens = _required_token_count(
        input_details,
        "cached_tokens",
        context="usage.input_tokens_details",
    )
    cache_write_tokens = _required_token_count(
        input_details,
        "cache_write_tokens",
        context="usage.input_tokens_details",
    )
    if cached_tokens + cache_write_tokens > input_tokens:
        raise BillingUnknownError(
            "OpenAI cached and cache-write tokens exceed total input tokens"
        )

    total_tokens = usage.get("total_tokens")
    if total_tokens is not None:
        total = _required_token_count(usage, "total_tokens", context="usage")
        if total != input_tokens + output_tokens:
            raise BillingUnknownError(
                "OpenAI total_tokens does not equal input_tokens + output_tokens"
            )

    output_details = usage.get("output_tokens_details")
    if output_details is not None:
        if not isinstance(output_details, dict):
            raise BillingUnknownError(
                "OpenAI output_tokens_details must be an object"
            )
        if "reasoning_tokens" in output_details:
            reasoning_tokens = _required_token_count(
                output_details,
                "reasoning_tokens",
                context="usage.output_tokens_details",
            )
            if reasoning_tokens > output_tokens:
                raise BillingUnknownError(
                    "OpenAI reasoning tokens exceed total output tokens"
                )

    return input_tokens, output_tokens, cached_tokens, cache_write_tokens


def _parse_response(
    response: dict[str, Any],
    *,
    requested_model: str,
    schema: type[BaseModel] | None,
    duration_ms: int,
    pricing: OpenAIPricing | None,
) -> LLMResult:
    if response.get("model") != requested_model:
        raise BillingUnknownError(
            "OpenAI response model does not exactly match the requested model"
        )
    if response.get("service_tier") != _DEFAULT_SERVICE_TIER:
        raise BillingUnknownError(
            "OpenAI response service_tier does not exactly match 'default'"
        )
    (
        input_tokens,
        output_tokens,
        cached_tokens,
        cache_write_tokens,
    ) = _parse_usage(response)

    text_parts: list[str] = []
    refusal: str | None = None
    protocol_violation: str | None = None

    def flag_violation(reason: str) -> None:
        nonlocal protocol_violation
        priority = {
            "unexpected_output_content": 1,
            "unexpected_output_item": 2,
            "unexpected_tool_call": 3,
        }
        if (
            protocol_violation is None
            or priority[reason] > priority[protocol_violation]
        ):
            protocol_violation = reason

    raw_output = response.get("output")
    if raw_output is None:
        output_items: list[Any] = []
    elif isinstance(raw_output, list):
        output_items = raw_output
    else:
        output_items = []
        flag_violation("unexpected_output_item")

    for item in output_items:
        if not isinstance(item, dict):
            flag_violation("unexpected_output_item")
            continue
        item_type = str(item.get("type") or "")
        if item_type not in {"reasoning", "message"}:
            flag_violation(
                "unexpected_tool_call"
                if _looks_like_tool_call(item_type)
                else "unexpected_output_item"
            )
            continue
        if item_type == "reasoning":
            continue

        raw_content = item.get("content")
        if raw_content is None:
            content_items: list[Any] = []
        elif isinstance(raw_content, list):
            content_items = raw_content
        else:
            content_items = []
            flag_violation("unexpected_output_content")
        for content in content_items:
            if not isinstance(content, dict):
                flag_violation("unexpected_output_content")
                continue
            content_type = str(content.get("type") or "")
            if content_type == "output_text":
                text_parts.append(str(content.get("text") or ""))
            elif content_type == "refusal":
                refusal = str(content.get("refusal") or "refused")
            else:
                flag_violation(
                    "unexpected_tool_call"
                    if _looks_like_tool_call(content_type)
                    else "unexpected_output_content"
                )

    text = "".join(text_parts)
    status = str(response.get("status") or "error")
    incomplete = response.get("incomplete_details") or {}
    stop_reason = (
        "refusal"
        if refusal is not None
        else str(incomplete.get("reason") or status)
    )
    is_error = (
        status != "completed"
        or refusal is not None
        or protocol_violation is not None
        or not text
    )
    if protocol_violation is not None:
        stop_reason = protocol_violation
    parsed: dict[str, Any] | None = None
    if schema is not None and not is_error:
        try:
            decoded = json.loads(text)
            restored = _restore_openai_maps(
                decoded,
                json_schema_for(schema),
            )
            validated = schema.model_validate(restored)
        except (json.JSONDecodeError, ValidationError, OpenAIClientError):
            is_error = True
            stop_reason = "invalid_json"
        else:
            parsed = validated.model_dump(mode="json")

    cost = (
        pricing.estimate(
            input_tokens=input_tokens,
            cached_input_tokens=cached_tokens,
            cache_write_tokens=cache_write_tokens,
            output_tokens=output_tokens,
        )
        if pricing is not None
        else 0.0
    )
    response_id = str(response.get("id") or "")
    return LLMResult(
        text=text if refusal is None else refusal,
        parsed=parsed,
        stop_reason=stop_reason,
        is_error=is_error,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cached_tokens,
        cache_creation_tokens=cache_write_tokens,
        cost_usd=cost,
        duration_ms=duration_ms,
        session_id=response_id,
        uuid=response_id,
        model=requested_model,
    )


def _looks_like_tool_call(item_type: str) -> bool:
    """Classify present and future call-shaped output as a tool-boundary breach."""
    return item_type.endswith("_call") or "_call_" in item_type


def _restore_openai_maps(value: Any, schema: dict[str, Any]) -> Any:
    """Invert the strict wire encoding used by ``_openai_strict_schema``."""
    root = schema

    def resolve(node: dict[str, Any]) -> dict[str, Any]:
        ref = node.get("$ref")
        if not isinstance(ref, str):
            return node
        if not ref.startswith("#/"):
            raise OpenAIClientError(f"unsupported schema reference {ref!r}")
        target: Any = root
        for raw_part in ref[2:].split("/"):
            part = raw_part.replace("~1", "/").replace("~0", "~")
            if not isinstance(target, dict) or part not in target:
                raise OpenAIClientError(f"unresolved schema reference {ref!r}")
            target = target[part]
        if not isinstance(target, dict):
            raise OpenAIClientError(f"schema reference {ref!r} is not an object")
        return target

    def restore(current: Any, node: dict[str, Any]) -> Any:
        node = resolve(node)
        alternatives = node.get("anyOf")
        if isinstance(alternatives, list):
            if current is None:
                return None
            candidate = next(
                (
                    resolve(option)
                    for option in alternatives
                    if isinstance(option, dict) and option.get("type") != "null"
                ),
                None,
            )
            return restore(current, candidate) if candidate is not None else current

        properties = node.get("properties")
        additional = node.get("additionalProperties")
        if (
            node.get("type") == "object"
            and not isinstance(properties, dict)
            and isinstance(additional, dict)
        ):
            if not isinstance(current, list):
                raise OpenAIClientError("strict map output was not a key/value list")
            restored_map: dict[str, Any] = {}
            for item in current:
                if (
                    not isinstance(item, dict)
                    or set(item) != {"key", "value"}
                    or not isinstance(item["key"], str)
                ):
                    raise OpenAIClientError("strict map entry was malformed")
                key = item["key"]
                if key in restored_map:
                    raise OpenAIClientError(f"strict map repeated key {key!r}")
                restored_map[key] = restore(item["value"], additional)
            return restored_map
        if isinstance(properties, dict):
            if not isinstance(current, dict):
                return current
            return {
                key: restore(child, properties[key])
                if key in properties and isinstance(properties[key], dict)
                else child
                for key, child in current.items()
            }
        items = node.get("items")
        if node.get("type") == "array" and isinstance(items, dict) and isinstance(current, list):
            return [restore(item, items) for item in current]
        return current

    return restore(value, schema)

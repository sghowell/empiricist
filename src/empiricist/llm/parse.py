"""Parse the `claude --output-format json` envelope into an LLMResult.

Pure and total: raises LLMParseError only when the bytes are not a usable
envelope (empty, not JSON, or missing the identifying fields). A refusal /
max_tokens / api-error is a VALID envelope that parses to a not-`ok` result —
the caller decides whether to retry.
"""

from __future__ import annotations

import json
from typing import Any

from empiricist.llm.models import LLMResult

# Fields that must be present for the string to be a claude result envelope at all.
_REQUIRED = ("result", "stop_reason", "session_id")


class LLMParseError(Exception):
    """The subprocess output was not a parseable claude result envelope."""


def parse_envelope(stdout: str, *, model: str) -> LLMResult:
    text = stdout.strip()
    if not text:
        raise LLMParseError("empty output (subprocess produced no envelope)")
    try:
        env: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMParseError(f"output is not JSON: {e}; head={text[:200]!r}") from e
    if not isinstance(env, dict) or any(k not in env for k in _REQUIRED):
        raise LLMParseError(f"missing required envelope fields; keys={list(env)[:20]}")

    usage = env.get("usage") or {}
    return LLMResult(
        text=env["result"] or "",
        parsed=env.get("structured_output"),
        stop_reason=env["stop_reason"],
        is_error=bool(env.get("is_error", False)),
        input_tokens=int(usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("output_tokens") or 0),
        cache_read_tokens=int(usage.get("cache_read_input_tokens") or 0),
        cache_creation_tokens=int(usage.get("cache_creation_input_tokens") or 0),
        cost_usd=float(env.get("total_cost_usd") or 0.0),
        duration_ms=int(env.get("duration_ms") or 0),
        session_id=env["session_id"],
        uuid=env.get("uuid", ""),
        model=model,
    )

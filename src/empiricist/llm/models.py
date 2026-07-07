"""LLM layer core models: Effort levels and the parsed result of one model call."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

# stop_reasons that indicate a usable response (verified against claude v2.1.201:
# plain text -> end_turn; --json-schema success -> tool_use).
_OK_STOP_REASONS = frozenset({"end_turn", "tool_use"})


class Effort(StrEnum):
    """Maps 1:1 to `claude --effort <level>` (Fable 5 depth control; no temperature)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
    MAX = "max"


@dataclass(frozen=True)
class LLMResult:
    """The parsed outcome of one `claude -p` invocation."""

    text: str                    # the envelope `result` field
    parsed: dict[str, Any] | None  # `structured_output` when --json-schema was used
    stop_reason: str
    is_error: bool
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    cost_usd: float
    duration_ms: int
    session_id: str
    uuid: str
    model: str

    @property
    def ok(self) -> bool:
        """Usable response: no error and a terminal (not refusal/max_tokens) stop."""
        return not self.is_error and self.stop_reason in _OK_STOP_REASONS

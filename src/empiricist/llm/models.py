"""LLM layer core models: Effort levels and the parsed result of one model call."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

# stop_reasons that indicate a usable response (verified against claude v2.1.201:
# plain text -> end_turn; --json-schema success -> tool_use).
_OK_STOP_REASONS = frozenset({"end_turn", "tool_use", "completed"})


class BillingUnknownError(RuntimeError):
    """A paid provider call lacks trustworthy usage/cost accounting."""


class Effort(StrEnum):
    """Shared role effort values supported by the active model transports."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
    MAX = "max"


@dataclass(frozen=True)
class LLMResult:
    """The parsed outcome of one provider invocation."""

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
        """Process-level success: no error and a terminal (not refusal/max_tokens)
        stop. NOTE: for --json-schema calls this does NOT guarantee an artifact —
        check `has_artifact` (or `parsed is not None`) before using `parsed`."""
        return not self.is_error and self.stop_reason in _OK_STOP_REASONS

    @property
    def has_artifact(self) -> bool:
        """A usable structured artifact was produced (schema calls): ok AND parsed."""
        return self.ok and self.parsed is not None

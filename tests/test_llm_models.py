"""Tests for LLM layer core models."""

import pytest

from empiricist.llm.models import Effort, LLMResult


def test_effort_members_map_to_cli_flag_values():
    assert {e.value for e in Effort} == {"low", "medium", "high", "xhigh", "max"}


def test_llm_result_ok_on_end_turn():
    r = LLMResult(
        text="hi", parsed=None, stop_reason="end_turn", is_error=False,
        input_tokens=10, output_tokens=2, cache_read_tokens=0,
        cache_creation_tokens=100, cost_usd=0.01, duration_ms=1000,
        session_id="s", uuid="u", model="claude-fable-5",
    )
    assert r.ok is True


def test_llm_result_ok_on_tool_use():
    """--json-schema success comes back as stop_reason=tool_use."""
    r = LLMResult(
        text='{"a":1}', parsed={"a": 1}, stop_reason="tool_use", is_error=False,
        input_tokens=10, output_tokens=2, cache_read_tokens=0,
        cache_creation_tokens=0, cost_usd=0.01, duration_ms=1,
        session_id="s", uuid="u", model="claude-fable-5",
    )
    assert r.ok is True and r.parsed == {"a": 1}


@pytest.mark.parametrize("stop", ["refusal", "max_tokens"])
def test_llm_result_not_ok_on_failure_stop_reasons(stop):
    r = LLMResult(
        text="", parsed=None, stop_reason=stop, is_error=False,
        input_tokens=1, output_tokens=0, cache_read_tokens=0,
        cache_creation_tokens=0, cost_usd=0.0, duration_ms=1,
        session_id="s", uuid="u", model="claude-fable-5",
    )
    assert r.ok is False


def test_llm_result_not_ok_when_is_error():
    r = LLMResult(
        text="", parsed=None, stop_reason="end_turn", is_error=True,
        input_tokens=0, output_tokens=0, cache_read_tokens=0,
        cache_creation_tokens=0, cost_usd=0.0, duration_ms=1,
        session_id="s", uuid="u", model="claude-fable-5",
    )
    assert r.ok is False


def test_llm_result_is_frozen():
    r = LLMResult(
        text="hi", parsed=None, stop_reason="end_turn", is_error=False,
        input_tokens=1, output_tokens=1, cache_read_tokens=0,
        cache_creation_tokens=0, cost_usd=0.0, duration_ms=1,
        session_id="s", uuid="u", model="claude-fable-5",
    )
    with pytest.raises(AttributeError):
        r.text = "x"  # type: ignore[misc]

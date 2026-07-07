"""Tests for parsing the `claude --output-format json` envelope into an LLMResult.

Envelopes below are minimized from real claude v2.1.201 output captured 2026-07-06.
"""

import json

import pytest

from empiricist.llm.parse import LLMParseError, parse_envelope

# Real plain-text success envelope (--tools "" , no --json-schema).
PLAIN_SUCCESS = json.dumps({
    "type": "result", "subtype": "success", "is_error": False,
    "duration_ms": 4329, "num_turns": 1, "result": "ok", "stop_reason": "end_turn",
    "session_id": "e97d657a", "total_cost_usd": 0.20132,
    "usage": {"input_tokens": 1352, "output_tokens": 4, "cache_read_input_tokens": 0,
              "cache_creation_input_tokens": 9380},
    "modelUsage": {"claude-fable-5": {"inputTokens": 1352, "outputTokens": 4}},
    "uuid": "7c8d031e",
})

# Real --json-schema success envelope (structured_output present, tool_use).
SCHEMA_SUCCESS = json.dumps({
    "type": "result", "subtype": "success", "is_error": False,
    "duration_ms": 4525, "num_turns": 2, "result": "{\"answer\":\"ok\"}",
    "stop_reason": "tool_use", "session_id": "3fbeff2e", "total_cost_usd": 0.01507,
    "usage": {"input_tokens": 34, "output_tokens": 53, "cache_read_input_tokens": 0,
              "cache_creation_input_tokens": 604},
    "modelUsage": {"claude-fable-5": {"inputTokens": 34, "outputTokens": 53}},
    "structured_output": {"answer": "ok"}, "uuid": "a9475db1",
})

REFUSAL = json.dumps({
    "type": "result", "is_error": False, "duration_ms": 500, "result": "",
    "stop_reason": "refusal", "session_id": "s", "total_cost_usd": 0.001,
    "usage": {"input_tokens": 10, "output_tokens": 0, "cache_read_input_tokens": 0,
              "cache_creation_input_tokens": 0},
    "modelUsage": {"claude-fable-5": {}}, "uuid": "u",
})

API_ERROR = json.dumps({
    "type": "result", "is_error": True, "api_error_status": 529, "duration_ms": 100,
    "result": "overloaded", "stop_reason": "end_turn", "session_id": "s",
    "total_cost_usd": 0.0,
    "usage": {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
              "cache_creation_input_tokens": 0},
    "modelUsage": {"claude-fable-5": {}}, "uuid": "u",
})


def test_parse_plain_success():
    r = parse_envelope(PLAIN_SUCCESS, model="claude-fable-5")
    assert r.ok and r.text == "ok" and r.parsed is None
    assert r.input_tokens == 1352 and r.output_tokens == 4
    assert r.cache_creation_tokens == 9380 and r.cost_usd == pytest.approx(0.20132)
    assert r.session_id == "e97d657a" and r.stop_reason == "end_turn"


def test_parse_schema_success_exposes_structured_output():
    r = parse_envelope(SCHEMA_SUCCESS, model="claude-fable-5")
    assert r.ok and r.parsed == {"answer": "ok"}
    assert r.text == '{"answer":"ok"}' and r.stop_reason == "tool_use"
    assert r.cost_usd == pytest.approx(0.01507)


def test_parse_refusal_is_not_ok():
    r = parse_envelope(REFUSAL, model="claude-fable-5")
    assert r.ok is False and r.stop_reason == "refusal" and r.parsed is None


def test_parse_api_error_is_not_ok():
    r = parse_envelope(API_ERROR, model="claude-fable-5")
    assert r.ok is False and r.is_error is True


def test_parse_empty_output_raises():
    with pytest.raises(LLMParseError):
        parse_envelope("", model="claude-fable-5")


def test_parse_non_json_raises():
    with pytest.raises(LLMParseError):
        parse_envelope("Error: not logged in\n", model="claude-fable-5")


def test_parse_missing_required_field_raises():
    with pytest.raises(LLMParseError):
        parse_envelope(json.dumps({"type": "result"}), model="claude-fable-5")


def test_parse_tolerates_missing_usage_subfields():
    """A degraded envelope with a partial usage block should default to 0, not crash."""
    env = json.dumps({
        "is_error": False, "result": "x", "stop_reason": "end_turn",
        "session_id": "s", "uuid": "u", "total_cost_usd": 0.0,
        "duration_ms": 1, "usage": {}, "modelUsage": {},
    })
    r = parse_envelope(env, model="claude-fable-5")
    assert r.input_tokens == 0 and r.output_tokens == 0 and r.cost_usd == 0.0

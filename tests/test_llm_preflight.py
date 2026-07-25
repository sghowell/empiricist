"""Tests for the one-call startup preflight and its structured-output canary."""

import asyncio
import json
import sys
from pathlib import Path

import pytest

from empiricist.llm.client import ClaudeCodeClient
from empiricist.llm.models import LLMResult
from empiricist.llm.openai_responses import OpenAIResponsesClient
from empiricist.llm.preflight import PreflightError, preflight

STUB = Path(__file__).parent / "stub_claude.py"


def _result(parsed: dict | None) -> LLMResult:
    return LLMResult(
        text=json.dumps(parsed) if parsed is not None else "ok",
        parsed=parsed,
        stop_reason="tool_use" if parsed is not None else "end_turn",
        is_error=False,
        input_tokens=1,
        output_tokens=1,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        cost_usd=0.001,
        duration_ms=1,
        session_id="test-session",
        uuid="test-response",
        model="test-model",
    )


def test_preflight_passes_strict_schema_to_exactly_one_call():
    class RecordingClient:
        def __init__(self) -> None:
            self.calls = []

        async def complete(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return _result({"ok": True})

    client = RecordingClient()
    report = asyncio.run(preflight(client))

    assert report.model_ok is True
    assert len(client.calls) == 1
    _args, kwargs = client.calls[0]
    schema = kwargs["schema"].model_json_schema()
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["ok"]
    assert schema["properties"]["ok"]["type"] == "boolean"


def test_preflight_passes_against_healthy_claude_stub(tmp_path, monkeypatch):
    argv_file = tmp_path / "argv.json"
    monkeypatch.setenv("STUB_ARGV_FILE", str(argv_file))
    c = ClaudeCodeClient(claude_bin=[sys.executable, str(STUB)])
    report = asyncio.run(preflight(c))
    assert report.model_ok is True and report.cost_usd >= 0.0

    argv = json.loads(argv_file.read_text())
    schema = json.loads(argv[argv.index("--json-schema") + 1])
    assert schema["required"] == ["ok"]


def test_preflight_uses_strict_structured_output_with_openai_responses():
    class StubTransport:
        def __init__(self) -> None:
            self.payloads = []

        async def post_json(self, url, headers, payload, *, timeout_s):
            self.payloads.append(payload)
            return {
                "id": "resp_preflight",
                "status": "completed",
                "model": "gpt-5.6-sol",
                "service_tier": "default",
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps({"ok": True}),
                            }
                        ],
                    }
                ],
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "input_tokens_details": {
                        "cached_tokens": 0,
                        "cache_write_tokens": 0,
                    },
                    "output_tokens_details": {"reasoning_tokens": 1},
                },
            }

    transport = StubTransport()
    client = OpenAIResponsesClient(api_key="test-key", transport=transport)

    report = asyncio.run(preflight(client))

    assert report.model_ok is True
    assert len(transport.payloads) == 1
    fmt = transport.payloads[0]["text"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["strict"] is True
    assert fmt["schema"]["additionalProperties"] is False
    assert fmt["schema"]["required"] == ["ok"]


def test_preflight_raises_on_crash(monkeypatch):
    monkeypatch.setenv("STUB_MODE", "crash")
    c = ClaudeCodeClient(claude_bin=[sys.executable, str(STUB)])
    with pytest.raises(PreflightError):
        asyncio.run(preflight(c))


@pytest.mark.parametrize("parsed", [None, {"ok": False}, {"ok": "true"}])
def test_preflight_rejects_missing_or_invalid_canary(parsed):
    class ScriptedClient:
        async def complete(self, *args, **kwargs):
            return _result(parsed)

    with pytest.raises(PreflightError, match="structured-output canary"):
        asyncio.run(preflight(ScriptedClient()))

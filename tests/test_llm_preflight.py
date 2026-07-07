"""Tests for the startup preflight (model-resolves + auth-live), against the stub."""

import asyncio
import sys
from pathlib import Path

from empiricist.llm.client import ClaudeCodeClient
from empiricist.llm.preflight import PreflightError, preflight

STUB = Path(__file__).parent / "stub_claude.py"


def test_preflight_passes_against_healthy_stub():
    c = ClaudeCodeClient(claude_bin=[sys.executable, str(STUB)])
    report = asyncio.run(preflight(c))
    assert report.model_ok is True and report.cost_usd >= 0.0


def test_preflight_raises_on_crash(monkeypatch):
    monkeypatch.setenv("STUB_MODE", "crash")
    c = ClaudeCodeClient(claude_bin=[sys.executable, str(STUB)])
    import pytest
    with pytest.raises(PreflightError):
        asyncio.run(preflight(c))

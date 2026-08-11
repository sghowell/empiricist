"""Tests for the LLMClient implementations.

ClaudeCodeClient is exercised against a STUB `claude` binary (tests/stub_claude.py)
so the full argv-build -> execute() -> parse path runs deterministically with no
network and no cost. Exactly one REAL model call exists in the milestone, in the
Task 6 live smoke — never in the unit suite.

The stub reads STUB_MODE / STUB_ARGV_FILE from its environment; the client runs
with env_passthrough=True (required by the real claude for auth), which is exactly
what carries those monkeypatched vars through execute() to the stub subprocess.
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest

from empiricist.ledger.db import Ledger
from empiricist.llm.client import ClaudeCodeClient, FakeLLMClient
from empiricist.llm.models import LLMResult
from empiricist.llm.roles import ROLES
from empiricist.llm.schemas import ConjectureOut
from empiricist.store import Store

STUB = Path(__file__).parent / "stub_claude.py"


def stub_client(**kw):
    # Invoke the stub via the current interpreter; sandbox=NONE (model calls need it).
    return ClaudeCodeClient(claude_bin=[sys.executable, str(STUB)], **kw)


def run(coro):
    return asyncio.run(coro)


# -- build_argv (pure) ---------------------------------------------------------

def test_build_argv_has_cost_control_and_model_flags():
    c = stub_client()
    argv = c.build_argv(ROLES["searcher"], "find a thing", session_id="sid",
                        system_prompt="ROLE CARD", schema=None)
    # cost recipe: replaced system prompt + dropped setting sources
    assert "--system-prompt" in argv and "ROLE CARD" in argv
    i = argv.index("--setting-sources")
    assert argv[i + 1] == ""
    assert "--model" in argv and "claude-fable-5" in argv
    assert "--tools" in argv and argv[argv.index("--tools") + 1] == ""
    assert "--output-format" in argv and "json" in argv
    assert "--effort" in argv and argv[argv.index("--effort") + 1] == "low"
    assert "--session-id" in argv and "sid" in argv
    assert "-p" in argv and "find a thing" in argv


def test_build_argv_includes_json_schema_when_given():
    c = stub_client()
    schema = {"type": "object", "properties": {"a": {"type": "string"}}}
    argv = c.build_argv(ROLES["conjecturer"], "p", session_id="s",
                        system_prompt="rc", schema=schema)
    i = argv.index("--json-schema")
    assert json.loads(argv[i + 1]) == schema


def test_build_argv_omits_json_schema_when_none():
    c = stub_client()
    argv = c.build_argv(ROLES["searcher"], "p", session_id="s",
                        system_prompt="rc", schema=None)
    assert "--json-schema" not in argv


# -- complete() via the stub binary -------------------------------------------

def test_complete_success_returns_ok_result():
    c = stub_client()
    r = run(c.complete(ROLES["searcher"], "prompt", session_id="s1"))
    assert isinstance(r, LLMResult) and r.ok
    assert r.text == "stub text answer" and r.model == "claude-fable-5"
    assert r.input_tokens == 30 and r.cost_usd == pytest.approx(0.001)


def test_complete_schema_mode_returns_parsed(monkeypatch):
    monkeypatch.setenv("STUB_MODE", "schema")
    c = stub_client()
    r = run(c.complete(ROLES["conjecturer"], "prompt", session_id="s2",
                       schema=ConjectureOut))
    assert r.ok and r.parsed is not None and r.parsed["family"] == "path"


def test_complete_refusal_returns_not_ok(monkeypatch):
    monkeypatch.setenv("STUB_MODE", "refusal")
    c = stub_client()
    r = run(c.complete(ROLES["searcher"], "prompt", session_id="s3"))
    assert r.ok is False and r.stop_reason == "refusal"


def test_complete_passes_correct_flags_to_binary(tmp_path, monkeypatch):
    argv_file = tmp_path / "argv.json"
    monkeypatch.setenv("STUB_ARGV_FILE", str(argv_file))
    c = stub_client()
    run(c.complete(ROLES["prover"], "prove it", session_id="sX",
                   system_prompt="THE PROVER CARD"))
    argv = json.loads(argv_file.read_text())
    assert "THE PROVER CARD" in argv and "prove it" in argv
    assert argv[argv.index("--effort") + 1] == "max"  # prover effort


def test_complete_records_full_runs_row_when_ledger_given(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    store = Store(tmp_path / "store")
    c = stub_client(store=store)
    r = run(c.complete(ROLES["searcher"], "prompt", session_id="s5",
                       run_id="run5", ledger=lg))
    row = lg.get_run("run5")
    assert row.role == "searcher" and row.model == "claude-fable-5"
    assert row.tokens_in == 30 and row.tokens_out == 5           # from the envelope
    assert row.cost_usd == pytest.approx(0.001) and row.ended is not None
    assert row.exit_code == 0
    assert row.provider == "anthropic"
    assert row.auth_route == "claude_code_cli"
    assert row.reasoning_effort == "low"
    assert row.argv and "--tools ''" in row.argv
    assert row.request_digest and store.exists(row.request_digest)
    assert row.response_digest and store.exists(row.response_digest)
    request = json.loads(store.get(row.request_digest))
    assert request["prompt"] == "prompt"
    assert request["tools"] == []
    assert r.ok
    lg.close()


def test_ledger_call_without_store_is_rejected_before_subprocess(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    c = stub_client()
    with pytest.raises(ValueError, match="Store"):
        run(c.complete(
            ROLES["searcher"], "prompt", run_id="missing-store", ledger=lg
        ))
    assert lg.conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
    lg.close()


def test_complete_crash_records_failure_row_and_flags_not_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "crash")
    lg = Ledger(tmp_path / "ledger.db")
    c = stub_client(store=Store(tmp_path / "store"))
    r = run(c.complete(ROLES["searcher"], "p", session_id="s6",
                       run_id="run6", ledger=lg))
    assert r is None or r.ok is False   # crash -> unparseable -> not ok
    row = lg.get_run("run6")
    assert row.ended is not None and row.exit_code != 0
    lg.close()


def test_complete_many_fans_out(tmp_path):
    c = stub_client(max_concurrency=4)
    prompts = [f"attempt {i}" for i in range(10)]
    results = run(c.complete_many(ROLES["searcher"], prompts))
    assert len(results) == 10 and all(r.ok for r in results)


def test_session_id_is_a_fresh_valid_uuid_per_call(tmp_path, monkeypatch):
    import uuid as _uuid
    seen = set()
    for _ in range(3):
        f = tmp_path / f"argv{_}.json"
        monkeypatch.setenv("STUB_ARGV_FILE", str(f))
        c = stub_client()
        run(c.complete(ROLES["searcher"], "p"))
        argv = json.loads(f.read_text())
        sid = argv[argv.index("--session-id") + 1]
        _uuid.UUID(sid)              # must parse as a UUID (real claude requires it)
        seen.add(sid)
    assert len(seen) == 3           # fresh per call (F2)


def test_complete_many_two_waves_no_runid_collision(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    c = stub_client(max_concurrency=4, store=Store(tmp_path / "store"))
    r1 = run(c.complete_many(ROLES["searcher"], [f"a{i}" for i in range(5)], ledger=lg))
    r2 = run(c.complete_many(ROLES["searcher"], [f"b{i}" for i in range(5)], ledger=lg))
    assert len(r1) == 5 and len(r2) == 5   # second wave must not crash on run_id collision
    lg.close()


# -- FakeLLMClient (deterministic, for downstream tests) ----------------------

def test_fake_client_returns_scripted_results():
    scripted = [
        LLMResult(text="a", parsed={"x": 1}, stop_reason="tool_use", is_error=False,
                  input_tokens=1, output_tokens=1, cache_read_tokens=0,
                  cache_creation_tokens=0, cost_usd=0.0, duration_ms=1,
                  session_id="f", uuid="f", model="claude-fable-5"),
    ]
    c = FakeLLMClient(scripted)
    r = run(c.complete(ROLES["searcher"], "anything", session_id="s"))
    assert r.parsed == {"x": 1}


def test_fake_client_records_calls_for_assertions():
    c = FakeLLMClient([])
    run_calls = c.calls
    assert run_calls == []

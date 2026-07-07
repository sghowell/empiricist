# Empiricist M4: LLM layer (Claude Code transport) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drive Fable 5 (`claude-fable-5`) as a pure structured-JSON role-sampler via Claude Code headless (`claude -p`), routed **through** `executor.runner.execute()` (so the model call is a provenance-recorded, resource-bounded subprocess — the model still never gets a shell, tools disabled). An injectable `LLMClient` protocol with a real `ClaudeCodeClient`, a deterministic `FakeLLMClient` for downstream tests, versioned role definitions, robust envelope parsing, and a preflight check.

**Architecture:** `llm/parse.py` (pure: the `claude --output-format json` envelope → `LLMResult`) · `llm/models.py` (`LLMResult`, `Role`, `Effort`) · `llm/roles.py` (the 7 role cards + sampling policy) · `llm/schemas.py` (pydantic output schemas → JSON schema for `--json-schema`) · `llm/client.py` (`LLMClient` Protocol; `ClaudeCodeClient` builds argv + runs via `execute(sandbox=NONE)` + parses + records a full runs row; `FakeLLMClient`; `AnthropicAPIClient` stub) · `llm/preflight.py` (model-resolves + auth-live, one cheap real call). Tests use a **stub `claude` binary** (a tiny python script emitting canned envelopes) so the full spawn→parse path is exercised deterministically with zero network/cost; exactly one real Fable-5 call happens in the Task 6 live smoke.

**Tech Stack:** Python 3.11, `pydantic>=2` (new dep; role schemas + validation), the M3 executor, the M1-2 ledger. Verified against `claude` v2.1.201.

**Reference:** spec §5 + D2 (docs/superpowers/specs/2026-07-06-empiricist-harness-design.md). Ground-truth transport facts (verified live 2026-07-06):
- Success envelope: `{result: str, stop_reason: "end_turn"|"tool_use", is_error: false, session_id, uuid, total_cost_usd, duration_ms, usage:{input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens}, modelUsage:{"claude-fable-5":{...}}}`. With `--json-schema`, a parsed **`structured_output`** object is present and `stop_reason == "tool_use"`.
- **Cost recipe (13× saving, mandatory):** `--system-prompt <role card>` + `--setting-sources ""` drops the leaked global CLAUDE.md/default-prompt (a trivial call goes $0.20 → $0.015). `--bare` would break subscription auth — do not use it.
- Failure `stop_reason ∈ {refusal, max_tokens}` or `is_error: true`.
- Fable 5: no temperature/seed (diversity via prompt/nonce); `--effort {low,medium,high,xhigh,max}`; `--tools ""` disables all tools.
- The model call is the ONE legitimate network user → it runs `sandbox=SandboxMode.NONE` (network needed for the API; the "no shell" guarantee comes from `--tools ""`, not the sandbox). This is a deliberate, documented exception to the default SANDBOX_EXEC posture.

**Branch:** `feat/m4-llm-client` off `feat/m3-executor-sandbox` (stacked; retarget after M3 merges).

---

### Task 1: Branch, pydantic dep, llm package + core models

**Files:**
- Modify: `pyproject.toml`
- Create: `src/empiricist/llm/__init__.py`
- Create: `src/empiricist/llm/models.py`
- Test: `tests/test_llm_models.py`

- [ ] **Step 1: Branch** (the `feat/m4-llm-client` branch already exists — carved off `feat/m3-executor-sandbox` with this plan on it; just switch to it)

```bash
git switch feat/m4-llm-client
```

- [ ] **Step 2: Add pydantic** — in `pyproject.toml` dependencies:

```toml
dependencies = [
    "blake3>=1.0",
    "psutil>=6.0",
    "pydantic>=2.0",
]
```

- [ ] **Step 3: Write `src/empiricist/llm/__init__.py`**

```python
"""The LLM layer: Fable 5 driven as a structured-JSON role-sampler via Claude Code.

The model proposes structured artifacts and never executes anything (tools are
disabled; the harness verifies). Transport is injectable (LLMClient Protocol):
ClaudeCodeClient (default, runs `claude -p` through the executor) for production,
FakeLLMClient for deterministic offline tests, AnthropicAPIClient as a documented
metered-billing alternative for high fan-out.
"""
```

- [ ] **Step 4: Write the failing tests** — `tests/test_llm_models.py`:

```python
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
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `uv run pytest tests/test_llm_models.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 6: Write `src/empiricist/llm/models.py`**

```python
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
```

- [ ] **Step 7: Run tests to verify they pass** — `uv run pytest tests/test_llm_models.py -v` → PASS

- [ ] **Step 8: Lock, sync, commit**

```bash
uv lock && uv sync
git add pyproject.toml uv.lock src/empiricist/llm/__init__.py src/empiricist/llm/models.py tests/test_llm_models.py
git commit -m "feat: llm package skeleton, Effort + LLMResult models, pydantic dep"
```

---

### Task 2: Envelope parsing (`llm/parse.py`)

**Files:**
- Create: `src/empiricist/llm/parse.py`
- Test: `tests/test_llm_parse.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_llm_parse.py`. These use REAL captured envelope shapes:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail** — `uv run pytest tests/test_llm_parse.py -v` → `ModuleNotFoundError`

- [ ] **Step 3: Write `src/empiricist/llm/parse.py`**

```python
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
        text=env["result"],
        parsed=env.get("structured_output"),
        stop_reason=env["stop_reason"],
        is_error=bool(env.get("is_error", False)),
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
        cache_read_tokens=int(usage.get("cache_read_input_tokens", 0)),
        cache_creation_tokens=int(usage.get("cache_creation_input_tokens", 0)),
        cost_usd=float(env.get("total_cost_usd", 0.0)),
        duration_ms=int(env.get("duration_ms", 0)),
        session_id=env["session_id"],
        uuid=env.get("uuid", ""),
        model=model,
    )
```

- [ ] **Step 4: Run tests to verify they pass** — `uv run pytest tests/test_llm_parse.py -v` → PASS

- [ ] **Step 5: Commit**

```bash
git add src/empiricist/llm/parse.py tests/test_llm_parse.py
git commit -m "feat: claude envelope parser (real-envelope fixtures, refusal/error tolerant)"
```

---

### Task 3: Output schemas (`llm/schemas.py`)

**Files:**
- Create: `src/empiricist/llm/schemas.py`
- Test: `tests/test_llm_schemas.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_llm_schemas.py`:

```python
"""Tests for pydantic role-output schemas and their JSON-schema export."""

import pytest
from pydantic import ValidationError

from empiricist.llm.schemas import ConjectureOut, CritiqueOut, json_schema_for


def test_conjecture_out_validates_a_wellformed_object():
    obj = ConjectureOut(
        family="path", closed_form="N-3", predicted_values={"3": 0, "4": 1},
        confidence=0.7,
    )
    assert obj.family == "path" and obj.predicted_values["4"] == 1


def test_conjecture_out_rejects_missing_field():
    with pytest.raises(ValidationError):
        ConjectureOut(family="path", closed_form="N-3")  # missing predicted_values


def test_critique_out_gap_or_no_gap():
    gap = CritiqueOut(verdict="GAP", location="lemma 2, line 5",
                      detail="unjustified step", edges_checked=[])
    nogap = CritiqueOut(verdict="NO_GAP_FOUND", location=None, detail=None,
                        edges_checked=["l1->l2", "l2->l3"])
    assert gap.verdict == "GAP" and nogap.verdict == "NO_GAP_FOUND"


def test_critique_out_rejects_bad_verdict():
    with pytest.raises(ValidationError):
        CritiqueOut(verdict="MAYBE", location=None, detail=None, edges_checked=[])


def test_json_schema_for_produces_cli_ready_dict():
    schema = json_schema_for(ConjectureOut)
    assert schema["type"] == "object"
    assert "family" in schema["properties"]
    # additionalProperties must be false so the CLI enforces a closed shape.
    assert schema.get("additionalProperties") is False


def test_json_schema_is_json_serializable():
    import json
    json.dumps(json_schema_for(CritiqueOut))  # must not raise
```

- [ ] **Step 2: Run tests to verify they fail** — `uv run pytest tests/test_llm_schemas.py -v` → `ModuleNotFoundError`

- [ ] **Step 3: Write `src/empiricist/llm/schemas.py`**

```python
"""Pydantic output schemas per role + JSON-schema export for `--json-schema`.

Schemas guarantee SHAPE only, never mathematical truth (spec §5.2): a
schema-valid Conjecture can still be false — the verifiers decide truth.
Keep schemas free of numeric bounds / recursion (unsupported by the CLI
json-schema path); use additionalProperties:false for a closed shape.

Domain-specific schemas that belong to a problem (e.g. the P5 fusion
Construction) live with that problem's package; these are the cross-role
schemas the LLM layer needs to function and be tested.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class _Closed(BaseModel):
    """Base: forbid unspecified fields so the exported schema is closed."""

    model_config = ConfigDict(extra="forbid")


class ConjectureOut(_Closed):
    family: str
    closed_form: str
    predicted_values: dict[str, int]
    confidence: float


class CritiqueOut(_Closed):
    verdict: Literal["GAP", "NO_GAP_FOUND"]
    location: str | None
    detail: str | None
    edges_checked: list[str]


def json_schema_for(model: type[BaseModel]) -> dict[str, Any]:
    """The model's JSON schema, ready to pass to `claude --json-schema`.

    pydantic emits `additionalProperties: false` for extra='forbid' models,
    which is what makes the CLI enforce a closed object.
    """
    return model.model_json_schema()
```

- [ ] **Step 4: Run tests to verify they pass** — `uv run pytest tests/test_llm_schemas.py -v` → PASS

Note: if pydantic emits `additionalProperties: false` only implicitly, confirm the assertion holds; pydantic v2 with `extra="forbid"` sets it. If a `$defs`/`title` key appears, that's fine (the CLI tolerates extra schema keys) — the test only checks the load-bearing fields.

- [ ] **Step 5: Commit**

```bash
git add src/empiricist/llm/schemas.py tests/test_llm_schemas.py
git commit -m "feat: pydantic role-output schemas + CLI json-schema export"
```

---

### Task 4: Roles (`llm/roles.py`)

**Files:**
- Create: `src/empiricist/llm/roles.py`
- Test: `tests/test_llm_roles.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_llm_roles.py`:

```python
"""Tests for the seven role definitions and their sampling policy (spec §5.4)."""

from empiricist.llm.models import Effort
from empiricist.llm.roles import ROLES, Role, active_roles


def test_all_seven_roles_present():
    assert set(ROLES) == {
        "prospector", "toolwright", "searcher", "conjecturer",
        "prover", "critic", "formalizer",
    }


def test_roles_are_frozen():
    import dataclasses
    import pytest
    r = ROLES["searcher"]
    assert dataclasses.is_dataclass(r)
    with pytest.raises(AttributeError):
        r.k = 99  # type: ignore[misc]


def test_effort_matches_spec_table():
    assert ROLES["searcher"].effort is Effort.LOW
    assert ROLES["conjecturer"].effort is Effort.MEDIUM
    assert ROLES["prover"].effort is Effort.MAX
    assert ROLES["critic"].effort is Effort.MAX
    assert ROLES["formalizer"].effort is Effort.HIGH


def test_sampling_counts_match_spec():
    assert ROLES["searcher"].k >= 16      # k=16..64 wave
    assert ROLES["critic"].k == 2         # two independent critics
    assert ROLES["prover"].k == 1
    assert ROLES["conjecturer"].k >= 4


def test_active_roles_excludes_v0_stubs():
    """Prospector + Toolwright are deferred stubs in v0 (spec D11)."""
    names = {r.name for r in active_roles()}
    assert "prospector" not in names and "toolwright" not in names
    assert {"searcher", "conjecturer", "prover", "critic", "formalizer"} <= names


def test_every_role_has_a_nonempty_system_prompt():
    for r in ROLES.values():
        assert isinstance(r.system_prompt, str) and len(r.system_prompt) > 20


def test_role_has_model_default_fable5():
    assert ROLES["searcher"].model == "claude-fable-5"
```

- [ ] **Step 2: Run tests to verify they fail** — `uv run pytest tests/test_llm_roles.py -v` → `ModuleNotFoundError`

- [ ] **Step 3: Write `src/empiricist/llm/roles.py`**

```python
"""The seven roles (spec §5.4): each a system prompt + sampling policy.

A Role is the frozen policy for one kind of model call. The system_prompt here
is the ROLE CARD; the Context Builder (a later milestone) prepends the frozen
problem spec + verified dependencies to form the full system prompt. Diversity
in SEARCH waves comes from prompt/nonce variation, never temperature (Fable 5
exposes none). v0-active vs deferred-stub is per spec D11.
"""

from __future__ import annotations

from dataclasses import dataclass

from empiricist.llm.models import Effort

_MODEL = "claude-fable-5"


@dataclass(frozen=True)
class Role:
    name: str
    system_prompt: str          # the role card (spec-block prepended later)
    effort: Effort
    k: int                      # samples per invocation (wave size)
    active: bool                # False = deferred v0 stub (spec D11)
    model: str = _MODEL


ROLES: dict[str, Role] = {
    "prospector": Role(
        name="prospector",
        system_prompt=(
            "You are the Prospector. Report prior art on the given problem. "
            "Every claim about the literature is EXTERNAL and must cite a source; "
            "you never assert a mathematical fact as established. Output the "
            "external_claims schema."
        ),
        effort=Effort.MEDIUM, k=1, active=False,
    ),
    "toolwright": Role(
        name="toolwright",
        system_prompt=(
            "You are the Toolwright. Write verifier/enumerator code with tests. "
            "Output the code_artifact schema. Your code is never trusted until it "
            "passes its golden suite and is certified by the harness."
        ),
        effort=Effort.HIGH, k=1, active=False,
    ),
    "searcher": Role(
        name="searcher",
        system_prompt=(
            "You are the Searcher. Propose one concrete candidate construction for "
            "the stated objective, in the required canonical form. Favor diversity: "
            "the nonce in your prompt distinguishes your attempt from parallel ones. "
            "Do not explain; emit only the schema."
        ),
        effort=Effort.LOW, k=32, active=True,
    ),
    "conjecturer": Role(
        name="conjecturer",
        system_prompt=(
            "You are the Conjecturer. Given a VERIFIED_N dataset, propose a precise "
            "closed-form statement for a named family and predict its values. State "
            "nothing you cannot check against the data. Output the conjecture schema."
        ),
        effort=Effort.MEDIUM, k=8, active=True,
    ),
    "prover": Role(
        name="prover",
        system_prompt=(
            "You are the Prover. Produce a lemma-DAG proof of the frozen statement: "
            "each lemma separately stated with its dependencies. No prose proof; a "
            "structured DAG whose every edge is independently checkable."
        ),
        effort=Effort.MAX, k=1, active=True,
    ),
    "critic": Role(
        name="critic",
        system_prompt=(
            "You are the Critic. You receive a lemma DAG and have no stake in its "
            "correctness. Your only win is a concrete defect: a false lemma (give a "
            "counterexample), an inferential gap (name lemma+line+missing step), or a "
            "definition mismatch. 'Looks correct' is a failure unless you checked "
            "every edge; then emit NO_GAP_FOUND with the edges checked. Never propose "
            "fixes. Output the critique schema."
        ),
        effort=Effort.MAX, k=2, active=True,
    ),
    "formalizer": Role(
        name="formalizer",
        system_prompt=(
            "You are the Formalizer. Emit a Lean 4 module (statement, then proof) "
            "against pinned mathlib, iterating on compiler feedback. Output the "
            "lean_module schema. sorry and native_decide are forbidden."
        ),
        effort=Effort.HIGH, k=1, active=True,
    ),
}


def active_roles() -> list[Role]:
    """Roles exercised in v0 (Prospector + Toolwright are deferred stubs, D11)."""
    return [r for r in ROLES.values() if r.active]
```

- [ ] **Step 4: Run tests to verify they pass** — `uv run pytest tests/test_llm_roles.py -v` → PASS

- [ ] **Step 5: Commit**

```bash
git add src/empiricist/llm/roles.py tests/test_llm_roles.py
git commit -m "feat: seven role definitions with per-role effort + sampling policy"
```

---

### Task 5: The client (`llm/client.py`)

**Files:**
- Create: `src/empiricist/llm/client.py`
- Create: `tests/stub_claude.py` (a fake `claude` binary for deterministic tests)
- Test: `tests/test_llm_client.py`

- [ ] **Step 1: Write the stub binary** — `tests/stub_claude.py`:

```python
#!/usr/bin/env python3
"""A fake `claude` binary for deterministic client tests — no network, no cost.

Emits a canned result envelope on stdout. Behavior is controlled by env vars:
  STUB_MODE = success | schema | refusal | crash   (default: success)
It also echoes its argv to STUB_ARGV_FILE (if set) so tests can assert how the
client invoked it. This exercises the full execute() -> parse path.
"""

import json
import os
import sys

if (argv_file := os.environ.get("STUB_ARGV_FILE")):
    with open(argv_file, "w") as f:
        json.dump(sys.argv[1:], f)

mode = os.environ.get("STUB_MODE", "success")

if mode == "crash":
    sys.stderr.write("stub crash\n")
    sys.exit(2)

env = {
    "type": "result", "is_error": False, "duration_ms": 5,
    "session_id": "stub-session", "uuid": "stub-uuid", "total_cost_usd": 0.001,
    "usage": {"input_tokens": 30, "output_tokens": 5, "cache_read_input_tokens": 0,
              "cache_creation_input_tokens": 600},
    "modelUsage": {"claude-fable-5": {"inputTokens": 30, "outputTokens": 5}},
}
if mode == "success":
    env |= {"result": "stub text answer", "stop_reason": "end_turn"}
elif mode == "schema":
    env |= {"result": "{\"family\":\"path\",\"closed_form\":\"N-3\","
                       "\"predicted_values\":{\"3\":0},\"confidence\":0.9}",
            "stop_reason": "tool_use",
            "structured_output": {"family": "path", "closed_form": "N-3",
                                  "predicted_values": {"3": 0}, "confidence": 0.9}}
elif mode == "refusal":
    env |= {"result": "", "stop_reason": "refusal"}

sys.stdout.write(json.dumps(env))
sys.exit(0)
```

- [ ] **Step 2: Write the failing tests** — `tests/test_llm_client.py`:

```python
"""Tests for the LLMClient implementations.

ClaudeCodeClient is exercised against a STUB `claude` binary (tests/stub_claude.py)
so the full argv-build -> execute() -> parse path runs deterministically with no
network and no cost. Exactly one REAL model call exists in the milestone, in the
Task 6 live smoke — never in the unit suite.
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest

from empiricist.ledger.db import Ledger
from empiricist.llm.client import ClaudeCodeClient, FakeLLMClient
from empiricist.llm.models import Effort, LLMResult
from empiricist.llm.roles import ROLES
from empiricist.llm.schemas import ConjectureOut

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
    c = stub_client()
    r = run(c.complete(ROLES["searcher"], "prompt", session_id="s5",
                       run_id="run5", ledger=lg))
    row = lg.get_run("run5")
    assert row.role == "searcher" and row.model == "claude-fable-5"
    assert row.tokens_in == 30 and row.tokens_out == 5           # from the envelope
    assert row.cost_usd == pytest.approx(0.001) and row.ended is not None
    assert row.exit_code == 0
    assert r.ok
    lg.close()


def test_complete_crash_records_failure_row_and_flags_not_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "crash")
    lg = Ledger(tmp_path / "ledger.db")
    c = stub_client()
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
```

- [ ] **Step 3: Run tests to verify they fail** — `uv run pytest tests/test_llm_client.py -v` → `ModuleNotFoundError`

- [ ] **Step 4: Write `src/empiricist/llm/client.py`**

```python
"""LLMClient implementations.

ClaudeCodeClient is the default transport: it builds a `claude -p` argv (cost
recipe: replaced system prompt + dropped setting-sources; tools disabled; JSON
output; per-role effort), runs it THROUGH executor.runner.execute() so the model
call is a provenance-recorded, resource-bounded subprocess (the "one audited
path"), parses the envelope, and — if a ledger is given — records a single
complete runs row with full token/cost accounting (execute() itself is run with
ledger=None so there is exactly one row, the richer one).

The model call is the sole legitimate network user, so it runs sandbox=NONE; the
"model never gets a shell" guarantee comes from `--tools ""`, not the sandbox.

FakeLLMClient returns scripted results for offline/deterministic downstream tests.
AnthropicAPIClient is a documented metered-billing alternative (stub in v0).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any, Protocol

from pydantic import BaseModel

from empiricist.executor.runner import ExecSpec, execute
from empiricist.executor.sandbox import SandboxMode
from empiricist.ledger.db import Ledger, RunAlreadyFinishedError
from empiricist.ledger.models import Run, now_iso
from empiricist.llm.models import LLMResult
from empiricist.llm.parse import LLMParseError, parse_envelope
from empiricist.llm.roles import Role
from empiricist.llm.schemas import json_schema_for


class LLMClient(Protocol):
    async def complete(
        self, role: Role, prompt: str, *, session_id: str,
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
    ) -> None:
        self._bin = list(claude_bin) if claude_bin else ["claude"]
        self._sem = asyncio.Semaphore(max_concurrency)
        self._timeout_s = timeout_s

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
        self, role: Role, prompt: str, *, session_id: str,
        system_prompt: str | None = None,
        schema: type[BaseModel] | None = None,
        run_id: str | None = None, ledger: Ledger | None = None,
    ) -> LLMResult | None:
        sys_prompt = system_prompt if system_prompt is not None else role.system_prompt
        schema_dict = json_schema_for(schema) if schema is not None else None
        argv = self.build_argv(
            role, prompt, session_id=session_id, system_prompt=sys_prompt,
            schema=schema_dict,
        )
        started = now_iso()
        rid = run_id or f"sample-{session_id}"
        # Open the runs row BEFORE the call so an in-flight harness crash leaves an
        # orphan row (reconcile_orphans closes it) rather than losing the call
        # silently. execute() runs with ledger=None so there is exactly one row —
        # this richer one, with the token/cost accounting the executor cannot see.
        if ledger is not None:
            ledger.start_run(Run(
                run_id=rid, move="SAMPLE", role=role.name, model=role.model,
                started=started,
            ))
        try:
            async with self._sem:
                res = await execute(
                    ExecSpec(
                        argv=argv, move="SAMPLE", role=role.name,
                        sandbox=SandboxMode.NONE, timeout_s=self._timeout_s,
                    ),
                    ledger=None,
                )
        except BaseException:
            if ledger is not None:
                with contextlib.suppress(RunAlreadyFinishedError, KeyError):
                    ledger.finish_run(rid, exit_code=-998, wall_s=0.0)
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
                role, p, session_id=f"{role.name}-{i}", schema=schema,
                run_id=f"{role.name}-wave-{i}" if ledger else None, ledger=ledger,
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
        self, role: Role, prompt: str, *, session_id: str,
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
```

- [ ] **Step 5: Run tests to verify they pass** — `uv run pytest tests/test_llm_client.py -v` → PASS. (`tests/stub_claude.py` is a helper, not a test module; if pytest tries to collect it, add it to `norecursedirs`/`collect_ignore` or ensure it has no `test_` functions — it doesn't, so it's ignored.)

- [ ] **Step 6: Full suite + lint**

Run: `uv run pytest && uv run ruff check src tests`
Expected: all prior + new tests pass, lint clean.

- [ ] **Step 7: Commit**

```bash
git add src/empiricist/llm/client.py tests/stub_claude.py tests/test_llm_client.py
git commit -m "feat: ClaudeCodeClient (via executor) + FakeLLMClient + API stub"
```

---

### Task 6: Preflight + live smoke + closeout

**Files:**
- Create: `src/empiricist/llm/preflight.py`
- Test: `tests/test_llm_preflight.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_llm_preflight.py` (against the stub, no network):

```python
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
```

- [ ] **Step 2: Run to verify fail** — `uv run pytest tests/test_llm_preflight.py -v` → `ModuleNotFoundError`

- [ ] **Step 3: Write `src/empiricist/llm/preflight.py`**

```python
"""Startup preflight: confirm the model resolves and auth is live (spec §5.3).

One cheap real call ("reply ok"). On the Claude Code subscription path this
catches an unavailable model or a broken login before a campaign starts. (ZDR
is an API-org concern, not the subscription path — relevant only to
AnthropicAPIClient.) Rate-limit / sustained-k probing is a separate, optional
concern deferred to the scheduler.
"""

from __future__ import annotations

from dataclasses import dataclass

from empiricist.llm.roles import Role
from empiricist.llm.models import Effort

_PREFLIGHT_ROLE = Role(
    name="preflight",
    system_prompt="You are a health check. Reply with exactly: ok",
    effort=Effort.LOW, k=1, active=False,
)


class PreflightError(Exception):
    pass


@dataclass(frozen=True)
class PreflightReport:
    model_ok: bool
    cost_usd: float
    session_id: str


async def preflight(client) -> PreflightReport:
    """Run one trivial call; raise PreflightError if the model/auth is unhealthy."""
    result = await client.complete(
        _PREFLIGHT_ROLE, "Reply with exactly: ok", session_id="preflight",
    )
    if result is None or not result.ok:
        raise PreflightError(
            "preflight call did not return a usable response "
            f"(result={'None' if result is None else result.stop_reason})"
        )
    return PreflightReport(
        model_ok=True, cost_usd=result.cost_usd, session_id=result.session_id,
    )
```

- [ ] **Step 4: Run to verify pass** — `uv run pytest tests/test_llm_preflight.py -v` → PASS

- [ ] **Step 5: Full suite + lint** — `uv run pytest && uv run ruff check src tests` → all green, clean.

- [ ] **Step 6: LIVE smoke test (manual, one real Fable-5 call, ~$0.015)**

```bash
uv run python - <<'EOF'
import asyncio
from empiricist.llm.client import ClaudeCodeClient
from empiricist.llm.preflight import preflight
from empiricist.llm.roles import ROLES
from empiricist.llm.schemas import ConjectureOut

async def main():
    c = ClaudeCodeClient()  # real `claude` on PATH
    rep = await preflight(c)
    print("preflight OK:", rep)
    # a real schema-constrained call
    r = await c.complete(
        ROLES["conjecturer"],
        "The dataset is F(path_N)=N-3 for N=3..8. Conjecture the closed form for the path family.",
        session_id="live-smoke-1", schema=ConjectureOut,
    )
    print("live result ok:", r.ok, "parsed:", r.parsed, "cost:", r.cost_usd)
    assert r.ok and r.parsed is not None and r.parsed["family"]
    print("LIVE SMOKE OK")

asyncio.run(main())
EOF
```

Expected: prints `preflight OK`, a parsed ConjectureOut object, and `LIVE SMOKE OK`. Cost should be a couple cents total (verifying the cost recipe holds end-to-end). If it prints a much higher cost (e.g. >$0.10), the `--setting-sources ""` / `--system-prompt` cost recipe regressed — report it rather than proceeding.

- [ ] **Step 7: Push + PR**

```bash
git push -u origin feat/m4-llm-client
env -u GH_TOKEN -u GITHUB_TOKEN gh pr create --base feat/m3-executor-sandbox --head feat/m4-llm-client \
  --title "M4: LLM layer (Claude Code transport)" --body "<summary>"
```

---

## Plan self-review (done at write time)

- **Spec coverage (§5/D2):** LLMClient protocol + 3 impls ✅ (T5); 7 roles w/ effort+sampling ✅ (T3); structured output via --json-schema + pydantic ✅ (T3,T5); envelope parse w/ usage/cost ✅ (T2); cost recipe (system-prompt + setting-sources) ✅ (T5, verified live); model-never-shells (--tools "") ✅ (T5); runs-row provenance for every call ✅ (T5); preflight ✅ (T6); fresh session per call + prompt-diversity ✅ (T5); sandbox=NONE documented exception ✅ (T5). Deferred w/ contract: AnthropicAPIClient (stub), sustained-k probe (scheduler), context-builder spec-prepend (later milestone — Role carries the role card, client accepts system_prompt override).
- **Placeholder scan:** none. Every step has code/commands.
- **Type consistency:** `Effort`/`LLMResult` (T1) ↔ parse (T2) ↔ client (T5); `Role` fields (T3) ↔ client build_argv/complete (T5) ↔ preflight (T6); `ExecSpec(argv,move,role,sandbox,timeout_s)` + `ExecResult(stdout,exit_code,wall_s,peak_rss_mb)` match the landed M3 runner; `Ledger.start_run/finish_run` + `Run` fields + `RunAlreadyFinishedError` match landed M1-2; `json_schema_for` (T3) ↔ client (T5).
- **Judgment calls for reviewers:** the client records its OWN runs row (execute ledger=None) because it has token/cost the executor can't see — one row, richer. Model call uses sandbox=NONE (network needed; no-shell via --tools ""). The stub-binary pattern gives full-path determinism without network/cost; exactly one real call (T6 live smoke) validates the cost recipe end-to-end.

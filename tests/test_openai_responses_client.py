"""Offline contract tests for the tool-free GPT-5.6 Responses adapter."""

from __future__ import annotations

import asyncio
import json

import pytest

from empiricist.ledger.db import UNKNOWN_BILLING_EXIT_CODE, Ledger
from empiricist.llm.models import BillingUnknownError
from empiricist.llm.openai_responses import (
    OpenAIAuthError,
    OpenAIClientError,
    OpenAIPricing,
    OpenAIResponsesClient,
    OpenAITransportError,
)
from empiricist.llm.roles import ROLES
from empiricist.llm.schemas import BellSchemeOut, ConjectureOut
from empiricist.store import Store


def _completed_response(text: str) -> dict:
    return {
        "id": "resp_test",
        "status": "completed",
        "model": "gpt-5.6-sol",
        "service_tier": "default",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
        "usage": {
            "input_tokens": 100,
            "output_tokens": 25,
            "input_tokens_details": {
                "cached_tokens": 20,
                "cache_write_tokens": 0,
            },
            "output_tokens_details": {"reasoning_tokens": 10},
        },
    }


class StubTransport:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, str], dict, float]] = []

    async def post_json(self, url, headers, payload, *, timeout_s):
        self.calls.append((url, headers, payload, timeout_s))
        return self.response


def _run(awaitable):
    return asyncio.run(awaitable)


def test_pro_mode_request_is_tool_free_and_uses_strict_structured_output():
    transport = StubTransport(
        _completed_response(
            json.dumps(
                {
                    "family": "path",
                    "closed_form": "N-3",
                    "predicted_values": [{"key": "3", "value": 0}],
                    "confidence": 0.9,
                }
            )
        )
    )
    client = OpenAIResponsesClient(api_key="test-key", transport=transport)

    result = _run(
        client.complete(
            ROLES["conjecturer"],
            "Find the pattern.",
            system_prompt="ROLE CARD",
            schema=ConjectureOut,
        )
    )

    assert result is not None and result.ok and result.has_artifact
    assert result.parsed["family"] == "path"
    assert result.model == "gpt-5.6-sol"

    url, headers, payload, timeout_s = transport.calls[0]
    assert url == "https://api.openai.com/v1/responses"
    assert headers["Authorization"] == "Bearer test-key"
    assert timeout_s == pytest.approx(900.0)
    assert payload["model"] == "gpt-5.6-sol"
    assert payload["store"] is False
    assert payload["service_tier"] == "default"
    assert payload["reasoning"] == {"mode": "pro", "effort": "medium"}
    assert payload["tools"] == []
    assert payload["tool_choice"] == "none"
    assert payload["parallel_tool_calls"] is False
    assert payload["instructions"] == "ROLE CARD"
    assert payload["input"] == [{"role": "user", "content": "Find the pattern."}]
    fmt = payload["text"]["format"]
    assert fmt["type"] == "json_schema" and fmt["strict"] is True
    predicted = fmt["schema"]["properties"]["predicted_values"]
    assert predicted["type"] == "array"
    assert predicted["items"]["additionalProperties"] is False
    assert set(predicted["items"]["required"]) == {"key", "value"}


def test_openai_schema_adapter_requires_defaulted_fields_recursively():
    transport = StubTransport(_completed_response("{}"))
    client = OpenAIResponsesClient(api_key="test-key", transport=transport)

    _run(client.complete(ROLES["p3_searcher"], "p", schema=BellSchemeOut))

    schema = transport.calls[0][2]["text"]["format"]["schema"]
    assert set(schema["required"]) == set(schema["properties"])
    mesh = schema["$defs"]["MeshElement"]
    assert set(mesh["required"]) == set(mesh["properties"])
    assert "default" not in json.dumps(schema)

    def assert_all_objects_closed(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
                assert set(node.get("required") or ()) == set(node.get("properties") or ())
            for child in node.values():
                assert_all_objects_closed(child)
        elif isinstance(node, list):
            for child in node:
                assert_all_objects_closed(child)

    assert_all_objects_closed(schema)


def test_usage_and_configured_pricing_are_normalized():
    response = _completed_response("plain answer")
    response["usage"]["input_tokens_details"]["cache_write_tokens"] = 10
    transport = StubTransport(response)
    pricing = OpenAIPricing(
        input_usd_per_mtok=10.0,
        cached_input_usd_per_mtok=1.0,
        output_usd_per_mtok=20.0,
    )
    client = OpenAIResponsesClient(
        api_key="test-key", transport=transport, pricing=pricing
    )

    result = _run(client.complete(ROLES["searcher"], "p"))

    assert result is not None
    assert result.input_tokens == 100
    assert result.cache_read_tokens == 20
    assert result.cache_creation_tokens == 10
    assert result.output_tokens == 25
    # 70 uncached * $10/M + 20 cached * $1/M + 10 writes * $12.50/M
    # + 25 output * $20/M.
    assert result.cost_usd == pytest.approx(0.001345)


def test_pricing_applies_gpt56_long_context_surcharge():
    pricing = OpenAIPricing(10.0, 1.0, 20.0)
    assert pricing.estimate(
        input_tokens=300_000,
        cached_input_tokens=0,
        cache_write_tokens=0,
        output_tokens=100,
    ) == pytest.approx(6.003)


@pytest.mark.parametrize("bad_rate", [float("nan"), float("inf"), -1.0, 0.0])
def test_pricing_rejects_nonfinite_or_nonpositive_rates(bad_rate):
    with pytest.raises(ValueError):
        OpenAIPricing(bad_rate, 1.0, 20.0)


@pytest.mark.parametrize("model", ["gpt-5.5", "gpt-5.6-preview", "gpt-5.6"])
def test_only_confirmed_gpt56_sol_model_id_is_accepted(model):
    with pytest.raises(ValueError, match="unsupported OpenAI model"):
        OpenAIResponsesClient(
            api_key="test-key",
            model=model,
            pricing=OpenAIPricing(10.0, 1.0, 20.0),
        )


def test_refusal_and_incomplete_responses_are_not_usable():
    refusal = _completed_response("")
    refusal["output"][0]["content"] = [
        {"type": "refusal", "refusal": "cannot comply"}
    ]
    refused = _run(
        OpenAIResponsesClient(
            api_key="test-key", transport=StubTransport(refusal)
        ).complete(ROLES["searcher"], "p")
    )
    assert refused is not None
    assert refused.ok is False
    assert refused.stop_reason == "refusal"
    assert refused.parsed is None

    incomplete = _completed_response("")
    incomplete["status"] = "incomplete"
    incomplete["incomplete_details"] = {"reason": "max_output_tokens"}
    partial = _run(
        OpenAIResponsesClient(
            api_key="test-key", transport=StubTransport(incomplete)
        ).complete(ROLES["searcher"], "p")
    )
    assert partial is not None
    assert partial.ok is False
    assert partial.stop_reason == "max_output_tokens"


def test_unexpected_tool_call_is_rejected_even_with_message_text():
    response = _completed_response("answer")
    response["output"].insert(0, {"type": "function_call", "name": "shell"})
    result = _run(
        OpenAIResponsesClient(
            api_key="test-key", transport=StubTransport(response)
        ).complete(ROLES["searcher"], "p")
    )
    assert result is not None and not result.ok
    assert result.stop_reason == "unexpected_tool_call"


def test_allowlisted_reasoning_item_is_accepted_with_message_text():
    response = _completed_response("answer")
    response["output"].insert(
        0,
        {"type": "reasoning", "summary": [{"type": "summary_text", "text": "..."}]},
    )
    result = _run(
        OpenAIResponsesClient(
            api_key="test-key", transport=StubTransport(response)
        ).complete(ROLES["searcher"], "p")
    )
    assert result is not None and result.ok


def test_unknown_output_item_is_rejected_even_with_message_text():
    response = _completed_response("answer")
    response["output"].insert(0, {"type": "future_model_event"})
    result = _run(
        OpenAIResponsesClient(
            api_key="test-key", transport=StubTransport(response)
        ).complete(ROLES["searcher"], "p")
    )
    assert result is not None and not result.ok
    assert result.stop_reason == "unexpected_output_item"


def test_unknown_message_content_is_rejected_even_with_output_text():
    response = _completed_response("answer")
    response["output"][0]["content"].insert(
        0, {"type": "future_content", "value": "ignored"}
    )
    result = _run(
        OpenAIResponsesClient(
            api_key="test-key", transport=StubTransport(response)
        ).complete(ROLES["searcher"], "p")
    )
    assert result is not None and not result.ok
    assert result.stop_reason == "unexpected_output_content"


def test_future_call_shaped_output_keeps_unexpected_tool_call_semantics():
    response = _completed_response("answer")
    response["output"].insert(0, {"type": "future_tool_call"})
    result = _run(
        OpenAIResponsesClient(
            api_key="test-key", transport=StubTransport(response)
        ).complete(ROLES["searcher"], "p")
    )
    assert result is not None and not result.ok
    assert result.stop_reason == "unexpected_tool_call"


def test_missing_api_key_fails_before_transport(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    transport = StubTransport(_completed_response("should not run"))
    client = OpenAIResponsesClient(api_key=None, transport=transport)

    with pytest.raises(OpenAIAuthError, match="OPENAI_API_KEY"):
        _run(client.complete(ROLES["searcher"], "p"))
    assert transport.calls == []


def test_model_request_and_response_are_cas_backed_and_linked_to_run(tmp_path):
    ledger = Ledger(tmp_path / "ledger.db")
    store = Store(tmp_path / "store")
    transport = StubTransport(_completed_response("answer"))
    client = OpenAIResponsesClient(
        api_key="test-key",
        transport=transport,
        store=store,
        pricing=OpenAIPricing(10.0, 1.0, 20.0),
    )
    try:
        result = _run(
            client.complete(
                ROLES["prover"], "prove it", run_id="openai-r1", ledger=ledger
            )
        )
        assert result is not None and result.ok

        run = ledger.get_run("openai-r1")
        assert run.provider == "openai"
        assert run.auth_route == "api_key"
        assert run.reasoning_mode == "pro"
        assert run.reasoning_effort == "max"
        assert run.request_digest and store.exists(run.request_digest)
        assert run.response_digest and store.exists(run.response_digest)
        assert run.config_hash and store.exists(run.config_hash)
        request_receipt = json.loads(store.get(run.request_digest))
        assert request_receipt["model"] == "gpt-5.6-sol"
        assert "test-key" not in store.get(run.request_digest).decode()
        config_receipt = json.loads(store.get(run.config_hash))
        assert config_receipt["endpoint"] == "https://api.openai.com/v1/responses"
        assert config_receipt["billing_rules"]["cache_write_input_multiplier"] == 1.25
    finally:
        ledger.close()


def test_ledger_calls_require_retrievable_receipts_and_known_pricing(tmp_path):
    ledger = Ledger(tmp_path / "ledger.db")
    transport = StubTransport(_completed_response("answer"))
    try:
        with pytest.raises(OpenAIClientError, match="Store"):
            _run(
                OpenAIResponsesClient(
                    api_key="test-key",
                    transport=transport,
                    pricing=OpenAIPricing(10.0, 1.0, 20.0),
                ).complete(ROLES["searcher"], "p", ledger=ledger)
            )
        with pytest.raises(OpenAIClientError, match="pricing"):
            _run(
                OpenAIResponsesClient(
                    api_key="test-key",
                    transport=transport,
                    store=Store(tmp_path / "store"),
                ).complete(ROLES["searcher"], "p", ledger=ledger)
            )
        assert transport.calls == []
        assert ledger.conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
    finally:
        ledger.close()


def test_post_response_parse_failure_marks_billing_unknown_with_receipt(tmp_path):
    response = _completed_response("answer")
    response["usage"]["input_tokens"] = "not-an-integer"
    ledger = Ledger(tmp_path / "ledger.db")
    store = Store(tmp_path / "store")
    client = OpenAIResponsesClient(
        api_key="test-key",
        transport=StubTransport(response),
        store=store,
        pricing=OpenAIPricing(10.0, 1.0, 20.0),
    )
    try:
        with pytest.raises(BillingUnknownError):
            _run(client.complete(
                ROLES["searcher"], "p", run_id="bad-usage", ledger=ledger
            ))
        run = ledger.get_run("bad-usage")
        assert run.ended is not None and run.exit_code == UNKNOWN_BILLING_EXIT_CODE
        assert run.response_digest and store.exists(run.response_digest)
    finally:
        ledger.close()


def test_unexpected_reported_service_tier_fails_closed_with_receipt(tmp_path):
    response = _completed_response("answer")
    response["service_tier"] = "priority"
    ledger = Ledger(tmp_path / "ledger.db")
    store = Store(tmp_path / "store")
    client = OpenAIResponsesClient(
        api_key="test-key",
        transport=StubTransport(response),
        store=store,
        pricing=OpenAIPricing(10.0, 1.0, 20.0),
    )
    try:
        with pytest.raises(BillingUnknownError):
            _run(client.complete(
                ROLES["searcher"], "p", run_id="wrong-tier", ledger=ledger
            ))
        run = ledger.get_run("wrong-tier")
        assert run.ended is not None
        assert run.exit_code == UNKNOWN_BILLING_EXIT_CODE
        assert run.response_digest and store.exists(run.response_digest)
        assert json.loads(store.get(run.response_digest))["service_tier"] == "priority"
    finally:
        ledger.close()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda response: response.pop("usage"),
        lambda response: response["usage"].__setitem__("input_tokens", -1),
        lambda response: response["usage"]["input_tokens_details"].__setitem__(
            "cached_tokens", 101
        ),
        lambda response: response["usage"]["input_tokens_details"].pop(
            "cache_write_tokens"
        ),
    ],
    ids=("missing-usage", "negative-total", "subcount-over-total", "missing-write"),
)
def test_malformed_usage_is_fatal_unknown_billing(tmp_path, mutate):
    response = _completed_response("answer")
    mutate(response)
    ledger = Ledger(tmp_path / "ledger.db")
    store = Store(tmp_path / "store")
    client = OpenAIResponsesClient(
        api_key="test-key",
        transport=StubTransport(response),
        store=store,
        pricing=OpenAIPricing(10.0, 1.0, 20.0),
    )
    try:
        with pytest.raises(BillingUnknownError):
            _run(client.complete(
                ROLES["searcher"], "p", run_id="malformed-usage", ledger=ledger
            ))
        run = ledger.get_run("malformed-usage")
        assert run.exit_code == UNKNOWN_BILLING_EXIT_CODE
        assert run.response_digest and store.exists(run.response_digest)
    finally:
        ledger.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("model", None),
        ("model", "gpt-5.6-other"),
        ("service_tier", None),
        ("service_tier", "priority"),
    ],
)
def test_missing_or_mismatched_billing_identity_is_fatal(tmp_path, field, value):
    response = _completed_response("answer")
    if value is None:
        response.pop(field)
    else:
        response[field] = value
    ledger = Ledger(tmp_path / "ledger.db")
    store = Store(tmp_path / "store")
    client = OpenAIResponsesClient(
        api_key="test-key",
        transport=StubTransport(response),
        store=store,
        pricing=OpenAIPricing(10.0, 1.0, 20.0),
    )
    try:
        with pytest.raises(BillingUnknownError):
            _run(client.complete(
                ROLES["searcher"], "p", run_id="billing-identity", ledger=ledger
            ))
        assert (
            ledger.get_run("billing-identity").exit_code
            == UNKNOWN_BILLING_EXIT_CODE
        )
    finally:
        ledger.close()


def test_transport_error_body_is_receipted_and_run_is_closed(tmp_path):
    class FailingTransport:
        async def post_json(self, *args, **kwargs):
            raise OpenAITransportError(
                "HTTP 429",
                receipt=b'{"body":"rate limited","kind":"http_error","status":429}',
            )

    ledger = Ledger(tmp_path / "ledger.db")
    store = Store(tmp_path / "store")
    client = OpenAIResponsesClient(
        api_key="test-key",
        transport=FailingTransport(),
        store=store,
        pricing=OpenAIPricing(10.0, 1.0, 20.0),
    )
    try:
        with pytest.raises(OpenAITransportError):
            _run(client.complete(
                ROLES["searcher"], "p", run_id="http-fail", ledger=ledger
            ))
        run = ledger.get_run("http-fail")
        assert run.ended is not None and run.exit_code == 1
        receipt = json.loads(store.get(run.response_digest))
        assert receipt["status"] == 429
    finally:
        ledger.close()


def test_ambiguous_transport_failure_marks_billing_unknown(tmp_path):
    class FailingTransport:
        async def post_json(self, *args, **kwargs):
            raise OpenAITransportError(
                "connection dropped after send",
                billing_unknown=True,
                receipt=b'{"kind":"transport_error"}',
            )

    ledger = Ledger(tmp_path / "ledger.db")
    store = Store(tmp_path / "store")
    client = OpenAIResponsesClient(
        api_key="test-key",
        transport=FailingTransport(),
        store=store,
        pricing=OpenAIPricing(10.0, 1.0, 20.0),
    )
    try:
        with pytest.raises(BillingUnknownError):
            _run(client.complete(
                ROLES["searcher"], "p", run_id="billing-unknown", ledger=ledger
            ))
        run = ledger.get_run("billing-unknown")
        assert run.ended is not None
        assert run.exit_code == UNKNOWN_BILLING_EXIT_CODE
        assert run.response_digest and store.exists(run.response_digest)
    finally:
        ledger.close()


def test_complete_many_receipts_all_siblings_before_raising_unknown_billing(tmp_path):
    class MixedTransport:
        def __init__(self):
            self.calls = 0

        async def post_json(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise OpenAITransportError(
                    "connection dropped after send",
                    billing_unknown=True,
                    receipt=b'{"kind":"transport_error"}',
                )
            await asyncio.sleep(0)
            return _completed_response("answer")

    ledger = Ledger(tmp_path / "ledger.db")
    store = Store(tmp_path / "store")
    transport = MixedTransport()
    client = OpenAIResponsesClient(
        api_key="test-key",
        transport=transport,
        store=store,
        pricing=OpenAIPricing(10.0, 1.0, 20.0),
        max_concurrency=1,
    )
    try:
        with pytest.raises(BillingUnknownError):
            _run(client.complete_many(
                ROLES["searcher"],
                [f"prompt-{index}" for index in range(10)],
                ledger=ledger,
            ))
        runs = ledger.conn.execute(
            "SELECT ended, exit_code, response_digest FROM runs ORDER BY rowid"
        ).fetchall()
        assert len(runs) == 10
        assert all(row["ended"] is not None for row in runs)
        assert UNKNOWN_BILLING_EXIT_CODE in {
            row["exit_code"] for row in runs
        }
        assert all(row["response_digest"] for row in runs)
        assert transport.calls < 10
    finally:
        ledger.close()


def test_cancellation_waits_for_and_receipts_inflight_paid_response(tmp_path):
    class ControlledTransport:
        def __init__(self):
            self.started = asyncio.Event()
            self.release = asyncio.Event()

        async def post_json(self, *args, **kwargs):
            self.started.set()
            await self.release.wait()
            return _completed_response("answer")

    ledger = Ledger(tmp_path / "ledger.db")
    store = Store(tmp_path / "store")
    transport = ControlledTransport()
    client = OpenAIResponsesClient(
        api_key="test-key",
        transport=transport,
        store=store,
        pricing=OpenAIPricing(10.0, 1.0, 20.0),
    )

    async def scenario():
        task = asyncio.create_task(client.complete(
            ROLES["searcher"],
            "p",
            run_id="cancelled-call",
            ledger=ledger,
        ))
        await transport.started.wait()
        task.cancel()
        transport.release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    try:
        _run(scenario())
        run = ledger.get_run("cancelled-call")
        assert run.ended is not None and run.exit_code == 0
        assert run.response_digest and store.exists(run.response_digest)
    finally:
        ledger.close()

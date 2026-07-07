"""The LLM layer: Fable 5 driven as a structured-JSON role-sampler via Claude Code.

The model proposes structured artifacts and never executes anything (tools are
disabled; the harness verifies). Transport is injectable (LLMClient Protocol):
ClaudeCodeClient (default, runs `claude -p` through the executor) for production,
FakeLLMClient for deterministic offline tests, AnthropicAPIClient as a documented
metered-billing alternative for high fan-out.
"""

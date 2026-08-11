"""Structured-JSON model transports for Empiricist roles.

The model proposes structured artifacts and never executes anything (tools are
disabled; the harness verifies). Transport is injectable (LLMClient Protocol):
ClaudeCodeClient remains the completed-pilot default; OpenAIResponsesClient is
the tool-free GPT-5.6 Sol API-key route; FakeLLMClient drives offline tests.
"""

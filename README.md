# empiricist

A lightweight harness that drives a frontier model against the open problems in
fault-tolerant fusion-based quantum computation (FT-FBQC), promoting claims up an
epistemic ledger (HEURISTIC → CONJECTURED → VERIFIED_N → CERTIFIED → FORMALIZED)
where every promotion is backed by a machine-checkable artifact.

- Problems: `docs/open_problems_ftfbqc.md`
- Harness design: `docs/empiricist_harness.md`
- Implementation spec (source of truth): `docs/superpowers/specs/2026-07-06-empiricist-harness-design.md`

## Development

```bash
uv sync --frozen
uv run ruff check src tests
uv run pytest -m "not slow and not slow_lean"
```

v0 pilots **Problem 5**: minimum-fusion synthesis of graph states, `F(G)`, in the
GHZ₃ resource model.

## GPT-5.6 Sol

The completed v0 pilot used Fable 5 through Claude Code. The harness also has a
tool-free OpenAI Responses transport for
[`gpt-5.6-sol`](https://developers.openai.com/api/docs/models/gpt-5.6-sol).
It defaults to `reasoning.mode: "pro"` because these are difficult,
quality-first research tasks. Each role still selects its own
`reasoning.effort`.

Pro and `max` are not alternatives:

- `pro` is a reasoning **mode** (`standard` or `pro`);
- `max` is a reasoning **effort**;
- mode and effort are independent, so a demanding role may use Pro mode and
  `max` effort together.

The supported harness authentication route is an OpenAI API key:

```bash
export OPENAI_API_KEY=...

# Paid live call; --max-gen bounds successful SEARCH work and --max-cost
# supplies the required OpenAI spend threshold.
uv run empiricist run P5 \
  --run-dir runs/p5-gpt56 \
  --live \
  --provider openai \
  --openai-model gpt-5.6-sol \
  --openai-reasoning-mode pro \
  --openai-max-output-tokens 32768 \
  --openai-input-usd-per-mtok 5 \
  --openai-cached-input-usd-per-mtok 0.5 \
  --openai-output-usd-per-mtok 30 \
  --max-gen 1 \
  --max-cost 25
```

API usage is billed separately from a Codex subscription. Do not copy, inspect,
or reuse private Codex subscription/OAuth credentials in the harness.
`codex exec` is also not the integration route: its coding-agent tool and shell
surface conflicts with Empiricist's load-bearing rule that the model receives
no shell or tools. The Responses adapter instead sends an empty tool list,
disables tool choice, requests strict structured output, and leaves execution
to the harness sandbox.

Every live OpenAI campaign requires all three operator-supplied rates:
`--openai-input-usd-per-mtok`, `--openai-cached-input-usd-per-mtok`, and
`--openai-output-usd-per-mtok`. The harness deliberately does not embed prices
that can drift; the example values were the published GPT-5.6 Sol rates on
2026-07-24 and should be checked before a run. Current GPT-5.6 cache-write
(1.25× input) and long-context (>272K: 2× input, 1.5× output) rules are applied
and recorded by the adapter. The CLI also defaults each request to a 32,768
output-token ceiling; raise `--openai-max-output-tokens` only when measured
pilot evidence justifies it.

The adapter currently accepts only the explicit `gpt-5.6-sol` ID and requests
`service_tier: "default"`. It also requires the response to report that exact
model and tier; a missing or different value is receipted and stops the
campaign as billing-unknown rather than applying the wrong rates.

Live campaigns fail closed unless the operator supplies `--max-gen` and/or
`--max-cost`. `--max-gen` is an inclusive, cumulative SEARCH-generation limit.
Because failed SEARCH attempts and CONJECTURE waves do not consume that limit,
live OpenAI campaigns additionally require `--max-cost`.
`--max-cost` is checked before the next paid call or wave; it is a stop
threshold, not a reservation-backed hard ceiling, so one in-flight call or
concurrent wave can cross it. Resuming a campaign that already meets either
configured condition skips client construction and paid preflight.

If a request may have reached the provider but no trustworthy token report
came back—or if a provider-backed run was orphaned by a crash—the run is marked
as billing-unknown and the current campaign stops. Resume then blocks before
preflight.
After comparing provider-side usage, an operator may proceed with
`--acknowledge-unknown-billing`; that acknowledgment is invocation-local and
does not pretend the missing cost was reconstructed.

See the
[source-of-truth implementation spec](docs/superpowers/specs/2026-07-06-empiricist-harness-design.md#521-gpt-56-sol-via-openai-responses-2026-07-24-amendment)
for the request and trust-boundary details. No CI job makes paid model calls.

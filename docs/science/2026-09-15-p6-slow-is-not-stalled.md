# P6 campaign: slow is not stalled — what the run ledger says the "transport stalls" were, and what they cost

**Date:** 2026-09-15 (analysis of 2026-09-09; the relaunch is today) · **Problem:** P6 (ii)(a) ·
**Milestone:** M26c (`docs/superpowers/plans/2026-09-09-m26c-slow-is-not-stalled.md`) ·
**Run:** `runs/p6-completion` · **Model spend:** none for the analysis.

## What the ledger shows

Run 3 (under `p6-zx-v2`, 2026-09-09) stopped itself after rounds 10 and 11 with
`transport_stall`: four proposer calls, no artifact, $0 recorded. A direct probe of the CLI with a
one-line prompt answered in 11 s, so the provider was up. The run ledger's `runs` rows explain
the rest. Every successful proposer call since round 2 emitted 22k–56k output tokens and took
269–724 s of wall time; the output rate is 78.5 tokens/s (total tokens over total wall). Every
call that "stalled" was killed by the transport at its own timeout (exit code −9): three at
run 1's 1800 s, twelve at the 600 s M25c introduced. The proposals — 35- to 41-rule systems with
their inline rule JSON, plus the model's deliberation — had outgrown the timeout. The stall
detector read slow as stalled.

| call | output tokens | wall | recorded |
|---|---|---|---|
| eight successful proposals | 4.9k – 55.8k | 64 – 724 s | $1.48 – $3.09 each, $16.24 in all |
| fifteen killed at the timeout | unknown (generation continued until the kill) | 600 s × 12, 1800 s × 3 | $0.00 |

A killed call records nothing, but the API bills for what it generated before the process died.
The ledger's `spent()` docstring says exactly this ("a LOWER BOUND on true spend … runs killed
mid-flight never record their cost. A capped campaign must reserve in-flight cost against the
cap"); the zx campaign never did.

## The estimate

`unrecorded_estimate` charges each killed proposer call for its whole wall time at the observed
cost per second of generation over the successful calls ($0.0057/s, total cost over total wall).
For this run directory: 15 calls, 12,601 s, **$71.78**; recorded plus estimate **$88.01** of the
$100 authorised. This is an upper bound: at 78.5 tokens/s an 1800 s call would have produced
141k tokens, beyond any output limit, so the three run-1 kills most likely stopped generating
well before they were killed; the true spend is probably between $50 and $65. The figures in
`docs/science/2026-09-09-p6-completion-campaign.md` ($6.64, $9.60, $16.24) are recorded spend
and stand as such; the console is the only place the true number lives.

## What changed (M26c)

- The proposer timeout defaults to 1500 s (a 60k-token proposal at the measured rate) and the
  playbook asks the model to reuse earlier inline rules by name rather than re-emit their JSON.
- The cost cap compares recorded spend **plus** the estimate with `--max-cost`; every `round`
  and `stop` record carries `unrecorded_usd` and `timeouts`; the driver prints both.
- A round whose calls all died at the timeout is a *timeout round*; two in a row stop the run
  with `proposer_timeout` (exit code 3) and the driver says what to raise. `transport_stall`
  stays for rounds that return nothing without a kill.

## The relaunch

`--max-cost 100 --proposer-timeout 1500`: with $88 effective spend the loop has room for two
or three more rounds before the cap. Raising the cap is the author's call, informed by the
console; the loop now reports what it cannot see.

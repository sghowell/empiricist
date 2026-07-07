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

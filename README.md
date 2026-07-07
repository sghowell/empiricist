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
uv sync
uv run pytest
```

v0 pilots **Problem 5**: minimum-fusion synthesis of graph states, `F(G)`, in the
GHZ₃ resource model.

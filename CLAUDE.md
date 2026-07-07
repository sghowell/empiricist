# Empiricist — project instructions

AI harness attacking open problems in fault-tolerant fusion-based quantum
computation (FT-FBQC). **Source of truth:**
`docs/superpowers/specs/2026-07-06-empiricist-harness-design.md`.
Background: `docs/empiricist_harness.md`, `docs/open_problems_ftfbqc.md`.

## Commands

- `uv sync` — install env (Python ≥3.11)
- `uv run pytest` — run tests
- `uv run ruff check src tests` — lint

## Non-negotiables

- **Epistemic discipline:** nothing enters the ledger above HEURISTIC without
  machine evidence. Statuses change only alongside evidence rows. REFUTED is terminal.
- **TDD** for ledger and verifiers. Golden suites gate verifier certification.
- **The model never gets a shell.** Model output is structured JSON; the harness
  executes everything in the sandbox (`executor/`).
- **Provenance:** every subprocess/model call becomes a `runs` row; artifact IDs
  are blake3 content hashes; certificates embed exact version pins.
- Commit messages: descriptive, **no AI attribution** (no Co-Authored-By).
- Branch per milestone → PR → squash-merge to `main`. Never push to `main`.
- The ledger DB and CAS blobs live on local disk and are **never** committed.

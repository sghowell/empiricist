# M24b: the `cosmology` pack — death_and_gravity's replay checkers as certified pack verifiers

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The charter's 2026-10-02 row: a `cosmology` pack under `empiricist.packs.cosmology` holding death_and_gravity's certificate replay checkers (ball arithmetic over `python-flint`, exact `sympy` identities; then the Taylor-model / Krawczyk validated-numerics checkers and the conic-dual checker as far as time allows), each a certified pack verifier with a golden suite built from the repository's pinned certificates and mutated FAIL fixtures; and one cosmology claim promoted in death_and_gravity with a pack verifier and a review receipt. The pack lands without touching core — that is the boundary's proof.

**Architecture:** Every death_and_gravity checker follows one contract: a package `<pkg>` whose `verify` module exposes `REPORT` (the pinned certificate path), `build_report()` (an exact, read-only replay) and `validate_report(expected, actual)` (raises `ValueError`/`KeyError`/`TypeError`/`AssertionError` on any difference). The pack vendors the checker packages under `packs/cosmology/checkers/<pkg>/` and wraps each in one generic `ReplayVerifier(BytesFileVerifier)`: the evidence payload is the certificate JSON; `verify_bytes` = `validate_report(json.loads(payload), build_report())` → PASS, a raised difference → FAIL, anything else → ERROR. The identity hashes the verifier module plus every vendored module of that checker (`module_source_hash`). Golden cases are vendored bytes: the pinned certificate (PASS) and a mutated copy (FAIL). Pack verifier names carry the `cosmo_` prefix so they never shadow the research repository's own command-verifier declarations (`p8a`, `p8a_radiation`, …), which stay as they are.

**Tech Stack:** Python 3.11+, `sympy`, `python-flint` (arb/acb ball arithmetic, fmpq exact rationals); later `clarabel`/`scipy` for the conic-dual checker. Optional dependency group `cosmology` in `pyproject.toml`; tests skip cleanly when the group is not installed.

**Spec:** charter `docs/superpowers/specs/2026-09-04-empiricist-v1-charter.md` §5, §9 (2026-10-02 row); the pack API in `src/empiricist/packs/__init__.py` (M24a Task 1) and `docs/superpowers/plans/2026-09-07-m24a-pack-boundary.md`.

## Global Constraints

- **Core is not touched.** Allowed edits outside `src/empiricist/packs/cosmology/` and `tests/`: `pyproject.toml` (an optional dependency group `cosmology`), `.github/workflows/ci.yml` (install the group in the fast job; if `python-flint` has no wheel for the runner, keep the group out of CI and let the tests skip), and docs. If something in core seems to block the pack, write it down in the plan outcome instead of changing core.
- The pack API (do not change it; ask by leaving a note in the outcome if it does not fit):
  ```python
  from empiricist.packs import BytesFileVerifier, GoldenCase, PackManifest, PackVerifier
  class BytesFileVerifier:            # run(evidence_rel) reads <repo>/<rel> and calls verify_bytes
      def __init__(self, repo: Path) ...
      def verify_bytes(self, payload: bytes) -> VerifierResult   # total: never raises
      def golden_suite(self) -> list[GoldenCase]                 # GoldenCase(label, payload: bytes, expected: Verdict)
      name: str; version: str; binary_hash: str (property)
  PackManifest(name="cosmology", version="0.1", verifiers={"cosmo_p8a": factory, ...}, problems={"P8": "..."})
  # the pack module exposes MANIFEST; import of the pack module must raise ImportError (only) when
  # an optional dependency is missing, so `load_pack("cosmology")` reads as "not installed".
  ```
- Vendored checker code is copied verbatim from death_and_gravity (branch `empiricist-claims-import`, or `main` where identical), with the origin path and commit recorded in a `SOURCES.md` inside the pack. Do not "improve" the checkers: a replay checker's value is that it is the code the certificates were produced against.
- The verifier is total: `verify_bytes` never raises (ERROR verdict with the message).
- Every verifier ships at least one PASS and one FAIL golden. A FAIL golden must fail *through the checker* (a mutated certificate value), not through malformed JSON.
- Model spend: only the review receipt(s) for the promotion in death_and_gravity (two reviewer samples at CERTIFIED, ~$5). Nothing else spends.
- TDD; `uv run ruff check src tests` clean; no AI attribution in commit messages. Work on the branch you are given (`feat/m24b-cosmology-pack`, stacked on `feat/m24a-packs`); commit per task.

## Where things are

- Research repository: `~/dev/research/death_and_gravity`. The claims trial branch `empiricist-claims-import` has `claims/verifiers/*.yaml` (seven declarations: `p8a`, `p8a_radiation`, `p8a_reference`, `p8a_asymptotics`, `p8a_backreaction`, `p8a_response`, `p8a_remainder`), `claims/fixtures/<name>/fail-mutated.json` (FAIL fixtures), `tools/empiricist_check.py` (the adapter; read it first, it is the contract), and 51 claim files. A worktree of that branch may exist under this session's scratchpad (`dg-claims`); create your own with `git -C ~/dev/research/death_and_gravity worktree add <path> empiricist-claims-import` if not. Never commit in death_and_gravity's `main`; use the import branch.
- Each declaration's `env.PYTHONPATH` and `inputs` tell you which package directory to vendor and which `<pkg>.verify` module to wrap; its `fixtures.pass` is the pinned certificate to vendor as the PASS golden, `fixtures.fail` the FAIL golden.
- The P8(a) checkers import `sympy` and `flint` (`arb`, `acb`, `ctx`, `fmpq`, `fmpq_poly`). The validated-numerics library (Taylor models, Krawczyk) is `problems/P4/src/p4/validated/` (~9.6k lines) and the conic-dual machinery is `problems/P9/src/p9/` (`clarabel`); port those only after the P8(a) family is certified and the deliverable claim is promoted.
- Empiricist CLI for the deliverable (run with `uv run --project ~/dev/empiricist empiricist …` from the research worktree; never `uv run` inside the research repo): `claims certify-verifier --repo . --name <name>` (resolves a pack verifier when no declaration of that name exists), `claims formulate`, `claims promote --id … --level … --verifier cosmo_… --evidence <certificate>`, `claims review --repo . --id … --target-level CERTIFIED` (model reviewer, two samples), `claims check --repo . --min-claims 1`.

---

### Task 1: the pack skeleton and the generic replay verifier

**Files:** `src/empiricist/packs/cosmology/__init__.py` (MANIFEST), `src/empiricist/packs/cosmology/replay.py` (`ReplayVerifier`), `src/empiricist/packs/cosmology/SOURCES.md`, `pyproject.toml` (group `cosmology = ["sympy>=1.14", "python-flint>=0.7"]`), `tests/test_packs_cosmology.py` (module-level `pytest.importorskip("flint")`).

- `ReplayVerifier(BytesFileVerifier)`: constructed with `(repo, *, name, version, checker_module, engine_modules, goldens)`; `binary_hash = module_source_hash(replay_module, checker_module, *engine_modules)`; `verify_bytes` as in the architecture paragraph; `golden_suite()` returns the vendored cases.
- Test with a tiny fake checker module (PASS on the pinned bytes, FAIL on a mutation, ERROR on a checker exception).

### Task 2: the P8(a) family

Vendor the seven `p8a*` checker packages under `checkers/`; register `cosmo_p8a`, `cosmo_p8a_radiation`, …, `cosmo_p8a_remainder` (version `"1"`), each with its PASS/FAIL goldens; `problems={"P8": "<the problem version the research repo records, or 'p8a-v1'>"}`. Tests: the manifest loads; every verifier certifies PASS in a temp repository (`certify_pack_verifier`); `verify_bytes` on each PASS golden is PASS, on each FAIL golden is FAIL; identities differ per verifier. Note the wall time per checker in the outcome (the command verifiers took ~4 s each).

### Task 3: the deliverable in death_and_gravity

On the import branch: `certify-verifier` the pack verifier(s); find a claim below CERTIFIED whose certificate one of the ported checkers replays (or, if every P8(a) claim is already CERTIFIED, port the checker family of a chain that is not — the S5/S6 chains follow the same contract — and promote one of its claims); `promote` it with the pack verifier as evidence; obtain a model review receipt at CERTIFIED (two samples) and promote to CERTIFIED; `claims check` green; commit and push the import branch. Record claim id, receipt ids, cost.

### Task 4: further checker families (as far as time allows, in this order)

1. Taylor-model and Krawczyk checkers from `problems/P4/src/p4/validated/` — vendor the minimal closure of modules a `validate_report`-style replay needs (start from whichever P4 `verify`-like entry point the repository's certificates use; if none exists, write the thinnest replay wrapper that recomputes and compares the pinned certificate, and say so in SOURCES.md).
2. The conic-dual checker from `problems/P9/src/p9/` (`clarabel` in the optional group).
Each: goldens, tests, manifest entry.

### Task 5: outcome

Append an outcome section to this plan: what was ported (files, line counts, wall times), the deliverable's claim and receipts, anything the pack API could not express, and what remains. Do not open a PR; the coordinator merges the stream.

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

## Outcome (2026-09-08)

Branch `feat/m24b-cosmology-pack`, stacked on `feat/m24a-packs`. Core untouched: nothing
under `src/empiricist/` outside `src/empiricist/packs/cosmology/` changed; `pyproject.toml`
gained the optional group `cosmology = ["sympy>=1.14", "python-flint>=0.7"]` and the CI fast
job installs it (both ship macos-14 wheels).

### What was ported

`checkers/death_and_gravity/` is a verbatim partial mirror of the research repository
(branch `empiricist-claims-import` at `e04bb6c`), produced by `vendor.py` and listed with
sha256 per file in `SOURCES.md`: 171 files (118 `.py`, 38 `.md`, 14 `.json`, `uv.lock`;
2.1 MB). The mirror, not just the packages, because every checker hashes `src/<pkg>/*.py`,
`tests/*.py`, `*.md` and `notes/*.md` relative to `Path(__file__).parents[2]` into the
certificate's `source_sha256`, and pins its prior certificates by path (`prior.REPORT`,
`P8/certificates/...`); the P8(b) classification certificate also pins the repository's
`uv.lock` sha256 and the exact Python / sympy / python-flint versions (3.11.14 / 1.14.0 /
0.9.0 -- the pack's locked environment matches, so the chain replays).

| family | vendored | lines |
|---|---|---|
| P8(a) chain: `p8a`, `p8a_radiation`, `p8a_reference`, `p8a_asymptotics`, `p8a_backreaction`, `p8a_response`, `p8a_remainder` (seven checker roots under `problems/P8/a/`) | src + tests + notes + certificates | 3,882 src, 1,774 tests |
| P8(b) base chain: `p8` (`problems/P8/`) | src + tests + notes + certificates + `uv.lock` | 1,916 src, 568 tests |
| notes / README / FORMULATION (hashed into certificates) | 38 files | 4,127 |
| certificates | 14 files | 887 KB |

Pack code proper: 712 lines (`replay.py`, `vendored.py`, `verifiers.py`, `vendor.py`,
`__main__.py`, three adapters); tests 292 lines (20 tests).

Ten verifiers, version `1`, all `cosmo_`-prefixed. Wall time is the read-only replay in a
warm interpreter (the research repository's command verifiers took ~4 s each including
interpreter start); a chain member replays every predecessor, so the times are cumulative.

| verifier | checker | replays | claim | wall |
|---|---|---|---|---|
| `cosmo_p8a` | `p8a.verify` | `focusing.json` | P8-A.1 | 0.6 s |
| `cosmo_p8a_radiation` | `p8a_radiation.verify` | `radiation-qsei.json` | P8-A.2 | 1.0 s |
| `cosmo_p8a_reference` | `p8a_reference.verify` | `radiation-reference.json` | P8-A.3 | 1.4 s |
| `cosmo_p8a_asymptotics` | `p8a_asymptotics.verify` | `radiation-asymptotics.json` | P8-A.4 | 1.7 s |
| `cosmo_p8a_backreaction` | `p8a_backreaction.verify` | `radiation-backreaction.json` | P8-A.5 | 2.3 s |
| `cosmo_p8a_response` | `p8a_response.verify` | `radiation-response.json` | P8-A.6 | 3.6 s |
| `cosmo_p8a_remainder` | `p8a_remainder.verify` | `radiation-remainder.json` | P8-A.7 | 4.1 s |
| `cosmo_p8_s0` | adapter over `p8.verify.report()` | `s0-identities.json` | P8-0 | 0.3 s |
| `cosmo_p8_s1` | adapter over `p8.verify_all.derivation_report()` | `s1-derived-action.json` | P8-1 | 12 s |
| `cosmo_p8_chain` | adapter over `p8.verify_all.build_reports()` | the six: `s1-derived-action`, `a25-regression`, `witness-C/D/CD_matter`, `classification` | P8-1, P8-2.C/D/CD/reg, P8-3 | 54 s |

- **Replay verifier.** `ReplayVerifier(BytesFileVerifier)`: PASS iff
  `validate_report(json.loads(payload), build_report())` returns; FAIL when the checker
  raises `ValueError`/`KeyError`/`TypeError`/`AssertionError` -- from `validate_report` *or*
  from `build_report` (a failed exact identity, a changed pinned prior), exactly the
  adapter's exit-3 set; ERROR for a non-JSON payload or any other exception. One replay per
  verifier instance (cached; a certification runs every golden against it; `promote`
  constructs a fresh instance, so it always replays).
- **Vendored imports.** The checkers are top-level packages importing each other by name;
  `vendored.py` serves the registered names through a `sys.meta_path` finder ahead of
  `sys.path`, and refuses (loudly) a name already imported from elsewhere. The tests assert
  `p8a.__file__` lies under the pack.
- **Identity.** blake3 over the source-file *bytes* of `replay.py`, the checker module and
  every module of every vendored package the replay imports (`p8a_remainder` hashes all
  seven packages). This is core's `module_source_hash` rule read from bytes instead of
  `inspect.getsource`, which raises `OSError` on an empty module file.
- **Goldens.** PASS: the pinned certificate(s) from the vendored tree (six for the chain
  verifier). FAIL: the research repository's own `claims/fixtures/<pkg>/fail-mutated*.json`
  for the seven P8(a) checkers (`status` set to `MUTATED_FOR_EMPIRICIST_FAIL_FIXTURE`);
  for the base chain, which the repository declares no verifier for, `vendor.py` mints one
  by changing a certified value (`benchmark_Hdot0_pinned` 1/375 -> 1/376; the first ADM
  residual 0 -> 1; `counts.M0.E` 12 -> 11). Every FAIL fails through the checker.
- **The P8(b) base chain needed adapters.** `p8.verify` / `p8.verify_all` predate the
  contract (`CERTIFICATE`/`report()`/`check_certificate()`, `derivation_report()`/
  `build_reports()`/`check_reports()`); `adapters/p8_s0.py`, `p8_s1.py`, `p8_chain.py` are
  the thinnest wrappers, calling the vendored functions unchanged. The chain adapter accepts
  a certificate iff it equals one of the six rebuilt reports (the S0 anchor is re-checked
  inside `build_reports` but is not one of them, so it has its own verifier).
- **Tests** (`tests/test_packs_cosmology.py`, `pytest.importorskip("flint")`): the replay
  verifier over a fake checker (PASS / FAIL / ERROR / checker-refusal-is-FAIL / `run`
  / identity over checker and engine sources / certification through a fake pack); the
  manifest; every golden of every fast verifier yields exactly its verdict; all nine fast
  verifiers certify in a temporary repository with distinct identities and suite hashes;
  the vendored code is what runs; the stopgap driver end to end; the chain verifier
  (`slow`, 51 s). Fast set ~20 s. Lint clean (`checkers/ruff.toml` excludes the vendored
  code).

### The deliverable: P8-0 CERTIFIED by `cosmo_p8_s0` (death_and_gravity `0ba4c6a`)

Every P8(a) claim was already CERTIFIED, and every S5/S6 checker pins and replays
HEURISTIC priors (P8-3, P8-2.CD, P8-S5.1.D, ...), so an honest dependency list would cap
any S5/S6 claim below CERTIFIED (charter section 3; a model receipt cannot waive it). The
P8(b) base chain is the one place a single review can honestly reach CERTIFIED: its claims
have no dependencies and its root certificate pins nothing but its own three modules. So
the base chain was ported (the adapters above) and **P8-0** -- the S0 anchor every P8(b)
certificate re-checks -- is the deliverable, on the research branch
`empiricist-claims-import` at `0ba4c6a` (pushed):

- `python -m empiricist.packs.cosmology certify --repo . cosmo_p8_s0`: stamp
  `cosmo_p8_s0` v1, binary `7ad7bd7882e4...`, golden suite `41869da5cd28...`,
  `pack: cosmology`, in `claims/verifiers.json` (no declaration under `claims/verifiers/`).
- P8-0 gained `formulation_version: problems/P8/FORMULATION.md@73dd18f7` and a note saying
  what the verifier is (the review bundle otherwise shows a pack verifier only as "not a
  command verifier declared in this repository; registry stamp ...").
- `claims check --min-claims 1`: green (51 claims, 0 blocking) before and after.
- `claims review --id P8-0 --target-level CERTIFIED` (two samples, `claude-fable-5`,
  14 minutes): receipts **`P8-0.20260909.model`** (REVISE, no blocking finding, $3.19,
  run `review-P8-0-b0bde1-s1`) and **`P8-0.20260909.model.2`** (REVISE, no blocking
  finding, $2.31, run `review-P8-0-b0bde1-s2`). **Cost $5.50.** Both samples checked the
  recorded GS/FS/exceptional_A3/Hdot(0) expressions against the statement by direct
  expansion and found them right; their warnings are about the record, not the algebra:
  before promotion the claim carried only IMPORTED entries and no exhibited verifier (the
  PASS entry is written by `promote`, which runs after the review -- an ordering the
  reviewer cannot see through); the three derivation modules the certificate pins by hash
  are not evidence entries; the imported S1/S2/ladder test files exceed the S0 scope; the
  exceptional-relation clause omits the certificate's own side conditions
  (X>0, G_T!=0, 3XA1-4F2!=0) and leaves Y, Q undefined in the statement text. Changing the
  statement would unbind both receipts and cost another review; charter F4's bar is "no
  blocking finding", so the warnings stay on record for the author.
- `python -m empiricist.packs.cosmology promote --repo . --id P8-0 --level CERTIFIED
  --verifier cosmo_p8_s0 --evidence problems/P8/certificates/s0-identities.json --receipt
  P8-0.20260909.model.2`: the replay ran inside `promote` (PASS, 0.3 s); P8-0 is
  **CERTIFIED, CURRENT**, `legacy_level` cleared, evidence entry
  `cosmo_p8_s0 v1 [7ad7bd78...] golden 41869da5...` at 2026-09-09T02:41:53Z, notes
  "promoted to CERTIFIED on receipt P8-0.20260909.model.2 (REVISE: 5 open warning(s) for
  the author, no blocking finding)".
- Committed: `CLAIMS.md`, `claims.lock.json`, `claims/P8-0.yaml`, `claims/verifiers.json`,
  the two receipts. Nothing on the research repository's `main`.

### What the pack API and core could not express (core left untouched)

1. **`feat/m24a-packs` carries M24a Task 1 only.** `promote._resolve_verifier`, `reverify`,
   `check.drifted_verifiers` and the CLI's `claims certify-verifier` resolve command
   verifiers only; the "declaration first, installed pack second" resolution of M24a
   Task 2 is not on the branch. The pack works around it with
   `python -m empiricist.packs.cosmology {certify,promote,reverify}` (`__main__.py`), which
   hands the pack verifier *object* to the same core functions and adds nothing: `promote`
   still checks the stamp, standing, lock and receipt and runs the verifier itself; a
   repository declaration of the same name is refused as shadowing. Consequences until
   Task 2 lands: `claims check` cannot see drift of a pack verifier (the stamp says
   `pack: cosmology`, but `drifted_verifiers` only asks `builtin_identity`, so an edited
   pack would not make its evidence STALE); `claims reverify` answers "no verifier
   available for cosmo_..." for pack-verified claims (the driver's `reverify` covers it);
   the review bundle shows a pack verifier as "not a command verifier declared in this
   repository; registry stamp ..." (hence the explanatory note on the claim). Delete
   `__main__.py` when core resolves packs.
2. **`promote._note` is command-verifier shaped**: a pack verifier's evidence note reads
   `argv=None cwd=None exit=None env_sha256=None`. The `VerifierResult.details` already
   carry `checker` and `certificate_sha256`; the note should carry those for pack verifiers.
3. **`module_source_hash` (inspect.getsource) raises `OSError` on an empty module file.**
   The pack hashes source bytes (`replay.source_hash`), the same rule; core's helper could
   read bytes too.
4. **The registry stamp's `pack` field is recorded but unused** by `check`/`promote`.
5. **`GoldenCase` has no provenance field**; the pack records each golden's origin (research
   fixture path or minted mutation) in `SOURCES.md` instead.
6. **`PackManifest.problems`**: the research repository records no per-problem version
   string; `{"P8": "problems-v1.1"}` names the tag its frozen problems document carries.

### Task 4: not started (assessment)

Neither remaining family has a replay entry point of the checker contract, so each is a
design task, not a vendoring task:

- **P4 validated numerics** (`problems/P4/src/p4/validated/`, 7,341 lines; flint arb/acb,
  numpy, scipy `solve_ivp`, multiprocessing). `tc_monotone.py`, `tc_energy.py`,
  `tc_leading.py`, `analyticity.py`, `krawczyk_kappa.py` are certificate *writers*
  (`main(argv)` runs the validated computation and dumps `results/theorem_*/*.json`); none
  has a `--check` mode, and the claims' evidence (`tc_monotone.json`, `krawczyk.json`, ...)
  is the writer's output. A replay wrapper must re-run the computation (wall time
  unmeasured; some modes are multiprocess) and decide which fields are certified values and
  which are run metadata, with the P4 owner. `main` also has uncommitted `tc_energy` edits.
- **P9 conic dual** (`problems/P9/src/p9/`, 4,168 lines; clarabel/cvxpy for the solver,
  flint for `verify.py`/`verify3.py`). `replay.py` re-verifies an LKR chain from the stored
  dual vectors `results/certificates/lkr_*/*.npz` -- hundreds of MB, gitignored, so not
  vendorable; only `state.json` is committed. `certify_feasible.py` (P9-1, "certificate =
  the point") re-checks class membership and chi-squared from the released data files
  (`problems/P9/data/raw/`, some large) and is the plausible first port.

### What remains

- M24a Task 2 on the stack, then delete `__main__.py` and run the deliverable's commands
  through `empiricist claims`.
- The S5/S6 chains (`p8_s5` ... `p8_matching`, 13 checkers, all following the contract) can
  be vendored the same way; every one pins and replays HEURISTIC priors (P8-3, P8-2.CD,
  P8-S5.1.D, ...), so their claims can rise only after the P8(b) base chain is re-earned
  bottom-up (P8-1, P8-2.*, P8-3 through `cosmo_p8_chain`, one review each).
- Task 4 as assessed above.

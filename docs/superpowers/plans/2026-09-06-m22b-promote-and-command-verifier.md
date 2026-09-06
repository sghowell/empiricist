# M22b: One Promotion Path — registry, generic command verifier, formulate/promote/reverify/demote — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Charter §4: `promote` is the only way a level rises, in both modes. This slice adds
the committed verifier registry for a research repository, the generic command verifier
(a declared command with hashed inputs and golden PASS/FAIL fixtures — the bridge that makes
existing pytest/`verify.py` suites admissible evidence), and the commands `formulate`,
`promote`, `reverify`, `demote`, plus the batch hook that makes Empiricist's own ingest
paths materialise claim files. `review` (receipts written by a model or a human) and the
skill pack are M22c.

**Architecture:** `empiricist.claims.registry` holds `claims/verifiers.json` (stamps:
name, version, binary_hash, golden_suite_hash, stamped, plus each verifier's declaration)
and answers `registry_newer` for standing. `empiricist.claims.command_verifier` declares a
verifier as data (`claims/verifiers/<name>.yaml`: argv template, cwd, env, inputs to hash,
PASS and FAIL fixtures), certifies it by running both fixtures through `executor.execute`
(exit 0 / non-zero), and verifies an evidence path by running the same command; its
`binary_hash` is the sha256 of the declaration plus every hashed input. `promote` (in
`empiricist.claims.promote`) is a pure function of (repo, claim, verifier, evidence,
receipt): stamp check → run → PASS required → receipt required for elevated `statement`
claims → dependencies CURRENT → write evidence entry, lock, level, rendered table; else a
refusal with a reason. The batch hook is the existing importer applied to one artifact
(`materialize_artifact`) called from the four ingest functions when a claims repo is
configured.

**Tech Stack:** Python ≥3.11, pydantic, PyYAML, the existing executor (`SandboxMode.NONE`
with `env_passthrough` for a research repo's own venv, recorded in the evidence note as the
declared command; charter §2's shell rule: the agent's shell is outside the trust boundary,
the verifier's re-run is the evidence).

**Spec:** charter §2 (F1, F3, F6, shell rule), §4, §5; M22a plan for the file formats.

## Global Constraints

- A level rises only through `promote` (charter §4); `check` still runs no verifiers.
- Receipts required for elevated (CERTIFIED, FORMALIZED) promotions of `statement` claims.
- Every verifier run through `promote` is recorded: verifier identity in the evidence entry,
  the exact argv/cwd/env in the entry's `note`, and (batch mode) the SQLite `runs` row.
- Core imports no pack; `claims/` stays domain-free.
- Branch `feat/m22b-promote`, PR, squash-merge; TDD; no AI attribution.

---

### Task 1: Verifier registry (`claims/registry.py`)

```python
class VerifierStamp(BaseModel): name; version; binary_hash; golden_suite_hash; stamped: str; declaration: str|None  # path of the declaration for command verifiers
class Registry(BaseModel): version: int = 1; stamps: dict[str, VerifierStamp]  # key = name
def registry_path(repo) -> Path            # claims/verifiers.json
def read_registry(repo) / write_registry(repo, reg)
def stamp(repo, verifier, golden_suite_hash, declaration=None) -> VerifierStamp
def current_stamp(repo, name) -> VerifierStamp|None
def registry_newer(repo) -> Callable[[EvidenceEntry], bool]   # True iff the registry's current stamp for entry.verifier has a version > entry.version, or the same version with a different binary_hash
```
- [ ] Tests: stamp/read round-trip; `registry_newer` on same/older/newer versions and on a
  changed binary hash; `check --repo` uses it (a claim whose verifier was re-stamped at a
  newer version becomes STALE).

### Task 2: Generic command verifier (`claims/command_verifier.py`)

Declaration `claims/verifiers/<name>.yaml`:
```yaml
name: p8a_remainder_replay
version: "1"
argv: [".venv/bin/python", "-m", "p8a_remainder.verify", "--check"]   # {evidence} placeholder allowed
cwd: "."                       # repo-relative
env: {PYTHONPATH: "problems/P8/a/src:..."}
inputs: ["problems/P8/a/applicability/.../src/p8a_remainder"]        # files/dirs hashed into binary_hash
fixtures:
  pass: ["problems/P8/.../certificates/radiation-remainder.json"]    # must exit 0
  fail: ["claims/fixtures/p8a_remainder_replay/mutated.json"]       # must exit non-zero
timeout_s: 1800
```
```python
class CommandVerifierSpec(BaseModel) (closed; paths repo-relative; argv non-empty)
class CommandVerifier:  name, version, binary_hash (sha256 over the declaration bytes + every input file, sorted), spec
    def run(self, repo, evidence_path) -> VerifierResult     # PASS iff exit 0; details: exit code, argv, cwd, env keys, stdout/stderr tails, wall_s
def load_command_verifier(repo, name) -> CommandVerifier
def certify_command_verifier(repo, name) -> VerifierStamp    # runs every pass fixture (must PASS) and every fail fixture (must FAIL); stamps with golden_suite_hash = sha256 of the fixture files' contents + names
```
The command runs through `executor.execute(ExecSpec(argv, cwd=repo/cwd, env_extra=env, env_passthrough=True, sandbox=SandboxMode.NONE, timeout_s))` with the evidence path substituted for `{evidence}` (or exported as `EMPIRICIST_EVIDENCE`). A FAIL fixture is mandatory (a suite that cannot fail certifies nothing — the P5 rule).
- [ ] Tests (offline, with a tiny script fixture in the test repo: `check.py` that exits 0 iff the evidence JSON has `"ok": true`): certification PASS; certification FAIL when the fail fixture unexpectedly passes; `binary_hash` changes when an input file changes; `run` on a passing and a failing evidence file; timeout → ERROR; missing declaration → ClaimSchemaError.

### Task 3: `formulate`, `promote`, `reverify`, `demote` (`claims/promote.py`, CLI)

```python
def formulate(repo, *, claim_id, problem, formulation_version, kind, statement, depends_on=(), notes="") -> ClaimFile   # writes a HEURISTIC claim file; refuses an existing id
class PromotionRefused(Exception): reason
def promote(repo, *, claim_id, level, verifier: CommandVerifier|Any, evidence_path, receipt_id=None, run_id=None, now=...) -> ClaimFile
    # 1 stamp current for verifier (name, version, binary_hash) in the registry; else refuse
    # 2 verifier.run(repo, evidence_path) must be PASS; else refuse (FAIL evidence entry is still recorded when the verdict is FAIL and the target is REFUTED)
    # 3 elevated statement levels need receipt_id naming a receipt for this claim whose statement_sha256 matches and that has no blocking finding
    # 4 every claim-id dependency must be CURRENT (derived, not stored); path dependencies must be lockable
    # 5 level must not decrease (use demote); REFUTED requires a FAIL verdict
    # 6 write evidence entry (+ note with argv/cwd), refresh lock, set level (+ n/coverage/substatus from kwargs), updated=today, save; refresh_repo(repo)
def reverify(repo, *, claim_id=None) -> dict[str, str]   # for each STALE (or the named) claim: re-run every evidence entry's verifier (command verifiers by name), fresh entries + lock; returns id -> outcome
def demote(repo, *, claim_id, level, receipt_id, reason) -> ClaimFile   # level down only, records a receipt id and the reason in notes
```
CLI: `empiricist claims formulate|promote|reverify|demote ...` with the arguments above.
- [ ] Tests: the happy path (formulate → certify a command verifier → promote to CERTIFIED with a receipt → check green → CLAIMS.md row); each refusal (no stamp, verifier FAIL, missing/blocking receipt, non-CURRENT dependency, level decrease); reverify after an evidence edit returns to CURRENT; demote records the receipt; refuted path.

### Task 4: Batch hook — Empiricist ingests materialise claim files

- `empiricist.claims.materialize.materialize_artifact(run_dir, repo, artifact_id)` = the
  importer for one artifact (reuse `import_ledger` internals; idempotent). `RunConfig` gains
  `claims_repo: Path | None` (also `EMPIRICIST_CLAIMS_REPO`); `verify_and_ingest_lean_artifact`,
  `ingest_p3_certificate`, `ingest_exact_witness`, `verify_and_ingest_scheme` call it after
  a successful transaction when a repo is configured (CONJECTURED or above, or REFUTED).
- [ ] Tests: with a tmp repo configured, a lean ingest through the fake verifier produces a
  claim file and a green check; without configuration nothing is written.

### Task 5: Campaign actions

- [ ] Certify one death_and_gravity `verify.py --check` as a command verifier on the trial
  branch (needs their `.venv`; declaration + a mutated-certificate FAIL fixture), then
  `reverify` the claim rows it covers so they carry a real PASS entry, and run `check`.
  Record what the first genuine `promote` there would need (a receipt → M22c).


---

## Outcome (2026-09-06)

- Task 1 (registry) and Task 2 (command verifier): as planned. `check` consults the
  committed registry by default (`registry_newer(repo)`); `certify-verifier` is a CLI
  command; a verifier run records its exact argv/cwd in the evidence note.
- Task 3: `formulate` / `promote` / `reverify` / `demote` as planned, plus: a failed
  verifier run is recorded as evidence without moving the level; `promote` clears
  `legacy_level` once the promoted level reaches it; `reverify` re-runs only claims that
  are STALE for their own reasons (lock drift, newer verifier) because propagated
  staleness clears with its source.
- Task 4 deviation: `RunConfig` is untouched. A machine path inside `config_hash` would
  make certificates non-portable, so the repo is `claims_repo=` on the ingest functions,
  else `EMPIRICIST_CLAIMS_REPO`. `materialize_artifacts(ledger, store, repo,
  artifact_ids=...)` is the shared per-artifact importer (import_ledger delegates) and
  stamps `claims/verifiers.json` from the ledger's PASS certifications without
  downgrading. The projection never blocks the ledger write (logged; `import-ledger`
  catches up).
- Task 5 (death_and_gravity trial, local branch `empiricist-claims-import`, commit
  c17c356): `tools/empiricist_check.py` adapts every `<package>.verify` checker (all 20
  P8 modules share `REPORT` / `build_report()` / `validate_report()`) to a command
  verifier; `claims/verifiers/p8a_remainder.yaml` certified (PASS fixture = pinned
  certificate, FAIL fixture = mutated status; ~4 s per replay); `P8-A.7` promoted to
  CONJECTURED with a real PASS entry. `promote --level CERTIFIED` is refused: a
  statement claim needs a review receipt -- that is M22c's `review`. `CLAIMS.md` there
  is now the rendered ledger (`report --force`, one-time) and `check --min-claims 50`
  is green with 51 claims (M22a's importer had silently dropped 2 rows with `|` in
  their statements; recovered).
- M22a review (17 findings) applied first; imported claims now enter at HEURISTIC with
  `legacy_level` ("not re-earned") and IMPORTED evidence, which is why the trial's rows
  read HEURISTIC until re-earned through `promote`.

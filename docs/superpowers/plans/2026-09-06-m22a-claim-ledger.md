# M22a: Claim Ledger v1 — files, lock, standing, check, import, report — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** The first slice of the v1 charter: a git-tracked claim ledger (one YAML per claim, a
hash lock, review-receipt slots, a rendered `CLAIMS.md`), the pure `check` command that
recomputes hashes, validates schemas and the dependency DAG, propagates STALE and exits
non-zero on any inconsistency, and one-time importers from (a) an Empiricist SQLite ledger
and (b) an existing `CLAIMS.md` table (death_and_gravity's). No verifiers run in this slice;
`promote`/`review`/`reverify`/`demote` are M22b.

**Architecture:** A new core package `empiricist.claims` that knows nothing about any
problem domain (charter §5: core imports no pack). `model.py` holds the pydantic schema for
a claim file and the YAML codec (sorted keys, deterministic); `lock.py` computes and
verifies `claims.lock.json`; `standing.py` derives CURRENT/STALE/CHALLENGED/SUPERSEDED from
the lock, the DAG, receipts and `supersedes` (Lem v3 semantics as absorbed by the charter);
`check.py` composes them into a report with an exit code; `render.py` writes `CLAIMS.md`;
`importer.py` seeds a repository from a v0 ledger or a legacy table. The SQLite ledger stays
local; its `claims` table becomes a rebuildable index later (M22b).

**Tech Stack:** Python ≥3.11, pydantic 2 (already a dependency), PyYAML (new main
dependency), hashlib sha256 (charter §3 names sha256 for the lock), blake3 stays for CAS ids.

**Spec:** `docs/superpowers/specs/2026-09-04-empiricist-v1-charter.md` §0–§5, §8, §9 row 1.
Lineage: `docs/lineage/lem-v3/` (copied in Task 0 from `~/dev/lem`).

## Global Constraints

- Charter F1: nothing rises above HEURISTIC without a PASS evidence entry from a certified
  verifier; F6: promoted claims carry hash-locked evidence and explicit dependencies; a
  change flips standing to STALE, which blocks new promotions on top of it.
- Charter §3: `claims/<id>.yaml`, `claims.lock.json`, `receipts/<id>.json`, `CLAIMS.md`
  rendered never hand-edited; only committed files are hashed.
- Charter §4: `check` runs no verifiers (pre-commit/CI safe).
- Charter §5: `empiricist.claims` imports nothing from `domain/`, `search/`, `campaign/`.
- Charter §9: core stays under twenty thousand lines of Python (today ≈ 12.8k).
- Repo rules: TDD; ruff + fast suite green before every commit; no AI attribution;
  branch `feat/m22a-claim-ledger` → PR → squash-merge.

---

## Task 0: Lineage copy and dependency

- [ ] Copy `lem_evidence_graph_v3.md`, `lem_cognitive_v3.md`, `lem_design_lineage_map_v1.md`
  (from `~/dev/lem/docs/initial_design_packet/md/lem_revised_v3/`) and
  `gpd_vs_lem_2026_03.md` (from `~/dev/lem/docs/roadmap/`) into `docs/lineage/lem-v3/` with
  a short `README.md` naming what the charter absorbs from each (standing/propagation; the
  six review dimensions; exact-hash vs semantic-key → `supersedes`).
- [ ] `uv add pyyaml`; commit `"docs: Lem v3 lineage documents; add pyyaml"`.

## Task 1: Claim file model and YAML codec (`claims/model.py`)

**Interfaces (produces):**
```python
Level = Literal["REFUTED","HEURISTIC","CONJECTURED","VERIFIED_N","CERTIFIED","FORMALIZED"]
Standing = Literal["CURRENT","STALE","CHALLENGED","SUPERSEDED"]
Kind = Literal["statement","dataset","construction"]
class EvidenceEntry(BaseModel): path: str; verifier: str; version: str; verdict: Literal["PASS","FAIL","ERROR"]; stamped: str (ISO); binary_hash: str|None; golden_suite_hash: str|None; note: str = ""
class ClaimFile(BaseModel):
    id: str (regex ^[A-Za-z0-9][A-Za-z0-9._:-]{0,120}$); problem: str; formulation_version: str
    kind: Kind; statement: str; level: Level; substatus: Literal["PROVED_DRAFT"]|None = None
    n: int|None = None; coverage: Literal["exhaustive","sampled"]|None = None   # VERIFIED_N only
    standing: Standing = "CURRENT"; depends_on: list[str] = []   # claim ids OR repo-relative paths
    supersedes: list[str] = []; evidence: list[EvidenceEntry] = []; receipts: list[str] = []
    notes: str = ""; updated: str (ISO date)
    # validators: VERIFIED_N requires n; non-VERIFIED_N forbids n/coverage; ids unique per repo
def load_claim(path) -> ClaimFile; def dump_claim(claim) -> str (yaml, sorted keys, block style)
def claim_path(repo, claim_id) -> Path   # <repo>/claims/<id>.yaml
def load_all(repo) -> dict[str, ClaimFile]   # raises ClaimSchemaError with the file name on any defect
```
- [ ] Tests (`tests/test_claims_model.py`): round-trip is byte-stable; a bad level / a
  VERIFIED_N without `n` / an unknown key / a malformed id raise `ClaimSchemaError` naming
  the field; `load_all` reports duplicate ids (a file whose `id` differs from its filename).
- [ ] Implement; commit `"claims: claim-file schema and YAML codec"`.

## Task 2: The lock (`claims/lock.py`)

**Interfaces:**
```python
def sha256_file(path) -> str
class LockEntry(BaseModel): sha256: str; verifier: dict|None   # {name, version, binary_hash, golden_suite_hash}
class Lock(BaseModel): version: int = 1; files: dict[str, LockEntry]   # key = repo-relative path
def lock_path(repo) -> Path   # <repo>/claims.lock.json
def read_lock(repo) -> Lock (empty if absent); def write_lock(repo, lock) -> None (sorted keys, 2-space indent, trailing newline)
def lock_paths_for(claim) -> list[str]   # every evidence path + every path-shaped dependency
def refresh_lock_entries(repo, claim, lock) -> Lock   # (re)hash the claim's paths now; used by importers/promote
def mismatches(repo, claims) -> dict[str, list[str]]   # claim id -> paths whose sha differs or that are missing/unlocked
```
- [ ] Tests: hashing a temp file; a claim whose evidence path is not in the lock is a
  mismatch; editing the file is a mismatch; paths outside the repo (`../x`, absolute) are
  rejected at claim load (validator in model: repo-relative, no `..`).
- [ ] Implement; commit `"claims: hash lock"`.

## Task 3: Standing (`claims/standing.py`)

**Interfaces:**
```python
class Receipt(BaseModel): id; claim_id; statement_sha256; evidence_sha256: list[str]; reviewer: str; findings: list[Finding]; verdict: Literal["PASS","REVISE","BLOCK"]; closes: str|None; created: str
class Finding(BaseModel): dimension: Literal["evidence_support","assumption_explicitness","internal_consistency","ledger_consistency","confidence_calibration","decision_soundness"]; severity: Literal["note","warning","blocking"]; text: str
def load_receipts(repo) -> dict[str, Receipt]   # receipts/<id>.json
def dependency_graph(claims) -> dict[str, list[str]]   # claim-id deps only
def find_cycle(graph) -> list[str]|None
def compute_standing(claims, lock_mismatches, receipts, registry_newer: Callable[[EvidenceEntry], bool]) -> dict[str, Standing]
```
Rules (charter §3): SUPERSEDED if some other claim lists it in `supersedes`; CHALLENGED if a
receipt with a `blocking` finding exists that no later receipt `closes`; STALE if any lock
mismatch, or `registry_newer(entry)` for any PASS evidence entry, or any dependency is
STALE/SUPERSEDED or has level REFUTED; STALE propagates forward along `depends_on` (DAG,
topological order); otherwise CURRENT. `registry_newer` is injected (M22b wires the SQLite
registry; `check` passes a constant False).
- [ ] Tests: each rule alone; propagation two levels deep; a cycle raises `ClaimGraphError`;
  a dependency naming an unknown id is an error; a closed blocking receipt returns to
  CURRENT; SUPERSEDED beats STALE in the reported standing.
- [ ] Implement; commit `"claims: standing derivation with propagation"`.

## Task 4: `check` and `render` (`claims/check.py`, `claims/render.py`, CLI)

**Interfaces:**
```python
class CheckIssue(BaseModel): code: str; claim_id: str|None; detail: str
class CheckReport(BaseModel): claims: int; issues: list[CheckIssue]; standings: dict[str, Standing]
    ok -> no issue with a blocking code
def check(repo) -> CheckReport
def render_claims_md(repo, claims, standings) -> str; def write_claims_md(repo, ...) -> Path
```
Blocking codes: `schema_error`, `graph_cycle`, `unknown_dependency`, `lock_mismatch`
(the claim is STALE), `elevated_without_pass` (level > HEURISTIC with no PASS entry),
`current_on_noncurrent` (a CURRENT claim depends on a non-CURRENT one), `claims_md_stale`
(the committed `CLAIMS.md` differs from the render). Non-blocking: `imported_unverified`
(evidence verifier `table-import`). CLI: `empiricist claims check --repo R [--write-md]`
(exit 1 on blocking issues), `empiricist claims report --repo R` (writes `CLAIMS.md`).
`CLAIMS.md` format: the death_and_gravity table (`id | problem | statement | level |
standing | evidence | updated`), rows sorted by id, with a header line stating it is
rendered by `empiricist claims report` and must not be hand-edited.
- [ ] Tests: a consistent mini-repo passes; each blocking code triggered; `--write-md`
  refreshes the table; the CLI exit codes.
- [ ] Implement; commit `"claims: check and CLAIMS.md render"`.

## Task 5: Importers (`claims/importer.py`, CLI)

**(a) From an Empiricist ledger** (`empiricist claims import-ledger --run-dir R --repo D --problem-prefix P3`):
for every artifact with status ≥ CONJECTURED (or REFUTED) that has a canonical claim row:
write the artifact's CAS content to `claims/evidence/<artifact-id[:16]>.<ext>` (`.lean` for
kind lean, `.json` otherwise), create `claims/<id>.yaml` with `id = f"{problem}.{family or title-slug}"`
(dedupe with a numeric suffix), `kind` mapped (lean/certificate → statement, dataset →
dataset, construction → construction), level = status, substatus/n/coverage carried,
evidence entries from PASS/FAIL rows (verifier, version, binary_hash, golden_suite_hash,
stamped = created_at), notes = title + statement, and lock entries. Idempotent: re-running
updates in place.
**(b) From a legacy table** (`empiricist claims import-table --file CLAIMS.md --repo D`):
parse the markdown table; each row → a claim file with `kind = statement`, level as
recorded (REFUTED allowed), evidence entries `verifier = "table-import"`, verdict PASS,
`path` per semicolon-separated evidence path that exists in the repo (missing paths become
notes and an `imported_unverified` issue), `updated` from the row; lock entries for the
existing paths.
- [ ] Tests: import a tmp Empiricist ledger built with the existing fixtures (one FORMALIZED
  lean artifact via the reverify test stub, one CERTIFIED certificate via
  `ingest_p3_certificate`) → files exist, `check` passes, re-import is idempotent; import
  the first six rows of death_and_gravity's table copied verbatim into a fixture → six
  claim files, missing evidence paths reported, `check` passes with `imported_unverified`
  notes only.
- [ ] Implement; commit `"claims: importers from a v0 ledger and a legacy CLAIMS.md"`.

## Task 6: Campaign actions (no code)

- [ ] Import `runs/p3-campaign`, `runs/p5-formalize`, `runs/p5-live` into THIS repo's
  `claims/` (the `ftfbqc` claims) and commit the rendered `CLAIMS.md`; `check` must be green
  in CI (add it to the workflow).
- [ ] Import death_and_gravity's `CLAIMS.md` into that repo on a branch (do not commit there
  without Sean: propose the branch), run `check`, and record the outcome in the M22b plan.

## Self-review

Charter §3 fields all have a home (`n`/coverage on VERIFIED_N, PROVED_DRAFT as substatus,
receipts referenced by id, notes); §4 `check` is pure and pre-commit safe; §5 the package
imports only `empiricist.ledger.models` enums (core); §8 lineage copied; §9 line budget
respected (estimate +1.5k lines).

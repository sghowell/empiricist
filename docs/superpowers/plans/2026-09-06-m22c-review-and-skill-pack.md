# M22c: `review`, receipts, verifier drift, skill pack, death_and_gravity end-to-end

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the charter's 2026-09-18 deliverable: `review` writes receipts (model reviewer with bounty framing and two samples for elevated promotions, or a recorded human review), `check` catches a changed verifier, a skill pack installs the interactive workflow into a research repository, and one death_and_gravity claim reaches CERTIFIED through `promote` with a receipt.

**Architecture:** `claims/review.py` builds a review bundle from the claim file, its evidence bytes (capped), its dependencies' statements and the target level, calls the existing `LLMClient` with a new `reviewer` role and a closed `ReviewOut` schema (fresh context per sample, provenance in a repo-local, gitignored ledger under `.empiricist/`), and writes one `receipts/<id>.json` per sample; a human review is the same receipt written from CLI arguments. `check` additionally hashes every command-verifier declaration's inputs and compares them to the committed registry stamp, so an edited checker makes its claims STALE without running anything. The skill pack is package data copied into `<repo>/.claude/skills/`.

**Tech Stack:** Python 3.11+, pydantic 2, PyYAML, the harness `LLMClient` (`ClaudeCodeClient`, `FakeLLMClient` for tests), SQLite ledger + blake3 CAS for provenance.

**Spec:** `docs/superpowers/specs/2026-09-04-empiricist-v1-charter.md` (sections 3, 4, 6); lineage `docs/lineage/lem-v3/` (six review dimensions, blocking objections never auto-promote).

## Global Constraints

- The model never gets a shell: the reviewer receives a bundle and returns structured JSON; nothing it says changes a level except through a receipt that `promote` reads.
- Nothing rises above HEURISTIC without a PASS evidence entry from a certified verifier (F1); elevated promotions of `statement` claims require a receipt with no blocking finding (F4).
- `check` runs no verifiers and writes nothing.
- Every model call is a `runs` row with request/response receipts (provenance); receipts are plain JSON in the research repository.
- No AI attribution in commit messages. Branch `feat/m22c-review`, stacked on `feat/m22b-promote`.
- Cost: the death_and_gravity review is two reviewer samples at MAX effort (~$5–10); nothing else spends.

---

### Task 1: Verifier drift is STALE (`check` sees an edited checker)

**Files:**
- Modify: `src/empiricist/claims/command_verifier.py` (add `declared_verifiers(repo) -> dict[str, CommandVerifier]`, loading every `claims/verifiers/*.yaml`; errors become `(name, message)` pairs)
- Modify: `src/empiricist/claims/check.py` (new issue codes `verifier_drift` and `verifier_declaration_error`; feed drift into standing)
- Modify: `src/empiricist/claims/registry.py` (`registry_newer` gains an optional `drifted: set[str]` so evidence from a drifted verifier counts as newer-registry STALE)
- Test: `tests/test_claims_check.py`

**Interfaces:**
- Produces: `declared_verifiers(repo) -> tuple[dict[str, CommandVerifier], list[tuple[str, str]]]`; `check(repo, ..., drift: bool = True)`; issue codes `verifier_drift` (non-blocking; the claims go STALE) and `verifier_declaration_error` (blocking).

- [ ] **Step 1: Write the failing test**

```python
def test_edited_checker_makes_its_claims_stale(tmp_path):
    repo = _command_repo(tmp_path)              # the toy tools/check.py repo from test_claims_promote
    certify_command_verifier(repo, "toy")
    formulate(repo, claim_id="P.x", problem="P", formulation_version="v1", kind="dataset", statement="x")
    promote(repo, claim_id="P.x", level="VERIFIED_N", verifier="toy", evidence_path="certs/good.json", n=1)
    assert check(repo).standings == {"P.x": "CURRENT"}
    (repo / "tools" / "check.py").write_text(_CHECKER + "\n# edited\n")
    rep = check(repo)
    assert rep.standings == {"P.x": "STALE"}
    assert any(i.code == "verifier_drift" and "toy" in i.detail for i in rep.issues)
    assert certify_command_verifier(repo, "toy")[0] is not None
    assert reverify(repo) == {"P.x": "re-verified"} and check(repo).standings == {"P.x": "CURRENT"}
```

- [ ] **Step 2: Run it** — `uv run pytest tests/test_claims_check.py -k drift -q` — FAIL (`declared_verifiers` undefined).
- [ ] **Step 3: Implement** `declared_verifiers`; in `check`, after reading the registry: for each declaration whose `binary_hash` differs from its stamp, add `verifier_drift` and put the name in `drifted`; pass `registry_newer(repo, drifted=drifted)` so `compute_standing` marks evidence from that verifier stale. A declaration that fails to load is `verifier_declaration_error` (blocking). Keep `check` pure (hashing only).
- [ ] **Step 4: Run** the claims suites — PASS. **Step 5: Commit** `claims: an edited command verifier makes its claims STALE`.

### Task 2: Receipts get provenance; `review --human` writes one

**Files:**
- Modify: `src/empiricist/claims/standing.py` (`Receipt.provenance: dict[str, str] | None = None`, `Receipt.target_level: Level | None = None`; `new_receipt_id(claim_id, reviewer, created, existing) -> str` = `<claim>.<YYYYMMDD>.<slug>.<k>` unique, filename-safe)
- Create: `src/empiricist/claims/review.py` (`record_human_review(repo, *, claim_id, reviewer, verdict, findings, closes=None, target_level=None, now=None) -> Receipt`: statement hash from the claim, evidence hashes from the lock; refuses an unknown claim, a `closes` that is not a receipt of the same claim, or a PASS verdict with a blocking finding)
- Modify: `src/empiricist/cli.py` (`claims review --repo R --id C --human --reviewer NAME --verdict PASS|REVISE|BLOCK [--finding DIM:SEV:TEXT ...] [--closes RID] [--target-level L]`)
- Test: `tests/test_claims_review.py`

- [ ] **Step 1: Failing test** — a human BLOCK receipt makes the claim CHALLENGED; a later human PASS receipt with `closes` returns it to CURRENT; `promote --level CERTIFIED --receipt <pass-id>` then succeeds; `receipt_stale` fires after editing the statement.
- [ ] **Step 2: Run** — FAIL. **Step 3: Implement.** **Step 4: Run** — PASS. **Step 5: Commit** `claims: human review receipts`.

### Task 3: The model reviewer (bounty framing, fresh context, two samples for elevated)

**Files:**
- Modify: `src/empiricist/llm/roles.py` (`reviewer` role: "You are paid only for concrete defects in one of six dimensions ...; NO_DEFECT is a failure unless you list every dimension you checked and what you checked it against"; effort MAX, k=2)
- Modify: `src/empiricist/llm/schemas.py` (`ReviewFinding(dimension, severity, text, where)`, `ReviewOut(findings: list[ReviewFinding], verdict: Literal["PASS","REVISE","BLOCK"], checked: list[Dimension])`, closed)
- Modify: `src/empiricist/claims/review.py` (`build_review_bundle(repo, claim, *, target_level, byte_cap=64_000) -> str` — statement, kind, formulation version, target level, evidence entries with verifier identity and the evidence files' text (capped, hashed), dependency ids + statements + standings, notes; `review_with_model(repo, *, claim_id, client, samples, run_dir, target_level, now=None) -> list[Receipt]` — one `client.complete` per sample with `run_id="review-<claim>-<nonce>-s<k>"`, ledger at `run_dir/ledger.db`, store at `run_dir/store`; a sample whose output does not parse is recorded as a receipt with verdict REVISE and a `ledger_consistency` warning "reviewer returned no parseable review" so the spend is never silent; each receipt carries `provenance={"run_id", "model", "request_digest", "response_digest"}`)
- Modify: `src/empiricist/cli.py` (`claims review --repo R --id C [--samples N] [--target-level L] [--run-dir DIR]`; default `run_dir = <repo>/.empiricist`; default samples = 2 when the target level is CERTIFIED/FORMALIZED, else 1)
- Test: `tests/test_claims_review.py` with `FakeLLMClient` returning a canned `ReviewOut` (one BLOCK sample + one PASS sample → CHALLENGED; two PASS → promote to CERTIFIED succeeds; unparseable → REVISE receipt)

- [ ] **Step 1: Failing tests** as listed. **Step 2: Run** — FAIL. **Step 3: Implement.** **Step 4: Run** — PASS; `uv run ruff check src tests` clean. **Step 5: Commit** `claims: model review with bounty framing writes receipts`.

### Task 4: Skill pack + installer

**Files:**
- Create: `src/empiricist/claims/skill/SKILL.md` (frontmatter `name: empiricist-claims`, `description: ...`; the interactive workflow: formulate → certify-verifier (declaration + PASS/FAIL fixtures, the `tools/empiricist_check.py`-style adapter convention) → promote → review → promote to CERTIFIED → check/report; what each refusal means; never hand-edit CLAIMS.md, standings, or levels)
- Create: `src/empiricist/claims/skill/adapter_template.py` (the generic checker adapter from the death_and_gravity trial, documented as a template)
- Modify: `src/empiricist/claims/install.py` (new: `install_skill(repo) -> list[Path]`: copies SKILL.md to `<repo>/.claude/skills/empiricist-claims/SKILL.md`, the adapter template to `<repo>/tools/empiricist_check.py` only if absent, appends `.empiricist/` to `.gitignore` if missing; idempotent)
- Modify: `pyproject.toml` (package data for `empiricist.claims.skill`), `src/empiricist/cli.py` (`claims install-skill --repo R`)
- Test: `tests/test_claims_install.py`

- [ ] **Step 1: Failing test** — install twice → same files, `.gitignore` has one `.empiricist/` line, an existing `tools/empiricist_check.py` is not overwritten. **Steps 2–5** as above; commit `claims: skill pack and installer`.

### Task 5: death_and_gravity end-to-end (the deliverable)

On the trial worktree (branch `empiricist-claims-import`, commit c17c356 and later):

- [ ] `uv run --project ~/dev/empiricist empiricist claims install-skill --repo <dg>`; commit.
- [ ] `claims review --repo <dg> --id P8-A.7 --target-level CERTIFIED` (two reviewer samples, MAX effort; provenance under `<dg>/.empiricist/`, gitignored). Read both receipts. If a blocking finding is real, leave the claim CHALLENGED and record the finding in the science note; do not close it with a model receipt.
- [ ] If both samples pass: `claims promote --repo <dg> --id P8-A.7 --level CERTIFIED --verifier p8a_remainder --evidence <cert> --receipt <id>`; `claims check --repo <dg> --min-claims 50` green; `report`; commit.
- [ ] Drift demonstration: append a comment to the p8a_remainder checker → `check` shows `verifier_drift` and P8-A.7 STALE → `certify-verifier` → `reverify` → CURRENT; revert the comment; commit nothing from this step (evidence in the science note).
- [ ] Science note `docs/science/2026-09-xx-claims-trial-death-and-gravity.md`: the import (51 rows, 2 recovered), the certified verifier, the two receipts (verdicts, findings, cost), what a second problem's verifier would need, and the open question of restoring the other 46 legacy levels (one verifier declaration per checker package; the adapter makes it mechanical).
- [ ] Charter table: mark the 2026-09-18 row with what counts (`check` green there; one promotion through `promote` with a receipt) and note the first genuine stale catch if the drift step counts.

### Deferred (explicit)

- `formulate --verifier/--evidence-glob` (declaring a certificate interface up front).
- Batch-mode `review` (the ledger's gate queue) and multi-sample aggregation policies beyond "any blocking sample blocks".
- The cosmology pack (2026-10-02 row).


---

## Outcome (2026-09-06)

- Tasks 1–3 merged as PR #72; Task 4 (skill pack + installer) and the trial note in PR #73,
  together with two changes the trial forced: `closes` is a list (two-sample reviews block
  in pairs), and a fresh sample without a blocking finding closes the blocks it was asked
  to close; the bundle gives each evidence file a fair share.
- Task 5, on the trial branch (`empiricist-claims-import`, pushed): the skill is
  installed; P8-A.7 was reviewed twice. Round 1 blocked on a real record defect (no
  dependency edges); the record was corrected; round 2 raised no blocking finding but
  would not sign CERTIFIED over HEURISTIC dependencies. The promotion with a receipt is
  therefore still open: it needs either a human receipt closing the blocks and a decision
  on dependency levels, or the P8(a) chain re-earned bottom-up. Details in
  `docs/science/2026-09-06-claims-trial-death-and-gravity.md`.
- Deferred (unchanged) plus: derive `depends_on` from certificate pins at import; a
  pytest-suite verifier shape (a FAIL fixture that is a failing test module); the
  dependency-level rule.

# M23a: ledger hygiene — relabel, supersede, built-in verifier drift, certificate reverify

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repository's own claim ledger tell the truth: the fourteen P3 Lean lemmas filed under P5 are relabelled through an auditable path, conjectures that FORMALIZED theorems now prove are marked superseded, a vacuous `True` "theorem" is demoted with a receipt, `check` sees when a built-in verifier (Lean, SOS certificate, exact witness) changes under a promoted claim, and certificate evidence can be re-earned the way Lean evidence already can.

**Architecture:** The v0 ledger (SQLite per run directory) stays the system of record; a relabel is a `Ledger` method that rewrites the artifact's `problem` column and leaves a `runs` row as its audit trail. The v1 importer, on seeing an artifact whose problem no longer matches its materialised claim, mints a new claim under the new problem prefix that `supersedes` the old one (the old file is never touched; its standing derives to SUPERSEDED). `check` compares committed registry stamps of built-in verifiers against the live identities exported by `empiricist.verifiers.builtin`. `reverify` grows a certificate pass mirroring the Lean pass. Lean ingest refuses a statement that is literally `True` and no longer defaults `problem` to P5.

**Tech Stack:** Python 3.11+, SQLite ledger + blake3 CAS, pydantic 2 claim files, pytest.

**Spec:** `docs/superpowers/specs/2026-09-04-empiricist-v1-charter.md` (sections 1, 3, 5); `docs/science/2026-09-05-trust-hygiene.md` (the Lean reverify precedent).

## Global Constraints

- Statuses change only alongside evidence rows (v0) or receipts (v1); REFUTED is terminal; nothing rises above HEURISTIC without a PASS from a certified verifier.
- `check` runs no verifiers and writes nothing; it may compute hashes.
- Claim files are never deleted; a replaced claim is superseded and its row kept.
- The ledger DB and CAS are never committed; backups go under `runs/_backup-<date>/`.
- Editing `verifiers/lean.py` changes `LeanVerifier.binary_hash`; every ledger that will ingest Lean again must be re-certified (`empiricist reverify`) before use, and the v1 registry stamp follows through `import-ledger`.
- No AI attribution in commit messages. Branch `feat/m23a-ledger-hygiene` off `main`.
- Model spend: one reviewer sample on the vacuous claim (~$2.50). Nothing else spends.

---

### Task 1: `Ledger.relabel_artifact` and `empiricist relabel`

**Files:**
- Modify: `src/empiricist/ledger/db.py` (after `get_artifact`)
- Modify: `src/empiricist/cli.py` (parser next to `audit`; dispatch in `main`)
- Test: `tests/test_ledger.py`, `tests/test_cli.py`

**Interfaces:**
- Produces: `Ledger.relabel_artifact(artifact_id: str, *, problem: str, note: str) -> Artifact` — rewrites `artifacts.problem`, inserts a finished `runs` row (`move="relabel"`, `argv` = canonical JSON of `{artifact_id, from, to, note}`, `exit_code=0`) in the same transaction; raises `KeyError` for an unknown artifact and `ValueError` when `problem` is already the artifact's problem or empty.
- CLI: `empiricist relabel --run-dir R --artifact ID --problem P3 --note "..."` prints `relabel: <id12> P5 -> P3 (run <run_id>)`, exit 0; exit 1 with `error: ...` on refusal.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ledger.py (append)
def test_relabel_artifact_rewrites_problem_and_leaves_a_run_row(ledger, store):
    art = make_artifact(store, problem="P5")
    ledger.add_artifact(art)
    out = ledger.relabel_artifact(art.id, problem="P3", note="mis-defaulted at ingest")
    assert out.problem == "P3" and ledger.get_artifact(art.id).problem == "P3"
    rows = ledger.conn.execute("SELECT * FROM runs WHERE move = 'relabel'").fetchall()
    assert len(rows) == 1
    run = ledger.get_run(rows[0]["run_id"])
    assert run.exit_code == 0 and run.ended is not None
    import json
    assert json.loads(run.argv) == {
        "artifact_id": art.id, "from": "P5", "to": "P3", "note": "mis-defaulted at ingest",
    }


def test_relabel_artifact_refuses_unknown_same_or_empty(ledger, store):
    art = make_artifact(store, problem="P5")
    ledger.add_artifact(art)
    with pytest.raises(KeyError):
        ledger.relabel_artifact("nope", problem="P3", note="x")
    with pytest.raises(ValueError):
        ledger.relabel_artifact(art.id, problem="P5", note="x")
    with pytest.raises(ValueError):
        ledger.relabel_artifact(art.id, problem="  ", note="x")
    assert ledger.conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
```

```python
# tests/test_cli.py (append)
def test_relabel_cli_rewrites_problem(tmp_path, capsys):
    from empiricist.ledger.db import Ledger
    from empiricist.ledger.models import Artifact, Status
    from empiricist.store import Store

    run_dir = tmp_path / "run"
    lg = Ledger(run_dir / "ledger.db")
    digest = Store(run_dir / "store").put(b"lemma")
    lg.add_artifact(Artifact(id=digest, kind="lean", problem="P5", title="Empiricist.x",
                             content_path=digest, status=Status.FORMALIZED))
    lg.close()
    rc = main(["relabel", "--run-dir", str(run_dir), "--artifact", digest,
               "--problem", "P3", "--note", "P3 lemma ingested under the P5 default"])
    assert rc == 0
    assert f"relabel: {digest[:12]} P5 -> P3" in capsys.readouterr().out
    lg = Ledger(run_dir / "ledger.db")
    assert lg.get_artifact(digest).problem == "P3"
    lg.close()
    rc = main(["relabel", "--run-dir", str(run_dir), "--artifact", digest,
               "--problem", "P3", "--note", "again"])
    assert rc == 1 and "error:" in capsys.readouterr().err
```

- [ ] **Step 2: Run them to verify they fail** — `uv run pytest tests/test_ledger.py -k relabel tests/test_cli.py -k relabel -q` → `AttributeError: 'Ledger' object has no attribute 'relabel_artifact'` / argparse error.

- [ ] **Step 3: Implement**

```python
# src/empiricist/ledger/db.py, after get_artifact
    def relabel_artifact(self, artifact_id: str, *, problem: str, note: str) -> Artifact:
        """Correct an artifact's `problem` label. The label is metadata (the id is the
        content digest; the status lattice is untouched), so this is not a status
        change -- but it is an act on the record, so it leaves a finished `runs` row
        (move='relabel') whose argv is the canonical JSON of what changed, in the same
        transaction as the rewrite."""
        new = problem.strip()
        if not new:
            raise ValueError("problem must be non-empty")
        art = self.get_artifact(artifact_id)  # KeyError when unknown
        if art.problem == new:
            raise ValueError(f"artifact {artifact_id[:12]} is already filed under {new}")
        run = Run(
            run_id=f"relabel-{uuid.uuid4().hex[:12]}", move="relabel",
            argv=json.dumps({"artifact_id": artifact_id, "from": art.problem, "to": new,
                             "note": note}, sort_keys=True),
            exit_code=0, ended=now_iso(), wall_s=0.0,
        )
        with self._tx() as c:
            c.execute("UPDATE artifacts SET problem = ? WHERE id = ?", (new, artifact_id))
            c.execute(
                "INSERT INTO runs (run_id, move, role, model, provider,"
                " reasoning_mode, reasoning_effort, auth_route, request_digest,"
                " response_digest, argv, seed, config_hash,"
                " env_fingerprint, tokens_in, tokens_out, cache_read, cost_usd,"
                " peak_rss_mb, exit_code, started, ended, wall_s)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,"
                " ?, ?, ?, ?)",
                (run.run_id, run.move, run.role, run.model, run.provider,
                 run.reasoning_mode, run.reasoning_effort, run.auth_route,
                 run.request_digest, run.response_digest, run.argv, run.seed,
                 run.config_hash, run.env_fingerprint, run.tokens_in, run.tokens_out,
                 run.cache_read, run.cost_usd, run.peak_rss_mb, run.exit_code,
                 run.started, run.ended, run.wall_s),
            )
        return self.get_artifact(artifact_id)
```

(Import `json`, `uuid` at the top of `db.py` if absent; `Run`, `now_iso` come from `ledger.models`.)

```python
# src/empiricist/cli.py: parser (after audit_p)
    relabel_p = sub.add_parser(
        "relabel", help="correct an artifact's problem label (leaves a runs row)"
    )
    relabel_p.add_argument("--run-dir", required=True, type=Path)
    relabel_p.add_argument("--artifact", required=True, help="artifact id (content digest)")
    relabel_p.add_argument("--problem", required=True)
    relabel_p.add_argument("--note", required=True, help="why the label was wrong")

# handler
def _cmd_relabel(args: argparse.Namespace) -> int:
    ledger_path = args.run_dir / "ledger.db"
    if not ledger_path.is_file():
        print(f"error: campaign ledger does not exist: {ledger_path}", file=sys.stderr)
        return 1
    ledger = Ledger(ledger_path)
    try:
        before = ledger.get_artifact(args.artifact).problem
        after = ledger.relabel_artifact(args.artifact, problem=args.problem, note=args.note)
        run_id = ledger.conn.execute(
            "SELECT run_id FROM runs WHERE move = 'relabel' ORDER BY rowid DESC LIMIT 1"
        ).fetchone()["run_id"]
    except (KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        ledger.close()
    print(f"relabel: {after.id[:12]} {before} -> {after.problem} (run {run_id})")
    return 0

# main(): if args.command == "relabel": return _cmd_relabel(args)
```

- [ ] **Step 4: Run the tests** — same command → PASS. Run `uv run pytest tests/test_ledger.py tests/test_cli.py tests/test_ledger_audit.py -q` (audit must accept the relabel run row: it has no receipts and no model).
- [ ] **Step 5: Commit** — `git commit -am "M23a: Ledger.relabel_artifact and the relabel command (runs row as audit trail)"`

---

### Task 2: A relabelled artifact materialises as a superseding claim

**Files:**
- Modify: `src/empiricist/claims/importer.py` (`materialize_artifacts`)
- Test: `tests/test_claims_importer.py`

**Interfaces:**
- Consumes: `Ledger.relabel_artifact` (Task 1); `ClaimFile.supersedes`, `compute_standing` (existing).
- Produces: in `materialize_artifacts`, when the claims already sourced from `art.id` contain none whose `problem == art.problem`, a new claim `<art.problem>.<slug>` is written with `supersedes=[prev.id]`, `depends_on=prev.depends_on`, notes `"relabelled from <prev.problem> (<prev.id>) after the ledger corrected the artifact's problem; " + <the usual notes>`; the previous claim's file is not touched; `by_artifact` prefers the claim whose problem matches the artifact so a further re-import updates the new claim only.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_claims_importer.py (append)
def test_relabelled_artifact_materializes_as_a_superseding_claim(tmp_path):
    run_dir = _v0_ledger(tmp_path)
    repo = tmp_path / "repo"
    import_ledger(run_dir, repo)
    old = load_all(repo)["P3.Empiricist.foo"]
    lg = Ledger(run_dir / "ledger.db")
    lg.relabel_artifact(old.source.ref, problem="P5", note="test")
    lg.close()
    rep = import_ledger(run_dir, repo)
    assert "P5.Empiricist.foo" in rep.written and "P3.Empiricist.foo" not in rep.written
    claims = load_all(repo)
    new, kept = claims["P5.Empiricist.foo"], claims["P3.Empiricist.foo"]
    assert new.supersedes == ["P3.Empiricist.foo"] and new.problem == "P5"
    assert new.level == "FORMALIZED" and new.evidence == kept.evidence
    assert new.source.ref == kept.source.ref and "relabelled from P3" in new.notes
    assert kept == old  # the superseded file is untouched
    report = check(repo)
    assert report.ok
    assert report.standings["P3.Empiricist.foo"] == "SUPERSEDED"
    assert report.standings["P5.Empiricist.foo"] == "CURRENT"
    # idempotent: a third import touches the new claim only
    rep3 = import_ledger(run_dir, repo)
    assert "P5.Empiricist.foo" in rep3.written and len(load_all(repo)) == 3
```

- [ ] **Step 2: Run it** — `uv run pytest tests/test_claims_importer.py -k relabelled -q` → FAIL (`P5.Empiricist.foo` absent; the P3 claim gets `problem: P5` in place).

- [ ] **Step 3: Implement** — in `materialize_artifacts`, replace the `by_artifact` construction and the `if art.id in by_artifact:` branch:

```python
    by_artifact: dict[str, list[str]] = {}
    for cid, c in existing.items():
        ref = _ledger_ref(c)
        if ref:
            by_artifact.setdefault(ref, []).append(cid)
    ...
        sourced = by_artifact.get(art.id, [])
        same_problem = [cid for cid in sourced if existing[cid].problem == art.problem]
        if same_problem:
            prev = existing[same_problem[0]]
            ... (existing keep_level / evidence-merge branch, unchanged)
            claim = revalidate(prev.model_copy(update=derived))
        elif sourced:
            # The ledger relabelled this artifact: the earlier materialisation stays as a
            # superseded row; the new problem gets its own claim carrying the same evidence.
            prev = existing[max(sourced, key=lambda cid: (existing[cid].updated, cid))]
            prefix = id_prefix or art.problem
            family = canonical.family if canonical and canonical.family else art.title
            cid = _unique_id(f"{prefix}.{_slug(family)}", taken)
            derived["evidence"] = entries + [e for e in prev.evidence if e not in entries]
            derived["updated"] = max(prev.updated, derived["updated"])
            claim = ClaimFile(
                id=cid, depends_on=list(prev.depends_on), supersedes=[prev.id],
                notes=(f"relabelled from {prev.problem} ({prev.id}) after the ledger "
                       f"corrected the artifact's problem; {notes}"),
                **derived,
            )
        else:
            ... (existing new-claim branch)
        save_claim(repo, claim)
        existing[claim.id] = claim
        taken.add(claim.id)
        by_artifact.setdefault(art.id, []).append(claim.id)
```

- [ ] **Step 4: Run** — `uv run pytest tests/test_claims_importer.py tests/test_claims_materialize.py -q` → PASS.
- [ ] **Step 5: Commit** — `git commit -am "M23a: a relabelled artifact materializes as a superseding claim"`

---

### Task 3: Built-in verifier drift is visible to `check`

**Files:**
- Create: `src/empiricist/verifiers/builtin.py`
- Modify: `src/empiricist/claims/check.py` (`drifted_verifiers`, the `verifier_drift` message)
- Test: `tests/test_claims_check.py`

**Interfaces:**
- Produces: `builtin_identity(name: str) -> tuple[str, str] | None` — `(version, binary_hash)` of the live `lean` / `sos_certificate` / `p3_exact_witness` verifier, `None` for unknown names or when the live verifier cannot be constructed (no Lean project on disk, import error).
- `drifted_verifiers(repo)` additionally marks a registry stamp drifted when `builtin_identity(name)` exists and differs in version or binary hash (only for names without a command-verifier declaration). Message: `"verifier {name}: the live {name} ({version} {hash[:12]}) is not the stamped identity ({sv} {sh[:12]}); its evidence is STALE until it is re-certified and its claims re-verified (`reverify` + `import-ledger`)"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_claims_check.py (append)
def test_builtin_verifier_drift_makes_its_evidence_stale(tmp_path, monkeypatch):
    from empiricist.claims import check as check_mod
    from empiricist.claims.model import EvidenceEntry, save_claim
    from empiricist.claims.registry import stamp
    from empiricist.claims.check import refresh_repo
    ev = tmp_path / "claims" / "evidence"; ev.mkdir(parents=True)
    (ev / "a.lean").write_text("theorem a : 1 = 1 := rfl")
    save_claim(tmp_path, _claim("P3.a", level="FORMALIZED", evidence=[EvidenceEntry(
        path="claims/evidence/a.lean", verifier="lean", version="3.3", verdict="PASS",
        stamped="2026-09-05T00:00:00Z", binary_hash="ab" * 32, golden_suite_hash="g")]))
    stamp(tmp_path, name="lean", version="3.3", binary_hash="ab" * 32, golden_suite_hash="g")
    refresh_repo(tmp_path)
    monkeypatch.setattr(check_mod, "builtin_identity", lambda name: ("3.3", "ab" * 32))
    assert check(tmp_path).ok and check(tmp_path).standings["P3.a"] == "CURRENT"
    monkeypatch.setattr(check_mod, "builtin_identity", lambda name: ("3.3", "cd" * 32))
    rep = check(tmp_path)
    assert rep.standings["P3.a"] == "STALE"
    assert [i.code for i in rep.issues if i.code == "verifier_drift"] == ["verifier_drift"]
    monkeypatch.setattr(check_mod, "builtin_identity", lambda name: None)
    assert check(tmp_path).standings["P3.a"] == "CURRENT"   # unknown live identity: no claim
```

(`_claim` is the file's existing helper; adapt its name if it differs.)

- [ ] **Step 2: Run** — FAIL (`builtin_identity` missing).

- [ ] **Step 3: Implement**

```python
# src/empiricist/verifiers/builtin.py
"""Live identities of the verifiers this package ships, for `claims check`."""
from __future__ import annotations

from collections.abc import Callable

_FACTORIES: dict[str, Callable[[], object]] = {}


def _lean():
    from empiricist.verifiers.lean import LeanVerifier
    return LeanVerifier()


def _sos():
    from empiricist.certificates.verifier import SOSCertificateVerifier
    return SOSCertificateVerifier()


def _p3_exact():
    from empiricist.verifiers.p3_exact import P3ExactVerifier
    return P3ExactVerifier()


_FACTORIES.update({"lean": _lean, "sos_certificate": _sos, "p3_exact_witness": _p3_exact})


def builtin_identity(name: str) -> tuple[str, str] | None:
    """(version, binary_hash) of the live built-in verifier `name`, or None when the name
    is not a built-in or its identity cannot be computed here (e.g. no Lean project)."""
    factory = _FACTORIES.get(name)
    if factory is None:
        return None
    try:
        v = factory()
        return str(v.version), str(v.binary_hash)
    except Exception:  # noqa: BLE001 - an uncomputable identity is "unknown", not drift
        return None
```

In `check.py`: `from empiricist.verifiers.builtin import builtin_identity` at module top; in `drifted_verifiers`, after the command-verifier loop:

```python
    for name, s in reg.stamps.items():
        if name in verifiers:
            continue
        live = builtin_identity(name)
        if live is not None and (live[0] != s.version or live[1] != s.binary_hash):
            drifted.add(name)
```

and make the `verifier_drift` message generic (`"verifier {name}: declaration, inputs or live identity changed since its stamp; its evidence is STALE until it is re-certified and re-verified"`).

- [ ] **Step 4: Run** — `uv run pytest tests/test_claims_check.py tests/test_claims_registry.py -q` → PASS. Then `uv run empiricist claims check --repo . --min-claims 1` → expect exit 1 with `verifier_drift` for `sos_certificate` and `P3.k0_standard_assignment_p_avg` STALE (the genuine catch; Task 6 re-earns it).
- [ ] **Step 5: Commit** — `git commit -am "M23a: check compares built-in verifier stamps to the live identities"`

---

### Task 4: Certificate reverify

**Files:**
- Create: `src/empiricist/certificates/reverify.py`
- Modify: `src/empiricist/cli.py` (`reverify --only {lean,certificates}`; default both)
- Test: `tests/test_certificates_reverify.py`, `tests/test_cli.py`

**Interfaces:**
- Produces: `reverify_certificate_artifacts(ledger, store, *, artifact_ids=None, dry_run=False, certify=True) -> ReverifyReport` (reuse `ReverifyOutcome`/`ReverifyReport` from `verifiers/reverify.py`). Targets: `kind="certificate"`, status CERTIFIED. Dispatch on the latest PASS evidence row's `verifier`: `sos_certificate` → `verify_and_ingest_p3_certificate(certificate_json=json.loads(blob), target=claim.scope["target"], title=art.title)`; `p3_exact_witness` → `verify_and_ingest_exact_witness(witness_json=json.loads(blob), claimed_success=claim.scope["claimed_success"], require_all_identified=claim.scope["require_all_identified"], title=art.title)`. `certify=True` stamps `certify_sos` / the exact suite when the live identity lacks a current PASS certification. A non-PASS result → evidence-only row (`details["reverify"]=True`), no status change. Unknown verifier / missing canonical claim → SKIPPED outcome.

- [ ] **Step 1: Write the failing test** (SOS path with the k0 golden; the exact path with the smallest exact witness fixture used by `tests/test_p3_exact_ingest.py` — copy its helper)

```python
# tests/test_certificates_reverify.py
from empiricist.certificates.goldens import certify_sos, load_k0_golden
from empiricist.certificates.ingest import ingest_p3_certificate
from empiricist.certificates.reverify import reverify_certificate_artifacts
from empiricist.certificates.verifier import SOSCertificateVerifier, certificate_to_json
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Certification, Verdict
from empiricist.store import Store


def test_reverify_certificate_records_a_pass_under_the_live_identity(tmp_path, monkeypatch):
    lg, st = Ledger(tmp_path / "ledger.db"), Store(tmp_path / "store")
    certify_sos(lg, SOSCertificateVerifier())
    art = ingest_p3_certificate(lg, st, certificate_json=certificate_to_json(load_k0_golden()),
                                target="k0_standard_assignment_p_avg", title="k0 cert")
    # simulate an edited checker: the live hash moves, the old stamp stays
    monkeypatch.setattr(SOSCertificateVerifier, "binary_hash",
                        property(lambda self: "cd" * 32))
    rep = reverify_certificate_artifacts(lg, st)
    assert rep.certified_now and [o.verdict for o in rep.outcomes] == ["PASS"]
    rows = lg.evidence_for(art.id)
    assert [r.binary_hash[:4] for r in rows][-1] == "cdcd" and len(rows) == 2
    assert lg.get_artifact(art.id).status.value == "CERTIFIED"
    assert not reverify_certificate_artifacts(lg, st).certified_now   # idempotent
    lg.close()
```

- [ ] **Step 2: Run** — FAIL (module missing).
- [ ] **Step 3: Implement** mirroring `verifiers/reverify.py` (`_targets` filtered on `kind == "certificate"`, per-artifact try/except → ERROR outcome, dispatch table `{"sos_certificate": _rerun_sos, "p3_exact_witness": _rerun_exact}`). CLI: `reverify_p.add_argument("--only", choices=("lean", "certificates"), default=None)`; `_cmd_reverify` runs the Lean pass unless `--only certificates`, then the certificate pass unless `--only lean`, printing both reports; exit 0 iff every executed pass is ok.
- [ ] **Step 4: Run** — `uv run pytest tests/test_certificates_reverify.py tests/test_reverify.py tests/test_cli.py -q` → PASS.
- [ ] **Step 5: Commit** — `git commit -am "M23a: reverify covers certificate artifacts (SOS and exact witness)"`

---

### Task 5: Lean ingest hygiene — `problem` required, vacuous statements refused

**Files:**
- Modify: `src/empiricist/verifiers/lean.py` (`ingest_lean_artifact`, `verify_and_ingest_lean_artifact`, `_record_verified_lean_artifact`)
- Modify: `src/empiricist/formalize/loop.py` (`FormalizeTask.problem` required), `src/empiricist/formalize/feedback.py` (`vacuous` gate message), `src/empiricist/verifiers/reverify.py` (`_reverify_one` → SKIPPED for a vacuous PASS)
- Test: `tests/test_lean_verifier.py` (offline stub tests), `tests/test_formalize_loop.py`, `tests/test_formalize_feedback.py`, `tests/test_reverify.py`; update every `FormalizeTask(...)`/`ingest_lean_artifact(...)` call in tests to pass `problem=`; change `tests/test_formalize_integration.py` "loop-smoke" goal from `Prove True.` to `Prove 1 + 1 = 2.`

**Interfaces:**
- Produces: `class VacuousStatementError(ValueError)` and `def is_vacuous_statement(statement: str) -> bool` (true iff `statement.strip() == "True"`) in `lean.py`. `_record_verified_lean_artifact` raises `VacuousStatementError` before any write. `verify_and_ingest_lean_artifact` returns `(VerifierResult(FAIL, {"gate": "vacuous", "statement": ...}), None)` instead of raising, so the loop feeds back. `ingest_lean_artifact` lets the error propagate. `format_feedback` for gate `vacuous`: `"The headline theorem's statement is `True` -- a placeholder, not a result. State the intended theorem as the declaration's type and prove that."`. `_reverify_one`: a vacuous PASS → `ReverifyOutcome(..., "SKIPPED", "vacuous statement (True) is not re-recorded as FORMALIZED")`.

- [ ] **Step 1: Write the failing tests** (stub verifier returning statement `"True"`; assert `VacuousStatementError` from `ingest_lean_artifact`, no artifact row; async path returns FAIL gate `vacuous`; loop test: round 1 vacuous → round 2 prompt carries the feedback → PASS; feedback test; reverify test with a legacy `True` artifact → SKIPPED, no new evidence; `FormalizeTask(name=, goal=, context=)` without `problem` raises `TypeError`).
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement** as specified; keep `LeanVerifier.version = "3.3"` (the gate's verify semantics are unchanged; the hash moves as it does for any edit and the ledgers are re-certified in Task 6).
- [ ] **Step 4: Run** — `uv run pytest -q -m "not slow_lean"` (whole suite minus real Lean) → PASS; `uv run ruff check src tests` clean.
- [ ] **Step 5: Commit** — `git commit -am "M23a: Lean ingest requires an explicit problem and refuses a True statement"`

---

### Task 6: Apply the hygiene to the repository's ledger

**Files:**
- Modify (data): `claims/*.yaml`, `claims.lock.json`, `claims/verifiers.json`, `receipts/`, `CLAIMS.md`
- Create: `docs/science/2026-09-07-ledger-hygiene.md`
- Local only: `runs/p3-campaign`, `runs/p5-formalize`, `runs/p5-live`, backups under `runs/_backup-2026-09-07/`

- [ ] **Step 1: Back up the three ledgers** — `for r in p3-campaign p5-formalize p5-live; do mkdir -p runs/_backup-2026-09-07/$r && sqlite3 runs/$r/ledger.db ".backup runs/_backup-2026-09-07/$r/ledger.db"; done`
- [ ] **Step 2: Confirm the catch** — `uv run empiricist claims check --repo .` → `verifier_drift` for `sos_certificate`; `P3.k0_standard_assignment_p_avg` STALE. Record the output for the note.
- [ ] **Step 3: Relabel the fourteen artifacts in `runs/p3-campaign`** (ids from `find_artifacts(kind="lean", problem="P5")`; every one is a P3 module — Bell labels, `Matrix.unitaryGroup (Fin 4)`, `Identifies`, Pauli eigenvectors) with note `"P3 k=0 formalization lemma ingested under FormalizeTask's P5 default (M23a hygiene)"`.
- [ ] **Step 4: Re-certify and re-verify each ledger under the edited code** — `uv run empiricist reverify --run-dir runs/p3-campaign` (16 Lean + 8 certificates), `... runs/p5-formalize` (20), `... runs/p5-live` (2). Expect PASS everywhere except the `True` probe (SKIPPED). Record wall times.
- [ ] **Step 5: Materialise** — `for r in p3-campaign p5-formalize p5-live; do uv run empiricist claims import-ledger --run-dir runs/$r --repo .; done`. Expect 14 new `P3.*` claims superseding `P5.*` ones, the registry stamps for `lean`/`sos_certificate`/`p3_exact_witness` at the live identities, and `claims check` green except the probe.
- [ ] **Step 6: Supersede proven conjectures** (hand edits; `updated: 2026-09-07`; a `notes` line each):
  - `P5.Empiricist.pathGraph_min_fusions` supersedes the ten `P5.Conjecture_path_*` claims.
  - `P5.Empiricist.star_min_fusions` supersedes `P5.Conjecture_star_F_N_F_n_n_-_3_for_all_n_3`.
  - `P5.Empiricist.complete_min_fusions` supersedes `P5.Conjecture_complete_F_N_F_N_N_-_3_for_all_N_3_the_complete_g` and `P5.Empiricist.complete_min_fusions_2`.
  - `P5.Empiricist.tree_min_fusions` supersedes `P5.Empiricist.tree_min_fusions_2`.
  - `P5.Empiricist.dh_characterization` supersedes `P5.Conjecture_Fable-generated_F_G_N-3_distance-hereditary_rank` with the note: "the formal statement uses `PendantTwinBuildable`, the Bandelt–Mulder generative characterization of distance-hereditary graphs (rank-width 1 ⟺ distance-hereditary is Oum 2005); `ProducibleByExt (N−3)` is `F(G) = N−3` given `fusion_cost_lower_bound`".
  - The cycle conjecture stays CONJECTURED (open for n ≥ 5).
- [ ] **Step 7: The vacuous probe** — `uv run empiricist claims review --repo . --id P3.Empiricist.pauli_eigvec_axis_aligned --samples 1` (model reviewer, ~$2.50); then `uv run empiricist claims demote --repo . --id P3.Empiricist.pauli_eigvec_axis_aligned --level HEURISTIC --receipt <id> --reason "statement is the placeholder True (a diagnostic probe module); the intended lemma is P3.pauli_eigvec_axis_aligned"`; add `supersedes: [P3.Empiricist.pauli_eigvec_axis_aligned]` to `P3.pauli_eigvec_axis_aligned` with a note.
- [ ] **Step 8: Render and check** — `uv run empiricist claims report --repo . --force`; `uv run empiricist claims check --repo . --min-claims 1` → green; `uv run empiricist audit --run-dir runs/p3-campaign` → OK.
- [ ] **Step 9: Write the note** `docs/science/2026-09-07-ledger-hygiene.md`: what was found (14 mislabelled lemmas, 13 proven-conjecture duplicates, a `True` FORMALIZED probe, the uninduced SOS verifier drift caught by the new check), what was done, wall times, the receipt id, and the kill-gate status (event 2: a genuine verifier change under a promoted claim, caught).
- [ ] **Step 10: Commit** — `git add claims claims.lock.json CLAIMS.md receipts docs && git commit -m "M23a: ledger hygiene applied — P3 lemmas relabelled, proven conjectures superseded, SOS drift re-earned"`

---

### Task 7: PR

- [ ] `uv run pytest -q -m "not slow_lean"`, `uv run ruff check src tests`, `uv run empiricist claims check --repo . --min-claims 1` all green.
- [ ] Update the charter status table (§7) with the second kill-gate event and the memory file.
- [ ] `env -u GH_TOKEN gh pr create` from `feat/m23a-ledger-hygiene`; squash-merge after CI.

## Follow-ups (not in this plan)

- M23b: the P5 campaign under v1 — materialise `conjecture.submit` and `ingest_dataset` results through the batch hook, an end-of-campaign catch-up, a `--claims-repo` flag, and a "settled families" nudge for the conjecturer.
- A `claims reverify` path for Lean evidence inside a research repository without a v0 ledger.

## Outcome (2026-09-07)

All seven tasks done on `feat/m23a-ledger-hygiene`. Fast suite 1117 passed; `claims check --repo . --min-claims 1` green with 77 claims (47 CURRENT, 30 SUPERSEDED); `audit` clean on the three ledgers (p3-campaign's seven pre-existing `run_billing_unknown` notes aside). Reverify walls 241 s / 182 s / 73 s. One reviewer sample ($2.24) blocked the `True` probe on six findings. The uninduced `sos_certificate` drift under `P3.k0_standard_assignment_p_avg` is the charter's second kill-gate event. Narrative: `docs/science/2026-09-07-ledger-hygiene.md`.

"""Importers from a v0 ledger and from a legacy CLAIMS.md (M22a Task 5)."""
from __future__ import annotations

from blake3 import blake3

from empiricist.certificates.goldens import certify_sos, load_k0_golden
from empiricist.certificates.ingest import ingest_p3_certificate
from empiricist.certificates.verifier import SOSCertificateVerifier, certificate_to_json
from empiricist.claims.check import check, refresh_repo
from empiricist.claims.importer import import_ledger, import_table, parse_claims_table
from empiricist.claims.model import load_all
from empiricist.cli import main
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Certification, Verdict
from empiricist.store import Store
from empiricist.verifiers.base import VerifierResult
from empiricist.verifiers.lean import ingest_lean_artifact
from empiricist.verifiers.lean_goldens import lean_suite_hash


class _StubLean:
    name, version, binary_hash = "lean", "9.9", "ab" * 32

    def verify(self, module_source, *, decl, timeout_s=600.0):
        statement = f"stmt:{decl}"
        return VerifierResult(verdict=Verdict.PASS, details={
            "decl": decl, "axioms": ["propext"], "statement": statement,
            "statement_hash": blake3(statement.encode()).hexdigest(),
        })


def _v0_ledger(tmp_path):
    run_dir = tmp_path / "run"
    lg = Ledger(run_dir / "ledger.db")
    st = Store(run_dir / "store")
    stub = _StubLean()
    lg.add_certification(Certification(verifier="lean", verifier_version="9.9",
                                       binary_hash="ab" * 32, golden_suite_hash=lean_suite_hash(),
                                       verdict=Verdict.PASS))
    ingest_lean_artifact(lg, st, "theorem foo : 1 = 1 := rfl", "Empiricist.foo",
                         verifier=stub, problem="P3", problem_version="p3-v1")
    certify_sos(lg, SOSCertificateVerifier())
    ingest_p3_certificate(lg, st, certificate_json=certificate_to_json(load_k0_golden()),
                          target="k0_standard_assignment_p_avg", title="k0 cert")
    lg.close()
    return run_dir


def test_import_ledger_writes_claims_and_check_passes(tmp_path):
    run_dir = _v0_ledger(tmp_path)
    repo = tmp_path / "repo"
    rep = import_ledger(run_dir, repo)
    assert sorted(rep.written) == ["P3.Empiricist.foo", "P3.k0_standard_assignment_p_avg"]
    claims = load_all(repo)
    lean = claims["P3.Empiricist.foo"]
    assert lean.level == "FORMALIZED" and lean.kind == "statement"
    assert lean.evidence[0].verifier == "lean" and lean.evidence[0].verdict == "PASS"
    assert lean.evidence[0].golden_suite_hash == lean_suite_hash()
    assert (repo / lean.evidence[0].path).read_text() == "theorem foo : 1 = 1 := rfl"
    cert = claims["P3.k0_standard_assignment_p_avg"]
    assert cert.level == "CERTIFIED" and cert.evidence[0].path.endswith(".json")
    assert "artifact " in lean.notes and lean.source.kind == "ledger"
    assert check(repo).ok
    # idempotent: same ids, same files, still green; hand-added links and notes survive,
    # and a level recorded in the repo is never lowered by a re-import
    from empiricist.claims.model import save_claim

    save_claim(repo, cert.model_copy(update={"depends_on": ["P3.Empiricist.foo"],
                                             "notes": "REVIEWED. " + cert.notes,
                                             "level": "FORMALIZED"}))
    rep2 = import_ledger(run_dir, repo)
    assert sorted(rep2.written) == sorted(rep.written) and len(load_all(repo)) == 2
    cert2 = load_all(repo)["P3.k0_standard_assignment_p_avg"]
    assert cert2.depends_on == ["P3.Empiricist.foo"] and cert2.notes.startswith("REVIEWED.")
    assert cert2.level == "FORMALIZED" and cert2.evidence == cert.evidence
    assert refresh_repo(repo).ok and (repo / "CLAIMS.md").is_file()


def test_import_table_from_legacy_claims_md(tmp_path):
    repo = tmp_path / "dg"
    (repo / "problems" / "P4").mkdir(parents=True)
    (repo / "problems" / "P4" / "cert.json").write_text("{}")
    table = (
        "# Claims ledger\n\nRules: ...\n\n"
        "| id | problem | statement | level | evidence | updated |\n"
        "|---|---|---|---|---|---|\n"
        "| P4-6 | P4 | Theorem B (mode count) | CERTIFIED (rigorous winding number) "
        "| problems/P4/cert.json; problems/P4/notes/proof.md | 2026-08-29 |\n"
        "| P4-7 | P4 | Structure of E at large kappa | CONJECTURED | problems/P4/notes/x.md "
        "| 2026-08-30 |\n"
        "| P9b-1.K | P9(b) | Ladder row S = {alpha_K}: (N) | CERTIFIED (= P9b-0) | as P9b-0 "
        "| 2026-08-31 |\n"
        "| bad | P4 | no level | MAYBE | x | 2026-01-01 |\n"
    )
    (repo / "CLAIMS.md").write_text(table)
    rows = parse_claims_table(table)
    assert [r["id"] for r in rows] == ["P4-6", "P4-7", "P9b-1.K", "bad"]
    rep = import_table(repo / "CLAIMS.md", repo)
    assert rep.written == ["P4-6", "P4-7", "P9b-1.K"]
    assert rep.skipped == ["bad: unrecognised level 'MAYBE'"]
    assert rep.missing_paths["P4-6"] == ["problems/P4/notes/proof.md"]
    assert rep.warnings and "report --force" in rep.warnings[0]
    claims = load_all(repo)
    # levels are earned: every row enters at HEURISTIC with the table's level kept aside
    assert claims["P4-6"].level == "HEURISTIC" and claims["P4-6"].legacy_level == "CERTIFIED"
    assert "rigorous winding" in claims["P4-6"].notes
    assert claims["P4-6"].evidence[0].path == "problems/P4/cert.json"
    assert claims["P4-6"].evidence[0].verifier == "table-import"
    assert claims["P4-6"].evidence[0].verdict == "IMPORTED"
    assert claims["P4-6"].source.kind == "table" and claims["P4-6"].source.ref == "P4-6"
    assert claims["P4-7"].legacy_level == "CONJECTURED"
    assert claims["P9b-1.K"].evidence == [] and "as P9b-0" in claims["P9b-1.K"].notes
    report = refresh_repo(repo)   # the legacy table is left alone without --force
    assert [i.code for i in report.blocking] == ["claims_md_legacy"]
    assert (repo / "CLAIMS.md").read_text() == table
    report = refresh_repo(repo, force=True)
    assert report.ok and {i.code for i in report.issues} == {"imported_unverified"}
    md = (repo / "CLAIMS.md").read_text()
    assert ("| P4-6 | P4 | Theorem B (mode count) | HEURISTIC (legacy CERTIFIED, not re-earned) |"
            in md)
    # re-importing the same (now rendered) file is a no-op; re-importing the legacy text
    # keeps hand-added links and never duplicates claims
    assert import_table(repo / "CLAIMS.md", repo).written == []
    (repo / "legacy.md").write_text(table)
    from empiricist.claims.model import save_claim

    save_claim(repo, claims["P4-7"].model_copy(update={"depends_on": ["P4-6"], "receipts": []}))
    rep2 = import_table(repo / "legacy.md", repo)
    assert rep2.written == ["P4-6", "P4-7", "P9b-1.K"] and len(load_all(repo)) == 3
    assert load_all(repo)["P4-7"].depends_on == ["P4-6"]


def test_parse_claims_table_recovers_pipes_and_reports_drops():
    table = (
        "| id | problem | statement | level | evidence | updated |\n|---|---|---|---|---|---|\n"
        "| A | P | convergent on |x| < 0.1 and |κ| > 2 | CERTIFIED | e.json | 2026-01-01 |\n"
        "| B | P | too few cells | CERTIFIED |\n"
    )
    dropped: list[str] = []
    rows = parse_claims_table(table, dropped=dropped)
    assert [r["id"] for r in rows] == ["A"]
    assert rows[0]["statement"] == "convergent on |x| < 0.1 and |κ| > 2"
    assert rows[0]["level"] == "CERTIFIED" and rows[0]["updated"] == "2026-01-01"
    assert dropped == ["line 4: 4 cells, expected 6"]


def test_split_level_forms():
    from empiricist.claims.importer import _split_level

    assert _split_level("**CERTIFIED** (why)") == ("CERTIFIED", "why")
    assert _split_level("`FORMALIZED`") == ("FORMALIZED", "")
    assert _split_level("CONJEC...") == ("CONJECTURED", "")
    assert _split_level("VERIFIED_N (n=2000)") == ("VERIFIED_N", "n=2000")
    assert _split_level("CERTIFIED(rigorous)") == ("CERTIFIED", "rigorous")
    assert _split_level("MAYBE") == ("", "MAYBE")


def test_import_table_skips_bad_rows_instead_of_crashing(tmp_path):
    repo = tmp_path
    (repo / "e.json").write_text("{}")
    table = (
        "| id | problem | statement | level | evidence | updated |\n|---|---|---|---|---|---|\n"
        "| G1 | P | good | VERIFIED_N (n=2000) | e.json | 2026-01-01 |\n"
        "| bad/id | P | bad id | CERTIFIED | e.json | 2026-01-01 |\n"
        "| G2 | P | odd date | CERTIFIED | e.json | Aug 2026 |\n"
    )
    (repo / "legacy.md").write_text(table)
    rep = import_table(repo / "legacy.md", repo)
    assert rep.written == ["G1", "bad_id", "G2"] and rep.skipped == []
    claims = load_all(repo)
    assert claims["G1"].legacy_level == "VERIFIED_N" and "n=2000" in claims["G1"].notes
    assert claims["G2"].updated == "1970-01-01" and "updated: Aug 2026" in claims["G2"].notes
    assert (repo / "claims.lock.json").is_file() and check(repo).ok


def test_cli_claims_commands(tmp_path, capsys):
    run_dir = _v0_ledger(tmp_path)
    repo = tmp_path / "repo"
    assert main(["claims", "import-ledger", "--run-dir", str(run_dir), "--repo", str(repo)]) == 0
    assert "wrote 2" in capsys.readouterr().out
    assert main(["claims", "check", "--repo", str(repo), "--min-claims", "2"]) == 0
    assert main(["claims", "check", "--repo", str(repo), "--min-claims", "3"]) == 1
    assert main(["claims", "report", "--repo", str(repo)]) == 0
    capsys.readouterr()
    ev = next((repo / "claims" / "evidence").glob("*.lean"))
    ev.write_text("theorem foo : 1 = 2 := sorry")
    assert main(["claims", "check", "--repo", str(repo)]) == 1
    out = capsys.readouterr().out
    assert "lock_mismatch: P3.Empiricist.foo changed:" in out
    assert "blocking issue(s)" in out and " 0 blocking" not in out


def test_import_ledger_keeps_pre_hardening_artifacts(tmp_path):
    """A v0 artifact without a canonical claim row (pre-hardening) is imported with
    its title as the statement and a note saying so, not dropped."""
    from empiricist.ledger.models import Artifact, EvidenceRow, Status

    run_dir = tmp_path / "run"
    lg = Ledger(run_dir / "ledger.db")
    st = Store(run_dir / "store")
    digest = st.put(b'{"conjecture": "F(G)=N-3 iff distance-hereditary"}')
    lg.add_artifact(Artifact(id=digest, kind="statement", problem="P5", title="DH characterization",
                             content_path=digest, status=Status.CONJECTURED))
    lg.record_evidence(EvidenceRow(artifact_id=digest, verifier="attack", verifier_version="1",
                                   binary_hash="ab" * 32, verdict=Verdict.PASS))
    lg.close()
    rep = import_ledger(run_dir, tmp_path / "repo")
    assert rep.written == ["P5.DH_characterization"] and rep.skipped == []
    c = load_all(tmp_path / "repo")["P5.DH_characterization"]
    assert c.statement == "DH characterization" and "no canonical claim row" in c.notes
    assert check(tmp_path / "repo").ok


def test_resolve_evidence_cell_handles_the_legacy_forms(tmp_path):
    from empiricist.claims.importer import resolve_evidence_cell

    repo = tmp_path
    for rel in ("problems/P9/results/certificates/feasible_L1_D4.json",
                "problems/P9/results/certificates/feasible_L2_D4.json",
                "problems/P9/b/tests/test_s2_rows.py", "problems/P9/b/certificates/P9b-1.K.json",
                "problems/P9/notes/proof.md"):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text("x")
    known = {"P9b-0", "P9b-1.K", "P9b-1.rows"}
    cell = ("results/certificates/feasible_L*_D*.json; b/tests/test_s2_rows.py; "
            "problems/P9/notes/proof.md §6.2; as P9b-0; CLAIMS P9b-0, P9b-1.K, P9b-1.rows; "
            "b/certificates/P9b-1.{K,rows}.json; results/summary.md; /etc/passwd; ../x")
    present, depends, missing = resolve_evidence_cell(repo, cell, "P9(b), ladder", known_ids=known)
    assert present == [
        "problems/P9/results/certificates/feasible_L1_D4.json",
        "problems/P9/results/certificates/feasible_L2_D4.json",
        "problems/P9/b/tests/test_s2_rows.py",
        "problems/P9/notes/proof.md",
        "problems/P9/b/certificates/P9b-1.K.json",
    ]
    assert depends == ["P9b-0", "P9b-1.K", "P9b-1.rows"]
    assert missing == ["results/summary.md", "/etc/passwd", "../x"]


def test_unique_ids_are_case_insensitive_and_directories_expand(tmp_path):
    from empiricist.claims.importer import _unique_id, resolve_evidence_cell

    taken = {"P5.path_N"}
    assert _unique_id("P5.path_n", taken) == "P5.path_n_2"
    repo = tmp_path
    for rel in ("problems/P8/tests/test_a.py", "problems/P8/tests/sub/test_b.py",
                "problems/P8/tests/__pycache__/x.pyc", "problems/P4/tests/t1.py",
                "problems/P4/tests/t2.py"):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text("x")
    present, deps, missing = resolve_evidence_cell(repo, "problems/P8/tests/", "P8(b)")
    assert present == ["problems/P8/tests/sub/test_b.py", "problems/P8/tests/test_a.py"]
    present, deps, missing = resolve_evidence_cell(repo, "tests/t1.py, tests/t2.py", "P4")
    assert present == ["problems/P4/tests/t1.py", "problems/P4/tests/t2.py"] and not missing


def test_import_table_inherits_evidence_from_a_referenced_claim(tmp_path):
    repo = tmp_path
    (repo / "problems" / "P9").mkdir(parents=True)
    (repo / "problems" / "P9" / "c.json").write_text("{}")
    table = (
        "| id | problem | statement | level | evidence | updated |\n|---|---|---|---|---|---|\n"
        "| P9b-0 | P9(b) | base | CERTIFIED | problems/P9/c.json | 2026-08-31 |\n"
        "| P9b-1.K | P9(b) | row K | CERTIFIED (= P9b-0) | as P9b-0 | 2026-08-31 |\n"
    )
    (repo / "CLAIMS.md").write_text(table)
    import_table(repo / "CLAIMS.md", repo)
    claims = load_all(repo)
    assert claims["P9b-1.K"].depends_on == ["P9b-0"]
    assert [e.path for e in claims["P9b-1.K"].evidence] == ["problems/P9/c.json"]
    assert "inherited from P9b-0" in claims["P9b-1.K"].evidence[0].note
    assert claims["P9b-1.K"].evidence[0].verdict == "IMPORTED"
    rep = refresh_repo(repo, force=True)
    assert rep.ok and rep.standings == {"P9b-0": "CURRENT", "P9b-1.K": "CURRENT"}
    assert all(c.level == "HEURISTIC" and c.legacy_level == "CERTIFIED" for c in claims.values())

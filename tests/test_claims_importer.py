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
    assert "artifact " in lean.notes
    assert check(repo).ok
    # idempotent: same ids, same files, still green
    rep2 = import_ledger(run_dir, repo)
    assert sorted(rep2.written) == sorted(rep.written) and len(load_all(repo)) == 2
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
    claims = load_all(repo)
    assert claims["P4-6"].level == "CERTIFIED" and "rigorous winding" in claims["P4-6"].notes
    assert claims["P4-6"].evidence[0].path == "problems/P4/cert.json"
    assert claims["P4-6"].evidence[0].verifier == "table-import"
    assert claims["P9b-1.K"].evidence == [] and "as P9b-0" in claims["P9b-1.K"].notes
    report = refresh_repo(repo)
    codes = {i.code for i in report.issues}
    # P4-7 (its only evidence path is missing) and P9b-1.K ("as P9b-0") have no evidence
    # entry at all, so their elevated levels are blocking until re-verified (M22b);
    # P4-6 is an imported-unverified note only.
    assert "elevated_without_pass" in codes and "imported_unverified" in codes
    assert [i.claim_id for i in report.blocking] == ["P4-7", "P9b-1.K"]
    assert "| P4-6 | P4 |" in (repo / "CLAIMS.md").read_text()


def test_cli_claims_commands(tmp_path, capsys):
    run_dir = _v0_ledger(tmp_path)
    repo = tmp_path / "repo"
    assert main(["claims", "import-ledger", "--run-dir", str(run_dir), "--repo", str(repo)]) == 0
    assert "wrote 2" in capsys.readouterr().out
    assert main(["claims", "check", "--repo", str(repo)]) == 0
    assert main(["claims", "report", "--repo", str(repo)]) == 0
    capsys.readouterr()
    ev = next((repo / "claims" / "evidence").glob("*.lean"))
    ev.write_text("theorem foo : 1 = 2 := sorry")
    assert main(["claims", "check", "--repo", str(repo)]) == 1
    out = capsys.readouterr().out
    assert "lock_mismatch: P3.Empiricist.foo changed:" in out
    assert "blocking issue(s)" in out and " 0 blocking" not in out

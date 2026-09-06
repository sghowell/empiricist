"""The batch hook: ingests materialise claim files when a repo is configured (M22b Task 4)."""
from __future__ import annotations

from blake3 import blake3

from empiricist.certificates.goldens import certify_sos, load_k0_golden
from empiricist.certificates.ingest import ingest_p3_certificate
from empiricist.certificates.verifier import certificate_to_json
from empiricist.claims.check import check
from empiricist.claims.materialize import ENV_CLAIMS_REPO, materialize_after_ingest
from empiricist.claims.model import load_all, save_claim
from empiricist.claims.registry import read_registry, stamp
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


def _ledger(tmp_path):
    lg = Ledger(tmp_path / "run" / "ledger.db")
    st = Store(tmp_path / "run" / "store")
    lg.add_certification(Certification(verifier="lean", verifier_version="9.9",
                                       binary_hash="ab" * 32, golden_suite_hash=lean_suite_hash(),
                                       verdict=Verdict.PASS))
    return lg, st


def test_lean_ingest_materializes_when_configured(tmp_path, monkeypatch):
    lg, st = _ledger(tmp_path)
    repo = tmp_path / "repo"
    monkeypatch.delenv(ENV_CLAIMS_REPO, raising=False)
    ingest_lean_artifact(lg, st, "theorem a : 1 = 1 := rfl", "Empiricist.a", verifier=_StubLean(),
                         problem="P3", problem_version="p3-v1")
    assert not (repo / "claims").exists()          # unconfigured: nothing written anywhere
    monkeypatch.setenv(ENV_CLAIMS_REPO, str(repo))
    art = ingest_lean_artifact(lg, st, "theorem b : 2 = 2 := rfl", "Empiricist.b",
                               verifier=_StubLean(), problem="P3", problem_version="p3-v1")
    claims = load_all(repo)
    assert list(claims) == ["P3.Empiricist.b"]
    c = claims["P3.Empiricist.b"]
    assert c.level == "FORMALIZED" and c.source.ref == art.id
    assert (repo / c.evidence[0].path).read_text() == "theorem b : 2 = 2 := rfl"
    # the ledger's PASS certification stamps the repo registry, so `check` can see a
    # newer lean later
    s = read_registry(repo).stamps["lean"]
    assert s.version == "9.9" and s.golden_suite_hash == lean_suite_hash()
    rep = check(repo)
    assert rep.ok and rep.standings == {"P3.Empiricist.b": "CURRENT"}
    # explicit argument wins over the environment; idempotent re-ingest keeps links
    other = tmp_path / "other"
    save_claim(repo, c.model_copy(update={"notes": "kept", "depends_on": []}))
    ingest_lean_artifact(lg, st, "theorem b : 2 = 2 := rfl", "Empiricist.b", verifier=_StubLean(),
                         problem="P3", problem_version="p3-v1", claims_repo=other)
    assert list(load_all(other)) == ["P3.Empiricist.b"]
    assert load_all(repo)["P3.Empiricist.b"].notes == "kept"
    lg.close()


def test_certificate_ingest_materializes_and_registry_never_downgrades(tmp_path):
    lg, st = _ledger(tmp_path)
    repo = tmp_path / "repo"
    from empiricist.certificates.verifier import SOSCertificateVerifier

    certify_sos(lg, SOSCertificateVerifier())
    stamp(repo, name="sos_certificate", version="999", binary_hash="ff" * 32,
          golden_suite_hash="00" * 32)
    ingest_p3_certificate(lg, st, certificate_json=certificate_to_json(load_k0_golden()),
                          target="k0_standard_assignment_p_avg", title="k0", claims_repo=repo)
    claims = load_all(repo)
    assert [c.level for c in claims.values()] == ["CERTIFIED"]
    assert read_registry(repo).stamps["sos_certificate"].version == "999"  # kept
    # the hook never raises into the ingest: an unwritable repo is logged, not fatal
    bad = tmp_path / "file-not-dir"
    bad.write_text("x")
    assert materialize_after_ingest(lg, st, next(iter(claims.values())).source.ref,
                                    claims_repo=bad) is None
    lg.close()


def test_registry_follows_the_latest_certification_of_a_version(tmp_path):
    """Two PASS certifications for lean 9.9 (an old binary, then a re-certified new one):
    the registry stamps the newer, so evidence from the old binary is STALE and evidence
    from the new one is CURRENT."""
    lg, st = _ledger(tmp_path)  # certifies lean 9.9 under "ab"*32
    repo = tmp_path / "repo"
    ingest_lean_artifact(lg, st, "theorem a : 1 = 1 := rfl", "Empiricist.a", verifier=_StubLean(),
                         problem="P3", problem_version="p3-v1", claims_repo=repo)

    class _NewLean(_StubLean):
        binary_hash = "cd" * 32

    lg.add_certification(Certification(verifier="lean", verifier_version="9.9",
                                       binary_hash="cd" * 32, golden_suite_hash=lean_suite_hash(),
                                       verdict=Verdict.PASS))
    ingest_lean_artifact(lg, st, "theorem b : 2 = 2 := rfl", "Empiricist.b", verifier=_NewLean(),
                         problem="P3", problem_version="p3-v1", claims_repo=repo)
    assert read_registry(repo).stamps["lean"].binary_hash == "cd" * 32
    rep = check(repo)
    assert rep.standings == {"P3.Empiricist.a": "STALE", "P3.Empiricist.b": "CURRENT"}
    lg.close()

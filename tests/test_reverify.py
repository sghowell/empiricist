"""Re-verification of legacy FORMALIZED Lean artifacts under the current gate."""
from __future__ import annotations

import pytest
from blake3 import blake3

from empiricist.ledger.audit import audit_ledger
from empiricist.ledger.db import Ledger, PromotionIntegrityError
from empiricist.ledger.models import (
    Artifact,
    Certification,
    EvidenceRow,
    Status,
    Verdict,
)
from empiricist.store import Store
from empiricist.verifiers.base import VerifierResult
from empiricist.verifiers.lean_goldens import lean_suite_hash
from empiricist.verifiers.reverify import reverify_lean_artifacts


class _StubLean:
    """LeanVerifier-shaped stub: PASS unless the source contains `sorry`."""

    name = "lean"
    version = "9.9"
    binary_hash = "ab" * 32

    def __init__(self) -> None:
        self.calls: list[str] = []

    def verify(self, module_source: str, *, decl: str, timeout_s: float = 600.0):
        self.calls.append(decl)
        if "sorry" in module_source:
            return VerifierResult(verdict=Verdict.FAIL, details={"gate": "compile"})
        statement = f"stmt:{decl}"
        return VerifierResult(
            verdict=Verdict.PASS,
            details={
                "decl": decl,
                "axioms": ["propext"],
                "statement": statement,
                "statement_hash": blake3(statement.encode()).hexdigest(),
            },
        )


@pytest.fixture()
def env(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    st = Store(tmp_path / "store")
    yield lg, st
    lg.close()


def _stamp(lg: Ledger, v: _StubLean) -> None:
    lg.add_certification(
        Certification(
            verifier=v.name,
            verifier_version=v.version,
            binary_hash=v.binary_hash,
            golden_suite_hash=lean_suite_hash(),
            verdict=Verdict.PASS,
        )
    )


def _legacy_formalized(
    lg: Ledger,
    st: Store,
    source: str,
    decl: str,
    *,
    problem_version: str = "legacy",
) -> Artifact:
    """A pre-hardening FORMALIZED row: PASS evidence without a golden_suite_hash."""
    digest = st.put(source.encode())
    art = Artifact(
        id=digest,
        kind="lean",
        problem="P5",
        problem_version=problem_version,
        title=decl,
        content_path=digest,
        status=Status.FORMALIZED,
    )
    lg.add_artifact(art)
    lg.record_evidence(
        EvidenceRow(
            artifact_id=art.id,
            verifier="lean",
            verifier_version="3.2",
            binary_hash="cd" * 32,
            verdict=Verdict.PASS,
            details={"decl": decl},
        )
    )
    return art


def _flagged(lg, st, artifact_id) -> bool:
    return any(
        i.code == "elevated_missing_certified_evidence" and i.artifact_id == artifact_id
        for i in audit_ledger(lg, st).issues
    )


def test_reverify_pass_clears_audit_flag_and_keeps_status(env):
    lg, st = env
    v = _StubLean()
    _stamp(lg, v)
    art = _legacy_formalized(lg, st, "theorem foo : 1 = 1 := rfl", "Empiricist.foo")
    assert _flagged(lg, st, art.id)

    rep = reverify_lean_artifacts(lg, st, verifier=v, certify=False)

    assert rep.ok and [o.verdict for o in rep.outcomes] == ["PASS"]
    assert rep.certified_now is False
    assert v.calls == ["Empiricist.foo"]
    assert not _flagged(lg, st, art.id)
    assert lg.get_artifact(art.id).status is Status.FORMALIZED
    rows = lg.evidence_for(art.id)
    assert len(rows) == 2
    new = [r for r in rows if r.golden_suite_hash == lean_suite_hash()]
    assert len(new) == 1 and new[0].claim_id is not None
    assert lg.claims_for(art.id)[0].statement == "stmt:Empiricist.foo"


def test_reverify_fail_records_evidence_without_demotion(env):
    lg, st = env
    v = _StubLean()
    _stamp(lg, v)
    art = _legacy_formalized(lg, st, "theorem bad : 1 = 2 := by sorry", "Empiricist.bad")

    rep = reverify_lean_artifacts(lg, st, verifier=v, certify=False)

    assert not rep.ok and rep.outcomes[0].verdict == "FAIL"
    assert rep.outcomes[0].detail == "compile"
    assert lg.get_artifact(art.id).status is Status.FORMALIZED  # never demoted
    assert _flagged(lg, st, art.id)  # still honest
    fails = [r for r in lg.evidence_for(art.id) if r.verdict is Verdict.FAIL]
    assert len(fails) == 1
    assert fails[0].details["reverify"] is True
    assert fails[0].golden_suite_hash == lean_suite_hash()
    assert lg.claims_for(art.id) == []


def test_reverify_dry_run_writes_nothing(env):
    lg, st = env
    v = _StubLean()
    _stamp(lg, v)
    art = _legacy_formalized(lg, st, "theorem foo : 1 = 1 := rfl", "Empiricist.foo")

    rep = reverify_lean_artifacts(lg, st, verifier=v, certify=False, dry_run=True)

    assert rep.dry_run and not rep.ok
    assert [o.verdict for o in rep.outcomes] == ["SKIPPED"]
    assert v.calls == []
    assert len(lg.evidence_for(art.id)) == 1


def test_reverify_refuses_without_current_certification(env):
    lg, st = env
    v = _StubLean()
    _legacy_formalized(lg, st, "theorem foo : 1 = 1 := rfl", "Empiricist.foo")
    with pytest.raises(PromotionIntegrityError):
        reverify_lean_artifacts(lg, st, verifier=v, certify=False)
    assert v.calls == []


def test_reverify_stale_stamp_is_refused_without_certify(env):
    lg, st = env
    v = _StubLean()
    lg.add_certification(
        Certification(
            verifier=v.name,
            verifier_version=v.version,
            binary_hash=v.binary_hash,
            golden_suite_hash="0" * 64,  # a stamp against some OTHER suite
            verdict=Verdict.PASS,
        )
    )
    _legacy_formalized(lg, st, "theorem foo : 1 = 1 := rfl", "Empiricist.foo")
    with pytest.raises(PromotionIntegrityError):
        reverify_lean_artifacts(lg, st, verifier=v, certify=False)


def test_reverify_filters_by_artifact_id_and_skips_non_lean(env):
    lg, st = env
    v = _StubLean()
    _stamp(lg, v)
    a = _legacy_formalized(lg, st, "theorem a : 1 = 1 := rfl", "Empiricist.a")
    _legacy_formalized(lg, st, "theorem b : 2 = 2 := rfl", "Empiricist.b")
    other = st.put(b"not lean")
    lg.add_artifact(
        Artifact(
            id=other,
            kind="report",
            problem="P5",
            title="r",
            content_path=other,
            status=Status.HEURISTIC,
        )
    )

    rep = reverify_lean_artifacts(lg, st, verifier=v, certify=False, artifact_ids=[a.id])

    assert [o.decl for o in rep.outcomes] == ["Empiricist.a"]
    assert v.calls == ["Empiricist.a"]


def test_reverify_is_idempotent(env):
    lg, st = env
    v = _StubLean()
    _stamp(lg, v)
    art = _legacy_formalized(lg, st, "theorem foo : 1 = 1 := rfl", "Empiricist.foo")
    reverify_lean_artifacts(lg, st, verifier=v, certify=False)
    reverify_lean_artifacts(lg, st, verifier=v, certify=False)
    # record_claimed_artifact dedups identical PASS rows: still exactly one new row.
    assert len(lg.evidence_for(art.id)) == 2


def test_reverify_leaves_the_legacy_row_and_versions_the_claim(env):
    """The pilot artifact row is immutable data and stays `legacy` (the M-hardening
    design, pinned by test_promotion_integrity); the NEW claim names the precise
    problem version the current gate actually checked."""
    from empiricist.verifiers.lean import DEFAULT_LEAN_PROBLEM_VERSION

    lg, st = env
    v = _StubLean()
    _stamp(lg, v)
    art = _legacy_formalized(lg, st, "theorem foo : 1 = 1 := rfl", "Empiricist.foo")
    assert reverify_lean_artifacts(lg, st, verifier=v, certify=False).ok
    assert lg.get_artifact(art.id).problem_version == "legacy"
    assert lg.claims_for(art.id)[0].problem_version == DEFAULT_LEAN_PROBLEM_VERSION
    assert DEFAULT_LEAN_PROBLEM_VERSION != "legacy"


def test_reverify_skips_an_artifact_whose_id_is_not_its_content_digest(env):
    lg, st = env
    v = _StubLean()
    _stamp(lg, v)
    digest = st.put(b"theorem foo : 1 = 1 := rfl")
    lg.add_artifact(Artifact(id="9" * 64, kind="lean", problem="P5", problem_version="legacy",
                             title="Empiricist.foo", content_path=digest,
                             status=Status.FORMALIZED))
    rep = reverify_lean_artifacts(lg, st, verifier=v, certify=False)
    assert [o.verdict for o in rep.outcomes] == ["SKIPPED"] and not rep.ok
    assert v.calls == []
    assert [a.id for a in lg.find_artifacts()] == ["9" * 64]  # no duplicate artifact


def test_reverify_isolates_a_bad_blob_and_keeps_going(env):
    lg, st = env
    v = _StubLean()
    _stamp(lg, v)
    _legacy_formalized(lg, st, "theorem a : 1 = 1 := rfl", "Empiricist.a")
    bad = st.put(b"\xff\xfe not utf-8")
    lg.add_artifact(Artifact(id=bad, kind="lean", problem="P5", problem_version="legacy",
                             title="Empiricist.bad", content_path=bad,
                             status=Status.FORMALIZED))
    lg.record_evidence(EvidenceRow(artifact_id=bad, verifier="lean", verifier_version="3.2",
                                   binary_hash="cd" * 32, verdict=Verdict.PASS))
    c = _legacy_formalized(lg, st, "theorem c : 3 = 3 := rfl", "Empiricist.c")
    rep = reverify_lean_artifacts(lg, st, verifier=v, certify=False)
    assert [o.verdict for o in rep.outcomes] == ["PASS", "ERROR", "PASS"]
    assert "UnicodeDecodeError" in rep.outcomes[1].detail
    assert v.calls == ["Empiricist.a", "Empiricist.c"]
    assert not _flagged(lg, st, c.id)


def test_reverify_reports_requested_ids_that_match_nothing(env):
    lg, st = env
    v = _StubLean()
    _stamp(lg, v)
    a = _legacy_formalized(lg, st, "theorem a : 1 = 1 := rfl", "Empiricist.a")
    rep = reverify_lean_artifacts(lg, st, verifier=v, certify=False,
                                  artifact_ids=[a.id, "f" * 64])
    assert [o.verdict for o in rep.outcomes] == ["PASS", "MISSING"] and not rep.ok
    assert rep.outcomes[1].artifact_id == "f" * 64
    dry = reverify_lean_artifacts(lg, st, verifier=v, certify=False, dry_run=True,
                                  artifact_ids=["f" * 64])
    assert [o.verdict for o in dry.outcomes] == ["MISSING"]


def test_reverify_keeps_an_explicit_problem_version(env):
    lg, st = env
    v = _StubLean()
    _stamp(lg, v)
    art = _legacy_formalized(
        lg, st, "theorem foo : 1 = 1 := rfl", "Empiricist.foo",
        problem_version="p5-custom-v7",
    )
    rep = reverify_lean_artifacts(lg, st, verifier=v, certify=False)
    assert rep.ok
    assert lg.get_artifact(art.id).problem_version == "p5-custom-v7"
    assert lg.claims_for(art.id)[0].problem_version == "p5-custom-v7"


def test_reverify_nothing_to_do_never_touches_certification(env):
    lg, st = env
    v = _StubLean()  # deliberately uncertified: with no targets it must not matter
    rep = reverify_lean_artifacts(lg, st, verifier=v, certify=True)
    assert rep.ok and rep.outcomes == () and rep.certified_now is False

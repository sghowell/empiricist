"""`check` and the CLAIMS.md render (M22a Task 4)."""
from __future__ import annotations

from empiricist.claims.check import check, refresh_repo
from empiricist.claims.lock import Lock, refresh_lock_entries, write_lock
from empiricist.claims.model import ClaimFile, EvidenceEntry, save_claim
from empiricist.claims.render import render_claims_md
from empiricist.claims.standing import Finding, Receipt, save_receipt


def _claim(cid, level="CERTIFIED", deps=(), verifier="v", verdict="PASS", **over):
    base = dict(
        id=cid, problem="P", formulation_version="v1", kind="statement",
        statement=f"statement of {cid} | with a pipe", level=level, updated="2026-09-06",
        depends_on=list(deps),
        evidence=[EvidenceEntry(path=f"ev/{cid}.json", verifier=verifier, version="1",
                                verdict=verdict, stamped="2026-09-06T00:00:00Z",
                                binary_hash=None if verifier == "table-import" else "ab" * 32)],
    )
    base.update(over)
    return ClaimFile(**base)


def _mini_repo(tmp_path, *claims):
    (tmp_path / "ev").mkdir(parents=True, exist_ok=True)
    lock = Lock()
    for c in claims:
        (tmp_path / "ev" / f"{c.id}.json").write_text(f'{{"c": "{c.id}"}}')
        save_claim(tmp_path, c)
        lock = refresh_lock_entries(tmp_path, c, lock)
    write_lock(tmp_path, lock)
    return tmp_path


def test_consistent_repo_passes_and_report_writes_md(tmp_path):
    repo = _mini_repo(tmp_path, _claim("a"), _claim("b", deps=["a"]))
    rep = check(repo)
    assert rep.ok and rep.claims == 2 and rep.standings == {"a": "CURRENT", "b": "CURRENT"}
    rep = refresh_repo(repo)
    assert rep.ok
    md = (repo / "CLAIMS.md").read_text()
    assert "do not hand-edit" in md
    assert "| a | P | statement of a \\| with a pipe | CERTIFIED | CURRENT |" in md
    assert md == render_claims_md(*_load(repo))


def _load(repo):
    from empiricist.claims.model import load_all

    claims = load_all(repo)
    return claims, {cid: c.standing for cid, c in claims.items()}


def test_each_blocking_code(tmp_path):
    repo = _mini_repo(tmp_path, _claim("a"), _claim("b", deps=["a"]))
    refresh_repo(repo)
    # lock mismatch -> STALE on a, propagates to b; the stored standings now differ
    (repo / "ev" / "a.json").write_text("{\"c\": \"tampered\"}")
    rep = check(repo)
    codes = {i.code for i in rep.issues}
    assert not rep.ok and "lock_mismatch" in codes and rep.standings == {"a": "STALE", "b": "STALE"}
    assert "stored_standing_differs" in codes and "claims_md_stale" in codes
    rep = refresh_repo(repo)  # report writes the derived standings and the table
    assert {i.code for i in rep.issues} == {"lock_mismatch"} and rep.standings["b"] == "STALE"
    # elevated without PASS
    repo2 = _mini_repo(tmp_path / "r2", _claim("x", verdict="FAIL"))
    assert {i.code for i in check(repo2).issues} >= {"elevated_without_pass"}
    # REFUTED without FAIL is blocking (a REFUTED claim poisons its dependents);
    # HEURISTIC needs nothing
    repo3 = _mini_repo(tmp_path / "r3", _claim("y", level="REFUTED", verdict="PASS"),
                       _claim("z", level="HEURISTIC", verdict="ERROR"))
    rep3 = check(repo3)
    assert not rep3.ok and {i.code for i in rep3.issues} == {"refuted_without_fail"}
    assert check(_mini_repo(tmp_path / "r3b", _claim("y", level="REFUTED", verdict="FAIL"))).ok
    # schema and graph errors short-circuit
    (tmp_path / "r3" / "claims" / "bad.yaml").write_text("id: bad\n")
    assert [i.code for i in check(repo3).issues] == ["schema_error"]
    (tmp_path / "r3" / "claims" / "bad.yaml").unlink()
    repo4 = _mini_repo(tmp_path / "r4", _claim("p", deps=["q"]), _claim("q", deps=["p"]))
    assert [i.code for i in check(repo4).issues] == ["graph_error"]


def test_current_on_noncurrent_and_imported_notes(tmp_path):
    repo = _mini_repo(tmp_path, _claim("old"), _claim("new", supersedes=["old"]),
                      _claim("user", deps=["old"], level="HEURISTIC", legacy_level="CERTIFIED",
                             verifier="table-import", verdict="IMPORTED"))
    refresh_repo(repo)
    rep = check(repo)
    assert rep.standings == {"old": "SUPERSEDED", "new": "CURRENT", "user": "STALE"}
    # `user` is STALE (it rests on a SUPERSEDED claim), not CURRENT, so no violation
    assert not any(i.code == "current_on_noncurrent" for i in rep.issues)
    assert any(i.code == "imported_unverified" and i.claim_id == "user" for i in rep.issues)
    assert rep.ok
    md = (repo / "CLAIMS.md").read_text()
    assert "| HEURISTIC (legacy CERTIFIED, not re-earned) | STALE | ev/user.json (imported) |" in md


def test_table_import_pass_never_counts(tmp_path):
    """A legacy importer cannot mint the PASS that lifts a level (charter F1)."""
    repo = _mini_repo(tmp_path, _claim("x", verifier="table-import", verdict="PASS"))
    rep = check(repo)
    assert [i.code for i in rep.blocking] == ["elevated_without_pass"]


def _blocking_receipt(rid, cid, created="2026-09-06", closes=None):
    return Receipt(id=rid, claim_id=cid, reviewer="human", statement_sha256="0" * 64,
                   findings=[Finding(dimension="evidence_support", severity="blocking",
                                     text="wrong")], verdict="BLOCK", created=created,
                   closes=closes)


def test_challenged_propagates_as_stale_two_hops(tmp_path):
    repo = _mini_repo(tmp_path, _claim("a"), _claim("b", deps=["a"]), _claim("c", deps=["b"]))
    save_receipt(repo, _blocking_receipt("r1", "a"))
    rep = refresh_repo(repo)
    assert rep.standings == {"a": "CHALLENGED", "b": "STALE", "c": "STALE"}
    assert rep.ok  # a challenge is a legitimate derived state, not a broken ledger
    assert "| b | P | statement of b \\| with a pipe | CERTIFIED | STALE |" in (
        repo / "CLAIMS.md").read_text()


def test_receipts_are_bound_to_the_statement_and_to_known_claims(tmp_path):
    from empiricist.claims.standing import statement_sha256

    ok = Receipt(id="r-ok", claim_id="a", reviewer="human",
                 statement_sha256=statement_sha256("statement of a | with a pipe"),
                 verdict="PASS", created="2026-09-06")
    repo = _mini_repo(tmp_path, _claim("a", receipts=["r-ok"]))
    save_receipt(repo, ok)
    assert check(repo).ok
    # statement edited after review -> blocking
    save_claim(repo, _claim("a", receipts=["r-ok"], statement="something else"))
    assert [i.code for i in check(repo).blocking] == ["receipt_stale"]
    # a receipt listed on the claim but written for another claim, or absent
    save_claim(repo, _claim("a", receipts=["r-ok", "r-none"]))
    save_receipt(repo, ok.model_copy(update={"claim_id": "zzz"}))
    codes = sorted(i.code for i in check(repo).blocking)
    assert codes == ["receipt_missing", "receipt_orphan", "receipt_stale"]


def test_min_claims_and_legacy_claims_md(tmp_path):
    repo = _mini_repo(tmp_path, _claim("a"))
    assert check(repo, min_claims=2).blocking[0].code == "too_few_claims"
    assert check(repo, min_claims=1).ok
    (repo / "CLAIMS.md").write_text("| id | problem |\n|---|---|\n| legacy | P |\n")
    assert [i.code for i in check(repo).blocking] == ["claims_md_legacy"]
    rep = refresh_repo(repo)  # refuses to clobber the legacy table
    assert [i.code for i in rep.blocking] == ["claims_md_legacy"]
    assert (repo / "CLAIMS.md").read_text().startswith("| id |")
    assert refresh_repo(repo, force=True).ok
    assert "do not hand-edit" in (repo / "CLAIMS.md").read_text()

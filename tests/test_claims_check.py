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
                                verdict=verdict, stamped="t")],
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
    # REFUTED without FAIL is a warning; HEURISTIC needs nothing
    repo3 = _mini_repo(tmp_path / "r3", _claim("y", level="REFUTED", verdict="PASS"),
                       _claim("z", level="HEURISTIC", verdict="ERROR"))
    rep3 = check(repo3)
    assert rep3.ok and {i.code for i in rep3.issues} == {"refuted_without_fail"}
    # schema and graph errors short-circuit
    (tmp_path / "r3" / "claims" / "bad.yaml").write_text("id: bad\n")
    assert [i.code for i in check(repo3).issues] == ["schema_error"]
    (tmp_path / "r3" / "claims" / "bad.yaml").unlink()
    repo4 = _mini_repo(tmp_path / "r4", _claim("p", deps=["q"]), _claim("q", deps=["p"]))
    assert [i.code for i in check(repo4).issues] == ["graph_error"]


def test_current_on_noncurrent_and_imported_notes(tmp_path):
    repo = _mini_repo(tmp_path, _claim("old"), _claim("new", supersedes=["old"]),
                      _claim("user", deps=["old"], verifier="table-import"))
    refresh_repo(repo)
    rep = check(repo)
    assert rep.standings == {"old": "SUPERSEDED", "new": "CURRENT", "user": "STALE"}
    # `user` is STALE (it rests on a SUPERSEDED claim), not CURRENT, so no violation
    assert not any(i.code == "current_on_noncurrent" for i in rep.issues)
    assert any(i.code == "imported_unverified" and i.claim_id == "user" for i in rep.issues)
    assert rep.ok


def test_challenged_claim_blocks_dependents_only_via_current_rule(tmp_path):
    repo = _mini_repo(tmp_path, _claim("a"), _claim("b", deps=["a"]))
    save_receipt(repo, Receipt(id="r1", claim_id="a", reviewer="human", statement_sha256="0" * 64,
                               findings=[Finding(dimension="evidence_support", severity="blocking",
                                                 text="wrong")], verdict="BLOCK", created="t"))
    rep = refresh_repo(repo)
    assert rep.standings == {"a": "CHALLENGED", "b": "CURRENT"}
    assert any(i.code == "current_on_noncurrent" and i.claim_id == "b" for i in rep.issues)
    assert not rep.ok

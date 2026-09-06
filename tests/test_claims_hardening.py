"""M22b adversarial-review hardening: the promotion path refuses what it must."""
from __future__ import annotations

import asyncio
import json
import sys

import pytest
import yaml

from empiricist.claims.check import check, refresh_repo
from empiricist.claims.command_verifier import (
    certify_command_verifier,
    golden_suite_hash,
    load_command_verifier,
)
from empiricist.claims.importer import import_table
from empiricist.claims.model import load_all, save_claim
from empiricist.claims.promote import PromotionRefused, demote, formulate, promote, reverify
from empiricist.claims.registry import stamp
from empiricist.claims.standing import Finding, Receipt, save_receipt, statement_sha256

_CHECKER = '''import json, os, sys
data = json.load(open(os.environ["EMPIRICIST_EVIDENCE"]))
print("LEAK=" + os.environ.get("EMPIRICIST_TEST_LEAK", "absent"))
sys.exit(0 if data.get("ok") is True else 3)
'''


def _decl(**over):
    d = {"name": "toy", "version": "1", "argv": [sys.executable, "tools/check.py", "{evidence}"],
         "inputs": ["tools"], "fail_exit_codes": [3],
         "fixtures": {"pass": ["certs/good.json"], "fail": ["certs/bad.json"]}}
    d.update(over)
    return d


def _repo(tmp_path, **over):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "check.py").write_text(_CHECKER)
    (tmp_path / "certs").mkdir()
    (tmp_path / "certs" / "good.json").write_text(json.dumps({"ok": True}))
    (tmp_path / "certs" / "bad.json").write_text(json.dumps({"ok": False}))
    (tmp_path / "certs" / "mine.json").write_text(json.dumps({"ok": True, "claim": "x"}))
    (tmp_path / "certs" / "other.json").write_text(json.dumps({"ok": True, "claim": "o"}))
    (tmp_path / "claims" / "verifiers").mkdir(parents=True)
    (tmp_path / "claims" / "verifiers" / "toy.yaml").write_text(yaml.safe_dump(_decl(**over)))
    return tmp_path


def _ready(tmp_path, *, kind="dataset"):
    repo = _repo(tmp_path)
    assert certify_command_verifier(repo, "toy")[0] is not None
    formulate(repo, claim_id="P.x", problem="P", formulation_version="v1", kind=kind,
              statement="x holds")
    promote(repo, claim_id="P.x", level="VERIFIED_N", verifier="toy",
            evidence_path="certs/mine.json", n=1)
    return repo


def _receipt(repo, rid, cid, statement, *, verdict="PASS", blocking=False, closes=None,
             evidence=()):
    sev = "blocking" if blocking else "note"
    r = Receipt(id=rid, claim_id=cid, reviewer="human",
                statement_sha256=statement_sha256(statement), evidence_sha256=list(evidence),
                findings=[Finding(dimension="evidence_support", severity=sev, text="x")],
                verdict=verdict, closes=closes, created="2026-09-06")
    save_receipt(repo, r)
    return r


# ---- B1: a FAIL fixture that does not run certifies nothing
def test_missing_directory_or_symlinked_fixture_does_not_certify(tmp_path):
    repo = _repo(tmp_path, fixtures={"pass": ["certs/good.json"], "fail": ["certs/nope.json"]})
    s, problems = certify_command_verifier(repo, "toy")
    assert s is None and "not a committed regular file" in problems[0]
    outside = tmp_path.parent / f"{tmp_path.name}-outside.json"
    outside.write_text(json.dumps({"ok": False}))
    (repo / "certs" / "link.json").symlink_to(outside)
    for bad in ("certs", "certs/link.json"):
        decl = repo / "claims" / "verifiers" / "toy.yaml"
        decl.write_text(
            yaml.safe_dump(_decl(fixtures={"pass": ["certs/good.json"], "fail": [bad]})))
        s, problems = certify_command_verifier(repo, "toy")
        assert s is None and "not a committed regular file" in problems[0], bad


# ---- B2: only declared exit codes are FAIL; refuting an established claim needs a receipt
def test_undeclared_exit_is_error_and_refutation_needs_a_receipt(tmp_path):
    repo = _repo(tmp_path)
    certify_command_verifier(repo, "toy")
    (repo / "certs" / "garbage.json").write_text("{")     # checker crashes: exit 1
    formulate(repo, claim_id="P.h", problem="P", formulation_version="v1", kind="dataset",
              statement="h")
    with pytest.raises(PromotionRefused, match="returned ERROR, not FAIL"):
        promote(repo, claim_id="P.h", level="REFUTED", verifier="toy",
                evidence_path="certs/garbage.json")
    h = load_all(repo)["P.h"]
    assert h.level == "HEURISTIC" and h.evidence[-1].verdict == "ERROR"
    assert "exit=1" in h.evidence[-1].note and "not a declared FAIL code" in h.evidence[-1].note
    # a HEURISTIC claim can be refuted on a declared FAIL alone; REFUTED is then terminal
    c = promote(repo, claim_id="P.h", level="REFUTED", verifier="toy",
                evidence_path="certs/bad.json")
    assert c.level == "REFUTED"
    with pytest.raises(PromotionRefused, match="terminal"):
        promote(repo, claim_id="P.h", level="CONJECTURED", verifier="toy",
                evidence_path="certs/good.json")
    # an established claim needs a receipt to be refuted
    formulate(repo, claim_id="P.c", problem="P", formulation_version="v1", kind="dataset",
              statement="c")
    promote(repo, claim_id="P.c", level="VERIFIED_N", verifier="toy",
            evidence_path="certs/mine.json", n=1)
    with pytest.raises(PromotionRefused, match="refuting a VERIFIED_N claim .* requires"):
        promote(repo, claim_id="P.c", level="REFUTED", verifier="toy",
                evidence_path="certs/bad.json")
    _receipt(repo, "r-ref", "P.c", "c", verdict="REVISE")
    c = promote(repo, claim_id="P.c", level="REFUTED", verifier="toy",
                evidence_path="certs/bad.json", receipt_id="r-ref")
    assert c.level == "REFUTED" and c.receipts == ["r-ref"] and check(repo).ok


# ---- B3: STALE is not laundered by a promotion on other evidence
def test_stale_claim_must_be_reverified_before_promotion(tmp_path):
    repo = _ready(tmp_path)
    (repo / "certs" / "mine.json").write_text(json.dumps({"ok": True, "tampered": 1}))
    assert check(repo).standings == {"P.x": "STALE"}
    with pytest.raises(PromotionRefused, match="STALE .*changed:certs/mine.json.*reverify"):
        promote(repo, claim_id="P.x", level="CERTIFIED", verifier="toy",
                evidence_path="certs/other.json")
    assert load_all(repo)["P.x"].level == "VERIFIED_N"
    assert reverify(repo) == {"P.x": "re-verified"}
    promote(repo, claim_id="P.x", level="CERTIFIED", verifier="toy",
            evidence_path="certs/other.json")
    assert check(repo).ok


# ---- B4: reviewer shopping; SUPERSEDED claims
def test_challenged_or_superseded_claims_are_not_promotable(tmp_path):
    repo = _ready(tmp_path, kind="statement")
    _receipt(repo, "r-block", "P.x", "x holds", verdict="BLOCK", blocking=True)
    _receipt(repo, "r-ok", "P.x", "x holds")
    with pytest.raises(PromotionRefused, match="CHALLENGED by blocking receipt\\(s\\) r-block"):
        promote(repo, claim_id="P.x", level="CERTIFIED", verifier="toy",
                evidence_path="certs/good.json", receipt_id="r-ok")
    _receipt(repo, "r-close", "P.x", "x holds", closes="r-block")
    formulate(repo, claim_id="P.y", problem="P", formulation_version="v2", kind="statement",
              statement="y holds")
    save_claim(repo, load_all(repo)["P.y"].model_copy(update={"supersedes": ["P.x"]}))
    with pytest.raises(PromotionRefused, match="SUPERSEDED"):
        promote(repo, claim_id="P.x", level="CERTIFIED", verifier="toy",
                evidence_path="certs/good.json", receipt_id="r-ok")


# ---- S1 / S2: argv and environment hygiene
def test_option_shaped_evidence_and_parent_env_are_neutralised(tmp_path, monkeypatch):
    repo = _repo(tmp_path)
    v = load_command_verifier(repo, "toy")
    assert v.argv_for("--help")[-1] == "./--help"
    assert v.env_for("--help")["EMPIRICIST_EVIDENCE"] == "./--help"
    monkeypatch.setenv("EMPIRICIST_TEST_LEAK", "1")
    r = v.run("certs/good.json")
    assert r.verdict.value == "PASS" and "LEAK=absent" in r.details["stdout_tail"]
    assert len(r.details["env_sha256"]) == 64
    assert "EMPIRICIST_TEST_LEAK" not in r.details["env_keys"]


# ---- S3: inputs must cover what runs
def test_uncovered_pythonpath_refuses_certification(tmp_path):
    repo = _repo(tmp_path, env={"PYTHONPATH": "lib"})
    (repo / "lib").mkdir()
    (repo / "lib" / "rules.py").write_text("x = 1\n")
    s, problems = certify_command_verifier(repo, "toy")
    assert s is None and problems == ["lib is executed but not listed in inputs (its edits would "
                                      "not change binary_hash)"]
    (repo / "claims" / "verifiers" / "toy.yaml").write_text(
        yaml.safe_dump(_decl(env={"PYTHONPATH": "lib"}, inputs=["tools", "lib"])))
    assert certify_command_verifier(repo, "toy")[0] is not None


# ---- S4: unlockable paths refuse BEFORE anything runs or is written
def test_symlinked_evidence_refuses_before_running(tmp_path):
    repo = _ready(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-ev.json"
    outside.write_text(json.dumps({"ok": True}))
    (repo / "certs" / "link.json").symlink_to(outside)
    before = load_all(repo)["P.x"]
    with pytest.raises(PromotionRefused, match="evidence certs/link.json is not a committed"):
        promote(repo, claim_id="P.x", level="CERTIFIED", verifier="toy",
                evidence_path="certs/link.json")
    assert load_all(repo)["P.x"] == before and check(repo).ok


# ---- S5 / M6: fixtures are part of the stamp
def test_changed_fixture_invalidates_the_stamp(tmp_path):
    repo = _ready(tmp_path)
    v = load_command_verifier(repo, "toy")
    h1 = golden_suite_hash(repo, v.spec)
    (repo / "certs" / "bad.json").write_text(json.dumps({"ok": False, "v": 2}))
    assert golden_suite_hash(repo, v.spec) != h1
    with pytest.raises(PromotionRefused, match="fixtures changed since certification"):
        promote(repo, claim_id="P.x", level="CERTIFIED", verifier="toy",
                evidence_path="certs/mine.json")
    assert reverify(repo, claim_id="P.x") == {"P.x": "verifier toy: its fixtures changed since "
                                                     "certification; run certify-verifier again"}
    assert certify_command_verifier(repo, "toy")[0] is not None
    assert reverify(repo, claim_id="P.x") == {"P.x": "re-verified"}


# ---- S6: registry downgrade and unknown identities
def test_registry_refuses_downgrade_and_flags_unknown_identities(tmp_path):
    stamp(tmp_path, name="v", version="2", binary_hash="aa" * 32, golden_suite_hash="bb" * 32)
    with pytest.raises(ValueError, match="below the current v2"):
        stamp(tmp_path, name="v", version="1", binary_hash="aa" * 32, golden_suite_hash="bb" * 32)
    stamp(tmp_path, name="v", version="1", binary_hash="aa" * 32, golden_suite_hash="bb" * 32,
          allow_downgrade=True)
    stamp(tmp_path, name="v", version="v2.0", binary_hash="aa" * 32, golden_suite_hash="bb" * 32)
    repo = _repo(tmp_path)
    decl = repo / "claims" / "verifiers" / "toy.yaml"
    decl.write_text(yaml.safe_dump(_decl(version="2")))
    assert certify_command_verifier(repo, "toy")[0] is not None
    decl.write_text(yaml.safe_dump(_decl(version="1")))
    s, problems = certify_command_verifier(repo, "toy")
    assert s is None and "below the current v2" in problems[0]
    assert certify_command_verifier(repo, "toy", allow_downgrade=True)[0] is not None


# ---- S10 / M4: demote
def test_demote_refusals(tmp_path):
    repo = _ready(tmp_path)
    formulate(repo, claim_id="P.o", problem="P", formulation_version="v1", kind="dataset",
              statement="o")
    _receipt(repo, "r-other", "P.o", "o")
    _receipt(repo, "r-old", "P.x", "an older statement")
    _receipt(repo, "r-x", "P.x", "x holds")
    with pytest.raises(PromotionRefused, match="REFUTED is reached through promote"):
        demote(repo, claim_id="P.x", level="REFUTED", receipt_id="r-x", reason="r")
    with pytest.raises(PromotionRefused, match="not a receipt for P.x"):
        demote(repo, claim_id="P.x", level="HEURISTIC", receipt_id="r-other", reason="r")
    with pytest.raises(PromotionRefused, match="different statement"):
        demote(repo, claim_id="P.x", level="HEURISTIC", receipt_id="r-old", reason="r")
    d = demote(repo, claim_id="P.x", level="HEURISTIC", receipt_id="r-x", reason="r")
    assert d.level == "HEURISTIC"
    assert check(repo).ok


# ---- S11: legacy claims without PASS entries are re-locked, not stranded
def test_reverify_relocks_claims_without_pass_entries(tmp_path):
    repo = tmp_path
    (repo / "e.json").write_text("{}")
    (repo / "legacy.md").write_text(
        "| id | problem | statement | level | evidence | updated |\n|---|---|---|---|---|---|\n"
        "| L1 | P | legacy | CERTIFIED | e.json | 2026-01-01 |\n")
    assert import_table(repo / "legacy.md", repo).written == ["L1"]
    (repo / "e.json").write_text("{\"v\": 2}")
    assert check(repo).standings == {"L1": "STALE"}
    assert reverify(repo) == {"L1": "re-locked"}
    assert check(repo).standings == {"L1": "CURRENT"} and check(repo).ok


# ---- S12: promote inside a running event loop
def test_promote_inside_a_running_event_loop(tmp_path):
    repo = _repo(tmp_path)
    certify_command_verifier(repo, "toy")
    formulate(repo, claim_id="P.a", problem="P", formulation_version="v1", kind="dataset",
              statement="a")

    async def go():
        return promote(repo, claim_id="P.a", level="VERIFIED_N", verifier="toy",
                       evidence_path="certs/good.json", n=1)

    assert asyncio.run(go()).level == "VERIFIED_N"


# ---- S13: formulate locks path dependencies
def test_formulate_locks_path_dependencies(tmp_path):
    repo = _repo(tmp_path)
    (repo / "data").mkdir()
    (repo / "data" / "m.json").write_text("{}")
    formulate(repo, claim_id="P.d", problem="P", formulation_version="v1", kind="dataset",
              statement="d", depends_on=["data/m.json"])
    assert check(repo).ok and check(repo).standings == {"P.d": "CURRENT"}
    with pytest.raises(PromotionRefused, match="dependency data/none.json is not a committed"):
        formulate(repo, claim_id="P.e", problem="P", formulation_version="v1", kind="dataset",
                  statement="e", depends_on=["data/none.json"])


# ---- a REVISE receipt (warnings, no blocker) warrants CERTIFIED and leaves its warnings
# on record; the receipt's evidence must match
def test_elevated_accepts_a_non_blocking_receipt_over_the_same_evidence(tmp_path):
    from empiricist.claims.lock import sha256_file
    from empiricist.claims.standing import Finding, Receipt, save_receipt, statement_sha256

    repo = _ready(tmp_path, kind="statement")
    save_receipt(repo, Receipt(
        id="r-rev", claim_id="P.x", reviewer="model", statement_sha256=statement_sha256("x holds"),
        findings=[Finding(dimension="assumption_explicitness", severity="warning", text="scope")],
        verdict="REVISE", created="2026-09-06"))
    c = promote(repo, claim_id="P.x", level="CERTIFIED", verifier="toy",
                evidence_path="certs/mine.json", receipt_id="r-rev")
    assert c.level == "CERTIFIED" and "1 open warning(s)" in c.notes
    formulate(repo, claim_id="P.z", problem="P", formulation_version="v1", kind="statement",
              statement="z holds")
    promote(repo, claim_id="P.z", level="VERIFIED_N", verifier="toy",
            evidence_path="certs/good.json", n=1)
    _receipt(repo, "r-zb", "P.z", "z holds", verdict="BLOCK", blocking=True)
    with pytest.raises(PromotionRefused, match="CHALLENGED"):
        promote(repo, claim_id="P.z", level="CERTIFIED", verifier="toy",
                evidence_path="certs/good.json", receipt_id="r-zb")
    repo_x = repo
    mine = sha256_file(repo_x / "certs" / "mine.json")
    _receipt(repo, "r-ev", "P.x", "x holds", evidence=[mine])
    with pytest.raises(PromotionRefused, match="reviewed different evidence"):
        promote(repo, claim_id="P.x", level="FORMALIZED", verifier="toy",
                evidence_path="certs/other.json", receipt_id="r-ev")
    c = promote(repo, claim_id="P.x", level="FORMALIZED", verifier="toy",
                evidence_path="certs/mine.json", receipt_id="r-ev")
    assert c.level == "FORMALIZED"


# ---- M1 / M5: an edited checker has no stamp
def test_edited_checker_has_no_stamp(tmp_path):
    repo = _ready(tmp_path)
    (repo / "tools" / "check.py").write_text(_CHECKER + "\n# edited\n")
    with pytest.raises(PromotionRefused, match="no current stamp"):
        promote(repo, claim_id="P.x", level="CERTIFIED", verifier="toy",
                evidence_path="certs/mine.json")
    assert reverify(repo, claim_id="P.x") == {"P.x": "verifier toy has no current stamp"}
    refresh_repo(repo)

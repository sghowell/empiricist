"""formulate / promote / reverify / demote (M22b Task 3)."""
from __future__ import annotations

import json
import sys

import pytest
import yaml

from empiricist.claims.check import check
from empiricist.claims.command_verifier import certify_command_verifier
from empiricist.claims.model import load_all
from empiricist.claims.promote import (
    PromotionRefused,
    demote,
    formulate,
    promote,
    reverify,
    statement_sha256,
)
from empiricist.claims.standing import Finding, Receipt, save_receipt
from empiricist.cli import main

_CHECKER = '''import json, os, sys
data = json.load(open(os.environ["EMPIRICIST_EVIDENCE"]))
sys.exit(0 if data.get("ok") is True else 3)
'''


def _repo(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "check.py").write_text(_CHECKER)
    (tmp_path / "certs").mkdir()
    (tmp_path / "certs" / "good.json").write_text(json.dumps({"ok": True}))
    (tmp_path / "certs" / "bad.json").write_text(json.dumps({"ok": False}))
    (tmp_path / "certs" / "mine.json").write_text(json.dumps({"ok": True, "claim": "P.x"}))
    (tmp_path / "claims" / "verifiers").mkdir(parents=True)
    (tmp_path / "claims" / "verifiers" / "toy.yaml").write_text(yaml.safe_dump({
        "name": "toy", "version": "1", "argv": [sys.executable, "tools/check.py"],
        "inputs": ["tools"], "fixtures": {"pass": ["certs/good.json"], "fail": ["certs/bad.json"]},
    }))
    return tmp_path


def _receipt(repo, rid, cid, statement, *, blocking=False, closes=None):
    r = Receipt(id=rid, claim_id=cid, reviewer="human",
                statement_sha256=statement_sha256(statement),
                findings=[Finding(dimension="evidence_support",
                                  severity="blocking" if blocking else "note", text="x")],
                verdict="BLOCK" if blocking else "PASS", closes=closes, created="2026-09-06")
    save_receipt(repo, r)
    return r


def test_happy_path_formulate_certify_promote(tmp_path):
    repo = _repo(tmp_path)
    c = formulate(repo, claim_id="P.x", problem="P", formulation_version="v1", kind="statement",
                  statement="x holds")
    assert c.level == "HEURISTIC" and c.standing == "CURRENT"
    with pytest.raises(PromotionRefused, match="no current stamp"):
        promote(repo, claim_id="P.x", level="VERIFIED_N", verifier="toy",
                evidence_path="certs/mine.json", n=1)
    assert certify_command_verifier(repo, "toy")[0] is not None
    c = promote(repo, claim_id="P.x", level="VERIFIED_N", verifier="toy",
                evidence_path="certs/mine.json", n=1, coverage="exhaustive")
    assert c.level == "VERIFIED_N" and c.n == 1 and c.evidence[-1].verdict == "PASS"
    assert c.evidence[-1].verifier == "toy" and "argv=" in c.evidence[-1].note
    rep = check(repo)
    assert rep.ok and rep.standings == {"P.x": "CURRENT"}
    assert "| P.x |" in (repo / "CLAIMS.md").read_text()
    # elevated statement level needs a receipt for THIS statement without blockers
    with pytest.raises(PromotionRefused, match="requires a review receipt"):
        promote(repo, claim_id="P.x", level="CERTIFIED", verifier="toy",
                evidence_path="certs/mine.json")
    _receipt(repo, "r-other", "P.x", "some other statement")
    with pytest.raises(PromotionRefused, match="different statement"):
        promote(repo, claim_id="P.x", level="CERTIFIED", verifier="toy",
                evidence_path="certs/mine.json", receipt_id="r-other")
    _receipt(repo, "r-block", "P.x", "x holds", blocking=True)
    with pytest.raises(PromotionRefused, match="blocking"):
        promote(repo, claim_id="P.x", level="CERTIFIED", verifier="toy",
                evidence_path="certs/mine.json", receipt_id="r-block")
    _receipt(repo, "r-close", "P.x", "x holds", closes="r-block")
    _receipt(repo, "r-ok", "P.x", "x holds")
    c = promote(repo, claim_id="P.x", level="CERTIFIED", verifier="toy",
                evidence_path="certs/mine.json", receipt_id="r-ok")
    assert c.level == "CERTIFIED" and c.n is None and "r-ok" in c.receipts
    assert check(repo).ok
    # level cannot go down through promote; REFUTED needs a FAIL verdict
    with pytest.raises(PromotionRefused, match="only goes down through demote"):
        promote(repo, claim_id="P.x", level="CONJECTURED", verifier="toy",
                evidence_path="certs/mine.json")
    with pytest.raises(PromotionRefused, match="returned PASS, not FAIL"):
        promote(repo, claim_id="P.x", level="REFUTED", verifier="toy",
                evidence_path="certs/mine.json")


def test_failed_verifier_records_evidence_but_no_promotion(tmp_path):
    repo = _repo(tmp_path)
    formulate(repo, claim_id="P.y", problem="P", formulation_version="v1", kind="dataset",
              statement="y")
    certify_command_verifier(repo, "toy")
    with pytest.raises(PromotionRefused, match="returned FAIL"):
        promote(repo, claim_id="P.y", level="VERIFIED_N", verifier="toy",
                evidence_path="certs/bad.json", n=2)
    c = load_all(repo)["P.y"]
    assert c.level == "HEURISTIC" and c.evidence[-1].verdict == "FAIL"
    assert check(repo).ok


def test_dependencies_must_be_current_and_reverify_restores(tmp_path):
    repo = _repo(tmp_path)
    certify_command_verifier(repo, "toy")
    formulate(repo, claim_id="P.base", problem="P", formulation_version="v1", kind="dataset",
              statement="base")
    promote(repo, claim_id="P.base", level="VERIFIED_N", verifier="toy",
            evidence_path="certs/good.json", n=1)
    formulate(repo, claim_id="P.top", problem="P", formulation_version="v1", kind="dataset",
              statement="top", depends_on=["P.base"])
    # tamper with the base evidence -> base STALE -> top cannot be promoted on it
    (repo / "certs" / "good.json").write_text(json.dumps({"ok": True, "v": 2}))
    assert check(repo).standings["P.base"] == "STALE"
    with pytest.raises(PromotionRefused, match="dependency P.base is STALE"):
        promote(repo, claim_id="P.top", level="VERIFIED_N", verifier="toy",
                evidence_path="certs/mine.json", n=1)
    outcomes = reverify(repo)
    assert outcomes == {"P.base": "re-verified"}
    assert check(repo).standings["P.base"] == "CURRENT"
    promote(repo, claim_id="P.top", level="VERIFIED_N", verifier="toy",
            evidence_path="certs/mine.json", n=1)
    assert check(repo).ok
    # a re-verification that now FAILS keeps the claim STALE with the FAIL on record
    (repo / "certs" / "good.json").write_text(json.dumps({"ok": False}))
    assert reverify(repo, claim_id="P.base") == {"P.base": "still failing"}
    rep = check(repo)
    assert rep.standings["P.base"] == "STALE" and rep.standings["P.top"] == "STALE"


def test_demote_needs_a_receipt_and_lowers_only(tmp_path):
    repo = _repo(tmp_path)
    certify_command_verifier(repo, "toy")
    formulate(repo, claim_id="P.z", problem="P", formulation_version="v1", kind="dataset",
              statement="z")
    promote(repo, claim_id="P.z", level="VERIFIED_N", verifier="toy",
            evidence_path="certs/good.json", n=3)
    with pytest.raises(PromotionRefused, match="not a receipt"):
        demote(repo, claim_id="P.z", level="HEURISTIC", receipt_id="nope", reason="r")
    _receipt(repo, "r-d", "P.z", "z")
    with pytest.raises(PromotionRefused, match="must lower"):
        demote(repo, claim_id="P.z", level="CERTIFIED", receipt_id="r-d", reason="r")
    c = demote(repo, claim_id="P.z", level="HEURISTIC", receipt_id="r-d", reason="found a gap")
    assert c.level == "HEURISTIC" and c.n is None
    assert "found a gap" in c.notes and "r-d" in c.receipts
    assert check(repo).ok


def test_formulate_refusals(tmp_path):
    repo = _repo(tmp_path)
    formulate(repo, claim_id="P.a", problem="P", formulation_version="v1", kind="statement",
              statement="a")
    with pytest.raises(PromotionRefused, match="already exists"):
        formulate(repo, claim_id="P.a", problem="P", formulation_version="v1", kind="statement",
                  statement="a")
    with pytest.raises(PromotionRefused, match="not a known claim"):
        formulate(repo, claim_id="P.b", problem="P", formulation_version="v1", kind="statement",
                  statement="b", depends_on=["P.ghost"])


def test_cli_promotion_commands(tmp_path, capsys):
    repo = _repo(tmp_path)
    assert main(["claims", "certify-verifier", "--repo", str(repo), "--name", "toy"]) == 0
    assert main(["claims", "formulate", "--repo", str(repo), "--id", "P.c", "--problem", "P",
                 "--formulation-version", "v1", "--kind", "dataset", "--statement", "c"]) == 0
    assert main(["claims", "promote", "--repo", str(repo), "--id", "P.c", "--level", "VERIFIED_N",
                 "--verifier", "toy", "--evidence", "certs/good.json", "--n", "4"]) == 0
    assert main(["claims", "promote", "--repo", str(repo), "--id", "P.c", "--level", "CERTIFIED",
                 "--verifier", "toy", "--evidence", "certs/good.json"]) == 0  # dataset: no receipt
    out = capsys.readouterr().out
    assert "stamped" in out and "promote: P.c -> CERTIFIED" in out
    assert main(["claims", "promote", "--repo", str(repo), "--id", "P.c", "--level", "FORMALIZED",
                 "--verifier", "toy", "--evidence", "certs/bad.json"]) == 1
    assert "refused" in capsys.readouterr().err
    assert main(["claims", "reverify", "--repo", str(repo)]) == 0
    assert main(["claims", "check", "--repo", str(repo)]) == 0

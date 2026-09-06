"""Review receipts: human reviews (M22c Task 2)."""
from __future__ import annotations

import json
import sys

import pytest
import yaml

from empiricist.claims.check import check
from empiricist.claims.command_verifier import certify_command_verifier
from empiricist.claims.model import load_all, save_claim
from empiricist.claims.promote import PromotionRefused, formulate, promote
from empiricist.claims.review import ReviewRefused, parse_finding, record_human_review
from empiricist.claims.standing import Finding, Receipt, load_receipts, new_receipt_id
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
    (tmp_path / "claims" / "verifiers").mkdir(parents=True)
    (tmp_path / "claims" / "verifiers" / "toy.yaml").write_text(yaml.safe_dump({
        "name": "toy", "version": "1", "argv": [sys.executable, "tools/check.py", "{evidence}"],
        "inputs": ["tools"], "fixtures": {"pass": ["certs/good.json"], "fail": ["certs/bad.json"]},
    }))
    certify_command_verifier(tmp_path, "toy")
    formulate(tmp_path, claim_id="P.s", problem="P", formulation_version="v1", kind="statement",
              statement="s holds")
    promote(tmp_path, claim_id="P.s", level="VERIFIED_N", verifier="toy",
            evidence_path="certs/good.json", n=1)
    return tmp_path


def test_human_block_then_close_then_certified(tmp_path):
    repo = _repo(tmp_path)
    block = record_human_review(
        repo, claim_id="P.s", reviewer="Sean Howell", verdict="BLOCK",
        findings=[Finding(dimension="evidence_support", severity="blocking", text="gap")],
        target_level="CERTIFIED", now="2026-09-06T10:00:00+00:00",
    )
    assert block.id == "P.s.20260906.sean-howell" and block.evidence_sha256
    assert check(repo).standings == {"P.s": "CHALLENGED"}
    with pytest.raises(PromotionRefused, match="blocking"):
        promote(repo, claim_id="P.s", level="CERTIFIED", verifier="toy",
                evidence_path="certs/good.json", receipt_id=block.id)
    ok = record_human_review(
        repo, claim_id="P.s", reviewer="Sean Howell", verdict="PASS",
        findings=[Finding(dimension="evidence_support", severity="note", text="fixed")],
        closes=block.id, now="2026-09-06T11:00:00+00:00",
    )
    assert ok.id == "P.s.20260906.sean-howell.2" and ok.closes == block.id
    assert check(repo).standings == {"P.s": "CURRENT"}
    c = promote(repo, claim_id="P.s", level="CERTIFIED", verifier="toy",
                evidence_path="certs/good.json", receipt_id=ok.id)
    assert c.level == "CERTIFIED" and c.receipts == [ok.id]
    assert check(repo).ok
    # the receipt is bound to the statement it reviewed
    save_claim(repo, c.model_copy(update={"statement": "s holds, but stronger"}))
    assert {i.code for i in check(repo).blocking} == {"receipt_stale", "claims_md_stale"}


def test_human_review_refusals(tmp_path):
    repo = _repo(tmp_path)
    with pytest.raises(ReviewRefused, match="does not exist"):
        record_human_review(repo, claim_id="P.nope", reviewer="h", verdict="PASS")
    with pytest.raises(ReviewRefused, match="not a receipt of"):
        record_human_review(repo, claim_id="P.s", reviewer="h", verdict="PASS", closes="ghost")
    with pytest.raises(ReviewRefused, match="PASS receipt cannot carry a blocking"):
        record_human_review(repo, claim_id="P.s", reviewer="h", verdict="PASS",
                            findings=[Finding(dimension="decision_soundness",
                                              severity="blocking", text="x")])
    with pytest.raises(ReviewRefused, match="BLOCK receipt must name"):
        record_human_review(repo, claim_id="P.s", reviewer="h", verdict="BLOCK")
    with pytest.raises(ReviewRefused, match="unknown level"):
        record_human_review(repo, claim_id="P.s", reviewer="h", verdict="PASS",
                            target_level="PROVEN")
    with pytest.raises(ReviewRefused, match="dimension:severity:text"):
        parse_finding("just words")
    with pytest.raises(ReviewRefused, match="dimension"):
        parse_finding("vibes:blocking:x")
    assert parse_finding("internal_consistency: warning : odd").severity == "warning"
    with pytest.raises(ValueError, match="close itself"):
        Receipt(id="r", claim_id="P.s", reviewer="h", statement_sha256="0" * 64,
                verdict="PASS", created="2026-09-06", closes="r")
    with pytest.raises(ValueError, match="filename-safe"):
        Receipt(id="bad/id", claim_id="P.s", reviewer="h", statement_sha256="0" * 64,
                verdict="PASS", created="2026-09-06")
    assert new_receipt_id("P.s", "Grace Hopper", "2026-09-06T00:00:00Z",
                          {"P.s.20260906.grace-hopper"}) == "P.s.20260906.grace-hopper.2"
    assert load_receipts(repo) == {}
    assert load_all(repo)["P.s"].level == "VERIFIED_N"


def test_cli_review_human(tmp_path, capsys):
    repo = _repo(tmp_path)
    rc = main(["claims", "review", "--repo", str(repo), "--id", "P.s", "--human",
               "--reviewer", "Sean", "--verdict", "BLOCK",
               "--finding", "assumption_explicitness:blocking:hidden hypothesis"])
    assert rc == 0 and "wrote receipts/P.s." in capsys.readouterr().out
    assert main(["claims", "check", "--repo", str(repo)]) == 0
    assert "CHALLENGED" in (repo / "CLAIMS.md").read_text()
    assert main(["claims", "review", "--repo", str(repo), "--id", "P.s", "--human",
                 "--reviewer", "Sean", "--verdict", "PASS",
                 "--finding", "evidence_support:blocking:x"]) == 1
    assert "refused" in capsys.readouterr().err
    assert main(["claims", "review", "--repo", str(repo), "--id", "P.s"]) == 2

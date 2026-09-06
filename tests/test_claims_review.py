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
from empiricist.claims.review import (
    ReviewRefused,
    build_review_bundle,
    parse_finding,
    record_human_review,
    review_with_model,
)
from empiricist.claims.standing import Finding, Receipt, load_receipts, new_receipt_id
from empiricist.cli import main
from empiricist.llm.client import FakeLLMClient
from empiricist.llm.models import LLMResult

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
        "inputs": ["tools"], "fail_exit_codes": [3],
        "fixtures": {"pass": ["certs/good.json"], "fail": ["certs/bad.json"]},
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
    assert ok.id == "P.s.20260906.sean-howell.2" and ok.closes == [block.id]
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
    legacy = Receipt(id="r", claim_id="P.s", reviewer="h", statement_sha256="0" * 64,
                     verdict="PASS", created="2026-09-06", closes=None)
    assert legacy.closes == []
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


def test_cli_review_model_uses_the_harness_client(tmp_path, capsys, monkeypatch):
    import empiricist.llm.client as client_mod

    repo = _repo(tmp_path)
    ok = {"findings": [], "checked": _ALL, "verdict": "PASS"}
    fake = FakeLLMClient([_result(ok), _result(ok)])
    monkeypatch.setattr(client_mod, "ClaudeCodeClient", lambda **kw: fake)
    rc = main(["claims", "review", "--repo", str(repo), "--id", "P.s",
               "--target-level", "CERTIFIED"])
    out = capsys.readouterr().out
    assert rc == 0 and out.count("wrote receipts/") == 2 and "$0.5000" in out
    assert len(fake.calls) == 2 and (repo / ".empiricist" / "ledger.db").is_file()
    rids = sorted(load_receipts(repo))
    assert main(["claims", "promote", "--repo", str(repo), "--id", "P.s", "--level", "CERTIFIED",
                 "--verifier", "toy", "--evidence", "certs/good.json", "--receipt", rids[0]]) == 0


def _result(parsed, *, stop="end_turn"):
    return LLMResult(text="", parsed=parsed, stop_reason=stop, is_error=False, input_tokens=1,
                     output_tokens=1, cache_read_tokens=0, cache_creation_tokens=0,
                     cost_usd=0.5, duration_ms=1, session_id="s", uuid="u", model="fake")


_ALL = ["evidence_support", "assumption_explicitness", "internal_consistency",
        "ledger_consistency", "confidence_calibration", "decision_soundness"]


def test_model_review_bundle_and_two_samples(tmp_path):
    repo = _repo(tmp_path)
    claim = load_all(repo)["P.s"]
    bundle = build_review_bundle(repo, claim, target_level="CERTIFIED")
    assert "s holds" in bundle and "promotion requested: CERTIFIED" in bundle
    assert "certs/good.json" in bundle and '"ok": true' in bundle and "toy v1 -> PASS" in bundle
    block = {"findings": [{"dimension": "evidence_support", "severity": "blocking",
                           "text": "the certificate checks ok=true, not s", "where": "statement"}],
             "checked": _ALL, "verdict": "PASS"}   # verdict contradicts the finding -> BLOCK
    ok = {"findings": [], "checked": _ALL, "verdict": "PASS"}
    client = FakeLLMClient([_result(block), _result(ok)])
    receipts = review_with_model(repo, claim_id="P.s", client=client, target_level="CERTIFIED",
                                 now="2026-09-06T12:00:00+00:00")
    assert [r.verdict for r in receipts] == ["BLOCK", "PASS"]
    assert [c[0] for c in client.calls] == ["reviewer", "reviewer"]   # two fresh calls
    assert receipts[0].provenance["run_id"].startswith("review-P.s-")
    assert receipts[0].provenance["cost_usd"] == "0.5000"
    assert "[statement]" in receipts[0].findings[0].text
    assert check(repo).standings == {"P.s": "CHALLENGED"}   # any blocking sample blocks
    with pytest.raises(PromotionRefused, match="blocking"):
        promote(repo, claim_id="P.s", level="CERTIFIED", verifier="toy",
                evidence_path="certs/good.json", receipt_id=receipts[1].id)
    # a human closes the model's block; the PASS sample then carries the promotion
    closing = record_human_review(repo, claim_id="P.s", reviewer="Sean", verdict="PASS",
                                  closes=receipts[0].id, now="2026-09-06T13:00:00+00:00")
    assert check(repo).standings == {"P.s": "CURRENT"} and closing.closes == [receipts[0].id]
    c = promote(repo, claim_id="P.s", level="CERTIFIED", verifier="toy",
                evidence_path="certs/good.json", receipt_id=receipts[1].id)
    assert c.level == "CERTIFIED"


def test_model_review_unusable_samples_are_revise_receipts(tmp_path):
    repo = _repo(tmp_path)
    partial = {"findings": [], "checked": ["evidence_support"], "verdict": "PASS"}
    client = FakeLLMClient([_result(None), _result({"nonsense": 1}), _result(partial)])
    receipts = review_with_model(repo, claim_id="P.s", client=client, samples=3,
                                 now="2026-09-06T12:00:00+00:00")
    assert [r.verdict for r in receipts] == ["REVISE", "REVISE", "REVISE"]
    assert "no parseable review" in receipts[0].findings[0].text
    assert "examined only" in receipts[2].findings[0].text
    assert check(repo).standings == {"P.s": "CURRENT"}   # REVISE never blocks by itself
    # a client that returns nothing at all still leaves a receipt per sample
    receipts = review_with_model(repo, claim_id="P.s", client=FakeLLMClient([]), samples=1,
                                 now="2026-09-06T12:30:00+00:00")
    assert receipts[0].verdict == "REVISE" and len(load_receipts(repo)) == 4
    with pytest.raises(ReviewRefused, match="samples"):
        review_with_model(repo, claim_id="P.s", client=FakeLLMClient([]), samples=0)


def test_model_review_can_close_an_earlier_block_only_with_a_pass(tmp_path):
    repo = _repo(tmp_path)
    block = {"findings": [{"dimension": "ledger_consistency", "severity": "blocking",
                           "text": "no deps", "where": "depends_on"}], "checked": _ALL,
             "verdict": "BLOCK"}
    first = review_with_model(repo, claim_id="P.s", client=FakeLLMClient([_result(block)]),
                              samples=1, now="2026-09-06T12:00:00+00:00")
    assert first[0].verdict == "BLOCK" and check(repo).standings == {"P.s": "CHALLENGED"}
    with pytest.raises(ReviewRefused, match="not a receipt of"):
        review_with_model(repo, claim_id="P.s", client=FakeLLMClient([]), samples=1,
                          closes="ghost")
    # the claim is corrected; a fresh round: one sample still objects, one passes
    ok = {"findings": [], "checked": _ALL, "verdict": "PASS"}
    again = review_with_model(repo, claim_id="P.s", client=FakeLLMClient([_result(block),
                                                                           _result(ok)]),
                              samples=2, closes=first[0].id, now="2026-09-06T13:00:00+00:00")
    assert [r.verdict for r in again] == ["BLOCK", "PASS"]
    assert again[0].closes == [] and again[1].closes == [first[0].id]
    # the new BLOCK keeps the claim CHALLENGED even though the old one is closed
    assert check(repo).standings == {"P.s": "CHALLENGED"}
    # a REVISE sample (warnings only) closes too; an unusable sample never does
    warn = {"findings": [{"dimension": "assumption_explicitness", "severity": "warning",
                          "text": "scope", "where": "statement"}], "checked": _ALL,
            "verdict": "REVISE"}
    more = review_with_model(repo, claim_id="P.s", client=FakeLLMClient([_result(warn),
                                                                          _result(None)]),
                             samples=2, closes=[again[0].id], now="2026-09-06T13:30:00+00:00")
    assert [r.verdict for r in more] == ["REVISE", "REVISE"]
    assert more[0].closes == [again[0].id] and more[1].closes == []
    assert check(repo).standings == {"P.s": "CURRENT"}
    # one fresh sample may close several blocks at once (two-sample reviews block in pairs)
    final = review_with_model(repo, claim_id="P.s", client=FakeLLMClient([_result(ok)]),
                              samples=1, closes=[first[0].id, again[0].id],
                              now="2026-09-06T14:00:00+00:00")
    assert final[0].closes == [first[0].id, again[0].id]
    assert check(repo).standings == {"P.s": "CURRENT"}


def test_review_bundle_gives_every_evidence_file_a_fair_share(tmp_path):
    repo = _repo(tmp_path)
    (repo / "certs" / "big.json").write_text(json.dumps({"ok": True, "pad": "x" * 200_000}))
    (repo / "notes.md").write_text("FORMULATION TAIL MARKER " * 400)
    c = load_all(repo)["P.s"]
    big = c.evidence[0].model_copy(update={"path": "certs/big.json"})
    md = c.evidence[0].model_copy(update={"path": "notes.md", "verdict": "IMPORTED",
                                          "verifier": "table-import"})
    c = c.model_copy(update={"evidence": [*c.evidence, big, md]})
    bundle = build_review_bundle(repo, c, target_level="CERTIFIED", byte_cap=90_000)
    assert "FORMULATION TAIL MARKER" in bundle          # the note survives the big file
    assert bundle.count("(truncated;") == 1              # only the big file is cut


def test_bundle_states_level_semantics_and_full_verifier_identity(tmp_path):
    repo = _repo(tmp_path)
    c = load_all(repo)["P.s"]
    bundle = build_review_bundle(repo, c, target_level="CERTIFIED")
    assert bundle.startswith("# Level semantics of this ledger")
    assert "CERTIFIED: a certificate that a certified verifier replays" in bundle
    assert f"binary_hash {c.evidence[0].binary_hash}" in bundle    # full hash, not a prefix
    assert "toy v1: argv [" in bundle and "every file under inputs ['tools']" in bundle
    assert "current stamp: v1 binary_hash" in bundle
    (repo / "claims" / "LEVELS.md").write_text("Our levels: CERTIFIED means replayed by us.\n")
    bundle = build_review_bundle(repo, c, target_level="CERTIFIED")
    assert "Our levels: CERTIFIED means replayed by us." in bundle
    assert "charter, section 3" not in bundle

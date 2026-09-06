"""The dependency-level rule (charter section 3): levels are capped by dependencies unless
a human receipt waives it; dependencies are derived from certificate pins."""
from __future__ import annotations

import hashlib
import json
import sys

import pytest
import yaml

from empiricist.claims.check import check
from empiricist.claims.command_verifier import certify_command_verifier
from empiricist.claims.importer import derive_dependencies_from_pins
from empiricist.claims.model import load_all
from empiricist.claims.promote import PromotionRefused, formulate, promote
from empiricist.claims.review import record_human_review
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
    (tmp_path / "certs" / "a.json").write_text(json.dumps({"ok": True, "claim": "A"}))
    a_sha = hashlib.sha256((tmp_path / "certs" / "a.json").read_bytes()).hexdigest()
    (tmp_path / "certs" / "b.json").write_text(
        json.dumps({"ok": True, "claim": "B", "prior_A_sha256": a_sha}))
    (tmp_path / "claims" / "verifiers").mkdir(parents=True)
    (tmp_path / "claims" / "verifiers" / "toy.yaml").write_text(yaml.safe_dump({
        "name": "toy", "version": "1", "argv": [sys.executable, "tools/check.py", "{evidence}"],
        "inputs": ["tools"], "fail_exit_codes": [3],
        "fixtures": {"pass": ["certs/good.json"], "fail": ["certs/bad.json"]},
    }))
    assert certify_command_verifier(tmp_path, "toy")[0] is not None
    formulate(tmp_path, claim_id="A", problem="P", formulation_version="v1", kind="statement",
              statement="a")
    formulate(tmp_path, claim_id="B", problem="P", formulation_version="v1", kind="statement",
              statement="b", depends_on=["A"])
    return tmp_path


def test_level_is_capped_by_dependencies_unless_a_human_waives(tmp_path):
    repo = _repo(tmp_path)
    with pytest.raises(PromotionRefused, match="CONJECTURED is above dependency A at HEURISTIC"):
        promote(repo, claim_id="B", level="CONJECTURED", verifier="toy",
                evidence_path="certs/b.json")
    promote(repo, claim_id="A", level="CONJECTURED", verifier="toy", evidence_path="certs/a.json")
    b = promote(repo, claim_id="B", level="CONJECTURED", verifier="toy",
                evidence_path="certs/b.json")
    assert b.level == "CONJECTURED" and check(repo).ok
    # a model receipt cannot waive; a human receipt can
    with pytest.raises(PromotionRefused, match="waives level_inversion"):
        promote(repo, claim_id="B", level="VERIFIED_N", verifier="toy",
                evidence_path="certs/b.json", n=1)
    waiver = record_human_review(repo, claim_id="B", reviewer="Sean", verdict="PASS",
                                 waivers=["level_inversion"], now="2026-09-06T10:00:00+00:00")
    assert waiver.waivers == ["level_inversion"]
    b = promote(repo, claim_id="B", level="VERIFIED_N", verifier="toy",
                evidence_path="certs/b.json", n=1, receipt_id=waiver.id)
    assert b.level == "VERIFIED_N"
    rep = check(repo)
    assert rep.ok and any(i.code == "level_inversion" and i.claim_id == "B" for i in rep.issues)


def test_dependencies_from_certificate_pins(tmp_path):
    repo = _repo(tmp_path)
    # B's certificate pins A's certificate by sha256, but B was formulated without the path
    added = derive_dependencies_from_pins(repo)
    assert added == {}          # no evidence entries yet: nothing to read pins from
    promote(repo, claim_id="A", level="CONJECTURED", verifier="toy", evidence_path="certs/a.json")
    promote(repo, claim_id="B", level="CONJECTURED", verifier="toy", evidence_path="certs/b.json")
    added = derive_dependencies_from_pins(repo)
    assert added == {"B": ["certs/a.json"]}   # the claim edge existed; the file edge is new
    assert load_all(repo)["B"].depends_on == ["A", "certs/a.json"]
    assert derive_dependencies_from_pins(repo) == {} and check(repo).ok
    # a change to the pinned file now makes B STALE
    (repo / "certs" / "a.json").write_text(json.dumps({"ok": True, "claim": "A", "v": 2}))
    assert check(repo).standings["B"] == "STALE"


def test_cli_waive_and_deps_from_pins(tmp_path, capsys):
    repo = _repo(tmp_path)
    assert main(["claims", "review", "--repo", str(repo), "--id", "B", "--human",
                 "--reviewer", "Sean", "--verdict", "PASS", "--waive", "level_inversion"]) == 0
    assert main(["claims", "deps-from-pins", "--repo", str(repo)]) == 0
    assert "0 claim(s) updated" in capsys.readouterr().out

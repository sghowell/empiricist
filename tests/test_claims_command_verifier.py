"""The generic command verifier (M22b Task 2), offline with a tiny checker script."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from empiricist.claims.command_verifier import (
    certify_command_verifier,
    golden_suite_hash,
    load_command_verifier,
)
from empiricist.claims.model import ClaimSchemaError
from empiricist.claims.registry import current_stamp
from empiricist.ledger.models import Verdict

_CHECKER = '''import json, os, sys
path = os.environ["EMPIRICIST_EVIDENCE"] if len(sys.argv) < 2 else sys.argv[1]
data = json.load(open(path))
sys.exit(0 if data.get("ok") is True else 3)
'''


def _repo(tmp_path: Path, *, argv_style="env") -> Path:
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "check.py").write_text(_CHECKER)
    (tmp_path / "certs").mkdir()
    (tmp_path / "certs" / "good.json").write_text(json.dumps({"ok": True}))
    (tmp_path / "certs" / "bad.json").write_text(json.dumps({"ok": False}))
    (tmp_path / "claims" / "verifiers").mkdir(parents=True)
    argv = [sys.executable, "tools/check.py"]
    if argv_style == "placeholder":
        argv.append("{evidence}")
    decl = {
        "name": "toy_check", "version": "1", "argv": argv, "cwd": ".",
        "env": {"TOY": "1"}, "inputs": ["tools"],
        "fixtures": {"pass": ["certs/good.json"], "fail": ["certs/bad.json"]},
        "timeout_s": 30,
    }
    import yaml

    (tmp_path / "claims" / "verifiers" / "toy_check.yaml").write_text(yaml.safe_dump(decl))
    return tmp_path


def test_certify_and_run(tmp_path):
    repo = _repo(tmp_path)
    s, problems = certify_command_verifier(repo, "toy_check")
    assert problems == [] and s is not None
    assert current_stamp(repo, "toy_check").binary_hash == s.binary_hash
    v = load_command_verifier(repo, "toy_check")
    assert s.golden_suite_hash == golden_suite_hash(repo, v.spec)
    ok = v.run("certs/good.json")
    assert ok.verdict is Verdict.PASS and ok.details["exit_code"] == 0
    assert "EMPIRICIST_EVIDENCE" in ok.details["env_keys"] and "TOY" in ok.details["env_keys"]
    bad = v.run("certs/bad.json")
    assert bad.verdict is Verdict.FAIL and bad.details["exit_code"] == 3
    assert v.run("certs/missing.json").details.get("invalid") is True
    assert v.run("/etc/passwd").details.get("invalid") is True


def test_placeholder_argv_and_binary_hash_tracks_inputs(tmp_path):
    repo = _repo(tmp_path, argv_style="placeholder")
    v = load_command_verifier(repo, "toy_check")
    assert v.argv_for("certs/good.json")[-1] == "certs/good.json"
    h1 = v.binary_hash
    (repo / "tools" / "check.py").write_text(_CHECKER + "\n# edited\n")
    assert load_command_verifier(repo, "toy_check").binary_hash != h1


def test_certification_fails_when_the_fail_fixture_passes(tmp_path):
    repo = _repo(tmp_path)
    (repo / "certs" / "bad.json").write_text(json.dumps({"ok": True}))  # cannot fail any more
    s, problems = certify_command_verifier(repo, "toy_check")
    assert s is None and problems and "must FAIL" in problems[0]
    assert current_stamp(repo, "toy_check") is None


def test_declaration_validation(tmp_path):
    repo = _repo(tmp_path)
    with pytest.raises(ClaimSchemaError, match="no command verifier"):
        load_command_verifier(repo, "nope")
    import yaml

    decl = repo / "claims" / "verifiers" / "toy_check.yaml"
    data = yaml.safe_load(decl.read_text())
    data["fixtures"]["fail"] = []
    decl.write_text(yaml.safe_dump(data))
    with pytest.raises(ClaimSchemaError, match="PASS and one FAIL"):
        load_command_verifier(repo, "toy_check")
    decl.write_text("name: other\nversion: '1'\nargv: [x]\nfixtures: {pass: [a], fail: [b]}\n")
    with pytest.raises(ClaimSchemaError, match="does not match"):
        load_command_verifier(repo, "toy_check")


def test_timeout_is_an_error(tmp_path):
    repo = _repo(tmp_path)
    (repo / "tools" / "check.py").write_text("import time; time.sleep(5)\n")
    v = load_command_verifier(repo, "toy_check")
    r = v.run("certs/good.json", timeout_s=0.5)
    assert r.verdict is Verdict.ERROR and r.details.get("error") == "timeout"

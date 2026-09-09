"""`empiricist.packs`: the pack protocol, manifest registry and certification (M24a Task 1)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from empiricist import packs
from empiricist.claims.registry import current_stamp
from empiricist.ledger.models import Verdict
from empiricist.packs import (
    BytesFileVerifier,
    GoldenCase,
    PackError,
    PackManifest,
    certify_pack_verifier,
    golden_suite_hash,
    load_pack,
    pack_identity,
    pack_of,
    resolve_pack_verifier,
)
from empiricist.verifiers.base import VerifierResult


class _Toy(BytesFileVerifier):
    """PASS iff the JSON payload says {"ok": true}; FAIL otherwise."""

    name = "toy_pack_check"
    version = "2"

    def __init__(self, repo: Path, *, broken: bool = False) -> None:
        super().__init__(repo)
        self._broken = broken

    @property
    def binary_hash(self) -> str:
        return "ab" * 32

    def verify_bytes(self, payload: bytes) -> VerifierResult:
        data = json.loads(payload)
        if self._broken:   # a checker that cannot FAIL its must-FAIL golden
            return VerifierResult(verdict=Verdict.PASS, details={})
        return VerifierResult(
            verdict=Verdict.PASS if data.get("ok") is True else Verdict.FAIL,
            details={"detail": "ok flag"},
        )

    def golden_suite(self) -> list[GoldenCase]:
        return [
            GoldenCase("good", b'{"ok": true}', Verdict.PASS),
            GoldenCase("bad", b'{"ok": false}', Verdict.FAIL),
        ]


def _manifest(**kw) -> PackManifest:
    return PackManifest(name="toy", version="0.1", verifiers={"toy_pack_check": _Toy}, **kw)


def test_resolve_identity_and_pack_of(tmp_path, monkeypatch):
    monkeypatch.setattr(packs, "installed_packs", lambda: {"toy": _manifest()})
    v = resolve_pack_verifier(tmp_path, "toy_pack_check")
    assert isinstance(v, _Toy) and v.name == "toy_pack_check"
    assert resolve_pack_verifier(tmp_path, "nope") is None
    assert pack_identity("toy_pack_check") == ("2", "ab" * 32)
    assert pack_identity("nope") is None
    assert pack_of("toy_pack_check") == "toy" and pack_of("nope") is None


def test_run_reads_the_repository_file_and_errors_on_a_missing_one(tmp_path, monkeypatch):
    monkeypatch.setattr(packs, "installed_packs", lambda: {"toy": _manifest()})
    (tmp_path / "ev").mkdir()
    (tmp_path / "ev" / "good.json").write_text('{"ok": true}')
    v = resolve_pack_verifier(tmp_path, "toy_pack_check")
    assert v.run("ev/good.json").verdict is Verdict.PASS
    r = v.run("ev/missing.json")
    assert r.verdict is Verdict.ERROR and "missing.json" in r.details["error"]


def test_certify_pack_verifier_stamps_iff_every_golden_matches(tmp_path, monkeypatch):
    monkeypatch.setattr(packs, "installed_packs", lambda: {"toy": _manifest()})
    stamp, problems = certify_pack_verifier(tmp_path, "toy_pack_check")
    assert problems == [] and stamp is not None
    assert stamp.name == "toy_pack_check" and stamp.version == "2" and stamp.pack == "toy"
    assert stamp.golden_suite_hash == golden_suite_hash(_Toy(tmp_path).golden_suite())
    assert current_stamp(tmp_path, "toy_pack_check") == stamp
    # a checker that cannot FAIL its must-FAIL case certifies nothing
    broken = PackManifest(name="toy", version="0.1",
                          verifiers={"toy_pack_check": lambda repo: _Toy(repo, broken=True)})
    monkeypatch.setattr(packs, "installed_packs", lambda: {"toy": broken})
    stamp2, problems2 = certify_pack_verifier(tmp_path, "toy_pack_check")
    assert stamp2 is None and any("bad" in p and "must FAIL" in p for p in problems2)
    assert current_stamp(tmp_path, "toy_pack_check") == stamp   # the old stamp stands
    assert certify_pack_verifier(tmp_path, "nope")[0] is None


def test_golden_suite_hash_is_content_sensitive():
    a = [GoldenCase("x", b"1", Verdict.PASS)]
    assert golden_suite_hash(a) == golden_suite_hash(list(a))
    assert golden_suite_hash(a) != golden_suite_hash([GoldenCase("x", b"2", Verdict.PASS)])
    assert golden_suite_hash(a) != golden_suite_hash([GoldenCase("x", b"1", Verdict.FAIL)])


def test_load_pack_unknown_or_uninstallable_is_none(monkeypatch):
    assert load_pack("nope") is None
    import importlib

    real = importlib.import_module

    def boom(name, *a, **k):
        if name == "empiricist.packs.cosmology":
            raise ImportError("no flint here")
        return real(name, *a, **k)

    monkeypatch.setattr(importlib, "import_module", boom)
    assert load_pack("cosmology") is None


def test_two_packs_declaring_one_name_is_an_error(tmp_path, monkeypatch):
    other = PackManifest(name="other", version="0.1", verifiers={"toy_pack_check": _Toy})
    monkeypatch.setattr(packs, "installed_packs", lambda: {"toy": _manifest(), "other": other})
    with pytest.raises(PackError):
        resolve_pack_verifier(tmp_path, "toy_pack_check")


# -- the claim ledger resolves pack verifiers (M24a Task 2) ----------------------------------


def _repo_with_claim(tmp_path):
    from empiricist.claims.promote import formulate

    (tmp_path / "ev").mkdir()
    (tmp_path / "ev" / "good.json").write_text('{"ok": true}')
    (tmp_path / "ev" / "bad.json").write_text('{"ok": false}')
    formulate(tmp_path, claim_id="P.x", problem="P", formulation_version="v1",
              kind="statement", statement="x holds")
    return tmp_path


def test_promote_and_reverify_on_a_pack_verifier(tmp_path, monkeypatch):
    from empiricist.claims.check import check
    from empiricist.claims.promote import PromotionRefused, promote, reverify

    monkeypatch.setattr(packs, "installed_packs", lambda: {"toy": _manifest()})
    repo = _repo_with_claim(tmp_path)
    with pytest.raises(PromotionRefused, match="no current stamp"):
        promote(repo, claim_id="P.x", level="CONJECTURED", verifier="toy_pack_check",
                evidence_path="ev/good.json")
    stamp, _ = certify_pack_verifier(repo, "toy_pack_check")
    c = promote(repo, claim_id="P.x", level="CONJECTURED", verifier="toy_pack_check",
                evidence_path="ev/good.json")
    assert c.level == "CONJECTURED" and c.evidence[0].verifier == "toy_pack_check"
    assert c.evidence[0].binary_hash == "ab" * 32 and c.evidence[0].version == "2"
    assert c.evidence[0].golden_suite_hash == stamp.golden_suite_hash
    assert check(repo).ok
    assert reverify(repo, claim_id="P.x") == {"P.x": "re-verified"}
    with pytest.raises(PromotionRefused, match="unknown verifier"):
        promote(repo, claim_id="P.x", level="VERIFIED_N", verifier="nope",
                evidence_path="ev/good.json", n=1)


def test_a_declaration_shadows_a_pack_verifier_of_the_same_name(tmp_path, monkeypatch):
    import sys

    import yaml

    from empiricist.claims.command_verifier import CommandVerifier
    from empiricist.claims.promote import _resolve_verifier

    monkeypatch.setattr(packs, "installed_packs", lambda: {"toy": _manifest()})
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "check.py").write_text("import sys; sys.exit(0)\n")
    (tmp_path / "certs").mkdir()
    (tmp_path / "certs" / "good.json").write_text("{}")
    (tmp_path / "certs" / "bad.json").write_text("{}")
    (tmp_path / "claims" / "verifiers").mkdir(parents=True)
    (tmp_path / "claims" / "verifiers" / "toy_pack_check.yaml").write_text(yaml.safe_dump({
        "name": "toy_pack_check", "version": "1", "argv": [sys.executable, "tools/check.py"],
        "inputs": ["tools"],
        "fixtures": {"pass": ["certs/good.json"], "fail": ["certs/bad.json"]},
    }))
    assert isinstance(_resolve_verifier(tmp_path, "toy_pack_check"), CommandVerifier)


def test_check_sees_pack_verifier_drift(tmp_path, monkeypatch):
    from empiricist.claims import check as check_mod
    from empiricist.claims.check import check, refresh_repo
    from empiricist.claims.promote import promote

    monkeypatch.setattr(packs, "installed_packs", lambda: {"toy": _manifest()})
    monkeypatch.setattr(check_mod, "identity_for", packs.pack_identity)
    repo = _repo_with_claim(tmp_path)
    certify_pack_verifier(repo, "toy_pack_check")
    promote(repo, claim_id="P.x", level="CONJECTURED", verifier="toy_pack_check",
            evidence_path="ev/good.json")
    refresh_repo(repo)
    assert check(repo).standings["P.x"] == "CURRENT"

    class _Edited(_Toy):
        @property
        def binary_hash(self) -> str:
            return "cd" * 32

    edited = PackManifest(name="toy", version="0.1", verifiers={"toy_pack_check": _Edited})
    monkeypatch.setattr(packs, "installed_packs", lambda: {"toy": edited})
    rep = check(repo)
    assert rep.standings["P.x"] == "STALE"
    assert any(i.code == "verifier_drift" and "toy_pack_check" in i.detail for i in rep.issues)


def test_cli_packs_and_certify_verifier_on_a_pack(tmp_path, monkeypatch, capsys):
    from empiricist.cli import main

    monkeypatch.setattr(packs, "installed_packs", lambda: {"toy": _manifest()})
    assert main(["claims", "packs"]) == 0
    out = capsys.readouterr().out
    assert "toy 0.1" in out and "toy_pack_check v2" in out
    (tmp_path / "claims").mkdir()
    argv = ["claims", "certify-verifier", "--repo", str(tmp_path), "--name", "toy_pack_check"]
    assert main(argv) == 0
    assert "toy_pack_check v2" in capsys.readouterr().out
    assert current_stamp(tmp_path, "toy_pack_check").pack == "toy"
    assert main(["claims", "certify-verifier", "--repo", str(tmp_path), "--name", "nope"]) == 1
    assert "no installed pack" in capsys.readouterr().out

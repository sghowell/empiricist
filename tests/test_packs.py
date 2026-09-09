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

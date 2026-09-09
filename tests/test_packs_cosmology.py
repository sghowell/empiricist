"""The `cosmology` pack (M24b): death_and_gravity's replay checkers as pack verifiers.

Skips cleanly when the optional `cosmology` dependency group (sympy, python-flint) is
not installed; `load_pack("cosmology")` then reads as absent, which `tests/test_packs.py`
covers.
"""
from __future__ import annotations

import json
import textwrap
import uuid
from pathlib import Path

import pytest

pytest.importorskip("flint")
pytest.importorskip("sympy")

from empiricist import packs  # noqa: E402
from empiricist.ledger.models import Verdict  # noqa: E402
from empiricist.packs import (  # noqa: E402
    GoldenCase,
    PackManifest,
    certify_pack_verifier,
    load_pack,
)
from empiricist.packs.cosmology.replay import ReplayVerifier  # noqa: E402
from empiricist.packs.cosmology.vendored import vendored_package  # noqa: E402

# --- Task 1: the generic replay verifier over a fake checker -------------------------

_PINNED = {"schema": 1, "claim": "T-1", "value": "42", "residual": "0"}

_CHECKER = '''
"""A fake death_and_gravity checker: REPORT, build_report(), validate_report()."""
import json
from pathlib import Path

REPORT = Path(__file__).resolve().parents[2] / "certificates" / "cert.json"
MODE = "ok"


def build_report():
    if MODE == "crash":
        raise RuntimeError("the checker fell over")
    if MODE == "prior":
        raise ValueError("Pinned prior certificate changed")
    return json.loads(REPORT.read_text())


def validate_report(expected, actual):
    if expected != actual:
        raise ValueError("fake certificate differs from exact replay")
'''


def _fake_checker(root: Path, name: str, *, extra: str = "") -> object:
    """Lay out `<root>/src/<name>/verify.py` + `<root>/certificates/cert.json` the way a
    death_and_gravity checker directory is laid out, and import it as a vendored package."""
    (root / "src" / name).mkdir(parents=True)
    (root / "src" / name / "__init__.py").write_text('"""A fake vendored checker package."""\n')
    (root / "src" / name / "verify.py").write_text(textwrap.dedent(_CHECKER) + extra)
    (root / "certificates").mkdir()
    (root / "certificates" / "cert.json").write_text(json.dumps(_PINNED, indent=2) + "\n")
    pkg = vendored_package(name, root / "src")
    return __import__(f"{name}.verify", fromlist=["verify"]), pkg


def _verifier(tmp_path: Path, name: str | None = None, **kw) -> ReplayVerifier:
    # vendored names are process-global: one fresh package name per fake checker
    name = name or f"fakechk_{uuid.uuid4().hex[:8]}"
    checker, pkg = _fake_checker(tmp_path / name, name, **kw)
    pinned = (tmp_path / name / "certificates" / "cert.json").read_bytes()
    mutated = json.dumps({**_PINNED, "value": "43"}).encode()
    return ReplayVerifier(
        tmp_path, name=f"cosmo_{name}", version="1", checker_module=checker,
        engine_modules=[pkg],
        goldens=[GoldenCase("pinned", pinned, Verdict.PASS),
                 GoldenCase("mutated", mutated, Verdict.FAIL)],
    )


def test_replay_verifier_pass_fail_error(tmp_path):
    v = _verifier(tmp_path)
    assert v.name.startswith("cosmo_fakechk_") and v.version == "1"
    pinned, mutated = (c.payload for c in v.golden_suite())
    assert v.verify_bytes(pinned).verdict is Verdict.PASS
    r = v.verify_bytes(mutated)
    assert r.verdict is Verdict.FAIL and "differs" in r.details["detail"]
    # not a certificate at all: ERROR, never a verdict a promotion could use
    r = v.verify_bytes(b"not json {")
    assert r.verdict is Verdict.ERROR and "JSON" in r.details["error"]
    # the checker refusing to build a report (a changed pinned prior, a failed exact
    # identity) is the checker's FAIL, as in the repository's own adapter
    v._checker.MODE = "prior"
    fresh = ReplayVerifier(tmp_path, name="x", version="1", checker_module=v._checker,
                           engine_modules=[], goldens=[])
    r = fresh.verify_bytes(pinned)
    assert r.verdict is Verdict.FAIL and "Pinned prior" in r.details["detail"]
    # anything else the checker raises is a fault, not a verdict
    v._checker.MODE = "crash"
    fresh = ReplayVerifier(tmp_path, name="x", version="1", checker_module=v._checker,
                           engine_modules=[], goldens=[])
    r = fresh.verify_bytes(pinned)
    assert r.verdict is Verdict.ERROR and "fell over" in r.details["error"]


def test_replay_verifier_run_reads_the_repository_file(tmp_path):
    v = _verifier(tmp_path)
    pkg = v.name.removeprefix("cosmo_")
    assert v.run(f"{pkg}/certificates/cert.json").verdict is Verdict.PASS
    assert v.run(f"{pkg}/certificates/nope.json").verdict is Verdict.ERROR


def test_identity_covers_replay_checker_and_engine_sources(tmp_path):
    a = _verifier(tmp_path / "a", "fakechk_a")
    b = _verifier(tmp_path / "b", "fakechk_b")
    same = _verifier(tmp_path / "c", "fakechk_c")
    # identical sources under different package names: the identity is the source text
    assert a.binary_hash == b.binary_hash == same.binary_hash
    edited = _verifier(tmp_path / "d", "fakechk_d", extra="\n# an edit\n")
    assert edited.binary_hash != a.binary_hash
    # engine modules are hashed too
    fewer = ReplayVerifier(tmp_path, name="x", version="1", checker_module=a._checker,
                           engine_modules=[], goldens=[])
    assert fewer.binary_hash != a.binary_hash
    assert len(a.binary_hash) == 64


def test_certify_a_replay_verifier_through_a_fake_pack(tmp_path, monkeypatch):
    v = _verifier(tmp_path)
    manifest = PackManifest(name="fake", version="0", verifiers={v.name: lambda repo: v})
    monkeypatch.setattr(packs, "installed_packs", lambda: {"fake": manifest})
    stamp, problems = certify_pack_verifier(tmp_path, v.name)
    assert problems == [] and stamp is not None and stamp.pack == "fake"
    assert stamp.binary_hash == v.binary_hash


def test_vendored_package_is_served_ahead_of_sys_path(tmp_path):
    checker, pkg = _fake_checker(tmp_path / "v", "fakechk_v")
    assert Path(pkg.__file__).resolve().is_relative_to((tmp_path / "v" / "src").resolve())
    assert Path(checker.__file__).name == "verify.py"


# --- the manifest ----------------------------------------------------------------------

def test_manifest_loads_as_the_cosmology_pack():
    m = load_pack("cosmology")
    assert m is not None and m.name == "cosmology"
    assert m.problems.get("P8")

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
from empiricist.packs.cosmology import verifiers as cv  # noqa: E402
from empiricist.packs.cosmology.replay import ReplayVerifier  # noqa: E402
from empiricist.packs.cosmology.vendored import CHECKERS, vendored_package  # noqa: E402

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


# --- Task 2: the vendored families ---------------------------------------------------

P8A = ["cosmo_p8a", "cosmo_p8a_radiation", "cosmo_p8a_reference", "cosmo_p8a_asymptotics",
       "cosmo_p8a_backreaction", "cosmo_p8a_response", "cosmo_p8a_remainder"]
P8_BASE = ["cosmo_p8_s0", "cosmo_p8_s1"]
P8_CHAIN = ["cosmo_p8_chain"]   # replays the whole P8(b) chain: ~1 minute, marked slow


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """name -> verifier, each constructed once: a replay is cached per instance, so every
    golden case and the certification below cost one replay per verifier."""
    cache: dict[str, ReplayVerifier] = {}

    def get(name: str) -> ReplayVerifier:
        if name not in cache:
            cache[name] = cv.VERIFIERS[name](tmp_path_factory.mktemp("repo"))
        return cache[name]

    return get


def _instance_factory(v):
    return lambda repo: v


def _certify_with_instances(names, built, repo, monkeypatch):
    real = load_pack("cosmology")
    manifest = PackManifest(
        name="cosmology", version=real.version, problems=real.problems,
        verifiers={n: _instance_factory(built(n)) for n in names},
    )
    monkeypatch.setattr(packs, "installed_packs", lambda: {"cosmology": manifest})
    out = {}
    for n in names:
        stamp, problems = certify_pack_verifier(repo, n)
        assert problems == [], (n, problems)
        assert stamp is not None and stamp.pack == "cosmology" and stamp.name == n
        assert stamp.binary_hash == built(n).binary_hash
        out[n] = stamp
    return out


def test_manifest_loads_as_the_cosmology_pack():
    m = load_pack("cosmology")
    assert m is not None and m.name == "cosmology"
    assert m.problems == {"P8": "problems-v1.1"}
    assert set(m.verifiers) == set(P8A + P8_BASE + P8_CHAIN)
    assert all(n.startswith("cosmo_") for n in m.verifiers)


def test_vendored_checkers_are_what_runs(built):
    built("cosmo_p8a")
    import p8a
    import p8a.verify

    assert Path(p8a.__file__).resolve().is_relative_to(CHECKERS.resolve())
    assert p8a.verify.REPORT.is_file() and p8a.verify.REPORT.is_relative_to(CHECKERS)


@pytest.mark.parametrize("name", P8A + P8_BASE)
def test_every_golden_yields_exactly_its_verdict(name, built):
    v = built(name)
    suite = v.golden_suite()
    assert {c.expected for c in suite} == {Verdict.PASS, Verdict.FAIL}
    for c in suite:
        r = v.verify_bytes(c.payload)
        assert r.verdict is c.expected, (c.label, r.details)
        if c.expected is Verdict.FAIL:
            assert "differs" in r.details["detail"]


def test_fast_verifiers_certify_and_have_distinct_identities(built, tmp_path, monkeypatch):
    stamps = _certify_with_instances(P8A + P8_BASE, built, tmp_path, monkeypatch)
    hashes = {s.binary_hash for s in stamps.values()}
    assert len(hashes) == len(stamps)
    # a chain verifier's identity covers its predecessors' code: p8a_radiation hashes p8a
    assert len({s.golden_suite_hash for s in stamps.values()}) == len(stamps)
    reg = json.loads((tmp_path / "claims" / "verifiers.json").read_text())
    assert set(reg["stamps"]) == set(P8A + P8_BASE)


def test_run_reads_a_committed_certificate_from_the_repository(tmp_path):
    v = cv.VERIFIERS["cosmo_p8a"](tmp_path)   # a verifier is bound to one repository
    rel = "problems/P8/a/certificates/focusing.json"
    (tmp_path / rel).parent.mkdir(parents=True)
    (tmp_path / rel).write_bytes((CHECKERS / rel).read_bytes())
    assert v.run(rel).verdict is Verdict.PASS
    (tmp_path / rel).write_bytes(v.golden_suite()[-1].payload)
    assert v.run(rel).verdict is Verdict.FAIL


# --- Task 3: core's CLI certifies, promotes with, and reverifies by a pack verifier ------

def test_core_cli_certifies_promotes_reverifies_and_respects_shadowing(tmp_path, capsys):
    from empiricist.claims.check import check
    from empiricist.claims.model import load_all
    from empiricist.claims.promote import formulate
    from empiricist.cli import main

    repo = tmp_path
    rel = "problems/P8/certificates/s0-identities.json"
    (repo / rel).parent.mkdir(parents=True)
    (repo / rel).write_bytes((CHECKERS / rel).read_bytes())
    formulate(repo, claim_id="P8-0", problem="P8(b)", formulation_version="v1",
              kind="statement", statement="S0 identities hold")
    promote_argv = ["claims", "promote", "--repo", str(repo), "--id", "P8-0", "--level",
                    "CONJECTURED", "--verifier", "cosmo_p8_s0", "--evidence", rel]
    # promotion before certification is refused by core
    assert main(promote_argv) == 1
    assert "no current stamp" in capsys.readouterr().err
    assert main(["claims", "certify-verifier", "--repo", str(repo), "--name", "cosmo_p8_s0"]) == 0
    assert "cosmo_p8_s0 v1" in capsys.readouterr().out
    assert main(promote_argv) == 0
    c = load_all(repo)["P8-0"]
    e = c.evidence[-1]
    assert c.level == "CONJECTURED" and e.verifier == "cosmo_p8_s0" and e.verdict == "PASS"
    assert e.binary_hash and e.golden_suite_hash
    assert check(repo).ok and check(repo).standings == {"P8-0": "CURRENT"}
    # an elevated statement promotion still needs a receipt: core's rule, unchanged
    assert main([*promote_argv[:7], "CERTIFIED", *promote_argv[8:]]) == 1
    assert "requires a review receipt" in capsys.readouterr().err
    # reverify resolves the pack verifier by name
    assert main(["claims", "reverify", "--repo", str(repo), "--id", "P8-0"]) == 0
    assert "P8-0: re-verified" in capsys.readouterr().out
    # a repository declaration of the same name shadows the pack verifier (here an invalid
    # one, so the command route refuses); an unknown name is refused outright
    (repo / "claims" / "verifiers").mkdir(exist_ok=True)
    (repo / "claims" / "verifiers" / "cosmo_p8_s0.yaml").write_text("name: cosmo_p8_s0\n")
    assert main(["claims", "certify-verifier", "--repo", str(repo), "--name", "cosmo_p8_s0"]) == 1
    assert main(["claims", "promote", "--repo", str(repo), "--id", "P8-0", "--level",
                 "CONJECTURED", "--verifier", "cosmo_nope", "--evidence", rel]) == 1
    assert "unknown verifier" in capsys.readouterr().err


@pytest.mark.slow
def test_the_p8b_chain_verifier_reproduces_all_six_certificates(built, tmp_path, monkeypatch):
    v = built("cosmo_p8_chain")
    suite = v.golden_suite()
    assert sum(c.expected is Verdict.PASS for c in suite) == 6
    for c in suite:
        r = v.verify_bytes(c.payload)
        assert r.verdict is c.expected, (c.label, r.details)
    # the S0 anchor is checked inside the chain but is not one of its six reports
    s0 = (CHECKERS / "problems/P8/certificates/s0-identities.json").read_bytes()
    r = v.verify_bytes(s0)
    assert r.verdict is Verdict.FAIL and "none of" in r.details["detail"]
    _certify_with_instances(P8_CHAIN, built, tmp_path, monkeypatch)

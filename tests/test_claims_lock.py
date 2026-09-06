"""The hash lock (M22a Task 2)."""
from __future__ import annotations

import json

import pytest

from empiricist.claims.lock import (
    Lock,
    lock_paths_for,
    mismatches,
    read_lock,
    refresh_lock_entries,
    sha256_file,
    write_lock,
)
from empiricist.claims.model import ClaimFile, ClaimSchemaError, EvidenceEntry


def _repo(tmp_path):
    (tmp_path / "ev").mkdir()
    (tmp_path / "ev" / "cert.json").write_text('{"bound": "1/2"}')
    (tmp_path / "ev" / "data.csv").write_text("1,2,3\n")
    return tmp_path


def _claim(cid="P.x", deps=()):
    return ClaimFile(
        id=cid, problem="P", formulation_version="v1", kind="statement", statement="s",
        level="CERTIFIED", updated="2026-09-06", depends_on=list(deps),
        evidence=[EvidenceEntry(path="ev/cert.json", verifier="sos_certificate", version="1.0",
                                verdict="PASS", stamped="2026-09-06T00:00:00Z",
                                binary_hash="ab" * 32, golden_suite_hash="cd" * 32)],
    )


def test_sha256_and_lock_round_trip(tmp_path):
    repo = _repo(tmp_path)
    import hashlib

    assert sha256_file(repo / "ev" / "cert.json") == hashlib.sha256(b'{"bound": "1/2"}').hexdigest()
    c = _claim(deps=["ev/data.csv", "P.other"])
    assert lock_paths_for(c) == ["ev/cert.json", "ev/data.csv"]
    lock = refresh_lock_entries(repo, c, Lock())
    assert lock.files["ev/cert.json"].verifiers["sos_certificate"].version == "1.0"
    assert lock.files["ev/data.csv"].verifiers == {}
    write_lock(repo, lock)
    text = (repo / "claims.lock.json").read_text()
    assert text.endswith("\n") and json.loads(text)["version"] == 2
    assert read_lock(repo) == lock
    assert read_lock(tmp_path / "nowhere") == Lock()


def test_mismatches_detect_unlocked_missing_and_changed(tmp_path):
    repo = _repo(tmp_path)
    c = _claim(deps=["ev/data.csv"])
    assert mismatches(repo, {"P.x": c}) == {
        "P.x": ["unlocked:ev/cert.json", "unlocked:ev/data.csv"]
    }
    lock = refresh_lock_entries(repo, c, Lock())
    write_lock(repo, lock)
    assert mismatches(repo, {"P.x": c}) == {}
    (repo / "ev" / "cert.json").write_text('{"bound": "49/100"}')
    assert mismatches(repo, {"P.x": c}) == {"P.x": ["changed:ev/cert.json"]}
    (repo / "ev" / "data.csv").unlink()
    assert mismatches(repo, {"P.x": c})["P.x"] == ["changed:ev/cert.json", "missing:ev/data.csv"]


def test_verifier_identity_is_locked_too(tmp_path):
    """Editing the recorded verifier identity (version/binary/golden hash) is STALE."""
    repo = _repo(tmp_path)
    c = _claim()
    write_lock(repo, refresh_lock_entries(repo, c, Lock()))
    e = c.evidence[0]
    for change in ({"version": "999"}, {"binary_hash": "ee" * 32}, {"golden_suite_hash": None}):
        c2 = c.model_copy(update={"evidence": [e.model_copy(update=change)]})
        assert mismatches(repo, {"P.x": c2}) == {
            "P.x": ["verifier_changed:ev/cert.json:sos_certificate"]
        }
    c3 = c.model_copy(update={"evidence": [e.model_copy(update={"verifier": "lean-fork"})]})
    assert mismatches(repo, {"P.x": c3}) == {"P.x": ["verifier_unlocked:ev/cert.json:lean-fork"]}
    # two claims sharing a path with different verifiers coexist in the lock
    lock = refresh_lock_entries(repo, c3, refresh_lock_entries(repo, c, Lock()))
    assert set(lock.files["ev/cert.json"].verifiers) == {"sos_certificate", "lean-fork"}
    assert mismatches(repo, {"P.x": c, "P.y": c3.model_copy(update={"id": "P.y"})}, lock) == {}


def test_symlinks_and_outside_paths_are_refused(tmp_path):
    repo = _repo(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside.json"
    outside.write_text("{}")
    (repo / "ev" / "link.json").symlink_to(outside)
    c = _claim().model_copy(update={"evidence": [
        _claim().evidence[0].model_copy(update={"path": "ev/link.json"})]})
    with pytest.raises(FileNotFoundError, match="symlink"):
        refresh_lock_entries(repo, c, Lock())
    lock = Lock(files={"ev/link.json": {"sha256": "0" * 64, "verifiers": {}}})
    assert mismatches(repo, {"P.x": c}, lock)["P.x"][0] == "outside:ev/link.json"


def test_v1_lock_is_migrated(tmp_path):
    repo = _repo(tmp_path)
    (repo / "claims.lock.json").write_text(json.dumps({"version": 1, "files": {
        "ev/cert.json": {"sha256": "0" * 64, "verifier": {
            "name": "sos_certificate", "version": "1.0", "binary_hash": "ab" * 32,
            "golden_suite_hash": "cd" * 32}},
        "ev/data.csv": {"sha256": "1" * 64, "verifier": None},
    }}))
    lock = read_lock(repo)
    assert lock.version == 2
    assert lock.files["ev/cert.json"].verifiers["sos_certificate"].version == "1.0"
    assert lock.files["ev/data.csv"].verifiers == {}


def test_refresh_refuses_a_missing_file_and_malformed_lock(tmp_path):
    repo = _repo(tmp_path)
    c = _claim(deps=["ev/nope.csv"])
    with pytest.raises(FileNotFoundError, match="nope.csv"):
        refresh_lock_entries(repo, c, Lock())
    (repo / "claims.lock.json").write_text("{not json")
    with pytest.raises(ClaimSchemaError, match="malformed lock"):
        read_lock(repo)

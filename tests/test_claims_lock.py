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
                                verdict="PASS", stamped="t", binary_hash="ab" * 32,
                                golden_suite_hash="cd" * 32)],
    )


def test_sha256_and_lock_round_trip(tmp_path):
    repo = _repo(tmp_path)
    import hashlib

    assert sha256_file(repo / "ev" / "cert.json") == hashlib.sha256(b'{"bound": "1/2"}').hexdigest()
    c = _claim(deps=["ev/data.csv", "P.other"])
    assert lock_paths_for(c) == ["ev/cert.json", "ev/data.csv"]
    lock = refresh_lock_entries(repo, c, Lock())
    assert lock.files["ev/cert.json"].verifier["name"] == "sos_certificate"
    assert lock.files["ev/data.csv"].verifier is None
    write_lock(repo, lock)
    text = (repo / "claims.lock.json").read_text()
    assert text.endswith("\n") and json.loads(text)["version"] == 1
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


def test_refresh_refuses_a_missing_file_and_malformed_lock(tmp_path):
    repo = _repo(tmp_path)
    c = _claim(deps=["ev/nope.csv"])
    with pytest.raises(FileNotFoundError, match="nope.csv"):
        refresh_lock_entries(repo, c, Lock())
    (repo / "claims.lock.json").write_text("{not json")
    with pytest.raises(ClaimSchemaError, match="malformed lock"):
        read_lock(repo)

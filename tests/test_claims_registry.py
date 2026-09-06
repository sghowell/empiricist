"""The committed verifier registry (M22b Task 1)."""
from __future__ import annotations

from empiricist.claims.model import EvidenceEntry
from empiricist.claims.registry import (
    Registry,
    current_stamp,
    is_current,
    read_registry,
    registry_newer,
    stamp,
)


def _entry(verifier="lean", version="3.3", binary_hash="ab" * 32):
    return EvidenceEntry(path="ev/x.json", verifier=verifier, version=version, verdict="PASS",
                         stamped="t", binary_hash=binary_hash)


def test_stamp_round_trip_and_current(tmp_path):
    assert read_registry(tmp_path) == Registry()
    s = stamp(tmp_path, name="lean", version="3.3", binary_hash="ab" * 32,
              golden_suite_hash="cd" * 32, now="2026-09-06T00:00:00+00:00")
    assert current_stamp(tmp_path, "lean") == s
    assert is_current(tmp_path, name="lean", version="3.3", binary_hash="ab" * 32)
    assert not is_current(tmp_path, name="lean", version="3.4", binary_hash="ab" * 32)
    assert (tmp_path / "claims" / "verifiers.json").read_text().endswith("\n")


def test_registry_newer_semantics(tmp_path):
    stamp(tmp_path, name="lean", version="3.3", binary_hash="ab" * 32, golden_suite_hash="x")
    newer = registry_newer(tmp_path)
    assert not newer(_entry())                                   # same version, same hash
    assert newer(_entry(version="3.2"))                          # older evidence
    assert newer(_entry(binary_hash="ef" * 32))                  # same version, different hash
    assert not newer(_entry(verifier="table-import", version="1"))  # unknown verifier
    assert not newer(_entry(version="3.10"))                     # evidence is newer than registry
    stamp(tmp_path, name="lean", version="3.10", binary_hash="ab" * 32, golden_suite_hash="x")
    assert registry_newer(tmp_path)(_entry(version="3.3"))       # 3.10 > 3.3 numerically

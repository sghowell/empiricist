"""Claim-file schema and YAML codec (M22a Task 1)."""
from __future__ import annotations

import pytest

from empiricist.claims.model import (
    ClaimFile,
    ClaimSchemaError,
    EvidenceEntry,
    dump_claim,
    load_all,
    load_claim,
    parse_claim,
    save_claim,
)


def _claim(**over) -> ClaimFile:
    base = dict(
        id="P3.k1_all_four", problem="P3", formulation_version="p3-linear-optical-scheme-v1",
        kind="statement", statement="There exists a unitary 5-mode scheme ...",
        level="FORMALIZED", updated="2026-09-05",
        evidence=[EvidenceEntry(path="claims/evidence/c6e57d9d.lean", verifier="lean",
                                version="3.3", verdict="PASS", stamped="2026-09-05T23:59:00Z",
                                binary_hash="ab" * 32, golden_suite_hash="cd" * 32)],
    )
    base.update(over)
    return ClaimFile(**base)


def test_round_trip_is_byte_stable_and_sorted():
    c = _claim(depends_on=["P3.k0_at_most_three", "data/manifest.json"], notes="héllo")
    text = dump_claim(c)
    assert parse_claim(text) == c
    assert dump_claim(parse_claim(text)) == text
    import re

    keys = [m.group(1) for m in (re.match(r"^([a-z_]+):", line) for line in text.splitlines()) if m]
    assert keys == sorted(keys) and len(keys) >= 10
    assert "héllo" in text


def test_schema_errors_name_the_field():
    with pytest.raises(ClaimSchemaError, match="level"):
        parse_claim(dump_claim(_claim()).replace("level: FORMALIZED", "level: PROVEN"))
    with pytest.raises(ValueError, match="VERIFIED_N requires"):  # direct construction
        _claim(level="VERIFIED_N")
    with pytest.raises(ClaimSchemaError, match="VERIFIED_N-only"):
        parse_claim(dump_claim(_claim()).replace("n: null", "n: 9"))
    with pytest.raises(ClaimSchemaError, match="(?i)extra"):
        parse_claim(dump_claim(_claim()) + "bogus: 1\n")
    with pytest.raises(ClaimSchemaError, match="id"):
        parse_claim(dump_claim(_claim()).replace("id: P3.k1_all_four", "id: 'bad id/'"))
    with pytest.raises(ClaimSchemaError, match="YAML mapping"):
        parse_claim("- just\n- a list\n")


def test_paths_must_be_repo_relative():
    with pytest.raises(ValueError, match="repo-relative"):
        EvidenceEntry(path="/etc/passwd", verifier="v", version="1", verdict="PASS", stamped="t")
    with pytest.raises(ValueError, match="repo-relative"):
        EvidenceEntry(path="../x.json", verifier="v", version="1", verdict="PASS", stamped="t")
    with pytest.raises(ValueError, match="neither"):
        _claim(depends_on=["bad id"])
    with pytest.raises(ValueError, match="itself"):
        _claim(depends_on=["P3.k1_all_four"])
    c = _claim(depends_on=["data/manifest.json", "P3.k0"])
    assert c.depends_on == ["data/manifest.json", "P3.k0"]


def test_verified_n_carries_n_and_coverage():
    c = _claim(level="VERIFIED_N", n=9, coverage="exhaustive")
    assert parse_claim(dump_claim(c)).n == 9 and c.rank == 2


def test_load_all_checks_filenames(tmp_path):
    save_claim(tmp_path, _claim())
    (tmp_path / "claims" / "P3.other.yaml").write_text(dump_claim(_claim()))  # id != filename
    with pytest.raises(ClaimSchemaError, match="does not match the filename"):
        load_all(tmp_path)
    (tmp_path / "claims" / "P3.other.yaml").unlink()
    assert list(load_all(tmp_path)) == ["P3.k1_all_four"]
    assert load_claim(tmp_path / "claims" / "P3.k1_all_four.yaml").level == "FORMALIZED"
    assert load_all(tmp_path / "nowhere") == {}

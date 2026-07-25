"""Schema-version and in-place migration tests for campaign ledgers."""

from __future__ import annotations

import sqlite3

import pytest

from empiricist.campaign.state import CampaignState
from empiricist.ledger.db import Ledger
from empiricist.ledger.migrations import (
    LATEST_SCHEMA_VERSION,
    SchemaVersionError,
)

_LEGACY_SCHEMA = """
CREATE TABLE artifacts (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  problem TEXT NOT NULL,
  title TEXT NOT NULL,
  content_path TEXT NOT NULL,
  status TEXT NOT NULL,
  substatus TEXT,
  status_n INTEGER,
  coverage TEXT,
  created_at TEXT NOT NULL,
  run_id TEXT
);
CREATE TABLE evidence (
  artifact_id TEXT NOT NULL,
  verifier TEXT NOT NULL,
  verifier_version TEXT NOT NULL,
  binary_hash TEXT NOT NULL,
  verdict TEXT NOT NULL,
  details_json TEXT NOT NULL DEFAULT '{}',
  log_path TEXT,
  wall_s REAL,
  created_at TEXT NOT NULL
);
CREATE TABLE certifications (
  verifier TEXT NOT NULL,
  verifier_version TEXT NOT NULL,
  binary_hash TEXT NOT NULL,
  golden_suite_hash TEXT NOT NULL,
  verdict TEXT NOT NULL,
  stamped_at TEXT NOT NULL,
  run_id TEXT,
  PRIMARY KEY (verifier, verifier_version, binary_hash)
);
CREATE TABLE runs (
  run_id TEXT PRIMARY KEY,
  move TEXT NOT NULL,
  role TEXT,
  model TEXT,
  argv TEXT,
  seed INTEGER,
  config_hash TEXT,
  env_fingerprint TEXT,
  tokens_in INTEGER NOT NULL DEFAULT 0,
  tokens_out INTEGER NOT NULL DEFAULT 0,
  cache_read INTEGER NOT NULL DEFAULT 0,
  cost_usd REAL NOT NULL DEFAULT 0.0,
  peak_rss_mb REAL,
  exit_code INTEGER,
  started TEXT NOT NULL,
  ended TEXT,
  wall_s REAL
);
CREATE TABLE claims (
  id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  statement TEXT NOT NULL,
  family TEXT
);
"""


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def test_fresh_ledger_is_stamped_at_latest_schema_version(tmp_path):
    ledger = Ledger(tmp_path / "ledger.db")
    try:
        assert ledger.conn.execute("PRAGMA user_version").fetchone()[0] == (
            LATEST_SCHEMA_VERSION
        )
    finally:
        ledger.close()


def test_legacy_ledger_migrates_in_place_without_losing_rows(tmp_path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.executescript(_LEGACY_SCHEMA)
    conn.execute(
        "INSERT INTO artifacts"
        " (id, kind, problem, title, content_path, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("a" * 64, "statement", "P5", "legacy claim", "b" * 64, "HEURISTIC", "t0"),
    )
    conn.execute(
        "INSERT INTO runs (run_id, move, model, started)"
        " VALUES ('r0', 'SAMPLE', 'claude-fable-5', 't0')"
    )
    conn.commit()
    conn.close()

    ledger = Ledger(path)
    try:
        assert ledger.conn.execute("PRAGMA user_version").fetchone()[0] == (
            LATEST_SCHEMA_VERSION
        )
        assert ledger.get_artifact("a" * 64).problem_version == "legacy"
        assert ledger.get_run("r0").model == "claude-fable-5"

        assert {
            "problem_version",
        } <= _column_names(ledger.conn, "artifacts")
        assert {
            "claim_id",
            "run_id",
            "golden_suite_hash",
        } <= _column_names(ledger.conn, "evidence")
        assert {
            "problem",
            "problem_version",
            "metric",
            "scope_json",
            "created_at",
        } <= _column_names(ledger.conn, "claims")
        assert {
            "provider",
            "reasoning_mode",
            "reasoning_effort",
            "auth_route",
            "request_digest",
            "response_digest",
        } <= _column_names(ledger.conn, "runs")
        assert ledger.conn.execute(
            "SELECT name FROM sqlite_master"
            " WHERE type='table' AND name='certification_attempts'"
        ).fetchone()
        evidence_fks = {
            (row["from"], row["table"], row["to"])
            for row in ledger.conn.execute("PRAGMA foreign_key_list(evidence)")
        }
        assert ("claim_id", "claims", "id") in evidence_fks
        assert ("run_id", "runs", "run_id") in evidence_fks
    finally:
        ledger.close()


def test_open_refuses_a_database_from_a_newer_schema(tmp_path):
    path = tmp_path / "future.db"
    conn = sqlite3.connect(path)
    conn.execute(f"PRAGMA user_version={LATEST_SCHEMA_VERSION + 1}")
    conn.close()

    with pytest.raises(SchemaVersionError, match="newer than this build"):
        Ledger(path)


def test_readonly_inspection_can_read_legacy_pilot_without_migrating(tmp_path):
    run_dir = tmp_path / "legacy-run"
    run_dir.mkdir()
    path = run_dir / "ledger.db"
    conn = sqlite3.connect(path)
    conn.executescript(_LEGACY_SCHEMA)
    conn.execute(
        "INSERT INTO artifacts"
        " (id, kind, problem, title, content_path, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("a" * 64, "statement", "P5", "legacy", "b" * 64, "HEURISTIC", "t0"),
    )
    conn.execute(
        "INSERT INTO evidence"
        " (artifact_id, verifier, verifier_version, binary_hash, verdict,"
        " details_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("a" * 64, "legacy-v", "1", "c" * 64, "PASS", "{}", "t0"),
    )
    conn.execute(
        "INSERT INTO claims (id, artifact_id, statement, family)"
        " VALUES (?, ?, ?, ?)",
        ("d" * 64, "a" * 64, "legacy statement", "path"),
    )
    conn.execute(
        "INSERT INTO runs (run_id, move, model, started)"
        " VALUES ('r0', 'SAMPLE', 'claude-fable-5', 't0')"
    )
    conn.commit()
    conn.close()
    before = path.read_bytes()

    state = CampaignState.open_readonly(run_dir)
    try:
        artifact = state.ledger.get_artifact("a" * 64)
        assert artifact.problem_version == "legacy"
        evidence = state.ledger.evidence_for(artifact.id)
        assert evidence[0].claim_id is None
        assert evidence[0].golden_suite_hash is None
        claim = state.ledger.claims_for(artifact.id)[0]
        assert claim.problem == "legacy"
        assert claim.scope == {}
        run = state.ledger.get_run("r0")
        assert run.provider is None
        assert run.request_digest is None
    finally:
        state.close()

    assert path.read_bytes() == before
    conn = sqlite3.connect(path)
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
    finally:
        conn.close()

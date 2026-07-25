"""Versioned, in-place SQLite schema bootstrap and migration.

``PRAGMA user_version`` is the durable schema-version marker.  Version zero
means either a fresh database or a pre-migration Empiricist ledger; the v1
migration is deliberately additive so existing campaign rows survive.
"""

from __future__ import annotations

import sqlite3

from empiricist.ledger.schema import SCHEMA

LATEST_SCHEMA_VERSION = 1


class SchemaVersionError(RuntimeError):
    """Raised when a ledger cannot be safely opened by this build."""


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _add_column(
    conn: sqlite3.Connection,
    table: str,
    name: str,
    declaration: str,
) -> None:
    if table in _tables(conn) and name not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")


def _migrate_v0_to_v1(conn: sqlite3.Connection) -> None:
    """Add claim identity and model/certification provenance fields."""

    additions = (
        ("artifacts", "problem_version", "TEXT NOT NULL DEFAULT 'legacy'"),
        ("evidence", "claim_id", "TEXT REFERENCES claims(id)"),
        ("evidence", "run_id", "TEXT REFERENCES runs(run_id)"),
        ("evidence", "golden_suite_hash", "TEXT"),
        ("claims", "problem", "TEXT NOT NULL DEFAULT 'legacy'"),
        ("claims", "problem_version", "TEXT NOT NULL DEFAULT 'legacy'"),
        ("claims", "metric", "TEXT"),
        ("claims", "scope_json", "TEXT NOT NULL DEFAULT '{}'"),
        ("claims", "created_at", "TEXT NOT NULL DEFAULT ''"),
        ("runs", "provider", "TEXT"),
        ("runs", "reasoning_mode", "TEXT"),
        ("runs", "reasoning_effort", "TEXT"),
        ("runs", "auth_route", "TEXT"),
        ("runs", "request_digest", "TEXT"),
        ("runs", "response_digest", "TEXT"),
    )
    for table, name, declaration in additions:
        _add_column(conn, table, name, declaration)


def _ensure_v1_indexes(conn: sqlite3.Connection) -> None:
    """Create indexes that depend on columns added by the v1 migration."""

    # These must be created after ALTER TABLE when opening a v0 database, so
    # they intentionally do not live in SCHEMA.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_evidence_claim"
        " ON evidence(claim_id, created_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_certification_attempts_verifier"
        " ON certification_attempts(verifier, verifier_version, binary_hash, stamped_at)"
    )


def bootstrap_schema(conn: sqlite3.Connection) -> None:
    """Create or migrate the ledger schema to ``LATEST_SCHEMA_VERSION``.

    The current implementation has one additive migration.  It is idempotent
    up to the final version stamp, so an interrupted startup can be retried.
    """

    current = int(conn.execute("PRAGMA user_version").fetchone()[0])
    if current > LATEST_SCHEMA_VERSION:
        raise SchemaVersionError(
            f"ledger schema version {current} is newer than this build "
            f"(supports {LATEST_SCHEMA_VERSION})"
        )

    # CREATE IF NOT EXISTS fills in tables absent from both fresh and legacy
    # databases. Existing legacy tables are then expanded by the migration.
    conn.executescript(SCHEMA)
    if current == LATEST_SCHEMA_VERSION:
        _ensure_v1_indexes(conn)
        return
    if current != 0:
        raise SchemaVersionError(
            f"no migration path from ledger schema version {current}"
        )

    conn.execute("BEGIN IMMEDIATE")
    try:
        _migrate_v0_to_v1(conn)
        _ensure_v1_indexes(conn)
        conn.execute(f"PRAGMA user_version = {LATEST_SCHEMA_VERSION}")
    except BaseException:
        conn.rollback()
        raise
    else:
        conn.commit()

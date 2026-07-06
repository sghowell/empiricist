"""The Ledger: single-writer SQLite system-of-record.

Discipline (spec §4.2, §4.4): one transaction per transition; statuses
change only via record_evidence(); REFUTED is terminal. The orchestrator
owns the single Ledger instance — workers post results to it, they never
open their own write connection.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from empiricist.ledger.models import (
    Artifact,
    EvidenceRow,
    Status,
    Verdict,
)
from empiricist.ledger.schema import PRAGMAS, SCHEMA


class TerminalStatusError(Exception):
    """Raised on any attempt to change the status of a REFUTED artifact."""


class Ledger:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Explicit-transaction mode: we drive BEGIN IMMEDIATE / COMMIT ourselves
        # in _tx() rather than relying on sqlite3's implicit transaction
        # handling, so isolation_level must be None (classic autocommit
        # default) or the bootstrap executescript(PRAGMAS) + our own
        # BEGIN IMMEDIATE can collide ("cannot start a transaction within
        # a transaction").
        self.conn = sqlite3.connect(self.path, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(PRAGMAS)
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    @contextmanager
    def _tx(self):
        """One BEGIN IMMEDIATE ... COMMIT per state transition."""
        if self.conn.in_transaction:
            raise RuntimeError(
                "nested _tx: Ledger methods must not call each other inside a transaction"
            )
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield self.conn
        except BaseException:
            self.conn.rollback()
            raise
        else:
            self.conn.commit()

    # -- artifacts ---------------------------------------------------------

    def add_artifact(self, art: Artifact) -> None:
        """Register a new artifact row. Creation is not a transition: entry
        status is the caller's claim (datasets legitimately enter at
        VERIFIED_N, spec §4.1). Only the single-writer orchestrator calls
        this; all subsequent status changes go through record_evidence()."""
        with self._tx() as c:
            c.execute(
                "INSERT INTO artifacts (id, kind, problem, title, content_path, status,"
                " substatus, status_n, coverage, created_at, run_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (art.id, art.kind, art.problem, art.title, art.content_path,
                 art.status.value, art.substatus, art.status_n, art.coverage,
                 art.created_at, art.run_id),
            )

    def get_artifact(self, artifact_id: str) -> Artifact:
        row = self.conn.execute(
            "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
        ).fetchone()
        if row is None:
            raise KeyError(artifact_id)
        return Artifact(
            id=row["id"], kind=row["kind"], problem=row["problem"], title=row["title"],
            content_path=row["content_path"], status=Status(row["status"]),
            substatus=row["substatus"], status_n=row["status_n"],
            coverage=row["coverage"], created_at=row["created_at"], run_id=row["run_id"],
        )

    # -- evidence & status transitions --------------------------------------

    def record_evidence(
        self,
        ev: EvidenceRow,
        *,
        new_status: Status | None = None,
        status_n: int | None = None,
        coverage: str | None = None,
        substatus: str | None = None,
    ) -> None:
        """Insert an evidence row; optionally change status in the same transaction.

        This is the ONLY way a status changes (F1: no promotion without
        machine evidence).
        """
        with self._tx() as c:
            row = c.execute(
                "SELECT status FROM artifacts WHERE id = ?", (ev.artifact_id,)
            ).fetchone()
            if row is None:
                raise KeyError(ev.artifact_id)
            if new_status is not None:
                if Status(row["status"]) is Status.REFUTED:
                    raise TerminalStatusError(
                        f"artifact {ev.artifact_id} is REFUTED (terminal)"
                    )
                if new_status is Status.VERIFIED_N:
                    c.execute(
                        "UPDATE artifacts SET status = ?,"
                        " status_n = COALESCE(?, status_n),"
                        " coverage = COALESCE(?, coverage),"
                        " substatus = COALESCE(?, substatus)"
                        " WHERE id = ?",
                        (new_status.value, status_n, coverage, substatus, ev.artifact_id),
                    )
                else:
                    # status_n/coverage are VERIFIED_N-specific: clear on any other status.
                    c.execute(
                        "UPDATE artifacts SET status = ?, status_n = NULL,"
                        " coverage = NULL, substatus = COALESCE(?, substatus)"
                        " WHERE id = ?",
                        (new_status.value, substatus, ev.artifact_id),
                    )
            c.execute(
                "INSERT INTO evidence (artifact_id, verifier, verifier_version,"
                " binary_hash, verdict, details_json, log_path, wall_s, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ev.artifact_id, ev.verifier, ev.verifier_version, ev.binary_hash,
                 ev.verdict.value,
                 json.dumps(ev.details, sort_keys=True, separators=(",", ":")),
                 ev.log_path, ev.wall_s, ev.created_at),
            )

    def evidence_for(self, artifact_id: str) -> list[EvidenceRow]:
        rows = self.conn.execute(
            "SELECT * FROM evidence WHERE artifact_id = ? ORDER BY created_at, rowid",
            (artifact_id,),
        ).fetchall()
        return [
            EvidenceRow(
                artifact_id=r["artifact_id"], verifier=r["verifier"],
                verifier_version=r["verifier_version"], binary_hash=r["binary_hash"],
                verdict=Verdict(r["verdict"]), details=json.loads(r["details_json"]),
                log_path=r["log_path"], wall_s=r["wall_s"], created_at=r["created_at"],
            )
            for r in rows
        ]

    # -- edges ---------------------------------------------------------------

    def add_edge(self, src: str, dst: str, rel: str) -> None:
        with self._tx() as c:
            c.execute("INSERT INTO edges (src, dst, rel) VALUES (?, ?, ?)", (src, dst, rel))

    def edges_from(self, src: str) -> list[tuple[str, str, str]]:
        return [
            (r["src"], r["dst"], r["rel"])
            for r in self.conn.execute(
                "SELECT src, dst, rel FROM edges WHERE src = ?", (src,)
            )
        ]

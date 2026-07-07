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
from dataclasses import dataclass
from pathlib import Path

from empiricist.ledger.models import (
    Artifact,
    Certification,
    EvidenceRow,
    Run,
    Status,
    Verdict,
    now_iso,
)
from empiricist.ledger.schema import PRAGMAS, SCHEMA

# Sentinel for runs orphaned by a crash (reconcile_orphans). Outside the
# -1..-64 range Python uses for signal-killed subprocess returncodes.
ORPHANED_EXIT_CODE = -999


class TerminalStatusError(Exception):
    """Raised on any attempt to change the status of a REFUTED artifact."""


class RunAlreadyFinishedError(Exception):
    """Raised on a second finish_run for the same run (exactly-once discipline)."""


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
        return self._artifact_from_row(row)

    def find_artifacts(
        self,
        *,
        kind: str | None = None,
        problem: str | None = None,
        status: Status | str | None = None,
    ) -> list[Artifact]:
        """Query artifacts by any combination of (kind, problem, status) --
        every filter is optional (None = unconstrained). Ordered oldest to
        newest (created_at, rowid tiebreak); a caller wanting the single
        newest match (e.g. campaign.moves.ensure_enumerate's idempotent
        VERIFIED_N dataset lookup) takes the last element."""
        q = "SELECT * FROM artifacts"
        clauses: list[str] = []
        params: list[str] = []
        if kind is not None:
            clauses.append("kind = ?")
            params.append(kind)
        if problem is not None:
            clauses.append("problem = ?")
            params.append(problem)
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value if isinstance(status, Status) else status)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY created_at, rowid"
        rows = self.conn.execute(q, params).fetchall()
        return [self._artifact_from_row(r) for r in rows]

    @staticmethod
    def _artifact_from_row(row: sqlite3.Row) -> Artifact:
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

        On any status change, substatus is set to exactly the given value
        (None clears it — a sub-status never survives a lattice move
        implicitly); evidence-only records leave it untouched.
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
                        " substatus = ?"
                        " WHERE id = ?",
                        (new_status.value, status_n, coverage, substatus, ev.artifact_id),
                    )
                else:
                    # status_n/coverage are VERIFIED_N-specific: clear on any other status.
                    c.execute(
                        "UPDATE artifacts SET status = ?, status_n = NULL,"
                        " coverage = NULL, substatus = ?"
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

    # -- certification stamps (spec §7: the trust boundary) --------------------

    def add_certification(self, cert: Certification) -> None:
        """Upsert the stamp for a (verifier, version, binary_hash) triple.

        certifications is a CURRENT-STATE view (upsert), not an append-only
        ledger; historical certify runs live in `runs` (the M5 certify command
        must record verdict+suite hash there or as evidence for
        reconstructability).
        """
        with self._tx() as c:
            c.execute(
                "INSERT OR REPLACE INTO certifications (verifier, verifier_version,"
                " binary_hash, golden_suite_hash, verdict, stamped_at, run_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (cert.verifier, cert.verifier_version, cert.binary_hash,
                 cert.golden_suite_hash, cert.verdict.value, cert.stamped_at,
                 cert.run_id),
            )

    def is_certified(self, verifier: str, version: str, binary_hash: str) -> bool:
        """Registry rule: verify() may run only if a PASS stamp exists."""
        row = self.conn.execute(
            "SELECT verdict FROM certifications WHERE verifier = ?"
            " AND verifier_version = ? AND binary_hash = ?",
            (verifier, version, binary_hash),
        ).fetchone()
        return row is not None and row["verdict"] == Verdict.PASS.value

    def get_certification(
        self, verifier: str, version: str, binary_hash: str
    ) -> Certification | None:
        """The full current stamp for a verifier triple, or None.

        The M5 registry must check BOTH is_certified() AND that the stamp's
        golden_suite_hash matches the suite it expects (spec §7): a PASS earned
        against an outdated golden suite must not read as trust.
        """
        r = self.conn.execute(
            "SELECT * FROM certifications WHERE verifier = ?"
            " AND verifier_version = ? AND binary_hash = ?",
            (verifier, version, binary_hash),
        ).fetchone()
        if r is None:
            return None
        return Certification(
            verifier=r["verifier"], verifier_version=r["verifier_version"],
            binary_hash=r["binary_hash"], golden_suite_hash=r["golden_suite_hash"],
            verdict=Verdict(r["verdict"]), stamped_at=r["stamped_at"],
            run_id=r["run_id"],
        )

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

    # -- runs & resume (spec §4.4) -------------------------------------------

    def start_run(self, run: Run) -> None:
        with self._tx() as c:
            c.execute(
                "INSERT INTO runs (run_id, move, role, model, argv, seed, config_hash,"
                " env_fingerprint, tokens_in, tokens_out, cache_read, cost_usd,"
                " peak_rss_mb, exit_code, started, ended, wall_s)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run.run_id, run.move, run.role, run.model, run.argv, run.seed,
                 run.config_hash, run.env_fingerprint, run.tokens_in, run.tokens_out,
                 run.cache_read, run.cost_usd, run.peak_rss_mb, run.exit_code,
                 run.started, run.ended, run.wall_s),
            )

    def finish_run(
        self,
        run_id: str,
        *,
        exit_code: int,
        wall_s: float,
        peak_rss_mb: float | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cache_read: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        with self._tx() as c:
            cur = c.execute(
                "UPDATE runs SET exit_code = ?, wall_s = ?, peak_rss_mb = ?,"
                " tokens_in = ?, tokens_out = ?, cache_read = ?, cost_usd = ?,"
                " ended = ? WHERE run_id = ? AND ended IS NULL",
                (exit_code, wall_s, peak_rss_mb, tokens_in, tokens_out,
                 cache_read, cost_usd, now_iso(), run_id),
            )
            if cur.rowcount == 0:
                row = c.execute(
                    "SELECT ended FROM runs WHERE run_id = ?", (run_id,)
                ).fetchone()
                if row is None:
                    raise KeyError(run_id)
                raise RunAlreadyFinishedError(
                    f"run {run_id} already finished at {row['ended']}; "
                    "finish_run is exactly-once — the first finish's numbers stand"
                )

    def get_run(self, run_id: str) -> Run:
        r = self.conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if r is None:
            raise KeyError(run_id)
        return Run(
            run_id=r["run_id"], move=r["move"], role=r["role"], model=r["model"],
            argv=r["argv"], seed=r["seed"], config_hash=r["config_hash"],
            env_fingerprint=r["env_fingerprint"], tokens_in=r["tokens_in"],
            tokens_out=r["tokens_out"], cache_read=r["cache_read"],
            cost_usd=r["cost_usd"], peak_rss_mb=r["peak_rss_mb"],
            exit_code=r["exit_code"], started=r["started"], ended=r["ended"],
            wall_s=r["wall_s"],
        )

    def reconcile_orphans(self) -> int:
        """Mark runs that started but never ended (kill -9 mid-flight) as incomplete.

        Resume rule (a) from spec §4.4: the in-flight sample is discarded;
        nothing else is lost.

        Precondition: call once at resume, BEFORE this session's first
        start_run — it marks every ended-IS-NULL row and would orphan live
        runs if called mid-session.
        """
        with self._tx() as c:
            cur = c.execute(
                "UPDATE runs SET exit_code = ?, ended = ? WHERE ended IS NULL",
                (ORPHANED_EXIT_CODE, now_iso()),
            )
            return cur.rowcount

    def spent(self) -> Spent:
        """Total budget consumed, summed from runs (spec §4.4(b): caps continue).

        NOTE: this is a LOWER BOUND on true spend — in-flight runs contribute
        0 until finish_run, and runs killed mid-flight never record their
        cost. A capped campaign must reserve in-flight cost against the cap
        (M9 scheduler concern). cache_read is informational sub-accounting
        and deliberately not summed here.
        """
        r = self.conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0.0) AS cost,"
            " COALESCE(SUM(tokens_in), 0) AS tin,"
            " COALESCE(SUM(tokens_out), 0) AS tout FROM runs"
        ).fetchone()
        return Spent(cost_usd=r["cost"], tokens_in=r["tin"], tokens_out=r["tout"])


@dataclass(frozen=True)
class Spent:
    cost_usd: float
    tokens_in: int
    tokens_out: int

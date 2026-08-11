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

from empiricist.ledger.migrations import bootstrap_schema
from empiricist.ledger.models import (
    Artifact,
    Certification,
    Claim,
    EvidenceRow,
    Run,
    Status,
    Verdict,
    now_iso,
)
from empiricist.ledger.schema import PRAGMAS

# Sentinel for runs orphaned by a crash (reconcile_orphans). Outside the
# -1..-64 range Python uses for signal-killed subprocess returncodes.
ORPHANED_EXIT_CODE = -999
# A provider may have accepted a paid request even though the client never
# received enough usage data to account for it. Resume must not silently treat
# that run as free.
UNKNOWN_BILLING_EXIT_CODE = -996


def _row_value(row: sqlite3.Row, key: str, default=None):
    """Read an additive-migration field from either a v1 or legacy row."""
    return row[key] if key in row.keys() else default


class TerminalStatusError(Exception):
    """Raised on any attempt to change the status of a REFUTED artifact."""


class RunAlreadyFinishedError(Exception):
    """Raised on a second finish_run for the same run (exactly-once discipline)."""


class PromotionIntegrityError(RuntimeError):
    """A claimed artifact did not meet the certified atomic-ingestion contract."""


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
        try:
            self.conn.executescript(PRAGMAS)
            bootstrap_schema(self.conn)
        except BaseException:
            self.conn.close()
            raise

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
                "INSERT INTO artifacts (id, kind, problem, problem_version,"
                " title, content_path, status,"
                " substatus, status_n, coverage, created_at, run_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (art.id, art.kind, art.problem, art.problem_version, art.title,
                 art.content_path, art.status.value, art.substatus, art.status_n,
                 art.coverage, art.created_at, art.run_id),
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
            problem_version=_row_value(row, "problem_version", "legacy"),
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
        self_validating: bool = False,
    ) -> None:
        """Insert an evidence row; optionally change status in the same transaction.

        This is the ONLY way a status changes (F1: no promotion without
        machine evidence).

        On any status change, substatus is set to exactly the given value
        (None clears it — a sub-status never survives a lattice move
        implicitly); evidence-only records leave it untouched.

        A promotion to an ELEVATED status (rank >= VERIFIED_N) via this general
        primitive requires `self_validating=True` — an explicit acknowledgment
        that the promotion's warrant is a SELF-VALIDATING verifier (one whose
        evidence re-checks against already-certified verifiers, e.g. the P5
        dataset ingest validating witnesses against the certified A/B engines),
        NOT a golden-suite certification. Certification-gated promotions
        (e.g. Lean FORMALIZED) must route through `record_claimed_artifact`,
        whose in-transaction certification re-check is the authoritative gate.
        This makes the invariant "no elevated artifact without either a matching
        current certification or an explicit self-validating warrant" STRUCTURAL
        rather than by-convention.
        """
        with self._tx() as c:
            row = c.execute(
                "SELECT status FROM artifacts WHERE id = ?", (ev.artifact_id,)
            ).fetchone()
            if row is None:
                raise KeyError(ev.artifact_id)
            if ev.claim_id is not None:
                claim_row = c.execute(
                    "SELECT artifact_id FROM claims WHERE id = ?", (ev.claim_id,)
                ).fetchone()
                if claim_row is None:
                    raise PromotionIntegrityError(
                        f"evidence references missing claim {ev.claim_id}"
                    )
                if claim_row["artifact_id"] != ev.artifact_id:
                    raise PromotionIntegrityError(
                        f"claim {ev.claim_id} belongs to a different artifact"
                    )
            if new_status is not None:
                current_status = Status(row["status"])
                if current_status is Status.REFUTED:
                    raise TerminalStatusError(
                        f"artifact {ev.artifact_id} is REFUTED (terminal)"
                    )
                if new_status is Status.REFUTED:
                    if ev.verdict is not Verdict.FAIL:
                        raise PromotionIntegrityError(
                            f"transition to REFUTED requires FAIL evidence, "
                            f"not {ev.verdict.value}"
                        )
                elif ev.verdict is not Verdict.PASS:
                    raise PromotionIntegrityError(
                        f"promotion to {new_status.value} requires PASS evidence, "
                        f"not {ev.verdict.value}"
                    )
                elif new_status.rank < current_status.rank:
                    raise PromotionIntegrityError(
                        f"status transition cannot reduce epistemic rank from "
                        f"{current_status.value} to {new_status.value}"
                    )
                if (
                    new_status is not Status.REFUTED
                    and new_status.rank >= Status.VERIFIED_N.rank
                    and not self_validating
                ):
                    raise PromotionIntegrityError(
                        f"promotion to {new_status.value} via record_evidence requires "
                        "self_validating=True (a self-validating verifier); "
                        "certification-gated promotions must route through "
                        "record_claimed_artifact"
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
                "INSERT INTO evidence (artifact_id, claim_id, run_id, verifier,"
                " verifier_version, binary_hash, golden_suite_hash, verdict,"
                " details_json, log_path, wall_s, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ev.artifact_id, ev.claim_id, ev.run_id, ev.verifier,
                 ev.verifier_version, ev.binary_hash, ev.golden_suite_hash,
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
                claim_id=_row_value(r, "claim_id"),
                run_id=_row_value(r, "run_id"),
                golden_suite_hash=_row_value(r, "golden_suite_hash"),
                log_path=r["log_path"], wall_s=r["wall_s"], created_at=r["created_at"],
            )
            for r in rows
        ]

    # -- claim-bound, certified artifact ingestion ---------------------------

    def require_certification(
        self,
        verifier: str,
        version: str,
        binary_hash: str,
        golden_suite_hash: str,
    ) -> Certification:
        """Return the exact current PASS stamp or fail closed."""

        cert = self.get_certification(verifier, version, binary_hash)
        if (
            cert is None
            or cert.verdict is not Verdict.PASS
            or cert.golden_suite_hash != golden_suite_hash
        ):
            raise PromotionIntegrityError(
                f"{verifier} v{version} [{binary_hash[:12]}] lacks a current "
                f"PASS certification for golden suite {golden_suite_hash}"
            )
        return cert

    def claims_for(self, artifact_id: str) -> list[Claim]:
        columns = {
            row[1] for row in self.conn.execute("PRAGMA table_info(claims)")
        }
        order = "created_at, rowid" if "created_at" in columns else "rowid"
        rows = self.conn.execute(
            f"SELECT * FROM claims WHERE artifact_id = ? ORDER BY {order}",
            (artifact_id,),
        ).fetchall()
        return [
            Claim(
                id=row["id"],
                artifact_id=row["artifact_id"],
                problem=_row_value(row, "problem", "legacy"),
                problem_version=_row_value(row, "problem_version", "legacy"),
                statement=row["statement"],
                family=row["family"],
                metric=_row_value(row, "metric"),
                scope=json.loads(_row_value(row, "scope_json", "{}")),
                created_at=_row_value(row, "created_at", ""),
            )
            for row in rows
        ]

    def record_claimed_artifact(
        self,
        art: Artifact,
        claim: Claim,
        ev: EvidenceRow,
        *,
        expected_golden_suite_hash: str,
    ) -> Artifact:
        """Atomically record artifact, canonical claim, and certified PASS evidence.

        Repeating the same claim is idempotent. The same content may support a
        second, differently-scoped claim, which gets its own evidence row.
        """

        if ev.verdict is not Verdict.PASS:
            raise PromotionIntegrityError("claimed-artifact ingestion requires PASS evidence")
        if claim.artifact_id != art.id or ev.artifact_id != art.id:
            raise PromotionIntegrityError("artifact, claim, and evidence identities differ")
        if claim.problem != art.problem:
            raise PromotionIntegrityError(
                "claim problem does not match the claimed artifact"
            )
        if claim.problem_version != art.problem_version:
            raise PromotionIntegrityError(
                "claim problem version does not match the claimed artifact"
            )
        try:
            canonical_claim = Claim.create(
                artifact_id=claim.artifact_id,
                problem=claim.problem,
                problem_version=claim.problem_version,
                statement=claim.statement,
                family=claim.family,
                metric=claim.metric,
                scope=claim.scope,
            )
        except ValueError as exc:
            raise PromotionIntegrityError(
                f"claim identity is not canonical: {exc}"
            ) from exc
        if canonical_claim.id != claim.id:
            raise PromotionIntegrityError(
                "claim id is not the canonical hash of its semantic fields"
            )
        if ev.claim_id != claim.id:
            raise PromotionIntegrityError("evidence does not identify the checked claim")
        if ev.golden_suite_hash != expected_golden_suite_hash:
            raise PromotionIntegrityError("evidence does not pin the expected golden suite")
        scope_json = json.dumps(
            claim.scope,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

        with self._tx() as c:
            cert = c.execute(
                "SELECT verdict, golden_suite_hash FROM certifications"
                " WHERE verifier = ? AND verifier_version = ? AND binary_hash = ?",
                (ev.verifier, ev.verifier_version, ev.binary_hash),
            ).fetchone()
            if (
                cert is None
                or cert["verdict"] != Verdict.PASS.value
                or cert["golden_suite_hash"] != expected_golden_suite_hash
            ):
                raise PromotionIntegrityError(
                    f"{ev.verifier} v{ev.verifier_version} [{ev.binary_hash[:12]}] "
                    "lacks a current PASS certification for golden suite "
                    f"{expected_golden_suite_hash}"
                )

            existing_artifact = c.execute(
                "SELECT * FROM artifacts WHERE id = ?", (art.id,)
            ).fetchone()
            if existing_artifact is None:
                c.execute(
                    "INSERT INTO artifacts (id, kind, problem, problem_version,"
                    " title, content_path, status, substatus, status_n, coverage,"
                    " created_at, run_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        art.id,
                        art.kind,
                        art.problem,
                        art.problem_version,
                        art.title,
                        art.content_path,
                        art.status.value,
                        art.substatus,
                        art.status_n,
                        art.coverage,
                        art.created_at,
                        art.run_id,
                    ),
                )
            else:
                if any(
                    (
                        existing_artifact["kind"] != art.kind,
                        existing_artifact["problem"] != art.problem,
                        existing_artifact["problem_version"]
                        not in {art.problem_version, "legacy"},
                        existing_artifact["content_path"] != art.content_path,
                    )
                ):
                    raise PromotionIntegrityError(
                        f"artifact id collision for {art.id}: stored identity differs"
                    )
                old_status = Status(existing_artifact["status"])
                if old_status is Status.REFUTED:
                    raise TerminalStatusError(f"artifact {art.id} is REFUTED (terminal)")
                if art.status.rank > old_status.rank:
                    c.execute(
                        "UPDATE artifacts SET status = ?, substatus = ?, status_n = ?,"
                        " coverage = ?, run_id = COALESCE(?, run_id) WHERE id = ?",
                        (
                            art.status.value,
                            art.substatus,
                            art.status_n,
                            art.coverage,
                            art.run_id,
                            art.id,
                        ),
                    )

            existing_claim = c.execute(
                "SELECT * FROM claims WHERE id = ?", (claim.id,)
            ).fetchone()
            if existing_claim is None:
                c.execute(
                    "INSERT INTO claims (id, artifact_id, problem, problem_version,"
                    " statement, family, metric, scope_json, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        claim.id,
                        claim.artifact_id,
                        claim.problem,
                        claim.problem_version,
                        claim.statement,
                        claim.family,
                        claim.metric,
                        scope_json,
                        claim.created_at,
                    ),
                )
            else:
                expected = (
                    claim.artifact_id,
                    claim.problem,
                    claim.problem_version,
                    claim.statement,
                    claim.family,
                    claim.metric,
                    scope_json,
                )
                actual = (
                    existing_claim["artifact_id"],
                    existing_claim["problem"],
                    existing_claim["problem_version"],
                    existing_claim["statement"],
                    existing_claim["family"],
                    existing_claim["metric"],
                    existing_claim["scope_json"],
                )
                if actual != expected:
                    raise PromotionIntegrityError(
                        f"claim id collision for {claim.id}: stored identity differs"
                    )

            duplicate = c.execute(
                "SELECT 1 FROM evidence WHERE artifact_id = ? AND claim_id = ?"
                " AND verifier = ? AND verifier_version = ? AND binary_hash = ?"
                " AND golden_suite_hash = ? AND verdict = ?",
                (
                    ev.artifact_id,
                    ev.claim_id,
                    ev.verifier,
                    ev.verifier_version,
                    ev.binary_hash,
                    ev.golden_suite_hash,
                    Verdict.PASS.value,
                ),
            ).fetchone()
            if duplicate is None:
                c.execute(
                    "INSERT INTO evidence (artifact_id, claim_id, run_id, verifier,"
                    " verifier_version, binary_hash, golden_suite_hash, verdict,"
                    " details_json, log_path, wall_s, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        ev.artifact_id,
                        ev.claim_id,
                        ev.run_id,
                        ev.verifier,
                        ev.verifier_version,
                        ev.binary_hash,
                        ev.golden_suite_hash,
                        ev.verdict.value,
                        json.dumps(
                            ev.details,
                            sort_keys=True,
                            separators=(",", ":"),
                            allow_nan=False,
                        ),
                        ev.log_path,
                        ev.wall_s,
                        ev.created_at,
                    ),
                )
        return self.get_artifact(art.id)

    # -- certification stamps (spec §7: the trust boundary) --------------------

    def add_certification(self, cert: Certification) -> None:
        """Upsert the stamp for a (verifier, version, binary_hash) triple.

        ``certifications`` is the current-state view; every call is also
        appended to ``certification_attempts`` so failed and superseded
        certification outcomes remain reconstructable.
        """
        with self._tx() as c:
            c.execute(
                "INSERT INTO certification_attempts (verifier, verifier_version,"
                " binary_hash, golden_suite_hash, verdict, stamped_at, run_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (cert.verifier, cert.verifier_version, cert.binary_hash,
                 cert.golden_suite_hash, cert.verdict.value, cert.stamped_at,
                 cert.run_id),
            )
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
                "INSERT INTO runs (run_id, move, role, model, provider,"
                " reasoning_mode, reasoning_effort, auth_route, request_digest,"
                " response_digest, argv, seed, config_hash,"
                " env_fingerprint, tokens_in, tokens_out, cache_read, cost_usd,"
                " peak_rss_mb, exit_code, started, ended, wall_s)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,"
                " ?, ?, ?, ?)",
                (run.run_id, run.move, run.role, run.model, run.provider,
                 run.reasoning_mode, run.reasoning_effort, run.auth_route,
                 run.request_digest, run.response_digest, run.argv, run.seed,
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
        response_digest: str | None = None,
    ) -> None:
        with self._tx() as c:
            cur = c.execute(
                "UPDATE runs SET exit_code = ?, wall_s = ?, peak_rss_mb = ?,"
                " tokens_in = ?, tokens_out = ?, cache_read = ?, cost_usd = ?,"
                " response_digest = COALESCE(?, response_digest),"
                " ended = ? WHERE run_id = ? AND ended IS NULL",
                (exit_code, wall_s, peak_rss_mb, tokens_in, tokens_out,
                 cache_read, cost_usd, response_digest, now_iso(), run_id),
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
            provider=_row_value(r, "provider"),
            reasoning_mode=_row_value(r, "reasoning_mode"),
            reasoning_effort=_row_value(r, "reasoning_effort"),
            auth_route=_row_value(r, "auth_route"),
            request_digest=_row_value(r, "request_digest"),
            response_digest=_row_value(r, "response_digest"),
            argv=r["argv"], seed=r["seed"], config_hash=r["config_hash"],
            env_fingerprint=r["env_fingerprint"], tokens_in=r["tokens_in"],
            tokens_out=r["tokens_out"], cache_read=r["cache_read"],
            cost_usd=r["cost_usd"], peak_rss_mb=r["peak_rss_mb"],
            exit_code=r["exit_code"], started=r["started"], ended=r["ended"],
            wall_s=r["wall_s"],
        )

    def reconcile_orphans(self) -> int:
        """Close runs that started but never ended (kill -9 mid-flight).

        Resume rule (a) from spec §4.4: the in-flight sample is discarded;
        nothing else is lost. A provider-backed orphan is accounting-unknown
        because the remote service may have accepted and billed its request.

        Precondition: call once at resume, BEFORE this session's first
        start_run — it marks every ended-IS-NULL row and would orphan live
        runs if called mid-session.
        """
        with self._tx() as c:
            cur = c.execute(
                "UPDATE runs SET exit_code = CASE"
                " WHEN provider IS NOT NULL THEN ? ELSE ? END,"
                " ended = ? WHERE ended IS NULL",
                (UNKNOWN_BILLING_EXIT_CODE, ORPHANED_EXIT_CODE, now_iso()),
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

    def run_aggregates(self) -> list[RoleAggregate]:
        """Per-role cost/token/run-count aggregates over `runs` (M7 T3: the
        report's per-role header line). `role` is nullable in the schema (a
        non-model subprocess run, e.g. an ENUMERATE-tier verifier call, has
        no role) -- that bucket is reported as `role=None` rather than
        dropped, so `SUM(runs.cost_usd)` always equals the sum across every
        returned row's `cost_usd`, same total-accounting discipline as
        `spent()`. Ordered by role (SQLite sorts NULL first) for a stable,
        deterministic report rendering.
        """
        rows = self.conn.execute(
            "SELECT role, COALESCE(SUM(cost_usd), 0.0) AS cost,"
            " COALESCE(SUM(tokens_in), 0) AS tin,"
            " COALESCE(SUM(tokens_out), 0) AS tout,"
            " COUNT(*) AS n"
            " FROM runs GROUP BY role ORDER BY role"
        ).fetchall()
        return [
            RoleAggregate(
                role=r["role"], cost_usd=r["cost"], tokens_in=r["tin"],
                tokens_out=r["tout"], run_count=r["n"],
            )
            for r in rows
        ]


@dataclass(frozen=True)
class Spent:
    cost_usd: float
    tokens_in: int
    tokens_out: int


@dataclass(frozen=True)
class RoleAggregate:
    role: str | None
    cost_usd: float
    tokens_in: int
    tokens_out: int
    run_count: int

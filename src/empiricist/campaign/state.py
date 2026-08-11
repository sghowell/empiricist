"""CampaignState: Ledger+Store+Registry+Population+Gates handles for one run
directory (M7 T1, spec §4.4/§9's create-or-resume semantics).

A run directory is `<run_dir>/ledger.db` (the single-writer SQLite ledger)
plus `<run_dir>/store/` (the content-addressed CAS) -- everything a campaign
touches lives under these two paths.  Mutating campaign work uses `load()`;
inspection uses `open_readonly()`, which requires an existing ledger and
does not bootstrap schema, reconcile runs, append events, or create SQLite
WAL/shared-memory sidecars.

Resume is not a special mode: `load()` always reconciles orphaned runs (spec
§4.4 resume rule (a) -- an in-flight sample killed mid-process is discarded,
nothing else is lost) and always logs a durable `search_events` marker for
the session boundary, `gen=-1` (outside the real generation numbering) so it
never collides with or is mistaken for a SEARCH wave. The marker's `trigger`
records which case this was: `"created"` for a genuinely empty run directory,
`"resume"` when prior `search_events` or `artifacts` rows already existed --
so the ledger itself carries an auditable trail of every process boundary a
campaign crossed, not just the first one.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from empiricist.ledger.db import Ledger
from empiricist.ledger.gates import Gates
from empiricist.ledger.migrations import LATEST_SCHEMA_VERSION, SchemaVersionError
from empiricist.search.database import Population
from empiricist.store import Store
from empiricist.verifiers.registry import Registry


@dataclass
class CampaignState:
    run_dir: Path
    ledger: Ledger
    store: Store
    registry: Registry
    population: Population
    gates: Gates

    @classmethod
    def _from_ledger(cls, run_dir: Path, ledger: Ledger) -> CampaignState:
        """Build the shared facades around an already-open ledger."""
        return cls(
            run_dir=run_dir,
            ledger=ledger,
            store=Store(run_dir / "store"),
            registry=Registry(ledger),
            population=Population(ledger),
            gates=Gates(ledger),
        )

    @classmethod
    def load(cls, run_dir: Path) -> CampaignState:
        """Create-or-resume: mkdir -p the run directory, open the Ledger/
        Store/Registry/Population/Gates handles, reconcile orphaned runs,
        and log the session-boundary `search_events` marker.

        Safe to call on both a brand-new directory and one from a prior
        session -- the ledger's own schema bootstrap (`Ledger.__init__`) and
        `reconcile_orphans` are both idempotent, and this method's own only
        write (the marker event) is unconditional, so calling `load` twice
        in a row simply logs two markers (the second correctly reads as a
        "resume": the first call's marker is itself a prior `search_events`
        row).
        """
        run_dir = Path(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)

        ledger = Ledger(run_dir / "ledger.db")
        population = Population(ledger)

        # Determine create-vs-resume BEFORE reconcile_orphans (which only
        # touches `runs`) so a prior session's evidence (search_events from
        # an earlier SEARCH/CONJECTURE wave, or artifacts from ENUMERATE) is
        # what's being checked, not anything this call itself is about to
        # write.
        existed = (
            ledger.conn.execute("SELECT 1 FROM search_events LIMIT 1").fetchone()
            is not None
            or ledger.conn.execute("SELECT 1 FROM artifacts LIMIT 1").fetchone()
            is not None
        )

        orphans = ledger.reconcile_orphans()
        population.log_event(
            -1, "resume" if existed else "created", {"orphans": orphans}
        )

        return cls._from_ledger(run_dir, ledger)

    @classmethod
    def open_readonly(cls, run_dir: Path) -> CampaignState:
        """Open an existing campaign for side-effect-free inspection.

        Unlike :meth:`load`, this method never creates a directory or
        database, bootstraps schema, reconciles orphaned runs, or logs a
        session marker.  SQLite's ``immutable=1`` URI flag is deliberate:
        plain ``mode=ro`` still creates ``-wal``/``-shm`` sidecars for this
        WAL-mode ledger when they are absent.  ``query_only`` is an
        additional connection-level guard against accidental writes through
        one of the normal Ledger mutation methods.

        The immutable view is a quiescent-ledger snapshot.  Callers that need
        crash recovery or current writes from an active WAL must use
        :meth:`load`, whose mutation is explicit.
        """
        run_dir = Path(run_dir)
        ledger_path = run_dir / "ledger.db"
        if not ledger_path.is_file():
            raise FileNotFoundError(f"campaign ledger does not exist: {ledger_path}")
        wal_path = ledger_path.with_name(f"{ledger_path.name}-wal")
        if wal_path.is_file() and wal_path.stat().st_size:
            raise RuntimeError(
                "campaign ledger has an active or uncheckpointed WAL; "
                "read-only inspection requires a quiescent campaign"
            )

        # Ledger's normal constructor creates parents, configures WAL, and
        # executes schema DDL, so inspection intentionally constructs the
        # same lightweight facade around a read-only SQLite connection.
        ledger = Ledger.__new__(Ledger)
        ledger.path = ledger_path
        uri = f"{ledger_path.resolve().as_uri()}?mode=ro&immutable=1"
        conn = sqlite3.connect(uri, uri=True, isolation_level=None)
        try:
            conn.row_factory = sqlite3.Row
            current_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
            if current_version > LATEST_SCHEMA_VERSION:
                raise SchemaVersionError(
                    f"ledger schema version {current_version} is newer than this "
                    f"build (supports {LATEST_SCHEMA_VERSION})"
                )
            conn.execute("PRAGMA query_only=ON")
        except BaseException:
            conn.close()
            raise
        ledger.conn = conn
        return cls._from_ledger(run_dir, ledger)

    def close(self) -> None:
        self.ledger.close()

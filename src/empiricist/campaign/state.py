"""CampaignState: Ledger+Store+Registry+Population+Gates handles for one run
directory (M7 T1, spec §4.4/§9's create-or-resume semantics).

A run directory is `<run_dir>/ledger.db` (the single-writer SQLite ledger)
plus `<run_dir>/store/` (the content-addressed CAS) -- everything a campaign
touches lives under these two paths, so `load()` is the entire bootstrap: no
other machinery constructs its own Ledger/Store for a live run.

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

from dataclasses import dataclass
from pathlib import Path

from empiricist.ledger.db import Ledger
from empiricist.ledger.gates import Gates
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
        store = Store(run_dir / "store")
        registry = Registry(ledger)
        population = Population(ledger)
        gates = Gates(ledger)

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

        return cls(
            run_dir=run_dir, ledger=ledger, store=store, registry=registry,
            population=population, gates=gates,
        )

    def close(self) -> None:
        self.ledger.close()

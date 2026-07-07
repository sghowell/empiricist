"""Population: the SEARCH loop's per-key elite archive over the ledger's
`population`/`evicted`/`search_events` tables (spec §9).

Unlike `ledger.frontier.Frontier` (a global multi-objective Pareto set),
Population keeps exactly one row PER `lc_orbit_key` -- the best-known
construction reaching that LC orbit -- compared by plain lexicographic
order on its `objective_vec` (e.g. `[fusion_count]`). This 1-D-per-key
elite structure is the correct one for M6 (spec's plan self-review: the
global Pareto frontier is not wired into the search loop in v0); a MAP-Elites
style `island`/`cell` label rides along on each row for the M7 scheduler.

No silent truncation: every time an elite is REPLACED (a strictly better
candidate wins), the row it displaced is logged to `evicted` with
`reason='improved'` and `dominated_by` set to the WINNING candidate's
`cert_hash` -- an eviction is always attributable to the certificate that
caused it. A worse-or-equal candidate never displaces the incumbent; it
only bumps `hit_count` (how many times this key has been re-hit without
improving) and reports no improvement. All writes go through
`Ledger._tx` (one transaction per `consider`/`log_event` call; Population
methods never nest `_tx`, matching the Ledger's single-writer discipline).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from empiricist.ledger.db import Ledger
from empiricist.ledger.models import now_iso


@dataclass(frozen=True)
class PopulationRow:
    lc_orbit_key: str
    island: int
    cell: str
    objective_vec: list[float]
    cert_hash: str | None
    hit_count: int


@dataclass(frozen=True)
class SearchEvent:
    gen: int
    trigger: str
    detail: dict[str, Any] | None
    ts: str


class Population:
    def __init__(self, ledger: Ledger) -> None:
        self._ledger = ledger

    def consider(
        self,
        lc_orbit_key: str,
        island: int,
        cell: str,
        objective_vec: list[float],
        cert_hash: str,
    ) -> bool:
        """Insert or upsert `lc_orbit_key`'s elite.

        New key -> INSERT, return True (an improvement: the population now
        covers a key it didn't before). Existing key with a strictly
        lexicographically smaller `objective_vec` -> REPLACE the row (fresh
        `hit_count=1`) + log the displaced row to `evicted` + return True.
        Existing key with a worse-or-equal vec -> leave the row untouched
        except `hit_count += 1`, return False.
        """
        with self._ledger._tx() as c:
            row = c.execute(
                "SELECT objective_vec FROM population WHERE lc_orbit_key = ?",
                (lc_orbit_key,),
            ).fetchone()
            if row is None:
                c.execute(
                    "INSERT INTO population"
                    " (lc_orbit_key, island, cell, objective_vec, cert_hash, hit_count)"
                    " VALUES (?, ?, ?, ?, ?, 1)",
                    (lc_orbit_key, island, cell, json.dumps(objective_vec), cert_hash),
                )
                return True

            incumbent_vec = json.loads(row["objective_vec"])
            if list(objective_vec) < incumbent_vec:
                c.execute(
                    "UPDATE population SET island = ?, cell = ?, objective_vec = ?,"
                    " cert_hash = ?, hit_count = 1 WHERE lc_orbit_key = ?",
                    (island, cell, json.dumps(objective_vec), cert_hash, lc_orbit_key),
                )
                c.execute(
                    "INSERT INTO evicted (lc_orbit_key, reason, dominated_by, ts)"
                    " VALUES (?, 'improved', ?, ?)",
                    (lc_orbit_key, cert_hash, now_iso()),
                )
                return True

            c.execute(
                "UPDATE population SET hit_count = hit_count + 1 WHERE lc_orbit_key = ?",
                (lc_orbit_key,),
            )
            return False

    def get(self, lc_orbit_key: str) -> PopulationRow | None:
        row = self._ledger.conn.execute(
            "SELECT * FROM population WHERE lc_orbit_key = ?", (lc_orbit_key,)
        ).fetchone()
        if row is None:
            return None
        return PopulationRow(
            lc_orbit_key=row["lc_orbit_key"],
            island=row["island"],
            cell=row["cell"],
            objective_vec=json.loads(row["objective_vec"]),
            cert_hash=row["cert_hash"],
            hit_count=row["hit_count"],
        )

    def count(self) -> int:
        row = self._ledger.conn.execute("SELECT COUNT(*) AS n FROM population").fetchone()
        return row["n"]

    def log_event(self, gen: int, trigger: str, detail: dict[str, Any] | None = None) -> None:
        with self._ledger._tx() as c:
            c.execute(
                "INSERT INTO search_events (gen, trigger, detail, ts) VALUES (?, ?, ?, ?)",
                (
                    gen,
                    trigger,
                    None if detail is None
                    else json.dumps(detail, sort_keys=True, separators=(",", ":")),
                    now_iso(),
                ),
            )

    def events(self, trigger: str | None = None) -> list[SearchEvent]:
        if trigger is None:
            rows = self._ledger.conn.execute(
                "SELECT gen, trigger, detail, ts FROM search_events ORDER BY ts, rowid"
            ).fetchall()
        else:
            rows = self._ledger.conn.execute(
                "SELECT gen, trigger, detail, ts FROM search_events"
                " WHERE trigger = ? ORDER BY ts, rowid",
                (trigger,),
            ).fetchall()
        return [
            SearchEvent(
                gen=r["gen"],
                trigger=r["trigger"],
                detail=None if r["detail"] is None else json.loads(r["detail"]),
                ts=r["ts"],
            )
            for r in rows
        ]

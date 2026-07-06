"""Pareto frontier over objective vectors (minimizing), persisted in the ledger.

A frontier-improvement event — consider() returning True — is the
Goodhart-resistant search score (spec §4.3). It is distinct from an
epistemic status promotion. The monotone version counter is MAX(frontier_version).

recompute_frontier() is the pure function used by the resume consistency
check (spec §4.4(d)): the persisted table must equal the recomputation
from the population, else resume fails hard.
"""

from __future__ import annotations

import json

from empiricist.ledger.db import Ledger
from empiricist.ledger.models import dominates


def recompute_frontier(vecs: dict[str, list[float]]) -> dict[str, list[float]]:
    """The non-dominated subset of vecs (pure; deterministic tie-handling).

    Duplicate vectors: the lexicographically-smallest key wins, matching the
    incremental rule that an equal vector never displaces an incumbent.
    """
    result: dict[str, list[float]] = {}
    for key in sorted(vecs):
        vec = vecs[key]
        if any(dominates(other, vec) or other == vec for other in result.values()):
            continue
        result = {k: v for k, v in result.items() if not dominates(vec, v)}
        result[key] = vec
    return result


class Frontier:
    def __init__(self, ledger: Ledger) -> None:
        self._ledger = ledger

    def version(self) -> int:
        row = self._ledger.conn.execute(
            "SELECT COALESCE(MAX(frontier_version), 0) AS v FROM pareto_frontier"
        ).fetchone()
        return row["v"]

    def entries(self) -> dict[str, list[float]]:
        return {
            r["lc_orbit_key"]: json.loads(r["objective_vec"])
            for r in self._ledger.conn.execute(
                "SELECT lc_orbit_key, objective_vec FROM pareto_frontier"
            )
        }

    def consider(self, key: str, vec: list[float]) -> bool:
        """Insert iff not dominated; evict newly-dominated rows; bump version.

        Returns True iff the frontier strictly improved (the event the
        stall detector and scheduler score on).
        """
        with self._ledger._tx() as c:
            rows = c.execute(
                "SELECT lc_orbit_key, objective_vec FROM pareto_frontier"
            ).fetchall()
            current = {r["lc_orbit_key"]: json.loads(r["objective_vec"]) for r in rows}
            incumbent = current.get(key)
            others = {k: v for k, v in current.items() if k != key}
            if any(dominates(v, vec) or v == vec for v in others.values()):
                return False
            if incumbent is not None and (dominates(incumbent, vec) or incumbent == vec):
                return False
            new_version = self.version() + 1
            for k, v in others.items():
                if dominates(vec, v):
                    c.execute("DELETE FROM pareto_frontier WHERE lc_orbit_key = ?", (k,))
            c.execute(
                "INSERT OR REPLACE INTO pareto_frontier"
                " (lc_orbit_key, objective_vec, frontier_version) VALUES (?, ?, ?)",
                (key, json.dumps(vec), new_version),
            )
            return True

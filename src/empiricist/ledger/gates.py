"""Persisted human-gate queue.

The four outer-loop gates (spec §9 of the harness doc, §4.2/§11 of the
implementation spec): REDUCE reformulations, opening a proof campaign,
accepting a PROVED_DRAFT for formalization, and anything leaving the repo.
An unattended campaign parks work here; the scheduler skips parked branches.
"""

from __future__ import annotations

import uuid

from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Gate, now_iso

GATE_KINDS = frozenset({"REDUCE", "PROOF_CAMPAIGN", "ACCEPT_DRAFT", "RELEASE"})


class GateError(Exception):
    pass


class Gates:
    def __init__(self, ledger: Ledger) -> None:
        self._ledger = ledger

    def open(self, kind: str, *, artifact_id: str, note: str | None = None) -> Gate:
        if kind not in GATE_KINDS:
            raise GateError(f"unknown gate kind: {kind!r} (expected one of {sorted(GATE_KINDS)})")
        gate = Gate(
            id=uuid.uuid4().hex, kind=kind, artifact_id=artifact_id,
            state="pending", opened_at=now_iso(), note=note,
        )
        with self._ledger._tx() as c:
            c.execute(
                "INSERT INTO gates (id, kind, artifact_id, state, opened_at, resolved_at, note)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (gate.id, gate.kind, gate.artifact_id, gate.state, gate.opened_at,
                 gate.resolved_at, gate.note),
            )
        return gate

    def list(self, *, state: str | None = None) -> list[Gate]:
        q, params = "SELECT * FROM gates", ()
        if state is not None:
            q, params = q + " WHERE state = ?", (state,)
        rows = self._ledger.conn.execute(q + " ORDER BY opened_at", params)
        return [self._from_row(r) for r in rows]

    def resolve(self, gate_id: str, *, approve: bool, note: str | None = None) -> Gate:
        with self._ledger._tx() as c:
            row = c.execute("SELECT * FROM gates WHERE id = ?", (gate_id,)).fetchone()
            if row is None:
                raise KeyError(gate_id)
            if row["state"] != "pending":
                raise GateError(f"gate {gate_id} already {row['state']}")
            c.execute(
                "UPDATE gates SET state = ?, resolved_at = ?,"
                " note = COALESCE(?, note) WHERE id = ?",
                ("approved" if approve else "rejected", now_iso(), note, gate_id),
            )
        return self._from_row(
            self._ledger.conn.execute("SELECT * FROM gates WHERE id = ?", (gate_id,)).fetchone()
        )

    @staticmethod
    def _from_row(r) -> Gate:
        return Gate(
            id=r["id"], kind=r["kind"], artifact_id=r["artifact_id"], state=r["state"],
            opened_at=r["opened_at"], resolved_at=r["resolved_at"], note=r["note"],
        )

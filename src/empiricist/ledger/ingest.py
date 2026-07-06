"""Ingest an artifact: content into the CAS, metadata row into the ledger.

The artifact id IS the blake3 digest of the canonical content — identity
and provenance are the same fact (spec §4.2 rule 1).
"""

from __future__ import annotations

from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Artifact, Status
from empiricist.store import Store


def ingest_artifact(
    ledger: Ledger,
    store: Store,
    *,
    content: bytes,
    kind: str,
    problem: str,
    title: str,
    status: Status,
    substatus: str | None = None,
    status_n: int | None = None,
    coverage: str | None = None,
    run_id: str | None = None,
) -> Artifact:
    digest = store.put(content)
    art = Artifact(
        id=digest, kind=kind, problem=problem, title=title, content_path=digest,
        status=status, substatus=substatus, status_n=status_n, coverage=coverage,
        run_id=run_id,
    )
    ledger.add_artifact(art)
    return art

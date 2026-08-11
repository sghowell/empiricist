"""Ingest an artifact: content into the CAS, metadata row into the ledger.

By default the artifact id IS the blake3 digest of the canonical content —
identity and provenance are the same fact (spec §4.2 rule 1). `content_path`
is ALWAYS that content digest (the CAS write is never overridden); `id` can
be overridden via `artifact_id` for the one documented exception in this
codebase (`search.conjecture.submit`'s semantic conjecture dedup, see its
docstring) where the identity that matters for dedup is a reduced hash of
the artifact's MATH, while the full content (incl. prose) is still what's
stored for provenance.
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
    problem_version: str = "legacy",
    substatus: str | None = None,
    status_n: int | None = None,
    coverage: str | None = None,
    run_id: str | None = None,
    artifact_id: str | None = None,
) -> Artifact:
    content_digest = store.put(content)
    art = Artifact(
        id=artifact_id if artifact_id is not None else content_digest,
        kind=kind, problem=problem, problem_version=problem_version,
        title=title, content_path=content_digest,
        status=status, substatus=substatus, status_n=status_n, coverage=coverage,
        run_id=run_id,
    )
    ledger.add_artifact(art)
    return art

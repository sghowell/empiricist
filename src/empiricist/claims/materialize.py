"""The batch hook (charter section 4: "batch loops materialize claims").

Every ingest path that records a claimed artifact calls `materialize_after_ingest`
after its ledger transaction commits. When a claims repository is configured -- the
`claims_repo` argument, else `EMPIRICIST_CLAIMS_REPO` -- the artifact becomes (or
refreshes) a claim file there, with its evidence bytes, lock entries and the verifier's
registry stamp. The projection never blocks the ledger write: a failure is logged and
`import-ledger` catches up later (the operation is idempotent).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from empiricist.ledger.db import Ledger
from empiricist.store import Store

ENV_CLAIMS_REPO = "EMPIRICIST_CLAIMS_REPO"
log = logging.getLogger(__name__)


def claims_repo_from_env() -> Path | None:
    value = os.environ.get(ENV_CLAIMS_REPO, "").strip()
    return Path(value) if value else None


def materialize_after_ingest(
    ledger: Ledger, store: Store, artifact_id: str, *, claims_repo: Path | str | None = None
):
    """Project one just-recorded artifact into the configured claims repository.
    Returns the ImportReport, or None when no repository is configured."""
    from empiricist.claims.importer import materialize_artifacts

    repo = Path(claims_repo) if claims_repo is not None else claims_repo_from_env()
    if repo is None:
        return None
    try:
        report = materialize_artifacts(ledger, store, repo, artifact_ids=[artifact_id])
    except Exception:  # noqa: BLE001 - the ledger row is already committed; never lose it
        log.exception("claims: could not materialize artifact %s into %s", artifact_id, repo)
        return None
    for skip in report.skipped:
        log.info("claims: %s", skip)
    return report

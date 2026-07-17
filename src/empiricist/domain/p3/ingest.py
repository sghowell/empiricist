"""Ledger ingestion for verified P3 Bell-measurement schemes (M20a Task 2).

The P5 convention, carried over verbatim (`verifiers/p3_scheme.py`'s own
docstring: "verifiers write nothing" -- `P3SchemeVerifier.verify()` is pure
in-process Python with no ledger writes): an ingestion helper, not the
verifier, owns the `EvidenceRow`. `ingest_scheme_artifact` is that helper for
P3 -- it takes an already-produced `domain.p3.verify.AgreedResult` (from
`verify_scheme_agreed`, the same two-engine contract `P3SchemeVerifier` wraps)
and records both the CAS/ledger artifact and the evidence row that justifies
it in one call.

**Why a PASS enters directly at VERIFIED_N, not HEURISTIC-then-promoted.**
Unlike `search/loop.py`'s exact-upgrade path (which ingests at HEURISTIC and
defers the dataset row's own status change to the M7 orchestrator), a PASS
from `verify_scheme_agreed` already IS two-engine machine agreement that
every claim the scheme makes is achieved -- there is no further
orchestrator-level promotion step for a standalone P3 construction. Two-engine
agreement is the machine evidence spec's status lattice asks for at
`VERIFIED_N` ("exactly machine-checked"), so the artifact is created at
`VERIFIED_N` directly (the same "datasets legitimately enter at VERIFIED_N"
exception `ledger.add_artifact`'s docstring documents) and the evidence row
is recorded in the same call, co-locating the transition with the evidence
that earned it.

**Canonicalization IS the dedup identity.** The artifact's CAS content is
`json.dumps(scheme_json, sort_keys=True, separators=(",", ":")).encode()` --
the canonical JSON of the caller's raw scheme dict (the same dict that was
screened by `search.p3_screen.screen_scheme` into the `BellScheme` that was
actually verified). Two calls with the same scheme, even key-order-shuffled,
collapse to the SAME blake3 digest and hence the SAME artifact id (spec §4.2
rule 1: id == content hash -- no override here, unlike
`search.conjecture.submit`'s semantic-hash exception): re-ingesting an
already-known scheme across search rounds is free and never mints a second
artifact.

**Duplicate handling** mirrors `search.conjecture.submit` exactly: look up
the pre-computed content digest via `ledger.get_artifact` first (short-circuit
return of the existing artifact, no new evidence row -- re-deriving the same
scheme is not new evidence about it); catch `sqlite3.IntegrityError` as
belt-and-braces against a concurrent insert racing between that existence
check and the ingest.
"""

from __future__ import annotations

import json
import sqlite3

from blake3 import blake3

from empiricist.domain.p3.verify import AgreedResult
from empiricist.ledger.db import Ledger
from empiricist.ledger.ingest import ingest_artifact
from empiricist.ledger.models import Artifact, EvidenceRow, Status, Verdict
from empiricist.store import Store
from empiricist.verifiers.p3_scheme import P3SchemeVerifier


def _canonical_scheme_json(scheme_json: dict) -> bytes:
    """Canonical CAS content for `scheme_json` -- sorted-key, separator-tight
    JSON, so dict insertion order never perturbs the digest (same convention
    as `search.conjecture._canonical_conjecture_json`). Raises `ValueError`
    (not a raw `TypeError`) on anything `json.dumps` cannot serialize: a
    caller error, not a schema violation the screen would have caught."""
    try:
        return json.dumps(
            scheme_json, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    except TypeError as exc:
        raise ValueError(f"scheme_json is not JSON-serializable: {exc}") from exc


def ingest_scheme_artifact(
    ledger: Ledger,
    store: Store,
    *,
    scheme_json: dict,
    result: AgreedResult,
    title: str,
    run_id: str | None = None,
) -> Artifact:
    """Ingest a PASS-verified P3 scheme as a `construction` artifact at
    `VERIFIED_N`, with the `EvidenceRow` that justifies it.

    Refuses (`ValueError`) unless `result.verdict == "PASS"` -- a FAIL/ERROR/
    INVALID result is never recorded above the trust boundary this helper
    exists to gate (an ERROR result in particular is the F3 stop-the-world
    alarm; a caller must never route it here). `scheme_json` must be
    JSON-serializable; see `_canonical_scheme_json`.

    Idempotent: a second call with the same canonical `scheme_json` returns
    the FIRST-ingested artifact (its original `title`) and records no second
    evidence row.
    """
    if result.verdict != "PASS":
        raise ValueError(
            f"refusing to ingest a non-PASS scheme (verdict={result.verdict!r}): "
            f"{result.detail}"
        )

    content = _canonical_scheme_json(scheme_json)
    art_id = blake3(content).hexdigest()
    try:
        return ledger.get_artifact(art_id)  # duplicate: short-circuit, no new evidence
    except KeyError:
        pass

    try:
        art = ingest_artifact(
            ledger, store, content=content, kind="construction", problem="P3",
            title=title, status=Status.VERIFIED_N, run_id=run_id,
        )
    except sqlite3.IntegrityError:
        # Raced with another insert of the same canonical scheme.
        return ledger.get_artifact(art_id)

    verifier = P3SchemeVerifier()
    report = result.report
    ledger.record_evidence(
        EvidenceRow(
            artifact_id=art.id,
            verifier=verifier.name,
            verifier_version=verifier.version,
            binary_hash=verifier.binary_hash,
            verdict=Verdict.PASS,
            details={
                "success_by_state": dict(report.success_by_state),
                "p_min": report.p_min,
                "p_avg": report.p_avg,
                "leakage": result.leakage,
                "detail": result.detail,
            },
        ),
        new_status=Status.VERIFIED_N,
    )
    return art

"""Re-verify CERTIFIED certificate artifacts under the live checker identities.

The certificate counterpart of `verifiers/reverify.py`: for every `certificate`
artifact at CERTIFIED, re-run the checker its evidence names (`sos_certificate` or
`p3_exact_witness`) on the stored payload and record a claim-bound PASS row pinned to
the live identity and golden suite through the same certification-gated ingest the
original promotion used. A non-PASS is recorded as evidence only (never a demotion).
"""
from __future__ import annotations

import json
from collections.abc import Iterable

from empiricist.certificates.goldens import certify_sos, sos_suite_hash
from empiricist.certificates.ingest import verify_and_ingest_p3_certificate
from empiricist.certificates.verifier import SOSCertificateVerifier
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import EvidenceRow, Status, Verdict
from empiricist.store import Store
from empiricist.verifiers.p3_exact import P3ExactVerifier
from empiricist.verifiers.p3_exact_goldens import certify_p3_exact, p3_exact_suite_hash
from empiricist.verifiers.reverify import ReverifyOutcome, ReverifyReport

_SOS = SOSCertificateVerifier.name
_EXACT = P3ExactVerifier.name


def _checker_for(ledger: Ledger, artifact_id: str) -> str | None:
    """The checker that certified this artifact: the verifier of its latest PASS row."""
    for row in reversed(ledger.evidence_for(artifact_id)):
        if row.verdict is Verdict.PASS and row.verifier in (_SOS, _EXACT):
            return row.verifier
    return None


def _targets(ledger: Ledger, artifact_ids: Iterable[str] | None):
    wanted = None if artifact_ids is None else list(dict.fromkeys(artifact_ids))
    found = [
        a
        for a in ledger.find_artifacts(kind="certificate", status=Status.CERTIFIED)
        if wanted is None or a.id in wanted
    ]
    missing = [] if wanted is None else [i for i in wanted if i not in {a.id for a in found}]
    return found, missing


def _ensure_certified(ledger: Ledger, name: str) -> bool:
    """Stamp the live checker `name` against its golden suite unless already current.
    Returns True iff a new stamp was issued; raises when the live checker fails its suite."""
    if name == _SOS:
        v, suite, certify = SOSCertificateVerifier(), sos_suite_hash(), certify_sos
    else:
        v, suite, certify = P3ExactVerifier(), p3_exact_suite_hash(), certify_p3_exact
    cert = ledger.get_certification(v.name, v.version, v.binary_hash)
    if cert is not None and cert.verdict is Verdict.PASS and cert.golden_suite_hash == suite:
        return False
    stamp = certify(ledger, v)
    if stamp.verdict is not Verdict.PASS:
        raise RuntimeError(
            f"the live {name} checker FAILED its golden suite; refusing to re-verify "
            "anything against an uncertified gate"
        )
    return True


def _rerun(ledger: Ledger, store: Store, art, checker: str) -> ReverifyOutcome:
    payload = json.loads(store.get(art.content_path).decode("utf-8"))
    if checker == _SOS:
        claims = ledger.claims_for(art.id)
        if not claims or "target" not in claims[-1].scope:
            return ReverifyOutcome(
                art.id, art.title, "SKIPPED", "no canonical claim names the target"
            )
        v = SOSCertificateVerifier()
        suite = sos_suite_hash()
        result, stored = verify_and_ingest_p3_certificate(
            ledger, store, certificate_json=payload, target=claims[-1].scope["target"],
            title=art.title,
        )
    else:
        from empiricist.domain.p3.exact_ingest import verify_and_ingest_exact_witness

        v = P3ExactVerifier()
        suite = p3_exact_suite_hash()
        result, stored = verify_and_ingest_exact_witness(
            ledger, store, witness_json=payload["witness"],
            claimed_success=payload["claimed_success"],
            require_all_identified=bool(payload.get("require_all_identified", False)),
            title=art.title,
        )
    if stored is not None:
        return ReverifyOutcome(art.id, art.title, "PASS", "re-verified")
    ledger.record_evidence(
        EvidenceRow(
            artifact_id=art.id, verifier=v.name, verifier_version=v.version,
            binary_hash=v.binary_hash, golden_suite_hash=suite, verdict=result.verdict,
            details={"reverify": True, **result.details},
        )
    )
    detail = result.details.get("failure") or result.details.get("detail") or ""
    return ReverifyOutcome(art.id, art.title, result.verdict.value, str(detail))


def reverify_certificate_artifacts(
    ledger: Ledger,
    store: Store,
    *,
    artifact_ids: Iterable[str] | None = None,
    dry_run: bool = False,
    certify: bool = True,
) -> ReverifyReport:
    """Re-run the live checker over every CERTIFIED certificate artifact (optionally
    restricted to `artifact_ids`). See the module docstring for the recording rules."""
    targets, missing = _targets(ledger, artifact_ids)
    missing_outcomes = [
        ReverifyOutcome(i, "", "MISSING", "no CERTIFIED certificate artifact with this id")
        for i in missing
    ]
    if dry_run:
        return ReverifyReport(
            outcomes=tuple(
                [ReverifyOutcome(a.id, a.title, "SKIPPED", "dry run") for a in targets]
                + missing_outcomes
            ),
            certified_now=False, dry_run=True,
        )
    checkers = {a.id: _checker_for(ledger, a.id) for a in targets}
    certified_now = False
    if certify:
        for name in sorted({c for c in checkers.values() if c}):
            certified_now = _ensure_certified(ledger, name) or certified_now
    outcomes: list[ReverifyOutcome] = []
    for art in targets:
        checker = checkers[art.id]
        if checker is None:
            outcomes.append(ReverifyOutcome(
                art.id, art.title, "SKIPPED", "no PASS evidence from a known certificate checker"
            ))
            continue
        try:
            outcomes.append(_rerun(ledger, store, art, checker))
        except Exception as exc:  # noqa: BLE001 - one bad artifact must not abort the pass
            outcomes.append(ReverifyOutcome(
                art.id, art.title, "ERROR", f"{type(exc).__name__}: {exc}"
            ))
    return ReverifyReport(tuple(outcomes + missing_outcomes), certified_now, False)

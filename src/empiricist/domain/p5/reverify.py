"""Re-verify P5 construction witnesses under the live engines; promote exact ones.

The construction counterpart of the Lean and certificate passes: for every
`construction` artifact whose evidence is a `verify_agreed` PASS flagged as an exact
upgrade, rebuild the witness from its CAS JSON, re-run both certified engines through
the (certified) agreement logic, and on a PASS that meets the recorded target's lower
bound record it at CERTIFIED with its canonical claim row through the same
certification-gated path the search loop now uses (M23b). July's eight closures were
recorded HEURISTIC under the v0 lattice; this pass is how they become claims.
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from empiricist.ledger.db import Ledger
from empiricist.ledger.models import EvidenceRow, Status, Verdict
from empiricist.search.loop import TargetSpec, record_exact_value
from empiricist.search.schemas import ConstructionOut, ScreenReject, to_construction
from empiricist.store import Store
from empiricist.verifiers.enum_fusion import EnumFusionVerifier
from empiricist.verifiers.goldens import suite_hash
from empiricist.verifiers.registry import (
    AGREED_NAME,
    AGREED_VERSION,
    Registry,
    agreed_binary_hash,
    agreed_is_certified,
    certify_agreed,
    verify_agreed,
)
from empiricist.verifiers.reverify import ReverifyOutcome, ReverifyReport
from empiricist.verifiers.stab_fusion import StabFusionVerifier


def _upgrade_row(ledger: Ledger, artifact_id: str) -> EvidenceRow | None:
    for row in reversed(ledger.evidence_for(artifact_id)):
        if (
            row.verifier == AGREED_NAME
            and row.verdict is Verdict.PASS
            and row.details.get("upgrade") is True
            and isinstance(row.details.get("target"), dict)
        ):
            return row
    return None


def _targets(ledger: Ledger, artifact_ids: Iterable[str] | None):
    wanted = None if artifact_ids is None else list(dict.fromkeys(artifact_ids))
    found = [
        a
        for a in ledger.find_artifacts(kind="construction")
        if a.status in (Status.HEURISTIC, Status.CERTIFIED)
        and (wanted is None or a.id in wanted)
        and _upgrade_row(ledger, a.id) is not None
    ]
    missing = [] if wanted is None else [i for i in wanted if i not in {a.id for a in found}]
    return found, missing


def ensure_engines_certified(ledger: Ledger) -> bool:
    """Stamp both fusion engines and the agreement logic against the live P5 suite
    unless already current. Returns True iff any stamp was issued."""
    registry = Registry(ledger)
    issued = False
    for verifier in (StabFusionVerifier(), EnumFusionVerifier()):
        cert = ledger.get_certification(verifier.name, verifier.version, verifier.binary_hash)
        stale = cert is None or cert.verdict is not Verdict.PASS
        if stale or cert.golden_suite_hash != suite_hash():
            registry.certify(verifier)
            issued = True
    if not agreed_is_certified(ledger):
        certify_agreed(ledger)
        issued = True
    return issued


def _target_from(details: dict) -> TargetSpec:
    t = dict(details["target"])
    t["representative_edges"] = tuple(tuple(e) for e in t.get("representative_edges", ()))
    return TargetSpec(**t)


def _reverify_one(
    ledger: Ledger, store: Store, art, claims_repo: Path | None
) -> ReverifyOutcome:
    row = _upgrade_row(ledger, art.id)
    assert row is not None
    try:
        out = ConstructionOut.model_validate(json.loads(store.get(art.content_path)))
        construction = to_construction(out)
    except (ValueError, ScreenReject) as exc:
        return ReverifyOutcome(
            art.id, art.title, "SKIPPED", f"witness does not parse: {exc}"
        )
    target = _target_from(row.details)
    registry = Registry(ledger)
    result = verify_agreed(registry, construction)
    f = construction.fusion_count
    achieved = result.details.get("stab_fusion_key")
    if result.verdict is Verdict.PASS and achieved != target.lc_orbit_key:
        result = result.__class__(
            verdict=Verdict.FAIL,
            details={
                **result.details,
                "failure": "witness reaches a different orbit than recorded",
            },
        )
    if result.verdict is Verdict.PASS and f == target.target_f:
        details = {
            "achieved_key": result.details["stab_fusion_key"],
            "f": f,
            "target": row.details["target"],
            "upgrade": True,
            "reverify": True,
            "stab_fusion_id": result.details["stab_fusion_id"],
            "enum_fusion_id": result.details["enum_fusion_id"],
        }
        was = art.status
        record_exact_value(
            ledger, store, art.id, target=target, f=f, details=details, claims_repo=claims_repo
        )
        detail = "promoted to CERTIFIED" if was is Status.HEURISTIC else "re-verified"
        return ReverifyOutcome(art.id, art.title, "PASS", detail)
    ledger.record_evidence(
        EvidenceRow(
            artifact_id=art.id, verifier=AGREED_NAME, verifier_version=AGREED_VERSION,
            binary_hash=agreed_binary_hash(), golden_suite_hash=suite_hash(),
            verdict=result.verdict, details={"reverify": True, "f": f, **result.details},
        )
    )
    if result.verdict is Verdict.PASS:
        return ReverifyOutcome(
            art.id, art.title, "PASS",
            f"witness at F={f} is above the lower bound {target.target_f}; "
            f"stays {art.status.value}",
        )
    detail = result.details.get("failure") or result.details.get("error") or ""
    return ReverifyOutcome(art.id, art.title, result.verdict.value, str(detail))


def reverify_construction_artifacts(
    ledger: Ledger,
    store: Store,
    *,
    artifact_ids: Iterable[str] | None = None,
    dry_run: bool = False,
    certify: bool = True,
    claims_repo: Path | None = None,
) -> ReverifyReport:
    """Re-run the certified engines over every exact-upgrade construction witness
    (optionally restricted to `artifact_ids`). See the module docstring."""
    targets, missing = _targets(ledger, artifact_ids)
    missing_outcomes = [
        ReverifyOutcome(i, "", "MISSING", "no exact-upgrade construction artifact with this id")
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
    certified_now = ensure_engines_certified(ledger) if (certify and targets) else False
    outcomes: list[ReverifyOutcome] = []
    for art in targets:
        if art.id != art.content_path:
            outcomes.append(ReverifyOutcome(
                art.id, art.title, "SKIPPED", "artifact id is not its content digest"
            ))
            continue
        try:
            outcomes.append(_reverify_one(ledger, store, art, claims_repo))
        except Exception as exc:  # noqa: BLE001 - one bad artifact must not abort the pass
            outcomes.append(ReverifyOutcome(
                art.id, art.title, "ERROR", f"{type(exc).__name__}: {exc}"
            ))
    return ReverifyReport(tuple(outcomes + missing_outcomes), certified_now, False)

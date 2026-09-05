"""Re-verify FORMALIZED Lean artifacts under the CURRENT gate.

Why this exists: artifacts recorded before golden-suite-hash tracking carry PASS
evidence the audit cannot cross-check against a certification
(`elevated_missing_certified_evidence`). The only honest way to clear that flag
is to run today's certified `LeanVerifier` over the exact stored source and
record a claim-bound evidence row through the certification-gated transaction
(`_record_verified_lean_artifact` -> `record_claimed_artifact`, the same path
`ingest_lean_artifact` uses). A non-PASS is recorded as evidence WITHOUT a status
change: the lattice never reduces rank, and REFUTED (terminal) would assert the
theorem is false, which a gate change does not show. The audit keeps flagging
such rows -- that is the correct outcome, not a bug.

`verifiers/lean.py` is deliberately left untouched (its source is part of the
LeanVerifier identity hash); this module only orchestrates it.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from empiricist.ledger.db import Ledger
from empiricist.ledger.models import EvidenceRow, Status, Verdict
from empiricist.store import Store
from empiricist.verifiers.lean import (
    DEFAULT_LEAN_PROBLEM_VERSION,
    LeanVerifier,
    _record_verified_lean_artifact,
)
from empiricist.verifiers.lean_goldens import certify_lean, lean_suite_hash

# Pre-migration artifacts carry this placeholder version (ledger/migrations.py);
# a re-verified claim gets the verifier's real default instead.
_LEGACY_PROBLEM_VERSION = "legacy"


@dataclass(frozen=True)
class ReverifyOutcome:
    artifact_id: str
    decl: str
    verdict: str  # "PASS" | "FAIL" | "ERROR" | "TIMEOUT" | "SKIPPED"
    detail: str


@dataclass(frozen=True)
class ReverifyReport:
    outcomes: tuple[ReverifyOutcome, ...]
    certified_now: bool  # True iff this pass issued a new certification stamp
    dry_run: bool

    @property
    def ok(self) -> bool:
        """Every target passed the current gate (a dry run is never `ok`)."""
        return (not self.dry_run) and all(o.verdict == "PASS" for o in self.outcomes)


def _targets(ledger: Ledger, artifact_ids: Iterable[str] | None):
    wanted = None if artifact_ids is None else set(artifact_ids)
    return [
        a
        for a in ledger.find_artifacts(kind="lean", status=Status.FORMALIZED)
        if wanted is None or a.id in wanted
    ]


def reverify_lean_artifacts(
    ledger: Ledger,
    store: Store,
    *,
    verifier=None,
    artifact_ids: Iterable[str] | None = None,
    dry_run: bool = False,
    certify: bool = True,
    timeout_s: float = 600.0,
) -> ReverifyReport:
    """Re-run the current Lean gate over every FORMALIZED `lean` artifact.

    PASS -> a claim-bound evidence row pinned to the live golden suite (the
    artifact keeps its id, content, and status; a `legacy` problem version is
    replaced by the verifier's default, any other is kept). Non-PASS -> an
    evidence-only row (`details["reverify"] is True`) with no status change.
    `dry_run` lists the targets and touches nothing. With `certify=True` the
    current verifier is certified against the live Lean golden suite first if
    its stamp is missing or stale; a verifier that fails its own suite aborts
    the whole pass (nothing is recorded).
    """
    v = verifier if verifier is not None else LeanVerifier()
    suite_hash = lean_suite_hash()
    targets = _targets(ledger, artifact_ids)
    if dry_run:
        return ReverifyReport(
            outcomes=tuple(
                ReverifyOutcome(a.id, a.title, "SKIPPED", "dry run") for a in targets
            ),
            certified_now=False,
            dry_run=True,
        )
    if not targets:
        return ReverifyReport(outcomes=(), certified_now=False, dry_run=False)

    certified_now = False
    if certify:
        cert = ledger.get_certification(v.name, v.version, v.binary_hash)
        if (
            cert is None
            or cert.verdict is not Verdict.PASS
            or cert.golden_suite_hash != suite_hash
        ):
            stamp = certify_lean(ledger, v)
            certified_now = True
            if stamp.verdict is not Verdict.PASS:
                raise RuntimeError(
                    "the current LeanVerifier FAILED its golden suite; refusing to "
                    "re-verify anything against an uncertified gate"
                )
    # Fail closed (PromotionIntegrityError) before touching any artifact.
    ledger.require_certification(v.name, v.version, v.binary_hash, suite_hash)

    outcomes: list[ReverifyOutcome] = []
    for art in targets:
        source = store.get(art.content_path).decode("utf-8")
        decl = art.title
        result = v.verify(source, decl=decl, timeout_s=timeout_s)
        if result.verdict is Verdict.PASS:
            problem_version = (
                DEFAULT_LEAN_PROBLEM_VERSION
                if art.problem_version == _LEGACY_PROBLEM_VERSION
                else art.problem_version
            )
            _record_verified_lean_artifact(
                ledger,
                store,
                source,
                decl,
                result,
                verifier=v,
                suite_hash=suite_hash,
                problem=art.problem,
                problem_version=problem_version,
                run_id=None,
            )
            outcomes.append(ReverifyOutcome(art.id, decl, "PASS", "re-verified"))
            continue
        ledger.record_evidence(
            EvidenceRow(
                artifact_id=art.id,
                verifier=v.name,
                verifier_version=v.version,
                binary_hash=v.binary_hash,
                golden_suite_hash=suite_hash,
                verdict=result.verdict,
                details={"reverify": True, **result.details},
            )
        )
        gate = result.details.get("gate") or result.details.get("error") or ""
        outcomes.append(ReverifyOutcome(art.id, decl, result.verdict.value, str(gate)))
    return ReverifyReport(tuple(outcomes), certified_now, False)

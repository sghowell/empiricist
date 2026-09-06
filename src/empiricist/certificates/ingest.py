"""Certificate -> CERTIFIED ingestion (spec section 4.1: a GENERAL statement with a
model-independent, machine-checkable certificate).

Two gates, in order: (1) DOMAIN MEANING -- the certificate's objective and
constraint polynomials must EQUAL the ones `p3_targets` derives for the declared
target (the checker verifies algebra only; this is where "these constraints are
unitarity, this objective is p_avg" is pinned, so a certificate can only certify
the target it claims); (2) the certified exact checker. Only then is the
artifact/claim/evidence transaction committed at CERTIFIED, through the same
certification-gated `record_claimed_artifact` path Lean uses.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from blake3 import blake3

from empiricist.certificates.core import Poly, SOSCertificate
from empiricist.certificates.goldens import sos_suite_hash
from empiricist.certificates.p3_targets import (
    standard_assignment_objective,
    unambiguity_constraints,
    unitarity_constraints,
)
from empiricist.certificates.verifier import (
    SOSCertificateVerifier,
    certificate_from_json,
    certificate_to_json,
)
from empiricist.claims.materialize import materialize_after_ingest
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Artifact, Claim, EvidenceRow, Status, Verdict
from empiricist.store import Store
from empiricist.verifiers.base import VerifierResult

P3_CERTIFICATE_PROBLEM_VERSION = "p3-sos-certificate-v1"


@dataclass(frozen=True)
class CertificateTarget:
    """What a certificate for `name` must encode, and the claim it then supports.

    `core_constraints` define the set the claim quantifies over (for P3: the
    unitarity variety, i.e. every U in U(m)); `side_constraints` are auxiliary
    equalities a certificate MAY use (for P3: the standard assignment's
    unambiguity conditions). A certificate proves `objective <= bound` on the
    variety of ALL its constraints. So the claim recorded is `statement_universal`
    only when every side-constraint multiplier is identically zero (the identity
    then holds on the core variety alone); otherwise `statement_restricted`,
    which names the side conditions explicitly. Both are `.format(bound=...)`."""

    name: str
    n_modes: int
    k: int
    objective: Callable[[], Poly]
    core_constraints: Callable[[], list[Poly]]
    side_constraints: Callable[[], list[Poly]]
    statement_universal: str
    statement_restricted: str
    metric: str

    def constraints(self) -> list[Poly]:
        return self.core_constraints() + self.side_constraints()


_K0_OBJECTIVE_GLOSS = (
    "the standard-assignment objective -- the total probability that the textbook "
    "Bell-analyser detection patterns land on their assigned Bell states, an upper "
    "bound on the unambiguous average success p_avg of that assignment --"
)

P3_CERTIFICATE_TARGETS: dict[str, CertificateTarget] = {
    "k0_standard_assignment_p_avg": CertificateTarget(
        name="k0_standard_assignment_p_avg",
        n_modes=4,
        k=0,
        objective=lambda: standard_assignment_objective(4),
        core_constraints=lambda: unitarity_constraints(4),
        side_constraints=lambda: unambiguity_constraints(4),
        statement_universal=(
            "For every passive interferometer U in U(4) acting on the ancilla-free "
            f"dual-rail Bell pair, {_K0_OBJECTIVE_GLOSS} is at most {{bound}} (exact "
            "SOS certificate on the unitarity variety; no unambiguity side constraint "
            "is used)."
        ),
        statement_restricted=(
            "For every passive interferometer U in U(4) acting on the ancilla-free "
            "dual-rail Bell pair AT WHICH the standard assignment is unambiguous "
            f"(Pr[S|B'] = 0 for every assigned pattern S and B' != f(S)), {_K0_OBJECTIVE_GLOSS} "
            "is at most {bound} (exact SOS certificate on the unitarity + unambiguity "
            "variety)."
        ),
        metric="p_avg_upper_bound",
    ),
}


def _canonical_json(data: dict) -> bytes:
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _check_target(cert: SOSCertificate, target: str) -> CertificateTarget:
    spec = P3_CERTIFICATE_TARGETS.get(target)
    if spec is None:
        raise ValueError(f"certificate does not encode a known target: {target!r}")
    if cert.objective != spec.objective() or list(cert.constraints) != spec.constraints():
        raise ValueError(
            f"certificate does not encode the declared target {target!r}: its objective "
            "or constraint polynomials differ from p3_targets' definitions"
        )
    return spec


def uses_side_constraints(cert: SOSCertificate, spec: CertificateTarget) -> bool:
    """True iff some multiplier on a SIDE constraint is a non-zero polynomial."""
    n_core = len(spec.core_constraints())
    return any(bool(m) for m in cert.multipliers[n_core:])


def verify_and_ingest_p3_certificate(
    ledger: Ledger,
    store: Store,
    *,
    certificate_json: dict,
    target: str,
    title: str,
    run_id: str | None = None,
    claims_repo: Path | None = None,
) -> tuple[VerifierResult, Artifact | None]:
    """Return the checker's result and ingest at CERTIFIED only on a certified PASS.

    Raises ValueError for a malformed certificate or one whose polynomials do
    not encode `target`; raises PromotionIntegrityError when the checker lacks
    a current certification stamp (fail closed, before any verification).
    """
    cert = certificate_from_json(certificate_json)
    spec = _check_target(cert, target)
    verifier = SOSCertificateVerifier()
    suite_hash = sos_suite_hash()
    ledger.require_certification(
        verifier.name, verifier.version, verifier.binary_hash, suite_hash
    )
    result = verifier.verify(cert)
    if result.verdict is not Verdict.PASS:
        return result, None
    # Hash the PARSED certificate's canonical form, not the caller's dict: keys the
    # parser ignores must not mint distinct artifacts for the same certificate.
    content = _canonical_json(certificate_to_json(cert))
    digest = store.put(content)
    restricted = uses_side_constraints(cert, spec)
    statement_template = spec.statement_restricted if restricted else spec.statement_universal
    evidence_run_id = run_id
    if evidence_run_id is not None:
        try:
            ledger.get_run(evidence_run_id)
        except KeyError:
            evidence_run_id = None
    art = Artifact(
        id=blake3(content).hexdigest(),
        kind="certificate",
        problem="P3",
        problem_version=P3_CERTIFICATE_PROBLEM_VERSION,
        title=title,
        content_path=digest,
        status=Status.CERTIFIED,
        run_id=evidence_run_id,
    )
    bound = str(cert.bound)
    claim = Claim.create(
        artifact_id=art.id,
        problem=art.problem,
        problem_version=art.problem_version,
        statement=statement_template.format(bound=bound),
        family=spec.name,
        metric=spec.metric,
        scope={
            "target": spec.name,
            "bound": bound,
            "n_modes": spec.n_modes,
            "k": spec.k,
            "uses_side_constraints": restricted,
        },
    )
    evidence = EvidenceRow(
        artifact_id=art.id,
        claim_id=claim.id,
        run_id=evidence_run_id,
        verifier=verifier.name,
        verifier_version=verifier.version,
        binary_hash=verifier.binary_hash,
        golden_suite_hash=suite_hash,
        verdict=Verdict.PASS,
        details={**result.details, "target": spec.name, "uses_side_constraints": restricted},
    )
    stored = ledger.record_claimed_artifact(
        art, claim, evidence, expected_golden_suite_hash=suite_hash
    )
    materialize_after_ingest(ledger, store, stored.id, claims_repo=claims_repo)
    return result, stored


def ingest_p3_certificate(
    ledger: Ledger,
    store: Store,
    *,
    certificate_json: dict,
    target: str,
    title: str,
    run_id: str | None = None,
    claims_repo: Path | None = None,
) -> Artifact:
    """`verify_and_ingest_p3_certificate` that refuses (ValueError) on non-PASS."""
    result, art = verify_and_ingest_p3_certificate(
        ledger,
        store,
        certificate_json=certificate_json,
        target=target,
        title=title,
        run_id=run_id,
        claims_repo=claims_repo,
    )
    if art is None:
        raise ValueError(
            "refusing to ingest a non-PASS certificate "
            f"({result.details.get('failure')}: {result.details.get('detail')})"
        )
    return art

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

from blake3 import blake3

from empiricist.certificates.core import Poly, SOSCertificate
from empiricist.certificates.goldens import sos_suite_hash
from empiricist.certificates.p3_targets import (
    standard_assignment_objective,
    unambiguity_constraints,
    unitarity_constraints,
)
from empiricist.certificates.verifier import SOSCertificateVerifier, certificate_from_json
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Artifact, Claim, EvidenceRow, Status, Verdict
from empiricist.store import Store
from empiricist.verifiers.base import VerifierResult

P3_CERTIFICATE_PROBLEM_VERSION = "p3-sos-certificate-v1"


@dataclass(frozen=True)
class CertificateTarget:
    """What a certificate for `name` must encode, and the claim it then supports."""

    name: str
    n_modes: int
    k: int
    objective: Callable[[], Poly]
    constraints: Callable[[], list[Poly]]
    statement: str  # `.format(bound=<rational string>)`
    metric: str


P3_CERTIFICATE_TARGETS: dict[str, CertificateTarget] = {
    "k0_standard_assignment_p_avg": CertificateTarget(
        name="k0_standard_assignment_p_avg",
        n_modes=4,
        k=0,
        objective=lambda: standard_assignment_objective(4),
        constraints=lambda: unitarity_constraints(4) + unambiguity_constraints(4),
        statement=(
            "For every passive interferometer U in U(4) acting on the ancilla-free "
            "dual-rail Bell pair, the standard-assignment average Bell-identification "
            "probability p_avg is at most {bound} (exact SOS certificate on the "
            "unitarity variety)."
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


def verify_and_ingest_p3_certificate(
    ledger: Ledger,
    store: Store,
    *,
    certificate_json: dict,
    target: str,
    title: str,
    run_id: str | None = None,
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
    content = _canonical_json(certificate_json)
    digest = store.put(content)
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
        statement=spec.statement.format(bound=bound),
        family=spec.name,
        metric=spec.metric,
        scope={"target": spec.name, "bound": bound, "n_modes": spec.n_modes, "k": spec.k},
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
        details={**result.details, "target": spec.name},
    )
    stored = ledger.record_claimed_artifact(
        art, claim, evidence, expected_golden_suite_hash=suite_hash
    )
    return result, stored


def ingest_p3_certificate(
    ledger: Ledger,
    store: Store,
    *,
    certificate_json: dict,
    target: str,
    title: str,
    run_id: str | None = None,
) -> Artifact:
    """`verify_and_ingest_p3_certificate` that refuses (ValueError) on non-PASS."""
    result, art = verify_and_ingest_p3_certificate(
        ledger,
        store,
        certificate_json=certificate_json,
        target=target,
        title=title,
        run_id=run_id,
    )
    if art is None:
        raise ValueError(
            "refusing to ingest a non-PASS certificate "
            f"({result.details.get('failure')}: {result.details.get('detail')})"
        )
    return art

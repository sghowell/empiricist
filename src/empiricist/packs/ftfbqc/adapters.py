"""v1 evidence adapters over the ftfbqc (P3/P5) verifiers.

Each adapter turns the bytes of a committed evidence file into the call the v0 verifier
already knows how to judge, and reports the v0 verifier's identity (name, version,
binary_hash) as its own: the serialisation shim is exercised by the golden suite, and the
trust identity stays the engine's, so evidence rows produced through the v0 ledger and
through these adapters compare equal in a repository's registry.
"""
from __future__ import annotations

import json
from pathlib import Path

from empiricist.ledger.models import Verdict
from empiricist.packs import BytesFileVerifier, GoldenCase
from empiricist.verifiers.base import VerifierResult


def _canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _malformed(exc: BaseException) -> VerifierResult:
    return VerifierResult(
        verdict=Verdict.FAIL, details={"invalid": True, "detail": f"malformed: {exc}"}
    )


class SOSCertificateAdapter(BytesFileVerifier):
    """Payload: the canonical SOS certificate JSON (`certificate_to_json`)."""

    def __init__(self, repo: Path) -> None:
        from empiricist.certificates.verifier import SOSCertificateVerifier

        super().__init__(repo)
        self._v = SOSCertificateVerifier()

    name = "sos_certificate"

    @property
    def version(self) -> str:
        return self._v.version

    @property
    def binary_hash(self) -> str:
        return self._v.binary_hash

    def verify_bytes(self, payload: bytes) -> VerifierResult:
        from empiricist.certificates.verifier import certificate_from_json

        try:
            cert = certificate_from_json(json.loads(payload))
        except (ValueError, KeyError, TypeError) as exc:
            return _malformed(exc)
        return self._v.verify(cert)

    def golden_suite(self) -> list[GoldenCase]:
        from empiricist.certificates.goldens import SOS_GOLDEN_SUITE
        from empiricist.certificates.verifier import certificate_to_json

        return [
            GoldenCase(f"sos-{i}", _canonical(certificate_to_json(c)), v)
            for i, (c, v) in enumerate(SOS_GOLDEN_SUITE)
        ]


class ExactWitnessAdapter(BytesFileVerifier):
    """Payload: `{"witness", "claimed_success": {bell: alg json}, "require_all_identified"}`
    -- the stored form of a P3 exact-witness artifact."""

    def __init__(self, repo: Path) -> None:
        from empiricist.verifiers.p3_exact import P3ExactVerifier

        super().__init__(repo)
        self._v = P3ExactVerifier()

    name = "p3_exact_witness"

    @property
    def version(self) -> str:
        return self._v.version

    @property
    def binary_hash(self) -> str:
        return self._v.binary_hash

    def verify_bytes(self, payload: bytes) -> VerifierResult:
        from empiricist.domain.p3.exact import alg_from_json

        try:
            data = json.loads(payload)
            claimed = {b: alg_from_json(q) for b, q in data["claimed_success"].items()}
            witness = data["witness"]
            require_all = bool(data.get("require_all_identified", False))
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            return _malformed(exc)
        return self._v.verify(
            witness, claimed_success=claimed, require_all_identified=require_all
        )

    def golden_suite(self) -> list[GoldenCase]:
        from empiricist.verifiers.p3_exact_goldens import P3_EXACT_GOLDEN_SUITE, _canon_claim

        return [
            GoldenCase(f"exact-{i}", _canonical({"witness": w, **_canon_claim(claim)}), v)
            for i, (w, claim, v) in enumerate(P3_EXACT_GOLDEN_SUITE)
        ]


def _construction_json(construction) -> dict:
    from empiricist.domain.p5.construction import LocalComplement

    steps = []
    for s in construction.steps:
        if isinstance(s, LocalComplement):
            steps.append({"op": "lc", "args": [s.v]})
        else:
            steps.append({"op": "fuse", "args": [s.a, s.b]})
    return {
        "resources": construction.resources,
        "steps": steps,
        "target_n": construction.target.n,
        "target_edges": [list(e) for e in sorted(tuple(e) for e in construction.target.edges)],
    }


class _FusionAdapter(BytesFileVerifier):
    """Payload: a `ConstructionOut` JSON (the search loop's own witness form)."""

    def _parse(self, payload: bytes):
        from empiricist.search.schemas import ConstructionOut, ScreenReject, to_construction

        try:
            return to_construction(ConstructionOut.model_validate(json.loads(payload)))
        except (ValueError, ScreenReject) as exc:
            raise ValueError(f"malformed construction: {exc}") from exc

    def golden_suite(self) -> list[GoldenCase]:
        from empiricist.verifiers.goldens import P5_GOLDEN_SUITE

        return [
            GoldenCase(f"fusion-{i}", _canonical(_construction_json(c)), v)
            for i, (c, v) in enumerate(P5_GOLDEN_SUITE)
        ]


class StabFusionAdapter(_FusionAdapter):
    name = "stab_fusion"

    def __init__(self, repo: Path) -> None:
        from empiricist.verifiers.stab_fusion import StabFusionVerifier

        super().__init__(repo)
        self._v = StabFusionVerifier()

    @property
    def version(self) -> str:
        return self._v.version

    @property
    def binary_hash(self) -> str:
        return self._v.binary_hash

    def verify_bytes(self, payload: bytes) -> VerifierResult:
        try:
            c = self._parse(payload)
        except ValueError as exc:
            return _malformed(exc)
        return self._v.verify(c)


class EnumFusionAdapter(_FusionAdapter):
    name = "enum_fusion"

    def __init__(self, repo: Path) -> None:
        from empiricist.verifiers.enum_fusion import EnumFusionVerifier

        super().__init__(repo)
        self._v = EnumFusionVerifier()

    @property
    def version(self) -> str:
        return self._v.version

    @property
    def binary_hash(self) -> str:
        return self._v.binary_hash

    def verify_bytes(self, payload: bytes) -> VerifierResult:
        try:
            c = self._parse(payload)
        except ValueError as exc:
            return _malformed(exc)
        return self._v.verify(c)


class AgreedFusionAdapter(_FusionAdapter):
    """Both engines, run directly (no ledger gating here: in a research repository the
    registry stamp is the gate), PASS iff both PASS with the same LC-orbit key; a
    disagreement is an ERROR (a machinery fault), never a verdict about the witness."""

    name = "verify_agreed"

    @property
    def version(self) -> str:
        from empiricist.verifiers.registry import AGREED_VERSION

        return AGREED_VERSION

    @property
    def binary_hash(self) -> str:
        from empiricist.verifiers.registry import agreed_binary_hash

        return agreed_binary_hash()

    def verify_bytes(self, payload: bytes) -> VerifierResult:
        from empiricist.verifiers.enum_fusion import EnumFusionVerifier
        from empiricist.verifiers.stab_fusion import StabFusionVerifier

        try:
            c = self._parse(payload)
        except ValueError as exc:
            return _malformed(exc)
        stab, enum_v = StabFusionVerifier().verify(c), EnumFusionVerifier().verify(c)
        details = {
            "stab_fusion_key": stab.details.get("lc_orbit_key"),
            "enum_fusion_key": enum_v.details.get("lc_orbit_key"),
            "stab_fusion_verdict": stab.verdict.value,
            "enum_fusion_verdict": enum_v.verdict.value,
        }
        if stab.verdict is Verdict.ERROR or enum_v.verdict is Verdict.ERROR:
            details["error"] = stab.details.get("error") or enum_v.details.get("error")
            return VerifierResult(verdict=Verdict.ERROR, details=details)
        if stab.verdict is not enum_v.verdict or (
            details["stab_fusion_key"] != details["enum_fusion_key"]
        ):
            details["disagreement"] = True
            details["error"] = "the two certified engines disagree"
            return VerifierResult(verdict=Verdict.ERROR, details=details)
        return VerifierResult(verdict=stab.verdict, details=details)

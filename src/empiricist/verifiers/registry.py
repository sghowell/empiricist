"""Certification-stamp-gated verifier dispatch (spec §7): a verifier's
verify() may run against real work ONLY after it has been certified -- i.e.
it has produced exactly the expected PASS/FAIL outcome on every case in the
live P5 golden suite (verifiers/goldens.py) -- and only for as long as its
(name, version, binary_hash) triple's stamp remains valid against that SAME
suite. This is the ledger-enforced trust boundary between "an engine that
looks like it implements the physics" and "an engine we're licensed to trust
the verdicts of".
"""

from __future__ import annotations

from empiricist.domain.p5.construction import Construction
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Certification, Verdict
from empiricist.verifiers.base import Verifier, VerifierResult
from empiricist.verifiers.enum_fusion import EnumFusionVerifier
from empiricist.verifiers.goldens import P5_GOLDEN_SUITE, suite_hash
from empiricist.verifiers.stab_fusion import StabFusionVerifier


class UncertifiedVerifierError(Exception):
    """Raised by Registry.verify() when the verifier lacks a current PASS
    certification stamp against the live golden suite (spec §7)."""


class Registry:
    """Wraps a `Ledger`: certifies verifiers against the P5 golden suite and
    gates `verify()` calls on a current, matching certification stamp."""

    def __init__(self, ledger: Ledger) -> None:
        self._ledger = ledger

    def certify(self, verifier: Verifier) -> Certification:
        """Run every case in P5_GOLDEN_SUITE through `verifier.verify()`.
        Stamp PASS iff EVERY case's outcome (verdict == PASS) matches its
        expected outcome exactly -- a verifier that can't correctly FAIL the
        wrong-target golden is exactly as untrustworthy as one that can't
        PASS the right ones. Writes the stamp to the ledger and returns it.
        """
        all_match = True
        for construction, expected_pass in P5_GOLDEN_SUITE:
            outcome = verifier.verify(construction)
            if (outcome.verdict == Verdict.PASS) != expected_pass:
                all_match = False
        stamp_verdict = Verdict.PASS if all_match else Verdict.FAIL
        cert = Certification(
            verifier=verifier.name,
            verifier_version=verifier.version,
            binary_hash=verifier.binary_hash,
            golden_suite_hash=suite_hash(),
            verdict=stamp_verdict,
        )
        self._ledger.add_certification(cert)
        return cert

    def verify(self, verifier: Verifier, construction: Construction) -> VerifierResult:
        """Dispatch `verifier.verify(construction)` -- but ONLY if `verifier`
        currently holds a PASS certification stamp (matching its exact
        name/version/binary_hash) AND that stamp's golden_suite_hash equals
        the LIVE suite's hash (spec §7's full rule: a stamp earned against an
        outdated or different suite must not read as trust). Otherwise raises
        UncertifiedVerifierError; never runs an uncertified verifier.
        """
        cert = self._ledger.get_certification(
            verifier.name, verifier.version, verifier.binary_hash
        )
        if (
            cert is None
            or cert.verdict is not Verdict.PASS
            or cert.golden_suite_hash != suite_hash()
        ):
            raise UncertifiedVerifierError(
                f"{verifier.name} v{verifier.version} "
                f"(binary_hash={verifier.binary_hash[:12]}...) is not currently "
                "certified against the live P5 golden suite"
            )
        return verifier.verify(construction)


def verify_agreed(registry: Registry, construction: Construction) -> VerifierResult:
    """Run BOTH independent, certification-gated fusion verifiers on
    `construction` and require agreement: PASS only if both individually PASS
    AND their result LC-orbit keys are identical -- F3 (two independent
    implementations, no shared transition code) made concrete. This is the
    function M5c/M6 call to treat a construction as verified.
    """
    stab_res = registry.verify(StabFusionVerifier(), construction)
    enum_res = registry.verify(EnumFusionVerifier(), construction)
    details = {
        "stab_fusion_key": stab_res.details.get("lc_orbit_key"),
        "enum_fusion_key": enum_res.details.get("lc_orbit_key"),
    }
    agree = (
        stab_res.verdict is Verdict.PASS
        and enum_res.verdict is Verdict.PASS
        and details["stab_fusion_key"] == details["enum_fusion_key"]
    )
    return VerifierResult(verdict=Verdict.PASS if agree else Verdict.FAIL, details=details)

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
    `construction`. This is the function M5c/M6 call to treat a construction
    as verified, and its verdict contract distinguishes the F3 alarm from an
    honest miss:

    - Both PASS with identical LC-orbit keys -> **PASS** (the F3 certificate:
      two independent implementations agree the construction hits its target).
    - Both FAIL with identical keys -> **FAIL** (honest: the engines agree on
      what the construction produces and it genuinely misses the target --
      "this recipe doesn't work", safe to record and move on).
    - Both ran to a PASS/FAIL verdict but their keys DIFFER, or one says PASS
      and the other FAIL -> **ERROR** with `details["disagreement"] = True`
      plus both keys and verdicts. This is the F3 alarm: one of our two
      engines is WRONG. It is a machinery fault, never evidence about the
      construction -- callers must stop the world, not read it as
      "construction didn't work".
    - Either sub-verifier returns ERROR (engine or canonicalizer raised) ->
      **ERROR**, propagating each failing sub-verifier's `details["error"]`
      message prefixed by which verifier produced it.

    Details always record both verifiers' keys and verdicts, plus each
    engine's full identity (`stab_fusion_id`/`enum_fusion_id` =
    "name@version:binary_hash[:12]") so downstream evidence rows can name
    exactly WHICH certified engine pair agreed (additive; M6 T5 review M4).
    """
    stab = StabFusionVerifier()
    enum_v = EnumFusionVerifier()
    stab_res = registry.verify(stab, construction)
    enum_res = registry.verify(enum_v, construction)
    details = {
        "stab_fusion_key": stab_res.details.get("lc_orbit_key"),
        "enum_fusion_key": enum_res.details.get("lc_orbit_key"),
        "stab_fusion_verdict": stab_res.verdict.value,
        "enum_fusion_verdict": enum_res.verdict.value,
        "stab_fusion_id": f"{stab.name}@{stab.version}:{stab.binary_hash[:12]}",
        "enum_fusion_id": f"{enum_v.name}@{enum_v.version}:{enum_v.binary_hash[:12]}",
    }

    errors = [
        f"{name}: {res.details.get('error', 'unknown error')}"
        for name, res in (("stab_fusion", stab_res), ("enum_fusion", enum_res))
        if res.verdict is Verdict.ERROR
    ]
    if errors:
        details["error"] = "; ".join(errors)
        return VerifierResult(verdict=Verdict.ERROR, details=details)

    if (
        details["stab_fusion_key"] != details["enum_fusion_key"]
        or stab_res.verdict is not enum_res.verdict
    ):
        details["disagreement"] = True
        return VerifierResult(verdict=Verdict.ERROR, details=details)

    # Full agreement: identical keys, identical verdicts -- PASS, or an honest FAIL.
    return VerifierResult(verdict=stab_res.verdict, details=details)

"""P3SchemeVerifier: the Verifier wrapping `domain.p3.verify.verify_scheme_agreed`
-- P3's own two-engine (PermanentEngine/FockEngine) agreed-verdict contract over a
`BellScheme` (spec §7, F3 discipline, mirroring the P5 fusion pair / M8 LeanVerifier).

**Why this is ONE Verifier, not a pair registered separately (M5b's actual shape).**
P5 certifies TWO independent `Verifier`s (`StabFusionVerifier`/`EnumFusionVerifier`)
against `Registry.certify()`, then combines them via the module-level
`registry.verify_agreed()`. P3's domain layer already did that combining step ITSELF:
`verify_scheme_agreed` runs both `PermanentEngine` and `FockEngine` internally and
returns the single agreed `AgreedResult` -- there is no single-engine P3 verifier to
register on its own (a lone engine's result was never meant to be trusted; see
verify.py's module docstring). So `P3SchemeVerifier` sits at the SAME layer as
`registry.verify_agreed` itself: `search/loop.py` gives `verify_agreed` its own
name/version/binary_hash for evidence-row purposes (`_VERIFY_AGREED_VERSION`,
`_VERIFY_AGREED_BINARY_HASH`) despite it being a plain function, not a certified
`Verifier` instance -- `P3SchemeVerifier` just makes that same "the agreed contract
IS the trust boundary" identity a first-class, independently certifiable `Verifier`.

**Why `certify_with_suite` (the Lean path), not `Registry.certify()`/`Registry.verify()`
(the fusion path).** `verify_scheme_agreed`'s signature --
`(scheme, *, claimed_p_min=None, claimed_p_avg=None, claimed_max_leakage=0.0)` -- does
not match the fusion `Verifier` protocol's single-argument `verify(construction)` any
more than `LeanVerifier.verify(module_source, *, decl, timeout_s)` does (registry.py's
own docstring on `certify_with_suite` says exactly this is the generic engine factored
out for "any OTHER verifier with its own golden suite"). `P3SchemeVerifier` reuses that
existing additive sibling verbatim: its own suite lives in `verifiers/p3_goldens.py`
(`P3_GOLDEN_SUITE` + `p3_suite_hash()` + `certify_p3()`), parallel to
`lean_goldens.py`/`LEAN_GOLDEN_SUITE`. `P3SchemeVerifier` is deliberately OUT of
`Registry.certify()`/`P5_GOLDEN_SUITE` for the same reason `LeanVerifier` is.

**Ledger provenance.** P5's in-process, pure-Python fusion verifiers do NOT write
`runs` rows: `Registry.certify()`/`Registry.verify()` only ever call
`ledger.add_certification()` (a certification stamp, upserted into the
`certifications` table); the per-artifact provenance trail is an `EvidenceRow`
(`verifier`/`verifier_version`/`binary_hash`/`verdict`/`details`) written by the
CALLER at ingestion time (`search/loop.py`'s exact-upgrade path, `domain/p5/dataset.py`
`_validate_dataset`) -- never inside `verify()`/`verify_agreed()` itself. `runs` rows
are reserved for actual subprocess executions through `executor.execute()` (even
LeanVerifier's own subprocess calls pass `ledger=None` -- see lean.py -- so its `runs`
row discipline is likewise "none, from inside verify()"). `P3SchemeVerifier.verify()`
mirrors this exactly: it is pure in-process Python (no subprocess, no executor), calls
`verify_scheme_agreed` directly, and writes nothing to the ledger itself. A future P3
ingestion helper (the `ingest_lean_artifact` analog) is responsible for the
`EvidenceRow`, exactly as `search/loop.py`/`dataset.py` are for P5.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from blake3 import blake3

from empiricist.domain.p3.scheme import BellScheme
from empiricist.domain.p3.verify import verify_scheme_agreed
from empiricist.ledger.models import Verdict
from empiricist.verifiers.base import VerifierResult

# repo_root/src/empiricist/domain/p3 -- read fresh from disk on every binary_hash
# access (mirrors LeanVerifier: a stamp must die the instant any of these files
# changes, even without a process restart / module reimport).
_P3_DIR = Path(__file__).resolve().parents[1] / "domain" / "p3"

# The exact engine/contract surface this verifier's trust rests on: both engines
# (`engine_permanent.py`, `engine_fock.py`), their shared input/metric layer
# (`scheme.py`, `fock.py`), the mesh convention both engines interpret identically
# (`interferometer.py`), and the agreed-verdict contract itself (`verify.py`).
# Sorted so the hash is deterministic and independent of any future reordering here.
_HASHED_SOURCE_FILES = tuple(sorted((
    "fock.py",
    "interferometer.py",
    "engine_permanent.py",
    "engine_fock.py",
    "scheme.py",
    "verify.py",
)))


class P3SchemeVerifier:
    """Verifier wrapping P3's two-engine agreed-verdict contract
    (`verify_scheme_agreed`). PASS/FAIL/ERROR map straight onto the domain
    layer's own verdicts of those names; INVALID (a malformed scheme or a
    non-finite/negative claim -- P3's analog of P5's screened-out input) has
    no matching `Verdict` member, so it is mapped to FAIL with
    `details["detail"]` prefixed `"invalid: "` and `details["p3_verdict"] ==
    "INVALID"` preserved verbatim -- a ledger reader can tell a screened-out
    input apart from an honest physics miss without a schema change, the same
    way `search/loop.py` keeps `screened_out` entirely separate from
    `verify_fail`/`verify_error` counts upstream of ever calling a verifier."""

    name = "p3_scheme_agreed"
    version = "1.0"

    @property
    def binary_hash(self) -> str:
        """blake3 over the SORTED p3 source files, read fresh from disk (not
        `inspect.getsource`/cached bytecode) so an edit to any of them -- even a
        comment -- invalidates any existing certification stamp immediately."""
        hasher = blake3()
        for filename in _HASHED_SOURCE_FILES:
            hasher.update((_P3_DIR / filename).read_bytes())
        return hasher.hexdigest()

    def applicable(self, kind: str) -> bool:
        return kind == "p3_scheme"

    def verify(
        self,
        scheme: BellScheme,
        *,
        claimed_p_min: float | None = None,
        claimed_p_avg: float | None = None,
        claimed_max_leakage: float = 0.0,
    ) -> VerifierResult:
        """Run `verify_scheme_agreed` and map its verdict onto `Verdict`. Total --
        never raises: `verify_scheme_agreed` is itself contractually total (see
        verify.py's module docstring), but the call is still guarded here as
        defense-in-depth, matching stab_fusion/enum_fusion's own belt-and-braces
        try/except around an already-total engine call."""
        try:
            result = verify_scheme_agreed(
                scheme,
                claimed_p_min=claimed_p_min,
                claimed_p_avg=claimed_p_avg,
                claimed_max_leakage=claimed_max_leakage,
            )
        except Exception as exc:
            return VerifierResult(verdict=Verdict.ERROR, details={"error": str(exc)})

        details: dict[str, Any] = {
            "p3_verdict": result.verdict,
            "detail": result.detail,
            "leakage": result.leakage,
            "claimed_p_min": claimed_p_min,
            "claimed_p_avg": claimed_p_avg,
            "claimed_max_leakage": claimed_max_leakage,
        }
        if result.report is not None:
            details["success_by_state"] = dict(result.report.success_by_state)
            details["p_min"] = result.report.p_min
            details["p_avg"] = result.report.p_avg
            details["unambiguous"] = result.report.unambiguous

        if result.verdict == "PASS":
            return VerifierResult(verdict=Verdict.PASS, details=details)
        if result.verdict == "FAIL":
            return VerifierResult(verdict=Verdict.FAIL, details=details)
        if result.verdict == "ERROR":
            details["error"] = result.detail
            return VerifierResult(verdict=Verdict.ERROR, details=details)

        # result.verdict == "INVALID": no Verdict member for screened/invalid
        # input exists (PASS/FAIL/ERROR/TIMEOUT) -- fold it into FAIL, prefixed
        # so it reads as "screened out", never as an honest physics miss.
        # `p3_verdict` above still carries the original "INVALID" for any
        # caller that wants to distinguish the two FAIL flavors precisely.
        details["detail"] = f"invalid: {result.detail}"
        return VerifierResult(verdict=Verdict.FAIL, details=details)

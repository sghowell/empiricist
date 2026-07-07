"""StabFusionVerifier: the Verifier wrapping engine A (stim tableau fusion,
domain/p5/fusion_stim.py). `apply_construction` itself takes no position on
whether its result matches the target (see its docstring) -- comparing the
two LC-orbit keys is this verifier's entire job.
"""

from __future__ import annotations

import sys

from empiricist.domain.p5 import fusion_stim
from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.construction import Construction, apply_construction
from empiricist.ledger.models import Verdict
from empiricist.verifiers.base import VerifierResult, module_source_hash


class StabFusionVerifier:
    """Verifier: engine A (StimEngine). PASS iff apply_construction's result
    is LC-equivalent to construction.target; FAIL otherwise (both keys are
    recorded in details either way); ERROR -- never raise -- if ANY part of
    the verify body throws, engine or canonicalizer alike (a machinery bug
    is evidence, not a crashed run)."""

    name = "stab_fusion"
    version = "1.0"

    def __init__(self) -> None:
        self._engine = fusion_stim.StimEngine()

    @property
    def binary_hash(self) -> str:
        return module_source_hash(sys.modules[__name__], fusion_stim)

    def applicable(self, kind: str) -> bool:
        return kind == "construction"

    def verify(self, construction: Construction) -> VerifierResult:
        # The try covers the WHOLE body -- engine AND canonicalizer: a raise
        # from lc_orbit_key (e.g. an orbit-size blowup at M5c scale) must also
        # become an ERROR verdict with the message in details, never a crash.
        try:
            result = apply_construction(construction, self._engine)
            result_key = lc_orbit_key(result)
            target_key = lc_orbit_key(construction.target)
        except Exception as exc:
            return VerifierResult(verdict=Verdict.ERROR, details={"error": str(exc)})
        details = {
            "lc_orbit_key": result_key,
            "fusion_count": construction.fusion_count,
            "target_key": target_key,
        }
        verdict = Verdict.PASS if result_key == target_key else Verdict.FAIL
        return VerifierResult(verdict=verdict, details=details)

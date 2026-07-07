"""EnumFusionVerifier: the Verifier wrapping engine B (pure-Python GF(2)
bitmask fusion, domain/p5/fusion_gf2.py) -- independent of engine A by
construction (F3: no stim, no numpy, no shared transition code). Same
contract as StabFusionVerifier: `apply_construction` takes no position on
whether its result matches the target -- comparing the two LC-orbit keys is
this verifier's entire job.
"""

from __future__ import annotations

import sys

from empiricist.domain.p5 import fusion_gf2
from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.construction import Construction, apply_construction
from empiricist.ledger.models import Verdict
from empiricist.verifiers.base import VerifierResult, module_source_hash


class EnumFusionVerifier:
    """Verifier: engine B (GF2Engine). PASS iff apply_construction's result
    is LC-equivalent to construction.target; FAIL otherwise (both keys are
    recorded in details either way); ERROR -- never raise -- if the engine
    itself throws (an engine bug is evidence, not a crashed run)."""

    name = "enum_fusion"
    version = "1.0"

    def __init__(self) -> None:
        self._engine = fusion_gf2.GF2Engine()

    @property
    def binary_hash(self) -> str:
        return module_source_hash(sys.modules[__name__], fusion_gf2)

    def applicable(self, kind: str) -> bool:
        return kind == "construction"

    def verify(self, construction: Construction) -> VerifierResult:
        try:
            result = apply_construction(construction, self._engine)
        except Exception as exc:
            return VerifierResult(verdict=Verdict.ERROR, details={"error": str(exc)})
        result_key = lc_orbit_key(result)
        target_key = lc_orbit_key(construction.target)
        details = {
            "lc_orbit_key": result_key,
            "fusion_count": construction.fusion_count,
            "target_key": target_key,
        }
        verdict = Verdict.PASS if result_key == target_key else Verdict.FAIL
        return VerifierResult(verdict=verdict, details=details)

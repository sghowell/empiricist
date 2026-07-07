"""LEAN_GOLDEN_SUITE: LeanVerifier's own mutation-resistant certification
suite (spec §7's discipline, applied to a verifier whose `verify()` shape
doesn't fit `registry.Registry`/`P5_GOLDEN_SUITE` -- see `verifiers/lean.py`'s
module docstring). Every case must produce EXACTLY its `expected_pass`
outcome, case by case, to earn a PASS stamp via `certify_lean`.

Cases (source, decl, expected_pass):

1. A trivially-true, sorry-free lemma -> True (the baseline: the harness
   CAN certify a real proof, not just reject bad ones).
2. The SAME lemma with `:= by sorry` -> False. **The trap golden**: `sorry`
   is a warning (exit 0), so a naive exit-code gate would PASS this; only
   the diagnostics-severity/hasSorry check catches it (confirmed live,
   `verifiers/lean.py`).
3. A `native_decide` proof -> False. Confirmed live: `#print axioms` reports
   a per-declaration synthesized axiom (`<decl>._native.native_decide.ax_1_1`),
   not a fixed name -- the axiom-audit gate's whitelist membership test
   catches it regardless of the exact generated name.
4. A type error (unknown identifier) -> False: gate 1's plain
   `severity == "error"` check.

A suite that can't fail certifies nothing (same rationale as P5's
`_WRONG_TARGET`): cases 2-4 are the suite's actual teeth.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from blake3 import blake3

from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Certification
from empiricist.verifiers.base import VerifierResult
from empiricist.verifiers.registry import certify_with_suite

if TYPE_CHECKING:
    from empiricist.verifiers.lean import LeanVerifier

_TRUE_SOURCE = """\
namespace Empiricist

theorem scaffold_true : 1 + 1 = 2 := rfl

end Empiricist
"""

_SORRY_SOURCE = """\
namespace Empiricist

theorem scaffold_true : 1 + 1 = 2 := by sorry

end Empiricist
"""

_NATIVE_DECIDE_SOURCE = """\
namespace Empiricist

theorem nd : 2 + 2 = 4 := by native_decide

end Empiricist
"""

_TYPE_ERROR_SOURCE = """\
namespace Empiricist

theorem bad : 1 + 1 = 2 := rfl_this_is_not_a_thing

end Empiricist
"""

LEAN_GOLDEN_SUITE: list[tuple[str, str, bool]] = [
    (_TRUE_SOURCE, "Empiricist.scaffold_true", True),
    (_SORRY_SOURCE, "Empiricist.scaffold_true", False),
    (_NATIVE_DECIDE_SOURCE, "Empiricist.nd", False),
    (_TYPE_ERROR_SOURCE, "Empiricist.bad", False),
]


def lean_suite_hash() -> str:
    """blake3 hex digest of a canonical JSON repr of LEAN_GOLDEN_SUITE."""
    canon = [
        {"source": source, "decl": decl, "expected_pass": expected}
        for source, decl, expected in LEAN_GOLDEN_SUITE
    ]
    payload = json.dumps(canon, sort_keys=True, separators=(",", ":"))
    return blake3(payload.encode("utf-8")).hexdigest()


def certify_lean(ledger: Ledger, verifier: LeanVerifier) -> Certification:
    """Run LEAN_GOLDEN_SUITE through `verifier.verify(source, decl=decl)`
    and stamp a Certification (PASS iff every case matches its
    expected_pass exactly) -- LeanVerifier's own certify path, parallel to
    but independent of `registry.Registry.certify()` (which is
    fusion-verifier-specific)."""

    def run(v: LeanVerifier, case: tuple[str, str]) -> VerifierResult:
        source, decl = case
        return v.verify(source, decl=decl)

    suite = [((source, decl), expected) for source, decl, expected in LEAN_GOLDEN_SUITE]
    return certify_with_suite(ledger, verifier, suite, run, golden_suite_hash=lean_suite_hash())

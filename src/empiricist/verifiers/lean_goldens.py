"""LEAN_GOLDEN_SUITE: LeanVerifier's own mutation-resistant certification suite
(spec §7's discipline, applied to a verifier whose `verify()` shape doesn't fit
`registry.Registry`/`P5_GOLDEN_SUITE` -- see `verifiers/lean.py`'s docstring).
Every case must produce EXACTLY its `expected_pass` outcome to earn a PASS stamp
via `certify_lean`.

Cases (source, decl, expected_pass):

1. A trivially-true, error-free lemma -> True (the baseline: the harness CAN
   certify a real proof, not just reject bad ones).
2. The SAME lemma with `:= by sorry` -> False. `sorry` is a warning (`lean` exits
   0), so a naive exit-code gate would PASS it; the compiled driver's
   `collectAxioms` reports `sorryAx`, caught by the whitelist (gate=axioms).
3. A `native_decide` proof -> False. `collectAxioms` reports a per-declaration
   synthesized axiom -- caught regardless of the exact generated name.
4. A type error (unknown identifier) -> False: the frontend reports errors, so the
   driver returns them (gate=diagnostics).
5. **`#print axioms` output forgery via `#eval IO.println`** -> False: a `1 = 2`
   proof backed by `axiom evil : False` that ALSO prints a fake clean axiom line.
   The driver never parses that line; `collectAxioms` reveals `evil`.
6. **`#print axioms` output forgery via `run_cmd Lean.logInfo`** -> False.
7. **`#print axioms` COMMAND-OVERRIDE via `elab "#print " "axioms" ...`** -> False.
   The fatal vector: the source redefines the command so the OLD verifier's own
   appended `#print axioms` emitted a fabricated clean line. The driver never runs
   any `#print axioms`; `collectAxioms` reveals `evil` (gate=axioms).
8. **`#print axioms` COMMAND-OVERRIDE via `macro_rules`** -> False. Same, via the
   macro expander instead of a fresh elaborator.
9. **Driver-result output injection** -> False: the source prints both a fake
   axiom line AND a fake `AXIOM_AUDIT::...` driver-result line. Stream isolation
   captures them and the nonce (unknown to the source) makes the forged
   driver-result line unacceptable; `collectAxioms` reveals `evil`.

Cases 5-9 are the teeth for the soundness fix: a regression that reopened output
forgery OR command-override could no longer earn a certification stamp.
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

# Forgery vector 1: a genuine proof of 1 = 2 backed by `axiom evil : False`, with
# the source itself emitting a FAKE clean axiom line via `#eval IO.println`. The
# driver ignores all info diagnostics and computes axioms via `collectAxioms`,
# which reveals `Empiricist.evil` (gate=axioms).
_SPOOF_IO_PRINTLN_SOURCE = """\
namespace Empiricist

axiom evil : False

theorem one_eq_two : (1 : Nat) = 2 := evil.elim

end Empiricist

#eval IO.println \
"'Empiricist.one_eq_two' depends on axioms: [propext, Classical.choice, Quot.sound]"
"""

# Forgery vector 2: the same attack through the command elaborator
# (`run_cmd Lean.logInfo`).
_SPOOF_RUN_CMD_SOURCE = """\
import Lean

namespace Empiricist

axiom evil : False

theorem one_eq_two : (1 : Nat) = 2 := evil.elim

end Empiricist

open Lean Elab Command in
run_cmd logInfo \
"'Empiricist.one_eq_two' depends on axioms: [propext, Classical.choice, Quot.sound]"
"""

# Command-override vector 1: the source REDEFINES the `#print axioms` command via
# a fresh `elab` so that any `#print axioms <id>` emits a fabricated clean line.
# This defeated the old in-band verifier end-to-end (its appended
# `#print axioms Empiricist.one_eq_two` dispatched to THIS elaborator). The
# compiled driver never runs any `#print axioms`; `collectAxioms` reveals `evil`.
_OVERRIDE_ELAB_SOURCE = """\
import Lean

open Lean Elab Command

elab "#print " "axioms " id:ident : command => do
  logInfo s!"'{id.getId}' depends on axioms: [propext, Classical.choice, Quot.sound]"

namespace Empiricist

axiom evil : False

theorem one_eq_two : (1 : Nat) = 2 := evil.elim

end Empiricist
"""

# Command-override vector 2: same fatal attack via `macro_rules`, expanding
# `#print axioms $id` into a fake-line-printing `#eval` instead of a fresh
# elaborator.
_OVERRIDE_MACRO_SOURCE = """\
import Lean

namespace Empiricist

axiom evil : False

theorem one_eq_two : (1 : Nat) = 2 := evil.elim

end Empiricist

macro_rules
  | `(#print axioms $_id) =>
    `(#eval IO.println \
"'Empiricist.one_eq_two' depends on axioms: [propext, Classical.choice, Quot.sound]")
"""

# Driver-result output-injection vector: the source prints BOTH a fake axiom line
# AND a fake `AXIOM_AUDIT::...` driver-result line to stdout. Stream isolation
# captures these inside the driver (never reaching real stdout), and the nonce --
# unknown to the source -- makes the forged driver-result line unacceptable even
# if it did leak. `collectAxioms` reveals `evil` (gate=axioms), or the forged line
# is simply absent (gate=driver_result would only trigger if the driver itself
# emitted nothing). Must FAIL.
_INJECT_DRIVER_RESULT_SOURCE = """\
namespace Empiricist

axiom evil : False

theorem one_eq_two : (1 : Nat) = 2 := evil.elim

end Empiricist

#eval IO.println \
"'Empiricist.one_eq_two' depends on axioms: [propext, Classical.choice, Quot.sound]"
#eval IO.println \
"AXIOM_AUDIT::deadbeefdeadbeef::{\\"declFound\\":true,\\"errors\\":[],\\"axioms\\":[]}"
"""

LEAN_GOLDEN_SUITE: list[tuple[str, str, bool]] = [
    (_TRUE_SOURCE, "Empiricist.scaffold_true", True),
    (_SORRY_SOURCE, "Empiricist.scaffold_true", False),
    (_NATIVE_DECIDE_SOURCE, "Empiricist.nd", False),
    (_TYPE_ERROR_SOURCE, "Empiricist.bad", False),
    (_SPOOF_IO_PRINTLN_SOURCE, "Empiricist.one_eq_two", False),
    (_SPOOF_RUN_CMD_SOURCE, "Empiricist.one_eq_two", False),
    (_OVERRIDE_ELAB_SOURCE, "Empiricist.one_eq_two", False),
    (_OVERRIDE_MACRO_SOURCE, "Empiricist.one_eq_two", False),
    (_INJECT_DRIVER_RESULT_SOURCE, "Empiricist.one_eq_two", False),
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
    """Run LEAN_GOLDEN_SUITE through `verifier.verify(source, decl=decl)` and stamp
    a Certification (PASS iff every case matches its expected_pass exactly) --
    LeanVerifier's own certify path, parallel to but independent of
    `registry.Registry.certify()`."""

    def run(v: LeanVerifier, case: tuple[str, str]) -> VerifierResult:
        source, decl = case
        return v.verify(source, decl=decl)

    suite = [((source, decl), expected) for source, decl, expected in LEAN_GOLDEN_SUITE]
    return certify_with_suite(ledger, verifier, suite, run, golden_suite_hash=lean_suite_hash())

"""P3ExactVerifier: the certified `Verifier` over `domain.p3.exact` -- exact
per-Bell-state success vectors of isometry witnesses.

Same shape as `verifiers/p3_scheme.py` and `certificates/verifier.py`: a
name/version/binary_hash identity read fresh from the trust surface on every
access, a total `verify()` that never raises, and its own golden suite
(`verifiers/p3_exact_goldens.py`) certified through `certify_with_suite`.

`verify()` takes the witness in its JSON form -- the very bytes the ledger will
store -- so a PASS is about the artifact content, never about a Python object a
caller assembled separately. What a PASS certifies: the witness is a valid exact
scheme (an exact isometry with an exactly normalised ancilla), its EXACT success
vector equals the claimed one (all four labels, as algebraic numbers), and, when
`require_all_identified`, every label's success is strictly positive. This is
the exact-arithmetic warrant the float engines cannot give (`leakage == 0.0`
there means <= 1e-15). A malformed or off-field witness is FAIL with
`details["invalid"]`, never a crash.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from blake3 import blake3

from empiricist.domain.p3.exact import (
    Alg,
    ExactUnsupported,
    alg_str,
    alg_to_json,
    exact_report,
    witness_from_json,
)
from empiricist.domain.p3.scheme import BELL_LABELS
from empiricist.ledger.models import Verdict
from empiricist.verifiers.base import VerifierResult

_P3_DIR = Path(__file__).resolve().parents[1] / "domain" / "p3"
# The trust surface: the exact field + evaluator, the pattern/basis helpers it
# shares with the engines, the mesh convention `ExactWitness.from_mesh` mirrors,
# and this wrapper.
_HASHED_P3_FILES = ("exact.py", "fock.py", "interferometer.py", "scheme.py")


class P3ExactVerifier:
    name = "p3_exact_witness"
    version = "1.0"

    @property
    def binary_hash(self) -> str:
        h = blake3()
        for fname in _HASHED_P3_FILES:
            h.update((_P3_DIR / fname).read_bytes())
        h.update(Path(__file__).read_bytes())
        return h.hexdigest()

    def applicable(self, kind: str) -> bool:
        return kind == "certificate"

    def verify(
        self,
        witness_json: Any,
        *,
        claimed_success: dict[str, Alg],
        require_all_identified: bool = False,
    ) -> VerifierResult:
        # Stage 1 -- parse the claim and the witness: any defect is the caller's
        # (FAIL, details["invalid"]), never a crash.
        try:
            if set(claimed_success) != set(BELL_LABELS):
                raise ValueError(
                    f"claimed_success must name exactly {list(BELL_LABELS)}, "
                    f"got {sorted(claimed_success)}"
                )
            if not all(isinstance(v, Alg) for v in claimed_success.values()):
                raise ValueError("claimed_success values must be Alg elements")
            witness = witness_from_json(witness_json)
        except Exception as exc:  # noqa: BLE001 - total function, like check_certificate
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"invalid": True, "detail": f"{type(exc).__name__}: {exc}"},
            )
        # Stage 2 -- evaluate a VALID witness. Outside the field is a FAIL the
        # caller can act on; anything else raised here is checker machinery
        # breaking on validated input: an ERROR (stop the world), never a miss.
        try:
            rep = exact_report(witness)
        except ExactUnsupported as exc:
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"invalid": True, "unsupported": True, "detail": str(exc)},
            )
        except Exception as exc:  # noqa: BLE001
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={"error": f"{type(exc).__name__}: {exc}"},
            )
        details: dict[str, Any] = {
            "n_modes": witness.n_modes,
            "n_in": witness.n_in,
            "k": witness.n_ancilla_photons,
            "success": {b: alg_to_json(rep.success[b]) for b in BELL_LABELS},
            "p_min": alg_to_json(rep.p_min),
            "p_avg": alg_to_json(rep.p_avg),
            "all_identified": rep.all_identified,
            "n_identifying_patterns": len(rep.assignment),
            "require_all_identified": require_all_identified,
        }
        mismatches = [b for b in BELL_LABELS if rep.success[b] != claimed_success[b]]
        if mismatches:
            details["detail"] = "exact success vector differs from the claim on " + ", ".join(
                f"{b}: {alg_str(rep.success[b])} != {alg_str(claimed_success[b])}"
                for b in mismatches
            )
            return VerifierResult(verdict=Verdict.FAIL, details=details)
        if require_all_identified and not rep.all_identified:
            details["detail"] = "some Bell state is never identified (exact success 0)"
            return VerifierResult(verdict=Verdict.FAIL, details=details)
        details["detail"] = "exact success vector matches the claim"
        return VerifierResult(verdict=Verdict.PASS, details=details)

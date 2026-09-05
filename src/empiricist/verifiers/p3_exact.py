"""P3ExactVerifier: the certified `Verifier` over `domain.p3.exact` -- exact
per-Bell-state success vectors for octant-angle schemes.

Same shape as `verifiers/p3_scheme.py` and `certificates/verifier.py`: a
name/version/binary_hash identity read fresh from the trust surface on every
access, a total `verify()` that never raises, and its own golden suite
(`verifiers/p3_exact_goldens.py`) certified through `certify_with_suite`.

What a PASS certifies: the scheme's EXACT success vector equals the claimed one
(all four labels, as elements of Q(sqrt2)) and, when `require_all_identified`,
every label's success is strictly positive. This is the exact-arithmetic warrant
that the float engines cannot give (`leakage == 0.0` there means <= 1e-15).
A scheme outside Q(i, sqrt2) is FAIL with `details["unsupported"]`, never a
crash: it simply cannot be certified this way.
"""
from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any

from blake3 import blake3

from empiricist.domain.p3.exact import QR, ExactUnsupported, exact_report
from empiricist.domain.p3.scheme import BELL_LABELS, BellScheme
from empiricist.ledger.models import Verdict
from empiricist.verifiers.base import VerifierResult

_P3_DIR = Path(__file__).resolve().parents[1] / "domain" / "p3"
_HASHED_P3_FILES = ("exact.py", "fock.py", "interferometer.py", "scheme.py")


def qr_to_json(q: QR) -> list[str]:
    """`a + b*sqrt2` as `["a", "b"]` (Fraction strings)."""
    return [str(q.a), str(q.b)]


def qr_from_json(v: Any) -> QR:
    """Inverse of `qr_to_json`; also accepts a bare rational string/number.
    Raises ValueError on any other shape."""
    try:
        if isinstance(v, (str, int)):
            return QR(Fraction(v), Fraction(0))
        a, b = v
        return QR(Fraction(a), Fraction(b))
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise ValueError(f"not a Q(sqrt2) element: {v!r} ({exc})") from exc


def qr_str(q: QR) -> str:
    return str(q.a) if q.b == 0 else f"{q.a} + {q.b}*sqrt2"


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
        scheme: BellScheme,
        *,
        claimed_success: dict[str, QR],
        require_all_identified: bool = False,
    ) -> VerifierResult:
        try:
            if set(claimed_success) != set(BELL_LABELS):
                raise ValueError(
                    f"claimed_success must name exactly {list(BELL_LABELS)}, "
                    f"got {sorted(claimed_success)}"
                )
            rep = exact_report(scheme)
        except ExactUnsupported as exc:
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"unsupported": True, "detail": f"outside Q(i, sqrt2): {exc}"},
            )
        except Exception as exc:  # noqa: BLE001 - total function, like check_certificate
            return VerifierResult(
                verdict=Verdict.FAIL,
                details={"invalid": True, "detail": f"{type(exc).__name__}: {exc}"},
            )
        achieved = {b: qr_to_json(rep.success[b]) for b in BELL_LABELS}
        details: dict[str, Any] = {
            "success": achieved,
            "p_min": qr_to_json(rep.p_min),
            "p_avg": qr_to_json(rep.p_avg),
            "all_identified": rep.all_identified,
            "n_identifying_patterns": len(rep.assignment),
            "require_all_identified": require_all_identified,
        }
        mismatches = [
            b for b in BELL_LABELS if rep.success[b] != claimed_success[b]
        ]
        if mismatches:
            details["detail"] = (
                "exact success vector differs from the claim on "
                + ", ".join(f"{b}: {qr_str(rep.success[b])} != {qr_str(claimed_success[b])}"
                            for b in mismatches)
            )
            return VerifierResult(verdict=Verdict.FAIL, details=details)
        if require_all_identified and not rep.all_identified:
            details["detail"] = "some Bell state is never identified (exact success 0)"
            return VerifierResult(verdict=Verdict.FAIL, details=details)
        details["detail"] = "exact success vector matches the claim"
        return VerifierResult(verdict=Verdict.PASS, details=details)

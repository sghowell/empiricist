"""SOSCertificateVerifier: the `Verifier` wrapping `certificates.core.check_certificate`.

Same shape as `verifiers/p3_scheme.py` / `LeanVerifier`: a name/version/binary_hash
identity whose certification stamp dies the instant the checker's source changes,
a total `verify()` that never raises, and its own golden suite
(`certificates/goldens.py`) certified through `certify_with_suite`. The checker's
exact rational arithmetic is the trust boundary; this class only gives it a
ledger identity, plus the canonical JSON form certificates travel in.
"""
from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any

from blake3 import blake3

from empiricist.certificates.core import Monomial, Poly, SOSCertificate, check_certificate
from empiricist.ledger.models import Verdict
from empiricist.verifiers.base import VerifierResult

_CERT_DIR = Path(__file__).resolve().parent
# The trust surface: the checker, the target definitions an ingest re-derives
# domain meaning from, the ingest module that turns a PASS into a ledger claim
# (its target registry and claim wording), and this wrapper. Read fresh from disk
# on every access (mirrors P3SchemeVerifier/LeanVerifier) so an edit to any of
# them invalidates existing stamps.
_HASHED_SOURCE_FILES = ("core.py", "ingest.py", "p3_targets.py", "verifier.py")


def _mono_key(mono: Monomial) -> str:
    return ",".join(str(i) for i in mono)


def _mono_from_key(key: str) -> Monomial:
    return tuple(int(x) for x in key.split(",")) if key else ()


def _poly_to_json(p: Poly) -> dict[str, str]:
    return {_mono_key(m): str(c) for m, c in sorted(p.items())}


def _rational(v: Any) -> Fraction:
    """Exact rationals only: strings ("1/2", "3") or ints. A JSON float is refused
    (it would be converted exactly but silently launder a rounded number)."""
    if isinstance(v, bool) or not isinstance(v, (str, int)):
        raise ValueError(f"rational must be a string or int, got {type(v).__name__}")
    return Fraction(v)


def _poly_from_json(d: Any) -> Poly:
    if not isinstance(d, dict):
        raise ValueError("polynomial must be a JSON object")
    return {_mono_from_key(k): _rational(v) for k, v in d.items()}


def certificate_to_json(cert: SOSCertificate) -> dict:
    """Canonical JSON form: every rational as a string, monomials as comma-joined
    index keys (the pinned golden file's format)."""
    return {
        "statement": cert.statement,
        "variables": list(cert.variables),
        "objective": _poly_to_json(cert.objective),
        "bound": str(cert.bound),
        "constraints": [_poly_to_json(c) for c in cert.constraints],
        "multipliers": [_poly_to_json(m) for m in cert.multipliers],
        "gram_basis": [list(m) for m in cert.gram_basis],
        "gram": [[str(v) for v in row] for row in cert.gram],
    }


def certificate_from_json(data: Any) -> SOSCertificate:
    """Inverse of `certificate_to_json`. Raises ValueError on any shape defect
    (the ingest path maps that to a refusal; the checker itself never sees it)."""
    try:
        return SOSCertificate(
            statement=str(data["statement"]),
            variables=tuple(str(v) for v in data["variables"]),
            objective=_poly_from_json(data["objective"]),
            bound=_rational(data["bound"]),
            constraints=tuple(_poly_from_json(c) for c in data["constraints"]),
            multipliers=tuple(_poly_from_json(m) for m in data["multipliers"]),
            gram_basis=tuple(tuple(int(i) for i in m) for m in data["gram_basis"]),
            gram=tuple(tuple(_rational(v) for v in row) for row in data["gram"]),
        )
    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
        raise ValueError(f"malformed certificate JSON: {type(exc).__name__}: {exc}") from exc


class SOSCertificateVerifier:
    """PASS iff the exact checker accepts the certificate. Total: never raises."""

    name = "sos_certificate"
    version = "1.0"

    @property
    def binary_hash(self) -> str:
        h = blake3()
        for fname in _HASHED_SOURCE_FILES:
            h.update((_CERT_DIR / fname).read_bytes())
        return h.hexdigest()

    def applicable(self, kind: str) -> bool:
        return kind == "certificate"

    def verify(self, cert: Any) -> VerifierResult:
        res = check_certificate(cert)
        details: dict[str, Any] = {"failure": res.failure, "detail": res.detail}
        if not res.ok:
            return VerifierResult(verdict=Verdict.FAIL, details=details)
        details["bound"] = str(cert.bound)
        details["gram_dim"] = len(cert.gram_basis)
        details["n_constraints"] = len(cert.constraints)
        return VerifierResult(verdict=Verdict.PASS, details=details)

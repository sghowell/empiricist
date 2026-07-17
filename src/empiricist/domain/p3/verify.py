# src/empiricist/domain/p3/verify.py
"""Two-engine agreed verdict for P3 schemes (the F3 discipline).

PASS: the engines agree on every per-Bell-state distribution (per-pattern over
the UNION of keys, missing -> 0.0, tolerance 1e-8) AND every stated claim is
achieved (metric tolerance 1e-9; leakage within the DECLARED budget).
FAIL: engines agree, claim not met -- an honest miss.
ERROR: the engines disagree -- a physics-model bug, never a search miss; the
campaign must stop, not retry.

Leakage policy: `claimed_max_leakage` defaults to 0.0 -- an unambiguity claim
is exact unless the claimant DECLARES a leakage budget, which is then recorded
with the claim. A search cannot silently ride under a fixed floor.
"""

from __future__ import annotations

from dataclasses import dataclass

from .engine_fock import FockEngine
from .engine_permanent import PermanentEngine
from .scheme import BELL_LABELS, BellScheme, SchemeReport, evaluate_scheme

_AGREE_TOL = 1e-8
_CLAIM_TOL = 1e-9


@dataclass(frozen=True)
class AgreedResult:
    verdict: str                 # "PASS" | "FAIL" | "ERROR"
    report: SchemeReport | None
    detail: str


def verify_scheme_agreed(
    scheme: BellScheme,
    *,
    claimed_p_min: float | None = None,
    claimed_p_avg: float | None = None,
    claimed_max_leakage: float = 0.0,
) -> AgreedResult:
    ra = evaluate_scheme(scheme, PermanentEngine())
    rb = evaluate_scheme(scheme, FockEngine())
    for b in BELL_LABELS:
        keys = set(ra.distributions[b]) | set(rb.distributions[b])
        for k in keys:
            da = ra.distributions[b].get(k, 0.0)
            db = rb.distributions[b].get(k, 0.0)
            if abs(da - db) > _AGREE_TOL:
                return AgreedResult(
                    "ERROR", None,
                    f"engines disagree on {b} pattern {k}: {da} vs {db}",
                )
    failures: list[str] = []
    if claimed_p_min is not None and ra.p_min < claimed_p_min - _CLAIM_TOL:
        failures.append(f"p_min {ra.p_min} < claimed {claimed_p_min}")
    if claimed_p_avg is not None and ra.p_avg < claimed_p_avg - _CLAIM_TOL:
        failures.append(f"p_avg {ra.p_avg} < claimed {claimed_p_avg}")
    if ra.leakage > claimed_max_leakage + 1e-15:
        failures.append(
            f"leakage {ra.leakage} exceeds declared budget {claimed_max_leakage}"
        )
    if failures:
        return AgreedResult("FAIL", ra, "; ".join(failures))
    return AgreedResult("PASS", ra, "agreed")

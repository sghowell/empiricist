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
with the claim. A search cannot silently ride under a fixed floor. The budget
is checked against max(leakage_A, leakage_B) over BOTH engines, and that value
is carried on the result as `AgreedResult.leakage`.

Certificate semantics (normative): a PASS never certifies bare "unambiguous";
it certifies "unambiguous up to leakage <= <declared budget> (engine prune
floor 1e-15)". A checked leakage of 0.0 certifies only that the
misidentification probability is <= n_patterns x 1e-15 -- the float
representability floor, NOT exact zero. POLICY: a claim that a scheme BEATS a
strict theoretical bound (e.g. p > 1/2 at k=0) must not be recorded above
HEURISTIC on this float evidence alone; strict unambiguity requires exact
(rational/interval) arithmetic -- that is the M20 certificate layer's job.
This verifier certifies achievability-with-declared-leakage only.
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
    report: SchemeReport | None  # Engine-A report, for downstream recording
    detail: str
    # max(leakage_A, leakage_B) -- the value the budget check used; downstream
    # recording reads it here, never from the (single-engine) report.
    leakage: float


def verify_scheme_agreed(
    scheme: BellScheme,
    *,
    claimed_p_min: float | None = None,
    claimed_p_avg: float | None = None,
    claimed_max_leakage: float = 0.0,
) -> AgreedResult:
    ra = evaluate_scheme(scheme, PermanentEngine())
    rb = evaluate_scheme(scheme, FockEngine())
    leakage = max(ra.leakage, rb.leakage)
    for b in BELL_LABELS:
        keys = set(ra.distributions[b]) | set(rb.distributions[b])
        for k in keys:
            da = ra.distributions[b].get(k, 0.0)
            db = rb.distributions[b].get(k, 0.0)
            if abs(da - db) > _AGREE_TOL:
                return AgreedResult(
                    "ERROR", None,
                    f"engines disagree on {b} pattern {k}: {da} vs {db}",
                    leakage,
                )
    failures: list[str] = []
    if claimed_p_min is not None and ra.p_min < claimed_p_min - _CLAIM_TOL:
        failures.append(f"p_min {ra.p_min} < claimed {claimed_p_min}")
    if claimed_p_avg is not None and ra.p_avg < claimed_p_avg - _CLAIM_TOL:
        failures.append(f"p_avg {ra.p_avg} < claimed {claimed_p_avg}")
    if leakage > claimed_max_leakage + 1e-15:
        failures.append(
            f"max-engine leakage {leakage} exceeds declared budget "
            f"{claimed_max_leakage}"
        )
    if failures:
        return AgreedResult("FAIL", ra, "; ".join(failures), leakage)
    return AgreedResult("PASS", ra, "agreed", leakage)

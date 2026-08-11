# src/empiricist/domain/p3/verify.py
"""Two-engine agreed verdict for P3 schemes (the F3 discipline).

Four verdicts; verify_scheme_agreed never raises on model-emittable input:
PASS: the engines agree on every per-Bell-state distribution (per-pattern over
the UNION of keys, missing -> 0.0, tolerance 1e-8), derive the SAME identifying
pattern assignment, agree on every derived success/leakage metric, AND every
stated claim is achieved by the conservative two-engine consensus report
(claim tolerance 1e-9; leakage within the DECLARED budget).
FAIL: engines agree, claim not met -- an honest miss.
ERROR: the engines disagree, OR an engine raises on a VALIDATED scheme (a
machinery bug, mirrors P5's verify_error) -- a physics-model or machinery
bug, never a search miss; the campaign must stop, not retry.
INVALID: the scheme or the claim itself is malformed (scheme validation
failure; non-finite or negative claim values) -- the campaign loop SKIPS it
(the analog of P5's screened_out); never treated as an engine alarm.

`AgreedResult.leakage` is defined only for PASS/FAIL verdicts; -1.0 otherwise
(on ERROR at least one engine is untrusted).

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

import math
from dataclasses import dataclass

from .engine_fock import FockEngine
from .engine_permanent import PermanentEngine
from .scheme import (
    BELL_LABELS,
    BellScheme,
    SchemeReport,
    bell_input_states,
    derive_assignment,
    evaluate_scheme,
)

_AGREE_TOL = 1e-8
_REPORT_AGREE_TOL = 1e-8
_CLAIM_TOL = 1e-9


@dataclass(frozen=True)
class AgreedResult:
    verdict: str                 # "PASS" | "FAIL" | "ERROR" | "INVALID"
    report: SchemeReport | None  # conservative two-engine consensus report
    detail: str
    # max(leakage_A, leakage_B) -- the value the budget check used; downstream
    # recording reads it here, never from the (single-engine) report. Defined
    # only for PASS/FAIL; -1.0 on ERROR/INVALID.
    leakage: float


def verify_scheme_agreed(
    scheme: BellScheme,
    *,
    claimed_p_min: float | None = None,
    claimed_p_avg: float | None = None,
    claimed_max_leakage: float = 0.0,
) -> AgreedResult:
    # NaN-proof: `not (x >= 0.0)` catches NaN and negatives in one comparison;
    # +inf passes `>= 0.0`, so reject it explicitly.
    if math.isinf(claimed_max_leakage) or not (claimed_max_leakage >= 0.0):
        return AgreedResult(
            "INVALID", None,
            "invalid claim: leakage budget must be a finite non-negative number",
            -1.0,
        )
    for name, val in (("claimed_p_min", claimed_p_min),
                      ("claimed_p_avg", claimed_p_avg)):
        if val is not None and not math.isfinite(val):
            return AgreedResult(
                "INVALID", None, f"invalid claim: {name} must be finite", -1.0
            )
    # Malformed-scheme screening (INVALID) is exactly what these two calls
    # reach; an exception past this point is an ENGINE bug (ERROR), never
    # conflated with a bad input.
    try:
        scheme.validate()
        bell_input_states(scheme.n_modes, scheme.ancilla)
    except (ValueError, TypeError) as e:
        return AgreedResult("INVALID", None, f"invalid scheme: {e}", -1.0)
    try:
        ra = evaluate_scheme(scheme, PermanentEngine())
        rb = evaluate_scheme(scheme, FockEngine())
    # Deliberately broad: ANY engine raise on a validated scheme is a
    # stop-the-world machinery alarm (P5 precedent: stab_fusion never raises).
    except Exception as e:
        return AgreedResult(
            "ERROR", None,
            f"engine exception (machinery bug, not a disagreement): {e}",
            -1.0,
        )
    diffs: list[tuple[str, tuple[int, ...], float, float]] = []
    for b in BELL_LABELS:
        keys = set(ra.distributions[b]) | set(rb.distributions[b])
        for k in keys:
            da = ra.distributions[b].get(k, 0.0)
            db = rb.distributions[b].get(k, 0.0)
            # NaN-proof form: a NaN probability can never silently "agree".
            if not (abs(da - db) <= _AGREE_TOL):
                diffs.append((b, k, da, db))
    if diffs:
        diffs.sort()
        return AgreedResult(
            "ERROR", None,
            f"engines disagree on {len(diffs)} pattern(s): {diffs[:8]}",
            -1.0,
        )

    # Distribution closeness alone is not semantic agreement: _AGREE_TOL is
    # deliberately looser than scheme.py's assignment threshold, so two values
    # may compare "close" while falling on opposite sides of _AMBIG_TOL. Require
    # the independently-derived identifying-pattern maps to agree exactly.
    assignment_a = derive_assignment(ra.distributions)
    assignment_b = derive_assignment(rb.distributions)
    assignment_diffs = [
        (
            pat,
            assignment_a.get(pat, "<unassigned>"),
            assignment_b.get(pat, "<unassigned>"),
        )
        for pat in set(assignment_a) | set(assignment_b)
        if assignment_a.get(pat) != assignment_b.get(pat)
    ]
    if assignment_diffs:
        assignment_diffs.sort(key=lambda item: item[0])
        return AgreedResult(
            "ERROR",
            None,
            "engines derive different identifying-pattern assignments on "
            f"{len(assignment_diffs)} pattern(s): {assignment_diffs[:8]}",
            -1.0,
        )

    # Belt-and-braces: even with identical assignments, accumulated numeric
    # error or a regression in report derivation can make the engines disagree
    # on the claimed metrics. Compare every derived field before constructing a
    # conservative consensus; never silently trust Engine A's report.
    report_diffs: list[str] = []
    for bell in BELL_LABELS:
        pa = ra.success_by_state[bell]
        pb = rb.success_by_state[bell]
        if not (abs(pa - pb) <= _REPORT_AGREE_TOL):
            report_diffs.append(f"success[{bell}]={pa} vs {pb}")
    for name, a, b in (
        ("p_min", ra.p_min, rb.p_min),
        ("p_avg", ra.p_avg, rb.p_avg),
        ("leakage", ra.leakage, rb.leakage),
    ):
        if not (abs(a - b) <= _REPORT_AGREE_TOL):
            report_diffs.append(f"{name}={a} vs {b}")
    if ra.unambiguous != rb.unambiguous:
        report_diffs.append(f"unambiguous={ra.unambiguous} vs {rb.unambiguous}")
    if report_diffs:
        return AgreedResult(
            "ERROR",
            None,
            f"engines derive different scheme reports: {report_diffs[:8]}",
            -1.0,
        )

    success = {
        bell: min(ra.success_by_state[bell], rb.success_by_state[bell])
        for bell in BELL_LABELS
    }
    leakage = max(ra.leakage, rb.leakage)
    report = SchemeReport(
        success_by_state=success,
        p_min=min(success.values()),
        p_avg=sum(success.values()) / 4.0,
        leakage=leakage,
        unambiguous=ra.unambiguous and rb.unambiguous,
        # Pattern distributions are diagnostic and already agreed above.
        # Retain one copy rather than doubling a potentially large report.
        distributions=ra.distributions,
    )
    failures: list[str] = []
    if claimed_p_min is not None and report.p_min < claimed_p_min - _CLAIM_TOL:
        failures.append(f"p_min {report.p_min} < claimed {claimed_p_min}")
    if claimed_p_avg is not None and report.p_avg < claimed_p_avg - _CLAIM_TOL:
        failures.append(f"p_avg {report.p_avg} < claimed {claimed_p_avg}")
    if leakage > claimed_max_leakage + 1e-15:
        failures.append(
            f"max-engine leakage {leakage} exceeds declared budget "
            f"{claimed_max_leakage}"
        )
    if failures:
        return AgreedResult("FAIL", report, "; ".join(failures), leakage)
    return AgreedResult("PASS", report, "agreed", leakage)

"""The P3 screen: caps + conversion BEFORE the verifier (P5's ScreenReject discipline).

Model output is never trusted: a schema-valid `BellSchemeOut` can still be a
compute DoS (a valid 50-photon ancilla sends Ryser's permanent into 2^50
iterations) or a malformed scheme. The screen converts and caps FIRST, raising
`ScreenReject` so the campaign loop skips (never halts, never verifies).

Caps are sized so the worst case inside them stays ~1.5 s per Bell state on
Engine A (n_modes=12, 6 photons); everything outside is rejected unexamined.
"""

from __future__ import annotations

from empiricist.domain.p3.scheme import BellScheme, scheme_from_out
from empiricist.llm.schemas import BellSchemeOut
from empiricist.search.schemas import ScreenReject

MAX_MODES = 12
MAX_PHOTONS = 4          # ancilla photons k; total photons = k + 2 <= 6
MAX_MESH_ELEMENTS = 64
MAX_ANCILLA_TERMS = 32


def screen_scheme(raw: dict) -> BellScheme:
    """Parse, cap, and convert a raw model-emitted dict into a validated BellScheme.

    Raises ScreenReject on ANY defect: schema violation, cap violation, or
    conversion/validation failure. Never raises anything else.
    """
    try:
        out = BellSchemeOut.model_validate(raw)
    except Exception as exc:  # pydantic ValidationError and friends
        raise ScreenReject(f"schema: {exc}") from exc
    if out.n_modes > MAX_MODES:
        raise ScreenReject(f"n_modes {out.n_modes} exceeds cap {MAX_MODES}")
    if out.n_ancilla_photons > MAX_PHOTONS:
        raise ScreenReject(
            f"n_ancilla_photons {out.n_ancilla_photons} exceeds cap {MAX_PHOTONS}"
        )
    if len(out.mesh) > MAX_MESH_ELEMENTS:
        raise ScreenReject(f"mesh length {len(out.mesh)} exceeds cap {MAX_MESH_ELEMENTS}")
    if len(out.ancilla) > MAX_ANCILLA_TERMS:
        raise ScreenReject(f"ancilla terms {len(out.ancilla)} exceed cap {MAX_ANCILLA_TERMS}")
    # belt-and-braces: pattern-level photon cap even if n_ancilla_photons lies
    for term in out.ancilla:
        if sum(term.pattern) > MAX_PHOTONS:
            raise ScreenReject("ancilla pattern photon count exceeds cap")
    try:
        return scheme_from_out(out)
    except (ValueError, TypeError) as exc:
        raise ScreenReject(f"invalid scheme: {exc}") from exc

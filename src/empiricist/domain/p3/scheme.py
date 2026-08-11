"""Bell-measurement schemes: dual-rail Bell inputs, derived assignment, metrics.

Dual-rail encoding on modes 0..3 (qubit A rails 0,1; qubit B rails 2,3):
  |phi+-> = (|1,0,1,0> +- |0,1,0,1>)/sqrt(2)
  |psi+-> = (|1,0,0,1> +- |0,1,1,0>)/sqrt(2)
The ancilla is a k-photon Fock superposition on modes 4..m-1. The assignment f
is DERIVED: pattern n is assigned to B iff Pr[n|B] > tol and Pr[n|B'] <= tol
for the other three (tol = _AMBIG_TOL). The tolerance only governs assignment
ROBUSTNESS -- honesty is carried by the `leakage` field: sub-tol probability
mass from the non-assigned Bell states on assigned patterns is accumulated and
reported, and `unambiguous` is derived from it (leakage <= _LEAK_FLOOR), never
asserted by construction.

Metrics (design decision): p_min = min_B (the problem's p) AND p_avg = mean_B
(the literature's figure -- e.g. Grice's boosted scheme is avg 3/4 but min 1/2).
Claims must name their metric.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from .interferometer import Mesh

BELL_LABELS = ("phi+", "phi-", "psi+", "psi-")
_AMBIG_TOL = 1e-11
# Numerically-unambiguous threshold for the derived `unambiguous` flag:
# deliberately below the 1e-9 claim tolerance and above engine noise. Distinct
# from _AMBIG_TOL, which only governs assignment robustness.
_LEAK_FLOOR = 1e-12

FockState = dict[tuple[int, ...], complex]


def bell_input_states(n_modes: int, ancilla: FockState) -> dict[str, FockState]:
    """The four Bell (x) ancilla input states on n_modes modes."""
    anc = ancilla if ancilla else {(): 1.0 + 0.0j}
    r = 1 / sqrt(2)
    bell4: dict[str, dict[tuple[int, int, int, int], float]] = {
        "phi+": {(1, 0, 1, 0): r, (0, 1, 0, 1): r},
        "phi-": {(1, 0, 1, 0): r, (0, 1, 0, 1): -r},
        "psi+": {(1, 0, 0, 1): r, (0, 1, 1, 0): r},
        "psi-": {(1, 0, 0, 1): r, (0, 1, 1, 0): -r},
    }
    out: dict[str, FockState] = {}
    for label, b4 in bell4.items():
        state: FockState = {}
        for p4, a4 in b4.items():
            for pa, aa in anc.items():
                full = (*p4, *tuple(pa))
                if len(full) != n_modes:
                    raise ValueError("ancilla pattern length must be n_modes - 4")
                state[full] = a4 * aa
        out[label] = state
    return out


@dataclass(frozen=True)
class BellScheme:
    n_modes: int
    n_ancilla_photons: int
    ancilla: FockState          # patterns on modes 4..m-1; {} means no ancilla
    mesh: Mesh

    def validate(self) -> None:
        if self.n_modes < 4:
            raise ValueError("a Bell scheme needs at least the 4 dual-rail modes")
        if self.mesh.n_modes != self.n_modes:
            raise ValueError("mesh/scheme mode mismatch")
        if self.ancilla:
            norm = sum(abs(a) ** 2 for a in self.ancilla.values())
            # NaN-proof form: a NaN amplitude makes the norm NaN, and the
            # naive `> 1e-9` comparison is False for NaN -- inverting keeps
            # a malformed input from riding through to a vacuous PASS.
            if not (abs(norm - 1.0) <= 1e-9):
                raise ValueError("ancilla not normalized")
            for pat in self.ancilla:
                # Screen BEFORE the sum check: a negative entry can cancel in
                # the photon sum (e.g. (-1, 2) sums to k=1) and would otherwise
                # only surface as an engine raise -- which the agreed verifier
                # classifies as stop-the-world ERROR, not INVALID.
                if any(p < 0 for p in pat):
                    raise ValueError(
                        "ancilla pattern occupations must be non-negative"
                    )
                if len(pat) != self.n_modes - 4:
                    raise ValueError("ancilla pattern on wrong number of modes")
                if sum(pat) != self.n_ancilla_photons:
                    raise ValueError("ancilla photon number mismatch")
        else:
            if self.n_ancilla_photons != 0:
                raise ValueError("k > 0 requires an ancilla state")
            if self.n_modes > 4:
                raise ValueError(
                    "n_modes > 4 requires an explicit ancilla state "
                    "(use a zero-photon pattern for vacuum modes)"
                )


def scheme_from_out(out) -> BellScheme:
    """Convert a model-facing scheme description into a validated `BellScheme`.

    `out` is duck-typed to `llm.schemas.BellSchemeOut` rather than imported
    directly: the domain layer must never import `llm` (layering runs
    llm -> domain, never the reverse -- see `search/schemas.py`'s identical
    choice for `to_construction`). Any object exposing the same shape works:
    `n_modes`, `n_ancilla_photons`, `ancilla` (a sequence of objects with
    `.pattern`/`.re`/`.im`), `mesh` (a sequence of objects with
    `.kind`/`.i`/`.j`/`.theta`/`.phi`).

    Per the M4 discipline this converter does no physics validation of its
    own: it defers entirely to `Mesh.__post_init__` and `BellScheme.validate`
    -- but it DOES call `validate()` before returning, so a malformed scheme
    fails fast here, at conversion time, rather than surfacing later inside
    `verify_scheme_agreed`. `ValueError` propagates to the caller uncaught
    (the campaign loop's millisecond screen tier is what catches it).
    """
    elements: list[tuple] = []
    for el in out.mesh:
        if el.kind == "bs":
            elements.append(("bs", el.i, el.j, el.theta, el.phi))
        else:  # "phase" (the only other kind BellSchemeOut/MeshElement allows)
            elements.append(("phase", el.i, el.theta))
    mesh = Mesh(n_modes=out.n_modes, elements=tuple(elements))
    ancilla = {tuple(term.pattern): complex(term.re, term.im) for term in out.ancilla}
    scheme = BellScheme(
        n_modes=out.n_modes,
        n_ancilla_photons=out.n_ancilla_photons,
        ancilla=ancilla,
        mesh=mesh,
    )
    scheme.validate()
    return scheme


@dataclass(frozen=True)
class SchemeReport:
    success_by_state: dict[str, float]
    p_min: float
    p_avg: float
    # Total probability mass on assigned patterns attributable to non-assigned
    # Bell states -- an upper bound on the misidentification probability; a
    # published claim must carry it.
    leakage: float
    unambiguous: bool           # derived: leakage <= _LEAK_FLOOR
    distributions: dict[str, dict[tuple[int, ...], float]]


def derive_assignment(
    distributions: dict[str, dict[tuple[int, ...], float]],
) -> dict[tuple[int, ...], str]:
    """Derive the unique-label assignment from one engine's distributions.

    Only uniquely-supported patterns appear in the returned mapping. Keeping
    this operation explicit lets the agreed verifier compare the two engines'
    *semantic* assignments, rather than treating numerically-close
    distributions on opposite sides of ``_AMBIG_TOL`` as agreement.
    """
    all_patterns = set().union(*(distributions[b] for b in BELL_LABELS))
    assignment: dict[tuple[int, ...], str] = {}
    for pat in all_patterns:
        supported = [
            b for b in BELL_LABELS if distributions[b].get(pat, 0.0) > _AMBIG_TOL
        ]
        if len(supported) == 1:
            assignment[pat] = supported[0]
    return assignment


def report_from_distributions(
    distributions: dict[str, dict[tuple[int, ...], float]],
) -> SchemeReport:
    """Compute assignment-derived metrics from a complete Bell distribution map."""
    assignment = derive_assignment(distributions)
    success = dict.fromkeys(BELL_LABELS, 0.0)
    leakage = 0.0
    for pat, winner in assignment.items():
        probs = {b: distributions[b].get(pat, 0.0) for b in BELL_LABELS}
        success[winner] += probs[winner]
        leakage += sum(probs[b] for b in BELL_LABELS if b != winner)
    p_min = min(success.values())
    p_avg = sum(success.values()) / 4.0
    return SchemeReport(
        success_by_state=success,
        p_min=p_min,
        p_avg=p_avg,
        leakage=leakage,
        unambiguous=leakage <= _LEAK_FLOOR,
        distributions=distributions,
    )


def evaluate_scheme(scheme: BellScheme, engine) -> SchemeReport:
    scheme.validate()
    dists = {
        label: engine.output_distribution(scheme.mesh, state)
        for label, state in bell_input_states(scheme.n_modes, scheme.ancilla).items()
    }
    return report_from_distributions(dists)

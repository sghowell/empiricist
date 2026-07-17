"""Exactly-known Bell-measurement schemes — the golden physics pins.

These constructions reproduce published success vectors exactly. Per design
decision D4 the published vector IS the spec: a construction that misses its
vector is a mesh bug to be fixed against the paper's physics, never a golden to
be relaxed. Each scheme here is a fixed, documented interferometer whose
per-Bell-state success vector is pinned by tests/test_p3_goldens.py.

Dual-rail convention (see scheme.py): qubit A on rails 0,1; qubit B on rails
2,3; ancilla (if any) on modes 4..m-1. Beamsplitter convention (see
interferometer.py): bs(i, j, theta, phi) with a†_i -> cos(theta) a†_i +
e^{i phi} sin(theta) a†_j. All elements below are 50:50 (theta = pi/4, phi = 0).
"""

from __future__ import annotations

from math import pi, sqrt

from .interferometer import Mesh
from .scheme import BellScheme

_BS = pi / 4  # 50:50 beamsplitter angle


def _bs(i: int, j: int) -> tuple[str, int, int, float, float]:
    return ("bs", i, j, _BS, 0.0)


def standard_bsm() -> BellScheme:
    """The textbook linear-optical Bell-state measurement (no ancilla).

    A 50:50 beamsplitter between each pair of corresponding rails —
    bs(0,2) mixes the two logical-0 rails, bs(1,3) the two logical-1 rails.

    Physics: psi+ and psi- send their two photons into DIFFERENT beamsplitters
    (one photon to bs(0,2), one to bs(1,3)); they never bunch and land on
    distinct single-photon detection patterns, so both are identified with
    certainty. phi+ and phi- send both photons into the SAME beamsplitter and
    HOM-bunch: phi+ -> (|2000> - |0020> + |0200> - |0002>)/2 and
    phi- -> (|2000> - |0020> - |0200> + |0002>)/2. Those two states carry the
    phi+/phi- sign only as a relative phase between disjoint detection
    patterns, which is invisible to photon-number-resolving detectors: both
    give the identical counting distribution (each doubled pattern w.p. 1/4).
    Hence phi+ and phi- are mutually ambiguous.

    Per-Bell-state success = (phi+, phi-, psi+, psi-) = (0, 0, 1, 1);
    p_avg = 1/2, p_min = 0, leakage = 0. (The classic linear-optics ceiling.)
    """
    return BellScheme(
        n_modes=4,
        n_ancilla_photons=0,
        ancilla={},
        mesh=Mesh(n_modes=4, elements=(_bs(0, 2), _bs(1, 3))),
    )


def grice_boosted_bsm() -> BellScheme:
    """Grice's ancilla-boosted Bell measurement — PRA 84, 042331 (2011).

    One Bell-pair ancilla lifts the average success from 1/2 to 3/4 by resolving
    the phi+/phi- ambiguity of the standard BSM half of the time, while leaving
    psi+ and psi- perfectly measured. Published vector (exact):
    per-state (phi+, phi-, psi+, psi-) = (1/2, 1/2, 1, 1), p_avg = 3/4,
    p_min = 1/2, leakage = 0.

    Ancilla: a dual-rail |Phi+> = (|1,0,1,0> + |0,1,0,1>)/sqrt(2) on modes 4-7
    (ancilla qubit A' on rails 4,5; ancilla qubit B' on rails 6,7), two photons.

    Mesh — three 50:50 layers, in order:
      1. input BSM     bs(0,2), bs(1,3)   — the standard measurement on the pair
      2. ancilla BSM   bs(4,6), bs(5,7)   — the same measurement on the ancilla
      3. rail coupling bs(0,4), bs(1,5), bs(2,6), bs(3,7)
                                          — each input rail meets its ancilla rail

    Physics of why this works. The standard BSM (layer 1) HOM-bunches the input
    phi+/phi- into the four doubled patterns above, encoding the phi sign in an
    UNmeasurable relative phase. The ancilla, itself a phi+ pair, is bunched the
    same way by layer 2. Layer 3 interferes each doubled input amplitude with
    the matching doubled ancilla amplitude: this four-photon interference
    converts the previously-invisible phi sign into a genuine population
    difference on half of the coincidence classes. Those events now discriminate
    phi+ from phi- outright; the other half remain ambiguous — giving success
    exactly 1/2 for each of phi+ and phi-. The psi states never bunched, carry
    no ambiguous phase, and stay at success 1. Net (1/2, 1/2, 1, 1), avg 3/4.

    (The exact layer choice was fixed by iterating against the published vector:
    the ancilla-internal BSM layer and the FULL four-rail coupling — not an
    A-side-only coupling, which yields (1/8, 1/8, 1, 1) — are both required to
    land on (1/2, 1/2, 1, 1). Layer order among the three is immaterial to the
    vector; this order is the physically legible one.)
    """
    r2 = 1.0 / sqrt(2)
    return BellScheme(
        n_modes=8,
        n_ancilla_photons=2,
        ancilla={(1, 0, 1, 0): r2, (0, 1, 0, 1): r2},
        mesh=Mesh(
            n_modes=8,
            elements=(
                _bs(0, 2), _bs(1, 3),                          # input BSM
                _bs(4, 6), _bs(5, 7),                          # ancilla BSM
                _bs(0, 4), _bs(1, 5), _bs(2, 6), _bs(3, 7),    # rail coupling
            ),
        ),
    )

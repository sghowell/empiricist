"""Canonicalization: pynauty iso-certificates and the LC-orbit canonical key.

pynauty.certificate() is McKay canonical labeling -- a TRUE isomorphism certificate
(equal iff isomorphic). WL-hash / VF2 are NOT certificates and must never be used
here. The LC-orbit canonical key (spec D5) is the LEXICOGRAPHICALLY MINIMUM iso-
certificate taken over the whole LC orbit: it is invariant across the orbit, so it
is the identity under which F(G) is well-defined and the population dedups.

Verified against the installed pynauty 2.8.8.1 API (see comment on `_to_pynauty`):
`pynauty.Graph(n, directed=False, adjacency_dict=adj)` + `pynauty.certificate(g)`
returns `bytes`, equal iff isomorphic (empirically confirmed: two labelings of the
same path give equal certificates; a path and a triangle on the same n do not).
"""

from __future__ import annotations

import pynauty

from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.localcomp import DEFAULT_ORBIT_CAP, lc_orbit


def _to_pynauty(gs: GraphState) -> pynauty.Graph:
    """Build the pynauty.Graph for gs. adjacency_dict must list EVERY vertex
    (including isolated ones) or pynauty raises/misbehaves on vertex count."""
    adj: dict[int, list[int]] = {v: [] for v in range(gs.n)}
    for a, b in gs.edges:
        adj[a].append(b)
        adj[b].append(a)
    return pynauty.Graph(gs.n, directed=False, adjacency_dict=adj)


def iso_certificate(gs: GraphState) -> bytes:
    """McKay canonical certificate: equal iff the graphs are isomorphic."""
    return pynauty.certificate(_to_pynauty(gs))


def lc_orbit_key(gs: GraphState, *, cap: int | None = None) -> str:
    """The LC-orbit canonical key as a hex string -- the single dedup identity
    for the population/frontier (the ledger stores it as TEXT PRIMARY KEY).

    The min iso-certificate over the LC orbit, hex-encoded. Invariant under BOTH
    local complementation AND vertex relabeling (the Adcock orbit-count match
    proves this); the certificate length encodes n, so keys for different n never
    collide. `cap=None` uses lc_orbit's own default (DEFAULT_ORBIT_CAP).
    """
    resolved_cap = DEFAULT_ORBIT_CAP if cap is None else cap
    return min(iso_certificate(g) for g in lc_orbit(gs, cap=resolved_cap)).hex()


def lc_equivalent(a: GraphState, b: GraphState) -> bool:
    """True iff a and b are LC-equivalent (same vertex count and orbit key)."""
    if a.n != b.n:
        return False
    return lc_orbit_key(a) == lc_orbit_key(b)

"""The Construction artifact (spec Appendix E) and its apply() on both engines."""

import random

import networkx as nx
import pytest

from empiricist.domain.p5.canonical import iso_certificate, lc_orbit_key
from empiricist.domain.p5.construction import (
    Construction,
    FusionOp,
    LocalComplement,
    apply_construction,
    apply_local_complement,
    build_workspace,
)
from empiricist.domain.p5.fusion_gf2 import GF2Engine
from empiricist.domain.p5.fusion_stim import StimEngine
from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.localcomp import local_complement
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Verdict
from empiricist.verifiers.enum_fusion import EnumFusionVerifier
from empiricist.verifiers.registry import Registry, verify_agreed
from empiricist.verifiers.stab_fusion import StabFusionVerifier


def _random_connected_graph(rng, n):
    while True:
        edges = [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < 0.5]
        gs = GraphState(n=n, edges=edges)
        if nx.is_connected(gs.to_networkx()):
            return gs


def test_workspace_is_ghz3_stars():
    ws = build_workspace(resources=2)
    assert ws.n == 6
    assert ws.edges == frozenset({(0, 1), (0, 2), (3, 4), (3, 5)})


def test_p4_construction_verifies_on_both_engines():
    c = Construction(
        resources=2,
        steps=(FusionOp(a=2, b=4),),
        target=GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)]),
    )
    for eng in (StimEngine(), GF2Engine()):
        out = apply_construction(c, eng)
        assert lc_orbit_key(out) == lc_orbit_key(c.target)
    assert c.fusion_count == 1


def test_wrong_target_fails_verification():
    c = Construction(
        resources=2,
        steps=(FusionOp(a=2, b=4),),
        target=GraphState(n=4, edges=[(0, 1), (0, 2), (0, 3)]),  # star, NOT P4's orbit
    )
    out = apply_construction(c, StimEngine())
    assert lc_orbit_key(out) != lc_orbit_key(c.target)


def test_construction_rejects_wrong_target_size():
    with pytest.raises(ValueError):
        Construction(
            resources=2,
            steps=(FusionOp(a=2, b=4),),
            target=GraphState(n=5, edges=[]),
        )  # 3*2-2*1 = 4 != 5


def test_construction_local_complement_step_does_not_count_toward_size():
    # 2 resources, 1 FusionOp + 1 LocalComplement -> still n=4 (3*2 - 2*1)
    c = Construction(
        resources=2,
        steps=(FusionOp(a=1, b=3), LocalComplement(v=0)),
        target=GraphState(n=4, edges=[]),
    )
    assert c.fusion_count == 1


@pytest.mark.parametrize("seed", range(10))
@pytest.mark.parametrize("eng_cls", [StimEngine, GF2Engine])
def test_engine_local_complement_matches_graph_rule(seed, eng_cls):
    """A1's replay mechanism (`apply_local_complement`), applied directly to
    a FRESH engine state, must reproduce the plain graph-level tau_v rule
    (localcomp.local_complement) exactly -- for BOTH engines independently."""
    rng = random.Random(4000 + seed)
    n = rng.randint(4, 7)
    gs = _random_connected_graph(rng, n)
    v = rng.randrange(n)

    engine = eng_cls()
    state = engine.state_from_graph(gs)
    new_state = apply_local_complement(engine, state, v)
    out = engine.to_graphstate(new_state)

    expected = local_complement(gs, v)
    assert iso_certificate(out) == iso_certificate(expected)


def test_construction_with_lc_steps_verifies(tmp_path):
    """The A1 finding, end to end: a mid-schedule LocalComplement step
    changes the reached orbit (found by an exhaustive search over small
    resources=3 schedules), and a Construction carrying that step PASSES
    verify_agreed (both independent engines certify it), while the SAME
    steps without the LocalComplement land in a genuinely different orbit.
    """
    with_lc_steps = (FusionOp(a=0, b=3), LocalComplement(v=4), FusionOp(a=1, b=6))
    without_lc_steps = (FusionOp(a=0, b=3), FusionOp(a=1, b=6))
    placeholder = GraphState(n=5, edges=[])  # 3*3 - 2*2 = 5; steps only validated by size

    probe = Construction(resources=3, steps=with_lc_steps, target=placeholder)
    stim_out = apply_construction(probe, StimEngine())
    gf2_out = apply_construction(probe, GF2Engine())
    assert lc_orbit_key(stim_out) == lc_orbit_key(gf2_out), (
        "both engines must independently agree on the LC-interleaved schedule's orbit"
    )

    without_probe = Construction(resources=3, steps=without_lc_steps, target=placeholder)
    without_out = apply_construction(without_probe, StimEngine())
    assert lc_orbit_key(stim_out) != lc_orbit_key(without_out), (
        "the LocalComplement step must be causally relevant -- removing it must "
        "change the reached orbit (otherwise this isn't a real A1 test case)"
    )

    real = Construction(resources=3, steps=with_lc_steps, target=stim_out)
    ledger = Ledger(tmp_path / "ledger.db")
    try:
        registry = Registry(ledger)
        registry.certify(StabFusionVerifier())
        registry.certify(EnumFusionVerifier())
        result = verify_agreed(registry, real)
    finally:
        ledger.close()

    assert result.verdict == Verdict.PASS
    assert result.details["stab_fusion_key"] == result.details["enum_fusion_key"]

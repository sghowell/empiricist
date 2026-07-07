"""The Construction artifact (spec Appendix E) and its apply() on both engines."""

import pytest

from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.construction import (
    Construction,
    FusionOp,
    apply_construction,
    build_workspace,
)
from empiricist.domain.p5.fusion_gf2 import GF2Engine
from empiricist.domain.p5.fusion_stim import StimEngine
from empiricist.domain.p5.graphstate import GraphState


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

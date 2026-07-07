"""P5_GOLDEN_SUITE: the mutation-resistant certification suite (spec §7)
that every fusion verifier must pass -- exactly, case by case -- to earn a
PASS stamp from `registry.Registry.certify()`.

Cases: the P4 pair-fusion construction (plan header golden: GHZ3 x GHZ3 fused
leaf-to-leaf) and the g=3,4,5 leaf-to-leaf chains (each yields P_{g+2}, the
F(path)=N-3 achievability witness) -- all must PASS -- plus one wrong-target
case that must FAIL. A suite that can't fail certifies nothing: a verifier
that always says PASS would sail through a suite with only PASS cases, so the
must-fail case is not optional decoration, it's the suite's actual teeth.

`suite_hash()` is a blake3 digest of a canonical (JSON) repr of the suite;
`registry.Registry.verify()` pins every certification stamp to this exact
hash, so editing the suite (adding/removing/changing a case) invalidates
every existing stamp rather than letting a certification earned against a
DIFFERENT suite silently continue to read as trust.
"""

from __future__ import annotations

import json

from blake3 import blake3

from empiricist.domain.p5.construction import Construction, FusionOp
from empiricist.domain.p5.graphstate import GraphState


def _chain(g: int) -> Construction:
    """g GHZ3 stars chained leaf-to-leaf (g-1 fusions) -> target P_{g+2}."""
    steps = tuple(FusionOp(a=3 * i + 2, b=3 * (i + 1) + 1) for i in range(g - 1))
    target = GraphState(n=g + 2, edges=[(i, i + 1) for i in range(g + 1)])
    return Construction(resources=g, steps=steps, target=target)


_P4 = Construction(
    resources=2,
    steps=(FusionOp(a=2, b=4),),
    target=GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)]),
)

# Same recipe as _P4, but the wrong target orbit (a star, not P4's path) --
# the must-fail case: no verifier earns a stamp without correctly FAILING this.
_WRONG_TARGET = Construction(
    resources=2,
    steps=(FusionOp(a=2, b=4),),
    target=GraphState(n=4, edges=[(0, 1), (0, 2), (0, 3)]),
)

P5_GOLDEN_SUITE: list[tuple[Construction, bool]] = [
    (_P4, True),
    (_chain(3), True),
    (_chain(4), True),
    (_chain(5), True),
    (_WRONG_TARGET, False),
]


def suite_hash() -> str:
    """blake3 hex digest of a canonical JSON repr of P5_GOLDEN_SUITE (each
    case's resources, fusion steps, target edges, and expected outcome)."""
    canon = [
        {
            "resources": construction.resources,
            "steps": [[op.a, op.b] for op in construction.steps],
            "target_n": construction.target.n,
            "target_edges": sorted(construction.target.edges),
            "expected_pass": expected,
        }
        for construction, expected in P5_GOLDEN_SUITE
    ]
    payload = json.dumps(canon, sort_keys=True, separators=(",", ":"))
    return blake3(payload.encode("utf-8")).hexdigest()

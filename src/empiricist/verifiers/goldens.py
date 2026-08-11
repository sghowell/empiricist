"""P5_GOLDEN_SUITE: the mutation-resistant certification suite (spec §7)
that every fusion verifier must pass -- exactly, case by case -- to earn a
PASS stamp from `registry.Registry.certify()`.

Cases: the P4 pair-fusion construction (plan header golden: GHZ3 x GHZ3 fused
leaf-to-leaf), the g=3,4,5 leaf-to-leaf chains (each yields P_{g+2}, the
F(path)=N-3 achievability witness), and two intra-component constructions
(one closing a cycle, one fusing adjacent qubits -- the latter is what
certification-gates engine B's deterministic-measurement branch; see the
comments on each) -- all must PASS -- plus one wrong-target case that must
FAIL. A suite that can't fail certifies nothing: a verifier that always says
PASS would sail through a suite with only PASS cases, so the must-fail case
is not optional decoration, it's the suite's actual teeth.

`suite_hash()` is a blake3 digest of a canonical (JSON) repr of the suite;
`registry.Registry.verify()` pins every certification stamp to this exact
hash, so editing the suite (adding/removing/changing a case) invalidates
every existing stamp rather than letting a certification earned against a
DIFFERENT suite silently continue to read as trust.

NOTE (M5c): binary_hash covers verifier+engine source but NOT the shared M5a
modules (canonical/localcomp/graphstate) both engines depend on -- the shared
canonicalizer is the residual single point of failure, trusted on the Adcock
goldens. M5c should consider extending the hash to the shared closure.
"""

from __future__ import annotations

import json

from blake3 import blake3

from empiricist.domain.p5.construction import Construction, FusionOp
from empiricist.domain.p5.graphstate import GraphState
from empiricist.ledger.models import Verdict


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

# Intra-component goldens. Both start from the g=3 chain (fusions (2,4) then
# (5,7) merge the three stars into ONE component: P5 in path order
# 1-0-3-6-8), then apply a third, INTRA-component fusion. Targets were
# computed by running both engines (they agree; instrumented in the M5b
# closeout review) and pinned here.
#
# (a) Cycle-close: fuse the P5's two ENDPOINT qubits (1, 8). Exercises the
# general intra-component random-measurement path (both fusion observables
# anticommute with some generator). Result on the survivors {0, 3, 6},
# relabelled (0, 1, 2): the triangle -- the connected 3-vertex orbit
# (LC-equivalent to P3 / the GHZ3 star).
_INTRA_CYCLE_CLOSE = Construction(
    resources=3,
    steps=(FusionOp(a=2, b=4), FusionOp(a=5, b=7), FusionOp(a=1, b=8)),
    target=GraphState(n=3, edges=[(0, 1), (0, 2), (1, 2)]),
)

# (b) Adjacent-qubit fusion: fuse the P5's endpoint 1 with its NEIGHBOR 0.
# For adjacent qubits one of the two fusion observables {X_a Z_b, Z_a X_b}
# is already (signs ignored) in the stabilizer group, so this golden drives
# engine B's DETERMINISTIC-measurement branch (_measure's no-anticommuting
# no-op path -- the previously-broken path fixed in the A/B fuzz, commit
# 8293edb): verified by instrumentation to fire exactly once here, so a
# regression on that branch can no longer earn a certification stamp.
# (The cycle-close golden above does NOT hit that branch -- also
# instrumented -- which is why this second intra-component case exists.)
# Result on the survivors {3, 6, 8}, relabelled (0, 1, 2): the single edge
# (1, 2) with vertex 0 isolated.
_INTRA_ADJACENT = Construction(
    resources=3,
    steps=(FusionOp(a=2, b=4), FusionOp(a=5, b=7), FusionOp(a=0, b=1)),
    target=GraphState(n=3, edges=[(1, 2)]),
)

P5_GOLDEN_SUITE: list[tuple[Construction, Verdict]] = [
    (_P4, Verdict.PASS),
    (_chain(3), Verdict.PASS),
    (_chain(4), Verdict.PASS),
    (_chain(5), Verdict.PASS),
    (_INTRA_CYCLE_CLOSE, Verdict.PASS),
    (_INTRA_ADJACENT, Verdict.PASS),
    (_WRONG_TARGET, Verdict.FAIL),
]


def suite_hash() -> str:
    """blake3 hex digest of a canonical JSON repr of P5_GOLDEN_SUITE (each
    case's resources, fusion steps, target edges, and expected verdict)."""
    canon = [
        {
            "resources": construction.resources,
            "steps": [[op.a, op.b] for op in construction.steps],
            "target_n": construction.target.n,
            "target_edges": sorted(construction.target.edges),
            "expected_verdict": expected.value,
        }
        for construction, expected in P5_GOLDEN_SUITE
    ]
    payload = json.dumps(canon, sort_keys=True, separators=(",", ":"))
    return blake3(payload.encode("utf-8")).hexdigest()

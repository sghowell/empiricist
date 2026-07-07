"""M6 T5 end-to-end integration test: ONE real generation through the FULL
stack, with every layer real except the model process itself.

Real Ledger + Store + Registry (both fusion verifiers certified) + real
Population, driven by `SearchLoop.run_generation` against a REAL
`ClaudeCodeClient` pointed at the stub `claude` binary
(tests/stub_claude.py, STUB_MODE=construction) instead of `FakeLLMClient`.
This is the one test in the suite that exercises the actual
subprocess -> envelope parse -> pydantic schema -> screen ->
verify_agreed(certified registry) -> population chain end to end, without a
real model call (that is M9's live smoke).

The stub's canned payload is the same P4 fixture used throughout
tests/test_search_loop.py: resources=2 GHZ3 stars, one fuse (leaf 2 with
leaf 4), claiming the resulting 4-path. Since STUB_MODE=construction always
emits the identical envelope, a k=2 wave produces exactly one NEW population
key (first candidate) and one duplicate hit (second candidate) -- enough to
prove `report.inserted >= 1` without needing prompt-level variation from the
stub (the stub has no model to vary; diversity in a live run comes from the
nonce in the prompt per `SearchLoop.build_prompt`, spec §9).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.construction import Construction, FusionOp
from empiricist.domain.p5.graphstate import GraphState
from empiricist.ledger.db import Ledger
from empiricist.llm.client import ClaudeCodeClient
from empiricist.search.database import Population
from empiricist.search.loop import SearchLoop, TargetSpec
from empiricist.store import Store
from empiricist.verifiers.enum_fusion import EnumFusionVerifier
from empiricist.verifiers.registry import Registry
from empiricist.verifiers.stab_fusion import StabFusionVerifier

STUB = Path(__file__).parent / "stub_claude.py"

# The P4 construction the stub's STUB_MODE=construction envelope encodes:
# resources=2 GHZ3 stars (qubits 0,1,2 and 3,4,5), fuse leaf 2 with leaf 4 ->
# a 4-path on the surviving qubits {0,1,3,5}. Matches tests/test_search_loop.py.
P4_CONSTRUCTION = Construction(
    resources=2, steps=(FusionOp(a=2, b=4),),
    target=GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)]),
)
P4_KEY = lc_orbit_key(P4_CONSTRUCTION.target)


def run(coro):
    return asyncio.run(coro)


def test_stub_claude_end_to_end_generation(tmp_path, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "construction")

    ledger = Ledger(tmp_path / "ledger.db")
    store = Store(tmp_path / "store")
    registry = Registry(ledger)
    registry.certify(StabFusionVerifier())
    registry.certify(EnumFusionVerifier())
    population = Population(ledger)

    client = ClaudeCodeClient(claude_bin=[sys.executable, str(STUB)])
    loop = SearchLoop(client, ledger, store, registry, population)

    target = TargetSpec(
        n=4, lc_orbit_key=P4_KEY, representative_edges=((0, 1), (1, 2), (2, 3)),
        known_bound="F >= 4 (Tier-0 unreachable)", target_f=1,
    )

    try:
        report = run(loop.run_generation(gen=1, targets=[target], k=2))

        # -- the full chain produced a real, certified improvement --
        assert report.sampled == 2
        assert report.screened_out == 0
        assert report.verify_error == 0
        assert report.verify_fail == 0
        assert report.inserted >= 1

        # -- population row exists, keyed by the achieved (real, computed) orbit --
        row = population.get(P4_KEY)
        assert row is not None
        assert row.objective_vec == [1]
        assert row.cert_hash is not None
        assert store.get(row.cert_hash)  # the CAS artifact is retrievable

        # -- search_events row exists for this generation --
        events = population.events(trigger="generation")
        assert len(events) == 1
        assert events[0].gen == 1
        assert events[0].detail["inserted"] >= 1
    finally:
        ledger.close()

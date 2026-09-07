"""`reverify` for P5 construction witnesses (M23b Task 4): July's HEURISTIC exact
upgrades become CERTIFIED claims under the live engines."""
from __future__ import annotations

import json
from dataclasses import asdict

from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.reverify import reverify_construction_artifacts
from empiricist.ledger.db import Ledger
from empiricist.ledger.ingest import ingest_artifact
from empiricist.ledger.models import EvidenceRow, Status, Verdict
from empiricist.search.loop import TargetSpec
from empiricist.store import Store
from empiricist.verifiers.enum_fusion import EnumFusionVerifier
from empiricist.verifiers.registry import Registry
from empiricist.verifiers.stab_fusion import StabFusionVerifier

P4_DICT = {
    "resources": 2,
    "steps": [{"op": "fuse", "args": [2, 4]}],
    "target_n": 4,
    "target_edges": [[0, 1], [1, 2], [2, 3]],
}
P4_KEY = lc_orbit_key(GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)]))


def _july_style_witness(lg, st, *, target_f=1, upgrade=True):
    """A construction recorded the pre-M23b way: HEURISTIC + a verify_agreed PASS row."""
    content = json.dumps(P4_DICT, sort_keys=True, separators=(",", ":")).encode()
    art = ingest_artifact(lg, st, content=content, kind="construction", problem="P5",
                          problem_version="p5-ghz3-v1", title="SEARCH exact upgrade: orbit 0000",
                          status=Status.HEURISTIC)
    target = TargetSpec(n=4, lc_orbit_key=P4_KEY, representative_edges=((0, 1), (1, 2), (2, 3)),
                        known_bound="F >= 1", target_f=target_f)
    details = {"achieved_key": P4_KEY, "f": 1, "target": asdict(target),
               "stab_fusion_id": "stab_fusion@1.0:x", "enum_fusion_id": "enum_fusion@1.0:x"}
    if upgrade:
        details["upgrade"] = True
    lg.record_evidence(EvidenceRow(artifact_id=art.id, verifier="verify_agreed",
                                   verifier_version="1.0", binary_hash="old" * 10,
                                   verdict=Verdict.PASS, details=details))
    return art


def test_reverify_promotes_a_july_exact_upgrade_to_certified(tmp_path):
    lg, st = Ledger(tmp_path / "ledger.db"), Store(tmp_path / "store")
    art = _july_style_witness(lg, st)
    rep = reverify_construction_artifacts(lg, st)
    assert rep.certified_now and rep.ok
    assert [o.detail for o in rep.outcomes] == ["promoted to CERTIFIED"]
    assert lg.get_artifact(art.id).status is Status.CERTIFIED
    claims = lg.claims_for(art.id)
    assert len(claims) == 1 and claims[0].metric == "min_fusions" and claims[0].scope["f"] == 1
    rows = lg.evidence_for(art.id)
    assert len(rows) == 2 and rows[-1].claim_id == claims[0].id
    assert rows[-1].golden_suite_hash is not None and rows[-1].binary_hash != "old" * 10
    # idempotent: a second pass re-verifies under the same identity, mints no second
    # claim and no duplicate evidence row
    rep2 = reverify_construction_artifacts(lg, st)
    assert rep2.ok and not rep2.certified_now
    assert [o.detail for o in rep2.outcomes] == ["re-verified"]
    assert len(lg.claims_for(art.id)) == 1 and len(lg.evidence_for(art.id)) == 2
    lg.close()


def test_reverify_leaves_a_witness_above_the_bound_heuristic(tmp_path):
    lg, st = Ledger(tmp_path / "ledger.db"), Store(tmp_path / "store")
    art = _july_style_witness(lg, st, target_f=4)
    rep = reverify_construction_artifacts(lg, st)
    assert rep.ok and "above the lower bound" in rep.outcomes[0].detail
    assert lg.get_artifact(art.id).status is Status.HEURISTIC
    assert lg.claims_for(art.id) == [] and len(lg.evidence_for(art.id)) == 2
    lg.close()


def test_reverify_targets_only_upgrade_witnesses_and_dry_runs(tmp_path):
    lg, st = Ledger(tmp_path / "ledger.db"), Store(tmp_path / "store")
    Registry(lg).certify(StabFusionVerifier())
    Registry(lg).certify(EnumFusionVerifier())
    _july_style_witness(lg, st, upgrade=False)
    assert reverify_construction_artifacts(lg, st).outcomes == ()
    rep = reverify_construction_artifacts(lg, st, artifact_ids=["nope"])
    assert [o.verdict for o in rep.outcomes] == ["MISSING"]
    lg.close()


def test_reverify_dry_run_writes_nothing(tmp_path):
    lg, st = Ledger(tmp_path / "ledger.db"), Store(tmp_path / "store")
    art = _july_style_witness(lg, st)
    rep = reverify_construction_artifacts(lg, st, dry_run=True)
    assert rep.dry_run and [o.verdict for o in rep.outcomes] == ["SKIPPED"]
    assert lg.get_artifact(art.id).status is Status.HEURISTIC
    assert len(lg.evidence_for(art.id)) == 1
    lg.close()

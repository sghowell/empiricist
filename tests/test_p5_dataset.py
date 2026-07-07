"""The VERIFIED_N dataset artifact tests (M5c Task 3): build_dataset /
to_canonical_json / ingest_dataset -- the harness's first VERIFIED_N
artifact. Small-scale (n_max=6) so the fast suite stays fast; the corruption
tests exercise ingest_dataset's reject-before-any-ledger-write discipline
(a rejected dataset must leave no artifact and no evidence row behind).
"""

from __future__ import annotations

import copy
import json

import pytest

from empiricist.domain.p5.dataset import (
    ADCOCK_TOTALS,
    build_dataset,
    ingest_dataset,
    to_canonical_json,
)
from empiricist.domain.p5.tablebase import tier0_search, tier1_search
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Status, Verdict
from empiricist.store import Store
from empiricist.verifiers.enum_fusion import EnumFusionVerifier
from empiricist.verifiers.registry import Registry
from empiricist.verifiers.stab_fusion import StabFusionVerifier


@pytest.fixture(scope="module")
def small_dataset():
    tier0 = tier0_search(6)
    tier1 = tier1_search(6)
    return build_dataset(tier0, tier1)


def _rows_by_n(dataset):
    by_n = {}
    for row in dataset["rows"]:
        by_n.setdefault(row["n"], []).append(row)
    return by_n


def test_build_dataset_row_counts_match_adcock(small_dataset):
    by_n = _rows_by_n(small_dataset)
    for n in range(3, 7):
        assert len(by_n[n]) == ADCOCK_TOTALS[n]
        assert len({r["orbit_id"] for r in by_n[n]}) == ADCOCK_TOTALS[n]


def test_build_dataset_tier_labels(small_dataset):
    """n=5: 3 tier0 + 1 tier1 (the plan's single resolved open orbit) + 0
    open. n=6: 8 tier0 + 2 tier1 + 1 open (the orbit that stays F>=9)."""
    by_n = _rows_by_n(small_dataset)

    tiers5 = [r["tier"] for r in by_n[5]]
    assert tiers5.count("tier0") == 3
    assert tiers5.count("tier1") == 1
    assert tiers5.count("open") == 0

    tiers6 = [r["tier"] for r in by_n[6]]
    assert tiers6.count("tier0") == 8
    assert tiers6.count("tier1") == 2
    assert tiers6.count("open") == 1


def test_mod3_and_lower_bounds(small_dataset):
    for row in small_dataset["rows"]:
        if row["exact"]:
            assert row["F"] == row["lower_bound"]
            assert row["F"] % 3 == (row["n"] - 3) % 3
            if row["tier"] == "tier0":
                assert row["F"] == row["n"] - 3
            elif row["tier"] == "tier1":
                assert row["F"] == row["n"]
            assert row["witness"] is not None
        else:
            assert row["F"] is None
            assert row["tier"] == "open"
            assert row["witness"] is None
            # n=6's open orbit: Tier-1 exhaustively searched n=6, so the
            # lower bound tightens past Tier-0's floor (n) to n+3.
            assert row["lower_bound"] == row["n"] + 3


def test_canonical_json_roundtrip(small_dataset):
    blob = to_canonical_json(small_dataset)
    assert isinstance(blob, bytes)
    back = json.loads(blob)
    assert back == small_dataset
    # canonical: compact separators, no stray whitespace.
    assert b", " not in blob
    assert b": " not in blob


def test_canonical_json_is_deterministic(small_dataset):
    assert to_canonical_json(small_dataset) == to_canonical_json(copy.deepcopy(small_dataset))


def test_ingest_dataset_creates_verified_n_artifact(small_dataset, tmp_path):
    ledger = Ledger(tmp_path / "ledger.db")
    store = Store(tmp_path / "cas")
    try:
        registry = Registry(ledger)
        registry.certify(StabFusionVerifier())
        registry.certify(EnumFusionVerifier())

        art = ingest_dataset(ledger, store, small_dataset, registry)

        assert art.status == Status.VERIFIED_N
        assert art.status_n == 6
        assert art.coverage == "exhaustive"
        assert art.kind == "dataset"
        assert store.get(art.content_path) == to_canonical_json(small_dataset)

        fetched = ledger.get_artifact(art.id)
        assert fetched.status == Status.VERIFIED_N
        assert fetched.status_n == 6
        assert fetched.coverage == "exhaustive"

        evidence = ledger.evidence_for(art.id)
        assert len(evidence) >= 1
        assert all(e.verdict == Verdict.PASS for e in evidence)
        assert evidence[0].details["exact_rows_verified"] == sum(
            1 for r in small_dataset["rows"] if r["exact"]
        )
    finally:
        ledger.close()


def test_ingest_dataset_rejects_mod3_corruption(small_dataset, tmp_path):
    """Bump one tier0 row's F by 1 -- breaks F === N-3 (mod 3) (and, more
    specifically here, the tier0-exact-F check) -- must be REJECTED before
    any ledger write."""
    corrupted = copy.deepcopy(small_dataset)
    bumped = False
    for row in corrupted["rows"]:
        if row["tier"] == "tier0" and row["n"] == 6:
            row["F"] += 1
            bumped = True
            break
    assert bumped

    ledger = Ledger(tmp_path / "ledger_mod3.db")
    store = Store(tmp_path / "cas_mod3")
    try:
        registry = Registry(ledger)
        registry.certify(StabFusionVerifier())
        registry.certify(EnumFusionVerifier())

        with pytest.raises(ValueError):
            ingest_dataset(ledger, store, corrupted, registry)

        n_artifacts = ledger.conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
        assert n_artifacts == 0
        n_evidence = ledger.conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
        assert n_evidence == 0
    finally:
        ledger.close()


def test_ingest_dataset_rejects_wrong_witness(small_dataset, tmp_path):
    """Swap the `steps` between two DIFFERENT n=6 tier0 orbits' witnesses
    (leaving each row's own target/F/representative untouched, so the
    pre-verify_agreed target/fusion-count consistency checks both still
    pass) -- the swapped-in steps genuinely reach a DIFFERENT orbit, so
    verify_agreed must FAIL and ingestion must REJECT the whole dataset."""
    corrupted = copy.deepcopy(small_dataset)
    tier0_n6 = [r for r in corrupted["rows"] if r["n"] == 6 and r["tier"] == "tier0"]
    assert len(tier0_n6) >= 2
    a, b = tier0_n6[0], tier0_n6[1]
    assert a["orbit_id"] != b["orbit_id"]
    a["witness"]["steps"], b["witness"]["steps"] = b["witness"]["steps"], a["witness"]["steps"]

    ledger = Ledger(tmp_path / "ledger_witness.db")
    store = Store(tmp_path / "cas_witness")
    try:
        registry = Registry(ledger)
        registry.certify(StabFusionVerifier())
        registry.certify(EnumFusionVerifier())

        with pytest.raises(ValueError):
            ingest_dataset(ledger, store, corrupted, registry)

        n_artifacts = ledger.conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
        assert n_artifacts == 0
        n_evidence = ledger.conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
        assert n_evidence == 0
    finally:
        ledger.close()


def test_build_dataset_full_range_past_n7():
    """M5c Task 4 gap fix, end-to-end: build_dataset must succeed for a
    Tier0Result reaching past n=7 (previously this raised ValueError, since
    `unreachable_representatives` was only materialized for n<=7). n=7,8
    have no Tier-1 pass here (tier1.n_max=6), so every one of their
    non-tier0 orbits must land as an "open" row with a REAL representative
    and lower_bound == n (Tier-0's L2 floor only -- Tier-1 never searched
    that far, so the bound can't tighten to n+3)."""
    tier1_6 = tier1_search(6)  # tier1_6.tier0.n_max == 6+2 == 8 (L4 transient)
    dataset = build_dataset(tier1_6.tier0, tier1_6)

    by_n = _rows_by_n(dataset)
    for n in range(3, 9):
        assert len(by_n[n]) == ADCOCK_TOTALS[n]
        assert len({r["orbit_id"] for r in by_n[n]}) == ADCOCK_TOTALS[n]

    for row in by_n[7] + by_n[8]:
        assert row["tier"] in ("tier0", "open")
        if row["tier"] == "open":
            assert row["lower_bound"] == row["n"]
            assert row["representative_edges"]  # a real representative, not a placeholder


def test_build_dataset_rejects_unmaterialized_n():
    """build_dataset's defensive check: an incompletely-materialized
    `unreachable_representatives` list (fewer representatives than
    `unreachable_count` for some n) must raise rather than silently produce
    a dataset missing open rows.

    Since the M5c Task 4 fix, `tier0_search` materializes representatives
    for EVERY n <= n_max (not just n<=7), so this scenario no longer arises
    naturally -- this test exercises build_dataset's own defensive check
    directly by corrupting a Tier0Result's bookkeeping (Tier0Result is a
    plain, non-frozen dataclass; this is not a mutation the public API ever
    performs, just a way to reach the check)."""
    from empiricist.domain.p5.tablebase import Tier1Result

    tier0_6 = tier0_search(6)
    assert tier0_6.unreachable_representatives[6], "sanity: n=6 must have open orbits to truncate"
    tier0_6.unreachable_representatives[6] = tier0_6.unreachable_representatives[6][:-1]
    fake_tier1 = Tier1Result(n_max=6, transient_max=8, tier0=tier0_6, newly_resolved={})
    with pytest.raises(ValueError):
        build_dataset(tier0_6, fake_tier1)

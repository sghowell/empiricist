"""Tier-0 tablebase tests (M5c Task 2): the all-merge reachability BFS.

Small-n exactness is checked against the Adcock connected-orbit counts
(1,1,1,2,4,11,26,101,440 for n=3..9 -- see tests/test_p5_canonical.py); the
n=7 split (15 reachable / 11 unreachable) and the n=8/9 totals (101, 440)
are the plan's pinned science-preview numbers -- this suite reproduces them
exactly (see the module's own run for n=8/9's reachable splits, which are
NEW numbers past the plan's preview, recorded below as regression pins).
"""

from __future__ import annotations

import pathlib
import tempfile

import networkx as nx
import pytest

from empiricist.domain.p5.canonical import iso_certificate
from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.tablebase import enumerate_connected_orbits, tier0_search
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Verdict
from empiricist.verifiers.enum_fusion import EnumFusionVerifier
from empiricist.verifiers.registry import Registry, verify_agreed
from empiricist.verifiers.stab_fusion import StabFusionVerifier

# Adcock's connected LC-orbit counts keyed by n (n=3 -> 1 orbit, ..., n=9 ->
# 440 orbits), matching test_p5_canonical.py::ADCOCK_CUMULATIVE. Tier0Result's
# own total_orbit_count[n] (the A3 real enumeration, via geng/itertools) is
# the ground truth compared against this table below.
ADCOCK_TOTALS = {3: 1, 4: 2, 5: 4, 6: 11, 7: 26, 8: 101, 9: 440}


@pytest.fixture(scope="module")
def result_n6():
    return tier0_search(6)


@pytest.fixture(scope="module")
def result_n7():
    return tier0_search(7)


def test_tier0_small_n_exact(result_n6):
    """n <= 6: every connected orbit is classified (reachable + unreachable
    == the Adcock total for that n, via the REAL A3 enumeration, not a
    tautological subtraction)."""
    for n in range(3, 7):
        assert result_n6.total_orbit_count[n] == ADCOCK_TOTALS[n], (
            f"n={n}: the independent enumeration found {result_n6.total_orbit_count[n]} "
            f"total orbits, expected Adcock's {ADCOCK_TOTALS[n]}"
        )
        assert (
            result_n6.reachable_count(n) + result_n6.unreachable_count[n]
            == ADCOCK_TOTALS[n]
        )


def test_k3_orbit_reachable_at_depth_0(result_n6):
    assert result_n6.reachable_count(3) == 1
    assert result_n6.reachable[3][0].depth == 0
    assert result_n6.reachable[3][0].size == 3


def test_p4_c4_orbit_reachable_at_depth_1(result_n6):
    """P4 and C4 are LC-equivalent (one orbit at n=4); that orbit must be
    among Tier-0's reachable orbits at depth 1 (one merge from the seed)."""
    p4 = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    enum4 = enumerate_connected_orbits(4)
    p4_root = enum4.orbit_root(iso_certificate(p4))

    reachable_roots = {
        enum4.orbit_root(o.representative_cert) for o in result_n6.reachable[4]
    }
    assert p4_root in reachable_roots

    matching = [
        o
        for o in result_n6.reachable[4]
        if enum4.orbit_root(o.representative_cert) == p4_root
    ]
    assert len(matching) == 1
    assert matching[0].depth == 1
    assert matching[0].size == 4


def test_tier0_depth_equals_size_minus_3(result_n6):
    """L3 surfaced as a test: every reachable orbit's depth == size - 3."""
    for n in range(3, 7):
        for orbit in result_n6.reachable[n]:
            assert orbit.depth == orbit.size - 3 == n - 3


def test_mod3_ladder_holds(result_n6):
    """Every Tier-0 reported F value (== orbit.depth, since Tier-0 IS the
    N-3 achievability search) satisfies F == N - 3, hence trivially F === N-3
    (mod 3). This pins the plumbing Tier-1 will reuse for the non-trivial
    F in {N, N+3, ...} ladder."""
    for n in range(3, 7):
        for orbit in result_n6.reachable[n]:
            f_value = orbit.depth
            assert f_value == n - 3
            assert f_value % 3 == (n - 3) % 3


def test_tier0_witnesses_certify(result_n6, tmp_path):
    """For n <= 6, EVERY reachable orbit's witness Construction PASSES
    verify_agreed (both independent engines certify it) -- the A-and-B
    certificate on every claimed F = N-3 value."""
    ledger = Ledger(tmp_path / "ledger.db")
    try:
        registry = Registry(ledger)
        registry.certify(StabFusionVerifier())
        registry.certify(EnumFusionVerifier())

        checked = 0
        for n in range(3, 7):
            for orbit in result_n6.reachable[n]:
                construction = result_n6.witness(orbit.representative_cert)
                assert construction.fusion_count == orbit.depth
                res = verify_agreed(registry, construction)
                assert res.verdict == Verdict.PASS, (
                    f"n={n} orbit={orbit.orbit_id}: witness failed verify_agreed: "
                    f"{res.details}"
                )
                checked += 1
        assert checked == sum(result_n6.reachable_count(n) for n in range(3, 7))
    finally:
        ledger.close()


def test_tier0_n7(result_n7):
    """NEW science (n=7, past the Task-1-era smallest cases): reachable +
    unreachable sums to Adcock's 26; the split is pinned to the review's
    preview (15 reachable / 11 unreachable) -- reproduced exactly here."""
    assert result_n7.total_orbit_count[7] == 26
    assert result_n7.reachable_count(7) == 15
    assert result_n7.unreachable_count[7] == 11
    assert result_n7.reachable_count(7) + result_n7.unreachable_count[7] == 26
    # n <= 7 materializes actual unreachable orbit representatives too.
    assert len(result_n7.unreachable_representatives[7]) == 11


@pytest.mark.slow
def test_tier0_n8_n9():
    """SCIENCE OUTPUT: Tier-0 to n=9, the project's first novel-science
    dataset (past the published n=8 frontier). Adcock totals (101, 440) are
    the A3 real-enumeration cross-check (via geng, not a published-count
    lookup); the reachable/unreachable splits are recorded here as
    regression pins after the first run:

        n=8: 42 reachable / 59 unreachable (of 101 total orbits)
        n=9: 104 reachable / 336 unreachable (of 440 total orbits)
    """
    result = tier0_search(9)

    assert result.total_orbit_count[8] == 101
    assert result.total_orbit_count[9] == 440
    assert result.reachable_count(8) + result.unreachable_count[8] == 101
    assert result.reachable_count(9) + result.unreachable_count[9] == 440

    # Pinned science output (see docstring) -- if these ever change, either
    # the search/enumeration broke or this is a genuine (surprising) result;
    # investigate before updating the pin.
    assert result.reachable_count(8) == 42
    assert result.unreachable_count[8] == 59
    assert result.reachable_count(9) == 104
    assert result.unreachable_count[9] == 336

    # L3 + mod-3 plumbing at the largest sizes too.
    for n in (8, 9):
        for orbit in result.reachable[n]:
            assert orbit.depth == n - 3

    # M5c Task 4 gap fix: unreachable-orbit representatives must now be
    # materialized at n=8,9 too (build_dataset needs a real representative
    # graph for every "open" row across the FULL n=3..9 range, not just
    # n<=7) -- one distinct GraphState per unreachable orbit, none of which
    # collides with a reachable orbit's root.
    for n in (8, 9):
        reps = result.unreachable_representatives[n]
        assert len(reps) == result.unreachable_count[n]
        enum_n = enumerate_connected_orbits(n)
        reachable_roots = {enum_n.orbit_root(o.representative_cert) for o in result.reachable[n]}
        rep_roots = set()
        for rep in reps:
            assert rep.n == n
            assert nx.is_connected(rep.to_networkx())
            root = enum_n.orbit_root(iso_certificate(rep))
            assert root not in reachable_roots
            rep_roots.add(root)
        assert len(rep_roots) == len(reps)  # every representative is a DISTINCT orbit

    # Spot-certify a sample of n=8/n=9 witnesses (full n<=6 coverage is
    # already exhaustive in test_tier0_witnesses_certify above; this is an
    # extra check that the witness bookkeeping still holds at deeper BFS
    # paths, not a repeat of the full-coverage claim).
    with tempfile.TemporaryDirectory() as d:
        ledger = Ledger(pathlib.Path(d) / "ledger.db")
        try:
            registry = Registry(ledger)
            registry.certify(StabFusionVerifier())
            registry.certify(EnumFusionVerifier())
            for n in (8, 9):
                for orbit in result.reachable[n][:5]:
                    construction = result.witness(orbit.representative_cert)
                    res = verify_agreed(registry, construction)
                    assert res.verdict == Verdict.PASS, (
                        f"n={n} orbit={orbit.orbit_id}: witness failed verify_agreed: "
                        f"{res.details}"
                    )
        finally:
            ledger.close()


def test_enumerate_connected_orbits_uses_geng_when_available():
    """A3: at n=8 the itertools fallback is infeasible (2^28 labeled
    graphs) -- this environment has nauty installed, so the real check must
    be exercised via geng, not silently skipped."""
    import shutil

    if shutil.which("geng") is None and shutil.which("nauty-geng") is None:
        pytest.skip("geng/nauty-geng not installed -- cannot exercise the geng path")
    enum8 = enumerate_connected_orbits(8)
    assert enum8.method == "geng"
    assert enum8.graph_count == 11117
    assert enum8.orbit_count == 101


def test_enumerate_connected_orbits_n8_without_geng_raises(monkeypatch):
    """Without geng, n=8 must raise rather than silently attempting an
    infeasible itertools enumeration (2^28 labeled graphs)."""
    import empiricist.domain.p5.tablebase as tb

    monkeypatch.setattr(tb, "_find_geng", lambda: None)
    with pytest.raises(RuntimeError):
        enumerate_connected_orbits(8)


def test_no_lc_orbit_key_in_tablebase():
    """A4: tablebase.py must never call lc_orbit_key (orbit ids are
    union-find roots over iso-certificates, computed for free by the BFS
    itself -- calling lc_orbit_key anywhere in the hot loop would re-walk a
    whole LC orbit per candidate, exactly the cost the search structure is
    designed to avoid)."""
    import inspect

    import empiricist.domain.p5.tablebase as tb

    source = inspect.getsource(tb)
    # The only appearance of the substring should be in this docstring
    # sentence explaining the guard itself -- assert it's not CALLED.
    assert "lc_orbit_key(" not in source

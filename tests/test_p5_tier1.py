"""Tier-1 tests (M5c Task 3): the f_i=1 exhaustive intra-fusion resolution
for orbits Tier-0's all-merge-only search (f_i=0) did not reach.

Per the plan's review preview (reproduced exactly here): n=5's single open
orbit resolves to F=5; n=6's 3 open orbits split 2 resolved (F=6) / 1
remains F>=9. n=7 is NEW science: this repo's own first run found the 11
Tier-0-open orbits split 7 resolved (F=7) / 4 remain open -- pinned below
(see test_tier1_n7_science) after verifying it against an independent
re-check of the same run.
"""

from __future__ import annotations

import pathlib
import tempfile

import pytest

from empiricist.domain.p5.tablebase import enumerate_connected_orbits, tier1_search
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Verdict
from empiricist.verifiers.enum_fusion import EnumFusionVerifier
from empiricist.verifiers.registry import Registry, verify_agreed
from empiricist.verifiers.stab_fusion import StabFusionVerifier


@pytest.fixture(scope="module")
def tier1_n6():
    return tier1_search(6)


def test_tier1_transient_cap(tier1_n6):
    """L4: the transient for f_i<=1 is n_max+2 -- Tier-1 reuses (and only
    needs) an all-merge search out to that size, not further."""
    assert tier1_n6.n_max == 6
    assert tier1_n6.transient_max == 8
    assert tier1_n6.tier0.n_max == 8


def test_tier1_n5_resolves_the_one_open_orbit(tier1_n6):
    assert tier1_n6.resolved_count(5) == 1
    orbit = tier1_n6.newly_resolved[5][0]
    assert orbit.f_value == 5
    assert orbit.size == 5


def test_tier1_n6_resolves_two_of_three(tier1_n6):
    assert tier1_n6.resolved_count(6) == 2
    for orbit in tier1_n6.newly_resolved[6]:
        assert orbit.f_value == 6
        assert orbit.size == 6

    # the third n=6 orbit Tier-0 left open must remain open after Tier-1
    # too: independently confirm (via the Adcock enumeration, not either
    # search's own bookkeeping) that exactly 1 of the 11 n=6 orbits is
    # neither Tier-0-reachable nor Tier-1-resolved.
    enum6 = enumerate_connected_orbits(6)
    t0 = tier1_n6.tier0
    t0_roots = {enum6.orbit_root(o.representative_cert) for o in t0.reachable[6]}
    resolved_roots = {bytes.fromhex(o.orbit_id) for o in tier1_n6.newly_resolved[6]}
    all_roots = enum6.all_orbit_roots()
    still_open = all_roots - t0_roots - resolved_roots
    assert len(still_open) == 1


def test_mod3_ladder_tier1(tier1_n6):
    """L2's ladder, non-trivially: every Tier-1-resolved F equals its own n
    exactly (F = N, not just F === N-3 mod 3, which N and N-3 both satisfy)."""
    for n, orbits in tier1_n6.newly_resolved.items():
        for orbit in orbits:
            assert orbit.f_value == n
            assert orbit.f_value % 3 == (n - 3) % 3


def test_tier1_witnesses_certify(tier1_n6, tmp_path):
    """Every Tier-1-resolved orbit's witness (merges -> one intra fusion)
    PASSES verify_agreed -- the A-and-B certificate on every claimed F=N
    value, exhaustively (n<=6 has only 3 such orbits total, cheap to cover
    all of them rather than sample)."""
    ledger = Ledger(tmp_path / "ledger.db")
    try:
        registry = Registry(ledger)
        registry.certify(StabFusionVerifier())
        registry.certify(EnumFusionVerifier())

        checked = 0
        for n, orbits in tier1_n6.newly_resolved.items():
            for orbit in orbits:
                construction = tier1_n6.witness(orbit)
                assert construction.fusion_count == orbit.f_value
                res = verify_agreed(registry, construction)
                assert res.verdict == Verdict.PASS, (
                    f"n={n} orbit={orbit.orbit_id}: witness failed verify_agreed: {res.details}"
                )
                checked += 1
        assert checked == tier1_n6.resolved_count(5) + tier1_n6.resolved_count(6) == 3
    finally:
        ledger.close()


@pytest.mark.slow
def test_tier1_n7_science():
    """NEW SCIENCE: n=7's 11 Tier-0-open orbits split under Tier-1 (f_i<=1,
    transient <= 9). Pinned after this repo's first run -- if this number
    ever changes, investigate before updating the pin (same discipline as
    Tier-0's own test_tier0_n7/test_tier0_n8_n9 pins)."""
    result = tier1_search(7)
    assert result.resolved_count(7) == 7
    for orbit in result.newly_resolved[7]:
        assert orbit.f_value == 7

    enum7 = enumerate_connected_orbits(7)
    t0_roots = {enum7.orbit_root(o.representative_cert) for o in result.tier0.reachable[7]}
    resolved_roots = {bytes.fromhex(o.orbit_id) for o in result.newly_resolved[7]}
    all_roots = enum7.all_orbit_roots()
    still_open = all_roots - t0_roots - resolved_roots
    assert len(still_open) == 4

    with tempfile.TemporaryDirectory() as d:
        ledger = Ledger(pathlib.Path(d) / "ledger.db")
        try:
            registry = Registry(ledger)
            registry.certify(StabFusionVerifier())
            registry.certify(EnumFusionVerifier())
            for orbit in result.newly_resolved[7]:
                construction = result.witness(orbit)
                assert construction.fusion_count == 7
                res = verify_agreed(registry, construction)
                assert res.verdict == Verdict.PASS, (
                    f"n=7 orbit={orbit.orbit_id}: witness failed verify_agreed: {res.details}"
                )
        finally:
            ledger.close()

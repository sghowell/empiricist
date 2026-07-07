"""Independent re-derivation tests (M5c Task 3, F3 discipline).

Two things this suite must establish:

1. **Independence itself**: `tablebase_check.py` must not import
   `tablebase.py` (the implementation it's re-deriving) or `moves.py`
   (in particular `merge_fresh_ghz3`, the closed form it independently
   re-implements via the engine) -- checked via `ast`-parsing
   `inspect.getsource`, not a substring scan, so neither module's
   prose (which freely discusses the other by name) can produce a false
   positive or a false negative.

2. **Agreement**: the independent search's per-n reachable-orbit partition
   must exactly match Tier-0's, for n <= 6 in the fast suite and n = 7
   marked slow. Per the plan, the comparator is computed HERE, not by either
   implementation: the min iso-certificate over each orbit representative's
   full LC-orbit closure (`canonical.lc_orbit_key`) -- neither `tablebase.
   tier0_search` nor `tablebase_check.independent_reachability_search` is
   trusted to hand out orbit ids comparable to the other's.
"""

from __future__ import annotations

import ast
import inspect

import pytest

from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.tablebase import tier0_search
from empiricist.domain.p5.tablebase_check import (
    independent_reachability_search,
    merge_via_engine,
)


def test_tablebase_check_does_not_import_tablebase_or_moves():
    """The F3 independence guard. Parses the ACTUAL import statements (via
    ast), not a text scan -- tablebase_check.py's own docstring discusses
    both `tablebase.py` and `moves.merge_fresh_ghz3` by name at length, so a
    naive substring check would false-positive on its own documentation."""
    import empiricist.domain.p5.tablebase_check as tbc

    source = inspect.getsource(tbc)
    tree = ast.parse(source)

    imported_modules: set[str] = set()
    imported_from: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imported_from.add((module, alias.name))

    # No import of the tablebase module itself, under any spelling.
    assert not any(m == "empiricist.domain.p5.tablebase" or m.endswith(".tablebase")
                   for m in imported_modules), (
        f"tablebase_check.py imports the tablebase module directly: {imported_modules}"
    )
    assert not any(
        (mod == "empiricist.domain.p5" and name == "tablebase") or mod.endswith(".tablebase")
        for mod, name in imported_from
    ), f"tablebase_check.py imports from the tablebase module: {imported_from}"

    # No import of the moves module AT ALL (not just merge_fresh_ghz3 by
    # name) -- this module reimplements the merge move via the engine
    # directly and has no legitimate need for moves.py.
    assert not any(m.endswith(".moves") for m in imported_modules), (
        f"tablebase_check.py imports the moves module: {imported_modules}"
    )
    assert not any(mod.endswith(".moves") for mod, _ in imported_from), (
        f"tablebase_check.py imports from the moves module: {imported_from}"
    )
    assert not any(name == "merge_fresh_ghz3" for _, name in imported_from), (
        "tablebase_check.py imports merge_fresh_ghz3 -- the closed form it must "
        "independently re-derive via the engine instead"
    )


def test_merge_via_engine_matches_p4_golden():
    """Sanity: the engine-backed merge reproduces the same P4 golden the
    closed form does (test_p5_moves.py::test_merge_golden_p4), computed via
    a completely different code path (GF2Engine.fuse on the actual disjoint
    union, not the closed-form rewrite)."""
    blob = GraphState(n=3, edges=[(0, 1), (0, 2)])
    out = merge_via_engine(blob, a=1, role="leaf")
    target = GraphState(n=4, edges=[(0, 1), (1, 2), (2, 3)])
    assert lc_orbit_key(out) == lc_orbit_key(target)


def test_independent_search_finds_k3_alone_at_n3():
    result = independent_reachability_search(3)
    assert result.reachable_count(3) == 1


@pytest.fixture(scope="module")
def tier0_n6():
    return tier0_search(6)


@pytest.fixture(scope="module")
def check_n6():
    return independent_reachability_search(6)


def test_reachable_counts_agree_n6(tier0_n6, check_n6):
    for n in range(3, 7):
        assert check_n6.reachable_count(n) == tier0_n6.reachable_count(n), (
            f"n={n}: tier0 found {tier0_n6.reachable_count(n)} reachable orbits, "
            f"the independent search found {check_n6.reachable_count(n)}"
        )


def test_partition_agrees_with_tier0_n6(tier0_n6, check_n6):
    """The independence contract itself: for n <= 6, both derivations'
    reachable-orbit SETS must be identical under a fingerprint NEITHER
    implementation computes on its own (canonical.lc_orbit_key, computed
    here in the test, per the plan)."""
    for n in range(3, 7):
        tier0_keys = {lc_orbit_key(o.representative) for o in tier0_n6.reachable[n]}
        check_keys = {lc_orbit_key(o.representative) for o in check_n6.reachable[n]}
        # sanity: each side's own orbits are pairwise distinct under this
        # fingerprint too (i.e. neither side's search double-counted an orbit).
        assert len(tier0_keys) == len(tier0_n6.reachable[n])
        assert len(check_keys) == len(check_n6.reachable[n])
        assert tier0_keys == check_keys, (
            f"n={n}: partitions DISAGREE -- tier0-only={tier0_keys - check_keys}, "
            f"independent-check-only={check_keys - tier0_keys} -- this is the F3 alarm: "
            "one of the two implementations is wrong, investigate before trusting either"
        )


@pytest.mark.slow
def test_partition_agrees_with_tier0_n7():
    """n=7 (NEW-science scale, per Tier-0's own test_tier0_n7 pin: 15
    reachable orbits) -- same agreement contract, marked slow per the plan."""
    tier0_res = tier0_search(7)
    check_res = independent_reachability_search(7)
    assert check_res.reachable_count(7) == tier0_res.reachable_count(7) == 15

    tier0_keys = {lc_orbit_key(o.representative) for o in tier0_res.reachable[7]}
    check_keys = {lc_orbit_key(o.representative) for o in check_res.reachable[7]}
    assert tier0_keys == check_keys, (
        f"n=7: partitions DISAGREE -- tier0-only={tier0_keys - check_keys}, "
        f"independent-check-only={check_keys - tier0_keys}"
    )

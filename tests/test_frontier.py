"""Tests for the Pareto frontier with monotone version counter (spec §4.3, §9)."""

import pytest

from empiricist.ledger.db import Ledger
from empiricist.ledger.frontier import Frontier, recompute_frontier


@pytest.fixture()
def frontier(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    yield Frontier(lg)
    lg.close()


def test_empty_frontier_version_zero(frontier):
    assert frontier.version() == 0
    assert frontier.entries() == {}


def test_first_insert_improves(frontier):
    assert frontier.consider("g1", [10.0]) is True
    assert frontier.version() == 1
    assert frontier.entries() == {"g1": [10.0]}


def test_dominated_candidate_rejected_version_unchanged(frontier):
    frontier.consider("g1", [10.0])
    assert frontier.consider("g2", [12.0]) is False
    assert frontier.version() == 1
    assert "g2" not in frontier.entries()


def test_equal_vector_rejected(frontier):
    frontier.consider("g1", [10.0])
    assert frontier.consider("g2", [10.0]) is False


def test_dominating_candidate_evicts(frontier):
    frontier.consider("g1", [10.0, 5.0])
    assert frontier.consider("g2", [9.0, 4.0]) is True
    assert frontier.entries() == {"g2": [9.0, 4.0]}
    assert frontier.version() == 2


def test_incomparable_candidates_coexist(frontier):
    frontier.consider("g1", [10.0, 5.0])
    assert frontier.consider("g2", [5.0, 10.0]) is True
    assert set(frontier.entries()) == {"g1", "g2"}
    assert frontier.version() == 2


def test_same_key_better_vec_updates(frontier):
    frontier.consider("g1", [10.0])
    assert frontier.consider("g1", [8.0]) is True
    assert frontier.entries() == {"g1": [8.0]}


def test_recompute_matches_incremental(frontier):
    vecs = {"a": [3.0, 3.0], "b": [1.0, 5.0], "c": [5.0, 1.0], "d": [4.0, 4.0]}
    for k, v in vecs.items():
        frontier.consider(k, v)
    assert recompute_frontier(vecs) == frontier.entries()


def test_tied_vectors_geometry_matches_despite_key_divergence(frontier):
    from empiricist.ledger.frontier import geometry, recompute_frontier

    # zzz arrives first and holds the frontier slot; recompute prefers aaa.
    frontier.consider("zzz", [5.0])
    assert frontier.consider("aaa", [5.0]) is False
    pop = {"zzz": [5.0], "aaa": [5.0]}
    assert recompute_frontier(pop) == {"aaa": [5.0]}          # sorted-key winner
    assert frontier.entries() == {"zzz": [5.0]}               # arrival winner
    # The resume check compares geometry, which agrees:
    assert geometry(recompute_frontier(pop)) == frontier.geometry() == {(5.0,)}


def test_non_finite_vectors_rejected(frontier):
    import math

    from empiricist.ledger.frontier import recompute_frontier

    for bad in ([math.nan], [math.inf, 1.0], [1.0, -math.inf]):
        with pytest.raises(ValueError):
            frontier.consider("g", bad)
        with pytest.raises(ValueError):
            recompute_frontier({"g": bad})
    assert frontier.entries() == {}  # nothing squatted

# tests/test_p3_fock.py
import pytest

from empiricist.domain.p3.fock import factorial_prod, pattern_index, patterns


def test_patterns_enumerates_all_compositions():
    ps = patterns(n_photons=2, n_modes=3)
    assert ps == ((0, 0, 2), (0, 1, 1), (0, 2, 0), (1, 0, 1), (1, 1, 0), (2, 0, 0))


def test_patterns_counts():
    # compositions of n into m parts: C(n+m-1, m-1)
    assert len(patterns(4, 8)) == 330
    assert len(patterns(0, 5)) == 1  # the vacuum


def test_pattern_index_roundtrip():
    ps = patterns(3, 4)
    for i, p in enumerate(ps):
        assert pattern_index(p) == i


def test_patterns_sorted_complete_unique():
    for n in range(5):
        for m in range(1, 6):
            ps = patterns(n, m)
            assert list(ps) == sorted(ps)
            assert all(sum(p) == n for p in ps)
            assert len(set(ps)) == len(ps)


def test_patterns_zero_modes():
    assert patterns(2, 0) == ()
    assert patterns(0, 0) == ((),)


def test_patterns_negative_raises():
    with pytest.raises(ValueError):
        patterns(-1, 3)


def test_factorial_prod():
    assert factorial_prod((2, 0, 3)) == 12

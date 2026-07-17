# tests/test_p3_fock.py
from empiricist.domain.p3.fock import factorial_prod, pattern_index, patterns


def test_patterns_enumerates_all_compositions():
    ps = patterns(n_photons=2, n_modes=3)
    assert ps == [(0, 0, 2), (0, 1, 1), (0, 2, 0), (1, 0, 1), (1, 1, 0), (2, 0, 0)]


def test_patterns_counts():
    # compositions of n into m parts: C(n+m-1, m-1)
    assert len(patterns(4, 8)) == 330
    assert len(patterns(0, 5)) == 1  # the vacuum


def test_pattern_index_roundtrip():
    ps = patterns(3, 4)
    for i, p in enumerate(ps):
        assert pattern_index(p) == i or ps[pattern_index(p)] == p


def test_factorial_prod():
    assert factorial_prod((2, 0, 3)) == 12

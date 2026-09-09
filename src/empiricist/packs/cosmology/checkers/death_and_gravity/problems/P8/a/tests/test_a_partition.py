import pytest
import sympy as sp
from p8a import independent, partition, validated


def test_exact_partition_and_beta_identities():
    assert all(sp.simplify(value) == 0 for value in partition.identities().values())
    assert partition.integrate_poly(partition.P*(1-partition.P)) == sp.Rational(9, 70)


def test_direct_trigonometric_differentiation_matches_rotation():
    x = sp.Symbol("x", real=True)
    v = sp.Function("v")(x)
    angle = sp.Function("angle")(x)
    direct = sp.diff(v*sp.cos(angle), x, 2)**2+sp.diff(v*sp.sin(angle), x, 2)**2
    radial = sp.diff(v, x, 2)-sp.diff(angle, x)**2*v
    tangential = 2*sp.diff(angle, x)*sp.diff(v, x)+sp.diff(angle, x, 2)*v
    assert sp.trigsimp(sp.expand(direct-radial**2-tangential**2)) == 0


def test_localization_known_exact_norm():
    z = partition.Z
    actual = partition.local_bilinear(partition.P, partition.P)/partition.A**3
    assert sp.expand(actual-(768+sp.Rational(6848, 35)*z+sp.Rational(1728, 715)*z**2)) == 0


def test_all_windows_have_strict_support_margin():
    assert partition.validate_coverage() == sp.Rational(14, 25)
    first_midpoint = partition.A/2
    first_window = (first_midpoint-(1-first_midpoint)/2,
                    first_midpoint+(1-first_midpoint)/2)
    assert first_window == (-sp.Rational(5, 16), sp.Rational(9, 16))
    assert -sp.Rational(1, 2) < first_window[0] < 0 < partition.A < first_window[1] < 1
    for j in (1, 2, 7, 100):
        left, right = 1-partition.R**(j-1), 1-partition.R**(j+1)
        midpoint = (left+right)/2
        assert sp.cancel((right-left)/(1-midpoint)) == sp.Rational(14, 25)


@pytest.mark.parametrize("ratio, duration", [(sp.Rational(1, 2), 1), (sp.Rational(3, 4), sp.Rational(1, 2)),
                                             (0, 1), (1, 1), (2, 1), (sp.Rational(3, 4), 0)])
def test_invalid_local_coverage_rejected(ratio, duration):
    with pytest.raises(ValueError):
        partition.validate_coverage(ratio, duration)


def test_dropped_infinite_tail_is_a_strict_underestimate():
    remainder = partition.tail_remainder(partition.P, 5)
    assert validated.positive(remainder)
    full = independent.tail_pair(independent.P, independent.P)
    truncated = independent.finite_cells(independent.P, independent.P, 4)
    assert full != truncated
    expected = sum(sp.Rational(str(value))*partition.Z**i
                   for i, value in enumerate(full))
    finite = sum(sp.Rational(str(value))*partition.Z**i
                 for i, value in enumerate(truncated))
    assert sp.expand(expected-finite-remainder) == 0


def test_changed_geometric_exponent_fails_reconstruction():
    k, ell = 2, 3
    r, a, x = partition.R, partition.A, partition.X
    local = partition.local_bilinear((1-a*x)**k, (1-a*x)**ell)/(a*r)**3
    correct = partition.monomial_tail_pair(k, ell)
    wrong = local/(1-r**(k+ell-2))
    assert sp.expand(correct-wrong) != 0


@pytest.mark.parametrize("power", [0, 1, -1])
def test_non_H2_endpoint_monomials_rejected(power):
    with pytest.raises(ValueError, match="endpoint"):
        partition.monomial_tail_pair(power, 2)


def test_noninteger_tail_and_empty_remainder_index_rejected():
    with pytest.raises(TypeError):
        partition.monomial_tail_pair(2.5, 2)
    with pytest.raises(ValueError):
        partition.tail_remainder(partition.P, 0)

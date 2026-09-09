import pytest
import sympy as sp
from p8a_radiation import validated, windows


def test_reference_credit_and_correct_estimate_direction():
    result = windows.reference_bridge(windows.CREDIT, 1)
    assert result["absolute_QSEI_multiplier"] == 1
    result = windows.reference_bridge(1, sp.Rational(1, 2))
    assert result["remaining_dimensionless_reference_deficit"] == "145/256"
    assert result["window_over_t_c"] == ["3/4", "5/4"]
    validated.enclosure(result["absolute_QSEI_multiplier"], "1.0011485", "1.0011487")
    assert not result["reference_bound_is_derived_here"]


@pytest.mark.parametrize("fraction", [0, -1, 2, 3, 0.5])
def test_windows_at_or_across_the_singular_boundary_and_floats_rejected(fraction):
    with pytest.raises(ValueError):
        windows.reference_bridge(1, fraction)


@pytest.mark.parametrize("beta", [None, -1, 0.5])
def test_missing_or_invalid_reference_bound_rejected(beta):
    with pytest.raises(ValueError):
        windows.reference_bridge(beta, sp.Rational(1, 2))


def test_geometric_bridge_is_explicitly_conditional():
    data = windows.geometric_bridge(reference_beta=1, t_min=2, kappa=3, hbar=1)
    assert data["conditional_on_SEE_and_reference_bound"]
    assert data["Q2"] == 3/(16*sp.pi**2)
    assert data["Q0"] == sp.Rational(435, 65536)/sp.pi**2
    with pytest.raises(ValueError):
        windows.geometric_bridge(reference_beta=None, t_min=1)
    with pytest.raises(ValueError):
        windows.geometric_bridge(reference_beta=1, t_min=0)


def test_duration_multiplier_decreases_on_shorter_positive_windows():
    short = windows.reference_bridge(1, sp.Rational(1, 10))["absolute_QSEI_multiplier"]
    long = windows.reference_bridge(1, 1)["absolute_QSEI_multiplier"]
    assert validated.positive(long-short)
    assert validated.positive(short-1)

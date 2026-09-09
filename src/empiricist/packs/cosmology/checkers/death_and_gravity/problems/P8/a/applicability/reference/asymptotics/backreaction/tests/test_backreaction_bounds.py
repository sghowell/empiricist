from fractions import Fraction

import pytest
from p8a_backreaction import bounds, verify


def slab(**changes):
    values = {"d": 1, "epsilon": "1/64", "t_minus": 1, "t_plus": 2}
    values.update(changes)
    return bounds.Slab(**values)


def test_certified_slab_and_common_past_domain():
    result = verify.slab_example()
    assert result["actual_z_max"] == "1/16"
    assert result["preparation"]["sufficient_radicand_lower_bound"] == "3/4"
    assert not result["synthetic_response_inputs_are_claimed_actual_quantum_bounds"]


@pytest.mark.parametrize("change", [
    {"d": 0}, {"d": -1}, {"epsilon": -1}, {"t_minus": 0}, {"t_plus": 1},
    {"z_max": 0}, {"z_max": "1/2"}, {"epsilon": 1}, {"epsilon": "1/4"},
])
def test_bad_domain_or_amplitude_rejected(change):
    with pytest.raises(ValueError):
        slab(**change)


@pytest.mark.parametrize("past", ["0", "1", "2", "1/8"])
def test_missing_or_nonpositive_preparation_radicand_rejected(past):
    with pytest.raises(ValueError):
        slab().preparation_check(past)


def test_zero_amplitude_returns_classical_zero_defect():
    result = bounds.frozen_bounds(slab(epsilon=0))
    assert result == {"density": 0, "pressure": 0, "EED": 0}


def test_response_inputs_are_explicit_and_not_reported_as_actual_bounds():
    result = bounds.response_bridge(slab(), density_response=1, pressure_response=2)
    assert result["actual_response_status"] == "CONDITIONAL_INPUT_NOT_DERIVED"
    assert not result["numerical_actual_quantum_response_certified"]
    assert Fraction(result["conditional_actual_density_defect_bound"]) == Fraction(7, 768)+Fraction(1, 4096)


@pytest.mark.parametrize("response", [-1, None, "nan"])
def test_invalid_or_missing_response_not_invented(response):
    with pytest.raises(ValueError):
        bounds.response_bridge(slab(), density_response=response, pressure_response=1)


def test_inexact_binary_float_parameter_rejected():
    with pytest.raises(TypeError, match="rational"):
        slab(epsilon=0.01)

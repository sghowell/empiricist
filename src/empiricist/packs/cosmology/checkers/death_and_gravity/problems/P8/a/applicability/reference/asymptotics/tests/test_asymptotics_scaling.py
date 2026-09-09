"""A.4 clock, source and EED scaling checks."""

import pytest
import sympy as sp
from p8a_asymptotics import independent, scaling, verify


def test_all_chain_rule_clock_source_and_exclusion_identities():
    result = scaling.identities()
    assert all(sp.simplify(value) == 0 for value in result["residuals"].values())


def test_independent_clock_and_coherent_scaling():
    verify.checked_scaling()
    result = independent.scaling_replay()
    assert result["reference_proper_coefficient_in_hbar_over_pi2_units"] == "1/5120"
    assert result["normalized_remainder_powers"] == [2, 3, 4]
    assert result["normalized_SEE_source_powers"] == [4, 8]


@pytest.mark.parametrize("powers", [(0, 0), (0, 1), (1, 1), (2, 3), (-1, -1)])
def test_exact_monomial_point_split_all_leibniz_allocations(powers):
    p, q = powers
    actual = scaling.coincidence(scaling.point_split_difference(scaling.ETA**p*scaling.ETAP**q))
    expected = (p-1)*(q-1)*scaling.ETA**(p+q-6)/scaling.A**4
    assert sp.simplify(actual-expected) == 0


def test_domain_control_is_a_wave_but_not_global_smooth_data():
    mean = scaling.B/(scaling.ETA-scaling.X[0])
    assert scaling.flat_wave(mean) == 0
    full_slice = mean.subs(scaling.ETA, 2)
    assert sp.denom(full_slice).subs(scaling.X[0], 2) == 0
    result = scaling.identities()["restricted_domain_control"]
    assert result["additional_leading_coefficient"] == "4*B**2"
    assert not result["smooth_on_full_spatial_Cauchy_slice"]


def test_non_bisolution_kernel_not_promoted_to_state():
    result = scaling.identities()["non_bisolution_control"]
    assert not result["admitted_as_state_difference"]
    assert sp.sympify(result["left_wave_residual"]) != 0
    assert sp.sympify(result["right_wave_residual"]) != 0


def test_extra_source_control_really_traceful_and_negative():
    result = scaling.identities()["excluded_extra_source_control"]
    assert result["formal_complete_density_and_pressure_match"]
    assert not result["ordinary_traceless_radiation"]
    names = {"t": scaling.T, "hbar": scaling.HBAR}
    assert sp.sympify(result["rho"], locals=names).is_negative
    assert sp.sympify(result["trace_FK"], locals=names).is_positive


def test_reference_limit_not_erased_by_radiation_or_constant_couplings():
    normalized_required = scaling.A**4*scaling.ETA**8*scaling.required_eed()
    assert sp.limit(normalized_required, scaling.ETA, 0, dir="+") == 0
    actual = sp.simplify(scaling.A**4*scaling.ETA**8*scaling.reference_eed())
    assert actual == scaling.HBAR/(320*sp.pi**2)
    assert actual.is_positive

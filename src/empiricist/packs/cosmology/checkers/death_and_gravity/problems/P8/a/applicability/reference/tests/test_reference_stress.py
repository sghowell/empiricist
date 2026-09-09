import pytest
import sympy as sp
from p8a_reference import independent, stress, verify


def test_source_sign_and_central_correction_dictionary():
    verify.verified_residuals(stress.convention_identities())


def test_source_specialization_modes_conservation_and_ambiguities():
    verify.verified_residuals(stress.identities())


def test_independent_conformal_stress_matches_proper_route():
    result = verify.checked_source_stress()
    assert result["FK_EED_coefficient"] == "1/5120"
    assert result["source_trace_coefficient"] == "1/3840"
    assert result["FK_trace_coefficient"] == "-1/3840"


def test_reference_eed_is_positive_and_not_zero():
    result = stress.reference_stress(1)
    assert result["EED_FK"] == stress.HBAR/(5120*sp.pi**2)
    assert result["EED_FK"].is_positive
    assert result["trace_FK"].is_negative


def test_wrong_trace_convention_reverses_candidate_sign():
    result = stress.reference_stress()
    wrong_eed = sp.simplify(result["rho"]+result["trace_FK"]/2)
    assert wrong_eed == -result["rho"]
    assert wrong_eed != result["EED_FK"]


@pytest.mark.parametrize("time", [0, -1, sp.oo, sp.I, sp.Symbol("unknown_time")])
def test_nonphysical_time_rejected(time):
    with pytest.raises(ValueError, match="positive"):
        stress.reference_stress(time)


def test_nonvacuum_state_does_not_have_zero_radiation_term_or_wick_square():
    result = stress.identities()["nonvacuum_negative_control"]
    for key in ("conformal_density_excess", "Wick_square_excess",
                "minimal_minus_conformal_density_and_pressure"):
        assert sp.sympify(result[key]) != 0
    # Trace and conservation do not select the actual zero-vacuum occupation.
    rho_family = stress.identities()["general_trace_conservation_density"]
    assert "C_radiation" in rho_family


def test_finite_curvature_freedom_not_dropped_in_other_flrw():
    assert stress.h1_tt(sp.Rational(2, 3)/stress.T) == 8/stress.T**4
    assert independent.source_stress()["finite_curvature_coefficients"] == ["0", "0"]


def test_independent_gravity_couplings_change_the_eed():
    assert stress.added_geometric_eed(metric_shift=1, einstein_shift=0, time=1) == -1
    assert stress.added_geometric_eed(metric_shift=0, einstein_shift=1, time=1) == -sp.Rational(3, 4)
    with pytest.raises(TypeError):
        stress.added_geometric_eed()


def test_reference_trace_is_incompatible_with_exact_radiation_see():
    trace = stress.reference_stress()["trace_FK"]
    assert trace != 0
    assert sp.diff(trace, stress.T) != 0  # A constant cosmological term cannot cancel it.

import copy
from fractions import Fraction as F

import pytest
import sympy as sp
from p8a_remainder import geometry, independent
from p8a_response import preparation as prior_preparation


def test_remainder_exact_geometry_and_wrong_clock_exclusion():
    values = geometry.identities()
    assert values.pop("wrong_frozen_clock_potential") != 0
    assert all(sp.simplify(value) == 0 for value in values.values())


def test_remainder_all_actual_clock_jets_against_fraction_taylor_series():
    report = independent.taylor_jet_audit(geometry.ring_records())
    assert report["all_six_exact_jet_comparisons_passed"]
    assert not report["control_is_the_physical_smooth_cutoff"]


def test_remainder_changed_jet_ring_detected_independently():
    ring = copy.deepcopy(geometry.ring_records())
    ring[4][0]["coefficient"] = str(F(ring[4][0]["coefficient"])+1)
    with pytest.raises(ValueError, match="Taylor clock"):
        independent.taylor_jet_audit(ring)


def test_remainder_switch_extension_preserves_pinned_lower_orders():
    earlier = prior_preparation.switch_derivative_bounds()
    current = geometry.smooth_switch_bounds()
    assert current["switch"][:6] == earlier["switch_derivatives"]
    assert current["r"][:6] == earlier["r_derivatives"]
    assert len(current["switch"]) == 8
    assert geometry.p_jet_bounds() == independent.p_bounds()


@pytest.mark.parametrize("order", [-1, 8, 1.5, True])
def test_remainder_uncertified_switch_order_rejected(order):
    with pytest.raises(ValueError, match="order 7"):
        geometry.smooth_switch_bounds(order)


def test_remainder_exact_finite_domain_and_caps():
    data = geometry.calibration()
    assert data["potential_bounds"][:2] == [F(20461, 128), F(61013499, 8192)]
    assert data["delta_bar"] == F(2048, 190897521)
    assert data["jet_term_counts"] == [3, 6, 11, 18, 29, 43]
    assert data["IR_exponent_at_cap"] <= F(1, 2)
    assert data["UV_exponent_at_cap"] == F(1, 2)
    assert data["Hubble_extra_at_cap"] <= 1
    assert max(max(row["p_jets"], default=0) for jet in geometry.ring_records() for row in jet) == 7
    assert geometry.check_amplitude(0) == 0
    assert geometry.check_amplitude(data["delta_bar"]) == sp.Rational(data["delta_bar"])
    assert geometry.check_amplitude(F(1, 10**12)) == sp.Rational(1, 10**12)


@pytest.mark.parametrize("amplitude", [-1, F(1, 2), 1.0, sp.oo, sp.Symbol("unknown")])
def test_remainder_unproved_amplitude_domain_rejected(amplitude):
    with pytest.raises(ValueError):
        geometry.check_amplitude(amplitude)


def test_remainder_past_preparation_and_physical_amplitude_dictionary():
    a, eta_star, epsilon, d = sp.symbols("A eta_star epsilon d", positive=True)
    t_star = a*eta_star**2/2
    delta = 16*epsilon*d/(a**2*eta_star**4)
    assert sp.simplify(delta-4*epsilon*d/t_star**2) == 0
    assert sp.simplify((4*d/sp.Symbol("t_star", positive=True)**2).subs(
        sp.Symbol("t_star", positive=True), 2*10**6*sp.sqrt(d))) == sp.Rational(1, 10**12)
    # Active history starts at y=1, although the state is prescribed at y=1/2.
    assert 2**4*2 < 3**4
    assert 2**4*F(1, 2) == 8


def test_remainder_unsupported_majorant_term_rejected():
    with pytest.raises(ValueError, match="Unsupported"):
        geometry.majorize({(0, F(-1, 2), 0, (2,)): F(1)})


def test_remainder_fractional_taylor_power_independent_control():
    order = 5
    base = [F(1), F(1)]
    square_root = independent.fractional_power(base, F(1, 2), F(1), order)
    assert independent.multiply(square_root, square_root, order) == base+[F(0)]*(order-1)

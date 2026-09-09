import sympy as sp
from p8 import coupled as c
from p8 import jets as j


def test_canonical_matter_background_is_metric_derived():
    bg = c.background()
    Y = sp.diff(c.chi, j.t)**2
    assert sp.cancel(bg["matter_EN"]+Y/2) == 0
    assert sp.cancel(bg["matter_Ea"]-Y/2) == 0


def test_coupled_constraints_and_matter_principal_blocks():
    result = c.derive()
    assert result["constraints_residual"] == (0, 0)
    assert result["kinetic"][1, 1] == sp.Rational(1, 2)
    assert result["gradient"][1, 1] == sp.Rational(1, 2)
    assert result["kinetic"] == result["kinetic"].T
    assert result["gradient"] == result["gradient"].T


def test_corrected_source_mixing_follows_from_covariant_action():
    out = c.derive()
    GT, _, Theta, _, Lambda, delta, velocity = out["symbols"]
    expected_K12 = -velocity*GT*(1-3*delta)/(2*Theta)
    expected_G12 = -velocity*Lambda/(2*Theta)
    assert sp.cancel(out["kinetic"][0, 1]-expected_K12) == 0
    assert sp.cancel(out["gradient"][0, 1]-expected_G12) == 0

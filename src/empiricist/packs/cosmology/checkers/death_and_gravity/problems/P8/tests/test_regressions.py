import sympy as sp
from p8 import independent_sigma, regressions
from p8 import jets as j


def test_A25_coefficients_against_covariant_expansion():
    residuals = regressions.A25_dictionary()
    assert all(residuals[key] == 0 for key in ("GT", "FT", "Lambda", "Theta", "background_EN", "background_Ea"))


def test_A25_Sigma_discrepancy_has_an_independent_covariant_check():
    result = regressions.A25_dictionary()
    independent = independent_sigma.A25_sigma()
    assert independent["auxiliary_remainder"] == 0
    assert sp.cancel(independent["Sigma"]-result["Sigma_derived"]) == 0
    g, a1 = (sp.Function(name)(j.t) for name in ("g1", "a1"))
    theta = j.H*(1+4*a1+g)+sp.diff(g, j.t)
    discrepancy = -2*g*(j.dt(theta+sp.diff(g, j.t))+3*j.H*(theta+sp.diff(g, j.t)))
    assert sp.cancel(result["Sigma"]-discrepancy) == 0
    assert result["Sigma"] != 0  # retaining the printed expression is a negative control


def test_corrected_A25_covariant_F_reconstruction_is_regular():
    result = regressions.A25_reconstruction()
    assert set(result["residuals"].values()) == {0}
    assert not sp.denom(result["FXX"]).has(j.H)


def test_CPS16_beyond_Horndeski_numerator_dictionary():
    assert set(regressions.CPS16_dictionary().values()) == {0}


def test_luminal_interacting_matter_principal_interface_only():
    assert set(regressions.luminal_interface().values()) == {0}

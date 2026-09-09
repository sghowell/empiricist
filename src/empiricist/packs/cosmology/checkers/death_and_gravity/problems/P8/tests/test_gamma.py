import sympy as sp
from p8 import gamma


def test_regular_hamiltonian_is_derived_before_dividing_by_Theta():
    result = gamma.hamiltonian()
    assert all(value == 0 for value in result["residuals"].values())
    _T, _, th, S, _, delta, l, _ = result["symbols"]
    # At Theta=0 the only lapse-elimination obstruction is J, not Theta.
    assert sp.cancel(result["J"].subs(th, 0)-(S-l**2*(3*delta-1)**2/2)) == 0
    assert sp.denom(sp.cancel(result["density"])).subs(th, 0) != 0


def test_regular_principal_action_is_derived_from_Hamiltonian():
    result = gamma.principal_chart()
    assert all(value == 0 for value in result["residuals"].values())


def test_positive_Lambda_forces_a_descending_healthy_gamma_crossing():
    result = gamma.principal_chart()
    T, _, th, lam, _, _, _ = result["symbols"]
    _, _, _, thd = result["derivative_symbols"]
    assert sp.cancel(result["gradient"][0, 0].subs(th, 0)+T*thd/lam) == 0


def test_matter_mixing_obstruction_survives_in_regular_chart():
    result = gamma.principal_chart()
    T, _, _, lam, w, l, _ = result["symbols"]
    difference = result["kinetic"]-result["gradient"]
    assert sp.cancel(difference.det()+(T*w/lam+l)**2/4) == 0
def test_auxiliary_chart_does_not_assume_J_nonzero():
    from p8.gamma import auxiliary_chart
    assert set(auxiliary_chart()["residuals"].values()) == {0}

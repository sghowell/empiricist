import sympy as sp
from p8 import jets as j
from p8 import quadratic as q


def test_background_comes_from_homogeneous_variation():
    bg = q.background()
    assert sp.cancel(bg["EN"].subs(bg["solution"])) == 0
    assert sp.cancel(bg["Ea"].subs(bg["solution"])) == 0


def test_Ia_unreduced_action_is_derived():
    result = q.derive()
    assert all(value == 0 for value in result["residuals"].values()), result["residuals"]


def test_GR_background_regression():
    X = sp.Symbol("X", positive=True)
    F0, FX = sp.Function("P0")(j.t), sp.Function("PX")(j.t)
    mapping = q.covariant_N_jets(F0+FX*(X-1), sp.Integer(0), -sp.Rational(1, 2),
                                sp.Integer(0), sp.Integer(0), X)
    bg = q.background()
    en = q.substitute_functions(bg["EN"], mapping)
    ea = q.substitute_functions(bg["Ea"], mapping)
    assert j.zero(en-(F0-2*FX+3*j.H**2))
    assert j.zero(ea-(F0+2*sp.diff(j.H, j.t)+3*j.H**2))

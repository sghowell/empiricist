import pytest
import sympy as sp
from p8 import horndeski as h


def test_exact_constraint_and_ibp_chain():
    result = h.derive()
    assert result["residuals"]
    assert all(value == 0 for value in result["residuals"].values())
    assert sp.cancel(result["solution"][h.n] - h.GT*h.zdot/h.Theta) == 0
    assert sp.cancel(result["boundary"] - h.a*h.k2*h.GT**2*h.z**2/h.Theta) == 0


def test_independent_polynomial_engine():
    assert all(h.independent_polynomial_check().values())


def test_constraint_chart_domain_is_not_hidden():
    raw = h.derive()["raw"]
    det = sp.det(sp.hessian(raw, (h.n, h.b)))
    assert sp.expand(det) == -4*h.a**2*h.k2**2*h.Theta**2
    # At gamma crossing the original constraints lose this invertibility.
    assert det.subs(h.Theta, 0) == 0
    # Bounce and gamma crossing are different conditions.
    assert det.subs(h.H, 0) == det


def test_no_H_denominator_and_finite_bounce_fixture():
    result = h.derive()
    for expr in (result["GS"], result["FS"], *result["solution"].values()):
        assert not sp.denom(sp.cancel(expr)).has(h.H)
    values = {h.H: 0, h.GT: 1, h.FT: 1, h.Theta: 1, h.Sigma: 1,
              h.GTdot: 0, h.Thetadot: -2}
    assert result["GS"].subs(values) == 4
    assert result["FS"].subs(values) == 1
    # These are coefficient jets, not a covariant bounce solution.


def test_GR_kessence_known_answer_away_from_H_zero():
    M2, Hd = sp.symbols("M2 Hd", nonzero=True)
    FS = h.derive()["FS"].subs({h.GT: M2, h.FT: M2, h.GTdot: 0,
                               h.Theta: M2*h.H, h.Thetadot: M2*Hd})
    assert sp.cancel(FS + M2*Hd/h.H**2) == 0
    # This specialization DOES fail at H=0: Theta=M2*H there. Never claim
    # that absence of a generic 1/H pole fixes the specialized gauge chart.
    assert sp.denom(sp.cancel(FS)).has(h.H)


def test_integral_hypothesis_negative_control():
    t = sp.Symbol("t", real=True)
    # Reduced-coefficient fixture: all four coefficients positive but the
    # past tensor integral converges. This is NOT a covariant-model witness.
    xi = 2*sp.exp(t)
    assert sp.diff(xi, t)-sp.exp(t) == sp.exp(t)
    assert sp.integrate(sp.exp(t), (t, -sp.oo, 0)) == 1
    assert sp.limit(xi, t, -sp.oo) == 0


def test_gamma_crossing_cannot_be_integrated_through_as_a_regular_xi():
    t = sp.Symbol("t", real=True)
    xi = -1/t  # a=GT=FT=1, Theta=-t
    assert sp.diff(xi, t)-1 == 1/t**2-1
    assert sp.limit(xi, t, 0, dir="-") == sp.oo
    assert sp.limit(xi, t, 0, dir="+") == -sp.oo


def test_boundary_derivative_rejects_unsupported_jets():
    with pytest.raises(ValueError):
        h.dt_boundary(h.H*h.z**2)

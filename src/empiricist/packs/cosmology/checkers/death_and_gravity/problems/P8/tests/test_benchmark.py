import mpmath as mp
import sympy as sp
from p8 import benchmark as b


def test_exact_bounce_jet_and_removable_a1_limit():
    jet = b.bounce_jet()
    assert jet["a0"] == 1
    assert jet["H0"] == 0
    assert sp.simplify(jet["Hdot0"] - (b.epsilon+3)/(6*b.epsilon*b.tau**2)) == 0
    expected = b.w*(11*b.epsilon-3)/(12*(b.epsilon+3)*sp.cosh(b.u)**2)
    assert sp.simplify(jet["a1_0"]-expected) == 0
    assert jet["Hdot0"].subs(b.PARAMETERS) == sp.Rational(1, 375)
    assert sp.simplify(jet["a1_0"].subs(b.PARAMETERS)
                       - sp.Rational(13, 12)/sp.cosh(sp.Rational(1, 10))**2) == 0


def test_theta_regularization_is_an_identity_before_using_background():
    # Treat H as an independent symbol: cancellation does not require a
    # floating-point evaluation of the 0/0 in the source a1 expression.
    H = sp.Symbol("H")
    s = b.t/b.tau
    g1 = b.w/(3*sp.cosh(s+b.u)**2)
    N = b.t**2*sp.tanh(s+b.u) + b.tau**2*sp.tanh(s)
    a1 = g1/4*(2*N/(H*b.tau*(b.t**2+b.tau**2))-1)
    source = H*(4*a1+g1+1)+sp.diff(g1, b.t)
    regular = H + 2*g1*b.tau/(b.t**2+b.tau**2)*(sp.tanh(s)-sp.tanh(s+b.u))
    # Rewrite tanh to sinh/cosh before exact rational cancellation; generic
    # trigsimp does not reliably choose this normalization.
    normalized = (source-regular).replace(sp.tanh, lambda x: sp.sinh(x)/sp.cosh(x))
    assert sp.cancel(normalized) == 0
    assert not sp.denom(sp.cancel(regular)).has(H)


def test_bounce_is_not_gamma_crossing_at_pinned_parameters():
    jet = b.bounce_jet()
    theta0 = jet["theta0"].subs(b.PARAMETERS)
    assert theta0.is_negative is True
    assert jet["H0"] == 0


def test_covariant_operator_does_not_vanish_when_its_background_value_does():
    X, g1, a1 = sp.symbols("X g1 a1")
    F2, A1 = -sp.Rational(1, 2)+g1*(1-X), a1*(X-1)
    assert (-2*F2).subs(X, 1) == 1
    assert (-2*F2+2*X*A1).subs(X, 1) == 1
    assert sp.diff(A1, X) == a1
    assert sp.diff(F2, X) == -g1


def test_a1_limit_agrees_with_two_sided_high_precision_evaluation():
    # Diagnostic cross-check, not a uniform or all-time enclosure.
    expr = b.background()["a1_quotient"].subs(b.PARAMETERS)
    fn = sp.lambdify(b.t, expr, "mpmath")
    with mp.workdps(70):
        expected = mp.mpf(str(sp.N(b.bounce_jet()["a1_0"].subs(b.PARAMETERS), 70)))
        for time in (mp.mpf("1e-20"), mp.mpf("-1e-20")):
            assert abs(fn(time)-expected) < mp.mpf("1e-19")

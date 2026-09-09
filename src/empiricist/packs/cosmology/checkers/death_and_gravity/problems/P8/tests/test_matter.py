import pytest
import sympy as sp
from flint import fmpq_mpoly_ctx
from p8 import matter


def test_luminal_matter_exact_matrix_chain():
    assert all(value == 0 for value in matter.luminal_identities().values())


def test_independent_luminal_determinant():
    ctx = fmpq_mpoly_ctx.get(("K11", "G11", "v", "q", "f", "g"))
    k11, g11, v, q, f, g = ctx.gens()
    determinant = (k11-g11)*(q-q) - (v*q*g-v*q*f)**2
    assert (determinant + v**2*q**2*(f-g)**2).is_zero()
    assert not determinant.is_zero()  # it is not generically PSD


def test_exceptional_covariant_relation_and_luminal_tensor_specialization():
    out = matter.exceptional_relation()
    assert out["residual"] == 0
    assert out["luminal_tensor_residual"] == 0


def test_printed_A25_D_discrepancy_is_not_silently_reintroduced():
    out = matter.exceptional_relation(printed_a25_D=True)
    X, F2, F2X, A1 = sp.symbols("X F2 F2X A1", real=True)
    expected = 4*F2X*(F2-A1*X)/(X*(3*A1*X-4*F2))
    assert sp.cancel(out["residual"]-expected) == 0
    assert out["residual"] != 0
    # On A1=0 the printed expression gives -3F2X/X instead of -2F2X/X.
    assert sp.cancel(out["solution"].subs(A1, 0) + 3*F2X/X) == 0


def test_D_dictionary_matches_Horndeski_and_benchmark_Lambda():
    A1, F2X, phi_dot, g1 = sp.symbols("A1 F2X phi_dot g1")
    corrected_D = 2*phi_dot*(2*F2X-A1)
    assert corrected_D.subs(A1, 2*F2X) == 0
    # A25 benchmark: X=phi_dot=GT=FT=1, F2X=-g1, A1=0, Delta=g1.
    Lambda = 1 + corrected_D.subs({phi_dot: 1, F2X: -g1, A1: 0}) + g1
    assert sp.expand(Lambda) == 1-3*g1


def test_ia_horndeski_locus():
    X, F2, F2X = sp.symbols("X F2 F2X")
    A2, A4, A5 = matter.ia_completion(F2, F2X, 2*F2X, 0, X)
    assert A2 == -2*F2X
    assert A4 == A5 == 0


def test_ia_GR_limit():
    X, F2 = sp.symbols("X F2")
    assert matter.ia_completion(F2, 0, 0, 0, X) == (0, 0, 0)


def verdict(kinetic, gradient):
    conditions = matter.principal_conditions_2x2(kinetic, gradient)
    return (all(x > 0 for x in conditions["strict"])
            and all(x >= 0 for x in conditions["weak"]))


@pytest.mark.parametrize("kinetic,gradient,expected", [
    (sp.diag(2, 1), sp.eye(2), True),  # one luminal mode is allowed
    (sp.eye(2), sp.diag(2, 1), False),  # f=g is NOT sufficient
    (sp.diag(-1, -1), sp.diag(-1, -1), False),  # det>0 alone misses ghosts
    (sp.eye(2), sp.diag(0, 1), False),  # no zero-speed boundary witnesses
    (sp.diag(2, 1), sp.Matrix([[1, sp.Rational(1, 10)],
                              [sp.Rational(1, 10), 1]]), False),
])
def test_principal_cone_fixtures(kinetic, gradient, expected):
    assert verdict(kinetic, gradient) == expected


def test_conditions_are_invariant_under_regular_congruence():
    # A time-local invertible variable change preserves the principal cone.
    T = sp.Matrix([[1, 2], [-1, 1]])
    for kinetic, gradient in ((sp.diag(2, 1), sp.eye(2)),
                              (sp.eye(2), sp.diag(2, 1))):
        assert verdict(T.T*kinetic*T, T.T*gradient*T) == verdict(kinetic, gradient)


def test_bad_matrix_input_is_rejected():
    with pytest.raises(ValueError):
        matter.principal_conditions_2x2(sp.eye(3), sp.eye(3))
    with pytest.raises(ValueError):
        matter.principal_conditions_2x2(sp.Matrix([[1, 1], [0, 1]]), sp.eye(2))

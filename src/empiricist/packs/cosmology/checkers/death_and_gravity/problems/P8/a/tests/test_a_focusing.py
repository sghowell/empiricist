import pytest
import sympy as sp
from flint import ctx
from p8a import focusing, geometry, partition, validated


def test_frozen_trial_preserves_all_endpoint_jets():
    q = focusing.trial()
    x = partition.X
    assert q.subs(x, 0) == sp.diff(q, x).subs(x, 0) == 0
    assert sp.simplify(q.subs(x, 1)) == 1
    assert sp.simplify(sp.diff(q, x).subs(x, 1)) == 0


def test_completed_square_and_unique_finite_family_optimum():
    result = focusing.optimize()
    assert all(value == 0 for value in result["residuals"].values())
    assert validated.positive(result["gram"][0, 0])
    assert validated.positive(result["gram"].det())
    shifted = sp.Matrix(focusing.COEFFICIENTS)-result["optimum"]
    gap = result["expression"]-result["optimized_threshold"]-(shifted.T*result["gram"]*shifted)[0]
    assert sp.cancel(gap) == 0


def test_improvement_and_separating_contraction_are_validated():
    result = focusing.optimize()
    validated.enclosure(result["optimized_threshold"], "4.4445507", "4.4445508")
    validated.enclosure(result["cubic_threshold"], "4.8747718", "4.8747719")
    validated.enclosure(100*result["improvement"]/result["cubic_threshold"], "8.825", "8.826")
    assert validated.positive(sp.Rational(9, 2)-result["optimized_threshold"])
    assert validated.positive(result["cubic_threshold"]-sp.Rational(9, 2))


def test_classical_zero_QEI_limit_and_explicit_initial_correction():
    initial = focusing.threshold(partition.P, alpha=0, beta=0, zeta=0)
    assert initial == sp.Rational(24, 5)
    corrected = focusing.threshold(partition.P, alpha=0, beta=0, zeta=-1)
    assert corrected-initial == -sp.Rational(11, 70)


@pytest.mark.parametrize("alpha,beta,zeta", [(-1, 0, 0), (0, -1, 0), (0, 0, 1)])
def test_bad_bound_signs_rejected(alpha, beta, zeta):
    with pytest.raises(ValueError):
        focusing.threshold(partition.P, alpha, beta, zeta)


def test_wrong_endpoint_data_and_family_size_rejected():
    with pytest.raises(ValueError, match="endpoint"):
        focusing.threshold(partition.X)
    with pytest.raises(ValueError, match="two"):
        focusing.trial([0])


def test_raychaudhuri_and_conditional_field_coefficient_mapping():
    data = geometry.identities()
    assert all(value == 0 for value in data["residuals"].values())
    assert "K=3H" in data["meaning_of_K"]
    assert "not_derived" in data


@pytest.mark.parametrize("expression,lower,upper", [(1, 2, 3), (1, 1, 1), (1, 3, 2)])
def test_invalid_Arb_enclosures_rejected(expression, lower, upper):
    with pytest.raises(ValueError):
        validated.enclosure(expression, lower, upper)


def test_false_sign_and_zero_containing_denominator_rejected():
    with pytest.raises(ValueError):
        validated.positive(-1)
    with ctx.workprec(10), pytest.raises(ValueError, match="denominator"):
        validated.evaluate(1/(partition.Z-sp.Rational(987, 100)))

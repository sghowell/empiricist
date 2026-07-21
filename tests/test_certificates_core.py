"""Tests for the exact SOS certificate checker (M20c Task 2, the trust
boundary). Every certificate here is either hand-verified in a comment
(the toy and its identity-breaking variant) or has its objective DERIVED
from its Gram matrix via the same polynomial arithmetic the checker itself
uses, so the algebraic identity holds by construction and the test isolates
exactly the check it targets (identity vs. PSD)."""

from fractions import Fraction

import pytest

from empiricist.certificates.core import (
    CheckResult,
    SOSCertificate,
    check_certificate,
    poly_add,
    poly_eq,
    poly_mul,
    poly_scale,
    poly_sub,
)


def _gram_poly(gram_basis, gram):
    """b^T Q b as a Poly, built with the same arithmetic helpers the checker
    uses. Handy for constructing synthetic Gram matrices (e.g. non-PSD ones)
    whose "objective" is then defined to make the identity hold trivially,
    isolating the PSD check."""
    n = len(gram_basis)
    out = {}
    for a in range(n):
        for b in range(n):
            coef = gram[a][b]
            if not coef:
                continue
            term = poly_mul({gram_basis[a]: Fraction(1)}, {gram_basis[b]: Fraction(1)})
            out = poly_add(out, poly_scale(term, coef))
    return out


# ---------------------------------------------------------------------------
# Test 1: the toy PASS.
#
# Hand check: bound - objective - mult*constr
#   = 1 - x - (-1/2)*(x^2 - 1)
#   = 1 - x + (1/2)x^2 - 1/2
#   = 1/2 - x + (1/2)x^2
# b^T Q b with b = (1, x), Q = [[1/2, -1/2], [-1/2, 1/2]]:
#   = 1/2*1 + (-1/2)*x + (-1/2)*x + 1/2*x^2 = 1/2 - x + (1/2)x^2   -- matches.
# ---------------------------------------------------------------------------

TOY = SOSCertificate(
    statement="1 - x >= 0 on {x^2 - 1 = 0}, i.e. x <= 1 on that variety",
    variables=("x",),
    objective={(0,): Fraction(1)},
    bound=Fraction(1),
    constraints=({(0, 0): Fraction(1), (): Fraction(-1)},),
    multipliers=({(): Fraction(-1, 2)},),
    gram_basis=((), (0,)),
    gram=(
        (Fraction(1, 2), Fraction(-1, 2)),
        (Fraction(-1, 2), Fraction(1, 2)),
    ),
)


def test_toy_certificate_passes():
    result = check_certificate(TOY)
    assert result == CheckResult(True, "", "")


def test_toy_tampered_gram_fails_psd():
    # A dedicated non-PSD Gram (det = 1*1 - 2*2 = -3 < 0) over the same
    # (1, x) basis, with the objective DERIVED from it so the identity
    # holds trivially -- isolates the PSD check.
    gram_basis = ((), (0,))
    gram = ((Fraction(1), Fraction(2)), (Fraction(2), Fraction(1)))
    target = _gram_poly(gram_basis, gram)  # {(): 1, (0,): 4, (0, 0): 1}
    cert = SOSCertificate(
        statement="deliberately non-PSD Gram",
        variables=("x",),
        objective=poly_scale(target, Fraction(-1)),
        bound=Fraction(0),
        constraints=(),
        multipliers=(),
        gram_basis=gram_basis,
        gram=gram,
    )
    result = check_certificate(cert)
    assert result.ok is False
    assert result.failure == "psd"


def test_toy_broken_identity_fails():
    # Same certificate as TOY but bound=2 instead of 1: changes the
    # constant term only (3/2 - x + (1/2)x^2 != 1/2 - x + (1/2)x^2), so the
    # Gram (still PSD) can no longer match -- identity fails first.
    broken = SOSCertificate(
        statement=TOY.statement,
        variables=TOY.variables,
        objective=TOY.objective,
        bound=Fraction(2),
        constraints=TOY.constraints,
        multipliers=TOY.multipliers,
        gram_basis=TOY.gram_basis,
        gram=TOY.gram,
    )
    result = check_certificate(broken)
    assert result.ok is False
    assert result.failure == "identity"


def test_semidefinite_pass_trivial():
    cert = SOSCertificate(
        statement="trivial 0 <= 0",
        variables=(),
        objective={(): Fraction(0)},
        bound=Fraction(0),
        constraints=(),
        multipliers=(),
        gram_basis=((),),
        gram=((Fraction(0),),),
    )
    result = check_certificate(cert)
    assert result == CheckResult(True, "", "")


def _garbage_cases():
    good_basis = ((),)
    good_gram = ((Fraction(1),),)
    length_mismatch = SOSCertificate(
        statement="bad",
        variables=("x",),
        objective={(): Fraction(0)},
        bound=Fraction(0),
        constraints=({(): Fraction(1)},),
        multipliers=(),  # length 0 != 1 constraint
        gram_basis=good_basis,
        gram=good_gram,
    )
    float_coefficient = SOSCertificate(
        statement="bad",
        variables=("x",),
        objective={(0,): 0.5},  # float, not Fraction/int -- disallowed
        bound=Fraction(0),
        constraints=(),
        multipliers=(),
        gram_basis=good_basis,
        gram=good_gram,
    )
    asymmetric_gram = SOSCertificate(
        statement="bad",
        variables=("x",),
        objective={(): Fraction(0)},
        bound=Fraction(0),
        constraints=(),
        multipliers=(),
        gram_basis=((), (0,)),
        gram=((Fraction(1), Fraction(2)), (Fraction(3), Fraction(1))),  # 2 != 3
    )
    dim_mismatch = SOSCertificate(
        statement="bad",
        variables=("x",),
        objective={(): Fraction(0)},
        bound=Fraction(0),
        constraints=(),
        multipliers=(),
        gram_basis=((),),  # length 1
        gram=(
            (Fraction(1), Fraction(0)),
            (Fraction(0), Fraction(1)),
        ),  # 2x2, mismatched with gram_basis
    )
    return [
        ("length_mismatch", length_mismatch),
        ("float_coefficient", float_coefficient),
        ("asymmetric_gram", asymmetric_gram),
        ("none", None),
        ("dim_mismatch", dim_mismatch),
    ]


def test_garbage_never_raises_and_reports_shape():
    for name, cert in _garbage_cases():
        try:
            result = check_certificate(cert)
        except Exception as exc:  # pragma: no cover - must never happen
            pytest.fail(f"check_certificate raised on {name!r}: {exc!r}")
        assert result.ok is False, name
        assert result.failure == "shape", name


def test_3x3_semidefinite_with_zero_eigenvalue_direction_passes():
    # [[1,1,0],[1,1,0],[0,0,1]]: block-diagonal (rank-1 2x2 block, PSD with
    # a zero eigenvalue, direction (1,-1,0)) plus an isolated positive 1x1.
    gram_basis = ((), (0,), (1,))
    gram = (
        (Fraction(1), Fraction(1), Fraction(0)),
        (Fraction(1), Fraction(1), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(1)),
    )
    target = _gram_poly(gram_basis, gram)
    cert = SOSCertificate(
        statement="synthetic 3x3 semidefinite",
        variables=("x0", "x1"),
        objective=poly_scale(target, Fraction(-1)),
        bound=Fraction(0),
        constraints=(),
        multipliers=(),
        gram_basis=gram_basis,
        gram=gram,
    )
    result = check_certificate(cert)
    assert result == CheckResult(True, "", "")


def test_3x3_with_negative_isolated_entry_fails_psd():
    # Same matrix but the isolated [2][2] entry is -1: eigenvalue -1 in
    # that isolated direction -- not PSD.
    gram_basis = ((), (0,), (1,))
    gram = (
        (Fraction(1), Fraction(1), Fraction(0)),
        (Fraction(1), Fraction(1), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(-1)),
    )
    target = _gram_poly(gram_basis, gram)
    cert = SOSCertificate(
        statement="synthetic 3x3, non-PSD",
        variables=("x0", "x1"),
        objective=poly_scale(target, Fraction(-1)),
        bound=Fraction(0),
        constraints=(),
        multipliers=(),
        gram_basis=gram_basis,
        gram=gram,
    )
    result = check_certificate(cert)
    assert result.ok is False
    assert result.failure == "psd"


# ---------------------------------------------------------------------------
# Sanity checks on the shared arithmetic helpers themselves.
# ---------------------------------------------------------------------------


def test_poly_mul_resorts_monomials():
    p = {(1,): Fraction(1)}
    q = {(0,): Fraction(1)}
    assert poly_mul(p, q) == {(0, 1): Fraction(1)}


def test_poly_sub_and_eq():
    p = {(0,): Fraction(1), (): Fraction(2)}
    q = {(0,): Fraction(1)}
    assert poly_eq(poly_sub(p, q), {(): Fraction(2)})
    assert not poly_eq(p, q)

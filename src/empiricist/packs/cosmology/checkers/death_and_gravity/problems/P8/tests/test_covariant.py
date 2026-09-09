import sympy as sp
from p8 import adm, covariant
from p8 import jets as j


def test_ADM_coefficient_identities():
    assert all(value == 0 for value in adm.coefficients()["residuals"].values())


def test_metric_inverse_and_background_sign():
    d = covariant.geometry()
    inverse = (d["g"]*d["gi"]).applyfunc(j.cut)
    assert inverse == sp.eye(4)
    curvature = covariant.scalar_invariants()["R4"].subs(j.eps, 0)
    assert j.zero(curvature+6*(sp.diff(j.H, j.t)+2*j.H**2))


def test_covariant_clock_contractions():
    assert all(covariant.contraction_residuals().values())


def test_covariant_curvature_boundary():
    assert covariant.curvature_ibp_residual()

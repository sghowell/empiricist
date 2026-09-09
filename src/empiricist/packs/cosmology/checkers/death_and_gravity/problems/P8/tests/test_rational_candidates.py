import pytest
import sympy as sp
from p8 import jets as j
from p8 import rational_candidates as r


@pytest.mark.parametrize("label", ["C", "D", "AC", "BC", "CD_matter"])
def test_candidates_solve_background_and_principal_targets(label):
    candidate = r.reconstruct(label)
    assert all(value == 0 for value in candidate["residuals"].values())
    assert candidate["GT"] == candidate["FT"]
    assert candidate["GT"].subs(j.t, 0) > 0
    assert candidate["kinetic"] == candidate["gradient"]
    assert candidate["H"].subs(j.t, 0) == 0
    assert sp.diff(candidate["H"], j.t).subs(j.t, 0) > 0


@pytest.mark.parametrize("label,off", [("C", ("K", "A1", "A3")), ("D", ("K", "A1")), ("AC", ("K", "A3")),
                                      ("BC", ("A1", "A3")), ("CD_matter", ("K", "A1"))])
def test_covariant_off_flags_are_identities(label, off):
    candidate = r.reconstruct(label)
    assert all(candidate[key] == 0 for key in off)
    if label == "D":
        assert sp.diff(candidate["F2"], r.X) == 0

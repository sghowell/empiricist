import sympy as sp
from p8 import jets as j
from p8.strong_gravity import derive


def test_explicit_covariant_strong_gravity_loophole():
    result = derive()
    assert set(result["residuals"].values()) == {0}
    assert result["total_tensor_integral"] == sp.pi**2/2
    assert sp.limit(result["GT"], j.t, sp.oo) == 0
    assert sp.limit(result["GT"], j.t, -sp.oo) == 0

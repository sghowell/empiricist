import sympy as sp
from p8.tilted_hessian import derive


def test_covariant_tilted_degeneracy_and_unitary_rank():
    result = derive()
    astar, _r, f, _fx, a1, _a3 = result["symbols"]
    assert result["tilted_scalar_block_determinant"] == 0
    assert sp.factor(result["unitary_K_minor"]+1024*(f-a1*astar**2)**6) == 0

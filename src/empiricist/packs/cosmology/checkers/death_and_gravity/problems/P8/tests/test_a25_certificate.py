from fractions import Fraction
from itertools import pairwise

from flint import arb, ctx
from p8.a25_certificate import Jet, ball, build


def test_jet_against_elementary_derivatives():
    with ctx.workprec(160):
        x = Jet(ball(Fraction(1, 3)), arb(1), arb(0))
        f = (1+x**2)**Fraction(1, 2)
        assert f.first.overlaps(x.value/(1+x.value**2).sqrt())
        assert f.second.overlaps((1+x.value**2)**ball(Fraction(-3, 2)))
        g = x.tanh()
        assert g.first.overlaps(1-x.value.tanh()**2)


def test_all_time_A25_regression():
    result = build()
    assert result["gamma_count"] == 1
    tiles = result["tiles"]
    assert tiles[0]["interval"][0] == "-500"
    assert tiles[-1]["interval"][1] == "500"
    assert all(a["interval"][1] == b["interval"][0] for a, b in pairwise(tiles))
    assert any(tile["chart"] == "gamma" for tile in tiles)

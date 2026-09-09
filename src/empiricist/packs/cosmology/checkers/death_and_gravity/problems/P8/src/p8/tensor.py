"""Direct transverse-traceless tensor coefficient check in the ADM action."""

import sympy as sp


def derive():
    z = sp.Symbol("z", real=True)
    h = sp.Function("h")(z)
    a, B, f, hd = sp.symbols("a B f hdot", nonzero=True, real=True)
    metric = sp.diag(a**2*sp.exp(h), a**2*sp.exp(-h), a**2)
    inverse = metric.inv()
    def partial(expr, index):
        return sp.diff(expr, z) if index == 2 else sp.Integer(0)
    connection = [[[sp.simplify(sum(inverse[i, m]*(partial(metric[m, k], j)+partial(metric[m, j], k)
                                                   -partial(metric[j, k], m))/2 for m in range(3)))
                    for k in range(3)] for j in range(3)] for i in range(3)]
    ricci = sp.zeros(3)
    for i in range(3):
        for j in range(3):
            ricci[i, j] = sum(partial(connection[k][i][j], k)-partial(connection[k][i][k], j)
                              +sum(connection[k][k][m]*connection[m][i][j]
                                   -connection[k][j][m]*connection[m][i][k] for m in range(3))
                              for k in range(3))
    R3 = sp.simplify(sp.trace(inverse*ricci))
    # K^i_j=diag(H+hdot/2,H-hdot/2,H); trace remains 3H.
    kinetic = -B*hd**2/2
    spatial = -f*R3
    return {"GT": -2*B, "FT": -2*f,
            "residuals": {"tensor_R3": sp.simplify(R3+sp.diff(h, z)**2/(2*a**2)),
                          "tensor_kinetic": sp.cancel(kinetic-(-2*B)*hd**2/4),
                          "tensor_gradient": sp.cancel(spatial+(-2*f)*sp.diff(h, z)**2/(4*a**2))}}

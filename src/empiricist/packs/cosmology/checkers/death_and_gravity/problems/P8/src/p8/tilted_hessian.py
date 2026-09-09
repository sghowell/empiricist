"""Covariant Ia velocity degeneracy on a foliation tilted from the scalar.

At one orthonormal point take phi_mu=(Astar,r,0,0). Spatial rotation makes
this general. Retain all seven velocities (normal derivative of Astar and
six extrinsic-curvature components); discard terms with fewer velocities.
This supplements, rather than assumes, the unitary-gauge degeneracy check.
"""

from functools import cache

import sympy as sp

from .matter import ia_completion


@cache
def derive():
    astar, r, f, fx, a1, a3 = sp.symbols("Astar r F2 F2X A1 A3", real=True)
    V, xx, yy, zz, xy, xz, yz = sp.symbols("V Kxx Kyy Kzz Kxy Kxz Kyz", real=True)
    X = astar**2-r**2
    K = xx+yy+zz
    KK = xx**2+yy**2+zz**2+2*(xy**2+xz**2+yz**2)
    Z = astar*V+r**2*xx
    L1 = V**2+astar**2*KK-2*r**2*(xx**2+xy**2+xz**2)
    L2 = (V+astar*K)**2
    L3, L4, L5 = astar*Z*(V+astar*K), Z**2, astar**2*Z**2
    a2, a4, a5 = sp.symbols("A2 A4 A5", real=True)
    kinetic = f*(K**2-KK)+4*fx*K*Z+a1*L1+a2*L2+a3*L3+a4*L4+a5*L5
    # Factor before inserting Ia: the 7x7 Hessian is block diagonal in the
    # three shear velocities and the two independent diagonal traceless parts.
    H = sp.hessian(kinetic.subs(a2, -a1), (V, xx, yy, zz, xy, xz, yz))
    block = H[:4, :4]
    determinant = sp.factor(block.det())
    _, A4, A5 = ia_completion(f, fx, a1, a3, X)
    degenerate = sp.factor(determinant.subs({a4: A4, a5: A5}))
    # The 6x6 K-only block is nondegenerate on a timelike tube with A1=0,
    # F2<0 and r=0. This establishes precisely one primary null direction
    # for the witnesses; the lapse/shift Hamiltonian fixes the scalar count.
    unitary_K_minor = sp.factor(H[1:, 1:].det().subs(r, 0))
    unitary_K_minor = sp.factor(unitary_K_minor.subs({a4: A4.subs(r, 0), a5: A5.subs(r, 0)}))
    return {"tilted_scalar_block_determinant": degenerate,
            "unitary_K_minor": unitary_K_minor,
            "tensor_shear_entries": [sp.factor(H[i, i]) for i in range(4, 7)],
            "symbols": (astar, r, f, fx, a1, a3)}

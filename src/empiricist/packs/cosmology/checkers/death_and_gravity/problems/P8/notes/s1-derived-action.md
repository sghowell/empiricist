# S1 — Covariant action, constraints and regular charts

Conventions and scope are fixed in [FORMULATION](../FORMULATION.md). All
statements here concern that quadratic Ia action on a timelike scalar tube,
and its **linear principal part**, not a nonlinear stability theorem.

## 1. Action-to-ADM bridge

`covariant.py` constructs the (+---) four-metric, inverse, connection and
curvature by coordinate index contractions to second perturbative order.
The Fourier wavevector is along one spatial axis; isotropy makes this
sufficient for the scalar principal action. Neither H nor its sign is
assumed nonzero. Let A*=1/N, X=A*², V=n(A*), K the positive-expansion
extrinsic-curvature trace, and b_i the spatial acceleration of the normal.
The checked contractions are

    Box phi = V + A* K,
    L1 = V² + X Kij Kij − 2X b_i b^i,
    L2 = (V + A* K)²,
    L3 = X V² + A* X K V,
    L4 = X V² − X² b_i b^i,
    L5 = X² V².

The curvature boundary is checked against the coordinate Ricci scalar,
not imported from P9:

    sqrt(-g) F2 R = N sqrt(h) [−F2 R3 + F2(K²−Kij Kij)
                     +2K n(F2) −2 D_i F2 b^i] + explicit divergence.

The divergence is constructed in `curvature_ibp_residual()`. In particular
the homogeneous curvature is −6(Hdot+2H²). Define

    B = F2−XA1,                 T = GT = −2B,       FT = −2F2,
    C = sqrt(X)(4F2X−2A1+XA3),
    Dv = X(A3+A4+XA5),          E = 4XF2X−2XA1−X²A4,
    Delta = C/(4B) = X(2A1−4F2X−XA3)/(2T).

The Ia completion gives exactly

    Dv + 3C²/(4T) = 0,
    E + FT Delta² + 2(−2F2+4XF2X)Delta = 0.

These cancel respectively the extra lapse-velocity square and its dangerous
spatial-gradient term in the transformed scalar variable. The tensor
normalization is independently checked in `tensor.py` using the exact TT
polarization h_ij=a² diag(exp(h),exp(−h),1):
R3=−h_z²/(2a²), delta(Kij Kij)=hdot²/2, so GT=−2B and FT=−2F2 with
the formulation's 1/8 tensor normalization.

`tilted_hessian.py` also checks degeneracy away from scalar-unitary slicing.
At an orthonormal point choose phi_mu=(A*,r,0,0), X=A*²−r². For the seven
velocities (V,Kxx,Kyy,Kzz,Kxy,Kxz,Kyz), let Z=A*V+r²Kxx. The velocity
parts are L3=A*Z(V+A*K), L4=Z², L5=A*²Z², with the full L1,L2 in code.
The F2R velocity term is F2(K²−KijKij)+4F2X K Z. Substitution of the
covariant Ia completion annihilates the Hessian determinant for arbitrary
tilt r, not just r=0. The unitary six-metric-velocity minor is
−1024(F2−A*²A1)^6, nonzero on the specified Ia domain. There is exactly
one primary velocity null direction there. The linear constraint reduction
below verifies the surviving degree count directly; this is not a claim
to have formalized the full nonlinear Dirac algorithm.

## 2. Derived background and unreduced quadratic action

`quadratic.py` expands the resulting ADM action using independent zeroth,
first and second **N derivatives** of its covariant coefficients at N=1.
Lapse and scale-factor variations give the two metric background equations;
F0 and FN are solved from those equations. The scalar equation follows from
the covariant diffeomorphism identity: with the metric equations and, in
M1, the chi equation satisfied, E_phi phi_dot=0. Here phi_dot=1, so no
extra scalar background equation is omitted.

Set zeta=v+Delta*n, where n is the lapse perturbation. Explicit boundaries
remove n_dot*v, n_dot*n and v_dot*v; their sum is differentiated back to
check the original action. The complete on-shell M0 quadratic action is

    a³[−3T vdot² + Sigma n² +6Theta n vdot
       + k²(2Theta n psi−2T vdot psi)]
      + a k²[FT v²+2Lambda n v],
    Lambda = −2F2+4XF2X+FT Delta.

Theta and Sigma are **outputs of the expansion**, not source inputs.
The scalar zero mode is used only for homogeneous variation; propagation
and the spatial shift inversion always use k!=0.

`coupled.py` expands sqrt(-g)Y/2 from the same four-metric. Both its metric
backreaction and (a³ chi_dot)'=0 are used before reducing constraints. With
l=chi_dot, w=l(3Delta−1), and S=Sigma_total, the complete additional terms
are a³[sdot²/2+w n sdot+3l v sdot−k² l psi s]−a k² s²/2. This compact
expression is checked against the whole second-order covariant expansion.
The term 3a³l v sdot can be changed to −3a³l vdot s by a boundary because
a³l is constant. This last fact would not apply unchanged to arbitrary
interacting matter; M1 is specifically the free canonical model.

On Theta!=0, variation of psi gives

    T vdot = Theta n − l s/2.

The usual reduced principal matrices are

    K = [[T² S/Theta²+3T, T w/(2Theta)],
         [T w/(2Theta), 1/2]],
    G = [[FS, −l Lambda/(2Theta)],
         [−l Lambda/(2Theta), 1/2]],
    FS = (a T Lambda/Theta)'/a − FT.

For M0 remove the second row/column and set l=0. For quartic Horndeski,
A1=2F2X and A3=0 imply Delta=0 and Lambda=T. This recovers the checked
KYY11 identity, including its domain Theta!=0. H never appears as a
constraint divisor.

## 3. Regular continuation at gamma crossing

A pole of the preceding coordinate action is not itself a physical
singularity. Write q=k²/a²>0 and b=a² psi. A direct Legendre transformation,
**before dividing by Theta**, gives canonical pairs

    (v, p_v=−2a³Tq b),       (s, p_s=a³P).
    J0=S+3Theta²/T,          J=J0−w²/2,
    R=q(Theta b+Lambda v)+wP/2−3l s Theta/(2T).

Before lapse elimination the Hamiltonian is a³[H0−J n²−2Rn], with

    H0=P²/2+q l b s+q s²/2−FT q v²−3l²s²/(4T).

Thus n=−R/J and H=a³(H0+R²/J). `gamma.hamiltonian()` checks both
Legendre identities and the lapse equation exactly. On any finite-time
compact set with J>0,T>0,a>0 the Hamiltonian is smooth, with a nondegenerate
symplectic form. The linear first-order ODE consequently has a unique
regular continuation for every fixed finite k!=0, including Theta=0.
There is one scalar canonical pair for M0, two for M1, throughout.

To exhibit the principal cone at a crossing use b, rather than v, as the
first coordinate. The canonical swap includes the time derivative of
2a³Tq: omitting it gives a wrong spatial coefficient. The momentum Hessian
determinant is (2q/J)[q Lambda²−FT J0]. For Lambda!=0 it is invertible
for sufficiently high q, and its actual high-q action yields

    K_b = [[T² J0/Lambda², −T w/(2Lambda)],
           [−T w/(2Lambda), 1/2]],
    G_b = [[Pgamma/Lambda², l/2], [l/2, 1/2]],
    Pgamma = Theta*(H T Lambda+Tdot Lambda+T Lambdadot)
             −T Lambda Thetadot−FT Theta² = Theta² FS.

This is a derived action with its boundary included, not a proposed
rescaling of singular matrices. In particular, at Theta=0,
G_b11=−T Thetadot/Lambda.

For the no-go proof it is important not to assume J!=0 in advance.
`gamma.auxiliary_chart()` retains the lapse during the canonical swap and
eliminates (v,n,P) **jointly**. Its determinant is
4q[q Lambda²−FT(J+w²/2)], with no division by J. It gives the same K_b
even when J=0. Therefore, on Lambda!=0, det K_b=T²J/(2Lambda²): J=0
really loses a principal kinetic direction and is outside strict health,
rather than being dismissed only because the Hamiltonian formula had a pole.
In M0 the corresponding result is K_b=T²J/Lambda².

On overlap charts both descriptions derive from the same constrained
action by invertible canonical operations. One coordinate/momentum chart
can fail at a particular **finite** q when q Lambda²=FT J0; the smooth
first-order Hamiltonian still applies there. This work certifies regular
linear continuation and high-frequency ghost/gradient/speed conditions,
not positivity of a finite-k Hamiltonian at all wavelengths or absence
of infrared growth, nonlinear instabilities, or strong coupling.

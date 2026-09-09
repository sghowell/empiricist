# Reference-state proof and absolute-QSEI bridge

All equations use `c=1`; `hbar` is restored explicitly. The source dictionary is
in [sources.md](sources.md). The trusted inputs are the conserved Hadamard
construction, conformal Wick-square transformation, conformal-vacuum stress
formula, and A.2 difference QSEI. The remainder below is a direct specialization
and calculation, checked by symbolic and independent rational implementations.

## 1. Signs are fixed by the physical covariant stress

The two stress-calculation sources use `g_S=-dt^2+a^2*dx^2`; FK uses
`g_F=dt^2-a^2*dx^2=-g_S`. In common coordinates the Levi-Civita connection is
unchanged. The massless minimal covariant stress expression is invariant:

`T_ab = partial_a(phi)*partial_b(phi) - g_ab*g^cd*partial_c(phi)*partial_d(phi)/2`.

Both metric factors change sign. The actions likewise agree: the source has
`-integral sqrt(-g_S)*(grad phi)^2_S/2`, and FK the opposite displayed action
sign with the opposite inverse metric. The positive-frequency modes and their
canonical normalization therefore describe the same physical field/state.

For a comoving unit vector, `U^a=(1,0,0,0)` in cosmic coordinates, so

`rho=T_tt`, `p=T_ii/a^2` (no sum) in **both** conventions.

In conformal coordinates the same statement is `rho=T_etaeta/a^2` and
`p=T_ii/a^2`, exactly the direct minimal-field source's Eq. (29). The covariant
stress tensor is not negated. Only contraction with the inverse metric flips
the trace:

`Tr_S(T)=-rho+3*p`, `Tr_F(T)=rho-3*p=-Tr_S(T)`.

FK's curvature convention additionally has `G_F=-G_S` and
`R_ab,F=-R_ab,S`; their scalar curvatures agree. This matches the respective
Einstein equations `G_F=-kappa*T` and `G_S=+kappa*T`. In particular the
radiation `G_tt,F=-3/(4*t^2)` is not the positive source `G_tt,S`.

The common Hadamard conservation correction also respects this dictionary.
For the massless operator on this `R=0` patch, `P_F=-P_S`, so the scalar
parametrix remainder `Q_H=<Phi*P*Phi>_H` changes sign. The product `g_ab*Q_H`
is invariant. Consequently the derivative-Wick correction below cannot insert
a hidden overall sign into the physical density. The code checks both the
classical quadratic expression and this central correction under the flip.

## 2. Why conformal stress evaluates this minimal reference

On the entire patch, `R=0`, so the two FK operators
`P_0=box` and `P_(1/6)=box+R/6` coincide, not merely at one point. Their
geometric parametrices may be chosen identically. FK's four-dimensional
prescription is

`(Phi^2)=(Phi^2)_H`,

`(Phi*nabla_(a nabla_b)*Phi)=(...)_H-g_ab*Q_H/3`,

`(nabla_a Phi*nabla_b Phi)=(...)_H+g_ab*Q_H/3`.

Because the operator and parametrix are common, so is `Q_H`. These opposite
corrections preserve the Leibniz rule and impose stress conservation. They
need not, and do not, impose `Phi*P*Phi=0` as a renormalized identity.

Subtract FK Eq. (23), using the *same* corrected Wick products, to obtain

`T_ab^(1/6)-T_ab^0=(g_ab*box-nabla_a*nabla_b-G_ab)*(Phi^2)/6`.

No classical equation of motion inside a Wick product was used. Pinamonti's
coincidence-limit transformation says the transported Minkowski-vacuum Wick
square differs only by the scalar-curvature correction. Both curvatures are
zero, and the Minkowski Wick square is zero. Thus

`<Phi^2>_ref=0`

throughout the patch, including all its derivatives, and the improvement
expectation vanishes. This transfers the conformal-reference stress to the
minimal reference. It is **not** a transfer of the target-state stress in A.2.

The two fields may have different finite choices in a general background. That
does not affect this conclusion: in the standard prescription class their
remaining stress differences vanish here, as proved in section 5.

## 3. The actual modes fix the radiation integration constant

Set `a=A*eta`, `t=A*eta^2/2`, `H=1/(2*t)`. The specified reference has

`psi_k=exp(-i*k*eta)/sqrt(2*k)`, `psidot_k=-i*k*psi_k/a`.

The subtracted integrand in Carlson--Anderson Eq. (2.4a) vanishes at each
`k>0`:

`|psidot|^2+(k/a)^2*|psi|^2-k/a^2=0`.

This is a pointwise finite identity, not a cancellation between separate
divergent integrals. The surviving local term gives

`H1_tt=-36*H*Hddot+18*Hdot^2-108*Hdot*H^2=0`,

`rho_ref=hbar*3*H^4/(2880*pi^2)=hbar/(15360*pi^2*t^4)`.

Conservation, which is already part of the prescription, now fixes
`p=-rho-rhodot/(3*H)=5*rho/3`. The direct minimal-field radiation calculation
in Glavan--Prokopec--Prymidis Eq. (41) independently gives precisely this
density and pressure for the same modes. Its conformal-time anomaly formulas
provide a second exact calculation in `eta` without the proper-time formula.

As a check rather than a state-fixing rule, the resulting FK trace is
`-hbar/(3840*pi^2*t^4)`. Solving trace plus conservation alone gives

`rho=hbar/(15360*pi^2*t^4)+C/a^4`,
`p=hbar/(9216*pi^2*t^4)+C/(3*a^4)`.

Every `C` has the same trace and is conserved. The mode integral above, not
either of these two equations, selects `C=0`.

A physical negative control is a homogeneous conformal mixed state with
occupation `n(k)=exp(-k/s)` for `s>0`. Its rapidly decaying occupation produces
a smooth Hadamard state difference and

`delta rho_conf=hbar/(2*pi^2*a^4)*integral k^3*n(k) dk=3*hbar*s^4/(pi^2*a^4)`,

`delta <Phi^2>=hbar/(2*pi^2*a^2)*integral k*n(k) dk=hbar*s^2/(2*pi^2*a^2)`.

The second quantity is nonzero. In radiation it also gives
`delta rho_min-delta rho_conf=delta p_min-delta p_conf=H^2*delta<Phi^2>/2`.
Thus neither `C=0` nor equality of minimal and conformal stresses follows for
arbitrary states. This control is not substituted for the fixed reference.

## 4. EED and the absolute inequality

The physical stress has orthonormal covariant components `(rho,p,p,p)`. Hence

`E_ref=rho-(rho-3*p)/2=(rho+3*p)/2=3*rho=hbar/(5120*pi^2*t^4)`.

In A.2's `hbar/(16*pi^2)` units the reference contribution is `1/320*t^-4`.
Subtract it from the A.2 difference-bound functional, rather than from the
observable, to obtain the absolute lower bound `-hbar*B/(16*pi^2)`, with

`B=integral [hddot^2-3*hdot^2/(8*t^2)+(105/256-1/320)*h^2/t^4] dt`.

The last coefficient is `521/1280`. Weighted Hardy integration by parts gives

`B=||hddot||^2-(3/8)||hdot/t-3*h/(2*t^2)||^2-(559/1280)||h/t^2||^2`.

All subtracted terms are nonnegative, proving the absolute multiplier `1`.
This direction of the comparison is essential: a smaller `B` gives a stronger
lower bound `-B`. No numerical reference lower bound remains assumed.

There is also a positive representation of the sharper functional. With any
clock scale `t_*>0`, write `x=log(t/t_*)`, `h=t^(3/2)*u(x)`. Directly,

`hddot=t^(-1/2)*(u_xx+2*u_x+3*u/4)`,
`hdot=t^(1/2)*(u_x+3*u/2)`.

After changing variables, the raw integrand minus
`u_xx^2+17*u_x^2/8+161*u^2/1280` is exactly

`d/dx [2*u_x^2+3*u*u_x/2+15*u^2/16]`.

Compact support removes the boundary term. On `H2_0(t_-,t_+)`, both endpoint
jets vanish; the smooth change of variables on a strictly positive compact
interval and density establish the same identities. This proves `0<=B`.
Sampling through `t=0`, or retaining nonzero first-derivative endpoint traces,
does not satisfy this argument.

## 5. Renormalization freedom and gravitational limits

With the usual locally covariant scaling restrictions, finite stress changes
are `c1*m^4*g+c2*m^2*G+c3*I+c4*J`. The mass terms vanish. Every term in the
variation of `R^2` has a factor of `R` or a derivative of it, so `I=0`.
Conformal flatness gives zero Weyl tensor and zero Weyl-squared variation. In
four dimensions the local Gauss--Bonnet variation vanishes, and

`Ricci^2=(Weyl^2-Euler_density)/2+R^2/3`

therefore gives `J=0` too. This local variational statement uses compactly
supported metric variations, not boundary conditions at the excluded `t=0`.
It does not claim that `Ricci^2` itself vanishes: it equals `3/(4*t^4)`.

The nonzero anomaly term is not a counterterm that may freely be adjusted
within this prescription class. A negative control with `a(t)=t^(2/3)` gives
`H1_tt=8/t^4`, showing why the same argument cannot drop the finite curvature
freedom in arbitrary FLRW geometries.

If one allows independent dimensionful additions `lambda*g+gamma*G_FK`, they
lie outside the fixed matter prescription class above. Their EED on this
patch is

`delta E=-lambda-3*gamma/(4*t^2)`.

The code exposes that shift; it is not treated as zero for a total physical
source. Cosmological/Einstein couplings can instead remain on the gravitational
side of the SEE, where their values require the physical model specification.

Finally, a radiation Einstein tensor has zero trace, while the computed
reference has trace `-hbar/(3840*pi^2*t^4)`. It cannot source the specified
metric alone, nor can traceless classical radiation remove this mismatch.
A fixed cosmological term cannot cancel it on an interval. The new absolute
QSEI therefore closes the reference gap of this fixed-background calibration,
not the separate SEE, general-geodesic-coverage or cosmological-focusing gaps.

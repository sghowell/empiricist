# P8(a) A.4: a whole-patch exact-radiation SEE obstruction

This checkpoint upgrades A.3's reference-state mismatch to a statement about
every Hadamard state of the same field on the **whole** radiation patch. It is
an asymptotic obstruction to one exact ansatz, not a finite-slab no-go theorem,
a backreaction calculation, or a new incompleteness theorem. A.1--A.3 remain
immutable and are replayed through the pinned A.3 certificate.

## Hypotheses and source class

- The entire globally hyperbolic spacetime is
  `M=(0,infinity)_eta x R3`, with `g_FK=(A*eta)^2*(deta^2-dx^2)`, `A>0`,
  and `t=A*eta^2/2`. The observer is the comoving `U=partial_t`.
- The field is the real, free, massless, minimally coupled scalar. The state
  has a Hadamard two-point distribution on all of `M`, in the usual
  microlocal two-point sense. It need not be
  quasifree, homogeneous, isotropic, of finite total energy, or represented by
  spatially decaying or tempered Cauchy data. Hadamard is the usual state
  condition; global smoothness of a difference is a consequence, not an
  extra restriction on the state. No regularity assumption on all higher
  n-point distributions or on a Weyl characteristic functional is added.
- The matter stress uses precisely the common locally covariant,
  conservation-preserving massless prescription of A.3. Its reference is
  `W_ref=W_Mink/[a(eta)*a(eta')]`. The standard finite curvature ambiguities
  `I,J` vanish here. Independent dimensionful cosmological and Einstein
  couplings remain separate.
- The attempted equation is
  `b*G_FK + ell*g_FK + alpha*I + beta*J = -kappa*(<T>_omega + T_rad)`,
  with finite constants `b>0`, `kappa>0`, arbitrary finite `ell,alpha,beta`,
  and ordinary comoving homogeneous classical radiation
  `rho_rad=C/a^4`, `p_rad=rho_rad/3`, `0<=C<infinity`.
  No other quantum field, arbitrary traceful fluid, state-dependent
  counterterm, time-dependent coupling, or higher-order effective source is
  included. A fixed `lambda*g+gamma*G_FK` matter shift can equivalently be
  moved to the displayed constant couplings and cannot evade the argument.

No numerical value of a gravitational coupling is chosen. The illustrative
dimensionless error certificate below is not a cosmological parameter fit.

## Derived statement

For every admitted state and every fixed spatial point `x`,

`lim_(eta -> 0+) A^4*eta^8*E_omega(eta,x) = hbar/(320*pi^2)`,

or equivalently

`lim_(t -> 0+) t^4*E_omega(t,x) = hbar/(5120*pi^2) > 0`.

Here `E_omega=<T(U,U)>_omega-(1/2)*Tr_FK(<T>_omega)` is an absolute
renormalized EED. The convergence is uniform on any fixed compact spatial
set for a fixed state, but no rate or positive-onset time uniform over the
state class is asserted.

Consequently the displayed SEE has no solution with this exact metric on
the whole patch in the stated field/state/additional-source class. Its EED
component would instead require

`E_omega = (3*b*A^2/kappa-C)/(A^4*eta^4) + ell/kappa`,

whose `A^4*eta^8` multiple tends to zero. The strictly positive universal
limit supplies the contradiction. The conclusion is a necessary-equation
obstruction; no isotropy assumption on the quantum state is used.

## Exact state-dependent remainder interface

Define the smooth rescaled bisolution

`F(X,Y)=a(eta)*a(eta')*(W_omega-W_ref)(X,Y)`.

At equal points, let `f0=[F]`, `f1=[partial_eta F+partial_eta' F]`, and
`f2=[partial_eta partial_eta' F]`. The written Cauchy-extension proof shows
that these functions extend smoothly to `eta=0`. It does not extend the
degenerate physical metric or assume a physical state beyond the big bang.

`E_omega = hbar/(320*pi^2*A^4*eta^8)`
`          + A^(-4)*(eta^(-6)*f0-eta^(-5)*f1+eta^(-4)*f2)`.

Thus the difference is `O_(omega,x)(eta^(-6))`, or `O_(omega,x)(t^(-3))`.
If specified bounds `|f0|<=M0`, `|f1|<=M1`, `|f2|<=M2` hold on
`0<=eta<=eta1` and a specified compact spatial set, then

`|A^4*eta^8*E_omega-hbar/(320*pi^2)| <= M0*eta^2+M1*eta^3+M2*eta^4`.

These finite bounds exist state by state; the program does not infer them
from the word Hadamard. Given such bounds, it certifies a sufficient positive
SEE-residual margin on an entire interval by a monotone positive-coefficient
error polynomial. One coherent-state example provides actual exact bounds;
an oversized proposed interval is rejected.

## Deliberate boundaries

- No exclusion of an exact solution solely on a slab bounded away from
  `eta=0` is proved. No controlled approximation to radiation is excluded.
- The full spatial Cauchy-slice condition matters. A coherent state on the
  restricted region `eta>0, eta-x1>0`, with `chi=1/(eta-x1)`, changes the
  leading coefficient along `x=0`. Its data are singular on every full
  constant-eta slice; it is outside the theorem, not a counterexample.
- Adding a specially chosen negative traceful fluid can cancel the
  reference stress and restore the exact ansatz. That source is explicitly
  outside ordinary traceless radiation and is a tested exclusion control.
- Eventual positive EED for each fixed state is not pointwise nonnegative
  EED for all states at all times. The all-state sampled absolute QSEI is
  the separate A.3 result.
- The argument does not assert validity of the semiclassical approximation
  at arbitrarily high curvature, a new singularity theorem, realistic-field
  cosmological calibration, or completion of P8(a).

The next useful physical task is a controlled **backreacted** testbed and a
QSEI/reference-error estimate stable under its metric change. The exact
radiation formula cannot simply be inserted into an SEE focusing argument.

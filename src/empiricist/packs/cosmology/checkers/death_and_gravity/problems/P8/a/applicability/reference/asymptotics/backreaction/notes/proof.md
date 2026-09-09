# Derivation, controls and qualitative state-transport theorem

## 1. First-order Einstein equations

Write `a=a0*(1+epsilon*q)`, `a0=sqrt(2*A*t)`, and fix
`C_rad=3*A^2/kappa`. The physical density equation is
`3*H^2=kappa*(C_rad/a^4+epsilon*rho_ref)+O(epsilon^2)`.
Using `H=1/(2*t)+epsilon*qdot+O(epsilon^2)` and the pinned A.3 density gives

`3*qdot/t=-3*q/t^2+3*d/t^4`,

where `d=kappa*hbar/(46080*pi^2)`. Multiplying by `t/3` and integrating
`(t*q)'=d/t^2` gives `q=c_time/t-d/t^2`. Conservation and the independent
pressure equation give the same result. The code checks both components,
not just a trace or an unconstrained acceleration equation.

A variation `C_rad -> C_rad+epsilon*delta_C` adds
`delta_C/(4*C_rad)` to `q`. A shift `t -> t-epsilon*tau` adds
`-tau/(2*t)`. These are normalization and time-origin modes, not freely
adjustable state terms that remove the `t^(-2)` correction.

## 2. Exact solution of a declared reduced model

At zeroth order, `rho_ref=hbar*H0^4/(960*pi^2)` and
`H0^2=kappa*rho_rad/3`. Substitution **inside the first-order correction**
gives the surrogate
`rho_q,OR=epsilon*hbar*kappa^2*rho_rad^2/(8640*pi^2)`.
With `p_q,OR=5*rho_q,OR/3`, this is exactly conserved on any FLRW metric
because `rho_q,OR` is proportional to `a^(-8)`.

Set `y=a^4`. The reduced Friedmann equation becomes

`ydot^2=16*A^2*y+256*epsilon*d*A^4`.

On the expanding branch, integration gives
`y=4*A^2*((t-t0)^2-4*epsilon*d)`. Fix `t0=0`. Both density and pressure
equations and both conservation equations are checked independently. The
`a^(-8)` term is a closure of the reduced equations, not a new physical fluid
postulated to represent the RSET exactly. The order-reduction method is
discussed by [Parker--Simon, Sections II--III and Appendix B](https://arxiv.org/pdf/gr-qc/9211002v1).
Their general source coefficients and sign conventions are not substituted
for A.3's explicitly evaluated minimal-field coefficient.

This all-order completion is not unique. Replacing `a_OR` by
`a_OR*exp(epsilon^2*f(t))`, for any fixed smooth `f`, preserves its entire
first-order metric coefficient. At second order the physical density and
pressure defects change respectively by `3*f'/t+3*f/t^2` and
`-2*f''-3*f'/t+f/t^2`. The code verifies this ambiguity explicitly. Thus even
the reduced model's endpoint is not a first-order prediction about the
actual SEE.

With `S=t^2-4*epsilon*d>0`, the exact geometric quantities are

`H=t/(2*S)`, `R_FK=-12*epsilon*d/S^2`,

`a''/a=a^2*R_FK/6=-4*A*epsilon*d/S^(3/2)`.

Primes in the last formula refer to the actual conformal time `deta=dt/a`,
not to `t` and not to the unperturbed conformal coordinate.

For the linear term, integrating that clock gives
`eta=sqrt(2*t/A)*(1-epsilon*d/(3*t^2))+O(epsilon^2)` after fixing its
additive constant. Its inverse is
`t=A*eta^2/2+2*epsilon*d/(3*(A*eta^2/2))+O(epsilon^2)`.
Consequently

`a(eta)=A*eta-8*epsilon*d/(3*A*eta^3)+O(epsilon^2)`,

`a''/a=-32*epsilon*d/(A^2*eta^6)+O(epsilon^2)`.

Reusing `t=A*eta^2/2` exactly after backreaction gives a wrong coefficient;
the independent clock checks and negative control detect that error.

## 3. Rational Taylor and frozen-defect bounds

Let `z=4*epsilon*d/t^2`. For `0<=z<=1/4`, compare the positive polynomials

`L=1-z/4-z^2/9`, `U=1-z/4-3*z^2/32`

with `(1-z)^(1/4)`. The rational Bernstein coefficients of
`(1-z-L^4)/z^2` and `(U^4-(1-z))/z^2` on `[0,1/4]` are all nonnegative;
the first are strictly positive. Since `L,U>0` there, fourth powers preserve
order and give `L<=(1-z)^(1/4)<=U`. The apparent divisions by `z^2` are
exact polynomial cancellations; zero is covered by continuity. This proves
the two-sided Taylor bounds in the formulation without relying on decimal
root evaluations. Separate rational arithmetic reproduces every coefficient.

Replacing the actual quantum stress by the fixed A.3 stress on the new
metric leaves exact defects

`D_rho=3*epsilon*d*(1/S^2-1/t^4)`,
`D_p=5*epsilon*d*(1/S^2-1/t^4)`.

These equal the rational `z` expressions in the formulation. The ratio
`(2-z)/(1-z)^2` is increasing because its derivative is
`(3-z)/(1-z)^3>0`. At `z=1/4` it is `28/9`, proving the reported constants
`7/3`, `35/9`, and `7`. This is genuine numerical control of the frozen
defect, not of the missing response term. Frozen reference stress is only
conserved to the retained order on this metric; it is not silently promoted
to an exactly conserved RSET.

## 4. Smooth prepared states give an actual qualitative defect theorem

Fix a compact slab `J` bounded away from zero and the cutoff family specified
in the formulation. For small `|epsilon|` around zero, the radicand is
uniformly positive on the cutoff support, so the metric is jointly smooth
in `epsilon,t,x`; negative epsilon is used only as a mathematical parameter
neighborhood in the smoothness argument, not in the certified physical domain.
The past is exactly the common radiation metric. Its reference state's full
Cauchy data therefore define a unique state on every new metric by free-field
Cauchy evolution. The symplectic evolution preserves the CCR and positivity;
Hadamard singularities propagate. The prepared state is homogeneous,
isotropic, quasifree, and has zero one-point function. This is an actual
family of states, not an assumption that arbitrary metric-dependent states
vary continuously.

The metric change is compact in time but not space. To use the local
smoothness result of
[Hollands--Wald, Lemma 6.2, Eqs. (219)--(228)](https://arxiv.org/pdf/gr-qc/0404074v2),
fix a compact observation set and a common past Cauchy slice before the
cutoff. Uniform positivity of the scale factor on the intervening compact
time interval bounds coordinate light speeds. All causal footprints of the
observation set, for parameters in a small closed interval, therefore lie
in one compact spatial ball. Replace the metric perturbation outside a
larger ball by a smooth spatial cutoff. Interpolate its positive spatial
scale, keeping `g_tt=1`, so this auxiliary metric is Lorentzian and has the
same uniform speed bound. Its perturbation now has compact spacetime support.

The auxiliary and original metrics agree on all the relevant causal
footprints, and both states agree with the reference near the past slice.
Uniqueness and finite propagation in **each** two-point variable imply
equality of their two-point functions on the observation neighborhood. Thus
the compact-perturbation lemma proves that `W_epsilon-H_epsilon` is jointly
smooth there. The conserved stress prescription consists of finite local
derivatives at coincidence plus smooth local curvature terms, so its
orthonormal density and pressure are smooth in epsilon. Covering the compact
slab by finitely many such neighborhoods supplies a finite derivative bound:

`rho_epsilon-rho_ref=epsilon*r_rho(epsilon,t)`,
`p_epsilon-p_ref=epsilon*r_p(epsilon,t)`,

with bounded `r_rho,r_p` on the chosen compact parameter/slab set. Translation
symmetry of the original prepared family makes these same scalar components
independent of spatial position. This proves existence of local response
constants, not values for them.

The actual physical-sign Einstein defects are therefore

`D_rho,actual=D_rho-kappa*epsilon*(rho_epsilon-rho_ref)`,
`D_p,actual=D_p-kappa*epsilon*(p_epsilon-p_ref)`.

The frozen defects are `O(epsilon^2)`, and so are the subtracted response
terms. This establishes a qualitative compact-slab residual theorem for an
actual Hadamard-state/metric pair. A small residual by itself is not an
existence or shadowing theorem for the nonlinear SEE. Its size at the physical
`epsilon=1` remains unquantified until response constants and an appropriate
stability estimate are proved. The metric need not satisfy even the truncated
equation in its preparation region.

## 5. Counterterms and mode deformation do not disappear

Define `I_ab=(1/sqrt|g|)*delta integral sqrt|g| R^2/delta g^ab` in the FK
curvature convention. Then

`I_ab=2*R*R_ab-(1/2)*g_ab*R^2-2*(g_ab*Box-nabla_a*nabla_b)R`.

In particular `I_tt=2*R*R_tt-R^2/2-6*H*Rdot`, not the formula with the
opposite derivative sign. On the exact surrogate,

`I_tt=-18*epsilon*d*(7*t^2-4*epsilon*d)/S^4`.

Its linear density and pressure are `-126*epsilon*d/t^6` and
`-378*epsilon*d/t^6`; its trace is `1008*epsilon*d/t^6=-6*Box R` to that
order. Four-dimensional conformal flatness and Gauss--Bonnet imply `J=I/3`
for the corresponding Ricci-squared variation. Neither tensor vanishes once
the metric is perturbed. However a fixed **loop-order** coefficient
`epsilon*alpha*I` first contributes at order epsilon squared because `I[a0]=0`.
An independent order-zero coefficient `alpha0*I` contributes at first order
and lies outside this testbed. Fixed massless matter renormalization freedoms
are included in the smooth RSET response, not set to zero on the new metric.
For additional explicit gravitational terms `epsilon*alpha*I+epsilon*beta*J`,
move `(alpha*I+beta*J)/kappa` into the effective quantum source before using
the numerical response interface. Its supplied constants must bound that
total source difference; alternatively the explicit coefficients must be
absent. The qualitative smoothness and order counting remain valid either
way, but a numerical bound cannot silently ignore them.

The rescaled minimal modes obey `u_k''+(k^2-a''/a)*u_k=0`; this is not the
conformal field's flat equation when `R!=0`. For an expansion
`-a''/a=epsilon*V1+O(epsilon^2)` with retarded initial data, the linear
correction is

`u1(eta)=-integral_(eta_i)^eta sin(k*(eta-s))/k * V1(s)*u0(s) ds`,

where `u0=exp(-i*k*(eta-eta_i))/sqrt(2*k)`, `k>0`. The mode equation and
zero initial response are checked symbolically. On the uncut target segment,
`V1=32*d/(A^2*eta^6)` with the local clock choice above; the preparation
region has the cutoff-dependent potential instead. The integral must retain
that history. Copying zeroth-order modes at a finite time where the potential
is nonzero is not a proof of a Hadamard state. A first-order mode formula
alone supplies neither uniform ultraviolet subtraction bounds nor an actual
RSET/QSEI error estimate.

## 6. Completion boundary

This advances the controlled testbed beyond exact radiation without claiming
full backreaction or new focusing. A quantitative continuation needs the
state-response constants, control of the renormalized mode/parametrix
remainder, and a stability theorem in a specified solution class. General
cosmological existence results such as
[Gottschalk--Siemssen, Section 5](https://arxiv.org/pdf/1809.03812v3)
have explicit moment-space and coefficient hypotheses; they do not certify
those constants for this family automatically. A new QSEI estimate also
needs uniform microlocal/Fourier control, not just smooth diagonal stress.
No endpoint at `z=1` or physical singularity/bounce may be inferred from
extrapolating the reduced surrogate beyond the certified regime.

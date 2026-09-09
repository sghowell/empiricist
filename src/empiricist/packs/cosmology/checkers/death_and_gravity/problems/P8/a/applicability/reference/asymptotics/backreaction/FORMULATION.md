# P8(a) A.5: finite-slab first-order radiation backreaction

This checkpoint gives a first-order Einstein--radiation calculation, exact
error bounds for a declared order-reduced surrogate, and a qualitative
`O(epsilon^2)` actual semiclassical residual on compact positive-time slabs
for a specified transported Hadamard-state family. It does **not** solve the
semiclassical Einstein equation (SEE), evaluate its second-order response, or
transfer A.3's QSEI constants to a different metric. A.1--A.4 are immutable.

## Fixed conventions, expansion and source model

Use the A.3/A.4 FK convention `(+---)`, `G_FK=-kappa*T`, with `kappa>0`.
For the source convention `(-+++)`, `g_FK=-g_source` and
`R_ab,FK=-R_ab,source`, so `R_FK=+6*(Hdot+2*H^2)`. This is not P8(b)'s
scalar-curvature convention. Comoving proper time is `t`, and `c=1`.

The zeroth-order metric has `a0=sqrt(2*A*t)`, `A>0`. Classical comoving
radiation is separately conserved with `rho_rad=C_rad/a^4`,
`p_rad=rho_rad/3`, and fixed `C_rad=3*A^2/kappa`. The cosmological term is
zero. The free real scalar remains massless and minimally coupled, with the
same conserved locally covariant matter prescription as A.3.

Set `d=kappa*hbar/(46080*pi^2)>0`. Introduce an explicit dimensionless
bookkeeping amplitude `epsilon>=0` multiplying the entire quantum source.
The equation whose defect is studied is

`G_FK[g]+kappa*(T_rad[g]+epsilon*<T[g]>_omega)=0`.

This is a loop-order family at fixed `hbar`, with the physical equation at
`epsilon=1`. It is not a claim that arbitrarily chosen Hadamard states have
stress of order `hbar`: the reference and transported state family are fixed
below. Fixed finite loop-order curvature-squared terms may be included with
an explicit `epsilon` prefactor. Independent order-zero `I,J` gravitational
couplings are excluded; they would change the first-order equation.

## First-order result and the conserved surrogate

The pinned reference has
`rho_ref=hbar/(15360*pi^2*t^4)` and `p_ref=5*rho_ref/3`.
For `a=a0*(1+epsilon*q+O(epsilon^2))`, fixed radiation normalization gives

`qdot+q/t=d/t^3`, hence `q=c_time/t-d/t^2`.

The `c_time/t` term is the first-order time-origin mode. If radiation
normalization also varies by `epsilon*delta_C`, the additional constant
mode is `delta_C/(4*C_rad)`. Both modes are fixed to zero for the reported
comparison; neither is mistaken for a quantum coefficient.

Define, specifically as an **order-reduced surrogate**,

`rho_q,OR=epsilon*hbar*kappa^2*rho_rad^2/(8640*pi^2)`,
`p_q,OR=5*rho_q,OR/3`.

This source is conserved exactly because it scales as `a^(-8)`. Its exact
Einstein solution on the positive expanding branch is

`a_OR^4=4*A^2*(t^2-4*epsilon*d)`,

`a_OR=a0*(1-z)^(1/4)`, where `z=4*epsilon*d/t^2` and `0<=z<1`.

This is an exact solution of the displayed surrogate fluid equations, not
an assertion that the actual scalar-field RSET equals that fluid on the new
metric. It reproduces the evaluated A.3 stress to first order only.
Its all-order completion is a choice, not uniquely fixed by the first-order
SEE: multiplying `a_OR` by `exp(epsilon^2*f(t))` for smooth `f` preserves
first-order cancellation but changes second-order geometry. In particular,
the surrogate's zero at `t^2=4*epsilon*d` is not a predicted physical
singularity or bounce.

## Certified finite-domain bounds

On `0<=z<=1/4`, exact rational polynomial certificates prove

`3*z^2/32 <= 1-z/4-(1-z)^(1/4) <= z^2/9`.

The inequalities are non-strict at zero. No global optimality of the upper
coefficient is claimed. Negative amplitudes, a nonpositive radicand, invalid
time intervals, or use outside this certified `z` domain are rejected.

For the exact surrogate metric, define the physical-sign frozen-reference
Einstein defects

`D_rho=3*H^2-kappa*(rho_rad+epsilon*rho_ref)`,
`D_p=-2*Hdot-3*H^2-kappa*(p_rad+epsilon*p_ref)`.

Then

`D_rho=3*z^2*(2-z)/(4*t^2*(1-z)^2)`,
`D_p=5*z^2*(2-z)/(4*t^2*(1-z)^2)`.

Consequently on this domain

`0<=D_rho<=7*z^2/(3*t^2)`,
`0<=D_p<=35*z^2/(9*t^2)`,
`0<=(D_rho+3*D_p)/2<=7*z^2/t^2`.

These are computable bounds on the **frozen-reference** defect, not on the
unknown actual RSET response. The corresponding FK equation residual has
the opposite physical component signs, with identical absolute bounds.

## Actual state family and qualitative residual theorem

Fix `J=[t_minus,t_plus]` with `0<t_minus<t_plus<infinity`. Choose a smooth
temporal cutoff `chi`, compactly supported strictly after some `t_pre>0`,
equal to one on a neighborhood of `J`, with `0<=chi<=1`. For sufficiently
small `epsilon`, put

`a_epsilon(t)=a0(t)*(1-4*epsilon*d*chi(t)/t^2)^(1/4)`.

It equals exact radiation near a past Cauchy slice and equals `a_OR` on `J`.
The sufficient preparation-domain restriction is
`4*epsilon_bar*d/t_pre^2<1`. Transport the original reference state's full
Cauchy data by the minimally coupled Klein--Gordon equation on this smooth
metric, not by copying instantaneous Minkowski modes where curvature is
nonzero. The resulting homogeneous quasifree state `omega_epsilon` is
positive and Hadamard, with `omega_0=omega_ref`.

By local causal-footprint reduction to compact metric perturbations and the
Hollands--Wald smooth-state lemma, the renormalized stress is jointly smooth
in `epsilon` and spacetime near the diagonal. Therefore on each fixed slab
and compact spatial set

`<T[g_epsilon]>_(omega_epsilon)=T_ref+O(epsilon)`.

With the first-order cancellation above, the **actual** equation residual is
`O(epsilon^2)` locally on `J`. The constant can depend on the slab,
preparation, prescription and couplings. Existence of this constant is
proved qualitatively; no numerical value, uniformity across preparations,
nearby exact SEE solution, or control at `epsilon=1` is inferred.

If supplied response bounds satisfy
`|kappa*(rho_epsilon-rho_ref)|<=epsilon*M_rho` and
`|kappa*(p_epsilon-p_ref)|<=epsilon*M_p`, the verification interface combines
them with the explicit frozen defects. It refuses to invent these inputs.
The numeric interface example is explicitly conditional and synthetic, not
a derived bound on the actual state.
The displayed interface uses the equation as written, with no additional
explicit gravitational `epsilon*alpha*I+epsilon*beta*J` terms. If those are
included, the supplied response constants must also bound their moved-to-
source contribution `(alpha*I+beta*J)/kappa`; no bound for them is omitted
or assumed zero. Their zeroth-order value vanishes, so the qualitative
second-order conclusion is unchanged for fixed finite coefficients.

## Remaining physical obligations

For a quantitative SEE approximation, derive actual metric/state-response
bounds in the fixed prescription and prove an appropriate stability result.
The old massless minimal/conformal reference identification no longer holds:
`R_FK!=0`, and the rescaled modes have nonzero potential `-a''/a`. Curvature
counterterms vanish at zeroth order but not on the perturbed metric.

For a quantitative QSEI application, separately bound the perturbed reference
functional and its geometric correction. Smooth diagonal RSET dependence
alone does not justify a uniform-frequency QSEI estimate or an `H2` operator
bound for all sampling functions. Initial/final sampling domains, SEE
matching, relevant normal-geodesic coverage, and focusing thresholds remain
unresolved. No extrapolation to `z=1`, new singularity/bounce theorem, or full
P8(a) completion is claimed.

# P8(a) A.1: conditional local-QEI focusing optimization

This is the first independent P8(a) checkpoint. It does not depend on completing
P8(b), and it makes no change to the frozen bounce classification. The certificate
proves a restricted variational improvement and checks the algebra of its focusing
implication. It does **not** derive a quantum energy inequality for a realistic
field or certify a cosmological application.

## Frozen geometric problem

Use four spacetime dimensions, signature (+---), and the Ricci convention in
Fewster--Kontou, arXiv:2108.12668v1. Write `rho=R_mu_nu U^mu U^nu`; timelike
convergence has `rho <= 0` in this convention. `K` is the **trace** of the initial
second fundamental form, so `K=3H` in four-dimensional FLRW. These are not the
Ricci-sign conventions of arXiv:2209.04347v3.

Let `tau > 0`. Assume the normal timelike geodesics under consideration admit
smooth backward extensions to proper time `-tau/2`. On each future-directed
unit-speed timelike geodesic normal to a smooth spacelike Cauchy surface that
extends forward through proper time `tau`, impose the following hypotheses.
Failure of forward extension already gives future timelike incompleteness;
failure of the required backward extension is instead a failure of a hypothesis,
not an alternative proof of future incompleteness.

1. The metric and `rho` are smooth along the extended segment `[-tau/2,tau]`.
   This extended domain is required for the geometric statement itself, not
   only for the optional field interpretation below.
2. For every smooth real test function supported compactly inside an allowed
   window `I_c=(c-T(c)/2,c+T(c)/2)`, with `0 <= c < tau` and `T(c)=tau-c`,
   the **assumed local geometric inequality** is
   `integral rho*h^2 <= Q2*integral (h'')^2 + Q0*integral h^2`,
   where `Q2 >= 0`, `Q0 >= 0`. Only windows inside the extended geodesic are used.
3. Initially `rho(t) <= rho0 <= 0` for `0 <= t <= tau/4`.

The pointwise initial assumption is explicit: this checkpoint is not an
incompleteness theorem assuming quantum inequalities alone.

The dimensionless demonstration freezes
`Q2/tau^2=1/10^6`, `Q0*tau^2=1/100`, `rho0*tau^2=0`.
These are conditional mathematical inputs, not particle masses, a state
temperature, measurements, or a claim of cosmological-scale validity.

## Trial and partition domain

Set `r=3/4`, `a=1-r=1/4` and first measure time in units of `tau`.
The partition nodes are `t_j=1-r^j` (`j=0,1,...`). On each cell
`[t_j,t_(j+1)]`, let `x=(t-t_j)/(a*r^j)` and rotate by
`theta(x)=(pi/2)*p(x)`, `p(x)=3x^2-2x^3`. The two active partition functions
are `cos(theta)` and `sin(theta)`. Their first derivatives vanish at joins;
the functions are piecewise smooth and C1, hence admissible in H2 after
multiplication by the specified trial and extension by zero.

The focusing function `g` equals one initially and has tail
`g(t)=q((1-t)/r)` for `a <= t <= 1`. The QEI test function `f` equals
`p(t/a)` initially and equals `g` thereafter. Keep the initial rising cutoff
fixed and vary only

`q(s)=p(s)+c0*s^2*(1-s)^2+c1*s^2*(1-s)^2*(2s-1)`.

Thus `q(0)=q'(0)=q'(1)=0`, `q(1)=1`. Every real `(c0,c1)` is admitted; no
unproved bound `0 <= q <= 1` is needed on the tail. On the initial segment the
fixed `p` does obey `0 <= p <= 1`. The tail vanishes quadratically, ensuring
convergence of the infinite localized H2 sum.

## What counts as certified

- Exact polynomial identities, exact cell integrals, and the full infinite
  geometric tail; no finite-tail truncation enters the bound.
- Strict support containment for every partition member; H2 density justifies
  the extension of the local smooth-test inequality used here.
- The unique minimum of the resulting **two-dimensional trial functional** for
  the frozen partition, parameters, cutoff and duration.
- Validated rational enclosures of that minimum, its positive improvement over
  the cubic trial in the **same** functional, and an illustrative contraction
  threshold which separates those two sufficient tests.
- The written Raychaudhuri/index-form implication under the geometric
  hypotheses. The machine checks its algebra, not the entire differential
  geometry or global causal theory in a proof assistant.

The result is not a global optimum over partitions, cutoff durations, all H2
tests, geometries or quantum states, and not a numerical improvement claimed
over every published theorem under its different trial choices.

## Conditional scalar-field dictionary

An optional interpretation uses a minimally coupled real linear Klein--Gordon
field of mass `m`, a Hadamard state, a fixed renormalization prescription, the
semiclassical Einstein equation `G_mu_nu=-kappa*<T_mu_nu>`, and the explicitly
assumed local QSEI plus Wick-square bound. If

`<EED>(h^2)+(m^2/2)*<Phi^2>(h^2) >= -C*hbar/(16*pi^2)*||h''||^2`

on each required window and `|<Phi^2>| <= phimax^2`, then

`Q2=kappa*C*hbar/(16*pi^2)`, `Q0=kappa*m^2*phimax^2/2`.

For `kappa=8*pi*G`, these become `C*G*hbar/(2*pi)` and
`4*pi*G*m^2*phimax^2`. This algebra does not establish the duration of the
local QSEI, its curvature/reference-state errors, the state bound, or validity of
the semiclassical equation. Those must be supplied for a physical application.
Additional matter, a cosmological constant or curvature counterterms cannot be
silently omitted from that matching. The source-equation dictionary is in
[notes/sources.md](notes/sources.md).

## Open work

Derive quantitatively justified local QEI/QSEI validity scales and reference-state
corrections; calibrate field and state bounds; optimize larger trial/partition
families; handle additional realistic fields and interactions; test a cosmological
example inside the approximation domain. Null, nonminimal, and worldvolume
extensions are separate tasks. No P8(a) completion or exclusion of a P8(b) bounce
is claimed.

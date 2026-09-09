# Exact localization and the conditional focusing improvement

All formulas below are independently derived for the frozen problem in
[FORMULATION.md](../FORMULATION.md). Time is dimensionless until section 4.

## 1. Local supports, Sobolev validity and the infinite sum

Let `t_j=1-r^j`, `h_j=(1-r)r^j`, `r=3/4`. On each cell the active pair is
`cos(theta_j), sin(theta_j)` with
`theta_j=(pi/2)p((t-t_j)/h_j)` and `p(x)=3x^2-2x^3`.
An interior partition member has support `[t_(j-1),t_(j+1)]`.
At its support midpoint `c`, its width divided by `T(c)=1-c` is

`2(1-r^2)/(1+r^2)=14/25 < 1`.

The first localized product is supported on `[0,1-r]`; its ratio is
`2(1-r)/(1+r)=2/7 < 1`. Every support therefore sits strictly inside an allowed
open window. In particular, the first window has midpoint `1/8` and is
`(-5/16,9/16)`: the geometric hypotheses explicitly require the smooth extended
geodesic domain `[-1/2,1]`, so its negative-time part is available. This extension
is not reserved for the field interpretation. The negative-control choice
`r=1/2` has interior ratio `6/5`, so using those windows would be invalid.

At each join the angle derivative vanishes. Products `f*phi_j`, extended by
zero, have continuous first derivatives, square-integrable piecewise second
derivatives, and compact support inside a window. Smooth approximation in H2
preserves both right-hand-side norms. Smooth `rho` on each compact window makes
the left side continuous under the same approximation. Thus the assumed QEI
applies to these H2 products without asserting that the partition is C-infinity.

The products obey `sum_j (f*phi_j)^2=f^2` pointwise. For a polynomial tail
vanishing to order at least two, the exact derivative sums in section 2 converge.
On a geodesic reaching `t=1`, smooth `rho` is bounded on its compact segment, so
`sum_j integral |rho| (f*phi_j)^2=integral |rho| f^2 < infinity`.
The passage to the infinite sum is consequently justified. It gives

`integral rho*f^2 <= Q2*sum_j ||(f*phi_j)''||^2 + Q0*||f||^2`.

## 2. An exact quadratic functional, with no triangle-inequality loss

For any cell functions `v,w`, differentiation of the rotating pair gives the
radial and tangential components

`A_v=v''-(theta')^2*v`, `B_v=2*theta'*v'+theta''*v`.

Orthogonality of the rotation proves

`((v cos theta)'')^2+((v sin theta)'')^2=A_v^2+B_v^2`.

In a unit cell, write `z=pi^2`, `d=p'/2`, `e=p''/2`. The polarized integral is

`E(v,w)=integral [v''w''+z{-d^2(v w''+v'' w)+(2dv'+ev)(2dw'+ew)}+z^2 d^4 v w] dx`.

This is a polynomial in `z` of degree two with rational coefficients for rational
polynomials `v,w`. Its diagonal is nonnegative at `z=pi^2` by the preceding
sum-of-squares identity, even though some expanded coefficients can be negative.
A physical cell length `h` contributes `h^(-3)`.

Write `q(s)=sum_(k>=2) b_k s^k`. On tail cell `j>=1`, let
`w(x)=1-(1-r)x`, so `q((1-t)/r)=sum b_k r^(k(j-1))w(x)^k`.
The exact infinite localized norm is

`S(q)=E(p,p)/(1-r)^3 + sum_(k,l>=2) b_k b_l E(w^k,w^l)/[((1-r)r)^3*(1-r^(k+l-3))]`.

The geometric exponent is `k+l-3>0`. Replacing its denominator or omitting the
remainder invalidates this formula. After cells `j=1,...,N`, the exact remaining
term for each `(k,l)` carries the additional factor `r^((k+l-3)N)`.
This is a sum of localized squared norms, not a signed error we may discard.

`independent.py` recomputes all three coefficients of every entry in the
three-basis tail Gram matrix with FLINT polynomial arithmetic, independently of
the SymPy integrator. It also integrates four finite cells by direct polynomial
substitution and verifies exact equality with the infinite sum minus its explicit
remainder. As a known answer,

`E(p,p)/(1-r)^3 = 768 + (6848/35)z + (1728/715)z^2`.

## 3. From the local bound to focusing

Let `g=1` initially and `g=q((1-t)/r)` thereafter; `f=p(t/(1-r))` initially
and `f=g` thereafter. Since `0<=p<=1`, the initial upper Ricci bound yields

`J[g]=integral [3(g')^2+rho*g^2]`

`<= Q2*S(q)+Q0*[(1-r)*13/35+r*integral q^2]`

`   +(3/r)*integral (q')^2+rho0*(1-r)*22/35`.

No bound on the sign or magnitude of the tail `q` was used.

For completeness, on a hypersurface-orthogonal geodesic congruence without a
focal point, the expansion satisfies, in the frozen Ricci convention,

`theta'=rho-theta^2/3-sigma^2`, with `sigma^2>=0`.

An exact integration-by-parts identity gives

`J[g]=-K+integral [3(g'-theta*g/3)^2+sigma^2*g^2]`,

using `g(0)=1`, `g(1)=0`, `theta(0)=K`. If there is no focal point through the
terminal time, smooth bounded expansion makes this strictly greater than `-K`:
equality would require `g'-theta*g/3=0` almost everywhere, whose solution with
initial value one cannot vanish at a finite endpoint. Therefore any trial with
`J[g] <= -K` forces a focal point at or before the terminal time.

This is a conditional geometric implication, not a numerical ODE experiment.
With the hypotheses imposed uniformly on all normal geodesics from a smooth
spacelike Cauchy surface in a globally hyperbolic spacetime, the usual maximizing
geodesic argument gives no timelike curve from that surface longer than the
terminal time, hence future timelike geodesic incompleteness. The certificate
checks the algebraic identities and constants; it does not formalize that global
causal theorem in a proof assistant. Reversing time gives the corresponding past
statement with the reversed initial normal and contraction sign.

## 4. Units and the certified finite-family optimization

Restore a general `tau` and set
`alpha=Q2/tau^2`, `beta=Q0*tau^2`, `zeta=rho0*tau^2`. Then
`J <= nu`, where `nu*tau` equals the dimensionless expression in section 3 with
`Q2,Q0,rho0` replaced by `alpha,beta,zeta`.

For the frozen demonstration `alpha=10^-6`, `beta=10^-2`, `zeta=0`, let

`q=p+c0*psi+c1*psi*(2s-1)`, `psi=s^2*(1-s)^2`.

The exact bound has form `B(c)=B0+2*l^T*c+c^T*G*c`, with entries rational in
`z=pi^2`. The positive gradient term alone is positive definite on the two
independent zero-endpoint variations; the localized and L2 terms are nonnegative.
Thus `G` is positive definite. Independently, Arb certifies its two Sylvester
minors at `z=pi^2`. Exact linear algebra gives

`c_*=-G^(-1)l`, `B_*=B0-l^T*G^(-1)l`,

and `B(c)-B_*=(c-c_*)^T*G*(c-c_*)`. This proves the unique global minimum in
the frozen two-dimensional affine family, not among all admissible test
functions. The coefficients are approximately `(-0.2684397319,-3.982815719)`;
the report retains their exact rational functions of `pi^2`.

Outward Arb arithmetic at 192 bits certifies

- `4.8747718 < B0 < 4.8747719` (unmodified cubic trial, same partition).
- `4.4445507 < B_* < 4.4445508` (optimized trial).
- `8.825% < 100*(B0-B_*)/B0 < 8.826%`.

Consequently initial contraction `-K*tau=9/2` is sufficient under the hypotheses
with the optimized trial, but not certified by the cubic bound or the initial
classical-SEC estimate `3/(tau/4)=12/tau`. Failure of either sufficient test
does **not** prove completeness. These dimensionless constants have not been
matched to a realistic field state or a controlled cosmological background.

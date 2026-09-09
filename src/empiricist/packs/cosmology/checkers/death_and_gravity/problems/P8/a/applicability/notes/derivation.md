# Radiation-patch QSEI derivation and verification

## 1. Exact field map and its domain

For a Fourier mode, the minimally coupled massless equation is

`phi''+2(a'/a)phi'+k^2 phi=0`.

Substitution `chi=a*phi` gives
`chi''+(k^2-a''/a)chi=0`. Therefore `a=A*eta`, `eta>0`, has reference modes
`exp(-ik*eta)/(a*sqrt(2k))`. Their Wronskian satisfies
`a^2*(phi*conj(phi)' - phi'*conj(phi))=i`, preserving the canonical commutator
with the usual creation/annihilation normalization (hbar is retained in W).
The inverse field map exists everywhere on this open patch.

The half-space `eta>0` with flat metric is globally hyperbolic, as is its smooth
positive conformal rescaling. The rescaled vacuum two-point function is a
positive bisolution with the correct commutator. Its Hadamard wavefront set is
preserved by the smooth nonvanishing factors and the conformal light cones.
This constructs the required reference state; it does not assert that arbitrary
minimally coupled FLRW fields are conformally invariant. For the negative
control `a=A*eta^2`, the same proposed modes have a nonzero KG residual.

On the comoving curve, `partial_t phi=a^-2 Dchi` where
`D=partial_eta-1/eta`. Since `dt=a*deta`, proper-time weighting becomes

`integral dt h(t)^2 :E: = integral deta f(eta)^2 :(Dchi)^2:`,

`f=a^-3/2 h(t(eta))`.

Here colons mean a state difference relative to the stated reference. The
geometric field map also maps the states to Hadamard states on the Minkowski
half-space. Apply the positive-type worldline lemma there, with Minkowski proper
time **eta** and the real smooth differential operator `D`. Thus no improper
substitution of conformal time for radiation proper time is made in a theorem
requiring proper-time parametrization.

## 2. Positive-type bound and exact spectral integral

The diagonal restriction of the smooth symmetric two-point state difference
can be written with a Fourier delta function. Restricting the symmetric Fourier
integral to positive frequency and discarding the nonnegative target-state
term gives the usual difference-QEI construction. For our reference,

`W_Mink(eta,eta';0)=hbar/(4*pi^2)*integral_0^infinity k*exp(-ik(eta-eta')) dk`.

Use `F(u)=integral exp(-iu*eta)f(eta) deta`, `B(u)=Fourier(f/eta)`. The reference
mode amplitude after differentiation is `-ik*F(alpha+k)-B(alpha+k)`.
Its squared norm is

`k^2 |F|^2+|B|^2-2k Im(F conj(B))`.

Changing to `u=alpha+k`, integrating `0<=k<=u`, and keeping all factors gives

`Q=hbar/(4*pi^3)*integral_0^infinity [u^4|F|^2/4+u^2|B|^2/2-(2/3)u^3 Im(F conj(B))] du`.

Real `f` and `f/eta` make each full integrand even after extending to negative
`u`. With the stated Fourier convention,
`integral f''(f/eta)' = -(1/(2*pi))*integral_R u^3 Im(F conj(B)) du`.
Parseval consequently yields

`Q=hbar/(16*pi^2)*integral [f''^2+2((f/eta)')^2+(8/3)f''(f/eta)'] deta`.

The same integrand equals

`[f''+(4/3)(f/eta)']^2+(2/9)[(f/eta)']^2`.

This proves positivity of the functional without a pointwise sign argument
about a subsequently integrated-by-parts density. Smooth compact support makes
the Fourier integrals finite; extension to H2 tests is by density, with all
weights bounded on the fixed positive-time support interval.

## 3. Exact curvature corrections in proper time

Two integration-by-parts steps in conformal time give

`16*pi^2*Q/hbar=integral [f''^2+6*f'^2/eta^2-12*f^2/eta^4] deta`.

The difference of the preceding positive-form density and this one is the
derivative of

`-8*f*f'/(3*eta^2)+4*f'^2/(3*eta)-14*f^2/(3*eta^3)`.

Substitute `t=A*eta^2/2`, `a=sqrt(2*A*t)`, `d/deta=a*d/dt` and `f=a^-3/2 h`.
The resulting proper-time density before its final integration by parts is

`hddot^2-2*hdot*hddot/t+15*h*hddot/(8*t^2)+5*hdot^2/(2*t^2)`

` -33*h*hdot/(8*t^3)+249*h^2/(256*t^4)`.

Subtracting the derivative of
`15*h*hdot/(8*t^2)-hdot^2/t-3*h^2/(16*t^3)` leaves

`hddot^2-3*hdot^2/(8*t^2)+105*h^2/(256*t^4)`.

All boundary terms vanish on the specified H2_0 domain. The scale normalization
`A` cancels, as expected for the proper-time expression on a radiation patch.

The weighted Hardy identity is

`||hdot/t-3h/(2t^2)||^2=integral hdot^2/t^2-(9/4)*integral h^2/t^4`.

It follows by integrating the derivative of `-3*h^2/(2*t^3)`. Therefore

`16*pi^2*Q/hbar=||hddot||^2-(3/8)||hdot/t-3h/(2t^2)||^2-(111/256)||h/t^2||^2`.

Both subtracted quantities are nonnegative. Thus this exact **difference** QSEI
has the Minkowski derivative coefficient for every compact sampling interval
strictly above zero, without assuming local flatness or a small duration.
For nonzero tests the positive-form representation gives `Q>0`, while the
strictly positive second subtraction gives `Q<hbar*||hddot||^2/(16*pi^2)`.
Neither fact implies nonnegative renormalized EED in arbitrary quantum states.

## 4. Reference-state credit and a conditional duration estimate

The absolute inequality retains `integral h^2 E_reference` on its right side.
Assume, only for this bridge, an independently justified bound

`E_reference >= -beta*hbar/(16*pi^2*t^4)`, `beta>=0`.

Combining it with section 3 leaves a potentially negative contribution only if
`delta=max(0,beta-111/256)>0`; dropping the nonnegative Hardy credit is safe.
On `I=(t_c-L/2,t_c+L/2)`, with `t_min=t_c-L/2>0`,

`integral h^2/t^4 <= t_min^-4*||h||^2 <= L^4/(pi^4*t_min^4)*||hddot||^2`.

The last bound applies the ordinary Dirichlet Poincare inequality to `h` and to
`hdot`, both of which have zero endpoint traces for `h in H2_0(I)`. It is not
claimed sharp for the clamped fourth-order problem. This proves the multiplier

`C=1+delta*(L/t_min)^4/pi^4`.

For the **conditional** example `beta=1`, `L/t_c=1/2`, the multiplier lies between
`1.0011485` and `1.0011487`. For `beta<=111/256`, it is exactly one, irrespective
of duration as long as the support remains in the patch. These are not measured
or derived reference stress bounds. When such a bound has not been supplied,
the interface refuses to output an absolute or Ricci verdict.

## 5. Independent checks and the physical boundary

The symbolic replay checks mode normalization, the spectral moments, both
coordinate changes, every boundary term and the Hardy completion. A separate
FLINT Laurent-polynomial integrator uses `A=2`, `t=eta^2` to integrate directly
in proper time on `[1,2]` and conformal time on `[1,sqrt(2)]`. It verifies the
proper density, conformal density and conformal positive form for two distinct
H2_0 polynomial tests. Integrals are exact rational combinations of `1,log(2)`.

For `h=(t-1)^2(2-t)^2`, the normalized flat norm is `4/5`, while the curved norm is

`-75587/1280+(2763/32)*log(2)`.

Arb verifies it lies in `(0.7965831,0.7965832)`, positive and below `4/5`.
Negative controls reject a sampling window meeting `t=0`, absent reference
input, incorrect endpoint jets, finite mass/generic-expansion mode substitution
and reversed Fourier cross signs. A negative pointwise reduced density is not
misread as a negative value of the integrated QEI functional.

The radiation patch is genuinely curved: `R=0`, but its Kretschmann invariant
is `3/(2*t^4)`. Comoving lines are geodesics and are all the normals to a
constant-t slice. These limited coverage facts do not solve the semiclassical
Einstein equations. In particular, the reference or target scalar stress has
not been shown to source the chosen radiation metric, and no new singularity
theorem follows merely from its finite-age coordinate domain.

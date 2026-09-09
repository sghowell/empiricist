# P8(a) A.2: an exact curved-background difference QSEI

This checkpoint addresses part of A.1's uncalculated local-duration input. It
derives a quantitative **difference** quantum strong energy inequality on one
specified curved spacetime. It does not certify a self-consistent semiclassical
solution or complete P8(a). The prior A.1 files and certificate remain unchanged.

## Fixed field, spacetime, reference and observable

- Four-dimensional spatially flat radiation FLRW patch
  `ds^2=a(eta)^2(deta^2-dx^2)`, `a(eta)=A*eta`, `A>0`, `eta>0`.
  The spatial sections are R3. Proper cosmic time is `t=A*eta^2/2>0`.
- A free, real, **massless minimally coupled** scalar field. No other fields,
  interactions, nonminimal stress tensor, or finite mass are included.
- The reference Hadamard state is obtained by rescaling the Minkowski vacuum
  restricted to the half-space `eta>0`:
  `W_reference=W_Minkowski/[a(eta)*a(eta')]`.
- The state of interest may be **any Hadamard state** of this field on the fixed
  patch; it need not be the reference or spatially homogeneous.
- The observer is comoving, with physical proper time `t`. The observable is
  the effective energy density `E=T(U,U)-Tr(T)/2`, not simply `T(U,U)`.
  Its state difference equals the state difference of `(partial_t phi)^2`.
- A common, fixed locally covariant stress-tensor renormalization prescription
  is used for the reference and target states. State-independent terms cancel
  in their difference, but are retained in `E_reference(t)` when converting
  back to the absolute renormalized observable. Nothing sets this term to zero.

The field map is exact only because `a''=0`: `chi=a*phi` obeys the massless
Minkowski equation on the half-space and preserves the canonical commutator.
The same plane-wave prescription fails for generic minimally coupled FLRW
fields. The radiation patch has vanishing Ricci scalar but nonzero curvature;
it is not being treated as flat spacetime physically.

## Sampling domain and exact result

Initially take real `h in C_c^infinity((0,infinity))` in physical proper time.
Equivalently, its support lies in some finite interval `[t_-,t_+]` with `t_->0`.
The extension to `H2_0(t_-,t_+)` uses density; both the function and its first
derivative vanish at the endpoints. No sampling across `t=0` is admitted.

With `f(eta)=a(eta)^(-3/2)*h(A*eta^2/2)`, the positive-type construction gives

`integral h^2(E_omega-E_reference) dt >= -Q[h]`,

`Q[h]=hbar/(16*pi^2)*integral [hddot^2-3*hdot^2/(8*t^2)+105*h^2/(256*t^4)] dt`.

This functional is nonnegative, despite the negative term in this particular
integrand. An exact positive representation in conformal time is proved in
[notes/derivation.md](notes/derivation.md). Weighted Hardy completion further gives

`Q[h]=hbar/(16*pi^2)*[||hddot||^2-(3/8)||hdot/t-3h/(2t^2)||^2-(111/256)||h/t^2||^2]`.

Thus `0 <= Q[h] <= hbar/(16*pi^2)*||hddot||^2` for the full admitted sampling
domain: the **difference bound** needs no assumed small averaging duration in
this exact testbed. The computed `Q` is not asserted to be the optimal QEI over
states, and the negative correction is not a negative QEI functional.

## Absolute and geometric bridges are conditional

The absolute inequality is

`integral h^2 E_omega dt >= integral h^2 E_reference dt - Q[h]`.

For example, **if separately established** that
`E_reference(t) >= -beta*hbar/(16*pi^2*t^4)`, `beta>=0`, then `beta<=111/256`
suffices for an absolute Minkowski-coefficient bound over every admitted test.
We do not compute or assume that the actual reference satisfies this hypothesis.

For arbitrary supplied `beta`, on
`I=(t_c-L/2,t_c+L/2)`, `t_c>0`, `0<L<2*t_c`, write `t_min=t_c-L/2`.
The elementary two-step Dirichlet Poincare bound on `H2_0(I)` proves the
sufficient absolute multiplier

`C=1+max(0,beta-111/256)*(L/t_min)^4/pi^4`.

It is an upper estimate on the required negative-energy bound, not an optimal
duration threshold. The exact sample `beta=1, L/t_c=1/2` is a **conditional
reference-input example**, not a field calibration. API functions reject missing
reference input instead of substituting a zero vacuum stress.

Only **if additionally** the chosen metric and target state solve the correctly
specified semiclassical Einstein equation can this be converted to A.1's Ricci
inequality. A convenient sufficient pair on a window is then

`Q2=kappa*hbar/(16*pi^2)`,
`Q0=kappa*hbar*max(0,beta-111/256)/(16*pi^2*t_min^4)`.

Additional sources, cosmological constants and curvature counterterms must be
included in that physical matching; they are not inferred away by this formula.

## Coverage and explicit nonclaims

The bound holds along every comoving line because the reference is spatially
homogeneous. These are exactly the normal geodesics of constant-cosmic-time
FLRW slices; this restricted coverage is checked. No other Cauchy surfaces,
tilted observers, perturbed backgrounds or arbitrary semiclassical solutions are
covered by the calculation. The cosmic-age variable `t` here is not silently
identified with A.1's proper-time origin on an initial Cauchy surface.

No absolute reference EED, reference-bound coefficient beta, self-consistent SEE
solution, new incompleteness theorem, realistic-field-strength cosmological
application, or exclusion of a P8(b) bounce is certified. The radiation metric's
known finite-age endpoint is not being advertised as a new theorem.

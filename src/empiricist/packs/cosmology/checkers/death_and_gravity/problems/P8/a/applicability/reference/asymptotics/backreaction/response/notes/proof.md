# Retarded linear response: derivation and verification boundary

All first variations are at epsilon zero. The common-past state is fixed by
its full Cauchy data, and hbar is displayed. The trusted inputs and sign
dictionary are in [sources.md](sources.md); no new SEE existence or QSEI
theorem is used.

## 1. Actual state and differentiating renormalized coincidence

The proper-time family and cutoff are specified in the formulation. For
small positive and negative epsilon the radicand is positive, and the
family is smooth. A past slice strictly before preparation has exactly the
radiation metric and reference state. Free Klein--Gordon evolution preserves
the CCR, positivity and the quasifree property; the Hadamard condition
propagates. Homogeneity and isotropy are preserved too.

The A.5 proof localizes this temporally compact but spatially homogeneous
metric change outside a common compact causal footprint, in each two-point
variable, to apply Hollands--Wald Lemma 6.2. Consequently `W_epsilon-H_epsilon`
is jointly smooth in the metric parameter and near-diagonal coordinates on
each compact observation region when a full smooth parametrix is used.
For the finite GS truncations one takes the order sufficiently high for
each derivative under discussion; higher omitted terms do not affect its
required coincidence value. No fixed finite truncation is claimed to have
a C-infinity remainder for all derivative orders. The coincidence operation and its finite
derivatives commute with the first parameter derivative. This justifies
identifying the differentiated, subtracted mode expression below with the
actual renormalized observable. It does not bound the second or higher
parameter derivatives uniformly by the new first-derivative constants.

Use the actual conformal coordinate of each metric with the same past
origin. At first order write `a_epsilon(eta)=A*eta*(1+epsilon*b(eta)+...)`.
For `Q(eta)=q(A*eta²/2)` and `J'=Q`, `J=0` before preparation, clock
conversion gives `b=Q+J/eta`. Therefore

    V=-b''-2*b'/eta=-Q''-3*Q'/eta.

The finite family is not replaced by a family with frozen unperturbed
conformal clock. Its exact rescaled modes obey
`v_k''+(k²+epsilon*V+O(epsilon²))*v_k=0`.

## 2. Born normalization, infrared behavior and spatial splitting

Choose the harmless common-past phase so that `v0=e^(-ik eta)/sqrt(2k)`.
Variation of the retarded mode equation gives

    v1(eta)=-integral_(eta_i)^eta sin(k*(eta-s))/k * V(s)*v0(s) ds,

with zero variation of both initial data. Taking `2 Re(conjugate(v0)*v1)`
gives exactly

    delta |v_k(eta)|²= -1/(2*k²) * integral_(eta_i)^eta
                                      V(s)*sin(2*k*(eta-s)) ds.

The factor includes both the real-scalar mode normalization and the real
part. At small k this is `O(1/k)`, so the radial `k² dk` Wick-square measure
is infrared integrable. There is no arbitrary mass regulator or infrared
state inserted into the model. At large k the leading term is
`-V(eta)/(4*k³)`, producing the expected logarithmic subtraction.

At equal conformal time and spatial separation `r>0`, use the GS Fourier
normalization `G=(1/(2*pi²))*integral k² |v_k|² sinc(kr) dk`, where `G`
is the two-point function of the rescaled field. Abel-regularize in k before
interchanging the finite history integral. The elementary Fourier integral
has the distributional limit

    integral_0^infinity sinc(kr)*sin(2*k*x) dk
      = 1/(2*r)*log |(2*x+r)/(2*x-r)|.

Thus, with `D=eta-eta_i`,

    delta G(eta,r)=-hbar/(8*pi²*r) * integral_0^D
                         V(eta-x)*log |(2*x+r)/(2*x-r)| dx.

The interior logarithm at `x=r/2` is integrable. For the constant part of V,
the integral is exactly

    D*log((2*D+r)/(2*D-r))
       +(r/2)*log((4*D²-r²)/r²),       0<r<2D.

After division by r its small-r expansion is `log(2D/r)+1+o(1)`.
The finite `+1` is essential. For the difference
`g(x)=V(eta-x)-V(eta)=O(x)`, the divided kernel converges to `1/x`.
The interval `x<=r` contributes `O(r*||V'||)` after scaling `x=r*y`;
on `x>=r` the logarithm is bounded by a constant times `r/x`, allowing
dominated convergence. Hence

    delta G = hbar/(8*pi²) * [V*log(r)-Fp_T[V]-V*(log(2T)+1)] + o(1),

where the explicitly defined retarded finite part is

    Fp_T[V]=lim_(delta->0) [integral_delta^D V(eta-x)/x dx
                            + V(eta)*log(delta/T)]
           = integral_0^D (V(eta-x)-V(eta))/x dx + V(eta)*log(D/T).

This is a defined Hadamard finite part, not a divergent integral treated as
an ordinary function. Since V and all its jets vanish at the past start,
integration by parts gives
`Fp_T[V]=integral_(eta_i)^eta V'(s)*log((eta-s)/T) ds`.

## 3. The local Hadamard piece fixes the finite constant and scale

The raw GS spatial parametrix of physical length lambda has the expansion

    a² H_lambda = hbar*[1/(4*pi²*r²)+a''/(48*pi²*a)
                       + V/(16*pi²)*log(r²*a²/(2*lambda²)) + O(r² log r)].

Here `V=-a''/a` for the minimal massless field. Its first variation is
`hbar/(8*pi²)*[-V/6+V*log(r*A*eta/(sqrt(2)*lambda))]`.
Subtracting it from the preceding exact spatial finite part gives

    delta [W-H_lambda]
      =-hbar/(8*pi²*A²*eta²) * [Fp_T[V]
                         +V*(log(sqrt(2)*A*eta*T/lambda)+5/6)].

This proves the formulation's F1 and K. The coefficient `5/6` is `1-1/6`,
not a choice left implicit in the retarded integral. T cancels because
`integral V'=V(eta)`. Derivatives of the logarithmic convolution can be
transferred onto successive derivatives of V, extended by zero into the
past; flatness removes boundary terms. This gives smooth K even though
the integrand's endpoint logarithm is singular.

As a kernel-only positive control, for `V(s)=(s-eta_i)^n`, `n>=1`, one gets

    K=D^n*[log(sqrt(2)*A*eta*D/lambda)+5/6-H_n].

These finite-order polynomial data are not relabelled as physical Hadamard
preparations. Omitting either the finite spatial constant or the local
Hadamard piece changes this exact result.

## 4. Conserved trace, anomaly and the actual initial constant

Let `F=[W-H_lambda]` in the raw prescription. GS (3.5) for the massless
minimal field has a cross-derivative term and a nonzero parametrix
remainder. Synge's rule and
`[(1 tensor Box)W_reg]=3*hbar*[v1]/(4*pi²)` give, in FK conventions,

    Theta=rho-3p=-Box F/2-hbar*[v1]/(4*pi²)-6*gamma*Box R,

    [v1]=R²/288+(Riem²-Ric²)/720-Box R/120.

The second term is not discarded by imposing the classical field equation
inside a Wick product. At radiation it gives
`Theta0=-hbar/(240*pi²*A⁴*eta⁸)=-4*rho0`, where
`rho0=hbar/(960*pi²*A⁴*eta⁸)` agrees with pinned A.3.

At fixed conformal time the local coefficient varies as

    delta[v1]=[-3*eta⁴*b''''+17*eta²*b''-34*eta*b'-4*b]
                /(60*A⁴*eta⁸).

This follows either by differentiating the covariant curvature expression
or the exact FLRW formula in GS. The separate geometry audit differentiates
H and Hdot in proper time instead, and compares the public response API.

Conservation is `rho'+(a'/a)*(4*rho-Theta)=0`. Linearization gives

    rho1'+4*rho1/eta = Theta1/eta-8*rho0*b'.

The forcing `-8*rho0*b'` cannot be omitted merely because the state response
is linear. Trace and conservation alone leave `C/eta⁴`, but in the unchanged
past metric/state the entire stress variation is zero, including every
local counterterm. Thus `rho1(eta_i)=0` actually fixes C. It is not a vacuum
condition inferred just from the trace.

For the Wick-square part the integrated derivative simplifies:

    integral eta³*(-Box F1/2) d eta
         = -(eta*F1'+F1)/(2*A²).

The local anomaly part integrates with the background forcing to

    rho1_local=hbar/(240*pi²*A⁴)
               *(3*b'''/eta⁵+3*b''/eta⁶-11*b'/eta⁷-b/eta⁸)
              =hbar/(240*pi²*A⁴)
               *(-3*V'/eta⁵+3*V/eta⁶+b'/eta⁷-b/eta⁸).

All integrated terms vanish in the past. Together these give the conformal
version of rho1. Then `p1=(rho1-Theta1)/3` and `E1=rho1-Theta1/2`, without
another free integration constant.

## 5. Proper-time comparison and finite prescription freedom

At fixed eta the proper-time shift is `delta t=A*eta*J`. At fixed t the
coordinate shift is therefore `delta eta=-J`, giving the scalar pullback
`rho1|t=rho1|eta-J*rho0'`. Its extra `8*rho0*J/eta` cancels the J term
in the local anomaly contribution exactly:

    b'/eta⁷-b/eta⁸ = Q'/eta⁷-2*J/eta⁹.

The analogous pressure and EED shifts cancel their J terms as well. This
proves all three fixed-proper-time formulas in the formulation. K retains
the actual history of V; cancellation of a coordinate integral does not
erase physical state memory. On the uncut target the correct potential is
`32*d/(A²*eta⁶)`; copying Q directly into b gives the wrong coefficient 48.

Varying the full FK curvature tensor before specialization gives
`I1_rho=36*(V'/eta⁵-V/eta⁶)/A⁴`. Its trace is `-6*Box R1`, and its
conservation fixes the pressure given in the formulation. Direct covariant
and conservation checks agree. With GS's source signature, `I_GS=-I_FK`;
this is why `gamma=-(c3_GS+c4_GS/3)`.

If lambda changes by a constant ratio, then `K` changes by
`-V*log(lambda2/lambda1)`. Consequently

    delta F1=-hbar*log(lambda2/lambda1)*R1/(48*pi²),
    delta T1=-hbar*log(lambda2/lambda1)*I1/(576*pi²).

The latter also follows from trace and conservation with unchanged past
data. Adding a finite gamma is independent; neither gamma nor the length
was determined by A.3. The explicit example defines a new named calibration,
not an assumption of a scheme-independent off-radiation stress.

## 6. General computable log-kernel estimates

Take a finite history duration at most T, observations `eta>=eta_->0`,
and derivative bounds B0,...,B3 on the full history. The integral of
`|log(x/T)|` over `[0,T]` is T. Differentiating the convolution on V gives
the respective bounds `T*B1`, `T*B2`, `T*B3`. For the local factor L,
`L'=1/eta`, `L''=-1/eta²`. Leibniz's rule gives exactly the three K bounds
in the formulation. Substituting them and a bound on `|Q'|` into the
absolute values of the stress expressions proves `response_bounds`.
The extra gamma terms are explicitly included. This interface estimates
the first derivative at zero; it is not an assumed bound on response
derivatives at every epsilon in a nonzero interval.

## 7. Rational bounds for the actual smooth switch

The switch r is C-infinity and flat at zero: every right derivative is an
exponential times a polynomial in `1/x`, tending to zero. Its denominator
`D(x)=r(x)+r(1-x)` is positive everywhere. For `0<x<=1/2`, put
`y=(1-x)/x>=1`. Directly,

    log(r'(x)/r'(1-x)) = -y+1/y+2*log y = g(y),
    g'(y)=-(y-1)²/y²<=0, g(1)=0.

Thus `D'<=0` on the left half, and symmetry gives the minimum at `x=1/2`:
`D>=2*e^-2>1/4`. No strictly positive second derivative is presumed.
The elementary exponential bounds used here are fully rational: the sum
through `1/4!` exceeds `8/3`; adding a geometric upper bound for the tail
from `1/5!` is below `11/4`; `(11/4)²<8`.

For `0<x<=1`, put `y=1/x`. Write `r^(n)(x)=e^-y*P_n(y)` with
`P0=1`, `P_(n+1)=y²*(P_n-P_n')`. For each monomial of degree m,

    sup_(y>=1) e^-y*y^m <= m^m/e^m < (3*m/8)^m,   m>=1.

The coefficient absolute sum produces rational bounds Rn for r derivatives;
R0 is bounded by `3/8`. Since `D*sigma=r`, `0<=sigma<=1`, `1/D<4` and
`|D^(j)|<=2*Rj`, the recurrence

    S0=1,
    Sn=4*[Rn+sum_(j=1)^n binomial(n,j)*2*Rj*S_(n-j)]

bounds `|sigma^(n)|`, including endpoint limits and the constant exterior.
The implementation checks n through five. No sampled extrema are used.

On the complete past-to-observation history `[eta_*,3*eta_*]`, the future
falling factor of chi_tilde equals one, including all its endpoint jets.
The first factor gives

    ||Q^(n)|| <= d*q_n/(A²*eta_*^(4+n)),
    q_n=4*sum_(j=0)^n binomial(n,j)*(4)_(n-j)*Sj,

where `(4)_m` is the rising factorial. From `V=-Q''-3*Q'/eta`,

    ||V^(n)|| <= d*v_n/(A²*eta_*^(6+n)),
    v_n=q_(n+2)+3*sum_(j=0)^n binomial(n,j)*j!*q_(n-j+1).

These are proved inputs, not a synthetic tuple. On the observation envelope
choose `T=2*eta_*` and the fixed physical length
`lambda=2*sqrt(2)*A*eta_*²`. The local factor is `log(eta/eta_*)+5/6`,
positive there and at most 2: a rational partial sum of `exp(7/6)` exceeds
3, proving `log 3<7/6`. The computed switch, Q, V and K bounds produce the
three rational response constants in the formulation. A second implementation
uses only `Fraction`, polynomial coefficient lists and integer combinatorics,
and must match every intermediate bound and final coefficient.

The bounds also have the right scaling: `Q^(j)` carries
`d/(A²*eta_*^(4+j))`, `V^(j)` carries `d/(A²*eta_*^(6+j))`, and K
carries `d/(A²*eta_*^6)`. Every stress term therefore has common units
`hbar*d/(pi²*A⁶*eta_*^12)`. Since `t_*=A*eta_*²/2`, these equal
`hbar*d/(64*pi²*t_*^6)`. The large constants are conservative, not optimized.

## 8. Asymptotic defect coefficients and a second-order correction

On any compact target inside the plateau, the frozen A.5 density/pressure
defects begin `24*epsilon²*d²/t⁶` and `40*epsilon²*d²/t⁶`. The actual
quantum source is multiplied by epsilon. The new derivative therefore fixes
the actual second-order coefficients

    F_rho=24*d²/t⁶-kappa*rho1,
    F_p=40*d²/t⁶-kappa*p1,
    F_E=72*d²/t⁶-kappa*E1.

For example, `sup|F_rho|<=24*d²/t_-^6+kappa*sup|rho1|`. This controls an
asymptotic coefficient, not the finite-epsilon Taylor remainder.

There is a constructive but still perturbative consequence. Multiply the
prepared scale factor by `exp(epsilon²*r(t))`. For fixed classical radiation
normalization, the extra density and pressure coefficients are respectively

    L_rho=3*r'/t+3*r/t²,
    L_p=-2*r''-3*r'/t+r/t².

Choose any reference time `t_ref` in the target and solve

    r'+r/t=-t*F_rho/3,
    r(t)=-(1/(3*t))*integral_(t_ref)^t s²*F_rho(s) ds.

This fixes the remaining second-order origin mode by `r(t_ref)=0`.
The original exact Einstein/source conservation identity implies
`F_rho'+3*(F_rho+F_p)/(2t)=0`, because both lower defect orders vanish
on the target. The same identity holds for `L_rho,L_p`. Density cancellation
therefore implies pressure cancellation; `H0=1/(2t)` is bounded away from
zero on this compact target.

The functions K and hence F_rho are smooth, so r extends smoothly from a
neighborhood of the target; multiply the extension by a temporal cutoff
equal to one there and zero in the common past. Positivity is preserved for
sufficiently small epsilon. Transport the same past state on this corrected
metric. Its first metric and state variations are unchanged, because the
new geometry differs only at second order. The same smooth-state theorem
therefore makes the actual corrected defect `O(epsilon³)` on the target.
This is a qualitative compact-slab result. No numerical third derivative,
finite-epsilon error constant, stability/shadowing or exact SEE solution
has been supplied. The extension/preparation region need not solve SEE.

## 9. Limits of this certificate

The normalization, subtraction algebra, anomaly/clock/curvature identities,
elementary exponential bounds and every rational recurrence are replayed.
The distributional limit and Hadamard/state regularity are written arguments
with explicit primary inputs, not machine-checked QFT theorems. In particular,
positivity is a property of the full prepared state, not of the truncated
Born expression considered as an independent covariance.

These results do not turn the derivative bound into A.5's uniform response
interface over an epsilon interval. They do not bound the renormalized mode
remainder, calibrate a perturbed QSEI, or imply that the corrected metric
solves SEE exactly. Arbitrary Hadamard states/preparations or other finite
coefficients are not covered by the named numerical calibration. None of
the results is a new singularity theorem or a global focusing application.

# Finite-amplitude remainder proof

All conformal derivatives in this proof are with respect to the actual
metric clock. The background label y is used only in Section 6. The state
and renormalization hypotheses are fixed in the formulation; the past
Cauchy slice is strictly before preparation, where all potential jets vanish.

## 1. Exact normalized mode equations

Let `w_k=sqrt(2k)*v_k`, `w0=e^(-ik*(eta-eta_i))`. The actual mode solves

    w=w0-integral_(eta_i)^eta sin(k*(eta-s))/k * U(s)*w(s) ds.

For a smooth real potential with flat-zero past, these are precisely the
normalized modes of the transported positive Hadamard state. The integral
is understood continuously at k=0 for the estimates; no infrared mass is
introduced. Define `F=|w|²`. Direct differentiation of the two KG factors
gives the exact third-order covariance equation

    L_U F=0, L_U=partial³+4*(k²+U)*partial+2*U',
    F(eta_i)=1, F'(eta_i)=F''(eta_i)=0.

The exact first Born term `F1=-(1/k)*integral U(s)*sin(2k*(eta-s)) ds`
solves `L_0 F1=-2U'` with zero initial data. It is linear in the **full
finite potential U**, not necessarily epsilon times A.6's first potential.
Set `D=F-1-F1`.

## 2. Uniform infrared control, 0<k<=K

Let the elapsed time be at most T and `|U|<=B0`. Iterating the Volterra
kernel using `|sin(kx)/k|<=x` bounds its nth term by
`B0^n*T^(2n)/(2n)!`. Hence `|w|<=cosh(sqrt(B0)*T)<=M`, where
`M=exp(B0*T²/2)`. The latter comparison is coefficientwise because
`(2n)!>=2^n*n!`.

Write `dw=w-w0` and `Rw=w-w0-w1`, where w1 is the first retarded iterate.
The following uniform bounds are direct consequences of the same series
and its differentiated integral equation:

    A0=B0*T²*M/2, A1=B0*T*M, A2=K²*A0+B0*M,
    |dw^(j)|<=Aj, j=0,1,2,

    E0=B0²*T⁴*M/24, E1=B0²*T³*M/6, E2=K²*E0+B0*A0,
    |Rw^(j)|<=Ej, j=0,1,2.

For E0 compare the series from its second term using
`(2n+4)!>=24*(2n)!`; for E1 integrate
`|U(s)*dw(s)|<=B0²*(s-eta_i)²*M/2`. The second-derivative bounds follow
from `dw''=-k²*dw-U*w` and `Rw''=-k²*Rw-U*dw`.

Since `D=2 Re(conjugate(w0)*Rw)+|dw|²`, its derivative bounds are

    d0=2E0+A0²,
    d1=2*(K*E0+E1+A0*A1),
    d2=2*(K²*E0+2K*E1+E2+A1²+A0*A2).

Thus `integral_0^K k*|D^(j)| dk <= K²*dj/2`. Every term has at least
two powers of potential size. The estimates are uniform at k=0 and do
not presume `k²+U>0`.

## 3. Uniform ultraviolet control, k>=K

For zero initial data the retarded inverse of L0 has kernel

    G0(x)=(1-cos(2kx))/(4k²), G0'=sin(2kx)/(2k), G0''=cos(2kx).

If `L_U E=-r` with zero initial data, the weighted norm
`N=max(k²|E|,k|E'|,|E''|)` satisfies

    N(eta)<=integral [|r(s)|+(4B0/k+2B1/k²)*N(s)] ds.

The endpoint terms vanish because G0 and G0' vanish at zero. Gronwall's
inequality therefore gives, when `|r|<=S/k⁴`,

    |E^(j)|<=T*S*exp[T*(4B0/k+2B1/k²)]/k^(6-j), j=0,1,2.

This is an exact residual estimate, not an unquantified asymptotic WKB
claim. To make its coefficient genuinely nonlinear, first observe

    L_U[1-U/(2k²)+(3U²+U'')/(8k⁴)]
       =[U^(5)+10U*U'''+20U'*U''+30U²*U']/(8k⁴).

The solitary fifth derivative would only give a linear error if left in
this expression. Instead use the exact Born term. Define

    E_lin=F1+U/(2k²)-U''/(8k⁴).

Then `L0 E_lin=-U^(5)/(8k⁴)`, with all initial jets zero. The preceding
Green estimate at U=0 gives `|E_lin^(j)|<=T*B5/(8*k^(6-j))`.

Use the approximation `Fapp=1+F1+3U²/(8k⁴)`. Its exact residual is

    L_U Fapp=[10U*U'''+20U'*U''+30U²*U']/(8k⁴)
                +4U*E_lin'+2U'*E_lin.

For k>=K it is bounded by S/k⁴, with

    S=(10B0*B3+20B1*B2+30B0²*B1)/8
                       +T*B0*B5/(2K)+T*B1*B5/(4K²).

Set `C=T*S*exp[T*(4B0/K+2B1/K²)]`. The difference F-Fapp has derivative
bounds `C/k^(6-j)`. Since `D=3U²/(8k⁴)+(F-Fapp)`, put

    P0=3B0²/8, P1=3B0*B1/4, P2=3*(B1²+B0*B2)/4.

The integrated UV bounds are exactly

    integral_K^infinity k*|D^(j)| dk
         <= Pj/(2K²)+C/((4-j)*K^(4-j)), j=0,1,2.

They are quadratic/cubic in potential size before their explicit
exponential. Absolute integrability, including the second derivative, is
now proved. The source needs U through order five; there is no hidden
large-frequency assumption on the low-frequency portion.

## 4. Renormalized Wick square and exact stress error

The radial Fourier normalization is `hbar/(4*pi²*a²)*integral k*F dk`.
At equal actual conformal time and comoving spatial separation r, the exact
finite-metric raw spatial parametrix has the coincidence expansion

    a²*H_lambda = hbar*[1/(4*pi²*r²)-U/(48*pi²)
                         +U/(16*pi²)*log(r²*a²/(2*lambda²))+o(1)].

Here U=-a''/a is the full potential. These are the exact finite-metric
coincidence coefficients, not their first parameter derivatives; higher
Hadamard terms vanish in this coincidence limit. This is the same spatial
subtraction calculation used in A.6, before any parameter linearization.
The exact Born term has the spatial finite part calculated in A.6; that
calculation is linear in an arbitrary flat-past U and uses the exact a in
the local Hadamard subtraction. The constant is still 5/6. The difference D
has the absolute, uniform derivative bounds just proved, so dominated
convergence removes spatial splitting and interchanges derivatives through
order two. This proves the exact Wick-square decomposition in the
formulation. This passage does not rely on assigning a numerical constant
to a qualitative smoothness statement.

The actual conserved trace obeys
`Theta=-Box <phi²>/2-hbar*v1/(4*pi²)-6gamma*Box R` in the stated scheme.
The approximate functional retains the same **exact** anomaly, scale and
finite terms. Consequently its trace error is precisely

    Theta_err=-Box[hbar*Rmode/(4*pi²*a²)]/2.

The actual and approximate past densities coincide. Conservation uniquely
fixes their difference: no homogeneous `C/a⁴` remains unspecified. To see
the explicit result, integrate `a⁴*rho_err'=...` in its conserved form
`(a⁴*rho_err)'=a³*a'*Theta_err`. Two integrations by parts use

    a'*a''-a*a'''=a²*U'.

All endpoint terms in the past vanish, since Rmode and its jets are zero.
Substituting the Wick remainder gives

    rho_err=hbar/(8*pi²*a⁴)*[-Hc*Rmode'+(Hc²-U)*Rmode+J_R].

The trace and EED definitions give p_err and E_err as displayed in the
formulation. Their conservation is independently checked from the full
covariant geometry. In particular, setting `J_R=0` for general varying U
fails this test. Since `|J_R|<=T*B1*M0`, the general stress bounds follow
from the integrated mode derivative bounds M0,M1,M2.

The difference has no lambda/gamma term because the same exact local
prescription appears in both quantities. Changing the approximation's
scheme alone would leave an additional local curvature term and invalidate
this error certificate. Neither absolute stress is scheme-independent.

## 5. Explicit finite metric and correct clock

The family is the original A.5 proper-time family with A.6's cutoff.
For the label `t=A*eta_*²*y²/2`, its exact radicand is `f=1-delta*p`.
The relations `d_eta=f^(1/4)*d_y/eta_*` and `a=A*eta_* y f^(1/4)` yield
the exact U formula in the formulation, including its delta-squared term.
Replacing this operator by an unperturbed coordinate derivative changes U;
a negative control explicitly detects that change.

For `0<=delta<=1/2`, `0<=p<=1` gives `1/2<=f<=1`. Hence the elapsed
actual conformal time from y=1 to observations is at most
`2*2^(1/4)*eta_*<3*eta_*`.

This duration counts the **active** history starting at y=1, not the
earlier Cauchy slice y=1/2: U, D, Rmode and all required initial jets are
zero between these times. Every retarded integral used in the estimates
can therefore start at y=1 with zero remainder data.

On the observation envelope,

    a⁴=A⁴*eta_*⁴*y⁴*f >=8*A⁴*eta_*⁴,
    |Hc| <= [1+delta*||p'||/2]/eta_*.

The latter bound follows directly from
`eta_*Hc=f^(1/4)/y-delta*p'*f^(-3/4)/4` using `f^(-3/4)<=2`.
No conformal clock is inverted approximately. For explicit integration of
the Born functional one may change its history variable to y: its time
differences are the exact integrals of `eta_*f^(-1/4)`, not background
coordinate differences. The retarded data and local lambda term are retained.

## 6. Actual C-infinity potential-jet majorants

A.6 proves the smooth-switch derivative recurrence using
`r^(n)(x)=e^(-1/x)*P_n(1/x)`,
`P_(n+1)=z²*(P_n-P_n')`, and
`r(x)+r(1-x)>=2e^-2>1/4`. Its polynomial coefficient estimate and quotient
Leibniz recurrence apply to every finite order. This new subtree extends
their calculation through order seven without editing A.6.

On the full history `1<=y<=3`, the future falling switch equals one,
including its endpoint jets. If Sj bounds the rising switch's jth
derivative, then the derivative bound for `p=chi_tilde/y⁴` is

    Pj=sum_(r=0)^j binomial(j,r)*(4)_(j-r)*Sr.

The exact finite U and repeated actual-clock derivatives are represented
by a rational ring of terms

    c*delta^n*f^r*y^(-m)*product p^(j).

Differentiation changes p jets, inverse-y powers, and contributes
`-r*delta*p'*f^(r-1)` from each f power, followed by multiplication by
`f^(1/4)`. The ring retains signs and combines identical terms before
enclosure. Its term counts through U^(5) are 3,6,11,18,29,43.

For every term, use `delta^n<=delta*(1/2)^(n-1)`, `y^(-m)<=1`,
`f^r<=1` for r>=0 and `f^r<=2^ceil(-r)` for r<0, and the proved Pj
bounds. This produces the exact rational b0,...,b5 with
`|U^(j)|<=delta*bj/eta_*^(j+2)`. Only p jets through seven occur.

An independent Fraction-only implementation evaluates these exact ring
jets against a separate truncated Taylor-series calculation of fractional
powers and the true clock operator at rational data. It also replays all
majorant arithmetic, potential bounds, mode integrals, stress constants and
the finite-amplitude accuracy check. The Taylor test is an algebraic audit,
not an alternative claimed physical cutoff/state.

## 7. Rational domain and finite-amplitude constants

Choose `K=1/eta_*`, `T=3*eta_*`. The four domain caps are

    delta<=1/2,
    delta<=1/(9*b0),
    delta<=1/(24*b0+12*b1),
    delta<=2/P1.

The first two exponential arguments are then at most 1/2 and the Hc bound
is at most `2/eta_*`. The elementary series gives `exp(1/2)<2`, so no
numerical transcendental enclosure is presumed. Their exact minimum is
`delta_bar=2048/190897521`.

With both exponentials replaced by the proved cap 2, every mode bound is
a polynomial with nonnegative coefficients and amplitude degree at least
two. Dividing by delta² leaves a nondecreasing polynomial. Evaluation at
delta_bar therefore bounds all `0<=delta<=delta_bar`, including zero by
continuity, not merely the endpoint. Write its exact rational coefficients
as m0,m1,m2, so `|Rmode^(j)|<=delta²*mj/eta_*^(j+2)`.

The component error coefficients in common units
`hbar*delta²/(pi²*A⁴*eta_*⁸)` are

    C_rho=[2m1+(4+delta_bar*b0+3delta_bar*b1)*m0]/64,
    C_p=[m2+6m1+(12+delta_bar*b0+3delta_bar*b1)*m0]/192,
    C_E=[m2+8m1+(16+6delta_bar*b1)*m0]/128.

Their exact fractions are in the certificate; rational comparisons prove
the displayed rounded upper bounds in the formulation. For the Wick-square
remainder itself, `a^-2<=1/(2A²eta_*²)` and
`|Hc'|<=B0+Hc²` give coefficients

    m0/8,
    (m1+4m0)/8,
    [m2+8m1+(24+2delta_bar*b0)*m0]/8

for its zeroth, first and second conformal derivatives, in units
`hbar*delta²/(pi²*A²*eta_*^(4+j))`. Thus the required C2 control is
explicit and finite.

At delta=10^-12 the report checks both domain membership and the three
one-percent comparisons exactly as rational inequalities. The positive
reference scales follow from A.3 at the same proper-time label y:

    rho_ref=hbar/(960*pi²*A⁴*eta_*⁸*y⁸),
    p_ref=hbar/(576*pi²*A⁴*eta_*⁸*y⁸),
    E_ref=hbar/(320*pi²*A⁴*eta_*⁸*y⁸).

Taking y<=3 produces the stated ratios. Actual/Born stress is not used as
a denominator, so a possible zero of either causes no hidden division.
Since `t_*=A*eta_*²/2`, `delta=4*epsilon*d/t_*²` exactly. At epsilon=1,
`t_*>=2*10^6*sqrt(d)` implies `delta<=10^-12`, so the same one-percent
bound holds. This dimensional statement requires no SI or cosmological
calibration and adds no SEE assertion.

## 8. Scope of the result

This is a finite-amplitude actual Hadamard-state RSET approximation with a
computed nonlinear error, not a formal Born covariance declared to be a
state. The elementary bounds are deliberately coarse. Optimizing the split
or derivative estimates could improve them but is not required for validity.

The Born functional still contains exact metric, local and history inputs;
replacing it by A.6's epsilon-linear formula requires separate quantitative
clock/geometry estimates. A.6's second-order corrected metric is a different
family whose finite jets have not been certified here. No finite-amplitude
SEE shadowing, stability, perturbed QSEI, all-geodesic coverage or cosmological
singularity theorem follows from the present fixed-background certificate.

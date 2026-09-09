# P8(a) A.6 — Actual retarded first stress response

Adopted 2026-09-05. This nested checkpoint pins and replays A.5 certificate
SHA256 `a7e1766a16778920c5784b9c52f997497a6e22259c48d956c8ca50ca60770930`.
No earlier source, formulation, test or certificate is changed.

## Physical, state and prescription hypotheses

Use the real massless minimally coupled scalar on the smoothly prepared A.5
metric, with fixed `A,d>0`, `d=kappa*hbar/(46080*pi²)`. At fixed proper time,

    a_epsilon(t)=sqrt(2*A*t)*(1-4*epsilon*d*chi(t)/t²)^(1/4),
    q(t)=partial_epsilon log(a_epsilon)|0=-d*chi(t)/t².

The real C-infinity cutoff has compact support strictly inside `t>0` and
`0<=chi<=1`. Restrict epsilon to a neighborhood of zero in which the scale
factor is positive. Transport the full radiation-reference Cauchy data from
a common past slice strictly before the cutoff starts. This fixes an actual
homogeneous, isotropic, zero-mean quasifree Hadamard state, not arbitrary
instantaneous vacuum data. All statements below concern its derivative at
`epsilon=0`. No uniform finite-epsilon response bound is inferred.

The conventions are FK `+---`, `R_FK=+6*(Hdot+2H²)`. For the primary
Gottschalk--Siemssen (GS) source, `g_FK=-g_GS`, `R_ab,FK=-R_ab,GS`, and
`R_FK=R_GS`. GS defines `Box=-g_GS^ab*nabla_a*nabla_b`, so its Box equals
FK Box. Physical lower orthonormal density and pressure do not change sign;
the trace does. This is not P8(b)'s curvature convention.

Define a named family of prescriptions `GS-H_lambda,gamma`: use the raw
Hadamard parametrix in GS Section 2.5, with constant physical length
`lambda>0`, and its conserved stress formula (3.4). The Wick square has no
additional `alpha*R`. Then add the physical FK tensor `gamma*I_R²` to the
stress, with arbitrary fixed real gamma. In this conformally flat problem
`J=I/3`; in the GS tensor notation `gamma=-(c3_GS+c4_GS/3)`. A.3 did not fix
gamma or lambda: their effects vanished on exact radiation. This checkpoint
does not retroactively assign their values. Independent cosmological and
Einstein couplings remain separate from the massless matter prescription.
Use a full smooth Hadamard parametrix, or a truncation sufficiently high for
each required coincidence derivative; a fixed finite truncation is not
asserted to leave a C-infinity remainder for every derivative order.

## Actual retarded formulas

Let `eta=sqrt(2*t/A)` denote the **background** conformal coordinate used to
label a fixed proper-time observation, and let primes below mean `d/deta`.
With the common-past conformal clock on each metric,

    Q(eta)=q(A*eta²/2), J(eta)=integral_(eta_i)^eta Q(s) ds,
    b(eta)=Q(eta)+J(eta)/eta,
    a_epsilon(eta)=A*eta*(1+epsilon*b(eta)+O(epsilon²)),
    V(eta)=-b''-2*b'/eta=-Q''-3*Q'/eta.

Here `eta_i` may be the cutoff start because all potential jets vanish there;
the actual Cauchy slice is strictly earlier. For any auxiliary constant
`T>0`, define the convergent retarded log kernel

    K(eta)=integral_(eta_i)^eta V'(s)*log((eta-s)/T) ds
           + V(eta)*(log(sqrt(2)*A*eta*T/lambda)+5/6).

It is independent of T. The history before observation is retained. The
actual Wick-square derivative is

    F1=partial_epsilon <phi²>_ren|0=-hbar*K/(8*pi²*A²*eta²).

Write `rho1,p1,E1` for the physical stress/EED derivatives at **fixed proper
time**. In the named prescription they are exactly

    rho1 = hbar/(16*pi²*A⁴)*(K'/eta⁵-K/eta⁶)
           + hbar/(240*pi²*A⁴)*(-3*V'/eta⁵+3*V/eta⁶+Q'/eta⁷)
           + gamma*I1_rho,

    p1 = hbar/(48*pi²*A⁴)*(-K''/eta⁴+3*K'/eta⁵-3*K/eta⁶)
         + hbar/(720*pi²*A⁴)*(3*V''/eta⁴-9*V'/eta⁵+10*V/eta⁶+5*Q'/eta⁷)
         + gamma*I1_p,

    E1 = hbar/(32*pi²*A⁴)*(-K''/eta⁴+4*K'/eta⁵-4*K/eta⁶)
         + hbar/(480*pi²*A⁴)*(3*V''/eta⁴-12*V'/eta⁵+13*V/eta⁶+6*Q'/eta⁷)
         + gamma*I1_E,

where

    I1_rho=36/A⁴*(V'/eta⁵-V/eta⁶),
    I1_p=-12/A⁴*(V''/eta⁴-3*V'/eta⁵+3*V/eta⁶),
    I1_E=-18/A⁴*(V''/eta⁴-4*V'/eta⁵+4*V/eta⁶).

At fixed conformal time replace `Q'` in these formulas by `b'-b/eta`.
Dropping this distinction loses the preparation-dependent clock shift.
The trace and conservation equations leave a homogeneous `C/eta⁴`; the
unchanged past state/metric fixes the derivative of this constant to zero.

Changing only the subtraction length from lambda1 to lambda2 changes the
first stress by `-hbar*log(lambda2/lambda1)*I1/(576*pi²)`. Finite gamma is an
additional independent choice. No scheme-independent numerical response is
claimed off radiation.

## Computable bounds and one fully specified smooth preparation

If `B_j>=||V^(j)||_infinity`, `j=0,...,3`, on the complete preparation-to-
observation history, `eta>=eta_->0`, `T` is at least the history duration,
and `C>=|log(sqrt(2)*A*eta*T/lambda)+5/6|` on observations, then

    |K| <= T*B1+C*B0 =: L0,
    |K'| <= T*B2+C*B1+B0/eta_- =: L1,
    |K''| <= T*B3+C*B2+2*B1/eta_-+B0/eta_-² =: L2.

Triangle inequalities in the displayed stress formulas now give explicit
response bounds, including a supplied `|gamma|` bound. Generic input tuples
are conditional interfaces; the following example **derives** its inputs.

Put `r(x)=exp(-1/x)` for `x>0`, zero otherwise, and
`sigma(x)=r(x)/(r(x)+r(1-x))`. For `eta_*>0` set

    chi_tilde(eta)=sigma((eta-eta_*)/eta_*)*sigma((4*eta_*-eta)/eta_*),
    chi(t)=chi_tilde(sqrt(2*t/A)).

This specifies the A.5 **proper-time cutoff by pullback**, not a replacement
of its coordinate clock. The observation envelope is `[2*eta_*,3*eta_*]`;
any compact target inside its interior satisfies A.5's open-neighborhood
plateau condition. Bounds extend to the envelope endpoints by smoothness.
The Cauchy slice is, for example, `eta_*/2`; the kernel can start at `eta_*`.

For the named calibration `lambda=2*sqrt(2)*A*eta_*²` and `gamma=0`, the
code proves exact rational derivative bounds for this C-infinity switch
through order five. With `T=2*eta_*`, `eta_-=2*eta_*`, `C=2`, it proves

    sup |rho1| <= 1365615131563/125829120 * hbar*d/(pi²*A⁶*eta_*¹²),
    sup |p1|   <= 1031121912446883/1342177280 * hbar*d/(pi²*A⁶*eta_*¹²),
    sup |E1|   <= 9323796896231963/8053063680 * hbar*d/(pi²*A⁶*eta_*¹²).

These are conservative genuine derivative bounds, not optimal constants,
sample-based estimates, or bounds for unspecified preparations. Changing
lambda/gamma requires the explicit scheme terms and corresponding bound.

## Consequence and boundary

On the target, the actual A.5 Einstein-defect epsilon-squared coefficients
are `F_rho=24*d²/t⁶-kappa*rho1`, `F_p=40*d²/t⁶-kappa*p1`, and
`F_E=72*d²/t⁶-kappa*E1`. Thus the new constants bound those asymptotic
coefficients. They are not a finite-epsilon residual certificate.

A smooth second-order scale correction `a_epsilon*exp(epsilon²*r(t))`,
prepared to vanish in the same past, cancels these coefficients on a compact
target if `r'+r/t=-t*F_rho/3`. Conservation supplies the pressure cancellation.
The A.5 smooth-state theorem then gives a **qualitative** actual residual
`O(epsilon³)` there. This construction supplies neither its numerical
remainder nor an exact SEE solution; its proof and scope are in the notes.

Still open: finite-amplitude RSET/mode remainder bounds, an exact/stable SEE
solution, quantitative perturbed-metric QSEI/Fourier estimates, all-normal-
geodesic coverage and a cosmological focusing application. Full P8(a) is not
complete. The replay certifies elementary algebra and enclosures conditional
on the stated primary Hadamard/state theorems, not those theorems themselves.

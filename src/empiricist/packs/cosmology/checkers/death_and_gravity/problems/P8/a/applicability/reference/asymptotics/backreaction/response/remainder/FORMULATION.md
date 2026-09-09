# P8(a) A.7 — Actual finite-amplitude renormalized remainder

Adopted 2026-09-05. The immutable dependency is A.6, certificate SHA256
`1101c2c2977716ef3bcf452ab02f69abb91ba43c7720df0920384099a1c1e868`.

## What is bounded

For the actual past-prepared massless minimally coupled scalar state,
this checkpoint gives an all-frequency nonlinear mode remainder through
two conformal-time derivatives. It implies a quantitative **finite-amplitude**
error for the full renormalized density, pressure and EED compared with an
explicit retarded Born functional evaluated on the **exact** prepared metric.
This is not merely a bound on a derivative at amplitude zero.

The Born functional is an approximation to expectation values. It is not
claimed to define a positive quantum state or solve SEE. The actual state
is the positive quasifree Hadamard state transported from the unchanged
radiation past, with the full Cauchy data fixed as in A.5/A.6.

## Field, metric, clock and prescription

Keep the A-track FK conventions `+---`, `R=+6*(Hdot+2H²)`. Physical density
and pressure agree with the GS source, its positive-time Box equals FK Box,
and its trace and curvature-variation tensor have the opposite contraction
dictionary stated in A.6. Do not import P8(b)'s R sign.

Use A.6's specified C-infinity cutoff, unchanged. In the background
proper-time label `y=sqrt(2*t/A)/eta_*`, put

    delta=16*epsilon*d/(A²*eta_*⁴), d=kappa*hbar/(46080*pi²),
    chi_tilde(y)=sigma(y-1)*sigma(4-y), p(y)=chi_tilde(y)/y⁴,
    f(y)=1-delta*p(y), a=A*eta_* y*f(y)^(1/4),

where `sigma(x)=r(x)/(r(x)+r(1-x))`, `r(x)=exp(-1/x)` for positive x and
zero otherwise. The actual proper-time cutoff is
`chi(t)=chi_tilde(sqrt(2*t/A)/eta_*)`. A past Cauchy slice can be `y=1/2`;
every potential jet is zero before preparation at y=1.

The exact conformal clock is **not** eta_* y:

    eta_actual/eta_*=1+integral_1^y f(s)^(-1/4) ds,
    d_eta=f^(1/4)/eta_* * d_y,

    U=-a''/a=delta/(4*eta_*²)*f^(-1/2)*(p''+3*p'/y)
                  +delta²/(8*eta_*²)*f^(-3/2)*(p')².

Only in this display do primes on p mean y derivatives. All mode, Wick
and stress derivatives below are in the actual conformal clock. The
observation envelope is `2<=y<=3`; compact targets in its interior retain
the A.5 near-target plateau condition.

Both actual stress and approximation use the same GS raw `H_lambda`
prescription and exact conservation correction, plus the same physical FK
`gamma*I_R²`, with any fixed `lambda>0`, real gamma. No additional Wick-square
`alpha*R` is included. Here `gamma=-(c3_GS+c4_GS/3)`. Independent cosmological
and Einstein couplings remain separate. The identical local terms cancel
from the error, not from either stress itself.

## Exact finite-potential decomposition

For `v_k''+(k²+U)v_k=0` with radiation-vacuum past data, define

    F_k=2*k*|v_k|²,
    F1_k[U]=-(1/k)*integral_(eta_i)^eta U(s)*sin(2*k*(eta-s)) ds,
    D_k=F_k-1-F1_k[U],
    Rmode(eta)=integral_0^infinity k*D_k(eta) dk.

The actual Wick square has the exact identity

    <phi²>_ren = -hbar/(8*pi²*a²)*K_{a,lambda}[U]
                  +hbar/(4*pi²*a²)*Rmode,

    K_{a,lambda}[U]=integral_(eta_i)^eta U'(s)*log((eta-s)/T) ds
                     +U(eta)*(log(sqrt(2)*a(eta)*T/lambda)+5/6).

T is any positive auxiliary scale; it cancels. The geometric a, potential U
and all time differences are exact, not linearized. The nonlinear integral
and its first two derivatives converge absolutely and uniformly on the
observation interval by the bounds proved below.

Define `W_B=-hbar*K/(8*pi²*a²)`. Its approximate trace retains the exact
geometry, anomaly and finite term:

    Theta_B=-Box W_B/2-hbar*v1/(4*pi²)-6*gamma*Box R,
    v1=R²/288+(Riem²-Ric²)/720-Box R/120.

Fix `rho_B(eta_i)=rho_ref(eta_i)` from A.3 and reconstruct

    rho_B=a^(-4)*[a_i⁴*rho_ref(eta_i)+integral_(eta_i)^eta a³*a'*Theta_B ds],
    p_B=(rho_B-Theta_B)/3, E_B=rho_B-Theta_B/2.

The initial density is actual specified state data, not an arbitrary
homogeneous radiation constant selected by trace alone.

Write `Hc=a'/a` and `J_R=integral_(eta_i)^eta U'(s)*Rmode(s) ds`. The exact
actual-minus-Born stress error is

    rho_err=hbar/(8*pi²*a⁴)*[-Hc*Rmode'+(Hc²-U)*Rmode+J_R],
    p_err=hbar/(24*pi²*a⁴)*[Rmode''-3*Hc*Rmode'+(3*Hc²+U)*Rmode+J_R],
    E_err=hbar/(16*pi²*a⁴)*[Rmode''-4*Hc*Rmode'+4*Hc²*Rmode+2*J_R].

These are exact identities, not asymptotic coefficients. The J_R history
term cannot be discarded on a varying potential.

## General all-frequency theorem

Let the history duration be at most T and `|U^(j)|<=B_j`, j=0,...,5, on
that history, with smooth flat-zero past data. Split at any k=K>0. The proof
gives explicit IR and UV bounds M_j such that

    integral_0^infinity k*|D_k^(j)| dk <= M_j, j=0,1,2.

They are implemented in `mode_bounds.bounds`. They are genuinely quadratic
as all potential-jet bounds scale to zero, with explicit exponential factors
`exp(B0*T²/2)` and `exp(T*(4B0/K+2B1/K²))`. No positive lower bound on
`k²+U`, ultraviolet cutoff, infrared mass, or assumed mode remainder is used.

The generic theorem assumes its supplied jet/geometry bounds are true.
The following calibration derives them for the stated actual C-infinity
preparation, rather than inserting an unconstrained tuple.

## Certified finite-family calibration

A rational fractional-power jet calculation gives
`|U^(j)|<=delta*b_j/eta_*^(j+2)` through j=5. Its p jets through order seven
are bounded using a new extension of the proved A.6 smooth-switch recurrence.
For example `b0=20461/128`, `b1=61013499/8192`. The full exact values are
in the read-only certificate.

With `K=1/eta_*`, history bound `T=3*eta_*`, the explicit domain is

    0<=delta<=delta_bar=2048/190897521.

The history bound counts active evolution from y=1, where the potential
and remainder data are flat-zero; the earlier Cauchy slice y=1/2 need
not be moved. The exact-kernel API in `p8a_remainder.kernel` takes the
full actual scale factor and actual conformal coordinate, not A.6's
radiation normalization as a substitute for a.

This is the minimum of four proved rational caps: `1/2`, `1/(9*b0)`,
`1/(24*b0+12*b1)`, and `2/||p'||`. They imply both exponential factors
are less than 2, `a^(-4)<=1/(8*A⁴*eta_*⁴)` and `|Hc|<=2/eta_*` on
the observation envelope. No floating comparison establishes the domain.

The resulting exact rational stress-error coefficients C_rho,C_p,C_E,
in units `hbar*delta²/(pi²*A⁴*eta_*⁸)`, obey the convenient rounded bounds

    C_rho < 8*10^14, C_p < 9*10^14, C_E < 17*10^14.

The exact fractions, the all-frequency Rmode derivative constants and the
Wick-square C2 bounds are pinned and independently replayed. These constants
are conservative, not optimal.

For the concrete finite amplitude `delta=10^-12`, all three exact uniform
error ratios are **strictly below 1/100** of the corresponding positive
A.3 radiation-reference component at the same proper time. The rational
checks are `960*3⁸*C_rho*delta²`, `576*3⁸*C_p*delta²`, and
`320*3⁸*C_E*delta²`, respectively. This is normalization by a positive
reference scale, not relative error against actual or Born stress, which
may vanish or have either sign. No claim that this metric solves SEE follows.

With `t_*=A*eta_*²/2`, the exact relation is `delta=4*epsilon*d/t_*²`.
Thus the example includes physical `epsilon=1` whenever
`t_*>=2*10^6*sqrt(d)`. This is a sufficient finite-amplitude regime for
the specified prepared metric/state, not a self-consistent cosmological
solution or an interpretation of the preparation scale as an initial
singularity time.

## Remaining boundaries

This controls a finite-amplitude actual RSET approximation on the specified
prepared metric. It does not assert that the Born functional is an exact
state, that A.6's epsilon-linear stress has this same error without additional
clock/geometry comparisons, or that A.6's corrected second-order metric
automatically satisfies these jet bounds. It supplies no SEE shadowing or
stability theorem, no quantitative perturbed-metric QSEI or all-geodesic
coverage, and no new singularity theorem. Full P8(a) remains open.

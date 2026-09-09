# S0 — Opening calculation and proof obligations

2026-09-04. S0 complete: 29 tests pass, Ruff passes, and the stored exact
certificate replays offline. The frozen object and row definitions are in
`../FORMULATION.md`.
This note distinguishes what the exact checks establish from the global
and covariant work still required.

## 1. Horndeski quadratic-action identity

Write T=G_T, F=F_T, n=delta lapse, b=scalar shift, z=zeta and v=zdot.
For one nonzero comoving Fourier mode, suppressing a common positive spatial
average, KYY11 (4.24) is

    L = a³[−3T v² + Sigma n² + 6Theta n v]
        + a k²[F z² + 2Theta n b − 2T v b + 2T n z].

The lapse/shift Hessian determinant is −4a²k⁴Theta². On a>0, k²>0,
Theta≠0, variation gives n=T v/Theta and solves for b. The mixed term
is removed with the explicit boundary term

    B = a k² T² z² / Theta,
    L_constrained − dB/dt = a³ G_S v² − a k² F_S z²,
    G_S = Sigma T²/Theta² + 3T,
    F_S = H T²/Theta + 2T Tdot/Theta − T² Thetadot/Theta² − F
        = (1/a) d(a T²/Theta)/dt − F.

`horndeski.py` derives this in SymPy; an independently written FLINT
polynomial expansion checks the denominator-cleared IBP identity. A wrong
boundary sign is a negative control. The certificate quantifies over the
coefficient jets of **this action**. It does not prove the covariant
Horndeski-to-action map, the global integral theorem, or regularity at Theta=0.
The identity has no 1/H, but a model can still have Theta proportional to H:
the GR/k-essence known-answer test correctly retains that specialized pole.

## 2. Conditional global no-go template (analytic, not kernel checked)

Assume on all R: a,T,F are finite smooth and strictly positive; Theta is
finite, smooth and nowhere zero; xi=a T²/Theta is C¹; the identity in §1
holds; F_S≥0; and both one-sided integrals of aF diverge. Then

    xidot = a(F_S+F) ≥ aF > 0.

For any finite t0, integrating towards either end forces xi to take a
negative value before t0 and a positive value after t0. Continuity then
forces a finite zero. But a T² is strictly positive and Theta is finite
and nonzero, a contradiction. This rules out coefficients satisfying all
these hypotheses; it is not a blanket theorem about every Horndeski bounce.

Removing the hypotheses changes the argument. A test fixture a=1,
T=F=exp(t), Theta=exp(t)/2, Sigma=0 has G_S=3exp(t), F_S=exp(t),
xi=2exp(t)>0: its past tensor integral is finite. It is only a reduced-
coefficient counterexample to omitting that hypothesis, not a reconstructed
strong-gravity bounce. A separate fixture xi=−1/t is increasing on each
side of its pole but jumps from +infinity to −infinity: patchwise positivity
does not justify integrating through gamma crossing. These tests prevent
two invalid theorem extensions; they do not settle the covariant loopholes.

## 3. Rolling luminal matter: an exact matrix obstruction

Use A25's source matrices with Q=P_Y>0, chi_dot≠0 and Theta≠0. Directly,

    det(K−G) = −chi_dot² Q² (f−g)².

If K≻0 and all speeds are ≤1 then K−G is positive semidefinite, so f=g.
This algebraic implication holds for finite nonzero matter amplitude, not
only infinitesimal matter. Using the source dictionary with MRV20 (8a)
for D (A25 (10g) is inconsistent; see the digest) gives

    A3 = 2(X A1−2F2)(A1−2F2_X) / [X(3X A1−4F2)].

The derivation requires X>0, Theta≠0, G_T≠0 and 3X A1−4F2≠0.
In the healthy subluminal tensor domain F2<0 and A1≥0, the last factor is
positive. Conditions enforced only along one trajectory give an on-shell
relation; they do **not** prove the relation on an open covariant domain.
On the restriction A1≡0 this reduces to A3=−2F2_X/X.

For f=g the characteristic polynomial factors as

    det(G−c²K) = Q(1−c²)[G_eff−c² K_eff],
    K_eff = G_S + G_T² YQ/Theta² − YQ g²,
    G_eff = F_S − YQ g².

One eigenvalue is exactly 1; the other still requires 0<G_eff≤K_eff.
Our matrix fixtures deliberately include a stable but superluminal f=g
case. This checks the source-level algebra, not the DHOST perturbation
derivation or a whole-row exclusion.

## 4. Benchmark: resolve H=0 before doing a scan

For A25 (28), a(0)=1, H(0)=0 and

    Hdot(0) = (epsilon+3)/(6 epsilon tau²) = 1/375.

With N=t² tanh(t/tau+u)+tau² tanh(t/tau), both N and H in (43)
have simple zeros at t=0. Their derivative ratio gives

    a1(0) = w(11epsilon−3)/[12(epsilon+3)cosh²u]
          = 13/[12cosh²(1/10)].

Before evaluating H=0, cancel H in (40) to obtain

    Theta = H + [2 g1 tau/(t²+tau²)]
                    [tanh(t/tau)−tanh(t/tau+u)].

Thus Theta(0)=−2w tanh(u)/[3tau cosh²u]<0 at the pinned parameters.
The bounce is not the gamma crossing. Tests check these exact local
identities and compare a1's two-sided limit at 70-digit precision.
They do not certify global a1 regularity, scalar stability, or the
existence/uniqueness of other H/Theta zeros.

The sigmoid in (28) gives positive weights summing to one; both powered
bases are ≥1. Hence a≥1 analytically, so its *prescribed metric* is causally
geodesically complete if extended with that formula on R. This is not yet
a proof that the metric solves our covariant equations. Its asymptotic
powers are 1/epsilon in the past and 1/3 in the future.

Do not add an arbitrarily small free M1 scalar and leave the benchmark
unchanged: Y=Cchi²/a⁶, and for its epsilon=5 contracting tail,
rho_chi/H² grows like |t|^(2−6/5). Thus small matter near the bounce is
not uniformly small on the whole past tail. The paper's interacting
matter sector and our M1 problem must be handled separately.

## 5. Next bounded task

Derive the covariant background and unreduced constraint system in P8's
conventions, beginning with the selected quadratic-Ia benchmark. Require
agreement with the tensor and M0 scalar coefficients before using its
plots or searching nearby parameters. Then construct a regular chart at
gamma crossing and validated core-plus-tail inequalities. Until those
gates close, S1/S2 and every M0/M1 row remain open.

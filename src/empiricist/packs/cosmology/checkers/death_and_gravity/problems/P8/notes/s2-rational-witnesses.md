# S2/S3 — Three all-time covariant witnesses

These are existence points for the frozen function-group ladder, not a
claim that the surrounding parameter space is viable. They are defined
exactly by `rational_candidates.specification()` and `reconstruct()`;
the resulting full F polynomials are recorded in `witness-*.json`.

## 1. Frozen choices and reconstruction

Use phi=t, X=1 on the background, d=1+phi², M=1. Each model has
a=d^(p/2), H=p*t/d, K=A1=0. The independent remaining functions are:

| Witness | p | F2(phi,X) | A3(phi,X) | Extra matter |
|---|---:|---|---|---|
| C | 1/2 | −T/2+3T(1−X)/(4d²), T=1−1/(2d) | 0 | none |
| D | 2 | −1/2 | 4/d³ | none |
| CD_matter | 4 | −1/2+(1−X)/(2d³) | 1/(d³X) | chi_dot=1/(10d⁶) |

A2,A4,A5 are the frozen covariant Ia completion, not extra independent
groups. The common clock tube is 9/10<=X<=11/10 for every real phi; it
lies within an open smooth domain. All three have A1=0 identically, not
just on the trajectory. For C, F2X is nonzero; for D, A3 is nonzero; for
CD both are nonzero. Thus their smallest supporting rows are exactly C,
D, and CD, respectively. No disformal change of matter frame is used.

For each choice the derived metric equations solve F0=F(phi,1) and
FN=∂_N F(phi,N^−2)|N=1. The coefficient FNN is solved from the target

    S = Theta²*(FS−3T)/T²,
    FS = (a*T*Lambda/Theta)'/a−FT.

Extend these jets covariantly, not merely on the trajectory:

    FX=−FN/2,        FXX=(FNN+3FN)/4,
    F(phi,X)=F0+FX*(X−1)+FXX*(X−1)²/2.

The exact derived metric equations, the matter equation, and every entry
of K−G are substituted back and vanish identically. The scalar clock
equation follows by the Bianchi argument in S1. All denominators of these
time coefficients are certified nonzero. This reconstruction prescription
is an explicit rational covariant function, not an ODE or an existence
assumption about an unspecified F.

The choices were found by exploratory exact inverse construction. A few
slow-decay choices were rejected **after canonical normalization**; AC and
BC remain labelled diagnostics in code. The three points above were frozen
before final certificate promotion. This is not a blind preregistered
parameter search; no scan, failed or successful, supplies an exclusion.

## 2. Coefficients, signs and crossing coverage

For all three FT=GT=T. The exact Theta,Lambda pairs are

    C:  Theta=t*(4t^6+14t^4+10t²+15)/(8d^4),
        Lambda=T*(1−3/(2d²));
    D:  Theta=2t/d, Lambda=1−2/d³;
    CD: Theta=t*(4d³−1)/d^4, Lambda=1−3/(2d³).

Each Theta/t is strictly positive, so t=0 is its only zero, a simple
ascending gamma crossing. Each Lambda is strictly negative on |t|<=1/4;
its two zeros occur outside that chart and are harmless in the unitary
chart, since Theta!=0 there. T>1/4 on the whole line (in fact T>=1/2).

`candidate_cert.py` provides exact rational Sturm certificates in x=t²:
unitary K11>0 and det K>0 for t!=0; regular-chart K_b11>0 and det K_b>0
on |t|<=1/4; J>0 globally; and the tensor and Theta/Lambda signs just
stated. K=G and K_b=G_b are exact identities. Hence all scalar and tensor
principal speeds are **exactly luminal**, including through the crossing.
Saturation at speed one is permitted by the frozen contract.

The coverage is the compact core [−2,2] plus the two infinite tails.
Use the unitary chart for |t|>=1/8 and the regular gamma chart for
|t|<=1/4; their overlap is nonempty on both sides. The global Sturm proofs
cover both tails and core simultaneously; this is not a finite grid with
unproved extrapolation. Independent FLINT rational-polynomial arithmetic
counts roots; positive endpoint/sample values select the strict sign.

In M1, a³ chi_dot=1/10 exactly, so matter rolls at every finite time and
its backreaction is included. K22=G22=1/2. Its positive determinant
certificate is essential: the exceptional relation alone would not prove
that the coupled system is healthy. Here that determinant has an explicit
positive-coefficient numerator, in addition to the general Sturm replay.

## 3. Domain and canonical tails

`candidate_cert.py` compactifies time with u=1/(1+t²), and uses
X=9/10+r/5, so (u,r) lies in the closed unit square. Exact rational
tensor-product Bernstein bounds prove −F2>0 on that whole tube. Since
A1=0, this also controls every Ia denominator. CD's explicit 1/X is
regular there. Rational time denominators are checked separately.

Every candidate has the smooth finite-time field redefinition

    varphi=sqrt(2p)*asinh(phi),
    U=dphi/dvarphi=sqrt(d/(2p)),  V=d²phi/dvarphi²=phi/(2p).

Its derivative is nonzero at every finite time. Under X_old=U² X_new,
the F polynomial has coefficients

    potential contribution: F0−FX+FXX/2 -> 0,
    X_new: d*(FX−FXX)/(2p) -> 1/2,
    X_new²: d²*FXX/(8p²) -> 0.

The covariant curvature coefficient approaches −1/2 and its normalized
X_new R correction d*F2X/(2p) tends to zero. The certificates provide
explicit rational C and integer n>=1 with |remainder|<=C/d^n, uniformly
over the clock tube, for these and for d²A3,d²A4,d³A5, H² and Hdot.
They also bound the first two canonical-phi and X derivatives: the first
canonical derivative is bounded through its square, and the second is
[d∂_phi²+phi∂_phi]/(2p). The constants and orders are in the JSON, not
inferred from asymptotic plots or leading-order cancellations alone.

Why the weighted Ai bounds suffice: writing u_mu=varphi_,mu and
h_mu_nu=varphi_;mu_nu, phi_;mu_nu=U h_mu_nu+V u_mu u_nu. Every term
induced from L3,L4 carries at most four factors U,V, and every term from
L5 at most six. Here p>=1/2 implies |U|,|V|<=sqrt(d). Thus the displayed
weighted bounds control all induced coefficients, including terms with
fewer second derivatives; L1,L2 and K vanish identically. Derivatives at
fixed X_new add the chain-rule term (2phi U/d) X_old ∂_X_old, whose
coefficient and first derivative are bounded on the tube. The stored
derivative bounds therefore control those transformed remainders too.

These are conventional **asymptotic action-coefficient and linear-background
tails in a covariant tube about the solution**. They do not assert an
analytic Lorentz-invariant vacuum at X=0 or a uniform scattering expansion
there: CD has an explicit 1/X. Such a UV requirement was not frozen and
cannot be inferred from this certificate. No quantitative strong-coupling
scale, nonlinear/BKL stability or observational viability is claimed.

## 4. Geometry and the separate tensor integral

a=d^(p/2)>=1 for all real t, H(0)=0, Hdot(0)=p>0, and every finite-time
curvature invariant of the smooth FLRW metric is finite. Both tails have
a~|t|^p with p>0 and H->0. The time axis is all R.

For null geodesics the affine length is proportional to ∫a dt, which
diverges in each direction. For a timelike geodesic with conserved spatial
momentum P, d(proper time)/dt=1/sqrt(1+P²/a²)>=1/sqrt(1+P²), so both
proper-time lengths diverge as well. Separately, FT>1/4 gives
∫a FT dt>=∫dt/4=∞ in both tails. No tensor-frame completeness hypothesis
has been silently replaced by physical metric completeness.

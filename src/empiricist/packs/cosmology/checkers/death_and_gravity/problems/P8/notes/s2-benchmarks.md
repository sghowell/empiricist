# S2 — Known-answer regressions and source corrections

The regression suite is separate from the new ladder witnesses. A known
mechanism reproduced here is not claimed as a novel discovery.

## 1. The A25 coefficient dictionary and corrected reconstruction

The pinned source is [A25 v2](https://arxiv.org/html/2501.09985v2), with
tau=10, epsilon=5, w=2, u=1/10. S0 recorded the inconsistent printed D;
S1 independently obtains the MRV20 value D=2 phi_dot(2F2X−A1).

There is a second, independent discrepancy. For arbitrary smooth g=g1(t)
and a1(t), the metric expansion reproduces GT=FT=1, Lambda=1−3g,
Theta=H(1+4a1+g)+gdot and the two source background equations. But

    Sigma_derived − Sigma_printed(47)
      = −2g * [(Theta+gdot)' + 3H(Theta+gdot)].

`regressions.py` computes this difference exactly. It is generally nonzero.
`independent_sigma.py` provides a second derivation: substitute the
homogeneous four-metric directly into the **unintegrated covariant action**,
take zeta=g*n, and use the second-derivative Euler operator. It does not
use the ADM action, its boundary algorithm, or the first Sigma expression.
The two derived Sigmas agree, and the remaining lapse-derivative Euler
terms cancel. Both source inconsistencies are retained as failing negative
controls, not silently corrected inputs.

This identifies an apparent source coefficient inconsistency, not a claim
that every conclusion of the paper is false. Section 3 leaves F to inverse
reconstruction. We reconstruct it with the **derived** Sigma set equal to
the prescribed smooth target, rather than claim to reproduce printed (47).
In jet notation F0=F(phi,1), FX=F_X(phi,1), FXX=F_XX(phi,1):

    F0=−2Hdot−3H²,
    FX=[F0+3H Theta+3H gdot−3g(2Hdot+3H²)]/2,
    FXX = the unique solution of Sigma_derived=Sigma_target.

`regressions.A25_reconstruction()` gives an explicit expression for FXX
in H,g,Theta and their derivatives, with no division by H. Substituting
4H a1=Theta−H(1+g)−gdot proves equivalence to the original covariant
dictionary. F=F0+FX(X−1)+FXX(X−1)²/2 is therefore an actual smooth
covariant extension solving the background equations and principal target.
A3 is the exceptional covariant relation; A2,A4,A5 use Ia completion.
The open domain X>0, F2−XA1<−1/4, 3XA1−4F2>1 contains the full
trajectory, since those last two quantities equal −1/2 and 2 at X=1.

The source a1 has an apparent 1/H pole. H has exactly one zero, at t=0,
and it is simple (S0 computes Hdot(0)=1/375). Here is an all-time check,
not merely a plot: for t>0 each contribution to a' is positive. For
t<0 set x=−t/10, d=1+x², delta=1/15, f=1/(1+exp(x)). Then
a=d^(1/10)[1+f(d^delta−1)]. Concavity gives d^delta−1<=delta*x²,
so a_x/d^(1/10)>=x/(5d)−delta*x² exp(−x)>0. The last strict inequality
uses x(1+x²)exp(−x)<=1/e+27/e³<3. The numerator in a1 also vanishes
at t=0, and the exact Taylor division in S0 gives its removable limit.
Thus a1 is smooth on the whole line. Also a>=1 directly from its positive
convex combination of powers of d.

## 2. Validated core and analytic tails

Let s=t/10, d=1+s², g=(2/3)sech²(s+1/10), lambda=1−3g. The numerically
evaluated quantities contain no 1/H or 1/Theta:

    Theta=H + g*(tanh(s)−tanh(s+1/10))/(5d),
    Sigma=1/d²+(1−tanh(s))/(2500d),
    P=H lambda Theta+lambda_dot Theta−lambda Theta_dot−Theta²,
    J=Sigma+3Theta².

The pure scalar unitary coefficients are J/Theta² and P/Theta²; in the
regular gamma chart they are J/lambda² and P/lambda². The Hamiltonian J
is positive. `a25_certificate.py` evaluates second-order analytic jets in
Arb at 160 bits and adaptively covers [−500,500] with 457 closed tiles.
Each tile proves a,J,P,J−P>0 and either Theta!=0 or lambda<0 with
Theta_dot>0. Exact outward **dyadic endpoints** are saved; pretty ball
strings are not used as sign evidence. The intervals meet exactly, with
no gaps. All possible zeros of Theta in the core are ascending simple
zeros, and both tails have the expected opposite signs, so there is
exactly one gamma crossing.

The infinite tails are closed as follows. Write x=|s|>=50, E=exp(−x),
r=1/6 in the future and r=1/10 in the past, and a0=(1+x²)^r.
With a=a0(1+e), elementary derivatives of the logistic function give

    |e|<=xE, |e_x|<=2xE, |e_xx|<=2xE.

To check these constants, e is f times either d^(1/15)−1 (past) or
−(1−d^(−1/15)) (future). For x>=50, the latter factor q obeys
|q|<=x, |q'|<=1, |q''|<=1, and |f|,|f'|,|f''|<=E. The stated bounds
follow by the product rule. In particular |e|<1/2. For h=10H and the
dominant h0=2rs/(1+s²), this gives the conservative estimates

    |h−h0|<=8xE, |h_s−h0_s|<=16xE,
    |g|<=4E², |g_s|<=8E², |g_ss|<=24E².

The g constants use exp(1/5)<3/2, itself enclosed in the certificate.
For b=10(Theta−H), differentiating its displayed regular expression gives
|b|<=16E²/d and |b_s|<=100E²/d. Also |h|<=1/x and |h_s|<=1/x² on
these tails (insert the previous errors into |h0|<=1/(3x) and
|h0_s|<=1/(3x²)). Set p=100P. Directly expanding around lambda=1,
Theta=H0 gives

    |P−P0| <=100xE/100,
    P0=2r(x²−1)/(100d²) >=1/(40*100*x²).

For an explicit error check, expand p=−h_s+(lambda−1)h²
+(lambda−2)hb−b²+lambda_s(h+b)−(lambda−1)h_s−lambda*b_s.
The first error is <=16xE; the other terms together are <=336E²,
which is less than 84xE on x>=50. For the speed gap, comparison with
the dominant J0 yields

    |(J−P)−(J0−P0)| <=200xE/100,
    J0−P0 >=1/d² >=1/(4x^4).

Indeed the dimensionless dominant gaps are (100+1/3)/d² in the future
and (100+7/25)/d² in the past. The Sigma error is at most
2E²/(25*100*d); the 3Theta² error together with the P error is bounded
by the displayed conservative 200xE/100. Thus both strict inequalities
follow from

    8000*x³*exp(−x)<1,     16*x^5*exp(−x)<1.

Both left sides decrease for x>=50, and their outward-rounded values at
50 are stored (<2e−13 and <1e−12). These even leave a factor-two
error margin relative to the lower bounds. Similarly
100*x²*exp(−x)<1 fixes the nonzero sign of Theta on each tail. No
finite truncation or sampling assumption enters these closures.

This gate certifies the corrected benchmark's reconstructed background,
all-time principal inequalities, regular crossing and causal geometry.
It is an **external regression**, not one of the frozen row witnesses.
In particular the paper's O(t^−4) quartic clock-kinetic coefficient is
not automatically a vanishing quartic coefficient after logarithmic
canonical normalization. Our three promoted witnesses satisfy the stronger
normalized tail tests in S2-rational-witnesses; we do not promote the
benchmark using only the paper's weaker clock-coordinate asymptotics.

## 3. Other mandatory regressions

KYY11 and the no-go identity are checked first at the source-action level
in S0 and then through the covariant Horndeski locus in S1. The proof in
S3 explicitly carries both divergent tensor integrals and handles gamma
crossing instead of assuming its quotient is globally regular.

For the [CPS16](https://arxiv.org/pdf/1610.04207) beyond-Horndeski escape,
`CPS16_dictionary()` independently checks the normalized quadratic
dictionary: Theta=T H−m1/2, Lambda=T−2m3,
Sigma=(m2−2T Hdot−6T H²)/2. Both their kinetic coefficient and their
generalized numerator agree with our reduced action. The usual positive
Horndeski numerator is recovered at m3=0. The covariant witnesses explicitly
realize the alternative: Lambda crosses zero while tensors remain healthy.
This is a mechanism regression, not a transcription of every CPS16 example.

For the strong-gravity loophole, `strong_gravity.py` supplies an independent
solvable covariant example, **not a claim to reproduce Ageeva et al.'s exact
Lagrangian**. Let d=1+t², I=atan(t)+pi/2, T=I/d² and a=d. Choose

    F2=−T/2, A1=A3=K=0,
    F=X*[3/(4I d^4)−3 Tdot²/(4T)].

The direct covariant reconstruction verifies both metric equations and

    Theta=1/(2d³), Lambda=T,
    GS=FS=3T>0, xi=2I², integral(a FT dt)=I²/2.

One way to obtain it is a conformal pullback of a canonical massless
Einstein-frame scalar: Omega=sqrt(I)/d, Einstein cosmic time
tau_E=(2/3)I^(3/2). It is smooth for every finite physical t and a>=1,
so physical causal geodesics are complete. Nevertheless
integral_R a FT dt=pi²/2 is finite and T->0 in both tails. It correctly
escapes the no-go's tensor-integral hypothesis and correctly fails the
frozen GR-tail witness contract. This negative control prevents confusing
physical and tensor-frame completeness.

Finally the rolling-luminal-matter matrix test is reproduced from the
covariant free-matter action and in both regular charts. The rank-one
matter speed bound forces the exceptional relation, but our certificates
also check the full Schur determinant; the relation is necessary, not
sufficient. A25 section 4's phi-dependent matter interactions are not
silently treated as free matter or as an M1 witness.

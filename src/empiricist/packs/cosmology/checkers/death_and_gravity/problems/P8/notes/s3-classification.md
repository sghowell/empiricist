# S3/S4 — The frozen function-group classification

This theorem is about [FORMULATION](../FORMULATION.md)'s timelike-clock,
flat-FLRW, physical-matter-frame **linear principal** class with regular
all-time geometry and conventional GR/scalar tails. It is not a theorem
about P8(a), all DHOST theories, arbitrary matter couplings, weak coupling,
nonlinear stability or UV completion.

## 1. Positive-numerator no-go, including gamma crossing

Write T=GT>0 and xi=a*T*Lambda/Theta on any connected component of
Theta!=0. The independently derived identity is

    xi' = a(FS+FT) > a FT > 0.

Assume Lambda>0 on that component and at every finite endpoint. At a
finite endpoint Theta=0, the S1 b chart is valid at sufficiently high
wavenumber because Lambda!=0. Its principal G11 is
−T*Theta_dot/Lambda. Strict positive gradient energy therefore requires
Theta_dot<0 at any such endpoint. This also rules out higher-order zeros,
touching zeros and zero intervals with such a boundary. There is no
blanket claim that gamma crossing itself is singular.

If the component has Theta>0, it cannot have a finite **left** endpoint:
a descending simple zero would instead make Theta negative immediately
to its right. The component must extend to −infinity. For any fixed t0
inside it, integrating the strict inequality to the past gives

    xi(t0)−xi(t) > integral_t^t0 a FT dt -> +infinity.

Hence xi(t) eventually becomes negative, contradicting its positive
numerator and Theta>0. If the component has Theta<0, its **right** endpoint
cannot be finite, and the divergent future tensor integral similarly
forces xi positive, a contradiction. Thus no such component can exist.
The identically-zero Theta case is excluded wherever Lambda>0, since
there G_b11=0, not strictly positive.

Only finite coefficient smoothness, strict principal health, positive
Lambda at component boundaries, and the two stated tensor integrals
enter this argument. The integrals diverge in the frozen class because
a>=a_min>0 and FT->M²>0 in each tail. This is a written analytic
calculus/topology lemma backed by exact coefficient/chart identities,
not a Lean-formalized proof and not a root-count extrapolation.

## 2. M0: C or D is necessary

With C and D disabled, F2X=0 and A3=0 as covariant identities. Put
FT=−2F2 and T=FT+2XA1. Tensor subluminality T>=FT>0, with X>0,
implies A1>=0 on the trajectory. The exact dictionary gives

    Delta=XA1/T,
    Lambda=FT*(1+XA1/T)>0.

The no-go above applies irrespective of F, F2_phi, A1_X or K_X.
Consequently all four subsets of {A,B} are excluded in M0. In particular
allowing braiding alone, or A1 with its dependent Ia completion, does
not remove the obstruction under these tail and speed hypotheses.

## 3. M1: both C and D are necessary

Let l=chi_dot, nonzero at every finite t. On Theta!=0 the coupled matrix
has K22=G22=1/2. Thus positive semidefiniteness of K−G forces its off-diagonal
entry to vanish. Equivalently

    Lambda=T(1−3Delta),
    A3=2(XA1−2F2)(A1−2F2X)/[X(3XA1−4F2)].

The denominator is strictly positive here:
3XA1−4F2=3XA1+2FT>0. `exclusions.py` checks the algebra exactly.
The same necessity holds in the regular b chart, since

    det(K_b−G_b)=−(T*w/Lambda+l)²/4,
    w=l(3Delta−1).

If C is disabled, substituting the exceptional relation yields

    Lambda = 2FT*(FT+2XA1)/(2FT+3XA1) > 0.

If D is disabled, the exceptional mismatch has the exact factorization

    Lambda−T(1−3Delta)
        = 2X(FT+XA1)(A1−2F2X)/T.

Its prefactor is strictly positive, so A1=2F2X along the trajectory,
Delta=0, and Lambda=T>0. These are on-shell necessary relations only;
they are not assumed to hold off the trajectory when a group is enabled.

For rigor one need not assume Theta's zeros are isolated in advance or
that the exceptional relation was derived in a chart covering the entire
line. Take any nonempty component of Theta!=0. The preceding positive
Lambda formulas hold throughout it and extend continuously, with a
strictly positive value, to each finite endpoint. Section 1 therefore
already contradicts that component. If Theta is identically zero on the
whole line, the conventional GR/scalar tails give Lambda->M²>0; in such
a tail the regular b chart instead has G_b11=0 and violates strict health.
Thus zero intervals and putative simultaneous chart zeros do not evade
the exclusion by invalidating a quotient used in its derivation.

There is no hidden J!=0 assumption at a boundary: the joint auxiliary
elimination in S1 exists for large q with Lambda!=0 even if J=0, and
then K_b is degenerate rather than positive definite. This is why a
vanishing lapse-reduced Hamiltonian denominator cannot rescue the row.

Using the scalar as clock does not lose any allowed solutions with X>0:
the monotone field admits a smooth local inverse at every finite time.
Under phi=f(clock), the second-Hessian terms transform triangularly:
A1 and A3 multiply their same second-Hessian invariants by nonzero powers
of f'; lower-Hessian terms may feed F and K, but cannot create a nonzero
A3 from A3=0 or F2X from F2X=0. A1=0 is likewise preserved. K_X is
unrestricted in every exclusion above, so possible induced braiding does
not enlarge an excluded row beyond the proof's hypotheses.

## 4. Existence and minimality

The exact C and D witnesses from S2 decide every M0 row containing either
C or D. The CD witness with fully backreacting free canonical matter
decides every M1 row containing both C and D. Enabled groups are
permissions, not requirements; the same action remains admissible when
further groups are enabled. Conversely the exclusions cover every row
without the indicated minimal support.

| Optional groups | M0 | M1 |
|---|:---:|:---:|
| baseline | N | N |
| A | N | N |
| B | N | N |
| C | E | N |
| D | E | N |
| AB | N | N |
| AC | E | N |
| AD | E | N |
| BC | E | N |
| BD | E | N |
| CD | E | E |
| ABC | E | N |
| ABD | E | N |
| ACD | E | E |
| BCD | E | E |
| ABCD | E | E |

Therefore all **32 sector-row verdicts** are decided: M0 has 12 E and
4 N rows, with minimal supports {C} and {D}; M1 has 4 E and 12 N rows,
with the unique minimal support {C,D}. The baseline F and F2(phi) are
always allowed. This is covariant **function-group minimality relative to
that baseline**, not a basis-independent minimum count of monomials.

The certificate includes the full 16-row inclusion enumeration. Its
mathematical dependencies are S1's action/chart identities, the written
no-go lemma above, and the all-time sign/domain/tail witness certificates.
No bounded parameter search supplies an N verdict. Known no-go and bounce
mechanisms are not claimed as new; no literature-priority claim is made
for the frozen classification itself.

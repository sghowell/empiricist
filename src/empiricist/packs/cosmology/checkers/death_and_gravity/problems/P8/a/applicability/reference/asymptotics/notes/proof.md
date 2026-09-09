# Written proof and hypothesis audit

## 1. Smooth state difference on the entire patch

Use the field, prescription and FK convention fixed in
[FORMULATION.md](../FORMULATION.md). A.3 is the source of the evaluated
reference EED, including its nonzero anomaly and the actual state's vanishing
radiation integration constant. Nothing here resets that constant for an
arbitrary state.

For `a=A*eta`, `a''=0`, and `chi=a*phi`, the minimal equation becomes
`(partial_eta^2-Delta_x)chi=0`. Multiplication by the smooth nonzero conformal
factor on `eta>0` carries the two-point function to that of the flat wave
field on the Minkowski half-space. The difference
`F=a*a'*(W_omega-W_ref)` is a smooth bisolution there.

For clarity, smoothness is a consequence of the ordinary Hadamard condition.
Both two-point distributions have the Hadamard wavefront orientation, and
their difference has vanishing antisymmetric part by the same CCR. Its
wavefront set is therefore contained in both that orientation and its
transpose. These disjoint cones have empty intersection, so the difference
is smooth. This is a distributional wavefront argument using the usual
microlocal Hadamard condition directly on `W2`. The propagation and
characterization are discussed in
[Sahlmann--Verch, Theorems 5.5 and 5.8](https://arxiv.org/pdf/math-ph/0008029v2).
The latter theorem is stated for C-infinity-regular Weyl states; we do not
import its extra state-level regularity assumptions. We assume the ordinary
two-point wavefront condition itself and use only the preceding distribution
argument. No higher n-point regularity or quasifreeness is needed.

The difference is real and symmetric for a real scalar: Hermiticity and the
common commutator give these properties. Smoothness on the product is
important; smoothness of only the diagonal would not suffice below.

## 2. Cauchy extension with no spatial growth restriction

Choose any `eta0>0`. Its entire spatial slice is a Cauchy surface of the
Minkowski half-space and also of full Minkowski spacetime. The four functions

`F_ij(x,y)=[partial_eta^i partial_eta'^j F]_(eta=eta'=eta0)`, `i,j in {0,1}`,

are jointly smooth on `R3 x R3`. They can be noncompact and unbounded at
spatial infinity. The general compact-data existence, uniqueness and causal
support input is
[Sahlmann--Verch, Proposition 3.3](https://arxiv.org/pdf/math-ph/0008029v2).
Here the flat three-dimensional spatial geometry also gives an explicit
local formula. For signed `s`, define

`M_s f(x)=(1/(4*pi))*integral_(S2) f(x+s*omega) dOmega`,

`S_s f=s*M_s f`, and `C_s f=partial_s(s*M_s f)`.

Kirchhoff's solution is `C_s f+S_s g`, with displacement `s=eta-eta0`.
The spherical mean is even in `s`; the displayed operators are smooth at
zero, have Cauchy data `(1,0)` and `(0,1)`, and satisfy the flat wave
equation. These facts follow from the spherical-mean identity
`partial_s^2(s*M_s f)=s*M_s(Delta f)`. They can first be checked for compact
data and then localized; no Taylor-series convergence is assumed.

Each integral samples a compact sphere. For a compact target set and a
bounded displacement interval, all its causal footprints lie in a compact
spatial ball. Multiply any smooth data by a cutoff equal to one on a
neighborhood of that ball, solve the compact-data problem, and restrict to
the target. Finite propagation and uniqueness make the answer independent
of the cutoff. Such solutions glue on overlapping compact sets. Thus
arbitrary smooth data, even without decay, produce a unique smooth solution
for every finite signed displacement. There is no global energy or
temperedness assumption hidden in this localization.

For two variables put `s=eta-eta0`, `s'=eta'-eta0` and define

`F_tilde = C_s^x C_s'^y F_00 + S_s^x C_s'^y F_10`
`          + C_s^x S_s'^y F_01 + S_s^x S_s'^y F_11`.

This is jointly smooth on full Minkowski squared: on each compact product,
the two spherical integrations and all parameter derivatives range over
fixed compact data sets. Differentiation in the other variable commutes
with them. The two wave operators commute with evolution in the other
variable, so `F_tilde` is a bisolution and has all four prescribed data.
First applying Cauchy uniqueness in one variable, then in the other, shows
that `F_tilde=F` for `eta,eta'>0`. This is not merely a separate-continuity
or a diagonal-extension argument.

Only the smooth difference is extended. No assumption is made about
positivity of a freely invented extension, and no extension of the physical
metric is claimed. As a separate consistency check, the free-field time-slice
isomorphism means that a state on this whole flat half-space already
determines a state on full Minkowski space; see
[Brunetti--Fredenhagen--Verch, Theorem 2.2](https://arxiv.org/pdf/math-ph/0112041v1).
That algebraic observation is not needed in the explicit proof.

In particular, `F_tilde` and its finitely many derivatives are bounded on
compact sets including `eta=eta'=0`. This is a consequence of finite
propagation from `eta0`, not a new big-bang regularity assumption.

## 3. Exact EED and its leading limit

In four dimensions the massless minimal EED is `(nabla_U phi)^2` at the
level of **state differences**. The common renormalization terms cancel;
no classical field identity is imposed on a single renormalized stress.
This is the same FK difference observable used and verified in A.2.

Since `partial_t=(A*eta)^(-1)*partial_eta`, direct differentiation gives

`Delta E = [partial_t partial_t' {F/(A^2*eta*eta')}]`
`        = A^(-4)*[eta^(-4)*F_11 - eta^(-5)*(F_10+F_01) + eta^(-6)*F_00]`

at equal points. Here the subscripts denote derivatives at the observation
point, not the data on the earlier chosen Cauchy slice. Their boundedness
shows `Delta E=O(eta^(-6))`, locally uniformly in space for a fixed state.
The constant in this estimate can depend on that state and the compact set.

Adding A.3's evaluated term produces

`A^4*eta^8*E_omega = hbar/(320*pi^2)`
`                      + eta^2*f0-eta^3*f1+eta^4*f2`.

The limit follows. With `eta=sqrt(2*t/A)`, the three difference terms have
coefficients `1/(8*A*t^3)`, `-1/(2^(5/2)*A^(3/2)*t^(5/2))`, and
`1/(4*A^2*t^2)` multiplying the corresponding bounded jets. Since
`t^4=A^4*eta^8/16`, the proper-time limit is `hbar/(5120*pi^2)`.
The code checks differentiation and this clock conversion independently.

## 4. The necessary SEE component cannot match

FK has `G=-kappa*T` for the ordinary Einstein equation. On this background
`R=0`, `E(G_FK)=R_FK(U,U)=-3/(4*t^2)`, and `E(g_FK)=-1`.
The variation tensors `I,J` vanish, not the quantum anomaly. For the
explicitly stated additional radiation, `E(T_rad)=C/a^4`.
Taking EED of the proposed equation yields

`E_omega+C/a^4 = 3*b/(4*kappa*t^2)+ell/kappa`.

Thus the normalized required source tends to zero, contradicting Section 3.
Only a necessary scalar component was used, so allowing an inhomogeneous or
anisotropic quantum state does not escape this obstruction. Constant finite
renormalizations of the cosmological/Newton terms merely change coefficients
of `eta^0` and `eta^(-4)`; they cannot cancel `eta^(-8)`.

For specified jet bounds the normalized residual of this equality is bounded
below by `c_*-P(eta)`, where `c_*=hbar/(320*pi^2)` and

`P(eta)=M0*eta^2+M1*eta^3`
`       +(M2+abs(C-3*b*A^2/kappa))*eta^4+abs(ell)*A^4*eta^8/kappa`.

Every coefficient is nonnegative. Certifying `P(eta_cut)<c_*/2` therefore
certifies a positive margin for all `0<eta<=eta_cut`, provided the supplied
jet bounds hold there. Existence of some cutoff is qualitative for every
state; evaluating a cutoff requires actual state-specific bounds.

## 5. Controls and what they rule out

For a real smooth flat-wave solution `chi`, shifting the vacuum field by
`chi/a` is an algebraic coherent-state automorphism. Its two-point difference
is `F=chi(X)*chi(Y)`; it is positive and Hadamard on the domain of that
solution. No unitary implementation or finite total energy is needed.

- `chi=B` gives `Delta E=B^2/(A^4*eta^6)`. This verifies a noncompact-data
  state with a genuinely nonzero subleading term.
- `chi=B*eta` gives a constant physical field and `Delta E=0`. Its nonzero
  mixed jets check the exact derivative cancellations.
- Polynomial wave solutions in all three spatial coordinates test the
  double Cauchy evolution and all four data. Two implementations agree
  exactly. Finite polynomial series are used only for these benchmarks.
- On the smaller causally convex region `eta>0, eta-x1>0`, the smooth wave
  `chi=B/(eta-x1)` gives `Delta E=4*B^2/(A^4*eta^8)` along `x=0`. It does
  not have smooth data on any full constant-eta spatial slice. This shows
  exactly why a restricted-domain state cannot replace the whole-patch
  hypothesis.
- A formal symmetric kernel `F=c/(eta*eta')` has the same dangerous power
  but fails the flat wave equation in each variable for `c!=0`; smoothness
  on the open positive-time product alone is not enough.
- If an extra fluid with `rho_X=-rho_ref`, `p_X=-p_ref` is admitted, it is
  separately conserved, traceful and negative. With `ell=0` and
  `C=3*b*A^2/kappa`, the reference plus this fluid plus classical radiation
  matches the Einstein tensor in both density and pressure. This is a
  deliberate exclusion control, not an allowed source or a physical model.

The proof uses the limit toward the missing endpoint. It says nothing by
itself about solving the SEE only on a slab `eta>=eta_->0`, nor about a
nearby metric with backreaction. It establishes neither a new singularity
theorem nor reliability of the semiclassical approximation at trans-Planckian
curvature. Its practical implication is that an SEE/focusing continuation
must change the exact testbed or the explicitly declared source model.

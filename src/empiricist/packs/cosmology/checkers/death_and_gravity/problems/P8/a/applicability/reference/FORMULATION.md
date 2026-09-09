# P8(a) A.3: radiation-reference EED and an absolute QSEI

This checkpoint evaluates the reference term left open by A.2. It concerns the
same fixed curved background and one specified free field, not a solution of the
semiclassical Einstein equation (SEE). A.1 and A.2 remain immutable.

## Physical and renormalization hypotheses

- Four-dimensional radiation FLRW patch with spatial sections R3,
  `g_FK=(A*eta)^2*(deta^2-dx^2)`, `A>0`, `eta>0`, and
  `t=A*eta^2/2>0`. Comoving observers have `U=partial_t`.
- Free real massless minimally coupled scalar, with reference two-point function
  `W_ref=W_Mink/[a(eta)*a(eta')]`. Its rescaled positive-frequency modes are
  `exp(-i*k*eta)/sqrt(2*k)` at every `k>0`, with vacuum occupations. This is the
  radiation conformal-reference state, not a state matched from inflation.
- Use the locally covariant, conservation-preserving Hadamard prescription
  described in Fewster--Kontou (FK), arXiv:1809.05047v2, Eqs. (24)--(27), with
  Minkowski-vacuum normalization and the usual Hollands--Wald scaling/analyticity
  restrictions. Its finite stress freedom has the form
  `c1*m^4*g+c2*m^2*G+c3*I+c4*J`, where `I,J` are the metric variations of
  `integral R^2` and `integral Ricci^2`. Every such term vanishes on this patch.
  The proof does not require a numerical choice of `c3,c4` or subtraction scale.
- The auxiliary conformally coupled field is used only to evaluate this
  reference stress. It is identified with the minimal field on this `R=0`
  patch using the same parametrix and conservation correction. This is not an
  identification of their stress tensors in general states or on general FLRW.
- Independently adjustable cosmological and Einstein couplings are not silently
  absorbed into this matter stress. Their values in a gravitational equation
  are unspecified. If an enlarged prescription adds `lambda*g+gamma*G_FK`, its
  EED shift is `-lambda-3*gamma/(4*t^2)` and must be retained separately.

The source-to-FK sign dictionary and the source-supported renormalization
argument are part of the hypotheses audit in [notes/derivation.md](notes/derivation.md).
The arithmetic certificate checks the displayed calculations; it is not a
machine proof of the underlying curved-spacetime quantum-field theorems.

## Reference result

With `c=1`, the physical reference density, pressure, FK trace and EED are

`rho_ref = hbar/(15360*pi^2*t^4)`,

`p_ref = hbar/(9216*pi^2*t^4) = (5/3)*rho_ref`,

`Tr_FK(T_ref) = rho_ref-3*p_ref = -hbar/(3840*pi^2*t^4)`,

`E_ref = T_ref(U,U)-Tr_FK(T_ref)/2 = hbar/(5120*pi^2*t^4) > 0`.

The vanishing scalar curvature does **not** imply zero reference stress. The
nonzero anomaly is retained. Conservation and trace alone allow an additional
`C/a^4`; the specified vacuum modes make the nonlocal conformal-vacuum mode
integrand zero pointwise and fix `C=0`. No decay condition is substituted for
this state calculation. A nonvacuum occupation negative control keeps that
distinction explicit.

## Absolute bound and sampling domain

The target may be any Hadamard state of the minimal field on this fixed patch.
Use real `h in C_c^infinity((0,infinity))`, or its `H2_0(t_-,t_+)` extension with
`0<t_-<t_+<infinity`; both `h` and `hdot` have zero endpoint traces. Sampling
through the finite-age endpoint `t=0` is excluded.

Combining the evaluated reference with the pinned A.2 difference inequality gives

`integral h^2*E_omega dt >= -hbar/(16*pi^2)*B[h]`,

`B[h] = integral [hddot^2-3*hdot^2/(8*t^2)+521*h^2/(1280*t^4)] dt`.

Equivalently,

`B[h] = ||hddot||^2-(3/8)||hdot/t-3*h/(2*t^2)||^2-(559/1280)||h/t^2||^2`.

In particular, the ordinary absolute Minkowski-coefficient estimate holds for
every admitted sample, without a small-duration hypothesis:

`integral h^2*E_omega dt >= -hbar/(16*pi^2)*||hddot||^2`.

The stronger functional is also nonnegative. For any arbitrary clock scale
`t_*>0`, put `x=log(t/t_*)` and `h(t)=t^(3/2)*u(x)`. Then

`B[h] = integral_R [u_xx^2+(17/8)*u_x^2+(161/1280)*u^2] dx >= 0`.

This is an evaluated state-independent lower bound on an absolute renormalized
observable. Neither its optimality over states nor a globally optimal QEI is
claimed. Choosing a reference in the derivation does not leave an unevaluated
reference-state input in the final bound.

## Boundary of the result

The calculation covers all comoving lines and hence all normals to constant
cosmic-time slices. It does not cover tilted observers, normals to other slices,
perturbed metrics, arbitrary SEE solutions, massive/nonminimal/interacting
fields, or additional matter models.

The trace required by the zero-cosmological-constant radiation Einstein tensor
is zero, whereas the reference quantum trace is nonzero and scales as `t^-4`.
Thus this reference alone, or this reference plus ordinary traceless classical
radiation, is not an exact source for the assumed metric. A fixed cosmological
term cannot cancel that time-dependent trace throughout an interval. No
self-consistent SEE solution, direct A.1 Ricci hypothesis, new singularity
theorem, realistic-field cosmological application, or full P8(a) completion is
established here.

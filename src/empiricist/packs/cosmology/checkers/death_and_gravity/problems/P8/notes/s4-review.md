# S4 — Adversarial self-review and completion boundary

This is a documented self-review using independent derivations/arithmetic
where stated, **not an external peer review or a separate-agent review**.
No subagents were used. Completion means the exact frozen linear P8(b)
classification in the formulation, not a resolution of every P8 question.

## Claim-level checks

| Potential failure | Disposition |
|---|---|
| Import P9's sign conventions or H>0 chart | Isolated (+---) metric calculation; R and tensor normalization rederived; cosmic H has no positivity assumption |
| Assume Ia degeneracy only on the trajectory | Exact covariant completion on an X tube; arbitrary-tilt velocity Hessian checked; nonzero six-metric minor |
| Insert source Theta/Sigma instead of deriving them | Both obtained from the covariant ADM expansion; Sigma additionally checked by a different unintegrated homogeneous Euler calculation |
| Treat gamma poles as automatically harmless | Smooth canonical Hamiltonian with J>0 and an explicit high-frequency b chart; time-dependent canonical boundary included |
| Dismiss J=0 using a chart that already divided by J | Joint auxiliary elimination has no 1/J; its derived kinetic determinant genuinely vanishes at J=0 |
| Exclude all gamma crossings in the no-go | Orientation follows from the regular gradient coefficient; connected-component proof includes touching/nonisolated-zero possibilities |
| Infer M1 exclusion in a chart unavailable at an endpoint | Exceptional positive-Lambda formula extends continuously from each nonzero-Theta component; endpoint b-chart proof applies there |
| Use a spectator instead of the prescribed matter | Free canonical metric action expanded; background backreaction, actual chi primitive and conserved a³ chi_dot checked |
| Impose an off-flag only at X=1 | Explicit full covariant functions and minimal-support checks; A1=K=0 identities for all promoted witnesses |
| Claim full-row exclusions from failed search | Every N row follows from the analytic no-go plus exact algebra; only E points were explored |
| Treat source formulas as infallible | Both D and Sigma inconsistencies are retained as negative controls; corrected reconstruction explicitly distinguished from printed equations |
| Lose positivity in saved interval strings | Store exact outward dyadic endpoints; tests independently inspect their signs and chart conditions |
| Extrapolate a finite grid into a tail theorem | Rational witnesses use global Sturm and Bernstein proofs; A25 uses 457 tiles plus explicit monotone exponential tail bounds |
| Mistake clock-coordinate decay for canonical tails | Slow-decay candidates rejected; weighted field-redefinition, mixed derivative and remainder bounds retained in each certificate |
| Confuse physical and tensor-frame completeness | Two separate proofs, plus a covariant countercheck with complete physical geometry and finite tensor integral |
| Quietly assume a UV/scattering vacuum | Tube domain and CD's 1/X stated explicitly; no X=0 analyticity or scattering-positivity conclusion |
| Promote a numerical observation to a formal proof | Exact/interval certificates and written analytic lemmas are distinguished; no Lean FORMALIZED label |

The covariant Bianchi identity closes the scalar background equation after
the two metric equations and the chi equation; the clock derivative is one.
The actual H=a'/a and chi_dot=chi' definitions are checked rather than
treated as independently assignable background functions.

The conventional tail's Lambda->M² statement is the coefficient limit of
the derived spatial metric/lapse block as the normalized action tends to
Einstein gravity with conventional scalars. It is not a disformal matter
frame assumption. The M1 no-go needs it only to discard the exceptional
case Theta identically zero on the entire real line; all nonzero-Theta
components are excluded without assuming isolated zeros globally.

## Verification and evidence limitations

Run the explicit P8 pytest suite, `p8.verify_all --check`, Ruff and
`git diff --check` from the README. The replay recomputes the S0 anchor
and six later artifacts and checks hashes of the P8 derivation, tests and
proof notes. It fails on altered scope/data, and tests cover changed
operator support and loss of interval sign information. The S0 artifact
and its three source hashes remain unchanged.

The trusted base is Python, SymPy for exact derivation, FLINT rational
polynomial arithmetic for Sturm counts, exact Fraction arithmetic for
Bernstein conversion, Arb for outward-rounded transcendental enclosures,
and the explicit analytic lemmas in the notes. These are not independent
physical experiments or kernel-checked differential-geometry proofs.
In particular the no-go's integration/topology step, regular-ODE theorem,
canonical-field expansion and analytic benchmark-tail estimates remain
written mathematical proofs whose hypotheses are pinned in the reports.

## Scope audit and stopping point

The completed theorem decides all 32 M0/M1 sector-row verdicts and their
minimal covariant function groups. Its witnesses establish background
existence, regular linear continuation, healthy subluminal principal cones,
causal geodesic completeness and the specified asymptotic tube limits.

No quantitative strong-coupling criterion, scattering background, UV
dispersion assumptions, or P8(a) target was frozen. Consequently **no UV
or strong-coupling gate is marked passed**. These questions remain open
extensions, as do nonlinear/BKL stability, every-wavelength infrared
stability and observables. Applying P9's conditional positivity prior here
would be unsupported. No user choice is needed to complete the stated
linear classification; expanding beyond it requires a new scoped task.

All P4/P9 edits and running work were left outside this task. No paid
compute, external publication, commit or push was performed.

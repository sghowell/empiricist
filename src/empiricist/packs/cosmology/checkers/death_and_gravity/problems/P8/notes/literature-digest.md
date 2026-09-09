# P8(b) source pins and modelling boundaries

Checked 2026-09-04. Source equations below are inputs/regressions until an
independent covariant derivation replaces them. Mathematical identities
checked downstream do not verify the transcription's physical provenance.
Closure update: S1/S2 have now supplied that independent covariant bridge
and the scoped regression certificates; see `s1-derived-action.md` and
`s2-benchmarks.md`. The descriptions of S0 below retain their historical
narrow scope. Two source expressions remain negative controls.
Equation numbers for A25 refer to its HTML numbering; the PDF uses
section prefixes (for example HTML (10g) is PDF (2.10g)).

## D1 — The quadratic-action anchor

Kobayashi, Yamaguchi, Yokoyama, *Generalized G-inflation*,
[arXiv:1105.5723v4](https://arxiv.org/pdf/1105.5723v4), (4.24), (4.29)–(4.33).
We transcribe (4.24), vary lapse/shift, and explicitly remove the mixed
derivative by a boundary term. GS and FS are outputs; (4.32)–(4.33) are
known-answer checks. This source uses the P9-style metric/X conventions;
only its already-normalized quadratic action is used in S0. Mapping the
covariant coefficients into P8's different conventions remains open.

## D2 — The no-go's quantifiers

Kobayashi, *Generic instabilities of nonsingular cosmologies in Horndeski
theory*, [arXiv:1606.05831v2](https://arxiv.org/pdf/1606.05831v2), (9)–(15)
and footnote 1. The short global argument assumes a continuous finite xi
chart; divergent tensor integrals at both ends force its sign change.
Neither finite Theta alone nor physical metric completeness alone supplies
all those assumptions. Its matter extension is (16)–(24).

Creminelli et al., *Stability of Geodesically Complete Cosmologies*,
[arXiv:1610.04207](https://arxiv.org/abs/1610.04207): later S2 regression
for the beyond-Horndeski escape and the tensor-frame completeness condition.
Ageeva, Petrov, Rubakov, *Nonsingular cosmological models with strong
gravity in the past*, Phys. Rev. D 104, 063530 (2021), project bibliography
`ageeva2021`: later S2 covariant regression for failure of the tensor-tail
hypothesis. Neither physical construction has been replayed by P8 yet.

## D3 — Matter and the selected bounce

An et al., *Fully viable DHOST bounce with extra scalar*,
[arXiv:2501.09985v2](https://arxiv.org/html/2501.09985v2):

- (2)–(3): covariant basis and Ia completion; (6): tensor coefficients.
- (9c), (10b–h): coupled matrices and mixing, with the D correction below.
  S0 checks matrix and exceptional-locus algebra, not the covariant reduction.
- (17): necessary exceptional relation for rolling luminal matter.
  It is not sufficient; test the full principal-matrix cone.
- (28), (30), (36), (42)–(45), (50): first M0 benchmark inputs.
  Freeze epsilon = 5 from (45), not epsilon = 10 in Fig. 1.
- (52)–(54): the published extra scalar has phi-dependent interactions.
  It is not our free canonical M1 sector.

At X=1 its A1 vanishes but A1_X generally does not. Off-trajectory operator
restrictions must therefore be enforced before assigning a ladder row.
The source's a1 formula contains a removable 0/0 at the bounce; S0 derives
that limit and a Theta expression without 1/H. The distinct Theta=0
crossing still requires an independent regular-chart proof.

Mironov, Rubakov, Volkova, *Superluminality in DHOST theory with extra
scalar*, [arXiv:2011.14912](https://arxiv.org/abs/2011.14912), is the
earlier exceptional-subclass result. Its (8a) supplies D for S0;
its unreduced action (25) is an independent S1/S2 source check.

### D3.1 — Coefficient inconsistency caught by the exact check

A25 HTML (10g), also the extracted PDF (2.10g), prints

    D_printed = 2 phi_dot (F2_X − A1).

In contrast, [MRV20 (8a)](https://arxiv.org/pdf/2011.14912) gives

    D_MRV = 2 phi_dot (2 F2_X − A1).

These sources use the same (+---), X=phi_dot² convention. Holding A25's
other displayed coefficients fixed, solving f=g with D_printed gives
a result differing from its (17) by

    4 F2_X (F2−A1 X) / [X(3 A1 X−4F2)].

It also fails the quartic Horndeski check: A1=2F2_X and A3=0 imply
Delta=0, so D must vanish to recover f=g. D_MRV passes; D_printed does not.
For the benchmark F2_X=−g1, A1=0 on X=1, the exceptional relation gives
A3=2g1 and Delta=g1. D_MRV then gives Lambda=1−3g1 as in A25 (39);
D_printed instead gives 1−g1. Three source-level consistency checks
therefore select D_MRV. The printed expression remains a negative-control
test; no silent alteration of a source equation is allowed.

This is an identified algebraic inconsistency/apparent coefficient typo,
not a refutation of the published model or a first-principles derivation
of the correct DHOST perturbation action. That bridge remains S1 work.

## Novelty and stopping rule

No known bounce, no-go, or exceptional relation is claimed as new here.
The intended contribution is a certificate-backed boundary in the frozen
covariant groups, with a fixed matter sector and genuine all-time coverage.
An exact identity from a source quadratic action is an initial verification
anchor, not that boundary. Full background reconstruction, crossing charts,
and tail certificates are required before any existence claim.

### D3.2 — Sigma inconsistency found by independent covariant derivation

S1 independently matches A25's tensors, Theta, Lambda and background
equations for arbitrary g1,a1, but not its (47). The exact difference is
Sigma_derived−Sigma_printed=−2g1*[(Theta+g1_dot)'+3H(Theta+g1_dot)].
A second homogeneous calculation from the unintegrated four-dimensional
covariant action agrees with Sigma_derived. The corrected M0 regression
reconstructs F using that result to impose the source's target (50).
It is not asserted to agree with printed (47), nor is this discrepancy
by itself a refutation of every physical claim in the paper. Full evidence
and the all-time reconstruction are in `s2-benchmarks.md`.

# Primary-source dictionary

Sources were read directly on 2026-09-05. Equations below fix conventions;
the retarded spatial integral, finite part, response formulas and explicit
preparation bounds are derived in this checkpoint.

| Source | Exact input and scope |
| --- | --- |
| [Gottschalk--Siemssen, 1809.03812v3](https://arxiv.org/pdf/1809.03812v3) | Eqs. (1.2), (2.1)--(2.2): source signature, positive-time Box, potential `V=-a''/a`. Eq. (2.8): radial Fourier normalization. Section 2.5, Eqs. (2.17)--(2.20): raw physical-length Hadamard parametrix and its spatial coincidence expansion. Eqs. (3.4)--(3.6): conserved stress, full finite freedom and anomaly coefficient. No moment-space SEE existence theorem is imported. |
| [Hollands--Wald, gr-qc/0404074v2](https://arxiv.org/pdf/gr-qc/0404074v2) | Lemma 6.2 and Eqs. (219)--(228): smooth parameter dependence of the past-transported Hadamard two-point function after subtraction. A.5 already supplies the compact-causal-footprint localization for the homogeneous preparation. This permits taking the first derivative at coincidence and gives qualitative Taylor remainders, not numerical bounds on them. |
| [Fewster--Kontou, 1809.05047v2](https://arxiv.org/pdf/1809.05047v2) | Eqs. (23)--(28), (31): A-track stress/curvature conventions, conserved Wick construction and EED definition. This checkpoint does not replace their QSEI hypotheses by diagonal stress smoothness. |

GS uses `g_S=-dt²+a²dx²` but defines `Box=-g_S^ab*nabla_a*nabla_b`.
Therefore `Box_GS=Box_FK`, while `g_FK=-g_S`, `R_ab,FK=-R_ab,S` and
`R_FK=R_GS`. Physical `rho=T_tt`, `p=T_ii/a²` are unchanged;
`Theta_FK=rho-3p=-Trace_GS`. GS's displayed curvature tensor is `I_GS=-I_FK`,
so its `c3*I+c4*J` corresponds to `gamma=-(c3+c4/3)` here.

The raw Wick square is specifically `[W-H_lambda]`; adding `alpha*R` would
alter its formula. Changing only the subtraction length is already tracked,
and does not eliminate independent finite stress freedom. No field equation
is imposed inside a renormalized product: the nonzero parametrix remainder
in GS (3.5) is essential to the trace derivation.

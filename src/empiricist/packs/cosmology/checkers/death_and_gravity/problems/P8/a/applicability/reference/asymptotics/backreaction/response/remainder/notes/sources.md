# Primary inputs and conventions

Read directly on 2026-09-05. The new IR/UV inequalities, finite-potential
decomposition, exact stress-error reconstruction and rational jet bounds
are proved here rather than borrowed from an existence theorem.

| Source | Input used and boundary |
| --- | --- |
| [Gottschalk--Siemssen, 1809.03812v3](https://arxiv.org/pdf/1809.03812v3) | Eqs. (2.1)--(2.2), (2.8)--(2.9): potential, radial normalization and covariance evolution. Section 2.5 and Eqs. (3.4)--(3.6): conserved point-split stress, raw physical-length parametrix, anomaly and finite freedom. The third-order covariance equation follows directly from this system; no asymptotic WKB theorem is assumed. |
| [Hollands--Wald, gr-qc/0404074v2](https://arxiv.org/pdf/gr-qc/0404074v2) | A.5/A.6 already audit the past-prepared Hadamard family and its local causal-footprint construction. The present numerical remainders follow from explicit mode estimates, not from promoting qualitative smoothness into a numerical bound. |
| [Meda--Pinamonti--Siemssen, 2007.14665v1](https://arxiv.org/pdf/2007.14665v1) | Context only: its massive-field result and nonlocal highest-derivative analysis do not automatically specialize to a quantitative massless minimal SEE theorem. None of its existence constants is imported here. |

Keep FK `g_F=-g_GS`, `R_ab,F=-R_ab,GS`, `R_F=R_GS`. The GS definition
`Box=-g_GS^ab*nabla_a*nabla_b` equals FK's positive-time Box. Physical
rho and p agree; `Theta_F=-Trace_GS`, and `I_GS=-I_F`. Therefore the
physical finite tensor coefficient is `gamma=-(c3_GS+c4_GS/3)` on FLRW.

The actual and approximate stresses retain the same exact local prescription.
Their difference is scheme-independent under a **common** length/finite-term
change; neither absolute stress is thereby scheme-independent. The Born
functional is never promoted to a positive state.

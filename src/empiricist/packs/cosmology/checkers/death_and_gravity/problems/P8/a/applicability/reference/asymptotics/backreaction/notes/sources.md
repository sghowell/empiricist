# Primary-source dictionary and verification boundary

Reviewed 2026-09-05. The report pins this dictionary, not downloaded PDFs.
Replay is offline. General quantum-field/PDE theorems remain written inputs.

| Source | Precisely used input and limitation |
| --- | --- |
| [Parker--Simon, gr-qc/9211002v1](https://arxiv.org/pdf/gr-qc/9211002v1) | Sections II--III, especially Eqs. (3.5)--(3.14), and Appendix B explain replacing higher-order terms using lower-order equations and tracking perturbative branches/integration modes. Their field-dependent coefficients are not used to replace the pinned A.3 minimal-field stress. Exact solutions of a reduced equation are not automatically exact quantum solutions. |
| [Hollands--Wald, gr-qc/0404074v2](https://arxiv.org/pdf/gr-qc/0404074v2) | Lemma 6.2, Eqs. (219)--(228), proves joint smoothness near the diagonal of the retardedly transported quasifree state's two-point function minus the corresponding Hadamard parametrix for smooth compact metric perturbations. The proof in this directory supplies the local causal-footprint reduction for a temporally prepared homogeneous metric. No numerical derivative bound is taken from the lemma. |
| [Gottschalk--Siemssen, 1809.03812v3](https://arxiv.org/pdf/1809.03812v3) | Eq. (2.2) gives the rescaled potential `V=(6*xi-1)*a''/a+a^2*m^2`. Theorems 5.1 and 5.6 give local existence/continuous-dependence bounds under moment-space and coefficient hypotheses. Section 5.6 and Proposition 5.10 discuss smooth preparation and Hadamard propagation. These are context and cross-checks; their full SEE theorem is not asserted to have been quantitatively specialized here. |
| [Fewster--Smith, gr-qc/0702056v2](https://arxiv.org/pdf/gr-qc/0702056v2) | The absolute-QEI construction uses a Hadamard series and microlocal/Sobolev estimates. It explains why diagonal RSET smoothness is not, by itself, a numerical bound on the half-line Fourier integral needed for a QSEI. No new QSEI constant is imported from it here. |

The A.4 certificate is pinned at
`05d8484a9f39cc4c47a6a6441d7ab589aea78ca449773bdc3cad72bd42dc5eec`
and replayed with A.3/A.2/A.1 before new calculations. A.3 fixes the reference
stress, common prescription, anomaly, and FK sign dictionary.

The first-order equations, exact reduced solution, rational Taylor/defect
bounds, clock conversion, explicit curvature variation and mode-response
identities are derived in this directory. Independent rational polynomial
arithmetic checks the symbolic route. The qualitative state theorem and
the conditional numerical response interface are kept separate. Neither
the routine existence of a finite response constant on a compact set nor
a synthetic supplied constant is represented as a computed physical bound.

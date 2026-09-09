# Primary-source and verification dictionary

Reviewed 2026-09-05. Links identify versions and mathematical inputs; downloaded
PDF bytes are not certificate inputs. Replay is offline and read-only.

| Source | Input used here |
| --- | --- |
| [Sahlmann--Verch, math-ph/0008029v2](https://arxiv.org/pdf/math-ph/0008029v2) | Proposition 3.3: wave Cauchy existence/uniqueness and causal propagation for compact data. Theorems 5.5 and 5.8 discuss Hadamard propagation and wavefront characterization. Theorem 5.8 is stated for C-infinity-regular Weyl states; we instead assume the ordinary microlocal condition on the two-point distribution directly. The proof uses its distributional orientation/CCR argument, not extra higher-point regularity. |
| [Brunetti--Fredenhagen--Verch, math-ph/0112041v1](https://arxiv.org/pdf/math-ph/0112041v1) | Definition 2.1(iii) and Theorem 2.2: time-slice property for the free Klein--Gordon algebra. Used only to audit that extension is not a new positivity restriction; the written smooth-kernel proof is sufficient on its own. |
| [Fewster--Kontou, 1809.05047v2](https://arxiv.org/pdf/1809.05047v2) | Eqs. (23)--(31): common conserved stress prescription and EED. At `m=xi=0`, state differences of EED reduce to the timelike derivative square. Earlier A.2/A.3 contain the full operator and sign audit. |
| [Glavan--Prokopec--Prymidis, 1308.5954v1](https://arxiv.org/pdf/1308.5954v1) | Eqs. (40)--(41): radiation modes and reference stress. A.3 independently fixes the positive physical density, pressure, FK trace/EED and reference integration constant using this and Carlson--Anderson. A.4 imports only the pinned result, not an arbitrary-state conformal-stress identification. |

The arbitrary noncompact-data extension, the explicit evolution in both
bisolution variables, the state-dependent scaling estimate, and the resulting
SEE obstruction are the derivation in [proof.md](proof.md). They are not
presented as quoted theorems from these sources.

## Pinned dependency

`../certificates/radiation-reference.json` has SHA-256
`dc762112cdd2a5c0330f12d8bf157e27f5bae10d31cafa3b877cbce6eaa92b31`.

It is replayed before this report, recursively checking A.2 and A.1. It fixes
`E_ref=hbar/(5120*pi^2*t^4)=hbar/(320*pi^2*A^4*eta^8)`, the massless common
prescription, and the curvature/sign dictionary. Any change is a hard failure.

## Computational versus written evidence

The symbolic route differentiates the actual point-split observable and
polynomial Cauchy data. The independent route uses Python rational sparse
polynomials and coefficient/exponent algebra, without importing SymPy.
Outward Arb inequalities validate one explicitly bounded coherent-state
example; they do not bound every Hadamard state's data. The report pins
source, documentation and tests and rejects changed scope as well as changed
numbers. General smooth wave well-posedness, the Hadamard property and the
coherent-state construction remain written mathematical inputs, not claims
that a finite arithmetic check has formally proved quantum field theory.

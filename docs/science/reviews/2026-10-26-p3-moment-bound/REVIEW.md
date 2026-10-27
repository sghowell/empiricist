**Verdict: correct with gaps.** The universal inequality is mathematically sound under the stated dual-rail, fixed-photon-number, passive-interferometer model. I found no admissible counterexample. The gaps are short, repairable omissions in the written proof, plus an incorrectly quantified tightness example.

The closest prior result is Olivo–Grosshans (2018), discussed below. The plausible novelty is the extension to arbitrary interferometers, rather than the numerical form of the bound. Separately, one older P3 YAML conjecture is false as written.

I worked read-only. The four supplied moment-evidence payloads passed exact replay, as did the seven exact scheme witnesses and the older standard-assignment SOS. Twenty-one selected tests passed. No files were modified.

**The proof audit supports the theorem.** I checked the [five-step argument](/Users/seanhowell/dev/empiricist/.claude/worktrees/agent-a861422ee037fb029/docs/science/2026-10-26-p3-moment-bounds.md:53) as follows.

1. **Definitions and Step 1: correct; a minor mixed-state omission.**

   The appropriate definition is
   \[
   p_B=\sum_{n:f(n)=B}\Pr(n\mid B),\qquad
   p_{\rm avg}=\frac14\sum_Bp_B,
   \]
   with
   \[
   f(n)=B\Longrightarrow \Pr(n\mid B')=0\quad(B'\ne B).
   \]
   Failure is allowed, including failure on every input of some Bell label. Success is unconditional on the measurement’s accepted outcomes; it is not the fraction of Bell labels having any identifying pattern.

   This matches the equiprobable, unambiguous-discrimination convention in Calsamiglia–Lütkenhaus, Grice, and Ewert–van Loock. Their headline efficiencies concern the average, not generally the minimum over inputs. [Calsamiglia–Lütkenhaus](https://arxiv.org/pdf/quant-ph/0007058), [Grice](https://harvest.aps.org/v2/journals/articles/10.1103/PhysRevA.84.042331/fulltext), [Ewert–van Loock](https://arxiv.org/pdf/1403.4841).

   For a pure ancilla, the stated conclusion about \(G(n)=z(n)z(n)^\dagger\) follows immediately.

   The headline includes mixed ancillas, whereas the proof introduces a ket. The missing extension is straightforward. Write
   \[
   \rho_A=\sum_r w_r|A_r\rangle\langle A_r|,\qquad
   G_\rho(n)=\sum_r w_rz_r(n)z_r(n)^\dagger.
   \]
   A forbidden probability is a sum of nonnegative component probabilities. If it vanishes, each positive-weight component vanishes. Thus the same assignment is unambiguous for every component, and both the Gram-matrix proof and averaging argument apply.

   **Severity: minor exposition gap.** This argument already appears as W0′ in the \(k=1,m=6\) evidence; it should also appear in the general proof.

2. **Step 2: correct, including photon bunching.**

   Every complete output pattern satisfies
   \[
   \sum_i n_i=k+2.
   \]
   Consequently,
   \[
   \sum_i\operatorname{tr}\Lambda_i=(k+2)\sum_Bp_B.
   \]
   Here \(n_i\) is the occupation number, not an indicator that detector \(i\) clicked. A three-photon bunch contributes three. No collision-free assumption enters.

   Normalization is consistent: normalized inputs give \(\sum_n\operatorname{tr}G(n)=4\). The factor \(1/4\) belongs in the final average.

3. **Step 3: correct for arbitrary entangled or mixed ancillas; several minor explanations should be added.**

   Let \(R\) denote the ancilla modes and define
   \[
   \gamma_{j\ell}=\operatorname{tr}(\rho_Aa_j^\dagger a_\ell),\qquad
   d_i=\sum_{j\in R}U_{ij}a_j.
   \]
   The ancilla contribution is
   \[
   c_i=\sum_{j,\ell\in R}\overline{U_{ij}}U_{i\ell}\gamma_{j\ell}
       =\operatorname{tr}(\rho_A d_i^\dagger d_i)\ge0.
   \]
   **Ancilla–ancilla cross terms need not vanish.** Entangled or coherent ancillas can have \(\gamma_{j\ell}\ne0\) for \(j\ne\ell\). Those terms are retained inside \(c_i\); their action on the signal is proportional to the identity.

   There are two distinct vanishing arguments:

   - Signal–ancilla terms change the total signal photon number from two to one or three, so their matrix elements between signal Bell states vanish.
   - Terms transferring a photon between the two signal qubits change their rail-pair occupations from \((1,1)\) to \((2,0)\) or \((0,2)\). Their compressed matrix elements also vanish. Total signal photon number alone does **not** explain this second cancellation.

   Within one qubit’s rails, \(a_p^\dagger a_q\) compresses to \(|p\rangle\langle q|\). Its coefficient matrix is
   \[
   \overline u\,u^T=s_A|\alpha\rangle\langle\alpha|,
   \]
   explaining the conjugation in \(\alpha\). The resulting operator is exactly
   \[
   \widehat O_i=
   s_A|\alpha\rangle\langle\alpha|\otimes I+
   s_BI\otimes|\beta\rangle\langle\beta|+c_iI.
   \]

   **Minor gaps:** explicitly supply the inter-qubit rail argument; choose any unit \(\alpha\) when \(s_A=0\), and similarly for \(\beta\); interpret the note’s ancilla-only expectation with vacuum in the signal modes, or replace it with the \(d_i^\dagger d_i\) formula above.

4. **Step 4: the dual operator and inequality are correct. The tightness sentence needs a sign condition.**

   First, the transpose matters. If \(M_i\) is the usual Bell-basis matrix of \(\widehat O_i\), then \(D_i=M_i^T\). Since \(\Lambda_i\) is real diagonal,
   \[
   D_i-\Lambda_i\succeq0
   \Longrightarrow M_i-\Lambda_i\succeq0.
   \]
   This uses **full transposition**, which preserves positivity—not partial transposition. The checker’s documentation supplies this justification; the note compresses it too much.

   For
   \[
   Y=|\alpha^\perp\rangle\langle\alpha^\perp|\otimes I+
     I\otimes|\beta^\perp\rangle\langle\beta^\perp|,
   \]
   the Bell states’ reduced density matrices are \(I/2\), giving
   \[
   Y\succeq0,\quad \langle B|Y|B\rangle=1,\quad
   \operatorname{tr}Y=4.
   \]
   Direct calculation gives
   \[
   \operatorname{tr}(Y\widehat O)=s_A+s_B+4c.
   \]
   Therefore
   \[
   \operatorname{tr}\Lambda
   =\operatorname{tr}(Y\Lambda)
   \le\operatorname{tr}(Y\widehat O).
   \]
   No commutativity assumption is needed: the trace of a product of two positive semidefinite matrices is nonnegative. The lemma genuinely holds for arbitrary real \(s_A,s_B,c,\lambda_B\).

   The SOS encoding is consistent with this argument. Its \(WW^\dagger\) hypothesis covers every positive semidefinite slack matrix.

   **Minor error:** the [tightness example](/Users/seanhowell/dev/empiricist/.claude/worktrees/agent-a861422ee037fb029/docs/science/2026-10-26-p3-moment-bounds.md:88) requires \(s\ge0\). For its proposed \(\Lambda\),
   \[
   \widehat O-\Lambda=2s|00\rangle\langle00|.
   \]
   This is not positive semidefinite when \(s<0\). If \(\Lambda\) must itself represent nonnegative success weights, \(c\ge0\) also suffices with \(s\ge0\). The lemma and its YAML statement do not contain this erroneous attainment claim.

5. **Step 5: correct, without a product-ancilla assumption.**

   Unitarity gives
   \[
   \sum_i s_A(i)=2,\qquad \sum_i s_B(i)=2,
   \]
   and, retaining every ancilla coherence,
   \[
   \sum_i c_i
   =\sum_{j,\ell\in R}\gamma_{j\ell}
      \sum_i\overline{U_{ij}}U_{i\ell}
   =\sum_{j\in R}\gamma_{jj}
   =\operatorname{tr}(\rho_A N_R)=k.
   \]
   Thus
   \[
   4(k+2)p_{\rm avg}\le4+4k,
   \qquad
   p_{\rm avg}\le\frac{k+1}{k+2}.
   \]
   Taking the minimum over Bell inputs can only decrease success.

The assumptions should be stated explicitly in a publication: normalized Bell states with one photon in each disjoint rail pair; a normalized, Bell-label-independent ancilla on disjoint modes; bosonic Fock-space evolution; one fixed passive \(U\); and complete photon counting. Polarization, path, and other resolved degrees of freedom may be mode labels, and \(U\) need not preserve polarization. Extra hyperentanglement of the two signal photons is a different input resource. Adaptive networks with outcome-dependent interferometers are not covered by this proof. Independently randomizing among admissible schemes still obeys the average upper bound.

The permanent normalization in the supplied small-instance checker is correct: its amplitude scale is \(1/(2\prod_i n_i!)\), including bunched patterns. I found no missing factorial or conjugation error.

**All four requested consequences follow, with the following qualifications.**

| Consequence | Assessment |
|---|---|
| \(p^*_{\rm avg}(2)=3/4\) | Correct: combine the universal upper bound with the two-photon Grice construction. No monotonicity assumption is needed. |
| \(1-p^*(k)\ge1/(k+2)\), both metrics | Correct. The bound is uniform over modes, ancillas, and assignments, so it survives taking the supremum. |
| \(1-p^*_{\rm avg}(k)=\Theta(1/k)\) | Correct, using idle-photon padding and unrestricted mode number. The note omits this short argument. |
| \(p_{\rm avg}\le2/3\) at \(k=1\) | Correct for every admissible mode number and ancilla. It does not establish optimality or prove that one photon is useless. |

For the asymptotic statement, an exactly-\(j\)-photon scheme can be embedded in an exactly-\(k\)-photon scheme, \(k\ge j\), by adding \(k-j\) photons in untouched auxiliary modes and extending \(U\) by the identity. Their deterministic detector record is ignored. Hence the optimum is nondecreasing in \(k\).

Choose \(N=\lfloor\log_2(k+2)\rfloor\) and pad the Grice scheme with \(j=2^N-2\). Then
\[
\frac1{k+2}
\le1-p^*_{\rm avg}(k)
\le2^{-N}
<\frac2{k+2}.
\]
This establishes the all-\(k\) conclusion, rather than only a subsequence result. **Severity of the omission: minor.**

The note correctly distinguishes the minimum metric at \(k=2\): the checked Grice witness has success vector \((1/2,1/2,1,1)\), so it supplies minimum \(1/2\). Randomly choosing between complementary analyzers balances the vector to \(3/4\), but that construction alone does not establish a single fixed-\(U\) realization under P3’s definition.

**The five primary claim files are appropriately scoped, subject to the disclosed boundary between exact checking and written mathematics.**

| Claim | Evidence assessment |
|---|---|
| [One-body lemma](/Users/seanhowell/dev/empiricist/.claude/worktrees/agent-a861422ee037fb029/claims/P3.one_body_usd_lemma.yaml:46) | Supported. Exact rational SOS identity and positive-semidefinite Gram matrix passed. The statement matches the encoded hypothesis and objective. |
| [\(k=0,m=4\)](/Users/seanhowell/dev/empiricist/.claude/worktrees/agent-a861422ee037fb029/claims/P3.k0_m4_p_avg_upper_bound.yaml:60) | Supported by the exact identities plus the disclosed assignment/counting reduction. It does not claim arbitrary \(m\). |
| [\(k=1,m=5\)](/Users/seanhowell/dev/empiricist/.claude/worktrees/agent-a861422ee037fb029/claims/P3.k1_m5_p_avg_upper_bound.yaml:60) | Supported, with the single ancilla photon in the sole ancilla input mode. |
| [\(k=1,m=6\)](/Users/seanhowell/dev/empiricist/.claude/worktrees/agent-a861422ee037fb029/claims/P3.k1_m6_p_avg_upper_bound.yaml:59) | Supported. Ancilla rotation handles pure single-photon states; W0′ correctly handles mixtures. A single rotation need not diagonalize or purify the mixture. |
| [General \(k,m\)](/Users/seanhowell/dev/empiricist/.claude/worktrees/agent-a861422ee037fb029/claims/P3.moment_bound_general_k.yaml:19) | Correctly remains HEURISTIC with no general machine certificate. The finite instances do not certify its universal quantifiers. Its standalone text should explicitly specify the dual-rail input and normalized independent ancilla. |

The instance replays checked respectively 64, 80, and 96 output-mode/ordered-Bell-pair cases, each against two complex polynomial identities. The certificates establish exact algebraic identities; the physical interpretation, transpose, PSD reduction, ancilla rotation, and mixed-state extension are partly written arguments. The evidence files disclose this honestly. Numerical tests of the semantic encoding are useful checks, but are not themselves universal proofs.

I also checked the broader set of 31 `P3.*.yaml` files. The seven exact witness probability vectors replayed correctly. The older standard-assignment SOS remains limited to that assignment objective. The 15 FORMALIZED statement scopes match their attached Lean theorem declarations; I did not perform a fresh Lean build. The superseded `True` claim does not provide a substantive theorem.

Two older claim texts need attention:

- **High severity—false unrestricted conjecture.** [“\(k=0\) forces \(\min_Bp_B=0\)”](/Users/seanhowell/dev/empiricist/.claude/worktrees/agent-a861422ee037fb029/claims/P3.Conjecture_Fable_search_sketch_k_0_forces_min_B_p_B_0.yaml:27) omits the **four-mode** restriction of its evidence.

  A static eight-mode counterexample uses only vacuum auxiliary inputs. Let
  \[
  H=\frac1{\sqrt2}
  \begin{pmatrix}
  1&0&1&0\\
  0&1&0&1\\
  1&0&-1&0\\
  0&1&0&-1
  \end{pmatrix},
  \qquad
  V=\frac1{\sqrt2}\begin{pmatrix}H\\HX_A\end{pmatrix},
  \]
  where \(X_A\) swaps the first qubit’s two input rails. Since \(V^\dagger V=I\), it extends to an eight-mode unitary. Accept the standard identifying patterns within either four-mode output branch and reject cross-branch patterns. The branches identify complementary Bell pairs. Exact evaluation gives
  \[
  (p_{\Phi^+},p_{\Phi^-},p_{\Psi^+},p_{\Psi^-})
  =(1/4,1/4,1/4,1/4).
  \]
  This refutes the unrestricted YAML conjecture, while respecting the new average bound.

- **Medium severity—ambiguous scope.** The [twirling/fixed-mesh claim](/Users/seanhowell/dev/empiricist/.claude/worktrees/agent-a861422ee037fb029/claims/P3.k_2_floor_twirl_achieves_min_3_4_verified_fixed-mesh_1_2_con.yaml:27) should explicitly identify its classical randomization and eight-mode setting. Its evidence does not prove a universal fixed-interferometer minimum bound of \(1/2\), nor does the twirl prove the fixed-\(U\) minimum optimum is \(3/4\).

There are also **medium-severity background issues** in the [original P3 statement](/Users/seanhowell/dev/empiricist/.claude/worktrees/agent-a861422ee037fb029/docs/open_problems_ftfbqc.md:100): several quoted average-success results are presented as results for its minimum metric. Their citations do not justify that substitution. Furthermore, “no perfect scheme exists” alone does not imply that a supremum over arbitrarily many modes is strictly below one. The new uniform bound supplies that missing conclusion.

**The literature search found a close restricted predecessor, but no earlier unrestricted theorem or valid counterexample.** The following references give the relevant statements and distinctions.

- **Andrea Olivo and Frédéric Grosshans**, “Ancilla-assisted linear optical Bell measurements and their optimality,” *Physical Review A* **98**, 042323 (2018), DOI **10.1103/PhysRevA.98.042323**. Section II.B, Eq. (4), proves
  \[
  P_{\rm fail}\ge\frac1{\lceil k+1\rceil_{\rm even}}
  =
  \begin{cases}
  1/(k+2),&k\text{ even},\\
  1/(k+1),&k\text{ odd}.
  \end{cases}
  \]
  Their analytic proof assumes \(U=\operatorname{diag}(U_H,U_V)\): polarization-preserving interferometers. Thus it equals the proposed bound for even \(k\), is stronger for odd \(k\), and implies the proposed inequality **within that restricted class**. It does not establish the arbitrary-\(U\) theorem. Their generic-interferometer optimization is numerical. [Paper, including the explicit restriction](https://arxiv.org/pdf/1806.01243).

- **John Calsamiglia and Norbert Lütkenhaus**, “Maximum efficiency of a linear-optical Bell-state analyzer,” *Applied Physics B* **72**, 67–71 (2001), DOI **10.1007/s003400000484**. Proves equiprobable USD success at most \(1/2\) with passive fixed linear optics and arbitrarily many vacuum auxiliary modes. This subsumes the new theorem’s entire \(k=0\) case, not just four modes, and already allows arbitrary assignments. [Paper](https://arxiv.org/pdf/quant-ph/0007058).

- **Norbert Lütkenhaus, John Calsamiglia, and Kalle-Antti Suominen**, “Bell measurements for teleportation,” *Physical Review A* **59**, 3295–3300 (1999), DOI **10.1103/PhysRevA.59.3295**. Establishes impossibility of a never-failing analyzer even with auxiliary bosons and conditional dynamics. It does not give the quantitative, mode-uniform \(k\)-dependent gap asserted here. [Paper](https://arxiv.org/pdf/quant-ph/9809063).

- **Lev Vaidman and Nadav Yoran**, “Methods for reliable teleportation,” *Physical Review A* **59**, 116–125 (1999), DOI **10.1103/PhysRevA.59.116**. Gives an earlier impossibility result for deterministic teleportation/Bell analysis with the noninteracting optical methods considered. It supplies no equivalent ancilla-photon resource curve. [Paper](https://arxiv.org/abs/quant-ph/9808040).

- **Angelo Carollo and G. Massimo Palma**, “The role of auxiliary photons in state discrimination with linear optical devices,” *Journal of Modern Optics* **49**, 1147–1155 (2002), DOI **10.1080/09500340110098370**. Its relevant theorem concerns **complete exact distinguishability**, requiring orthogonality of conditional states for every possible count. It does not say that ancillary photons cannot improve probabilistic USD efficiency, and does not imply the proposed quantitative bound. [Paper](https://arxiv.org/pdf/quant-ph/0106041).

- **Peter van Loock and Norbert Lütkenhaus**, “Simple criteria for projective measurements with linear optics,” *Physical Review A* **69**, 012302 (2004), DOI **10.1103/PhysRevA.69.012302**. Derives a hierarchy of photon-number moment conditions for exact discrimination, including first moments. This is relevant methodological prior art, but supplies no equivalent success-probability inequality in \(k\). [Paper](https://arxiv.org/pdf/quant-ph/0304057).

- **W. P. Grice**, “Arbitrarily complete Bell-state measurement using only linear optical elements,” *Physical Review A* **84**, 042331 (2011), DOI **10.1103/PhysRevA.84.042331**. Constructs success \(1-2^{-N}\) using \(2^N-2\) ancillary photons, including \(3/4\) with two photons. These are achievable values, not upper bounds; they saturate the proposed theorem along that family. [Paper](https://harvest.aps.org/v2/journals/articles/10.1103/PhysRevA.84.042331/fulltext).

- **Fabian Ewert and Peter van Loock**, “3/4-efficient Bell measurement with passive linear optics and unentangled ancillae,” *Physical Review Letters* **113**, 140403 (2014), DOI **10.1103/PhysRevLett.113.140403**. Achieves \(3/4\) using four unentangled single-photon ancillas and develops extensions. Four photons, rather than two, must be counted for that construction. It does not violate or universally prove the proposed bound. [Paper](https://arxiv.org/pdf/1403.4841).

- **Stephen Wein, Khabat Heshami, Christopher A. Fuchs, Hari Krovi, Zachary Dutton, Wolfgang Tittel, and Christoph Simon**, “Efficiency of an enhanced linear optical Bell-state measurement scheme with realistic imperfections,” *Physical Review A* **94**, 032332 (2016), DOI **10.1103/PhysRevA.94.032332**. Analyzes standard and \(75\%\)-efficient enhanced analyzers with loss, dark counts, and detector limitations. Its bounds concern implementation performance and detector requirements, not a universal ancilla-photon optimum. [Paper](https://arxiv.org/abs/1509.00088).

- **Sara Bartolucci, Patrick M. Birchall, Mercedes Gimeno-Segovia, Eric Johnston, Konrad Kieling, Mihir Pant, Terry Rudolph, Jake Smith, Chris Sparrow, and Mihai D. Vidrighin**, “Creation of Entangled Photonic States Using Linear Optics,” **arXiv:2106.13825** (2021). Gives Type-II fusion success \(7/12\) with one auxiliary photon and \(2/3\) with two, allowing projections onto possibly nonorthogonal maximally entangled states. That fusion task differs from identifying a fixed orthogonal Bell alphabet. Neither value exceeds the present bound. [Paper, Section VII](https://arxiv.org/pdf/2106.13825).

- **Sara Bartolucci, Patrick Birchall, Hector Bombín, Hugo Cable, Chris Dawson, Mercedes Gimeno-Segovia, Eric Johnston, Konrad Kieling, Naomi Nickerson, Mihir Pant, Fernando Pastawski, Terry Rudolph, and Chris Sparrow**, “Fusion-based quantum computation,” *Nature Communications* **14**, 912 (2023), DOI **10.1038/s41467-023-36493-1**. Develops the architecture and fault-tolerance analysis using fusion measurements; it does not establish the unrestricted photon-resource bound. [Paper](https://www.nature.com/articles/s41467-023-36493-1).

- **Matthias J. Bayerbach, Simone E. D’Aurelio, Peter van Loock, and Stefanie Barz**, “Bell-state measurement exceeding 50% success probability with linear optics,” *Science Advances* **9**, eadf4080 (2023), DOI **10.1126/sciadv.adf4080**. Its two-ancilla-photon implementation has ideal success \(5/8\), with measured success \(57.9\%\). It is compatible with the \(k=2\) ceiling \(3/4\); it gives no universal upper bound. [Paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12488041/).

- **Tomohiro Yamazaki, Rikizo Ikuta, and Takashi Yamamoto**, “Stabilizer formalism in linear optics and application to Bell-state discrimination,” **arXiv:2301.06551** (2023). The analyzed construction reaches \(403/512\) at 28 ancilla photons. This is a construction-specific maximum, below \(29/30\), and is explicitly distinguished from its asymptotically maximally entangling measurement behavior. [Paper](https://arxiv.org/abs/2301.06551).

- **Paul Hilaire, Yaron Castor, Edwin Barnes, Sophia E. Economou, and Frédéric Grosshans**, “Linear Optical Logical Bell State Measurements with Optimal Loss-Tolerance Threshold,” *PRX Quantum* **4**, 040322 (2023), DOI **10.1103/PRXQuantum.4.040322**. Its bounds concern loss tolerance of encoded logical measurements, rather than fixed-\(k\) assistance to two unencoded dual-rail photons. It neither subsumes nor contradicts this theorem. [Paper](https://arxiv.org/abs/2302.07908).

- **Nico Hauser, Matthias J. Bayerbach, Simone E. D’Aurelio, Raphael Weber, Matteo Santandrea, Shreya P. Kumar, Ish Dhand, and Stefanie Barz**, “Boosted Bell-state measurements for photonic quantum computation,” *npj Quantum Information* **11**, 41 (2025), DOI **10.1038/s41534-025-00986-2**. Demonstrates the ancillary-pair approach with measured \(69.3\%\), targeting ideal \(75\%\). This is consistent with the bound. [Paper](https://arxiv.org/abs/2410.16380).

- **Simone E. D’Aurelio, Matthias J. Bayerbach, and Stefanie Barz**, “Boosted quantum teleportation,” *npj Quantum Information* **11**, 37 (2025), DOI **10.1038/s41534-025-00992-4**. Demonstrates boosted teleportation with approximately \(69.71\%\) acceptance. This is an application of an enhanced analyzer, not a competing resource upper bound. [Paper](https://arxiv.org/abs/2406.05182).

- **Anand Kumar, Wojciech Roga, Devendra Kumar Mishra, and Masahiro Takeoka**, “Symmetry-resolved tree tensor network analysis of Bell-state discrimination with ancilla-assisted passive linear optics,” **arXiv:2609.07319** (2026). Evaluates recursively structured analyzers and resource families up to 32 modes. Its discussion explicitly excludes global optimality over interferometers and ancillary resources. It does not preempt the claimed universal result. [Paper, discussion](https://arxiv.org/html/2609.07319v1).

I also examined apparent exceptions rather than treating their advertised efficiencies as directly comparable:

- **Hussain A. Zaidi and Peter van Loock**, “Beating the One-Half Limit of Ancilla-Free Linear Optics Bell Measurements,” *Physical Review Letters* **110**, 260501 (2013), DOI **10.1103/PhysRevLett.110.260501**. The \(64.3\%\) dual-rail result uses **active squeezing**, outside passive \(U(m)\). [Paper](https://arxiv.org/abs/1301.2749).

- **Jake A. Smith and Lev Kaplan**, “Approaching near-perfect state discrimination of photonic Bell states through the use of unentangled ancilla photons,” **arXiv:1802.10527** (2018). The optimization maximizes mutual information, permitting ambiguous outcomes. Its extrapolation toward near-perfect discrimination is not an exhibited USD scheme beating this bound. [Paper, Sections IV–V](https://arxiv.org/pdf/1802.10527).

- **Jatin Ghai and Sibasish Ghosh**, “Linear optics and the problem of Bell-like state discrimination,” **arXiv:2402.00832v1** (2024). The abstract describes \(1-2^{-N}\) while calling \(N\) the ancillary-photon count. That resource statement is inconsistent with the cited Grice construction: Section VI starts with two ancilla photons and adds another four at the next stage. It is not a demonstrated exponential-in-photon-count counterexample. [Paper](https://arxiv.org/html/2402.00832v1).

- **Zhanjie Gao, Zengping Su, Qinghua Song, Patrice Genevet, and Konstantin E. Dorfman**, “Metasurface for complete measurement of polarization Bell state,” *Nanophotonics* **12**, 569–577 (2023), DOI **10.1515/nanoph-2022-0593**. Its advertised \(75\%\)/complete measurement does not establish single-copy USD under the present definition. For example, substituting its first proposed polarizer setting into its Eq. (14) gives a detector amplitude proportional to \(\langle\Psi_2|+\langle\Psi_4|\): that outcome is ambiguous. Combining information from different settings does not repair single-pattern unambiguity. This is my direct check of its displayed equations. [Paper, Eqs. (13)–(15)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11501330/).

- **Pradip Laha and Peter van Loock**, “Auxiliary Schmidt Rank as a Resource for Photonic Bell Measurements,” **arXiv:2606.24591v2** (2026). Studies extra entanglement in degrees of freedom carried by the **same two photons**. Its deterministic-discrimination resource threshold concerns auxiliary Schmidt rank, not independent ancillary photons on disjoint modes. It is outside the input model here. [Paper](https://arxiv.org/abs/2606.24591).

**My novelty assessment is provisional but positive for the unrestricted theorem.** The search through 26 October 2026 found no earlier proof covering arbitrary \(U(m)\) and arbitrary fixed-\(k\) ancillary states. The defensible contribution is removing the interferometer restriction from the resource bound and establishing unrestricted optimality of the matching constructions. The note’s “first bound below 1 at \(k=1\)” is **a medium-severity priority overstatement unless qualified** as a uniform quantitative bound for unrestricted interferometers. The formula itself and restricted-class bounds have clear prior art; a negative literature search cannot guarantee priority.
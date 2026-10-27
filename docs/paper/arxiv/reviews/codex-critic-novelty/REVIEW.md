**Novelty verdict.** I found no earlier explicit statement of either exact theorem in the paper’s model: three-qubit GHZ resources, destructive two-qubit Bell measurements, and free single-qubit Cliffords. The qualified statement “We have not found … stated in the literature” is defensible as of **26 October 2026**.

The characterization has modest mathematical novelty: it makes an accessible consequence of existing results explicit in a particular resource model. The statement “Both directions can be assembled from published results” is accurate and appropriately candid. The general bound \(F(G)\ge n+3\,\mathrm{rw}(G)-6\) appears to be the more substantial new statement.

There is **no blocking priority conflict identified**. There are several attribution and bibliography corrections, including one substantive overstatement of an algorithmic result. I worked read-only and changed no files.

**Closest previous work**

| Work | Relevant previous result | Relation to this paper |
|---|---|---|
| [Kumabe–Mori–Yoshimura, Theorem 7 and Corollary 5](https://arxiv.org/html/2402.05874v4) | For connected graphs, two-qubit Clifford preparation complexity is at least \(n+\mathrm{rw}(G)-2\), and equals \(n-1\) at rank-width one. Together these imply an optimal-cost iff characterization by distance-hereditary graphs. | The closest structural analogue of **both** results. Their resources are initially unentangled qubits; their model permits ancillas and computational-basis measurements. It does not count GHZ₃ fusions. |
| [Löbl et al., §IV.3, Eq. (2), Appendix A](https://arxiv.org/html/2412.04587v3) | In the single-emitter model, \(f_{\min}\ge\mathrm{lrw}(G)-1\); the zero-fusion connected class consists of graphs locally equivalent to caterpillars. | A previous width-dependent **fusion-count lower bound** already exists. Since \(\mathrm{rw}\le\mathrm{lrw}\), it also implies a weaker rank-width bound in that model. Caterpillar resources are supplied without fusion cost, unlike GHZ₃ resources here. |
| [Connolly et al., Proposition 1 and §4](https://arxiv.org/html/2603.23892v2), combined with [Lee–Jeong, §2.2](https://arxiv.org/html/2304.11988v4) | Assemble distance-hereditary graph states by type-II fusions of split-decomposition stars/cliques; construct an \(m\)-vertex star from \(m-2\) GHZ₃ states. | Directly supplies the constructive half after resource accounting. Connolly et al. primarily analyze gate, depth, and auxiliary-qubit costs; they do not state the exact GHZ₃ minimum-fusion characterization. |
| [Bandelt–Mulder](https://www.sciencedirect.com/science/article/pii/0095895686900432), combined with the [Zaidi et al. fusion rule](https://arxiv.org/pdf/1410.3753) | Distance-hereditary graphs admit pendant/twin constructions; the fusion rule realizes those additions using GHZ₃ resources. | The constructive implication can be assembled from substantially older ingredients. Its availability does not begin with Connolly’s 2026 preprint. |
| [Van den Nest et al. 2007, Eqs. (7)–(8) and Theorem 3](https://arxiv.org/pdf/quant-ph/0608060) | Graph-state Schmidt-rank width equals rank-width; optimal tree tensor networks reflect these cut ranks. | Supplies the entanglement ingredient for the necessity direction. It does not itself state a fusion-count theorem. |
| [Sharma et al., §4 and Appendix D](https://arxiv.org/html/2506.00292v2) | Edge minimization is applied to reducing GHZ₃ resources and fusions for generalized repeater graph states. | Closer to the paper’s resource model than the current “other models” paragraph suggests, but not a general DH characterization or rank-width fusion bound. |
| [Adcock et al., *Hard limits on postselectability of optical graph states*](https://arxiv.org/abs/1806.03263) | Studies attainability from optical resources, including Bell pairs, under postselected gates and fusion, with tree-related constructions and small-state classifications. | Relevant nearby Bell-pair literature. Its operations and postselection constraints differ; it does not state either GHZ₃ theorem. |

The assembly claim can be made quite concrete. For sufficiency, let the split decomposition have \(q\) bags of sizes \(m_i\), including marker vertices. Then
\[
\sum_i m_i=n+2(q-1).
\]
Preparing the bags as stars and joining them costs
\[
\sum_i(m_i-3)+(q-1)=n-3
\]
fusions and \(\sum_i(m_i-2)=n-2\) GHZ₃ resources. This is my accounting of the cited constructions, rather than a formula explicitly asserted by Connolly et al.

For necessity, equality in the elementary counting bound forces a tree of GHZ₃ resources. Its tensor network has bond dimension two, hence Schmidt-rank width at most one; the graph-state width identity and Oum’s characterization give distance-heredity. The counting/tree-network step is needed: equality of the two width notions alone does not establish the implication.

A fair novelty formulation would therefore be:

> We make explicit the GHZ₃ minimum-fusion characterization obtainable from existing entanglement-width and graph-decomposition results, and prove the more general cycle-rank lower bound. We have not located either exact statement in this resource and operation model. Width-dependent fusion bounds were previously known for emitter-generated caterpillar resources.

**Numbered findings**

1. **Major — The transformation-complexity summary omits essential restrictions.**  
   **Location:** [main.tex:476](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:476), through line 478.

   “Transformation problems … under local operations, efficient at bounded rank-width and hard in general” is too broad. For arbitrary target graph states, the cited general algorithm requires bounded **source rank-width and target size**. The operations are single-qubit Cliffords, single-qubit Pauli measurements, and classical communication. Special targets, including GHZ states, admit stronger statements. The counting paper concerns orbit cardinality, not a transformation-decision problem.

   **Evidence:** [Dahlberg–Wehner 2018, abstract and Theorem 1.1](https://arxiv.org/pdf/1805.05305): “whenever the rank-width of G and the size of G′ are bounded.” The separate [counting paper](https://arxiv.org/abs/1907.08024) establishes that “counting the number of graph states” in an LC orbit is #P-complete.

   **Fix:** Replace the sentence with a precise distinction:
   > Under single-qubit Clifford operations and Pauli measurements, graph-state transformation is NP-complete in general. It is fixed-parameter tractable in source rank-width and target size, with stronger algorithms for particular target families. Counting LC-equivalent graph states is #P-complete.

   Add `Dahlberg2018transforming`, which is already in `refs.bib` but currently uncited.

2. **Minor — Löbl’s bound needs the subtraction by one.**  
   **Locations:** [main.tex:101](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:101) and [main.tex:455](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:455).

   “Bound the count below by the linear rank-width” can be read as \(f_{\min}\ge\mathrm{lrw}\). Their actual bound is \(f_{\min}\ge\mathrm{lrw}-1\). A connected caterpillar already demonstrates the distinction: linear rank-width one, zero fusions.

   **Evidence:** [§IV.3, Eq. (2)](https://arxiv.org/html/2412.04587v3): “\(n_f^{\min}(G)+1\ge n_s^{\min}(G)\),” with \(n_s^{\min}\) identified immediately beforehand as linear rank-width.

   **Fix:** Write the formula explicitly in both places. The claims about the eight-qubit tablebase and caterpillar zero-fusion class are correct.

3. **Minor — Connolly–Nishio–Nemoto count orbit sizes, not the number of orbits.**  
   **Location:** [main.tex:472](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:472).

   “Count the local-equivalence classes of families” suggests counting distinct equivalence classes. The paper derives sizes of individual equivalence classes for specified graph families.

   **Evidence:** [Their abstract](https://arxiv.org/abs/2602.23825): “determining the size of the resulting equivalence classes.”

   **Fix:** Replace with:
   > derive formulas for the sizes of local-equivalence classes of several families of distance-hereditary graphs.

4. **Minor — Davies–Jena’s general forbidden-vertex-minor result is conditional.**  
   **Location:** [main.tex:465](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:465).

   The existing broad description is not an explicit false formula, but it conceals a significant qualification. Their general \(O(n\log n)\) result for proper vertex-minor-closed classes assumes Geelen’s Weak Structural Conjecture. Their results for circle graphs and bounded-rank-width graphs are unconditional.

   **Evidence:** [Theorems 1.1 and 5.2](https://arxiv.org/html/2504.00291v2) begin: “Conjecture 5.1 implies the following.”

   **Fix:** Say:
   > Davies and Jena give unconditional preparation bounds for circle graphs and bounded-rank-width graphs, and a conditional \(O(n\log n)\) bound for general proper vertex-minor-closed classes.

5. **Minor — The GHZ₃ motivation overgeneralizes the cited photonic architectures.**  
   **Location:** [main.tex:63](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:63).

   GHZ₃ is an established resource, but calling it “the basic resource of photonic proposals” while citing Bartolucci et al. is overly sweeping. That paper’s principal examples use four-qubit GHZ and six-qubit ring resources.

   **Evidence:** [Bartolucci et al., §VI.A](https://arxiv.org/pdf/2101.09310): “The resource state is the four qubit Greenberger-Horne-Zeilinger (GHZ) state.” Section VI.B uses six-qubit rings.

   **Fix:** Use “a basic resource in several photonic proposals,” citing Gimeno-Segovia et al. and, optionally, Zaidi et al. Keep Bartolucci et al. attached to the general FBQC description.

6. **Minor — `Connolly2026local` has an outdated publication record and incorrect primary arXiv category.**  
   **Location:** [refs.bib:266](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/refs.bib:266).

   The arXiv identifier, authors, and title are correct. A journal publication is now recorded, and the primary category is `math.CO`, not `quant-ph`.

   **Evidence:** The publisher-deposited Crossref record displayed in [Quantum’s cited-by list](https://quantum-journal.org/papers/q-2026-07-18-2165/) gives “Journal of Physics A: Mathematical and Theoretical 59 39, 395310 (2026).” The [arXiv page](https://arxiv.org/abs/2602.23825) identifies “Combinatorics (math.CO).”

   **Fix:** Update to an article with:
   - *Journal of Physics A: Mathematical and Theoretical* **59**(39), **395310** (2026);
   - DOI [10.1088/1751-8121/aea45d](https://doi.org/10.1088/1751-8121/aea45d);
   - retain arXiv:2602.23825 and set `primaryClass = {math.CO}`.

   The direct IOP page was inaccessible during this review; the journal metadata was checked through the Crossref record displayed by Quantum and corroborating publisher citation metadata.

7. **Minor — Hein et al. 2006 has recoverable published chapter metadata.**  
   **Location:** [refs.bib:334](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/refs.bib:334).

   The existing arXiv citation is valid, but the bibliography comment saying volume/pages were unverified can now be resolved.

   **Evidence:** The [institutional publication record](https://research.uni-hannover.de/de/publications/entanglement-in-graph-states-and-its-applications/) records “Seiten 115-218” and “Band 162.”

   **Fix:** Cite the chapter in *Quantum Computers, Algorithms and Chaos*, Proceedings of the International School of Physics “Enrico Fermi,” **162**, pp. **115–218**, IOS Press (2006), DOI [10.3254/978-1-61499-018-5-115](https://doi.org/10.3254/978-1-61499-018-5-115). Retain quant-ph/0602096.

8. **Nit — The Lean citation omits the LNCS volume.**  
   **Location:** [refs.bib:615](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/refs.bib:615).

   Authors, title, conference, pages, year, and DOI are correct.

   **Evidence:** [Springer’s chapter page](https://link.springer.com/chapter/10.1007/978-3-030-79876-5_37) explicitly gives “volume 12699.”

   **Fix:** Add `volume = {12699}`.

9. **Nit — The displayed local-complementation identity needs a global-phase qualification.**  
   **Location:** [main.tex:149](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:149), Eq. `lc`.

   The operator and signs are correct as an implementation on quantum states. With the exact vector normalization introduced immediately above, the equality holds only up to global phase.

   **Evidence:** [Van den Nest–Dehaene–De Moor, §II.A](https://arxiv.org/pdf/quant-ph/0308151) explicitly treats stabilizer vectors “up to an arbitrary phase.” The corresponding unitary also appears in [Hein et al., Proposition 8](https://arxiv.org/pdf/quant-ph/0307130).

   **Fix:** State that the equation holds up to global phase. If literal vector equality is desired, direct evaluation with your convention gives
   \[
   U_v|G\rangle=e^{i\pi(\deg(v)-1)/4}|\tau_v(G)\rangle,
   \]
   so multiply the present right-hand side by \(e^{i\pi(1-\deg(v))/4}\).

**Complete citation and bibliography audit**

I identified **42 distinct bibliography entries cited by `main.tex`**. The following tables account for all of them. Except for the corrections and retrieval limitations identified here, the author lists, titles, publication fields, and DOI/arXiv pairings agree with the primary records checked. Initials versus expanded names and title capitalization are not errors.

“Supported” below concerns what the cited work establishes; it does not certify the manuscript’s computational artifacts.

| Cited entry | Claim check | Publication and identifier check |
|---|---|---|
| `Bartolucci2023fusion` | General FBQC description supported; GHZ₃ wording needs finding 5. | *Nature Communications* **14**, 912 (2023); [DOI](https://doi.org/10.1038/s41467-023-36493-1); [arXiv:2101.09310](https://arxiv.org/abs/2101.09310). |
| `GimenoSegovia2015three` | GHZ₃ resources for ballistic photonic computation supported. Four-author list correct. | *PRL* **115**(2), 020502 (2015); [DOI](https://doi.org/10.1103/PhysRevLett.115.020502); [arXiv:1410.3720](https://arxiv.org/abs/1410.3720). |
| `Browne2005resource` | Type-II fusion and probabilistic optical implementation supported. The manuscript appropriately specifies its Bell-basis convention separately. | *PRL* **95**(1), 010501 (2005); [DOI](https://doi.org/10.1103/PhysRevLett.95.010501); [quant-ph/0405157](https://arxiv.org/abs/quant-ph/0405157). |
| `Zaidi2015near` | The neighbor-joining rule is supported by Fig. 1 and the appendix, with the appropriate local basis change. | *PRA* **91**(4), 042301 (2015); [DOI](https://doi.org/10.1103/PhysRevA.91.042301); [arXiv:1410.3753](https://arxiv.org/abs/1410.3753). |
| `Lee2023graph` | Heuristics, \(X\otimes Z,Z\otimes X\) convention, fusion graph rule, and Pauli outcome corrections supported. §2.2 gives the star construction; its \(m-3\) fusion count and optimality follow by elementary counting. | *Quantum* **7**, 1212 (2023); [DOI](https://doi.org/10.22331/q-2023-12-20-1212); [arXiv:2304.11988](https://arxiv.org/abs/2304.11988). |
| `Lobl2025transforming` | §3.1 supports the stated Bell convention and disjoint-graph rule; the paper also treats more general adjacency/neighborhood cases. Four authors correct. | *Quantum* **9**, 1795 (2025); [DOI](https://doi.org/10.22331/q-2025-07-14-1795); [arXiv:2405.02414](https://arxiv.org/abs/2405.02414). |
| `Lobl2025generating` | Eight-qubit completeness, dynamic programming, and caterpillar class supported; bound needs finding 2. “Tablebase” is used there, explicitly borrowed from chess terminology. | *PRA* **111**(5), 052604 (2025); [DOI](https://doi.org/10.1103/PhysRevA.111.052604); [arXiv:2412.04587](https://arxiv.org/abs/2412.04587). Six authors, including Jena and Dellantonio, correct. |
| `Kumabe2026complexity` | Both quoted formulas correct. Their “two-qubit Clifford” formulation genuinely has the stated CZ-cost equivalence; this is not merely a CZ-only theorem being overgeneralized. | *Quantum* **10**, 2165 (2026); [DOI](https://doi.org/10.22331/q-2026-07-18-2165); [arXiv:2402.05874](https://arxiv.org/abs/2402.05874). |
| `Connolly2026efficient` | Proposition 1 and §4 support split-fuse construction of every DH graph state. | [arXiv:2603.23892](https://arxiv.org/abs/2603.23892), 2026; arXiv DOI correct. The PDF/HTML byline confirms **William John Munro** as in the bibliography. |
| `Connolly2026local` | Orbit-size results supported; wording needs finding 3. | Authors/title/arXiv identifier correct; journal/category update in finding 6. |
| `Staudacher2026adaptive` | Linear-cluster resources, adaptive protocols, and fusion failures supported. Their cost analysis includes stochastic preparation overhead, beyond the manuscript’s deterministic successful-fusion count. | *PRA* **114**(3), 032614 (2026); [DOI](https://doi.org/10.1103/2z98-6bsp); [arXiv:2601.02087](https://arxiv.org/abs/2601.02087). |
| `Cashman2025finding` | Trail-cover decompositions and optimization of linear fusion networks supported. | [arXiv:2508.18375](https://arxiv.org/abs/2508.18375), 2025; authors/title/arXiv DOI correct. |
| `Ji2026towards` | Ring, star, and linear motifs joined by type-I fusion supported. | [arXiv:2606.02880](https://arxiv.org/abs/2606.02880), 2026; four authors/title/arXiv DOI correct. |
| `Davies2025preparing` | Preparation bounds supported with the qualification in finding 4. | [arXiv:2504.00291](https://arxiv.org/abs/2504.00291), 2025; authors/title/arXiv DOI correct. |
| `Cabello2011optimal` | Optimizing entangling-gate count and preparation depth through LC representatives supported. This should not be read as optimizing every possible interleaved Clifford circuit. | *PRA* **83**(4), 042314 (2011); [DOI](https://doi.org/10.1103/PhysRevA.83.042314); [arXiv:1011.5464](https://arxiv.org/abs/1011.5464). |
| `Sharma2026minimising` | Minimum-edge LC representatives supported. Its direct GHZ₃-fusion application deserves mention. | *Quantum* **10**, 2001 (2026); [DOI](https://doi.org/10.22331/q-2026-02-09-2001); [arXiv:2506.00292](https://arxiv.org/abs/2506.00292). |

| Cited entry | Claim check | Publication and identifier check |
|---|---|---|
| `Howorka1977characterization` | Appropriate foundational DH reference. | *Quarterly Journal of Mathematics* **28**(4), 417–420 (1977); [publisher/DOI](https://doi.org/10.1093/qmath/28.4.417). |
| `Bandelt1986distance` | Pendant/twin construction and its use for recognition supported. The connected construction used in the proof is valid. | *JCT B* **41**(2), 182–208 (1986); [publisher/DOI](https://doi.org/10.1016/0095-8956(86)90043-2). |
| `Oum2005rank` | Proposition 7.3 establishes rank-width at most one iff DH; cut-rank invariance under LC supports all uses of LC closure. | *JCT B* **95**(1), 79–100 (2005); [DOI](https://doi.org/10.1016/j.jctb.2005.03.003); [author-hosted text](https://mathsci.kaist.ac.kr/~sangil/pdf/vertexminor.pdf). |
| `Oum2017rank` | Definition/survey use appropriate; also corroborates the attribution of the \(C_5\) vertex-minor characterization to Bouchet. | *Discrete Applied Mathematics* **231**, 15–24 (2017); [DOI](https://doi.org/10.1016/j.dam.2016.08.006); [arXiv:1601.03800](https://arxiv.org/abs/1601.03800). |
| `Bouchet1987isotropic` | The \(C_5\) attribution is corroborated explicitly by Oum’s papers. Original full text was not retrieved. | *European Journal of Combinatorics* **8**(3), 231–244 (1987); [publisher/DOI](https://doi.org/10.1016/S0195-6698(87)80027-6). |
| `Bouchet1988transforming` | The publisher abstract directly confirms that locally equivalent trees are isomorphic. Its other structural uses are corroborated by Oum and split-decomposition literature. | *Journal of Graph Theory* **12**(2), 195–207 (1988); [publisher/DOI](https://doi.org/10.1002/jgt.3190120210). |
| `Hammer1990completely` | Star/clique split-decomposition characterization corroborated by Gioan–Paul, who credit this work. Original full text was unavailable. | *Discrete Applied Mathematics* **27**(1–2), 85–99 (1990). Authors/title/venue/pages/year match [Maffray’s publication list](https://pagesperso.g-scop.grenoble-inp.fr/~maffrayf/publications.html). The listed DOI is `10.1016/0166-218X(90)90131-U`; primary-endpoint verification remained incomplete. |
| `Hein2004multiparty` | Graph-state definition, cut Schmidt rank \(2^{\rho_G(A)}\), and classification through seven qubits supported. | *PRA* **69**(6), 062311 (2004); [DOI](https://doi.org/10.1103/PhysRevA.69.062311); [quant-ph/0307130](https://arxiv.org/abs/quant-ph/0307130). |
| `Hein2006entanglement` | Review citation appropriate. | Authors/title/year/[quant-ph/0602096](https://arxiv.org/abs/quant-ph/0602096) correct; published chapter metadata in finding 7. |
| `VandenNest2004graphical` | LC equivalence iff successive graph local complementations supported. Unitary correct modulo finding 9. | *PRA* **69**(2), 022316 (2004); [DOI](https://doi.org/10.1103/PhysRevA.69.022316); [quant-ph/0308151](https://arxiv.org/abs/quant-ph/0308151). |
| `VandenNest2006universal` | Entanglement-width context appropriate. The precise Schmidt-rank-width/TTN statement is more directly supported by the accompanying 2007 citation. | *PRL* **97**(15), 150504 (2006); [DOI](https://doi.org/10.1103/PhysRevLett.97.150504); [quant-ph/0604010](https://arxiv.org/abs/quant-ph/0604010). |
| `VandenNest2007classical` | Schmidt-rank width equals rank-width for graph states; TTN interpretation supported. The width is logarithmic in Schmidt rank. | *PRA* **75**(1), 012337 (2007); [DOI](https://doi.org/10.1103/PhysRevA.75.012337); [quant-ph/0608060](https://arxiv.org/abs/quant-ph/0608060). |
| `Danielsen2006classification` | Table 1’s indecomposable-code counts are exactly **1, 2, 4, 11, 26, 101, 440** for \(n=3,\ldots,9\), summing to **585**. Classification through twelve vertices supported. | *JCT A* **113**(7), 1351–1367 (2006); [DOI](https://doi.org/10.1016/j.jcta.2005.12.004); [math/0504522](https://arxiv.org/abs/math/0504522). |
| `Adcock2020mapping` | Mapping LC orbits supported. Its 587-orbit total through nine qubits includes the one- and two-qubit cases; this is consistent with 585 here. | *Quantum* **4**, 305 (2020); [DOI](https://doi.org/10.22331/q-2020-08-07-305); [arXiv:1910.03969](https://arxiv.org/abs/1910.03969). |
| `Dahlberg2020how` | General hardness and special-case algorithms supported; broad summary needs finding 1. | *Quantum Science and Technology* **5**(4), 045016 (2020); [DOI](https://doi.org/10.1088/2058-9565/aba763); [arXiv:1805.05306](https://arxiv.org/abs/1805.05306). |
| `Dahlberg2020transforming` | NP-completeness of transformation to specified Bell pairs under the stated restricted local operations supported. | *Quantum* **4**, 348 (2020); [DOI](https://doi.org/10.22331/q-2020-10-22-348); [arXiv:1907.08019](https://arxiv.org/abs/1907.08019). |
| `Dahlberg2020counting` | #P-completeness concerns counting LC-equivalent graph states; distinguish this from transformation decision. | *Journal of Mathematical Physics* **61**(2), 022202 (2020); [DOI](https://doi.org/10.1063/1.5120591); [arXiv:1907.08024](https://arxiv.org/abs/1907.08024). |

| Cited entry | Claim check | Publication and identifier check |
|---|---|---|
| `deMoura2021lean` | Appropriate Lean 4 reference. | CADE 28, pp. 625–635 (2021); [DOI](https://doi.org/10.1007/978-3-030-79876-5_37). Add LNCS **12699**. |
| `Mathlib2020lean` | Appropriate standard mathlib reference; collective author correct. | CPP 2020, pp. 367–381; [DOI](https://doi.org/10.1145/3372885.3373824); [arXiv:1910.09336](https://arxiv.org/abs/1910.09336). |
| `Gidney2021stim` | Appropriate stabilizer-simulator reference. | *Quantum* **5**, 497 (2021); [DOI](https://doi.org/10.22331/q-2021-07-06-497); [arXiv:2103.02202](https://arxiv.org/abs/2103.02202). |
| `McKay2014practical` | Appropriate nauty/canonical-labeling reference. | *Journal of Symbolic Computation* **60**, 94–112 (2014); [DOI](https://doi.org/10.1016/j.jsc.2013.09.003); [arXiv:1301.1493](https://arxiv.org/abs/1301.1493). |
| `RomeraParedes2024mathematical` | FunSearch supports the statement about new constructions through program search. Twelve-author list correct. | *Nature* **625**(7995), 468–475 (2024); [publisher/DOI](https://doi.org/10.1038/s41586-023-06924-6). |
| `Novikov2025alphaevolve` | AlphaEvolve supports the program-search/scientific-discovery context. Eighteen-author list correct. | [arXiv:2506.13131](https://arxiv.org/abs/2506.13131), 2025; title and arXiv DOI correct. |
| `Georgiev2025mathematical` | Supports mathematical exploration and improved constructions across several fields, including analysis. Four-author list correct. | [arXiv:2511.02864](https://arxiv.org/abs/2511.02864), 2025; title and arXiv DOI correct. |
| `Trinh2024solving` | Broad claim about machine generation combined with formal reasoning is fair. AlphaGeometry uses a specialized symbolic deduction/algebra engine; it should not be described as Lean-kernel verification. | *Nature* **625**(7995), 476–482 (2024); [publisher/DOI](https://doi.org/10.1038/s41586-023-06747-5). Five authors correct. |
| `Hubert2026olympiad` | AlphaProof directly supports the Lean/formal-proof comparison. Full author list checked. | *Nature* **651**(8106), 607–613 (2026); [publisher/DOI](https://doi.org/10.1038/s41586-025-09833-y). The 2026 issue year is correct despite “2025” in the DOI. |

For the older graph-theory attributions, the evidence is stronger than a generic secondary summary: [Oum’s original paper](https://mathsci.kaist.ac.kr/~sangil/pdf/vertexminor.pdf) explicitly attributes the \(C_5\) characterization to Bouchet, and [Gioan–Paul](https://arxiv.org/pdf/0810.1823) explicitly credits Hammer–Maffray for the relevant DH split-tree structure. Nevertheless, those corroborations should not be represented as inspection of every original theorem in the inaccessible articles.

**Missing citations and closer connections worth adding**

- **Required for the corrected complexity sentence:** [Dahlberg–Wehner 2018](https://arxiv.org/abs/1805.05305), *Transforming graph states using single-qubit operations*. It is already in the bibliography and is the direct source for the parameterized algorithm.

- **Recommended beside the split-decomposition derivation:** [Gioan–Paul 2012](https://arxiv.org/pdf/0810.1823), *Split decomposition and graph-labelled trees*, *Discrete Applied Mathematics* **160**(6), 708–733, DOI [10.1016/j.dam.2011.05.007](https://doi.org/10.1016/j.dam.2011.05.007). Their node-join operation is the same neighborhood-completion operation used by the fusion lemma, and they give the star/clique characterization directly. This entry is also already present but uncited.

- **Recommended to explain the distinction between the two extremal classes:** [Bui-Xuan–Kanté–Limouzy, *A Note on Graphs of Linear Rank-Width 1*](https://arxiv.org/abs/1306.1345). It connects connected linear-rank-width-one graphs with local equivalence to caterpillars. This makes the difference between Löbl’s zero-fusion class and the present DH class precise.

- **Recommended in the machine-discovery discussion:** [Davies et al. 2021, *Advancing mathematics by guiding human intuition with AI*](https://www.nature.com/articles/s41586-021-04086-x), *Nature* **600**, 70–74. Data-guided conjecture formation is particularly relevant to the manuscript’s discovery account. The entry is already present but uncited.

- **Useful if the related-work scope includes Bell-pair/postselected models:** [Adcock et al. 2019](https://arxiv.org/abs/1806.03263), DOI [10.1088/2058-9565/aae950](https://doi.org/10.1088/2058-9565/aae950).

- **Expand an existing citation:** Mention Sharma et al.’s Appendix D GHZ₃-fusion application explicitly. The current minimum-edge description is correct but understates its relevance.

I would not require a large additional bibliography of generic photonic generation schemes. The central missing work is the direct algorithm citation; the main novelty comparisons are already substantially present.

**Search log**

The independent search used result descriptions, mathematical phrases, alternative resources, and exact formulas before following the manuscript’s citation chain.

| Search purpose | Queries used | Principal sources checked |
|---|---|---|
| Exact fusion-width bound | `"rank-width" "fusion" lower bound`; `"Schmidt-rank width" "fusion"`; `"fusion counts" "rank-width"`; `"fusion" "n+3" "rank"` | Löbl generating paper; KMY; Van den Nest width/TTN papers; fusion-generation literature. No exact GHZ₃ bound located. |
| Exact extremal characterization | `"n-3" "distance-hereditary" fusion`; `"fusion" "distance-hereditary" GHZ`; `graph state fusion distance hereditary rank width`; `GHZ graph state fusion tree distance hereditary` | Connolly split-fuse and orbit papers; Bandelt–Mulder; Oum; Gioan–Paul; Lee–Jeong. No earlier explicit iff located. |
| Nearby resources and operations | `"Bell pairs" "distance-hereditary" preparation`; `"GHZ" "minimum" "fusion" "star" graph states lower bound`; `minimum fusion graph states Schmidt rank width lower bound` | Adcock postselectability; Browne–Rudolph; Zaidi; Sharma; Staudacher; Cashman; Ji; caterpillar/linear-rank-width literature. |
| Broader Schmidt-rank terminology | Fusion, Schmidt-rank, qudit, and ancilla searches | [Rimock–Oz, *Generalized Fusion of Qudit Graph States*](https://arxiv.org/abs/2510.16623). Its per-event Schmidt-rank/ancilla bounds concern a different quantity from graph-state Schmidt-rank width and total GHZ₃ fusion count. |
| Possible nearby structural results | Graph-state preparation, circle graphs, rank-width, split decomposition | [*The Structure of Circle Graph States*](https://arxiv.org/abs/2603.08847), KMY references, Davies–Jena, and Cashman’s thesis. No collision with either stated theorem found. |
| Citation and metadata verification | Exact titles, author combinations, arXiv identifiers, and DOI searches for all 42 cited entries; publication-status searches for recent preprints | arXiv abstracts and full texts; APS, Quantum, Nature, Springer, Wiley, OUP, Elsevier, institutional author records, and publisher-deposited Crossref metadata. |

The principal retrieval limitations were the original full texts of Bouchet’s older papers and Hammer–Maffray, plus the current IOP page for Connolly–Nishio–Nemoto. Those limitations are identified above; the negative novelty result remains a literature-search conclusion, not a proof of priority.
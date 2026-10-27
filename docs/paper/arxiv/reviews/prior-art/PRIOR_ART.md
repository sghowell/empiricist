# Prior art and bibliography: "Distance-hereditary graphs characterize minimum-fusion synthesis of graph states"

- Paper: `docs/paper/paper.tex` (July 2026 draft). I read the abstract, the introduction, Section 2, the rest of the body, and the inline bibliography (12 entries). No repository file was edited.
- Date of search: 2026-10-26. Coverage: journals and arXiv through October 2026, plus theses that are indexed or hosted.
- Method:
  - WebSearch, standard and extended (log in Section 9).
  - WebFetch of arXiv abstract and HTML pages.
  - arXiv API (`export.arxiv.org`) for metadata.
  - Crossref metadata plus `doi.org` resolution to the publisher page, for every DOI.
  - Full-text PDF extraction (`pdftotext`) wherever a statement is quoted.
  - Helper scripts and the extracted texts are in `src/`.
- Companion file: `refs.bib` (55 entries, each with a DOI or eprint field and a one-line verification comment). A throwaway `\nocite{*}` build with tectonic/BibTeX parses all 55 entries with an empty warning log.

---

## 1. Verdict

**Not anticipated as stated, but close to known results.**

What I could not find anywhere (journals, arXiv through 2026-10-26, indexed theses):
- the statement "F(G) = N − 3 if and only if G is distance-hereditary" in the GHZ3 / type-II model, or any equivalent wording (rank-width ≤ 1, C5-vertex-minor-free);
- the lower bound F(G) ≥ N − 3 stated explicitly;
- a minimum-fusion classification of the 585 connected LC orbits with N ≤ 9 in this model.

The per-N counts of DH LC orbits (1, 2, 3, 8, 15, 42, 104) and of non-extremal orbits match no OEIS entry. The tree-containing count 93 does match OEIS: it equals the number of unlabelled trees on 3–9 vertices (A000055), which is what Bouchet's theorem that LC-equivalent trees are isomorphic predicts.

However, the theorem is not deep news to a specialist. Both directions follow in a few lines from published results (Section 3). Two 2026 papers in neighbouring models come very close:

1. **Kumabe, Mori, Yoshimura, Quantum 10, 2165 (2026)** [`Kumabe2026complexity`].
   - Model: Clifford circuits; cost = number of two-qubit Clifford (CZ) gates.
   - Result: for connected G, CZ-complexity ≥ n + r − 2 (r = rank-width, Thm. 7) and ≤ n − 1 when r = 1 (Cor. 5).
   - Consequence: CZ-complexity = n − 1 exactly for the connected rank-width-1, i.e. distance-hereditary, graphs. This is the circuit-model twin of the paper's theorem, though they never use the words "distance-hereditary" or "fusion".
2. **Connolly, Nishio, Browne, Munro, Nemoto, arXiv:2603.23892 (Mar 2026)** [`Connolly2026efficient`].
   - Every DH graph state is assembled from star graph states by type-II fusions along its split tree (Prop. 1, "split-fuse").
   - Combined with Lee and Jeong's star-from-GHZ3 construction, this gives exactly N − 2 GHZ3 states and N − 3 fusions for every DH graph. That is the forward direction, although neither paper states it.
3. **Löbl, Pettersson, Jena, Dellantonio, Paesani, Sørensen, Phys. Rev. A 111, 052604 (2025)** [`Lobl2025generating`]. This is the closest *fusion-count* work, in the emitter-caterpillar model:
   - an exact minimum-fusion lookup table (which they call a "tablebase") for all graph states up to 8 qubits;
   - the zero-fusion class: LC-equivalent to sets of caterpillars (Thm. 2);
   - a linear-rank-width lower bound, n_f^min + 1 ≥ n_s^min (Eq. 2);
   - the 5-qubit ring is the smallest state needing a fusion.

**Recommendation.**
- Cite these three prominently.
- Present the theorem as the exact characterization *in the GHZ3/type-II model*, and acknowledge the split-decomposition and Schmidt-rank-width routes.
- Locate the novelty in the parts that are genuinely new:
  - the certified classification of all 585 orbits, including exact values above the floor (F = N, F = N + 3);
  - the refutation of the "linear in rank-width" refinement;
  - the machine discovery under the stated discipline;
  - the Lean formalization.

As the draft stands, a referee who knows split decompositions or Kumabe et al. will say the main theorem is "known in spirit".

---

## 2. Closest works and how each differs

| # | Work | Resource / cost model | What it proves | Difference from the paper |
|---|------|----------------------|----------------|---------------------------|
| 1 | Connolly, Nishio, Browne, Munro, Nemoto 2026, arXiv:2603.23892 [`Connolly2026efficient`] | Star states prepared by CZ gates, then type-II fusions (H + Bell measurement) along the split tree (QASST); cost counted in CZ gates, time steps and auxiliary qubits | Prop. 1: "If G is a graph with split decomposition into quotient graphs QASST(G)=(Q1,…,Qk), then the graph state \|G⟩ can be recovered from quotient graph states \|Q1⟩,…,\|Qk⟩ by using Type-II fusions on all pairs of connected split-nodes described by the QASST." For DH graphs every quotient is a star or clique ("completely separable [Hammer–Maffray]; this is equivalent to the distance-hereditary condition"). Split-fuse uses k − 1 fusions and n + 2k − 3 CZ gates (fusions counted as CZ). | No GHZ3-only resource, no minimum-fusion claim, no lower bound, no converse. Nevertheless it contains the whole forward-direction construction (Section 3a). Preprint, not yet published. |
| 2 | Kumabe, Mori, Yoshimura, Quantum 10, 2165 (2026), arXiv:2402.05874 (v4 Jul 2026) [`Kumabe2026complexity`] | Computational-basis measurements, single-qubit and two-qubit Cliffords, ancillas allowed; cost = number of two-qubit Cliffords ("CZ-complexity" Γ_CZ) | Cor. 5: "For any graph G with n vertices and rank-width 1, Γ_CZ(\|G⟩) ≤ n − 1." Followed by: "Since n − 1 is a trivial lower bound … Corollary 5 implies that Γ_CZ(\|G⟩) = n − 1 for any connected graph G with rank-width 1." Thm. 7: "For any connected graph G with n ≥ 2 vertices and rank-width at least r, Γ_CZ(\|G⟩) ≥ n + r − 2" (so Γ_CZ(C_n) = n for n ≥ 5). Thm. 3: Γ_CZ ≤ t iff G is reachable by vertex deletions, local complementations and ≤ t "elementary edge-complementations". One of these toggles "all edges between the neighborhoods of two non-adjacent vertices", which is exactly the graph action of a type-II fusion before the two qubits are deleted. | Different cost (CZ gates, not fusions of GHZ3), different resource (\|0⟩ inputs plus ancillas). Neither result implies the other directly. Same structure as the paper: trivial connectivity floor, extremal class = rank-width 1, C5 first non-extremal case. Does not use the words "distance-hereditary" or "fusion". Priority: the n + r − 2 lower bound is in the v1 abstract (Feb 2024). Cor. 5 is checked here in v4 (Jul 2026, = the Quantum version); v1 already lists an O(rn log n) upper bound. |
| 3 | Löbl, Pettersson, Jena, Dellantonio, Paesani, Sørensen, Phys. Rev. A 111, 052604 (2025), arXiv:2412.04587 [`Lobl2025generating`] | Caterpillar graph states from a single quantum emitter, plus type-II fusions measuring X_A Z_B ∧ Z_A X_B | Dynamic-programming lookup table ("tablebase", their word) giving the exact minimum number of fusions for ~2.8×10^7 graph states, all ≤ 8 qubits. Thm. 2: emitter + local operations generate "only graph states that are local Clifford equivalent to sets of caterpillar graphs" (the zero-fusion class). Eq. (2): n_f^min(G) + 1 ≥ n_s^min(G), the minimum number of static qubits ("corresponds to the linear rank width"). Thm. 7: the bound is monotone under induced subgraphs. "The smallest graph state that requires at least one (two) fusion(s) is the five-qubit ring." Reports 1, 1, 2, 4, 11, 26, 101 orbits for 2–8 nodes and 440 at 9. | Different resource (caterpillars, not GHZ3), so different values and a different extremal class (linear rank-width ≤ 1 vs rank-width ≤ 1). No DH or rank-width characterization. The paper's "tablebase" term and its orbit-level DP mirror this work; credit it explicitly. |
| 4 | Lee & Jeong, Quantum 7, 1212 (2023), arXiv:2304.11988 [`Lee2023graph`] | 3-qubit star (GHZ3) resources, type-II fusion (H + BSM) | Exact graph rule F_{v1,v2} (Section 5). Sec. 2.2: "An m-qubit star graph state can be constructed by conducting fusions on m − 2 copies of \|G*(3)⟩." Sec. 2.1.1 "unraveling" of a bipartitely-complete subgraph replaces "nm edges with n+m edges and one fusion", i.e. undoes a split. Heuristic optimizer (OptGraphState) for expected resource count under probabilistic fusion. | Same model as the paper, but heuristic: "our strategy does not guarantee that the obtained generation method is strictly optimal." No lower bound, no characterization, no DH/rank-width. Gives the star (hence K_N) upper bound N − 3. |
| 5 | Van den Nest, Dür, Vidal, Briegel, PRA 75, 012337 (2007) [`VandenNest2007classical`]; Hein, Eisert, Briegel, PRA 69, 062311 (2004), Prop. 3 / Eq. (43) [`Hein2004multiparty`] | Entanglement theory | log2(Schmidt rank of \|G⟩ across A\|B) = rank over F2 of Γ_AB (the cut-rank). Schmidt-rank width of \|G⟩ equals rank-width of G (VdN et al. Eqs. 7–8). Schmidt-rank width relates to optimal tree tensor networks. | Not about fusion. Together with Oum 2005 it gives the reverse direction in a few lines (Section 3b). |
| 6 | Connolly, Nishio, Nemoto, arXiv:2602.23825 (Feb 2026) [`Connolly2026local`] | Pure graph theory | Explicit LC-class sizes for families of DH graphs via split decomposition. States "a connected graph is distance-hereditary if and only if it has rank-width 1 (Proposition 7.3 of [Oum])" and Bouchet's "Any two locally equivalent trees are isomorphic" (Thm. VI.6). | Counts orbit sizes, not fusion costs. Useful citation for DH/LC background. |
| 7 | Ji, Weerasena, Farfurnik, Liu, arXiv:2606.02880 (Jun 2026) [`Ji2026towards`] | Ring/star/linear motifs joined by **type-I** fusion | Heuristic decomposition (CFD); the minimum-edge LC representative as a proxy for good synthesis. | Heuristic, type-I, no bound or characterization. Requested citation; verified. |
| 8 | Cabello, Danielsen, López-Tarrida, Portillo, PRA 83, 042314 (2011) [`Cabello2011optimal`]; Sharma, Goodenough, Borregaard, Rozpędek, Helsen, Quantum 10, 2001 (2026) [`Sharma2026minimising`]; Adcock et al., Quantum 4, 305 (2020) [`Adcock2020mapping`] | Circuit / edge-count models over LC orbits | Optimal (minimum two-qubit gate / minimum edge) preparation of LC classes; Sharma et al. apply it to fusion-based generation of repeater graph states. | Different cost measures, no DH characterization. Cite as LC-orbit optimization context. |
| 9 | Staudacher, Jeevanesan, Guggemos, PRA 114, 032614 (2026) [`Staudacher2026adaptive`]; Cashman, de Felice, Kissinger, arXiv:2508.18375 (2025) [`Cashman2025finding`] and Cashman's Oxford MMathCS thesis (2024) | Linear-cluster resources, type-I/II fusions, failure-aware | Fusion-count optimization; NP-hardness of trail-cover formulations; fusions = \|E\| − \|V\| + \|C\| for trail covers (thesis Eq. 6.1). | Different resources, heuristic or complexity results, no DH. Cite as 2025–26 fusion-optimization work. |
| 10 | Davies & Jena, arXiv:2504.00291 (2025) [`Davies2025preparing`]; Dahlberg, Helsen, Wehner (QST 2020; Quantum 2020; JMP 2020) | CZ-distance; vertex-minor problems | CZ-distance bounds for vertex-minor-closed classes and bounded rank-width. Efficient algorithms for GHZ extraction from Schmidt-rank-width-one (DH) graph states; hardness of related problems. | Context for DH/rank-width in graph-state preparation and for the complexity open question. No fusion characterization. |

Nothing else found anticipates the result. Notable non-anticipating 2024–2026 items seen during the search:
- Miguel-Ramiro & Dür, "Graph state fission" (arXiv:2412.00197);
- Rimock & Oz, PRA 114, 042439 (2026) (weighted-graph fusion);
- Hahn, McCarty, Poulsen Nautrup, Claudet, arXiv:2603.08847 (circle graph states);
- Revis et al., arXiv:2609.30400 (minimal emitters, linear rank-width);
- Manohar et al., arXiv:2605.09325;
- Hartnett et al., arXiv:2508.16505 (automated discovery of ballistic generators);
- de Felice et al., arXiv:2409.13541 ("Fusion and flow");
- Claudet's PhD thesis, arXiv:2511.22271.

---

## 3. Both directions follow quickly from published results (my analysis, not found stated anywhere)

This is the main referee risk. It also bears on the paper's one non-formalized step.

### (a) Forward direction, DH ⇒ F(G) = N − 3

1. A connected graph is DH iff every node of its split decomposition is a star or a complete graph. Sources:
   - Bouchet 1988 [`Bouchet1988transforming`], quoted as Theorem 2.9 in Adler–Kanté–Kwon, arXiv:1403.1081;
   - Hammer–Maffray 1990 [`Hammer1990completely`], as cited by Connolly et al. 2026;
   - Cunningham 1982 [`Cunningham1982decomposition`] and Gioan–Paul 2012 [`Gioan2012split`] for split decomposition itself.
2. Let the split tree have k nodes, node i a star or clique on m_i ≥ 3 vertices. Then Σ m_i = N + 2(k − 1).
3. By Connolly et al. 2026, Prop. 1, |G⟩ is obtained from the k quotient states by k − 1 type-II fusions.
4. Each quotient state is LC-equivalent to the m_i-qubit star, which Lee & Jeong (Sec. 2.2) build from m_i − 2 GHZ3 states with m_i − 3 fusions.
5. Totals:
   - resources: Σ(m_i − 2) = N − 2;
   - fusions: Σ(m_i − 3) + (k − 1) = N − 3.

### (b) Reverse direction, F(G) = N − 3 ⇒ DH, for arbitrary schedules

1. **The fusion network is a tree.** At f = N − 3, the identity N = 3g − 2f forces g = N − 2 = f + 1. Let M be the multigraph whose nodes are the resources and whose edges are the fusions. M must be connected: otherwise either the output is a product state, contradicting connectivity of G, or some component has all qubits consumed (f_i = 1.5 g_i), which forces f > g − 1. So M is a tree. This means no intra-blob fusions, no self-loops and no multi-edges.
2. **Each tree edge carries Schmidt rank at most 2.** Fix an edge e of M and let A | B be the output qubits on its two sides. The fusions on disjoint qubit pairs commute, so the final state is a contraction of a state on A ∪ {x} with a state on B ∪ {y} through one two-qubit projection on (x, y). Its Schmidt rank across A | B is therefore at most 2. Local Cliffords and Pauli byproducts do not change this.
3. **This bounds the cut-rank.** By Hein–Eisert–Briegel Prop. 3 / Eq. (43) and Van den Nest et al. 2007 Eq. (7), cut-rank_G(A) = log2(Schmidt rank) ≤ 1.
4. **The fusion tree is a rank decomposition.** Attach each output qubit as a leaf to its resource node. Every resource node then has degree 3, so this is a subcubic tree with N leaves, and every edge has cut-rank ≤ 1. Hence rw(G) ≤ 1, so G is DH (Oum 2005 [`Oum2005rank`]).

### Implications for the paper

- **Section 6, the single-blob normal form.** The argument in (b) needs no reordering into a single growing blob. It handles multi-component and intra-blob schedules directly. The paper could state it as an alternative (prose) proof of the physical reverse direction, which removes the "single-blob normal form" gap from the theorem's proof. It would still be unformalized, consistent with the paper's remark that rank-width is not in mathlib.
- **Positioning.** The paper should cite the ingredients above and say that the characterization can be read off from split decomposition plus Schmidt-rank width. The Lean development and the certified tablebase are still the new contributions.

---

## 4. Specific sub-questions

### Is the N − 3 lower bound stated in prior work?

Not explicitly, anywhere I searched.
- Nearest: Lee & Jeong's (m − 2)-copy star construction (an upper bound for stars) and the "nm edges → n + m edges and one fusion" bookkeeping.
- Kumabe et al. call n − 1 a "trivial lower bound" in the CZ model.
- The repo's own `docs/open_problems_ftfbqc.md` (Problem 5) calls the bound "folklore, two lines".
- Present it as an elementary observation, not as a result.

### Are exact values for trees, paths, stars, K_N, K_{m,n} known in this model?

- **Stars / GHZ (and K_N by one LC):** the N − 3 construction is explicit in Lee & Jeong (Sec. 2.2). Minimality is not claimed but is immediate from the counting bound.
- **Trees, paths, K_{m,n}:** no explicit minimum-fusion statement found in the GHZ3/type-II model. All are DH, so they follow from Section 3a.
- **Nearby models:**
  - CZ model: Kumabe et al. note Γ_CZ(K_n) ≤ n − 1 via the star, Γ_CZ = n − 1 for every connected rank-width-1 graph, and Γ_CZ(C_n) = n for n ≥ 5.
  - Caterpillar model: caterpillars need 0 fusions (Löbl et al. Thm. 2).
  - Connolly et al. 2026 give minimal-edge representatives for complete multipartite orbits; for K_{n,m}, "the minimal edge representative has |E(G)| = n + m − 1".

### Bell-pair / type-I / linear-optics / vertex-minor variants

- No characterization of an extremal class in a Bell-pair, star/GHZ + type-I, or linear-cluster model was found.
- The only rank-width-type fusion bound found is Löbl et al.'s linear-rank-width bound (Eq. 2).
- The nearest vertex-minor/rank-width preparation results are Kumabe et al. and Davies & Jena (CZ cost).

### Two free external cross-checks the paper can cite

1. **Orbit counts.** The 585 orbits (1, 2, 4, 11, 26, 101, 440 for N = 3..9) are exactly Danielsen–Parker's Table 1 [`Danielsen2006classification`]. Their text: "The set of all distinct LC orbits of connected graphs on n vertices is a partitioning of G_n into i_n disjoint sets." Löbl et al. report the same numbers. The N ≤ 7 part is the Hein–Eisert–Briegel classification.
2. **Tree-containing orbits.** The paper's "93 of the 175 extremal orbits contain a tree" equals the number of unlabelled trees on 3–9 vertices: 1 + 2 + 3 + 6 + 11 + 23 + 47 = 93 (OEIS A000055, checked). This is exactly what Bouchet's theorem predicts (two LC-equivalent trees are isomorphic; Bouchet 1988 Cor. 5.4 per Connolly–Nishio–Nemoto Thm. VI.6; also used by Löbl et al.).

---

## 5. The fusion rule: citable source, exact statement, conditions

### Origin

Browne & Rudolph, PRL 95, 010501 (2005) [`Browne2005resource`] introduce type-II fusion. Verbatim:

> "When it succeeds, with probability 1/2, (as heralded by the detection of a photon in each output mode) this gate is a destructive projective measurement onto maximally entangled states, i.e. the Kraus operators are (⟨HH| + ⟨VV|)/√2, (⟨HV| + ⟨VH|)/√2. The failure outcome (signaled by detecting no photons in one of the modes) effectively performs a projective measurement of σx on each of the photons."

Their action is given at the state level for redundantly encoded cluster qubits. It is not a general graph rule.

### First explicit general derivation

Zaidi, Dawson, van Loock, Rudolph, PRA 91, 042301 (2015), Fig. 1 and Appendix [`Zaidi2015near`]. Qubit 1′ is Hadamard-rotated, then a Bell measurement (X1X1′, Z1Z1′) is applied to two cluster states. Verbatim:

> "The qubit i inherits all its neighbours along with the neighbours of 1′, j inherits all its neighbours along with the neighbours of 1. This analysis holds for all qubits i and j that are neighbors of 1 and 1′, respectively. It also holds for other projectors in the Bell basis up to local unitary operations."

### Cleanest formal statement (recommended primary citation)

Lee & Jeong, Quantum 7, 1212 (2023), Sec. 1.2 "Type-II fusion operation", Fig. 3 [`Lee2023graph`]. Verbatim:

> "The type-II fusion operation (hereafter referred to simply as "fusion") [Browne–Rudolph] is a two-qubit operation that consists of applying a Hadamard gate (Ĥ) to one of the qubits, followed by a BSM, and finally erasing the qubits. In other words, fusion indicates a destructive measurement of two Pauli operators X̂⊗Ẑ and Ẑ⊗X̂ on a pair of qubits. By applying a fusion on an unconnected pair (v1, v2) of vertices in a graph state, we can connect (disconnect) every adjacent vertex of v1 with every adjacent vertex of v2 up to several Pauli-Z operators if they are unconnected (connected) … More formally, for two unconnected vertices v1 and v2 of a graph G, F_{v1,v2} is defined as a graph operation that, for every u1 ∈ adj(v1) and u2 ∈ adj(v2), connect (disconnect) u1 and u2 if they are unconnected (connected) and delete v1 and v2 from the graph. When v1 and v2 undergo a fusion for which the Hadamard gate is applied on v1, the resulting state is ∏_{u1∈adj(v1)} Ẑ_{u1}^{(1−m_sign)/2} ∏_{u2∈adj(v2)} Ẑ_{u2}^{(1−m_lett)/2} |F_{v1,v2}(G)⟩, where (m_sign, m_lett) is the outcome of the BSM."

Bell outcomes are labelled (±1, 1) for |φ±⟩ and (±1, −1) for |ψ±⟩. They add: "fusion was originally defined as a BSM in Ref. [Browne–Rudolph]. Nevertheless, we consider its variant (differing only by a Hadamard gate)". The linear-optical BSM "can distinguish only two among the four Bell states, thus the fusion succeeds with the probability of p_succ(η) = (1 − η)²/2" (η = photon loss).

### Complete rule set

Löbl, Pettersson, Paesani, Sørensen, Quantum 9, 1795 (2025), Sec. 3.1, Eqs. (8)–(11) [`Lobl2025transforming`]. For X_A Z_B ∧ Z_A X_B with unconnected A, B, and no other assumption:

- ∀a_i ∈ N(A)∖N(B): X_{a_i} Z_{N(a_i) Δ N(B)}
- ∀b_i ∈ N(B)∖N(A): X_{b_i} Z_{N(b_i) Δ N(A)}
- ∀c_i ∈ N(A)∩N(B): X_{c_i} Z_{N(c_i) Δ N(A) Δ N(B)}
- all other vertices are unchanged; A and B are removed.

Signs are handled separately: "We do not consider the stabilizer signs … The provided graph transformations, together with the local Clifford gates, therefore give a graph basis state that is equivalent to a graph state up to local Pauli Z-gates."

Other cases:
- Sec. 3.2 treats the bare "standard fusion" X_A X_B ∧ Z_A Z_B. Its result is LC-equivalent to a graph state on a different graph, built with a "special neighbour" a*.
- Appendices D/E cover connected fusion qubits and all five rotated success cases.
- Failure "corresponds to two independent single-qubit measurements".

### Exact statement to use in the paper (disjoint inputs, as in the GHZ3 model)

Let |G1⟩, |G2⟩ be graph states on disjoint vertex sets, with a ∈ V(G1) and b ∈ V(G2). Measure X_a Z_b and Z_a X_b destructively; equivalently, apply a Hadamard on one of the two qubits and then a Bell measurement {XX, ZZ}. For every one of the four outcomes, the remaining qubits are left in

  ∏_{u∈N(a)} Z_u^{(1−m_sign)/2} ∏_{w∈N(b)} Z_w^{(1−m_lett)/2} |G′⟩,

where G′ = (G1 − a) ∪ (G2 − b) + {uw : u ∈ N_{G1}(a), w ∈ N_{G2}(b)}.

Sources: Lee–Jeong Sec. 1.2 (with H on v1 = a); Löbl et al. Eqs. (8)–(9) with N(a) ∩ N(b) = ∅; Zaidi et al. Appendix. I re-derived this from the stabilizers and it agrees.

### Conditions

1. **Basis.** The neighbour-join rule is exact, up to Pauli Z, for the X⊗Z / Z⊗X pair, i.e. an {XX, ZZ} Bell measurement preceded by a Hadamard on one fused qubit.
   - The bare {XX, ZZ} measurement (Browne–Rudolph's original, Löbl's "standard fusion") gives a state LC-equivalent to a graph state, but in general on a different graph (Löbl Sec. 3.2).
   - Because single-qubit Cliffords are free and F is LC-invariant, both conventions give the same F. The paper already says this in Section 2.
2. **Unconnected qubits.** v1 and v2 must be unconnected. This is automatic for qubits in different components, where also N(a) ∩ N(b) = ∅, so the toggle rule reduces to "add every edge between N(a) and N(b)".
3. **Outcome dependence.** Only Pauli-Z byproducts depend on the outcome. The graph is the same for all four Bell outcomes.
4. **Linear optics.** Only two of the four Bell states are distinguished (success probability 1/2 with no loss). Failure acts as two single-qubit measurements: σx in Browne–Rudolph's convention; setup-dependent in Löbl et al.'s Appendix A. F counts successful fusions only.

### Suggested sentence for Section 2 of the paper

"Type-II fusion was introduced by Browne and Rudolph [Browne2005resource]; in the X⊗Z, Z⊗X convention used here its action on graph states (remove a, b and join every neighbour of a to every neighbour of b, up to outcome-dependent Pauli-Z corrections) is stated explicitly in [Lee2023graph, Sec. 1.2] (see also [Zaidi2015near]), and in full generality, for all rotated variants and overlapping neighbourhoods, in [Lobl2025transforming]."

Connolly et al. 2026 restate the rule in exactly this form for two different graph states: "each of the neighbors of q1 is connected to all of the neighbors of q2 (and vice versa) and then q1 and q2 are deleted."

---

## 6. Bibliography actions for `paper.tex`

### Existing entries

All 12 inline entries re-verified against Crossref/DOI. Their bibliographic data are correct.

| Old key | New key in `refs.bib` |
|---|---|
| fbqc | Bartolucci2023fusion |
| graphstates | Hein2004multiparty |
| vandennest | VandenNest2004graphical |
| bouchet | Bouchet1988graphic |
| bandeltmulder | Bandelt1986distance |
| howorka | Howorka1977characterization |
| oum-rw | Oum2005rank |
| oum-seymour | Oum2006approximating |
| lean4 | deMoura2021lean |
| mathlib | Mathlib2020lean |
| stim | Gidney2021stim |
| nauty | McKay2014practical |

### Additions, by location

**Introduction**
- Fusion-optimization context: Lee2023graph, Lobl2025generating, Kumabe2026complexity, Connolly2026efficient. Add Ji2026towards, Staudacher2026adaptive, Cashman2025finding, Sharma2026minimising as recent work.
- The sentence on DH equivalences:
  - the C5-vertex-minor characterization has no citation; add Bouchet1987isotropic and Bouchet1988transforming (attribution per Oum's survey, Oum2017rank: "A theorem of Bouchet [Isotropic systems; Transforming trees…] implies that a graph G has rank-width at most 1 if and only if C5 … is not isomorphic to a vertex-minor of G");
  - add Hammer1990completely / Cunningham1982decomposition / Gioan2012split if the split-decomposition view is mentioned.
- Rank-width as an entanglement measure: VandenNest2006universal, VandenNest2007classical.

**Section 2 (model)**
- Fusion rule: Browne2005resource, Lee2023graph, Lobl2025transforming (Zaidi2015near optional).
- GHZ3 as the FBQC primitive: Bartolucci2023fusion, GimenoSegovia2015three (Bartolucci2021creation optional).
- "Model dependence … emitter-generated caterpillar resources": Lobl2025generating, plus Hilaire2023near, Lindner2009proposal, Li2022photonic.
- The N − 3 bound: present as elementary. Optionally note the analogous trivial n − 1 CZ bound [Kumabe2026complexity].

**Section 4 (tablebase)**
- Cite Danielsen2006classification (and Hein2004multiparty for N ≤ 7) for the orbit counts.
- Note Löbl et al.'s tablebase / DP precedent [Lobl2025generating].
- Optionally note that C5 is also the first non-trivial case in the caterpillar model (Löbl) and in the CZ model (Kumabe Thm. 7).

**Section 5 / 6 (characterization, forward, reverse)**
- Cite Connolly2026efficient and Connolly2026local.
- Acknowledge the split-decomposition route (Section 3a here) and the Schmidt-rank-width route (Section 3b here), citing VandenNest2007classical, Hein2004multiparty and Oum2005rank. Consider using 3b to close the single-blob gap.
- For "93 orbits contain a tree": cite Bouchet1988transforming (LC-equivalent trees are isomorphic) and note that 93 equals the number of unlabelled trees on 3–9 vertices.

**Discussion (complexity of F)**
- Kumabe2026complexity, Dahlberg2020how, Dahlberg2020transforming, Dahlberg2020counting, Davies2025preparing.
- Löbl et al. describe their optimization as computationally demanding.

**Section 3 (method, brief)**
- RomeraParedes2024mathematical (FunSearch), Novikov2025alphaevolve, Georgiev2025mathematical, Davies2021advancing, Wagner2021constructions, Hubert2026olympiad (AlphaProof), Trinh2024solving (AlphaGeometry), alongside deMoura2021lean and Mathlib2020lean.

**Further reading:** Hein2006entanglement (review), Adcock2020mapping, Cabello2011optimal, Patil2026graphical, Rimock2026type.

---

## 7. Errors spotted in the repo's own notes (reported only, not edited)

`docs/open_problems_ftfbqc.md`, references:

- **[40]** lists "M. C. Löbl, S. X. Chen, S. Paesani, A. S. Sørensen". The arXiv record and Crossref give six authors: Löbl, Pettersson, Jena, Dellantonio, Paesani, Sørensen.
- **[41]** conflates three different papers:
  - "How to transform graph states using single-qubit operations…", QST 5, 045016 (2020);
  - "Transforming graph states to Bell-pairs is NP-Complete", Quantum 4, 348 (2020);
  - "Counting single-qubit Clifford equivalent graph states is #P-complete", J. Math. Phys. 61, 022202 (2020).
- **[42]** Li–Economou–Barnes is npj Quantum Inf. **8, 11** (2022), not "8, 93".

Fix these if the paper, cover letter or a later note reuses them.

---

## 8. Unverified items and caveats

1. **Hein2006entanglement.** Only the arXiv record was verified (comments: "To appear in the Proceedings of the International School of Physics 'Enrico Fermi' …, Varenna, Italy, July, 2005"). No DOI was found in Crossref, and the volume and page numbers were not verified. The bib entry deliberately omits them.
2. **Theorem numbers taken from secondary citations.** Publisher pages (ScienceDirect, Wiley) returned HTTP 403.
   - Oum 2005 "Proposition 7.3" (rank-width 1 ⇔ DH): number taken from Connolly–Nishio–Nemoto 2026. The statement itself is confirmed in Oum's own survey (Oum2017rank, arXiv full text) and in Adler–Kanté–Kwon.
   - Bouchet 1988 "Corollary 5.4" (LC-equivalent trees are isomorphic): from Connolly–Nishio–Nemoto, Thm. VI.6.
   - Bouchet 1988 as the source of "DH ⇔ every split-decomposition bag is a clique or star": from Adler–Kanté–Kwon, Thm. 2.9.
   - Hammer–Maffray "completely separable = DH": from Connolly et al. 2603.23892.
   - The bibliographic data of all these papers are verified via Crossref/DOI.
3. **Kok & Lovett textbook** (*Introduction to Optical Quantum Information Processing*, CUP 2010, doi:10.1017/CBO9781139193658). Bibliographic record verified via Crossref. Its fusion-rule content was not checked (Zaidi et al. and Löbl et al. cite it as an earlier treatment), so it is not in `refs.bib`.
4. **Cashman thesis** ("Optimisation of fusion networks with linear resource states", MMathCS, Oxford, Trinity 2024). PDF read at cs.ox.ac.uk/people/aleks.kissinger/theses/cashman-thesis.pdf. It has no DOI or eprint, so it is not in `refs.bib`; cite Cashman2025finding instead.
5. **AlphaProof.** Crossref gives the print issue, Nature 651, 607–613 (2026). The online-first date (2025) was not checked.
6. **Preprints.** Connolly2026efficient, Connolly2026local, Ji2026towards, Davies2025preparing, Cashman2025finding, Novikov2025alphaevolve, Georgiev2025mathematical and Bartolucci2021creation are arXiv-only as of 2026-10-26. Re-check for journal versions before submission.
7. **The derivations in Section 3** are my own analysis. They are not claims found in the literature. They are short and, I believe, correct, but should be checked by the author before use.
8. **Search recall.** Google Scholar was not queried directly, and non-English theses were not searched. A 2026 preprint using nonstandard terminology could still be missed.

---

## 9. Search log (2026-10-26)

### WebSearch queries (mode, query, relevant results)

1. standard — `Lee Jeong "Graph-theoretical optimization of fusion-based graph state generation" Quantum` → arXiv:2304.11988; Quantum q-2023-12-20-1212; OptGraphState.
2. standard — `Browne Rudolph "Resource-efficient linear optical quantum computation" Phys. Rev. Lett. 95 010501 arXiv quant-ph/0405157` → quant-ph/0405157.
3. extended — `"distance-hereditary" graph state fusion GHZ minimum number of fusions` → Cashman thesis; 2412.04587; 2506.00292; 2606.02880; 2403.11950. No DH/fusion result.
4. extended — `rank-width graph state generation fusion Bell measurement resource states characterization` → 2405.02414; 2412.04587; 2304.11988; 2601.13381; 2605.09325.
5. standard — `Kumabe Mori Yoshimura complexity of graph-state preparation by Clifford circuits distance-hereditary` → 2402.05874 (Quantum 10, 2165); **2603.23892**.
6. extended — `graph states "rank-width" one GHZ tree fusion "Schmidt-rank width" distance-hereditary photonic` → 0904.3641; 2602.23825; 2603.08847; quant-ph/0602096; 2108.12466; 2609.30400.
7. extended — `minimum number of fusions graph state three-qubit GHZ type-II fusion lower bound n-3 trees optimal 2025 2026 arXiv` → 2412.04587; 2601.13381; 2603.27315; 2601.02087; 2412.18882. No N − 3 statement.
8. extended — `split decomposition graph state fusion Bell measurement "split" marker vertices GHZ star clique totally decomposable` → 2412.00197; 2304.11988; 2403.11950. Nothing new.
9. extended — `"vertex-minor" OR "rank-width" "fusion" graph state photonic resource cost lower bound GHZ "linear optics"` → 2402.06260; 1805.04559; 2506.00292; 2609.30400; 2510.16623; 1508.04718.
10. extended — `tree graph state generation from three-qubit GHZ states fusions "n-2" resource states minimum fusions star graph state "m-2 copies"` → Lee–Jeong (m − 2 copies); 2209.01545; Hilaire 2023.
11. standard — `Patil Guha "Clifford manipulations of stabilizer states" graphical rule book cluster states photonic` → 2312.02377; IEEE TQE 2026.
12. standard — `Zaidi Dawson van Loock Rudolph "Near-deterministic creation of universal cluster states with probabilistic Bell measurements and three-qubit resource states"` → 1410.3753; PRA 91, 042301.
13. extended — `"distance-hereditary" "graph states" fusion network GHZ construction "rank-width one" OR "rank-width 1"` → 1805.05306; 1805.05305; 2603.23892; 2602.23825.
14. extended — `fusion cost graph state cut-rank Schmidt rank Bell measurement tree "rank decomposition" GHZ resource states minimum` → 2609.28241; 0812.4625; 2511.22271. Nothing anticipating.
15. extended — `"type-II fusion" "split decomposition" graph state` → 2508.18375; 2603.23892; 2407.01429; 2604.21475; PRA bf7h-2mk9.
16. extended — `arXiv 2026 fusion-based graph state generation minimum fusions rank-width lower bound characterization GHZ resource` → nothing beyond the above (2605.09325).
17. extended — `Bell pairs type-I fusion graph state construction minimum number of fusions trees star graph states optimal linear optics` → 2508.16505; 2510.16623. No extremal characterization.
18. extended — `language model discovered theorem graph states fusion formalized Lean distance-hereditary 2026` → 2609.03478, 2606.05400, 2609.25199 (unrelated). No competing AI-derived result.
19. standard — `Oum "Rank-width and vertex-minors" pdf distance-hereditary "rank-width at most 1" Bouchet C5 vertex-minor` → 1601.03800; 1403.1081; 1508.04718.
20. standard — `"distance-hereditary" "if and only if" "vertex-minor isomorphic to C5" OR "no C5 vertex-minor" Bouchet 1988 "Transforming trees by successive local complementations"` → 1601.03800 (attribution sentence quoted in Section 6).
21. extended — `"fusions" graph state "3-GHZ" OR "GHZ3" OR "three-photon GHZ" number of qubits "3g" OR "n-2 GHZ" OR "N-3 fusions" counting lower bound connected tree fusion network` → 2409.13541; Gupta QCE'23; 2607.17101. No N − 3 statement.

### Primary-page and full-text checks

**WebFetch (arXiv abstract/HTML):**
2412.04587; 2606.02880; 2602.23825; 2304.11988 (abs + v4 HTML, three passes); quant-ph/0405157; 2405.02414 (abs + v2 HTML, two passes); 2402.05874 (abs + v4 HTML); 2603.23892 (abs + v2 HTML, two passes); 2506.00292; 2412.00197; 2603.08847; 2609.30400; 2601.02087; 1410.3753; 2312.02377; 2101.09310; quant-ph/0307130; quant-ph/0602096; 2508.18375; 1805.05305; 2601.13381; 2511.22271; quant-ph/0608060.

**arXiv API batches:**
- the 21 IDs in `src/arxiv_batch1.txt` and 11 in `src/arxiv_batch2.txt`;
- quant-ph/0604010, quant-ph/0702116, 1508.04718, 1403.1081, 1601.03800, 2504.00291, 2508.16505, 2605.09325, 2510.16623, 2106.13825, 0810.2587, 2409.13541, 2403.11950;
- title searches for 1907.08019, 1907.08024, 1906.05689.

**Crossref + doi.org:**
- 39 DOIs in `src/crossref_batch{1,2,3}.txt`;
- 10.1016/j.dam.2016.08.006, 10.1016/S0195-6698(87)80027-6, 10.22331/q-2020-10-22-348, 10.1063/1.5120591, 10.1103/PhysRevLett.97.150504, 10.1103/PhysRevLett.103.113602, 10.1017/CBO9781139193658.

**Full-text extraction (pdftotext), for quoted statements:**
- Browne–Rudolph; Zaidi et al.; Lee–Jeong v4; Löbl et al. Quantum (v2) and PRA (v3);
- Kumabe et al. v4; Connolly et al. 2603.23892 and 2602.23825;
- Hein–Eisert–Briegel; Van den Nest–Dür–Vidal–Briegel; Van den Nest–Dür–Miyake–Briegel (NJP 2007);
- Oum survey 1601.03800; Adler–Kanté–Kwon 1403.1081; Kanté–Kwon 1508.04718; Dahlberg–Helsen–Wehner 1805.05306;
- Danielsen–Parker; Davies–Jena; Cashman thesis.

**OEIS:**
- A000055: sum over n = 3..9 is 93, confirmed.
- Searches for 1,2,3,8,15,42,104 / 1,1,2,3,8,15,42,104 / 2,3,8,15,42,104 / 0,1,3,11,59,336: no match.

**Version history:** arXiv abstract pages 2402.05874v1 and v2 fetched (curl) to date Kumabe et al.'s rank-width bounds.

**Blocked (HTTP 403):** ScienceDirect (Oum 2005, Hammer–Maffray) and Wiley (Bouchet 1988) landing pages. These were covered via Crossref plus secondary full texts, as noted in Section 8.

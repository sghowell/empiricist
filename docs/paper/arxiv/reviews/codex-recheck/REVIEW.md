**Verdict: minor corrections remain; no blocking or major mathematical error found.** All eight mathematical-review findings are resolved. Seven numbered novelty findings are resolved; the complexity paragraph needs one further scope qualification, and the Hein chapter metadata remains unapplied. Table I reproduces exactly. I worked read-only and modified no files. :codex-file-citation{path="/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.pdf" purpose="source"}

“M” and “N” below refer to the mathematical and novelty reports. Locations refer to the current files.

| Finding | Status | Current text and assessment |
|---|---|---|
| **M1 — Missing size restrictions** | **Resolved** | The abstract now says “graph \(G\) on \(n\ge3\) vertices,” “so for \(n\ge3\),” and “three to nine vertices.” The discovery sample is “three to seven vertices.” The corresponding occurrences in the introduction and body are corrected. [main.tex:40](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:40) |
| **M2 — Overstated computational independence** | **Resolved** | “Independent implementations of fusion and of graph extraction” is followed by “they share the replay of a construction, the graph-level local complementation and the orbit canonicalization.” This accurately describes the implementation boundary. [main.tex:365](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:365) |
| **M3 — Calling open lower bounds tight** | **Resolved** | The corrected output says, for example, “open; search bound F >= 8; rank-width bound F >= 11; combined F >= 11.” The code reserves “attained” and “missed by” for exact values. [rankwidth_check.py:104](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/anc/scripts/rankwidth_check.py:104), [output:74](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/anc/scripts/rankwidth_check.out.txt:74) |
| **M4 — Incorrect supplement count and missing aggregation** | **Resolved** | The README now says “ten exact rows above the minimum, from Tier 1” and documents “Table I as printed,” including the nine later constructions and 25 rank-width improvements. The new aggregation produces that table. [README.md:14](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/anc/README.md:14) |
| **M5 — Invalid checksum manifest** | **Resolved** | This is an artifact correction rather than a prose change: all **50** entries in the current manifest match, including the new script and output. [SHA256SUMS](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/anc/SHA256SUMS) |
| **M6 — Missing algorithm parameters** | **Resolved** | “Decidable in time cubic in the size of the source when its rank-width and the size of the target are bounded,” with the direct Dahlberg–Wehner citation. Both required parameters are present. [main.tex:487](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:487); [primary source](https://arxiv.org/html/1805.05305) |
| **M7 — Global phase in Eq. (1)** | **Resolved** | “It is implemented on graph states, up to a global phase.” This adequately qualifies the displayed equality. [main.tex:150](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:150) |
| **M8 — Reversed implication names** | **Resolved** | The introduction now explicitly identifies “the implication from \(F(G)=n-3\) to distance-hereditary” with the tree-network/width argument, and “the converse” with the constructive arguments. [main.tex:103](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:103) |
| **N1 — Transformation-complexity overstatement** | **Partly resolved; remaining issue minor** | The revised sentence specifies “single-qubit Clifford operations, single-qubit Pauli measurements and classical communication,” supplies both bounded parameters, and separates decision from counting. The original major overstatement is fixed. However, “counting the graph states in a local-complementation orbit is #P-complete” needs a labelled-orbit qualification under this paper’s conventions; see finding R1 below. [main.tex:487](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:487) |
| **N2 — Missing subtraction in Löbl’s bound** | **Resolved** | “At least the linear rank-width minus one” appears in both relevant prose passages; the post-proof comparison gives \(F\ge\mathrm{lrw}(G)-1\). [main.tex:103](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:103), [main.tex:265](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:265), [main.tex:462](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:462). This agrees with [Löbl et al., Eq. (2)](https://arxiv.org/html/2412.04587v3). |
| **N3 — Orbit sizes versus number of orbits** | **Resolved** | “Derive the sizes of the local-equivalence classes of several families of distance-hereditary graphs.” This accurately describes [Connolly–Nishio–Nemoto](https://arxiv.org/abs/2602.23825). [main.tex:483](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:483) |
| **N4 — Conditional Davies–Jena result** | **Resolved** | “Unconditionally for circle graphs and for bounded rank-width and, assuming a structural conjecture of Geelen, by \(O(n\log n)\) for every proper vertex-minor-closed class.” The distinction agrees with [their theorems](https://arxiv.org/html/2504.00291v2). [main.tex:473](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:473) |
| **N5 — Overgeneralized GHZ₃ motivation** | **Resolved** | “A basic resource in several photonic proposals,” now citing Gimeno-Segovia and Zaidi. Bartolucci remains attached to the general FBQC description. The narrowed statement is supported. [main.tex:60](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:60); [Gimeno-Segovia et al.](https://arxiv.org/abs/1410.3720), [Zaidi et al.](https://arxiv.org/abs/1410.3753) |
| **N6 — Connolly publication metadata/category** | **Resolved** | The entry now contains J. Phys. A **59**(39), **395310** (2026), DOI `10.1088/1751-8121/aea45d`, and `primaryClass = {math.CO}`. These match the publisher-deposited record and arXiv. [refs.bib:267](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/refs.bib:267); [Crossref record](https://api.crossref.org/works/10.1088/1751-8121/aea45d), [arXiv](https://arxiv.org/abs/2602.23825) |
| **N7 — Hein chapter metadata** | **Not resolved** | The entry remains `@misc`; the comment still says “volume/pages NOT verified.” The response explicitly records that the correction was not applied. The publisher now supplies the necessary evidence; see R2. [refs.bib:339](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/refs.bib:339) |
| **N8 — Lean LNCS volume** | **Resolved** | `volume = {12699}` has been added and agrees with [Springer’s chapter record](https://link.springer.com/chapter/10.1007/978-3-030-79876-5_37). [refs.bib:626](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/refs.bib:626) |
| **N9 — Global phase** | **Resolved** | The new “up to a global phase” qualification resolves this duplicate of M7. [main.tex:150](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:150) |

The novelty report’s additional citation recommendations were also implemented:

| Recommendation | Current text and result |
|---|---|
| Direct algorithm citation | Dahlberg–Wehner 2018 now accompanies the bounded-parameter statement; covered above. |
| Gioan–Paul beside split decomposition | Added beside “Every node … is a star or a complete graph.” The [primary text](https://arxiv.org/pdf/0810.1823) supports this characterization. [main.tex:284](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:284) |
| Bui-Xuan–Kanté–Limouzy | Added beside “the connected graphs of linear rank-width one.” The claim and new bibliography entry agree with [arXiv:1306.1345](https://arxiv.org/abs/1306.1345). [main.tex:461](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:461) |
| Davies et al. on conjecture formation | “Machine learning has guided mathematicians to conjectures from data” accurately describes [the cited work](https://www.nature.com/articles/s41586-021-04086-x). [main.tex:494](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:494) |
| Adcock on postselectability | “Bound which graph states can be produced from optical resources with postselected fusions” is supported by [the paper](https://arxiv.org/abs/1806.03263). Its bibliography has the dating nit below. [main.tex:478](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:478) |
| Sharma’s GHZ₃ application | “Reduce the GHZ resources and fusions needed for repeater graph states” is supported by [§4 and Appendix D](https://arxiv.org/html/2506.00292v2). [main.tex:477](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:477) |
| More candid novelty framing | “Width-dependent fusion bounds were known before” and “We make the characterization explicit in this resource model” implement the suggested distinction. [main.tex:100](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:100) |

**Remaining and newly identified findings**

1. **R1 — Minor: distinguish labelled complexity problems from the paper’s isomorphism convention.**  
   **Location:** [main.tex:490](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:490), read alongside the definition at [main.tex:158](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:158).

   The paper identifies graphs under both local complementation and isomorphism. The cited #P-completeness theorem counts graphs on a fixed labelled vertex set under local complementation alone. It does not establish the corresponding claim for the number of nonisomorphic representatives. Similarly, the Bell-pair hardness result specifies which qubits must form which pairs. The current wording leaves these distinctions implicit. [Counting paper, definitions and Theorem V.1](https://arxiv.org/html/1907.08024); [Bell-pair paper](https://arxiv.org/abs/1907.08019).

   **Concrete fix:** Replace the relevant clauses with:
   > In general the transformation problem is NP-complete, even for a tensor product of Bell pairs on specified pairs of qubits. Separately, counting labelled graph states in an LC-only orbit, without identifying isomorphic graphs, is #P-complete.

   Retain the bounded-parameter statement and special-target algorithm citations.

2. **R2 — Minor, carried over from N7: published Hein metadata remains omitted.**  
   **Location:** [refs.bib:339](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/refs.bib:339).

   The arXiv citation is valid, but Crossref’s failure to return a record does not settle whether published metadata exists. The **publisher’s own page** lists the six authors, chapter pages **115–218**, book volume **162**, publication year **2006**, and DOI **10.3254/978-1-61499-018-5-115**. [IOS Press record](https://ebooks.iospress.nl/volume/quantum-computers-algorithms-and-chaos).

   **Concrete fix:** Convert to a chapter entry in *Quantum Computers, Algorithms and Chaos*, series *Proceedings of the International School of Physics “Enrico Fermi”*, volume 162, IOS Press, pages 115–218 (2006), with that DOI. Retain `quant-ph/0602096` and update the verification comment.

3. **R3 — Nit: Adcock uses the online-publication year rather than the journal-issue year.**  
   **Location:** [refs.bib:775](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/refs.bib:775).

   The entry combines volume **4**(1), article **015010**, with **2018**. That is a genuine online-publication year—28 November 2018—but the issue is dated **2019**, and the institutional citation uses 2019. The authors, title, DOI and other fields are correct. [Publisher-deposited Crossref record](https://api.crossref.org/works/10.1088/2058-9565/aae950); [authors’ institutional record](https://research-information.bris.ac.uk/en/publications/hard-limits-on-the-postselectability-of-optical-graph-states/).

   **Concrete fix:** Use `year = {2019}` for the journal citation, optionally retaining the 2018 online date in a note. This is a citation-convention correction, not an invalid publication record.

**Computational and mathematical recheck**

`final_table.py` reproduces its saved output exactly, and every cell agrees with Table I in both the TeX and PDF:

| Category | 3 | 4 | 5 | 6 | 7 | 8 | 9 | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Connected orbits | 1 | 2 | 4 | 11 | 26 | 101 | 440 | 585 |
| \(F=n-3\) | 1 | 2 | 3 | 8 | 15 | 42 | 104 | 175 |
| \(F=n\) | 0 | 0 | 1 | 2 | 7 | 6 | 0 | 16 |
| \(F=n+3\) | 0 | 0 | 0 | 1 | 2 | 0 | 0 | 3 |
| Open, \(F\ge n\) | 0 | 0 | 0 | 0 | 0 | 52 | 312 | 364 |
| Open, \(F\ge n+3\) | 0 | 0 | 0 | 0 | 2 | 1 | 24 | 27 |

The nine later constructions match nine distinct tablebase orbits. Their costs equal the corresponding stored lower bounds, and all nine witnesses replay successfully through both engines. Thus the aggregation correctly combines **ten original** and **nine later** exact values above the floor. The 25 rank-width improvements comprise one eight-vertex and 24 nine-vertex orbits.

`rankwidth_check.py` also reproduces its saved output exactly. It correctly reports the three \(F=n+3\) witnesses as rank-width two, missing the bound by three, and the six later eight-vertex witnesses as attaining the bound. Its initial summary concerns the original tablebase; the later constructions are reported separately. That explains its remaining “open” entries before aggregation.

I additionally checked rank-width and linear rank-width using a separate in-memory subset dynamic program on all 585 representatives and the nine later constructions, with agreement throughout. `table_facts.py` and `replay_constructions.py` reproduced their saved outputs, and all 50 manifest hashes verified.

I checked every diff hunk against the current paper and fetched primary sources for the changed literature claims. Apart from the qualifications above, I found no inaccurate revised sentence or mismatched new/changed bibliography entry. The mathematical recheck found no error in the fusion and merge rules, component counting, cycle-rank/Schmidt-rank argument, either direction of the characterization, split-decomposition accounting, or Appendix A’s normal form. In particular,
\[
f_0=n-3+3t,\qquad \operatorname{rw}(G)\le t+1
\]
still give the stated bound, and the split-bag accounting gives exactly \(n-2\) resources and \(n-3\) fusions.

**Whole-paper framing**

I found no remaining substantive overclaim about novelty, Lean, or computational independence. The introduction acknowledges the older ingredients and qualifies its priority statement. Section IV explicitly says that the quantum fusion semantics, rank-width proof, and identification with intrinsic distance heredity are not formalized. The revised machine-mathematics paragraph correctly distinguishes AlphaGeometry’s symbolic engine from AlphaProof’s Lean verification. [AlphaGeometry](https://www.nature.com/articles/s41586-023-06747-5); [AlphaProof](https://www.nature.com/articles/s41586-025-09833-y).

The shared replay, local-complementation and canonicalization code is now disclosed, appropriately limiting what agreement between the engines establishes. This review inspected the Lean source and statements; it did not perform a fresh Lake build or rerun the entire historical search.
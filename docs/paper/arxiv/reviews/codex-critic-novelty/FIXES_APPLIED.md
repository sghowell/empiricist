# Fixes applied: Codex novelty and citation review

Review: `REVIEW.md` in this directory (Codex, gpt-6-astra, maximum reasoning, live web search,
read-only; prompt in `PROMPT.md`). Verdict: no earlier statement of either theorem found; the
characterization has modest novelty (it makes an accessible consequence of existing results explicit),
the general bound is the more substantial new statement; no blocking priority conflict. Every finding was
accepted. New bibliographic data were re-checked against Crossref and arXiv before use.

| # | Finding | Fix |
|---|---|---|
| 1 (major) | The transformation-complexity sentence omitted the restrictions (bounded source rank-width *and* target size), conflated decision and counting, and did not cite Dahlberg-Wehner 2018 | Rewritten (the reviewed text predates the math-review fix): decidable in cubic time when the source's rank-width and the target's size are bounded [Dahlberg2018transforming]; NP-complete in general, already for Bell-pair targets, with more efficient algorithms for particular targets [Dahlberg2020how, Dahlberg2020transforming]; counting the graph states of an orbit is #P-complete [Dahlberg2020counting] |
| 2 | Loebl et al.'s bound is f >= lrw - 1, not f >= lrw | Stated as "at least the linear rank-width minus one" in the introduction and related work, and as F >= lrw(G) - 1 after the proof of Theorem 1 |
| 3 | Connolly-Nishio-Nemoto compute the sizes of equivalence classes, not their number | "derive the sizes of the local-equivalence classes of several families of distance-hereditary graphs" |
| 4 | Davies-Jena's general O(n log n) result is conditional on Geelen's conjecture | Stated: unconditional for circle graphs and bounded rank-width, conditional O(n log n) for every proper vertex-minor-closed class |
| 5 | "The basic resource of photonic proposals" overgeneralizes (Bartolucci et al.'s examples use 4-GHZ and 6-ring resources) | "a basic resource in several photonic proposals", citing Gimeno-Segovia et al. and Zaidi et al.; Bartolucci et al. stays on the general FBQC sentence |
| 6 | `Connolly2026local` is now published; primary category math.CO | Updated to J. Phys. A 59(39), 395310 (2026), DOI 10.1088/1751-8121/aea45d (checked in the Crossref API), primaryClass math.CO |
| 7 | Hein et al. 2006 has chapter metadata | Applied after the recheck: verified on the IOS Press chapter page (vol. 162, pp. 115-218, 2006, DOI 10.3254/978-1-61499-018-5-115); Crossref had returned no record, so it was first left out |
| 8 | Lean citation missing the LNCS volume | volume 12699 added |
| 9 | Eq. (1) holds up to a global phase | Already fixed after the mathematical review |
| Missing | Dahlberg-Wehner 2018; Gioan-Paul beside the split decomposition; Bui-Xuan-Kante-Limouzy (caterpillars = linear rank-width one); Davies et al. 2021 (conjectures from data); Adcock et al. 2018 (postselectability); Sharma et al.'s GHZ3-fusion application | All added; Bui-Xuan et al. (arXiv 1306.1345) and Adcock et al. (QST 4, 015010, Crossref) are new bibliography entries |
| Framing | Suggested novelty formulation | The introduction now says width-dependent fusion bounds were known for caterpillar resources, that both directions can be assembled from older ingredients (Bandelt-Mulder with the fusion rule, or the split-decomposition route), and that the paper makes the characterization explicit in this model and proves the general bound |

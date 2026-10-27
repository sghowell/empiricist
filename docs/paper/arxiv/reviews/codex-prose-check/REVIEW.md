The mathematics is preserved. I found **one substantive wording discrepancy**: the rewrite broadens a claim about what was not found in the literature. One sentence replacement resolves it.

I worked read-only, confirmed that `main.before.tex` matches commit `4a6f983`, and formed my judgment before reading the intermediate prose reviews. This report concerns fidelity, not scientific acceptance or prose style.

**Discrepancy: the novelty claim has become broader.**

Location: Introduction, [rewrite lines 116–118](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:116), corresponding to [original lines 110–112](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/reviews/prose-fidelity/main.before.tex:110).

Original:

> “we have not found either statement, or a classification of minimum fusion counts in this model, in the literature”

Rewrite:

> “We have not found Theorem~\ref{thm:main}, the bound of Theorem~\ref{thm:rw}, or exact minimum fusion counts for this model in the literature.”

**Why it matters:** Not finding a *classification* of minimum counts is narrower than not finding *exact minimum counts*. The rewrite can be read as denying that any individual exact counts were found. The original separately acknowledged minimum-fusion star constructions; the repository’s prior-art report also distinguishes those constructions from the absence of a classification. This finding does not require reopening the literature search: the negative claim itself has become stronger.

**Severity:** Moderate—novelty-scope drift, with no effect on the mathematical results.

**Exact replacement** for the sentence beginning “We have not found”:

```latex
We have not found Theorem~\ref{thm:main}, the bound of Theorem~\ref{thm:rw},
or a classification of minimum fusion counts in this model, in the literature.
```

Retain the following sentence, “We make the characterization explicit …”.

The four intended corrections have the following outcomes.

| Correction | Assessment |
|---|---|
| **(a) Discovery and construction provenance** | **Right and complete; no new inaccuracy found.** The introduction, Sec. VI and acknowledgments consistently distinguish the coding assistant’s initial observation from Fable’s subsequent re-derivation. |
| **(b) Removing the supposed arithmetic error** | **Right and complete; no new inaccuracy.** The original error example was mistaken. |
| **(c) Identifying how the remaining errors were caught** | **Right and complete; no new inaccuracy.** The rewrite distinguishes statement review from the later exact computation. |
| **(d) Content-addressed artifacts** | **The final wording is right and complete, but this repairs an intermediate draft rather than the supplied original.** There is also a distinction between readable claim-file IDs and hashed internal ledger claim IDs. |

For **(a)**, the [July 12 note](/Users/seanhowell/dev/empiricist/docs/science/2026-07-12-p5-tier0-characterization.md:3) identifies the initial hypothesis as Opus-authored and describes mining the full 585-orbit table. The [July 15 note](/Users/seanhowell/dev/empiricist/docs/science/2026-07-15-p5-dh-characterization-fable.md:8) explicitly distinguishes that observation from Fable’s re-derivation, using 44 labeled orbits without the class names. The dates establish the three-day interval; the rewrite’s “then” preserves the chronology without asserting a different interval. The [design-spec author line](/Users/seanhowell/dev/empiricist/docs/superpowers/specs/2026-07-06-empiricist-harness-design.md:3) supplies Opus 4.8.

The [deterministic-search report](/Users/seanhowell/dev/empiricist/docs/science/2026-07-07-p5-tier0-tier1-results.md:13) supports removing “Fable classified the orbits.” The nine later constructions are supported by the campaign history, with one qualification about the supplied source: the July 9 report alone records seven upgrades. The [July 10 cluster result](/Users/seanhowell/dev/empiricist/docs/science/2026-07-10-p5-2d-cluster.md:19) and [September continuation](/Users/seanhowell/dev/empiricist/docs/science/2026-09-07-p5-campaign-under-v1.md:44) account for the remaining two. The rewrite does not incorrectly assign all nine to July 9. The 541 orbits remain correctly described as unseen by Fable, without implying that the initial coding assistant had not seen them.

For **(b)**, I counted the [tablebase](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/anc/data/tablebase.json) directly:

- 585 rows total;
- 185 exact: 175 at \(F=n-3\), plus ten from Tier 1;
- 400 open.

Thus 175/410 partitions the orbits by whether they attain \(n-3\), not by whether their value is exact. Both appended October 26 corrections say this. Removing the purported arithmetic slip, and reducing the error account to two items, is correct.

For **(c)**, [rewrite lines 459–463](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:459) accurately replace the original attribution to “the discipline.” The [family-theorem note](/Users/seanhowell/dev/empiricist/docs/science/2026-07-10-p5-formalized-lower-bound.md:109) records tightening the statement after review. The added explanation about Lean concerns detecting the inadequacy of the statement as a formulation of the intended claim; it does not imply a failure to check its proof. The [rank-width correction](/Users/seanhowell/dev/empiricist/docs/science/2026-07-12-p5-tier0-characterization.md:86) supports the account of exact computation during paper preparation: the six-vertex orbit has rank-width two and linear rank-width three.

For **(d)**, the supplied [original already says](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/reviews/prose-fidelity/main.before.tex:420):

> “Artifacts are addressed by content hash”

The [rewrite](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:440) preserves that distinction and explicitly retains both verifier-code and test-suite hashes. The code confirms that [artifact IDs are content hashes](/Users/seanhowell/dev/empiricist/src/empiricist/ledger/models.py:64), while [claim files accept readable, filename-safe IDs](/Users/seanhowell/dev/empiricist/src/empiricist/claims/model.py:47). However, [internal ledger `Claim.create`](/Users/seanhowell/dev/empiricist/src/empiricist/ledger/models.py:115) also computes a hashed identity. Consequently, “claims have readable names” should not be generalized to every claim representation. The manuscript makes no such generalization and needs no replacement here.

The mathematical comparison produced no discrepancies:

| Material | Result |
|---|---|
| Rank-width theorem and proof | Same hypotheses, bound, gate rearrangement, contraction formula, spanning-tree construction, cut argument and concluding inequalities. |
| Characterization theorem and proof | Same connectedness and \(n\ge3\) restrictions; both implications and all pendant/twin construction steps preserved. |
| Disjoint-fusion lemma and stabilizer calculation | Same measurement convention, disjointness assumption, outcome-dependent Pauli qualification, generator updates and resulting graph. |
| Counting proposition and proof | Same surviving component, qubit identities, cycle rank, lower bound and congruence. The added \(t\ge0\) notation restates the original prose. |
| Lean model theorem and accompanying argument | Same production predicates, equivalence, structural inductions, true-twin identity and over-approximating schedule constructor. |
| Concrete-graph remark | Same pendant-addition counterexample, explicit local-complementation steps, leaf-only limitation and 93/175 count. |
| Clifford-absorption lemma and proof | Same neighbor assumption, Clifford generators, preserved edge, factorization, Pauli and phase qualifications. |
| Normal-form lemma and proof | Same resource/fusion counts, discarded components, fusion ordering, connectivity argument and treatment of carried Clifford gates. |

The **two numbered equations, two unnumbered displays and both table bodies are byte-identical**. All mathematical numbers, ranges and Lean declaration names survive. The numerical changes associated with provenance and removal of the mistaken error example are the intended corrections, not unexplained drift.

The important qualifications also survive: \(n\ge3\); global phase and Pauli byproducts; successful-fusion modeling; the restriction to three-qubit resources; the precise boundary of Lean formalization; the unformalized identification with distance-hereditary graphs; simulator code sharing; conditional versus unconditional cited results; specified Bell-pair labels; and counting labeled graphs without quotienting by isomorphism. “A specialist can readily derive” preserves the original assessment that the characterization is within easy reach of a specialist.

I checked every entry in the three earlier `FIXES_APPLIED.md` files:

- **Mathematical review, items 1–8:** preserved, including the range restrictions, simulator-independence qualification, exact/open reporting, ten-plus-nine accounting, manifest regeneration, bounded-source/bounded-target algorithm conditions, global phase and explicitly named implications.
- **Novelty review, items 1–9, missing citations and framing:** preserved. Löbl’s bound remains linear rank-width **minus one**; Connolly–Nishio–Nemoto still concern class **sizes**; Davies–Jena’s general result remains conditional; the photonic-resource qualification and all bibliographic corrections remain. The new wording discrepancy identified above broadens a separate literature-search claim.
- **Recheck, R1–R3:** preserved, including specified qubit pairs, labeled counting, Hein’s chapter metadata and Adcock’s 2019 issue year.

The relevant ancillary scripts, saved outputs, bibliography source and build script match the accepted commit. All **50 manifest hashes** pass. Both versions cite the same **47 distinct bibliography keys**, and all 47 occur in the rewritten bibliography. Moving related work into the introduction has not reassigned claims to different sources.

Finally, I checked the apparent additions against their counterparts or repository evidence. The abstract’s spanning-tree explanation and explicit \(n\)-to-\(n+3\) improvement come from the original proof and results. The more detailed introductory descriptions of resource models come from the original related-work section with their citations retained. The explicit external identification of the Lean class comes from the original formalization discussion. The revised provenance and error-detection explanations are supported as described above. Apart from the broadened novelty sentence, I found no unsupported new assertion.

**Verdict:** As written, the rewrite is mathematically equivalent but **not fully scientifically equivalent under the requested fidelity standard**, because its literature-search claim is stronger. With the single replacement above, it is scientifically equivalent to the reviewed original, allowing for the verified intended corrections. No other replacements are required.
**I found no new discrepancies. The earlier literature-search discrepancy is resolved.** I checked every changed sentence against `main.checked.tex`, the original `main.before.tex`, and the relevant repository records. No files were modified.

At [Introduction, lines 116–118](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:116), the checked version said:

> “or exact minimum fusion counts for this model”

The current version says:

> “or a classification of minimum fusion counts in this model”

This restores the original scope. “We have not found” remains a qualified account of the literature search, and “either statement” refers to the characterization and the rank-width bound. Combining the two sentences introduces no stronger novelty claim. **The previous moderate discrepancy is closed; no replacement is required.**

The remaining sentence changes have the following outcomes. Locations refer to the current manuscript.

| Location | Change and assessment |
|---|---|
| [Introduction, 157–158](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:157) | “Can readily derive” becomes “could derive … without difficulty.” This preserves the original assessment, “within easy reach of a specialist.” Moving the section reference does not change the discovery account or imply greater difficulty. |
| [Theorem 1 proof, 270–272](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:270) | The partition and crossing-fusion statements are separated into two sentences. Their mathematical content is unchanged; details below. |
| [After Theorem 1, 280–283](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:280) | The sentence is split, and “close in spirit” becomes “related.” This remains a qualitative comparison; it introduces no claim of implication or equivalence between the bounds. The tensor-network attribution, linear-rank-width-minus-one formula, gate-bound attribution, and citations remain intact. |
| [Formal verification, 350–352](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:350) | “Handled” becomes “treated,” and “away from” becomes explicit transformations. Leaf-removal induction, one local complementation from a star to \(K_n\), and three from a double star to \(K_{m,n}\) match the original and Lean files. Reversing the recorded bipartite-to-double-star sequence is valid because local complementation is involutive. |
| [Simulators, 384–386](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:384) | The independence qualification moves after the simulator descriptions. It still concerns **fusion and graph extraction**. The following sentence still identifies the shared replay, graph-level local-complementation, and orbit-canonicalization code. Independence is not overstated. |
| [Tablebase, 389–392](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:389) | Splitting the sentence preserves all 585 rows, orbit representatives, exact values with witnesses versus lower bounds, and storage as one content-addressed file. “Following Ref. … we call it a tablebase” retains the attribution to Löbl et al. |
| [Claim statuses, 436–439](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:436) | The live status ordering, evidence requirement, heuristic ceiling for unsupported model assertions, and permanence of refutation all survive. Calling refuted “separate” agrees with the code’s explicit distinction between terminal refutation and the ordering of live statuses. |
| [Verifier requirements and hashes, 439–441](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:439) | Sentence splitting preserves the requirement to pass the fixed test suite and both verifier hashes: code and test suite. “Hashes of their contents” means the same as “content hashes,” and still refers to artifacts. |
| [Discovery input, 451–453](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:451) | The two sentences preserve the restriction to 44 orbits with \(3\le n\le7\), edge-list representation, labels for attaining \(F=n-3\), absence of invariant or class names, and the local-complementation-invariance hint. These match the July 15 record. |
| [Lean proof development, 458–459](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:458) | The revision loop becomes a past-tense account of revising modules in response to returned proof obligations. This matches the recorded hole-by-hole development and the formalization loop. “Without running Lean itself” remains explicit. |
| [Family-theorem error, 459–461](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:459) | Removing “Two errors were caught during the work” and directly describing statement review preserves the event and its attribution. “Could not detect the error” still concerns a well-typed statement’s failure to express the intended claim, not an unchecked proof. |
| [Rank-width error, 461–462](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:461) | “Found by an exact computation” becomes “computed … exactly and found.” Timing, method, the six-vertex orbit with \(F=9\), and the confusion between rank-width and linear rank-width are unchanged. |

The **proof of Theorem 1 is unchanged in substance**. The sole edit within its proof environment replaces:

> “sets \(X\) and \(Y\), and the surviving qubits into \(A\) and \(B\), and the fusions…”

with:

> “sets \(X\) and \(Y\) and the surviving qubits into \(A\) and \(B\). The fusions…”

I confirmed mechanically that this exact substitution accounts for the entire proof difference. The crossing fusions remain \(e\) together with some of the \(t\) non-tree fusions. Consequently, the product expansion, Schmidt-rank bound \(2^{1+t}\), cut-rank bound \(1+t\), and concluding fusion-cost inequality are identical. The original also separated these two assertions into sentences.

The four intended corrections remain intact:

- **Discovery provenance:** the coding assistant’s initial observation from 585 orbits remains distinct from Fable’s subsequent re-derivation from 44. The introduction, methods, and acknowledgments retain the corrected attribution.
- **Supposed arithmetic error:** the erroneous example remains removed. Directly counting the saved tablebase again gives **185 exact rows—175 at \(n-3\) and ten above it—and 400 open rows**.
- **Error detection:** statement review receives credit for the family-theorem issue; exact computation during paper preparation receives credit for the rank-width correction.
- **Content addressing:** artifacts remain content-addressed, with verifier-code and test-suite hashes explicit. As the earlier review noted, this repairs an intermediate rewrite; the supplied original already described artifacts correctly.

The mechanical comparison also confirms that all inline mathematics, mathematical statement environments, numbered equations, unnumbered displays, table bodies, Lean declaration names, and citation groups are byte-identical to `main.checked.tex`. The other four proof environments are byte-identical. No mathematical number or range changed, no attribution moved to another source, and no substantive hedge or scope restriction was weakened.

**Verdict:** The current `main.tex` is scientifically equivalent to the reviewed original, allowing for the four verified intended corrections. No discrepancies remain, and no replacement text is required.
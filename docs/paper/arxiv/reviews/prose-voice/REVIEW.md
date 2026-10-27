The mathematical exposition generally reads like a specialist preprint. The clearest departures from your preferred voice occur in the repeated verification narrative and passages that sound like a software development report.

I read only [main.tex](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex) and made no changes. Quotations below omit citation commands and render cross-references normally.

1. consider. Abstract, “Both directions of this characterization…”

   > Both directions of this characterization can be assembled from published results on Schmidt-rank width and split decompositions, but we have not found it stated, and the graph-theoretic core of its constructive direction is verified in Lean 4.

   The sentence joins a relationship to previous work, a qualified novelty claim, and a verification statement. The accumulation sounds defensive, although the individual qualifications are reasonable.

   Rewrite: “Published results on Schmidt-rank width and split decompositions yield both directions of this characterization, which we have not found stated in the literature. We verified the graph-theoretic core of its constructive direction in Lean 4.”

2. consider. Introduction, “The characterization was first conjectured…”

   > The characterization was first conjectured by a language model from the labeled orbits with \(3\le n\le 7\), within an automated system that accepts a claim only after machine verification, and the same model wrote the Lean proofs.

   The embedded assurance about verification interrupts the account of how the conjecture arose. Similar assurances recur in Computational methods and the Acknowledgments. Here, “only” expresses a substantive restriction; the problem is the sentence’s construction and cumulative effect.

   Rewrite: “A language model first conjectured the characterization from the labeled orbits with \(3\le n\le 7\) and wrote the Lean proofs. It worked within an automated system that requires machine verification before accepting a claim.”

3. consider. Introduction, “Given the results cited above…”

   > Given the results cited above, the characterization is within reach of standard techniques, and we describe how it was found in Sec. VI.

   “Within reach of standard techniques” is an indirect appraisal of the result’s difficulty. Following the detailed account of its relationship to previous work, it sounds like another qualification of the paper’s contribution.

   Rewrite: “The characterization can be derived from the cited results by standard techniques. We describe how we found it in Sec. VI.”

4. should fix. Graph states and fusions, “We therefore treat fusions…”

   > We therefore treat fusions as deterministic and leave the probabilistic success of linear-optical fusion to a layer above the present problem.

   “A layer above the present problem” imports software-architecture language and leaves the scope of the model unnecessarily abstract.

   Rewrite: “We therefore treat fusions as deterministic. The present model does not include the probabilistic success of linear-optical fusion.”

5. should fix. Formal verification, “Before the general theorem…”

   > Before the general theorem, the development proves constructions at the minimum for several families, each stated together with the general lower bound so that no family theorem can hold vacuously.

   “The development proves constructions” is awkward, and the ending advertises protection against a defective theorem statement. State what the family theorems establish directly.

   Rewrite: “Before the general theorem, we prove constructions attaining the minimum for several families. Each family theorem states the general lower bound and gives a construction attaining it.”

6. consider. Formal verification, remark beginning “Although every statement…,” sentence “The graphs \(P_3\) and \(K_3\)…”

   > The graphs \(P_3\) and \(K_3\) are \(\mathrm{LC}\)-equivalent, yet a pendant at the center of \(P_3\) gives the four-vertex star, while a pendant at a vertex of \(K_3\) gives the paw, which is \(\mathrm{LC}\)-equivalent to the path \(P_4\) and not to the star.

   The ending uses the positive–negative contrast form covered by your rule. The distinction is mathematically necessary; the concern is its phrasing. The sentence also stacks “yet,” “while,” and “and not.”

   Rewrite: “The graphs \(P_3\) and \(K_3\) are \(\mathrm{LC}\)-equivalent. Adding a pendant at the center of \(P_3\) gives the four-vertex star; adding one at a vertex of \(K_3\) gives the paw. The paw is \(\mathrm{LC}\)-equivalent to \(P_4\) and lies in a different \(\mathrm{LC}\) class from the star.”

7. should fix. Minimum fusion counts for small graphs, “No orbit changed.”

   > No orbit changed.

   This is test-log shorthand. The intended statement concerns the results of the searches with additional Clifford choices; the orbits themselves are fixed mathematical objects.

   Rewrite: “The additional Clifford choices left the set of reachable orbits unchanged.”

8. consider. Minimum fusion counts for small graphs, “The resulting table has…”

   > The resulting table has one row for each of the \(585\) orbits, with an orbit representative and either an exact value with a witness schedule or a lower bound, and it is stored as a single content-addressed file.

   The sentence mixes the mathematical contents of the table with a storage detail. “Content-addressed” also assumes familiarity with software terminology.

   Rewrite: “The table contains one row for each of the \(585\) orbits, giving an orbit representative and either an exact value with a witness schedule or a lower bound. We store it in a single file identified by a hash of its contents.”

9. consider. Minimum fusion counts for small graphs, “Table I summarizes…”

   > Table I summarizes the results. An independent pendant-and-twin elimination on all \(585\) representatives confirms that the orbits with \(\mathrm{F}=n-3\) are exactly the distance-hereditary ones.

   The opening is generic signposting immediately after the table. The reference can be incorporated into the substantive sentence.

   Rewrite: “An independent pendant-and-twin elimination on all \(585\) representatives in Table I confirms that the orbits with \(\mathrm{F}=n-3\) are exactly the distance-hereditary ones.”

10. consider. Minimum fusion counts for small graphs, “The bound improves the table…”

    > The bound improves the table for \(25\) open orbits, one with \(n=8\) and \(24\) with \(n=9\), which have rank-width three and hence \(\mathrm{F}\ge n+3\), whereas the search had established only \(\mathrm{F}\ge n\).

    “Improves the table” sounds like a project update. The improvement concerns the lower bounds, which can be named directly. “Only” has a legitimate comparative function here.

    Rewrite: “For \(25\) open orbits of rank-width three, one with \(n=8\) and \(24\) with \(n=9\), the theorem strengthens the search bound \(\mathrm{F}\ge n\) to \(\mathrm{F}\ge n+3\).”

11. should fix. Computational methods, “Each proposal is recorded…”

    > Each proposal is recorded with a status that can rise only when a verifier accepts it, a claim supported only by the model's assertion stays at the lowest status, and a refuted claim remains refuted.

    This has the three-clause cadence of a declaration of safeguards. “A refuted claim remains refuted” sounds tautological until its meaning as a permanent status is made explicit. The restrictions themselves are substantive and should remain.

    Rewrite: “We record a status for each proposal and require verifier acceptance before raising it. Claims supported solely by model assertions retain the lowest status, and refutation is permanent.”

12. should fix. Computational methods, “These checks caught several errors…”

    > These checks caught several errors during the work, among them an arithmetic slip in an early hand-written count of the extremal orbits (\(185/400\) instead of \(175/410\)), a family theorem whose first statement had its construction built into the claim, and, while this paper was being prepared, a note that reported the linear rank-width of the six-vertex orbit with \(\mathrm{F}=9\) as its rank-width.

    “Instead of” directly violates your stated rule, although this is an ordinary factual correction. The nested drafting chronology and long catalogue of caught errors also give the sentence an audit-report character.

    Rewrite: “The errors detected by these checks included an arithmetic slip in an early handwritten count of the extremal orbits (\(185/400\), with \(175/410\) the correct counts) and a family theorem whose first statement had its construction built into the claim. During preparation of this paper, the checks also detected a note that reported the linear rank-width of the six-vertex orbit with \(\mathrm{F}=9\) as its rank-width.”

13. consider. Discussion, “The combinatorial part of the constructive direction…”

    > The combinatorial part of the constructive direction of Theorem 2 is verified in Lean, while the steps that involve quantum states, Lemma 3 and the proof of Theorem 1, are written proofs supported by the two simulators and by the exhaustive search.

    The scope of formal verification has already been stated in Sec. IV and discussed in the Introduction. Repeating it as a certification statement contributes to the defensive cadence. There is also an awkward grammatical equation between “steps” and “written proofs.”

    Rewrite: “We verified the combinatorial part of the constructive direction of Theorem 2 in Lean. For the steps involving quantum states, Lemma 3 and the proof of Theorem 1, we give written proofs supported by the two simulators and the exhaustive search.”

14. consider. Discussion, “Several questions remain open.”

    > Several questions remain open. The data of Sec. V show that \(\mathrm{F}\) is not a function of rank-width beyond rank-width one, and it would be interesting to find the invariant that separates \(\mathrm{F}=n\) from \(\mathrm{F}=n+3\) among graphs of rank-width two.

    The generic opener is followed by the familiar evaluative phrase “it would be interesting.” Naming the question directly gives the paragraph more purpose.

    Rewrite: “The data of Sec. V show that \(\mathrm{F}\) is not a function of rank-width beyond rank-width one. Among the open questions is which invariant separates \(\mathrm{F}=n\) from \(\mathrm{F}=n+3\) for graphs of rank-width two.”

15. consider. Discussion, “Theorem 2 makes the decision problem…”

    > Theorem 2 makes the decision problem \(\mathrm{F}(G)=n-3\) polynomial, since distance-hereditary graphs are recognized by pendant-and-twin elimination, but the complexity of computing \(\mathrm{F}\) in general is open.

    “Makes the decision problem … polynomial” is compressed and slightly conversational. Specifying polynomial time gives it the register expected in a technical paper without changing the claim.

    Rewrite: “Theorem 2 gives a polynomial-time test for \(\mathrm{F}(G)=n-3\), using pendant-and-twin elimination to recognize distance-hereditary graphs. The complexity of computing \(\mathrm{F}\) in general remains open.”

16. should fix. Discussion, “It is also natural to ask…”

    > It is also natural to ask whether analogous characterizations hold for larger GHZ states or for linear cluster states as resources.

    This is one of the stock phrases you explicitly want to avoid. The adjective supplies no information about the question.

    Rewrite: “We also ask whether analogous characterizations hold for larger GHZ states or linear cluster states as resources.”

17. consider. Data and code availability, “The ancillary files of this paper…”

    > The ancillary files of this paper contain the Lean modules behind every declaration in Table II, as a self-contained Lake project with a script that builds them and prints their axioms, as well as the table, the nine later constructions, and scripts that recompute every number in Sec. V, including the exact rank-widths, replay the constructions with both simulators, and repeat Tier 1 with single-qubit Cliffords on the fused qubits.

    This is an overloaded inventory sentence. The nested “as,” “with,” “as well as,” and “including” phrases make the relationships between the files and scripts difficult to follow. The technical terminology is appropriate in this section; the problem is the packaging.

    Rewrite: “The ancillary files contain a self-contained Lake project with the Lean modules for all declarations in Table II and a script that builds the modules and prints their axioms. They also include the table and the nine later constructions. The accompanying scripts recompute all numbers in Sec. V, including the exact rank-widths, replay the constructions with both simulators, and repeat Tier 1 with single-qubit Cliffords on the fused qubits.”

18. should fix. Acknowledgments, “Codex (OpenAI, model gpt-6-astra)…”

    > Codex (OpenAI, model gpt-6-astra) independently checked the proofs, the claims and the relation to previous work, and confirmed that a later rewording of the text did not change its content; the errors it found have been corrected.

    The sentence combines attribution with an editorial audit and ends with an assurance that the audit’s findings were resolved. That ending is particularly characteristic of an agent’s completion report. The same information can be stated more plainly.

    Rewrite: “Codex (OpenAI, model gpt-6-astra) independently checked the proofs, claims and relation to previous work. It also confirmed that a later rewording preserved the content. We corrected the errors it found.”

19. consider. Acknowledgments, “This work was carried out…” and “I chose the problem…”

    > This work was carried out with AI systems working under my direction.

    > I chose the problem and take full responsibility for the content of this paper.

    These switch from the paper’s “we” to “my” and “I.” Singular attribution is normal in a single-author acknowledgment, so this is a consistency issue under your stated convention, not a machine-writing tell.

    Rewrite: “We carried out this work with AI systems under our direction.” And: “We chose the problem and accept responsibility for the paper’s entire content.”

I found no prose bullet lists, rhetorical bold or italic run-in labels outside the standard theorem/proof apparatus, colon reveals, em-dash asides, or clear British spellings. Most occurrences of “exactly,” “only,” and “every” express mathematical or procedural restrictions. The repeated “Fusing with…” openings distinguish three concrete cases, and the sequential signposting in the appendix follows the proof’s operations; neither needs artificial variation.

Overall, the definitions, proofs, and interpretation of the results largely sound like an experienced physicist’s preprint. The machine-like effect is concentrated in the repeated account of verification and correction, together with occasional software-report phrasing. Those passages need the most editing to produce a consistently natural Physical Review A voice.
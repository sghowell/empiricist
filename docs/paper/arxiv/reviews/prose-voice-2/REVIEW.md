I read only `main.tex` and made no changes. I found no bullet lists, prohibited contrast constructions, prose colon reveals, em-dash asides, or American-spelling problems. The three-part lists generally enumerate actual mathematical cases or procedures. Most occurrences of “exactly,” “only,” and “every” have substantive mathematical or methodological meanings.

The concerns are concentrated in the discussion of verification and the automated workflow.

1. should fix. Throughout the theorem, proof, and remark environments; for example, Theorem 1, “For every connected graph” ([source](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:82)).

   > For every connected graph \(G\) on \(n\ge 3\) vertices, \(F(G)\ge n+3\,\mathrm{rw}(G)-6\).

   The `amsthm` environments introduce bold or italic run-in labels. This conflicts with the literal formatting rule you supplied, although it is conventional mathematical typography and carries no implication of machine authorship.

   Retain the sentence verbatim, with “Theorem 1 (Rank-width bound)” set separately in plain roman type. Apply the same treatment to the other theorem, proof, and remark labels.

2. consider. Abstract, “For 25 orbits” ([source](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:52)).

   > For 25 orbits of rank-width three whose minimum is not known, the bound raises the lower bound from \(n\) to \(n+3\).

   “The bound raises the lower bound” is an awkward repetition in an otherwise direct abstract.

   Rewrite: “For 25 orbits of rank-width three whose minimum is not known, we improve the lower bound from \(n\) to \(n+3\).”

3. consider. Introduction, “The present work” ([source](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:117)).

   > The present work makes the characterization explicit for this resource model and adds the more general bound.

   This is a generic contribution-summary sentence after the contributions have already been described. “The present work” also shifts away from the requested “we” voice. The sentence is ordinary academic boilerplate, so this is a modest concern.

   Rewrite: “We make the characterization explicit for this resource model and establish the more general bound.”

4. should fix. Introduction, “Given the results cited above” ([source](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:155)).

   > Given the results cited above, the characterization is within easy reach of a specialist, and we report how it was found in Sec. VI as an example of a correct and checkable conjecture produced from data by such a system.

   The sentence combines anticipatory self-deprecation with an assurance of correctness. “Within easy reach of a specialist” manages the reader’s assessment of novelty, while “correct and checkable” evaluates the work on the reader’s behalf. This is the clearest instance of defensive meta-commentary.

   Rewrite: “A specialist can readily derive the characterization from the cited results. In Sec. VI we describe its discovery as an example of a conjecture inferred from data by the automated system and subsequently verified.”

5. consider. Graph states and fusions, “A counting form of the bound” ([source](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:238)).

   > A counting form of the bound, in a merge model of schedules that also tracks fusions which split or consume a component, is the Lean theorem `fusion_cost_lower_bound`.

   The long interruption separates the subject from an awkward predicate: a “form of the bound” *is* a software declaration. It reads like documentation attached to the mathematics.

   Rewrite: “The Lean theorem `fusion_cost_lower_bound` proves a counting version of this bound in a merge model of schedules that also tracks fusions which split or consume a component.”

6. should fix. Formal verification, “Each family theorem” ([source](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:349)).

   > Each family theorem states the general lower bound together with a construction that attains it, so that none of them can hold vacuously.

   The final clause reassures the reader that the results avoid a basic logical defect. Its intended mathematical point is better expressed positively as an existence statement.

   Rewrite: “For each family, we prove the general lower bound and the existence of a construction attaining it.”

7. should fix. Computational methods, “Each claim is recorded” and “Nothing the model merely asserts” ([source](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:437)).

   > Each claim is recorded with one of the statuses refuted, heuristic, conjectured, verified up to a given size, certified and formalized, listed in increasing order, and its status rises only when a verifier accepts the evidence for it. Nothing the model merely asserts is recorded above heuristic, and refutation is permanent.

   The first sentence is overloaded with administrative detail. The second changes from describing a procedure to proclaiming epistemic discipline, particularly through “Nothing” and “merely asserts.” The underlying rules can remain explicit without that defensive tone.

   Rewrite: “We record each claim as refuted, heuristic, conjectured, verified up to a given size, certified, or formalized, in increasing order of status. A claim can advance only after a verifier accepts supporting evidence. Model assertions without such evidence receive at most heuristic status, and refuted claims retain that status.”

8. consider. Computational methods, “This checker was hardened” ([source](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:447)).

   > This checker was hardened against adversarial submissions, including tampered compiled files, substitution of files between checking and use, and elaborators that hide axioms, before it was used.

   “Hardened against adversarial submissions” has the register of a software security report. The technical details are concrete and relevant to the described method; the three examples are not a rhetorical tricolon. A direct account of the action would fit the surrounding paper better.

   Rewrite: “Before using the checker, we modified it to protect against adversarial submissions, including tampered compiled files, substitution of files between checking and use, and elaborators that conceal axioms.”

9. consider. Computational methods, “While this paper was being prepared” ([source](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:462)).

   > While this paper was being prepared, a note was found to give the linear rank-width of the six-vertex orbit with \(F=9\) as its rank-width.

   The two passive constructions make this sound like an incident report. “A note was found to give” is particularly indirect. The requested authorial voice makes the account more natural without changing the correction being reported.

   Rewrite: “During preparation of this paper, we found a note that reported the linear rank-width of the six-vertex orbit with \(F=9\) as its rank-width.”

10. consider. Discussion, “The combinatorial part” ([source](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:471)).

    > The combinatorial part of the constructive direction of Theorem 2 is verified in Lean. The steps that involve quantum states, Lemma 3 and the proof of Theorem 1, rest on written proofs, which are supported by the two simulators and by the exhaustive search. Formalizing these steps would require definitions of graph states, Pauli measurements and schedules in Lean, and rank-width is not yet available in `mathlib`.

    The opening repeats the verification boundary already explained in Formal verification. “Rest on written proofs, which are supported by…” adds another layer of assurance. A discussion can reasonably revisit this boundary, but organizing the paragraph around the remaining formalization work would make the repetition more purposeful.

    Rewrite: “Extending the Lean verification of the combinatorial construction in Theorem 2 to the quantum-state arguments in Lemma 3 and Theorem 1 would require definitions of graph states, Pauli measurements and schedules; rank-width is not yet available in `mathlib`. We give written proofs of these quantum-state arguments, supported by the two simulators and the exhaustive search.”

11. should fix. Acknowledgments, “This work was carried out” and “I chose the problem” ([source](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:496)).

    > This work was carried out with AI systems working under my direction.

    > I chose the problem and take full responsibility for the content of this paper.

    These sentences switch from the paper’s “we” voice to “my” and “I.” Singular first person is natural in a single-author acknowledgment, but it conflicts with your stated voice rule. The first sentence also repeats “work” and “working.”

    Rewrite: “We directed the AI systems used to carry out this work.”

    Rewrite: “We chose the problem and take full responsibility for the content of this paper.”

12. consider. Acknowledgments, “Codex (OpenAI” ([source](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:500)).

    > Codex (OpenAI, model gpt-6-astra) independently checked the proofs, the claims and the relation to previous work, and the errors it found were corrected.

    The passive closing assurance repeats the error-correction narrative from Computational methods. Making the author responsible for the action produces a more direct disclosure while preserving both the independent check and the corrections.

    Rewrite: “We corrected the errors identified by Codex (OpenAI, model gpt-6-astra) during its independent checks of the proofs, the claims and the relation to previous work.”

The mathematical exposition largely reads like a conventional PRA preprint: restrained, specific, and logically connected. The strongest machine-written impression comes from the repeated assurances surrounding verification, nonvacuity, and error correction. Those passages intermittently give the paper the voice of a software validation report; the definitions and proofs show much less of that tendency.
I read only `docs/paper/arxiv/main.tex`. The paper largely satisfies your explicit rules: I found no bullet lists, bold or italic run-in labels, prohibited contrast constructions, colon reveals, em-dash asides, or American-spelling problems. The mathematical uses of “exactly,” “only,” and “every” generally carry real information. The technical enumerations and sequential signposting in the proofs are also appropriate.

The concerns below are mainly about register, repetition, and sentence construction. Quotations normalize LaTeX notation; `[citation]` denotes an existing citation that should be retained.

1. **consider — Introduction, [“We have not found…”](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:116)**

   > We have not found Theorem 2, the bound of Theorem 1, or exact minimum fusion counts for this model in the literature. We make the characterization explicit for this resource model and prove the more general bound.

   The second sentence restates the announced contribution. Following the discussion of what can be assembled from published results, this produces a slightly defensive account of novelty. The qualification about the literature is legitimate; the repetition is the concern.

   Rewrite:

   > For this resource model, we establish the characterization of Theorem 2 and prove the more general bound of Theorem 1; we have not found either statement or exact minimum fusion counts in the literature.

2. **should fix — Introduction, [“A specialist can readily…”](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:157)**

   > A specialist can readily derive the characterization from the results cited above, and we describe how it was found in Sec. VI.

   “Readily” is an evaluative emphasis word. The appeal to what a specialist can do sounds self-conscious and defensive, particularly after the preceding discussion of the result’s relationship to published work. The sentence also joins an assessment of difficulty to a navigation instruction.

   Rewrite:

   > The characterization follows from the cited results. We describe how we found it in Sec. VI.

3. **consider — The rank-width bound and the characterization, [“Removing \(e\) splits…”](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:270)**

   > Removing \(e\) splits the resources of \(H_0\) into two sets \(X\) and \(Y\), and the surviving qubits into \(A\) and \(B\), and the fusions joining \(X\) and \(Y\) are \(e\) together with some of the \(t\) fusions outside \(S\).

   The repeated “and” gives the sentence an accumulated, clause-by-clause rhythm. Separating the partition from the description of the crossing fusions makes the argument easier to follow.

   Rewrite:

   > Removing \(e\) splits the resources of \(H_0\) into sets \(X\) and \(Y\), with surviving qubits \(A\) and \(B\), respectively. The fusions joining \(X\) and \(Y\) consist of \(e\) and some of the \(t\) fusions outside \(S\).

4. **consider — The rank-width bound and the characterization, [“The argument is the fusion analogue…”](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:280)**

   > The argument is the fusion analogue of bounding the Schmidt-rank width of a tensor network by its bond structure [citations], and it is close in spirit to the bound \(F\ge\mathrm{lrw}(G)-1\) in terms of the linear rank-width in Ref. [citation] and to the gate bound of Ref. [citation].

   “Close in spirit” is a vague, conversational comparison. The sentence also carries several relationships in one long coordination. These are modest stylistic concerns, not evidence that the comparison itself is inappropriate.

   Rewrite:

   > We bound Schmidt-rank width using the bond structure of the fusion network, as in the corresponding tensor-network arguments [citations]. This argument is related to the linear-rank-width bound \(F\ge\mathrm{lrw}(G)-1\) of Ref. [citation] and the gate bound of Ref. [citation].

5. **consider — Formal verification, [“Paths, stars and all trees…”](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:350)**

   > Paths, stars and all trees are handled by induction on the removal of leaves, \(K_n\) is one local complementation away from a star, and \(K_{m,n}\) is three local complementations away from a double star.

   “Are handled” has the register of an implementation report, while the repeated “away from” is conversational. The three cases are substantive mathematical cases, so I would not classify this as a rhetorical tricolon.

   Rewrite:

   > We prove the results for paths, stars and general trees by induction using leaf removal. One local complementation transforms a star into \(K_n\), and three transform a double star into \(K_{m,n}\).

6. **consider — Minimum fusion counts for small graphs, [“Each recorded construction is replayed…”](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:384)**

   > Each recorded construction is replayed by two stabilizer simulators with independent implementations of fusion and of graph extraction, a tableau simulator built on STIM [citation] and an implementation over \(\mathrm{GF}(2)\).

   The long apposition arrives after an already substantial description of the simulators. It reads like an implementation inventory. Splitting the sentence also makes the precise scope of independence easier to see.

   Rewrite:

   > We replay each recorded construction with two stabilizer simulators. One is a tableau simulator built on STIM [citation], and the other operates over \(\mathrm{GF}(2)\); their implementations of fusion and graph extraction are independent.

7. **consider — Minimum fusion counts for small graphs, [“The resulting table…”](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:389)**

   > The resulting table, a tablebase in the terminology of Ref. [citation], has one row for each of the \(585\) orbits, with an orbit representative and either an exact value with a witness schedule or a lower bound, and it is stored as a single file identified by a hash of its contents.

   Terminology, table structure, evidential contents, and file storage accumulate in one sentence. This is a recurring source of the software-report cadence: a scientific statement acquires successive implementation qualifications.

   Rewrite:

   > We record each of the \(585\) orbits in one row, giving a representative and either an exact value with a witness schedule or a lower bound. The resulting tablebase, in the terminology of Ref. [citation], is stored as a single file identified by a hash of its contents.

8. **consider — Computational methods, [“It records each claim…”](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:436)**

   > It records each claim as heuristic, conjectured, verified up to a given size, certified or formalized, in increasing order of strength, or as refuted, and a claim advances only when a verifier accepts evidence for it. A claim supported only by the model’s assertion is recorded at most as heuristic, and the status refuted is permanent.

   The nested status list and “a claim advances” sound like a software specification. Together with the introduction’s assurance that claims require machine verification, the passage contributes to a repeated account of the system’s trustworthiness. The restrictions themselves are substantive; “only” is not merely an intensifier here.

   Rewrite:

   > The system records claims as heuristic, conjectured, verified up to a given size, certified or formalized, in increasing order of strength; refuted is a separate status. A stronger status requires a verifier to accept supporting evidence. A model assertion alone supports at most heuristic status, and the refuted status is permanent.

9. **should fix — Computational methods, [“Each verifier must pass…”](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:439)**

   > Each verifier must pass a fixed suite of test cases before use, and artifacts and verifiers are identified by content hashes, a verifier by the hashes of its code and of its test suite.

   The final phrase is an awkward explanatory appendage. The sentence combines a testing requirement with an identification convention and then partially restates the latter. This is conspicuously less polished than the mathematical exposition.

   Rewrite:

   > Before use, each verifier must pass a fixed suite of test cases. Artifacts are identified by content hashes, and each verifier is identified by the hashes of its code and test suite.

10. **consider — Computational methods, [“Working within the system…”](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:451)**

    > Working within the system, the model was then given only the \(44\) orbits with \(3\le n\le 7\) as edge lists, each marked according to whether it attains \(F=n-3\), with no invariant or class name and with only the information that the property is invariant under local complementation.

    The successive qualifications—“as,” “each,” “with,” and “with only”—make this sound like a prompt specification transcribed into prose. The input restrictions matter and should remain, but they can be stated in connected sentences.

    Rewrite:

    > Within the system, we then gave the model only the \(44\) orbits with \(3\le n\le 7\), represented as edge lists and labeled by whether they attain \(F=n-3\). We supplied no invariant or class name; the sole additional information was that the property is invariant under local complementation.

11. **consider — Computational methods, [“The model then wrote…”](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:457)**

    > The model then wrote the Lean proofs in a loop in which the checker returns the remaining proof obligations and the model revises the module, without running Lean itself.

    “In a loop in which” is cumbersome, and the sentence shifts from past-tense narration to present-tense process description. The final qualification is also distant from its subject.

    Rewrite:

    > The model then wrote the Lean proofs by revising the module in response to the remaining proof obligations returned by the checker. It did not run Lean itself.

12. **consider — Computational methods, [“Two errors were caught…”](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:459)**

    > Two errors were caught during the work. The first statement of a family theorem had its construction built into the claim. Such a statement is well typed, so the Lean checker cannot detect it, and it was caught when the statement was reviewed. While preparing this paper, we found by an exact computation of rank-widths that a note had given the linear rank-width of the six-vertex orbit with \(F=9\) as its rank-width.

    The opening announces an error inventory before supplying it, and “caught” is repeated. “Cannot detect it” has an awkward antecedent: the checker cannot detect the error, although the nearest noun is the statement. Reporting the events directly would reduce the quality-control-report tone.

    Rewrite:

    > Review of the initial statement of a family theorem revealed that it included the construction in the claim. Because the statement was well typed, the Lean checker could not detect the error. While preparing the paper, we computed the rank-widths exactly and found that a note had reported the linear rank-width of the six-vertex orbit with \(F=9\) as its rank-width.

13. **should fix — Acknowledgments, [“This work was carried out…”](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:495) and [“I chose the problem…”](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:503)**

    > This work was carried out with AI systems working under my direction.

    > I chose the problem and take full responsibility for the content of this paper.

    “My” and “I” depart from your specified “we” voice. The opening also repeats “work/working” in a passive construction. A responsibility statement is conventional in an AI disclosure; its presence is not itself a machine-writing tell.

    Rewrites:

    > We carried out this work using AI systems under our direction.

    > We chose the problem and take responsibility for the content of this paper.

14. **consider — Acknowledgments, [“Codex (OpenAI…”](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:502)**

    > Codex (OpenAI, model gpt-6-astra) independently checked the proofs, the claims and the relation to previous work; the errors it found have been corrected.

    The passive closing clause reads as a general assurance of correctness. This effect is stronger because the methods section has already narrated error detection and correction. Keeping the disclosure while naming the authors’ action gives it a more direct voice.

    Rewrite:

    > Codex (OpenAI, model gpt-6-astra) independently checked the proofs, the claims and the relation to previous work. We corrected the errors it found.

Overall, the mathematical exposition reads like a conventional, professionally written preprint. The strongest machine-like residue is the repeated narration of verification and error correction, accompanied by some overloaded methods sentences. The paper needs local editing for register and rhythm, rather than a wholesale change of voice.
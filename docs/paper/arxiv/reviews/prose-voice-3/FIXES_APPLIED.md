# Fixes applied: third Codex voice review (cold read)

Review: `REVIEW.md` in this directory (Codex, gpt-6-astra, read-only; the prompt is the first
round's, copied to `PROMPT.md`). It read only the final `main.tex`. Verdict: "the mathematical
exposition reads like a conventional, professionally written preprint", and "the paper needs local
editing for register and rhythm, rather than a wholesale change of voice". The remaining residue is
in the narration of verification and in overloaded methods sentences. Fourteen items were raised, three
of them "should fix" (2, 9, 13). These fixes were applied together with the one discrepancy found by
the Codex equivalence check (`../codex-prose-check/`), and a second equivalence check covers this
round's edits.

| # | Item | Fix |
|---|---|---|
| 1 | Novelty restated in two sentences | One sentence, which also restores the original scope that the equivalence check asked for: "We make the characterization explicit for this resource model and prove the more general bound of Theorem 1, and we have not found either statement, or a classification of minimum fusion counts in this model, in the literature." |
| 2 | "A specialist can readily derive": an emphasis word in a self-conscious assessment | "A specialist could derive the characterization from the results cited above without difficulty, and Sec. VI describes how it was found." The equivalence check confirmed that this assessment is the original's and must stay, so the suggested "follows from the cited results" was not used |
| 3 | A run-on "and ... and" sentence in the proof of Theorem 1 | Split into two sentences, with the same mathematics |
| 4 | "close in spirit" | "It is related to the bound ... and to the gate bound of ..." |
| 5 | "are handled", "away from" | "Paths, stars and all trees are treated by induction on the removal of leaves. One local complementation turns a star into K_n, and three local complementations turn a double star into K_{m,n}." |
| 6 | Long apposition on the simulators | "...two stabilizer simulators, a tableau simulator built on stim and an implementation over GF(2), whose implementations of fusion and of graph extraction are independent." |
| 7 | Terminology, contents and storage piled into one sentence | Two sentences, with "Following Ref. [Lobl2025generating] we call it a tablebase" |
| 8 | The status list reads like a specification | "...or as refuted, which is a separate and permanent status. A claim reaches a stronger status only when a verifier accepts evidence for it, and an assertion of the model alone supports at most the status heuristic." |
| 9 | Awkward appendage on the hashes | "Each verifier must pass a fixed suite of test cases before use. Artifacts are identified by hashes of their contents, and each verifier by the hashes of its code and of its test suite." |
| 10 | The model's input reads like a transcribed prompt specification | "...the 44 orbits with 3 <= n <= 7, as edge lists labeled by whether they attain F=n-3. Its prompt named no invariant or class and said only that the property is invariant under local complementation." |
| 11 | "in a loop in which" and a tense shift | "The model then wrote the Lean proofs, revising each module in response to the remaining proof obligations returned by the checker, without running Lean itself." |
| 12 | The error inventory is announced before it is given; "cannot detect it" has an unclear antecedent | "A review of the first statement of a family theorem found that it had its construction built into the claim. Such a statement is well typed, so the Lean checker could not detect the error. While preparing this paper, we computed the rank-widths exactly and found that a note had given..." |
| 13 | "I" and "my" in the acknowledgments | Not changed. This is the author's template in his other papers |
| 14 | Passive closing clause in the Codex sentence | Not changed. This is the author's template wording |

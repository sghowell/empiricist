# Fixes applied: Codex voice review (cold read)

Review: `REVIEW.md` in this directory (Codex, gpt-6-astra, read-only; prompt in `PROMPT.md`). The
reviewer read only `main.tex` as revised in commit 6f7f633 and never saw an earlier version. It
listed nineteen items, seven of them "should fix" (4, 5, 7, 11, 12, 16, 18) and twelve "consider".
The fixes were applied in one pass together with those of the fidelity review (`../prose-fidelity/`).
Where the two conflicted, fidelity took precedence, so a voice rewrite that would have dropped or
changed content was replaced by a different wording that keeps it.

| # | Item | Fix |
|---|---|---|
| 1 | Abstract: one sentence joins the relation to previous work, the novelty statement and the Lean verification | Split into two sentences: "...although we have not found it stated in the literature. The graph-theoretic core of its constructive direction is verified in Lean 4." |
| 2 | Introduction: the embedded assurance in "The characterization was first conjectured by a language model..." | "A language model first conjectured the characterization from the labeled orbits with 3 <= n <= 7 and wrote the Lean proofs, working within an automated system that accepts a claim only after machine verification." |
| 3 | "within reach of standard techniques" | Replaced, with fidelity item S5, by "within easy reach of a specialist", and the discovery is presented "as an example of a correct and checkable conjecture produced from data by such a system", which restores the earlier case-study framing |
| 4 | "leave ... to a layer above the present problem" | "We therefore treat fusions as deterministic and do not model the probabilistic success of linear-optical fusion." |
| 5 | "the development proves constructions ..., each stated together with the general lower bound so that no family theorem can hold vacuously" | "the development gives constructions attaining the minimum for several families. Each family theorem states the general lower bound together with a construction that attains it, so that none of them can hold vacuously." The vacuity clause is kept because it says why each family theorem carries the lower bound, which was content in the earlier version |
| 6 | Remark: "yet ... while ... and not to the star" | Split into two sentences with "whereas"; the paw "lies in a different orbit from the star"; with fidelity item S7, local complementation is applied "as an explicit step" |
| 7 | "No orbit changed." | "The additional Clifford choices did not change the set of orbits reached by Tier 1." |
| 8 | "content-addressed" and the storage detail | "stored as a single file identified by a hash of its contents"; following fidelity item M2, the table is also called a tablebase "in the terminology of" Lobl et al. |
| 9 | "Table I summarizes the results." | "Table I gives the number of orbits in each class." The suggested rewrite ("representatives in Table I") was not used, because Table I lists counts and no representatives |
| 10 | "The bound improves the table for 25 open orbits..." | "For 25 open orbits of rank-width three, one with n=8 and 24 with n=9, Theorem 1 strengthens the bound F >= n established by the search to F >= n+3." |
| 11 | The status sentence has the cadence of a declaration of safeguards | Rewritten together with fidelity items S8, S9 and A14. The six statuses are listed in increasing order. "Nothing the model merely asserts is recorded above heuristic, and refutation is permanent." The system runs every check in a sandbox, and the hash of a verifier covers its code and its test suite |
| 12 | Errors sentence ("instead of", a nested catalogue) | Rewritten as three plain sentences giving the exact list of errors (fidelity item S11), without "instead of" |
| 13 | Discussion: "verified in Lean, while ... are written proofs" | Split into two sentences: the quantum steps "rest on written proofs, which are supported by the two simulators and by the exhaustive search" |
| 14 | "Several questions remain open" and "it would be interesting" | Opener deleted; "it is not known which invariant separates F=n from F=n+3 among graphs of rank-width two" |
| 15 | "makes the decision problem ... polynomial" | "gives a polynomial-time test for F(G)=n-3" |
| 16 | "It is also natural to ask" | Merged into the preceding sentence: "..., as is the question whether analogous characterizations hold for larger GHZ states or for linear cluster states as resources." |
| 17 | Overloaded inventory sentence in the data availability section | Split into three sentences |
| 18 | Acknowledgments: the Codex sentence reads like a completion report and claims a rewording check | The rewording claim is deleted, because no such check had been made (fidelity item M3). The sentence now reads "Codex ... independently checked the proofs, the claims and the relation to previous work, and the errors it found were corrected." |
| 19 | "I" in the acknowledgments against "we" in the body | Not changed. The reviewer itself notes that singular attribution is normal in a single-author acknowledgment, and the sentence states the author's personal responsibility |

A second cold read of the revised text is in `../prose-voice-2/`.

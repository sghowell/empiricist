# Fixes applied: second Codex voice review (cold read)

Review: `REVIEW.md` in this directory (Codex, gpt-6-astra, read-only; the prompt is the first
round's, copied to `PROMPT.md`). The reviewer read only `main.tex` after the first-round fixes and
never saw an earlier version. Verdict: "The mathematical exposition largely reads like a conventional
PRA preprint: restrained, specific, and logically connected." The remaining machine-written impression
comes from repeated assurances about verification, nonvacuity and error correction. Twelve items were
raised, five of them "should fix" (1, 4, 6, 7, 11).

These fixes were applied together with the fidelity re-check (`../prose-fidelity/RECHECK.md`).
Several of the same sentences also had their content corrected there (N1 to N4).

| # | Item | Fix |
|---|---|---|
| 1 | The amsthm theorem, proof and remark labels are bold or italic run-in labels | Not changed. These are standard theorem typography in revtex. The author's run-in-label rule concerns paragraph labels, which the first revision removed |
| 2 | Abstract: "the bound raises the lower bound" | "we improve the lower bound from n to n+3" |
| 3 | "The present work makes the characterization explicit ... and adds the more general bound." | "We make the characterization explicit for this resource model and prove the more general bound." This keeps the framing that the novelty review asked for |
| 4 | "within easy reach of a specialist ... as an example of a correct and checkable conjecture": defensive meta-commentary | "A specialist can readily derive the characterization from the results cited above, and we describe how it was found in Sec. VI." The account of who found it was corrected at the same time (fidelity N4) |
| 5 | "A counting form of the bound, ..., is the Lean theorem fusion_cost_lower_bound." | "The Lean theorem fusion_cost_lower_bound proves a counting form of this bound in a merge model of schedules that also tracks fusions which split or consume a component." |
| 6 | "so that none of them can hold vacuously" | "Before the general theorem, the development treats several families separately. For each family, the Lean theorem states both the general lower bound and the existence of a construction that attains it." |
| 7 | Overloaded status sentence; "Nothing the model merely asserts" | The system "records each claim as heuristic, conjectured, verified up to a given size, certified or formalized, in increasing order of strength, or as refuted, and a claim advances only when a verifier accepts evidence for it. A claim supported only by the model's assertion is recorded at most as heuristic, and the status refuted is permanent." Refuted is now outside the strength order, as in the code (fidelity re-check, S8 note) |
| 8 | "hardened against adversarial submissions" sounds like a security report | "Before it was used, the checker was revised in response to adversarial submissions, ..." |
| 9 | "a note was found to give" | "While preparing this paper, we found by an exact computation of rank-widths that a note had given..." (fidelity N1) |
| 10 | Discussion repeats the verification boundary as an assurance | One forward-looking sentence: "Extending the formal verification from the combinatorial core of the constructive direction of Theorem 2 to Lemma 3 and to the proof of Theorem 1 would require definitions of graph states, Pauli measurements and schedules in Lean, and rank-width is not yet available in mathlib." Sec. IV already states what is and is not formalized, and Secs. II and V state the support from the simulators and the search |
| 11 | "I" and "my" in the acknowledgments against "we" in the body | Not changed. The author's other arXiv papers (`~/dev/research/zx_quantum_gravity/research/route_b/*/arxiv/main.tex`) use exactly this first-person template |
| 12 | Passive closing assurance in the Codex sentence | Restored to the author's template wording: "...; the errors it found have been corrected." |

A third cold read of the final text is in `../prose-voice-3/`.

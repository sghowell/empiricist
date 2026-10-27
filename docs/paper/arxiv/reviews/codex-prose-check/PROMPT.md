You are checking that a prose rewrite of a physics preprint is scientifically equivalent to the already-reviewed original. Work read-only and do not modify any file. This is a fidelity check. Do not reopen the scientific acceptance of the paper, and do not judge prose style.

Files, all in /Users/seanhowell/dev/empiricist:
- ORIGINAL: docs/paper/arxiv/reviews/prose-fidelity/main.before.tex. It is byte-identical to docs/paper/arxiv/main.tex at commit 4a6f983, the version that passed the earlier Codex reviews.
- REWRITE: docs/paper/arxiv/main.tex in the working tree.
- Earlier reviews whose fixes must survive the rewrite: docs/paper/arxiv/reviews/codex-critic-math/FIXES_APPLIED.md, docs/paper/arxiv/reviews/codex-critic-novelty/FIXES_APPLIED.md and docs/paper/arxiv/reviews/codex-recheck/FIXES_APPLIED.md. The prior-art pass is in docs/paper/arxiv/reviews/prior-art/PRIOR_ART.md.
- The intermediate prose reviews and their fixes are in docs/paper/arxiv/reviews/prose-voice/, prose-voice-2/ and prose-fidelity/. Read them only after you have formed your own judgment.

The rewrite also makes four intended corrections of content. Verify each against the repository instead of treating it as drift:
(a) Provenance. The original says that a language model (Fable 5) first proposed the characterization from the 44 labeled orbits with n <= 7. The repository's records say otherwise. The coding assistant that built the system (Claude Code, model Claude Opus 4.8) first noticed the pattern in the table of all 585 orbits, and Fable re-derived it three days later from the 44 orbits, with no class names. The sources are the header of docs/science/2026-07-12-p5-tier0-characterization.md, docs/science/2026-07-15-p5-dh-characterization-fable.md, and the author line of docs/superpowers/specs/2026-07-06-empiricist-harness-design.md. The rewrite changes the introduction, Sec. VI and the acknowledgments accordingly. The acknowledgments also no longer say that Fable "classified the orbits". The table was computed by the system's deterministic search (docs/science/2026-07-07-p5-tier0-tier1-results.md), and Fable, in its searcher role, proposed the nine later constructions (docs/science/2026-07-09-p5-live-campaign-report.md).
(b) The original lists, as an error caught by the system, an arithmetic slip of "185/400 instead of 175/410". The records show that 185/400 was the correct split of the table into exact and open rows (anc/data/tablebase.json has 185 exact rows and 400 open rows), and that the correction of July 15 misread it. The rewrite drops this item. See the corrections appended on 2026-10-26 to the two July notes.
(c) The original credits the system's checks with catching the two remaining errors. The records show that the vacuous family-theorem statement was caught in review (docs/science/2026-07-10-p5-formalized-lower-bound.md). They also show that the rank-width slip was found by an exact computation while the paper was being prepared (the correction of 2026-10-26 in docs/science/2026-07-12-p5-tier0-characterization.md).
(d) The original says that claims are identified by content hashes. In the code, artifacts are content-addressed and claims have readable names (src/empiricist/ledger/models.py and src/empiricist/claims/model.py).
For each correction, say whether it is right and complete, and whether it introduces any new inaccuracy.

Compare the two versions claim by claim:
1. Every theorem, lemma, proposition, remark, proof step and equation must be mathematically identical.
2. Every number, range, Lean declaration name and table entry must be unchanged.
3. Every hedge, scope restriction and qualification must survive, and no claim may become stronger or weaker. Examples are "for n >= 3", "up to a global phase", "not formalized", what the Lean development does and does not prove, "we have not found ... in the literature", the code shared by the two simulators, conditional results of cited works, and the account of how the result was found and how hard it is.
4. Every attribution must keep its citation, and no claim may move to a different source.
5. Every fix listed in the three earlier FIXES_APPLIED files must still be in force in the rewrite.
6. Any statement in the rewrite with no counterpart in the original must be supported by the original, by the cited sources or by the repository. Check each one.

For each discrepancy, give:
- its location;
- the original text and the rewritten text;
- why it matters;
- a severity;
- exact replacement text.
End with a verdict. Say whether the rewrite is scientifically equivalent to the original, and if it is not, whether it would be after the replacements you give. Write the report as your final message, in Markdown.

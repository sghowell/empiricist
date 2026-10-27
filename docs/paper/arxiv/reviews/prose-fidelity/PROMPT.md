You are a fidelity reviewer for a prose revision of a physics preprint. A rewrite for voice can silently change content, and your only job is to find every such change. Work read-only: do not modify any file in the repository.

Files (in /Users/seanhowell/dev/empiricist):
- OLD version (before the prose revision): docs/paper/arxiv/reviews/prose-fidelity/main.before.tex
- NEW version: docs/paper/arxiv/main.tex
- Bibliography (unchanged): docs/paper/arxiv/refs.bib

Compare OLD and NEW claim by claim. Go through OLD sentence by sentence and find where each claim went in NEW. Check in particular:
1. Every number (orbit counts, 585, 175, 16, 3, 19, 25, 44, 541, 93, 36, six classes, 185/400 vs 175/410, n ranges such as 3 <= n <= 9, mathlib v4.31.0, eight resources/nine fusions/three local complementations, etc.).
2. Every theorem, lemma, proposition and remark statement, proof step and equation: they must be mathematically identical (notation changes are fine only if equivalent).
3. Every hedge, scope restriction and qualification (e.g. "for n >= 3", "up to a global phase", "up to a Pauli operator", "not formalized", what Lean does and does not prove, "we have not found ... in the literature", the shared code between the two simulators, conditional results of cited works). A hedge that disappeared or weakened, or a claim that became stronger, is a finding.
4. Every attribution to a cited work: same citation keys on the same claims, and no claim attributed to a different work.
5. Any NEW claim that has no counterpart in OLD.
6. Any OLD claim that is missing from NEW.
7. Cross-references (labels such as sec:, thm:, lem:, prop:, eq:, tab:, app:) that now point to the wrong place or describe the target wrongly (e.g. "Sec. X describes ..." when it does not).

The author made these structural changes deliberately; report on them but classify them as "intentional" unless they lose or change content: the separate "Related work" section was folded into the introduction; the bulleted "What is proved, and how" list became prose; the sentence about the language model's role was moved from the abstract to the introduction and Sec. VI; the methods section was condensed (the ordered list of claim statuses REFUTED < HEURISTIC < ... was replaced by a prose description); the open questions became prose; the run-in paragraph labels were removed.

Report as your final message, in Markdown: a short verdict; then a table of findings with columns: location (section and first words in NEW, or in OLD if missing), OLD text, NEW text, kind (changed number / changed math / lost or weakened hedge / strengthened claim / attribution change / new claim / missing claim / broken cross-reference / intentional), severity (must fix / should fix / acceptable), and a suggested fix that restores the OLD content in the NEW style. Quote text exactly. Be exhaustive on substance and silent on style.

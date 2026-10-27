# Fixes applied: Codex scientific-equivalence check

This follows the author's practice for AI-assisted rewrites (cf. `research/route_b/bh_magic/reviews/codex-prose-check/`
in zx_quantum_gravity).

**First check** (`PROMPT.md`, `REVIEW.md`; the text it read is saved as `main.checked.tex`). The
mathematics is preserved: both numbered equations, the displays and both table bodies are
byte-identical. Every fix in the three earlier `FIXES_APPLIED.md` files is still in force, 47 citation
keys are cited in both versions, and all 50 manifest hashes pass. The four intended corrections of
content were checked against the repository and found right and complete: who first noticed the
characterization, the "185/400" non-error, how the remaining two errors were caught, and the content
addressing of artifacts. One discrepancy, of moderate severity: the literature-search sentence had
broadened "a classification of minimum fusion counts in this model" to "exact minimum fusion counts
for this model". Fixed by restoring the original scope, merged with the next sentence as the third
voice review suggested.

**Second check** (`PROMPT-2.md`, `REVIEW-2.md`): the fix and every edit made after the first check,
compared against the original.
Verdict: no new discrepancies, and the earlier one is resolved. Mechanically, the only change inside a
proof is the split sentence in the proof of Theorem 1, and the other four proof environments,
all inline mathematics, equations, displays, table bodies, Lean names and citation groups are
byte-identical to the checked text. "The current `main.tex` is scientifically equivalent to the
reviewed original, allowing for the four verified intended corrections." Nothing further to apply.

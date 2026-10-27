# Fixes applied: Codex mathematical review

Review: `REVIEW.md` in this directory (Codex, gpt-6-astra, maximum reasoning, read-only; prompt in
`PROMPT.md`). Verdict: no blocking or major error; six minor findings and two nits. Every finding was
accepted.

| # | Finding | Fix |
|---|---|---|
| 1 | The characterization needs n >= 3 (K2 is distance-hereditary); the counts 585 and 44 are for 3..9 and 3..7 vertices | Abstract states n >= 3 for both the bound and the characterization; "three to nine" and "three to seven" vertices in the abstract; 3 <= n <= 7 and 3 <= n <= 9 in Sections I, IV and VI |
| 2 | "Two stabilizer engines that share no code" overstates independence: construction replay, graph-level local complementation and orbit canonicalization are shared | Abstract: "two independently implemented stabilizer engines"; Sections I, V and VI now say the engines have independent implementations of fusion and graph extraction and share the replay, the graph-level local complementation and the canonicalization |
| 3 | `rankwidth_check.py` called lower bounds of open rows "tight" and gave "slack -3" for a rank-width-three open row | `report` now takes exactness: for exact values it says whether the bound is attained or by how much it is missed; for open rows it prints the search's lower bound, the rank-width bound and their maximum. Output regenerated |
| 4 | The README said the tablebase has sixteen exact rows above the minimum (it has ten), and no script printed the final Table I | README corrected (ten from Tier 1, nine later constructions); new `scripts/final_table.py` joins the nine constructions to their tablebase rows by orbit key and applies the rank-width improvements, printing Table I exactly; output in `scripts/final_table.out.txt` |
| 5 | `SHA256SUMS` stale for README | `build.sh` regenerates the manifest on every build; regenerated after the final edits |
| 6 | "Efficient at bounded rank-width" needs both the source's rank-width and the target's size bounded | Related work now cites Dahlberg and Wehner (Phil. Trans. R. Soc. A 2018) for the algorithm, cubic in the size of the source when its rank-width and the target's size are bounded, and Dahlberg, Helsen and Wehner for the hardness results |
| 7 | Eq. (1) holds only up to a global phase | "up to a global phase" added |
| 8 | "Reverse" and "forward" swapped relative to the theorem's statement | The sentence now names the implications explicitly ("the implication from F(G) = n - 3 to distance-hereditary ... and the converse ...") |

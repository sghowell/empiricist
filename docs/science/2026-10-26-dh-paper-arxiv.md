# The distance-hereditary paper, arXiv-ready: a rank-width bound, honest positioning, and three corrections

**Date:** 2026-10-26 · **Problem:** P5 (minimum-fusion synthesis of graph states) · **Milestone:** M27a
(`docs/superpowers/plans/2026-10-26-m27a-dh-paper-arxiv.md`) · **Paper:** `docs/paper/arxiv/` ·
**Model spend:** the prior-art pass (one subagent) and two Codex reviews; no harness campaign.

## What changed between the July draft and the arXiv version

1. **A new theorem with a short proof.** F(G) >= n + 3 rw(G) - 6 for every connected graph G. The
   resources and fusions of a schedule form a multigraph; the component holding the output has cycle
   rank t with f >= n - 3 + 3t (the counting bound, made exact); a spanning tree of it, with the output
   qubits attached as leaves, is a rank decomposition in which every cut crosses at most 1 + t fusion
   bonds, each of Schmidt rank at most two, so rw <= 1 + t. The idea is the prior-art agent's (its
   Section 3b, the case t = 0); the general bound and its use on the data are new here.
2. **The characterization's hard direction is now a short written proof** (the case t = 0), covering
   every schedule, so the July draft's one unformalized step (the single-blob reordering) is no
   longer needed for the theorem. The reordering survives as the normal form that makes the search
   exhaustive (Appendix A of the paper).
3. **Honest positioning.** The prior-art pass found no statement of either result, but both directions
   of the characterization can be assembled from published results: the reverse from Schmidt-rank
   width = rank-width (Van den Nest et al. 2007), the forward from Connolly et al. 2026's split-fuse
   construction plus Lee-Jeong's stars. The circuit-model twin is Kumabe-Mori-Yoshimura (Quantum
   2026): CZ count >= n + rw - 2, exactly n - 1 at rank-width one. The paper says all of this and
   frames the machine discovery as a case study, not as evidence that the result is hard.
4. **New certified data from the bound.** Exact rank-widths for every orbit above the minimum (all
   rank decompositions enumerated): every non-distance-hereditary orbit with n <= 7 has rank-width 2;
   the bound is attained by all sixteen orbits with exact F = n and missed by three (all rank-width 2)
   with F = n + 3; and 25 open orbits (one at n = 8, 24 at n = 9) have rank-width 3, which raises their
   lower bound from n to n + 3.

## Corrections found while preparing the paper

- The July notes gave the six-vertex orbit with F = 9 rank-width 3; every six-vertex graph has
  rank-width at most 2 (the 3 was its linear rank-width). Correction appended to
  `docs/science/2026-07-12-p5-tier0-characterization.md`. The orbit is an exact counterexample to
  "F is a function of rank-width".
- The count of exact values above the minimum is 19, not 13 (six n = 8 orbits were certified at F = 8
  after July).
- The search fused in one fixed Bell basis, while the model allows any single-qubit Clifford before a
  fusion. For merges this is harmless (Lemma A.1, local complementation absorbs the Clifford); for the
  single intra-component fusion of Tier 1 it was re-checked with all six (and for n <= 5 all 36)
  pre-rotation classes, and no orbit changed, so the three F = n + 3 values stand.
- `docs/open_problems_ftfbqc.md` references [40]-[42] had wrong authors, a conflation of three papers,
  and a wrong article number; corrected.

## The submission state

Build: `docs/paper/arxiv/build.sh` (tectonic and TeX Live 2026 pdflatex both 10 pages; isolated
rebuild from the bundle alone; no undefined references or overfull boxes; ASCII source; USTAR bundle).
Supplement: a self-contained Lake project whose `check_axioms.sh` builds and prints the axioms of all
twelve declarations (about a minute with prebuilt mathlib), the tablebase and constructions, and
scripts whose outputs are committed. Reviews: Codex (mathematics; novelty and citations) under
`docs/paper/arxiv/reviews/`. Decisions left to Sean: `docs/paper/arxiv/ARXIV_SUBMISSION.md`.

## The reviews

A prior-art and bibliography pass (a subagent; `docs/paper/arxiv/reviews/prior-art/PRIOR_ART.md`) set the
framing above. Codex (gpt-6-astra, maximum reasoning) then reviewed the paper twice, independently: the
mathematics (no blocking or major error; it reproduced every Table I cell and replayed all 194 witnesses
through both engines; six minor findings and two nits, about scope (n >= 3), the description of what the
two engines share, the reporting of a script, a stale checksum, the Dahlberg-Wehner algorithm's
parameters, a global phase and the naming of the implications), and the relation to previous work with
live web search (no earlier statement of either theorem found; "the general bound appears to be the more
substantial new statement"; one major attribution fix and several minor ones). A recheck confirmed the
fixes, cross-checked the rank-widths with its own dynamic program, and found three remaining small items,
also fixed. Every finding and its fix is in the `FIXES_APPLIED.md` files under `docs/paper/arxiv/reviews/`.

## The prose revision and the corrections it surfaced (2026-10-26)

At Sean's request the paper was rewritten to his style rules: connected paragraphs; no run-in labels
or lists; no "not X but Y", colon reveals, tricolons or emphasis words; the register of a PRA paper.
Following his practice for AI-assisted rewrites, two kinds of independent review checked it:
- cold reads of the voice by Codex, three rounds, which never saw an earlier version
  (`docs/paper/arxiv/reviews/prose-voice*/`);
- a claim-by-claim fidelity review against the merged text, with a re-check
  (`reviews/prose-fidelity/`);
- a final Codex scientific-equivalence check against the merged text (`reviews/codex-prose-check/`).

The fidelity reviews found that the first rewrite had dropped content. It lost the n >= 3 scope in the
abstract, the credit to Löbl et al.'s exact table up to eight qubits together with the Bui-Xuan et al.
citation, and several hedges. It also added a false claim about a rewording check. All of this was
restored or removed.

Checking the new wording against the repository's own records then exposed three errors that were
already in the merged paper (and in the July draft):

- **Who found the characterization.** The paper said a language model (Fable 5) first proposed it. The
  July records say the coding assistant that built the harness (Claude Code; the spec's author line
  gives Claude Opus 4.8) noticed the distance-hereditary pattern on 2026-07-12 while mining the full
  585-orbit table. Fable re-derived it on 2026-07-15 from the 44 orbits with n <= 7, with no class
  names, and the 541 held-out orbits agreed. The table itself came from the harness's deterministic
  search, so "Fable classified the orbits" was also wrong; Fable proposed the nine later
  constructions. The introduction, Sec. VI and the acknowledgments now say this.
- **The "185/400 arithmetic slip" was not a slip.** 185/400 is the exact/open split of the tablebase
  (185 exact rows = 175 Tier-0 + 10 Tier-1; 400 open). The July 15 "count correction" to 175/410
  confused it with the split at the minimum. The item is gone from the paper, and dated corrections
  are appended to both July notes. The content-addressed evidence artifact that repeats the misreading
  (`claims/evidence/85e7a63cdadb48c2.json`, field `count_correction`) is left as recorded.
- **What caught the remaining errors.** The paper credited "the system's checks". The vacuous
  family-theorem statement was well typed and was caught in review. The rank-width slip was found by an
  exact computation while the paper was being prepared. The paper now says so, and it also says that
  artifacts are content-addressed (claims have readable names).

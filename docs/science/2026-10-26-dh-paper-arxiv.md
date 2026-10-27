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

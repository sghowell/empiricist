# arXiv submission sheet: the distance-hereditary paper

Status: draft for Sean's decision. Upload: `docs/paper/arxiv/arxiv_source.tar.gz` (main.tex,
main.bbl, refs.bib, anc/). Rebuild and checks: `docs/paper/arxiv/build.sh`.

## Checks done

- The bundle compiles in isolation under pdflatex (TeX Live 2026, via TinyTeX), which is what
  arXiv runs, from the shipped `main.bbl` without BibTeX, and under tectonic; no undefined
  references or citations, no overfull boxes, matching page counts (`build.sh` fails otherwise).
- Source is pure ASCII; the bundle is a USTAR archive with uid/gid 0 and no extended attributes.
- Every number in the paper was re-derived from the committed artifacts by the scripts in `anc/`
  (outputs in `anc/scripts/*.out.txt`); the Lean project in `anc/lean` builds and every declaration
  the paper names depends only on `propext`, `Classical.choice` and `Quot.sound`.
- Reviews (all in `reviews/`): a prior-art and bibliography pass (`prior-art/PRIOR_ART.md`, 55 verified
  entries); Codex (gpt-6-astra, maximum reasoning) mathematical review (`codex-critic-math/`: no blocking
  or major error; every Table I cell and all 194 witnesses reproduced) and novelty and citation review
  with live web search (`codex-critic-novelty/`: no priority conflict found; the general bound is the
  more substantial new statement); every finding answered in the `FIXES_APPLIED.md` files; a recheck of
  the fixes in `codex-recheck/`.

## Metadata

Title:

```
Distance-hereditary graphs characterize minimum-fusion synthesis of graph states
```

Authors:

```
Sean Howell
```

Abstract: the text of the `abstract` environment of `main.tex` (1,698 characters; the limit is
1,920; math stays in `$...$`).

Comments field (fill in the tag after merge):

```
10 pages, 2 tables; ancillary files contain the Lean development, the table of minimum fusion counts and the scripts that recompute every number; code at https://github.com/sghowell/empiricist (tag dh-paper-v1)
```

Suggested categories: quant-ph primary; cross-list math.CO (the theorem is a graph
characterization) and possibly cs.LO (the Lean formalization).

License suggestion: CC BY 4.0.

## Decisions for Sean

- Whether and when to post.
- Affiliation: decided 2026-10-26, email only (sean.g.howell@gmail.com), no affiliation.
- Thanks: the acknowledgments currently contain only the AI-use statement. Add colleagues?
- Title: the July draft had the subtitle "A machine-discovered result with a formally verified
  core". It is dropped: the prior-art pass showed both directions of the characterization can be
  assembled from published results, and the distance-hereditary pattern was first noticed by the coding
  assistant (Claude Code with Claude Opus 4.8) in the full table, with Fable's blind re-derivation from
  the orbits with n <= 7 three days later. The paper now says so in the introduction, Sec. VI and the
  acknowledgments. The July model name is taken from the author line of the harness design spec;
  please confirm it. An alternative title that leads with the new bound: "Rank-width bounds the number of
  fusions needed to build a graph state from three-qubit GHZ states".
- Framing: the review verdict is that the characterization has modest novelty (an explicit
  consequence of existing results in this model) and the bound F >= n + 3 rw - 6 is the more
  substantial new statement. The paper says so. A short note (or a letter-length venue) fits this
  content better than a long article.
- Whether a colleague reads the paper first. So far only AI models have reviewed it.
- Endorsement, if the account has not posted to quant-ph before.
- Tag the repository commit that the comments field names (proposed tag `dh-paper-v1`) after
  the PR merges.

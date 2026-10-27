# arXiv submission sheet: the distance-hereditary paper

Status: draft for Sean's decision. Upload: `docs/paper/arxiv/arxiv_source.tar.gz` (main.tex,
main.bbl, refs.bib, anc/). Rebuild and checks: `docs/paper/arxiv/build.sh`.

## Checks done

- The bundle compiles in isolation under pdflatex (TeX Live 2026, via TinyTeX), which is what
  arXiv runs, from the shipped `main.bbl` without BibTeX, and under tectonic; no undefined
  references or citations, no overfull boxes, matching page counts (`build.sh` fails otherwise).
- Source is pure ASCII; the bundle is a USTAR archive with uid/gid 0 and no extended attributes.
- Every number in the paper was re-derived from the committed artifacts by the scripts in `anc/`
  (outputs in `anc/scripts/*.log`); the Lean project in `anc/lean` builds and every declaration
  the paper names depends only on `propext`, `Classical.choice` and `Quot.sound`.
- Reviews: see `reviews/` (Codex) and `reviews/FIXES_APPLIED.md`.

## Metadata

Title:

```
Distance-hereditary graphs characterize minimum-fusion synthesis of graph states
```

Authors:

```
Sean Howell
```

Abstract: the text of the `abstract` environment of `main.tex` (1,722 characters; the limit is
1,920; math stays in `$...$`).

Comments field (fill in the tag after merge):

```
N pages, 1 table; ancillary files contain the Lean development, the certified tablebase and the scripts that re-derive every number; code at https://github.com/sghowell/empiricist (tag dh-paper-v1)
```

Suggested categories: quant-ph primary; cross-list math.CO (the theorem is a graph
characterization) and possibly cs.LO (the Lean formalization).

License suggestion: CC BY 4.0.

## Decisions for Sean

- Whether and when to post.
- Affiliation: the July draft gave only an email address; the zx_quantum_gravity papers give
  PsiQuantum. Keep the email only, or add an affiliation?
- Thanks: the acknowledgments currently contain only the AI-use statement. Add colleagues?
- Title: the July draft had the subtitle "A machine-discovered result with a formally verified
  core". It is dropped here so that the title states the result; the abstract and Section VI
  describe the method. Restore it if you prefer.
- Whether a colleague reads the paper first. So far only AI models have reviewed it.
- Endorsement, if the account has not posted to quant-ph before.
- Tag the repository commit that the comments field names (proposed tag `dh-paper-v1`) after
  the PR merges, and fill in the page count.

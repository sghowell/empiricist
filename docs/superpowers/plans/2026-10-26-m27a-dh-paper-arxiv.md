# M27a: the distance-hereditary paper, arXiv-ready

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the July 2026 preprint `docs/paper/paper.tex` ("Distance-hereditary graphs characterize minimum-fusion synthesis of graph states") into an arXiv-ready submission to the standard of Sean's `zx_quantum_gravity` papers: revtex4-2 source with a `.bib` and shipped `.bbl`, an isolated rebuild under pdflatex (TeX Live 2026, as arXiv runs) and tectonic with no undefined references or overfull boxes, an `anc/` supplement (Lean sources, the certified tablebase, re-check scripts, README mapping claims to files, SHA-256 manifest), cross-model (Codex) reviews with fixes applied, and a submission sheet with title, abstract, comments, categories and the decisions left to Sean.

**Architecture:** Everything lives in `docs/paper/arxiv/`: `main.tex`, `refs.bib`, `main.bbl`, `main.pdf`, `anc/`, `arxiv_source.tar.gz`, `build.sh` (both builds plus the bundle), `ARXIV_SUBMISSION.md`, and `reviews/` (Codex prompts and reports, fixes applied). The old `paper.tex`/`paper.pdf` are removed (history keeps them); `docs/paper/README.md` points to the new layout. No code changes outside `docs/` unless a check reveals a defect in a claim the paper reports, in which case the claim is corrected through the ledger first.

**Tech Stack:** LaTeX (revtex4-2, amsthm), TinyTeX pdflatex + bibtex at `~/Library/TinyTeX/bin/universal-darwin/`, tectonic, the Codex CLI (`codex exec`), the claims ledger and the P5 engines for re-checks.

**Spec:** `docs/paper/paper.tex` (the July draft), the P5 ledger rows (`claims/P5.*`), `docs/science/2026-07-*-p5-*.md`, and Sean's arXiv standard in `~/dev/research/zx_quantum_gravity/research/route_b/ARXIV_SUBMISSION.md`.

## Global Constraints

- The paper states exactly what is proved and in what sense (Lean theorem, engine-verified, written proof); every number in it is re-derived from the committed artifacts, not copied from the July draft.
- Author: Sean Howell. The acknowledgments disclose the AI work (Fable 5 through the harness for the discovery and the Lean proofs; Claude Code, model Claude Opus 5.5, for the revision and the written proofs added here; Codex for independent review) and that Sean chose the problem and takes responsibility. Affiliation and any thanks to colleagues are Sean's decisions, left open in the submission sheet.
- No priority claim beyond what the prior-art pass supports; the closest works are cited and the differences stated.
- Source is pure ASCII; bundle is a USTAR tar with uid/gid 0 and no extended attributes; abstract within 1,920 characters.
- No AI attribution in commit messages. Branch `docs/m27a-dh-paper-arxiv` off `main`; PR; Sean decides posting.

---

### Task 1: re-derive the paper's facts from the artifacts

- [ ] Orbit counts per N, the 175/410 split, the 93/82 tree-orbit split, the thirteen exact values above the floor, and the 44 labeled / 541 held-out orbits — each recomputed from `claims/evidence/dc8649519e5f8694.json` (the tablebase) and the P5 claims, with a script in `anc/`.
- [ ] The Lean declarations named in the paper: located in `lean/EmpiricistLean/EmpiricistLean/*.lean` or `claims/evidence/*.lean`, axioms printed, mathlib pin confirmed (`v4.31.0`, rev `fabf563…`).
- [ ] The completeness of the search's move set: the fusion is measured in one fixed Bell basis, while the model allows any single-qubit Clifford on the fused qubits before a fusion. For merges this is absorbed by local complementation (written proof, Task 2). For the single intra-component fusion of Tier-1 (which certifies the three values F = N + 3 and the refutation of F = N − 3 + 3(rw − 1)), re-run Tier-1 with all six pre-rotation classes and record the outcome; if any orbit changes, correct the ledger before the paper states it.

### Task 2: the written proofs the paper's main theorem rests on

- [ ] Lemma (single-blob normal form, with frames): any schedule producing a connected target can be reordered — fusions on disjoint qubit pairs commute; a spanning tree of the resource-fusion multigraph in breadth-first order gives the merges; remaining fusions follow as intra-blob fusions; resource groups disconnected from the target are deleted — and every pre-fusion single-qubit Clifford on a merge qubit is traded, by local complementations on a connected graph, for Cliffords on the other qubits. Full proof in an appendix.
- [ ] The merge rewrite stated as the standard type-II fusion rule on graph states, cited to its primary source (from the prior-art pass), with the engines' fuzz agreement as the independent check.

### Task 3: related work and bibliography

- [ ] `refs.bib` from the prior-art pass (every entry verified against arXiv or the publisher), a related-work section placing the result against minimum-fusion optimization in other resource models (Löbl et al. 2025 and later), graph-state LC classification, distance-hereditary graphs and rank-width, and machine-assisted mathematics.

### Task 4: the manuscript

- [ ] `docs/paper/arxiv/main.tex` in revtex4-2 (aps, pra, onecolumn, superscriptaddress, nofootinbib, longbibliography), the July content revised: precise model definition (fusion basis, free local Cliffords, outcomes), the theorem stated with its proof status, the new normal-form appendix, related work, data and code availability (repository URL at a tagged commit, `anc/`), acknowledgments with the AI-use statement.

### Task 5: the supplement and the builds

- [ ] `anc/`: the Lean modules behind every declaration in the paper's table with a build-and-axioms script, the tablebase JSON, the fact re-derivation script and the rotation re-check, README mapping each claim to a file, `SHA256SUMS`.
- [ ] `build.sh`: tectonic build; isolated pdflatex + bibtex build (TinyTeX, TeX Live 2026) from a clean copy of the bundle; checks for undefined references, overfull boxes, matching page counts, ASCII-only source; creates `arxiv_source.tar.gz` (main.tex, main.bbl, refs.bib, anc/) as USTAR with uid/gid 0.

### Task 6: independent review

- [ ] Codex reviews (critic of the mathematics and the claims, novelty and citation check against the sources, prose check), each saved under `reviews/`; every finding either fixed or answered in `reviews/FIXES_APPLIED.md`; a recheck after fixes.

### Task 7: submission sheet and hand-off

- [ ] `ARXIV_SUBMISSION.md`: title, authors, abstract (≤ 1,920 characters), comments field, suggested categories (quant-ph primary; math.CO cross-list), license suggestion, and the decisions for Sean (posting, affiliation, thanks, whether a colleague reads it first, endorsement).
- [ ] Note in `docs/science/`, memory, PR.

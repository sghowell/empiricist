# Fixes applied: claim-by-claim fidelity review of the prose revision

Review: `REVIEW.md` in this directory. A Claude subagent compared the text before the prose
revision (`main.before.tex`, the version merged in PR #92) with the revised text of commit 6f7f633,
claim by claim; its prompt is in `PROMPT.md`. Verdict: the mathematics is unchanged (every theorem,
lemma, proof step, equation, number and Lean name, and both table bodies), but there are three
must-fix changes of content and eleven smaller drifts. Every must-fix and should-fix item was
accepted.

| ID | Finding | Fix |
|---|---|---|
| M1 | The abstract dropped "for n >= 3" from the characterization (false for K2) | "The bound is attained at rank-width one, so that for n >= 3 we have F(G)=n-3 if and only if G is distance-hereditary." |
| M2 | Merging the related-work section into the introduction dropped the credit to Lobl et al.'s exact table up to eight qubits, their zero-fusion class, and the Bui-Xuan et al. citation | Restored in Sec. I: Lobl et al. computed the exact minimum number of fusions for all graph states on up to eight qubits; in their model the graphs needing no fusion are those locally equivalent to caterpillars, the connected graphs of linear rank-width one [BuiXuan2013note]; both the counts and the class at the minimum differ from ours. The term "tablebase" is attributed to them in Sec. V. Bui-Xuan et al. is back in `main.bbl` |
| M3 | The acknowledgments claimed that Codex had confirmed the rewording did not change the content, which nobody had checked | Clause deleted |
| S1 | "for fusions of GHZ states" lost "three-qubit" | "for fusions of three-qubit GHZ states" |
| S2 | "the fusion network of an optimal schedule is a tree" is false for graphs that are not distance-hereditary | "the fusion network of a schedule with n-3 fusions is a tree" |
| S3 | "local-equivalence classes" in place of "orbits" for the Hein and Danielsen-Parker classifications | "The local-complementation orbits of graph states were classified by..." |
| S4 | The identification of the Lean class with the distance-hereditary graphs sat inside "The Lean development shows that" | The Lean sentence ends at the class definition. A new sentence says that by results of Bandelt-Mulder and Oum, which are not part of the formalization, the class consists of the connected distance-hereditary graphs on at least three vertices |
| S5 | "within easy reach of a specialist" weakened, and the case-study framing and the novelty framing dropped | "within easy reach of a specialist", reported "as an example of a correct and checkable conjecture produced from data by such a system"; and "The present work makes the characterization explicit for this resource model and adds the more general bound." |
| S6 | "merge model" dropped from the description of `fusion_cost_lower_bound` | Restored |
| S7 | "applies local complementation only where it is needed" changed the meaning of "only explicitly" | "applies local complementation as an explicit step" |
| S8 | "stays at the lowest status" misplaces unsupported claims, since refuted is the lowest status | The statuses are listed in order (refuted, heuristic, conjectured, verified up to a given size, certified, formalized), and nothing the model merely asserts is recorded above heuristic |
| S9 | Sandboxing was stated only for Lean modules | "The model never executes code, and the system runs every check in a sandbox." |
| S10 | "tested against adversarial submissions" is stronger than "developed against" | "hardened against adversarial submissions" |
| S11 | "several errors ..., among them" implied unlisted errors, and "count of the extremal orbits" was mislabeled and undefined | Exactly three errors, each in its own sentence; the count is of "the orbits that do and do not attain the minimum" (185 and 400, against the correct 175 and 410) |
| A2 (optional) | "the fusion cost is not determined by rank-width" | "above rank-width one" added |
| A4 (optional) | "associated with simple graphs" | "in one-to-one correspondence with simple graphs" restored |
| A5 (optional) | Ji et al.'s type-I fusion of motifs merged into a generic phrase | "or from ring, star and linear motifs joined by type-I fusion [Ji2026towards]" |
| A14 (optional) | The verifier hash no longer said to cover the test suite; "read-only" dropped | Both restored |
| Outside the brief | The abstract said the proof bounds the Schmidt rank "by the cycle rank" (it bounds its logarithm by 1+t), and "tree decomposition" suggests treewidth | "The proof turns a spanning tree of the network formed by the resources and the fusions into a rank decomposition of G and bounds the Schmidt rank of the output across each of its cuts in terms of the cycle rank of the network." |
| Outside the brief | The submission sheet gave the old abstract length; the comments field and `anc/README.md` used "certified tablebase", "extremal" and "gate-certified"; the README placed `floor_schedule_iff_dh` in a remark | Abstract length updated (1,704 characters); comments field reworded; README terms replaced or defined, and the location corrected to the paragraph after Theorem 5 in Sec. IV |

The items marked acceptable in the review (A1, A3, A6 to A13 and A15 to A20) were left as they are. A
re-check of these fixes by the same reviewer is in `RECHECK.md`.

## Re-check (`RECHECK.md`)

The same reviewer re-checked the fixes. It found every must-fix item resolved, ten of the eleven
should-fix items resolved, and the optional items applied correctly. Checking the new wording against
the repository's own records then turned up four new problems. Two of them were in the merged text
before the prose revision. Every item was verified against the primary records before it was fixed.

| ID | Finding | Verification | Fix |
|---|---|---|---|
| N1 | "The checks of the system also caught three errors" credits the system with errors it did not catch | The vacuous family-theorem statement was well typed and was caught in review (`docs/science/2026-07-10-p5-formalized-lower-bound.md`: "tightened after review"; commit dab87a0). The rank-width slip was found by an exact computation while the paper was being prepared | "Two errors were caught during the work." The family-theorem sentence now says that the Lean checker cannot detect such a statement and that a review of the statement caught it. The rank-width sentence says "we found by an exact computation of rank-widths" |
| N2 | The "arithmetic slip, 185/400 instead of 175/410" was not an error (it was in OLD too) | `anc/data/tablebase.json` has 185 exact rows (175 at F = n - 3 and 10 from Tier 1) and 400 open rows. The July 12 note's "185/185 exact rows ... 0/400 open rows" was correct. The July 15 "count correction" read the exact rows as the orbits at the minimum | Item removed from the paper. Dated corrections appended to `docs/science/2026-07-12-p5-tier0-characterization.md` and `docs/science/2026-07-15-p5-dh-characterization-fable.md`. The content-addressed evidence artifact that repeats the misreading (`claims/evidence/85e7a63cdadb48c2.json`, field `count_correction`) is left unedited |
| N3 | "claims and verifiers are identified by content hashes": claims have readable names | `validate_id` in `src/empiricist/claims/model.py`; `Artifact.id` is a blake3 content hash in `src/empiricist/ledger/models.py` | "artifacts and verifiers are identified by content hashes, a verifier by the hashes of its code and of its test suite" |
| N4 | "A language model first conjectured the characterization" (OLD: "first proposed by a language model, Fable 5") is contradicted by the records | The July 12 note's header and the July 15 note say that the harness author (Opus) made the distance-hereditary leap while mining the full 585-orbit table. Fable re-derived it on July 15 from the 44 orbits with n <= 7, with no class names. The spec's author line gives the July model as Claude Opus 4.8. The table itself came from the deterministic `tier0_search`/`tier1_search` (`docs/science/2026-07-07-p5-tier0-tier1-results.md`), so "Fable classified the orbits" in the acknowledgments was also wrong. Fable's searcher role proposed the nine later constructions | Introduction: the coding assistant used to build the system first noticed the characterization in the table of all 585 orbits, and a language model working within the system then re-derived it from the labeled orbits with n <= 7 alone and wrote the Lean proofs. Sec. VI opens the account of the discovery with the same fact. Acknowledgments: Claude Code (model Claude Opus 4.8) built the first version of Empiricist, including its exhaustive search, and first noticed the pattern; Fable proposed the nine later constructions, re-derived the characterization from the orbits with n <= 7 and wrote the Lean proofs. The Lean modules named in the paper are recorded as Fable-authored (`docs/science/2026-07-16-p5-dh-forward-formalized.md`) |
| S8 note | The code ranks REFUTED outside the strength order ("terminal, not weakest") | `src/empiricist/ledger/models.py` | "heuristic, conjectured, verified up to a given size, certified or formalized, in increasing order of strength, or as refuted" |
| Outside the brief | The bundle was stale (README edited after the build); the README called the ledger "the system described in Sec. VI" | | Rebuilt after the last edit; the README now says "part of the system" |
| Outside the brief | Some July evidence rows have `golden_suite_hash: null` | Golden-suite certification existed from 2026-07-06 (commits b33445f, 76caecd). The null fields are records migrated from the pre-hardening ledger, which did not store the hash | No change to the paper |

A Codex scientific-equivalence check of the final text against OLD, following the practice of the
author's other papers, is in `../codex-prose-check/`.

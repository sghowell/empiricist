I found **no blocking or major error in the main theorems for connected graphs with \(n\ge3\)**. The fusion rule, counting argument, rank-width proof, constructive characterization, and normal form withstand the requested edge cases. I reproduced every entry of Table I. The corrections below concern omitted hypotheses, overbroad descriptions, and supplement reporting. I inspected the Lean statements and proofs but did not run Lake or independently repeat kernel certification. No files were modified. :codex-file-citation{path="/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.pdf" purpose="source"}

1. **Minor — Missing size restriction.**  
   **Location:** Abstract, [main.tex:40](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:40), “At rank-width one the bound is attained”; orbit counts at lines 47, 125–126, 133 and 434–435.  
   The characterization requires \(n\ge3\). Without that restriction, \(K_2\) is distance-hereditary and has rank-width one, but cannot satisfy \(F(K_2)=2-3=-1\). Likewise, 585 and 44 count connected orbits on **3–9** and **3–7** vertices, respectively, rather than all orders up to those limits.  
   **Fix:** State the \(n\ge3\) domain explicitly in the abstract and use the precise intervals for the counts.

2. **Minor — Independence of verification is described too broadly.**  
   **Location:** Section V, [main.tex:362](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:362), “Each recorded construction is replayed by two stabilizer engines that share no code”; also lines 124 and 423.  
   The stabilizer fusion implementations are separate, but the construction checks share `apply_construction`, graph-level local complementation, and `lc_orbit_key`. In particular, [construction.py:106](/Users/seanhowell/dev/empiricist/src/empiricist/domain/p5/construction.py:106) implements a local-complementation step by extracting a graph, applying the shared graph rewrite, and preparing a fresh engine state. Agreement therefore does not independently validate that shared machinery. This does not invalidate the reproduced upper bounds.  
   **Fix:** Say “independent stabilizer fusion and extraction implementations, sharing construction replay and graph canonicalization.”

3. **Minor — The rank-width output incorrectly calls lower bounds “tight.”**  
   **Location:** Section V’s supporting script, [rankwidth_check.py:103](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/anc/scripts/rankwidth_check.py:103), especially line 108.  
   For open rows, `f_value` is the stored **lower bound**, yet the script treats it as an exact fusion cost when computing “tight” or “slack.” Thus open eight-vertex rows are printed as “tight,” while the rank-width-three row receives “slack −3.” Neither is a valid statement about actual slack.  
   **Fix:** Pass exactness into `report`. Report tightness only for exact costs; for open rows report the old bound, the rank-width bound, and their maximum. The computed rank-widths and Table I remain correct.

4. **Minor — The supplement’s table map has an incorrect count and omits the final aggregation.**  
   **Location:** Data availability, [main.tex:509](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:509), “scripts that re-derive every number”; [anc/README.md:13](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/anc/README.md:13).  
   The README says the original tablebase contains sixteen exact rows above the floor. It contains **ten**; the nine later constructions bring the total to nineteen. Moreover, the advertised `table_facts.py` command prints the original tablebase counts, not final Table I. Obtaining that table requires joining the nine later certificates by orbit and applying the rank-width improvements to 25 open rows.  
   **Fix:** Change “sixteen” to “ten” and document that aggregation explicitly, preferably with a command that prints final Table I.

5. **Minor — The checksum manifest does not verify.**  
   **Location:** Data availability, main.tex:512; [anc/SHA256SUMS:1](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/anc/SHA256SUMS:1).  
   The recorded README digest begins `277a7cfe…`, whereas the current file hashes to `c014f72a…`. The other 47 listed digests match.  
   **Fix:** Regenerate the manifest after finalizing the ancillary files.

6. **Minor — The bounded-rank-width algorithm claim needs qualification.**  
   **Location:** Related work, [main.tex:476](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:476), “Transformation problems … efficient at bounded rank-width.”  
   The cited general transformation result requires bounded source rank-width **and bounded target size**. Its runtime is \(O(f(|G'|,\operatorname{rw}(G))|G|^3)\). GHZ targets admit a stronger special-case result without that target-size restriction. [Dahlberg–Wehner, Theorems 1.1–1.2](https://arxiv.org/html/1805.05305).  
   **Fix:** State both parameters for general targets and distinguish the GHZ special case; cite the corresponding result directly.

7. **Nit — Equation (1) omits a global phase.**  
   **Location:** Section II, [main.tex:150](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:150).  
   With the explicit graph-vector convention at line 143, the displayed equality is not exact. Its right-hand side equals
   \[
   e^{i\pi(\deg(v)-1)/4}\,|\tau_v(G)\rangle.
   \]
   For example, complementing the center of \(P_3\) gives phase \(e^{i\pi/4}\).  
   **Fix:** Add “up to global phase,” or insert the inverse phase factor. No subsequent mathematical conclusion changes.

8. **Nit — The implication names are reversed.**  
   **Location:** Introduction, [main.tex:103](/Users/seanhowell/dev/empiricist/docs/paper/arxiv/main.tex:103), “The reverse direction of Theorem…”  
   Relative to the theorem’s displayed order and its explicitly labeled proof, the rank-width argument proves \(F=n-3\Rightarrow\mathrm{DH}\), while the split-decomposition construction proves \(\mathrm{DH}\Rightarrow F=n-3\).  
   **Fix:** Swap “reverse” and “forward” in this sentence.

**Checks that passed**

- **Disjoint fusion and merge rules:** The anticommutation statements, generator replacements, removal of measured-qubit support, and outcome-dependent Pauli signs are correct. Leaf-\(P_3\), center-\(P_3\), and \(K_3\) merges give pendant, false-twin, and true-twin additions.

- **Counting bound:** Connected output forces all survivors into one resource/fusion component. Both \(f_0=n-3+3t\) and \(f\equiv n\pmod3\) follow correctly. Loops, parallel edges, and components without survivors cause no exception.

- **Theorem 1:** Moving single-qubit gates and commuting disjoint fusions is valid. The resource-degree bound, pruning and suppression, and correspondence between resulting tree cuts and spanning-tree cuts work. At most \(t+1\) fusion bras cross each relevant cut, giving Schmidt rank at most \(2^{t+1}\). Local Cliffords and a consistent relabeling preserve the required cut ranks.

- **Theorem 2:** Both directions are sound. Pendant/twin pruning of a connected distance-hereditary graph can stop at a connected three-vertex graph while preserving connected intermediates. The three merges realize the reverse construction with exactly \(n-3\) fusions.

- **Appendix A:** The two Clifford images generate \(S_3\); the chosen neighbor persists under both local complementations. Frame absorption, the breadth-first merge order, and the connectivity induction are valid. The 36 frame pairs reduce to six measurement classes when generator/product permutations and outcome relabelings are allowed.

- **Lean scope:** `ProducibleByExt`, `PendantTwinBuildable`, `dh_characterization`, `dh_forward`, `dh_min_fusions`, `floor_schedule_iff_dh`, and the family statements match Section IV’s qualified descriptions. `fusion_cost_lower_bound` is a conditional arithmetic theorem about the stated counting assumptions. The paper correctly acknowledges that the intrinsic distance-hereditary identification, quantum fusion semantics, and rank-width proof are not formalized. Supplementary source copies and version pins match.

- **Distance heredity and rank-width:** Both supplied standard-library scripts reproduced their saved results. Independently checking distances in connected induced subgraphs agreed with the pendant/twin test on all 585 representatives. Independent cut-rank calculations and a subset dynamic program agreed with the rank-width results. The enumerator generates the expected distinct binary rank-decomposition trees.

- **Table I and witnesses:** Every cell reconciles. The five row totals are \(175,16,3,364,27\). The 25 rank-width-three orbits comprise one at eight vertices and 24 at nine vertices. All 185 original exact witnesses and nine later witnesses replayed successfully through both engines, with independently checked final orbit membership. The 93 tree-orbit count also checks out.

- **Rotated Tier 1:** A read-only rerun of the frame/fusion loop, supplied with independently LC-expanded inputs, found no additional orbits: all 36 frame pairs for \(n=3,4,5\), and the six reduced classes for \(n=6,7\). Additional randomized merge, fusion-commutation, and intra-component fusion checks passed.
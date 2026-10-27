# P5: the F=N−3 characterization, re-derived by Fable (spec-clean conjecture)

**Date:** 2026-07-15 · **Problem:** P5(ii)/(iii), structure · **Method:** Fable-5
hypothesis-generation over the VERIFIED_N tablebase + deterministic grounding.

## Why this note exists

The extremal-class characterization `F(G)=N−3 ⟺ distance-hereditary` was first written
up in the M17 note (`2026-07-12-p5-tier0-characterization.md`). Under the project's
model-attribution rule, that hypothesis was **out of spec**: the "it's distance-hereditary
/ rank-width 1" leap was made by the *harness author* (Opus), not by the model. Creative
mathematical hypothesis-generation must route through **Fable 5**. This note records the
re-derivation with Fable generating the hypothesis and the harness grounding it
deterministically.

## Method

1. **Labeled data (Fable's input).** All connected graph-state LC-orbits for n≤7 — 44
   orbits, given only as edge lists + a boolean `extremal` (= attains `F=N−3`). No
   invariant, class name, or the words *distance-hereditary / rank-width / pendant / twin*
   appeared in the prompt. Fable was told only that the target property is a
   local-complementation invariant (true, since `F` is).
2. **Fable's hypothesis** (run `dh-structural-conjecture-fable-v2`). Fable proposed, with
   high confidence, that the extremal orbits are **exactly the distance-hereditary graphs
   (= connected graphs of rank-width 1 = C₅-vertex-minor-free)**. It supplied all four
   standard equivalent characterizations (metric; rank-width ≤ 1; forbidden induced
   {house, gem, domino, Cₖ≥5}; pendant/true-twin/false-twin elimination), cited the correct
   LC-invariance results (Bouchet 1988; Oum 2005), identified the house graph as the
   smallest obstruction (the n=5 non-extremal orbit *is* the LC-orbit of C₅), and proposed
   the physical mechanism: rank-width 1 ⟺ split/GHZ-decomposable, which is what enables the
   `N−3` fusion floor.
3. **Deterministic grounding (harness).** A distance-hereditary checker (Bandelt–Mulder
   pendant/twin elimination — precisely Fable's check recipe #4) was run on the full
   585-orbit VERIFIED_N tablebase (`dc8649…f25`), comparing `is_DH` against
   `extremal = (F==N−3)`.

## Result

| set | orbits | extremal | distance-hereditary | mismatches |
|---|---|---|---|---|
| train (n≤7, Fable saw) | 44 | 29 | 29 | **0** |
| held-out (n=8,9, unseen) | 541 | 146 | 146 | **0** |
| all (n≤9) | 585 | 175 | 175 | **0** |

`F(G)=N−3 ⟺ G distance-hereditary` holds on **every one of the 585 orbits, zero
exceptions**, including the 541 held-out n=8,9 orbits Fable never saw — the conjecture
generalizes cleanly past its training data. Recorded as a **CONJECTURED** artifact
(`85e7a63c…`, P5) in `runs/p5-live`, promoted by this grounding as its PASS evidence.

## Count correction

The Opus-era M17 note stated the split as **185 exact / 400 open**. That is an arithmetic
error. The true split from the tablebase is **175 extremal / 410 open**, matching the M5c
per-`n` extremal counts exactly (1+2+3+8+15+42+104 = 175). The characterization itself was
never in doubt — only the tally was wrong; the deterministic recheck fixes it.

**Correction (2026-10-26).** This count correction is wrong. "185 exact / 400 open" in the M17 note
was the correct exact/open split of the tablebase: 185 exact rows (175 Tier-0 rows at `F=N−3` and 10
Tier-1 rows at `F=N`) and 400 open rows. 175/410 is the split into orbits that do and do not attain
`F=N−3`, as the table above shows. Nothing was mis-tallied in the M17 note. The `count_correction`
field of the content-addressed evidence artifact `claims/evidence/85e7a63cdadb48c2.json` repeats the
error and is left unedited; this note is the correction of record. Found by the fidelity review of the
DH paper's prose revision (`docs/paper/arxiv/reviews/prose-fidelity/RECHECK.md`, item N2).

## Status of the two directions (unchanged)

- **DH ⟹ F=N−3** — a general construction (pendant = the formalized leaf-merge; twin = the
  new move). Formalizable; the twin-step producibility lemma is the open work.
- **F=N−3 ⟹ DH** — needs rank-width / vertex-minor machinery mathlib lacks. Open.

The five formalized families (paths, stars, trees, K_N, K_{m,n}) are all distance-hereditary
— instances of this one structural law, which is *why* they attain the bound.

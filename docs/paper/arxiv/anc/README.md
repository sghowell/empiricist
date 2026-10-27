# Ancillary files: Distance-hereditary graphs characterize minimum-fusion synthesis of graph states

Everything here is also in the repository https://github.com/sghowell/empiricist (MIT license);
the paper's tagged commit is named in the arXiv comments field. `SHA256SUMS` lists every file.

## Map from the paper to the files

| Statement in the paper | File | How to check |
|---|---|---|
| The model characterization (`dh_characterization`), the forward direction (`dh_forward`, `dh_min_fusions`), the center-merge (`ghz3CenterMerge_iso_addFalseTwin`), the true-twin identity (`addPendant_localComplement_center`), the lower bound (`fusion_cost_lower_bound`), trees (`tree_min_fusions`) | `lean/EmpiricistLean/*.lean`, checked by `lean/Paper/LibraryAxioms.lean` | `lean/check_axioms.sh` |
| Paths, stars, complete graphs, complete bipartite graphs | `lean/Paper/PathGraph.lean`, `Star.lean`, `Complete.lean`, `CompleteBipartite.lean` | `lean/check_axioms.sh` |
| The over-approximating schedule model (`floor_schedule_iff_dh`, the remark after the proof of the main theorem) | `lean/Paper/FloorBridge.lean` | `lean/check_axioms.sh` |
| Table I, the 585 orbits, distance-hereditary = extremal on every orbit | `data/tablebase.json` | `python3 scripts/table_facts.py data/tablebase.json` (standard library only); output in `scripts/table_facts.log` |
| The nineteen exact values above the bound | `data/tablebase.json` (sixteen rows from Tier 1 and the bound), `data/certified_orbits/*` (the nine later constructions and their ledger records) | `scripts/replay_constructions.py` (needs the repository); output in `scripts/replay_constructions.log` |
| Rank-width does not determine F above the bound | `data/tablebase.json` | `cd scripts && python3 rankwidth_check.py ../data/tablebase.json`; output in `scripts/rankwidth_check.log` |
| Tier 1 is unchanged by single-qubit Cliffords on the fused qubits | `scripts/rotated_tier1.py` | needs the repository; output in `scripts/rotated_tier1.log` |

## Lean

`lean/` is a self-contained Lake project pinned to Lean `v4.31.0` and mathlib `v4.31.0`
(`lake-manifest.json`). The library modules are copied unchanged from
`lean/EmpiricistLean/EmpiricistLean/` of the repository; `Paper/*.lean` are the gate-certified
modules recorded in the repository's claims ledger (`claims/evidence/`), copied unchanged:

| File | Ledger artifact |
|---|---|
| `Paper/PathGraph.lean` | `claims/evidence/c3926eee6182df38.lean` (`P5.Empiricist.pathGraph_min_fusions`) |
| `Paper/Star.lean` | `claims/evidence/60b904be671f0d9a.lean` (`P5.Empiricist.star_min_fusions`) |
| `Paper/Complete.lean` | `claims/evidence/ae693e034fa7b3e4.lean` (`P5.Empiricist.complete_min_fusions`) |
| `Paper/CompleteBipartite.lean` | `claims/evidence/ff6c58d78cf346fe.lean` (`P5.Empiricist.completeBipartite_min_fusions`) |
| `Paper/FloorBridge.lean` | `claims/evidence/c84d528bedee2ae0.lean` (`P5.Empiricist.floor_schedule_iff_dh`) |

The ledger's artifacts for `dh_characterization`, the center-merge, the true-twin identity, the
lower bound and the tree theorem are byte-identical to the library modules `DHCharacterization`,
`CenterMerge`, `TrueTwin`, `Foundation` and `TreeThm`.

To check (requires [elan](https://github.com/leanprover/elan)):

```
cd lean
lake exe cache get     # prebuilt mathlib for the pinned release
./check_axioms.sh      # builds the library, then prints the axioms of every declaration
```

Every declaration must report only `propext`, `Classical.choice` and `Quot.sound` (the lower
bound uses only `propext` and `Quot.sound`). With prebuilt mathlib the check takes about a
minute.

## Data

`data/tablebase.json` is the certified tablebase artifact (`claims/evidence/dc8649519e5f8694.json`
in the repository): one row per connected local-complementation orbit with 3 to 9 vertices, with
`F` and `exact` (an exact value, with a `witness` schedule), or `lower_bound` (an open row). A
witness lists the number of resources (copies of the three-qubit GHZ state, qubits numbered
consecutively) and the steps: `lc` (local complementation at a qubit) and `fuse` (a fusion of
qubits `a` and `b`). `data/certified_orbits/` holds the nine later constructions above the
bound in the same format (`fuse` and `lc` steps with their qubit arguments), each with the
ledger record of its claim (`.yaml`) and its verifier evidence.

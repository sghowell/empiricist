"""Assemble Table I of the paper from the tablebase, the nine later constructions and the
rank-width bound.

Run from a clone of https://github.com/sghowell/empiricist (it uses the repository's `empiricist`
package for the local-complementation orbit key):

    uv run python docs/paper/arxiv/anc/scripts/final_table.py

Steps: (1) the tablebase gives exact values (F = n - 3 at Tier 0, F = n at Tier 1) and lower bounds
for the open rows; (2) each later construction is matched to its tablebase row by the canonical key
of the local-complementation orbit (the minimum nauty certificate over the orbit) and makes that row
exact; (3) an open row whose rank-width is three gets the lower bound n + 3 from the rank-width bound
F >= n + 3 rw - 6.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rankwidth_check import rank_width  # noqa: E402

from empiricist.domain.p5.canonical import lc_orbit_key  # noqa: E402
from empiricist.domain.p5.graphstate import GraphState  # noqa: E402

rows = json.loads((HERE.parent / "data" / "tablebase.json").read_text())["rows"]
keyed = {}
for r in rows:
    if not r["exact"]:
        keyed[lc_orbit_key(GraphState(r["n"], r["representative_edges"]))] = r

matched = 0
for f in sorted((HERE.parent / "data" / "certified_orbits").glob("*.yaml")):
    text = " ".join(f.read_text().split())
    m = re.search(r"F\(G\) = (\d+) for the LC-orbit ([0-9a-f]+) of connected (\d+)-qubit.*?"
                  r"representative edges (\[.*?\])\)", text)
    fv, key, n, edges = int(m.group(1)), m.group(2), int(m.group(3)), eval(m.group(4))
    assert lc_orbit_key(GraphState(n, edges)) == key, f"{f.name}: orbit key mismatch"
    row = keyed[key]                       # the open tablebase row of this orbit
    assert row["n"] == n and row["lower_bound"] <= fv, f"{f.name}: inconsistent with the table"
    row["exact"], row["F"] = True, fv
    matched += 1

cells = Counter()
for r in rows:
    n = r["n"]
    if r["exact"]:
        tier = (r["F"] - (n - 3)) // 3
        cells[(["F = n - 3", "F = n", "F = n + 3"][tier], n)] += 1
    else:
        bound = max(r["lower_bound"], n + 3 * rank_width(n, r["representative_edges"], lower=2) - 6)
        cells[("open, F >= n" if bound == n else "open, F >= n + 3", n)] += 1
    cells[("connected orbits", n)] += 1

print(f"later constructions matched to tablebase rows: {matched}")
labels = ["connected orbits", "F = n - 3", "F = n", "F = n + 3", "open, F >= n", "open, F >= n + 3"]
ns = range(3, 10)
print(f"{'':18}" + "".join(f"{n:>5}" for n in ns) + "  total")
for lab in labels:
    vals = [cells[(lab, n)] for n in ns]
    print(f"{lab:18}" + "".join(f"{v:>5}" for v in vals) + f"  {sum(vals):>5}")

"""Replay the certified constructions above the bound with both stabilizer engines.

Run from a clone of https://github.com/sghowell/empiricist at the commit named in the README
(it uses the repository's `empiricist` package):

    uv run python docs/paper/arxiv/anc/scripts/replay_constructions.py

For each construction in ../data/certified_orbits, the two independent engines (a stim tableau
simulator and a GF(2) implementation) replay the schedule; the construction passes when both
reach the target's local-complementation orbit and agree with each other. Prints the number of
fusions, which is the certified upper bound on F; the matching lower bounds come from the
exclusion of the lower tiers in the tablebase.
"""
import json
from pathlib import Path

from empiricist.packs.ftfbqc.adapters import AgreedFusionAdapter

HERE = Path(__file__).resolve().parent
for path in sorted((HERE.parent / "data" / "certified_orbits").glob("*.construction.json")):
    payload = path.read_bytes()
    obj = json.loads(payload)
    fusions = sum(1 for s in obj["steps"] if s["op"] == "fuse")
    r = AgreedFusionAdapter(HERE).verify_bytes(payload)
    print(f"{path.name.replace('.construction.json', ''):32} n={obj['target_n']} "
          f"fusions={fusions} resources={obj['resources']} -> {r.verdict.value}")

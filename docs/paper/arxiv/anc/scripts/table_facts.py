"""Re-derive the paper's tablebase numbers from the certified tablebase JSON.

Usage: python table_facts.py path/to/tablebase.json

Prints, per vertex count N: the number of connected local-complementation orbits, how many
attain F = N - 3 (extremal), how many are distance-hereditary by Bandelt-Mulder pendant/twin
elimination, and the exact values above the floor. Pure standard library; the elimination
is written from the definition (a pendant vertex, or a pair of twins -- vertices with equal
open or closed neighbourhoods -- can be removed; a graph is distance-hereditary iff repeated
removal reaches a single vertex).
"""
import json
import sys
from collections import Counter, defaultdict


def is_distance_hereditary(n: int, edges: list) -> bool:
    adj = {v: set() for v in range(n)}
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
    alive = set(range(n))
    while len(alive) > 1:
        removed = False
        for v in sorted(alive):
            nv = adj[v] & alive
            if len(nv) == 1:                                   # pendant vertex
                alive.discard(v)
                removed = True
                break
            for u in sorted(alive):
                if u == v:
                    continue
                nu = adj[u] & alive
                if nu - {v} == nv - {u}:                       # false or true twins
                    alive.discard(v)
                    removed = True
                    break
            if removed:
                break
        if not removed:
            return False
    return True


def main(path: str) -> None:
    d = json.load(open(path))
    rows = d["rows"]
    by_n = defaultdict(list)
    for r in rows:
        by_n[r["n"]].append(r)
    tot = Counter()
    print(f"{'N':>2} {'orbits':>6} {'F=N-3':>6} {'DH':>4} {'DH=extremal':>11}  exact values above the floor")
    for n in sorted(by_n):
        rs = by_n[n]
        ext = [r for r in rs if r["exact"] and r["F"] == n - 3]
        dh = [r for r in rs if is_distance_hereditary(n, r["representative_edges"])]
        agree = all((r["exact"] and r["F"] == n - 3) == is_distance_hereditary(n, r["representative_edges"])
                    for r in rs)
        above = Counter(r["F"] for r in rs if r["exact"] and r["F"] > n - 3)
        lower = Counter(r["lower_bound"] for r in rs if not r["exact"])
        tot.update(orbits=len(rs), extremal=len(ext), dh=len(dh))
        print(f"{n:>2} {len(rs):>6} {len(ext):>6} {len(dh):>4} {str(agree):>11}  "
              f"exact above floor {dict(sorted(above.items()))}; open rows by lower bound {dict(sorted(lower.items()))}")
    print(f"total orbits {tot['orbits']}, extremal {tot['extremal']}, distance-hereditary {tot['dh']}")
    print("per_n_totals in file:", d.get("per_n_totals"))
    print("schema_version", d.get("schema_version"), "n_max", d.get("n_max"), "tier1_n_max", d.get("tier1_n_max"))


if __name__ == "__main__":
    main(sys.argv[1])

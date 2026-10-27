"""Rank-width facts behind the paper's rank-width bound F >= n + 3 rw - 6 and its tightness.

For every orbit above the minimum F = n - 3 in the tablebase (exact or open) and for the nine later
certified constructions, print whether it is distance-hereditary, its linear rank-width (brute force
over vertex orderings, n <= 8) and its rank-width (brute force over all labeled unrooted binary trees
with the vertices as leaves; (2n-5)!! trees), each from GF(2) cut-ranks. For an exact value, say
whether the bound n + 3 rw - 6 is attained; for an open row, print the search's lower bound, the
rank-width bound and their maximum. The summary counts rows by (n, exact/open, rank-width).

Usage: python rankwidth_check.py path/to/tablebase.json [path/to/certified_orbits]
"""
import itertools
import json
import sys

from table_facts import is_distance_hereditary


def gf2_rank(rows: list[int]) -> int:
    rank, rows = 0, [r for r in rows if r]
    while rows:
        pivot = max(rows)
        top = pivot.bit_length() - 1
        rows = [r ^ pivot if (r >> top) & 1 else r for r in rows if r != pivot]
        rows = [r for r in rows if r]
        rank += 1
    return rank


def cut_rank(adj: list[int], side: set[int], n: int) -> int:
    other = [v for v in range(n) if v not in side]
    mask = 0
    for i, v in enumerate(other):
        mask |= 1 << v
    return gf2_rank([adj[u] & mask for u in side])


def linear_rank_width(n: int, edges: list) -> int:
    adj = [0] * n
    for u, v in edges:
        adj[u] |= 1 << v
        adj[v] |= 1 << u
    best = n
    for order in itertools.permutations(range(n)):
        width, prefix = 0, set()
        for v in order[:-1]:
            prefix.add(v)
            width = max(width, cut_rank(adj, prefix, n))
            if width >= best:
                break
        best = min(best, width)
    return best


def binary_trees(n: int):
    """All labeled unrooted binary trees with leaves 0..n-1 (n >= 3), as edge lists over nodes
    0..n-1 (leaves) and n.. (internal), by inserting leaf k on every edge of each tree on k leaves."""
    trees = [[(0, n), (1, n), (2, n)]]
    nxt = n + 1
    for k in range(3, n):
        new = []
        for edges in trees:
            internal = max(max(e) for e in edges) + 1
            for i, (u, v) in enumerate(edges):
                rest = edges[:i] + edges[i + 1:]
                new.append(rest + [(u, internal), (internal, v), (k, internal)])
        trees = new
    return trees


def rank_width(n: int, edges: list, lower: int = 1) -> int:
    """Exact rank-width; stops early once a tree of width `lower` (a known lower bound) is found."""
    adj = [0] * n
    for u, v in edges:
        adj[u] |= 1 << v
        adj[v] |= 1 << u
    best = n
    for tree in binary_trees(n):
        nbrs = {}
        for u, v in tree:
            nbrs.setdefault(u, []).append(v)
            nbrs.setdefault(v, []).append(u)
        width = 0
        for u, v in tree:
            side, stack, seen = set(), [u], {u, v}       # the leaves on u's side of edge uv
            while stack:
                x = stack.pop()
                if x < n:
                    side.add(x)
                for y in nbrs[x]:
                    if y not in seen:
                        seen.add(y)
                        stack.append(y)
            if 0 < len(side) < n:
                width = max(width, cut_rank(adj, side, n))
            if width >= best:
                break
        best = min(best, width)
        if best <= lower:
            return best
    return best


def report(n: int, edges: list, label: str, f_value: int, exact: bool) -> None:
    dh = is_distance_hereditary(n, edges)
    rw = rank_width(n, edges, lower=1 if dh else 2)
    lrw = linear_rank_width(n, edges) if n <= 8 else -1
    bound = n + 3 * rw - 6
    head = f"n={n} {label}: distance-hereditary {dh}; rank-width {rw}; linear rank-width {lrw}; "
    if exact:
        tight = "attained" if f_value == bound else f"missed by {f_value - bound}"
        print(head + f"F = {f_value}; rank-width bound {bound} ({tight})")
    else:
        print(head + f"open; search bound F >= {f_value}; rank-width bound F >= {bound}; "
                     f"combined F >= {max(f_value, bound)}")


def main(path: str, certified_dir: str | None) -> None:
    import glob
    import re
    from collections import Counter
    rows = json.load(open(path))["rows"]
    summary = Counter()
    for r in rows:
        n = r["n"]
        value = r["F"] if r["exact"] else r["lower_bound"]
        if value <= n - 3:
            continue
        e = r["representative_edges"]
        rw = rank_width(n, e, lower=2)
        summary[(n, "exact" if r["exact"] else "open", rw)] += 1
        if n <= 8:
            report(n, e, f"orbit ..{r['orbit_id'][-8:]}", value, r["exact"])
    print("summary of rows above the bound, (n, exact/open, rank-width): count")
    for k in sorted(summary):
        n, kind, rw = k
        print(f"  n={n} {kind:5} rank-width {rw}: {summary[k]} (rank-width bound F >= {n + 3 * rw - 6})")
    if certified_dir:
        for f in sorted(glob.glob(f"{certified_dir}/*.yaml")):
            text = " ".join(open(f).read().split())
            m = re.search(r"F\(G\) = (\d+) for the LC-orbit [0-9a-f]+ of connected (\d+)-qubit.*?"
                          r"representative edges (\[.*?\])\)", text)
            if m:
                fv, n, edges = int(m.group(1)), int(m.group(2)), eval(m.group(3))
                report(n, edges, Path(f).stem + " (later construction)", fv, True)


if __name__ == "__main__":
    from pathlib import Path
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)

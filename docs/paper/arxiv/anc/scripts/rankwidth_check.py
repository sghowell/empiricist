"""Rank-width facts behind the paper's remark that rank-width does not determine F above the
floor. For every orbit whose certified lower bound is N + 3 (or more), print whether it is
distance-hereditary (rank-width 1) and its linear rank-width, computed exactly by brute force
over vertex orderings (cut-rank over GF(2) of every prefix). Not distance-hereditary and linear
rank-width 2 together give rank-width exactly 2.

Usage: python rankwidth_check.py path/to/tablebase.json
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


def main(path: str) -> None:
    rows = json.load(open(path))["rows"]
    for r in rows:
        n = r["n"]
        bound = r["F"] if r["exact"] else r["lower_bound"]
        if bound < n + 3:
            continue
        e = r["representative_edges"]
        dh = is_distance_hereditary(n, e)
        print(f"N={n} orbit {r['orbit_id'][-12:]}: {'F =' if r['exact'] else 'F >='} {bound}; "
              f"distance-hereditary {dh}; linear rank-width {linear_rank_width(n, e)}; edges {e}")


if __name__ == "__main__":
    main(sys.argv[1])

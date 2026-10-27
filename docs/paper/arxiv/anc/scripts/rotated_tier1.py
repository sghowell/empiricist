"""Does Tier-1 lose generality by fusing in one fixed Bell basis?

The model lets a single-qubit Clifford act on each fused qubit before a fusion. The fusion
measurement {X_a Z_b, Z_a X_b} is invariant under a 6-element subgroup K of S3 x S3 (frames
mod Pauli), so the inequivalent pre-rotations are represented by (sigma on a, identity on b),
sigma in S3. Tier-0's LC closure visits every graph of each reached LC orbit; this script
re-runs Tier-1's single intra fusion with all six sigma on qubit a (and, for n <= 5, all 36
pairs on (a, b) as a cross-check of the K-reduction) and reports any size-n orbit that only a
rotated intra fusion reaches.
"""
import sys
import time

import networkx as nx

from empiricist.domain.p5.canonical import iso_certificate
from empiricist.domain.p5.fusion_gf2 import GF2Engine, GF2State
from empiricist.domain.p5.tablebase import enumerate_connected_orbits, tier0_search


def rot(state: GF2State, q: int, word: str) -> GF2State:
    """Apply a word in {H, S} to qubit id q (signs ignored: frames mod Pauli)."""
    j = state.active.index(q)
    bit = 1 << j
    gens = list(state.generators)
    for g in word:
        out = []
        for x, z in gens:
            xb, zb = x & bit, z & bit
            if g == "H":                          # X <-> Z
                x = (x & ~bit) | zb
                z = (z & ~bit) | xb
            elif g == "S":                        # X -> Y: z_q += x_q
                z = z ^ xb
            out.append((x, z))
        gens = out
    return GF2State(generators=tuple(gens), active=state.active)


S3 = ["", "H", "S", "HS", "SH", "HSH"]           # the six classes of single-qubit Cliffords mod Pauli


def main(n_max: int) -> None:
    t_start = time.monotonic()
    t0 = tier0_search(n_max + 2)
    by_size: dict[int, list] = {}
    for cert, g in t0._visited.items():
        by_size.setdefault(g.n, []).append((cert, g))
    eng = GF2Engine()
    for n in range(3, n_max + 1):
        m = n + 2
        enum_n = enumerate_connected_orbits(n)
        t0_roots = {enum_n.orbit_root(o.representative_cert) for o in t0.reachable[n]}
        std: set[bytes] = set()
        rotated: dict[bytes, tuple] = {}
        pairs = [(sa, sb) for sa in S3 for sb in S3] if n <= 5 else [(sa, "") for sa in S3]
        for _cert, g in by_size.get(m, []):
            base = eng.state_from_graph(g)
            for a in range(g.n):
                for b in range(a + 1, g.n):
                    for sa, sb in pairs:
                        st = rot(rot(base, a, sa), b, sb)
                        h = eng.to_graphstate(eng.fuse(st, a, b))
                        if h.n != n or not nx.is_connected(h.to_networkx()):
                            continue
                        root = enum_n.orbit_root(iso_certificate(h))
                        if sa == "" and sb == "":
                            std.add(root)
                        elif root not in rotated:
                            rotated[root] = (g.edges, a, b, sa, sb)
        only_rot = {r: w for r, w in rotated.items() if r not in std and r not in t0_roots}
        print(f"n={n}: orbits {enum_n.orbit_count}; tier0 {len(t0_roots)}; tier1 standard new "
              f"{len(std - t0_roots)}; reached only by a rotated intra fusion: {len(only_rot)} "
              f"({len(pairs)} frame classes, {time.monotonic() - t_start:.0f}s)", flush=True)
        for r, (edges, a, b, sa, sb) in list(only_rot.items())[:10]:
            print(f"   orbit {r.hex()[:16]} via m={m} graph {sorted(edges)} a={a} b={b} "
                  f"rot_a={sa or 'I'} rot_b={sb or 'I'}", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 7)

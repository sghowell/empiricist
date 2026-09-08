"""Which P5 families the claims ledger already settles with a FORMALIZED theorem.

The conjecturer's family set is small (path, cycle, star, complete). Three of the four
are Lean theorems in the repository ledger; a campaign that re-conjectures them wastes
its waves. This module names the theorem claim per family and confirms, against the
configured claims repository, that the claim is present, FORMALIZED and CURRENT before
the campaign treats the family as settled -- the ledger is memory, not this table.
"""
from __future__ import annotations

from pathlib import Path

SETTLED_FAMILIES: dict[str, str] = {
    "path": "P5.Empiricist.pathGraph_min_fusions",
    "star": "P5.Empiricist.star_min_fusions",
    "complete": "P5.Empiricist.complete_min_fusions",
}


def settled_families(claims_repo: Path | str | None) -> dict[str, str]:
    """family -> claim id, restricted to families whose theorem claim is present in
    `claims_repo` at FORMALIZED with standing CURRENT. Empty without a repository or
    when the repository cannot be read."""
    if claims_repo is None:
        return {}
    try:
        from empiricist.claims.check import check
        from empiricist.claims.model import load_all

        claims = load_all(claims_repo)
        standings = check(claims_repo).standings
    except Exception:  # noqa: BLE001 - an unreadable repository settles nothing
        return {}
    out: dict[str, str] = {}
    for family, cid in SETTLED_FAMILIES.items():
        c = claims.get(cid)
        if c is not None and c.level == "FORMALIZED" and standings.get(cid) == "CURRENT":
            out[family] = cid
    return out

"""The VERIFIED_N dataset artifact (M5c Task 3): assemble Tier-0 + Tier-1
results into a canonical JSON table of F(G) (exact or a lower bound) per
connected graph-state orbit, and ingest it into the ledger + CAS at
`Status.VERIFIED_N` -- the harness's first novel-science artifact.

**Row identity.** Every row's `orbit_id` lives in ONE canonical namespace:
the root returned by `tablebase.enumerate_connected_orbits(n).orbit_root`
(the independent, full-population union-find already used as the A3 Adcock
cross-check and as Tier-1's own "already reached at Tier-0?" arbiter). Tier-0
rows are re-rooted into this namespace here (their own `ReachableOrbit.
orbit_id` is a DIFFERENT identity -- tablebase's BFS union-find root -- not
directly comparable to Tier-1's enum-rooted ids); Tier-1 rows and "open" rows
already carry (or are computed against) this same root scheme. This is what
makes the per-n row set a genuine, checkable PARTITION of the Adcock
population: no orbit counted twice, none silently dropped.

**Trust discipline at ingest** (`ingest_dataset`): every EXACT row's witness
is re-verified via `verify_agreed` (both certified engines, no sampling --
every single row), the mod-3 ladder invariant and the per-n Adcock totals are
checked against the dataset's OWN embedded content (not re-derived from a
live search -- ingestion validates the ARTIFACT, not the process that made
it), and every check runs to completion BEFORE any ledger/store write: a
violation anywhere raises and nothing is ingested (no partial artifact, no
orphaned evidence row).
"""

from __future__ import annotations

import json
import sys
from typing import Any

from empiricist.domain.p5.canonical import iso_certificate
from empiricist.domain.p5.construction import Construction, FusionOp, LocalComplement
from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.tablebase import Tier0Result, Tier1Result, enumerate_connected_orbits
from empiricist.ledger.db import Ledger
from empiricist.ledger.ingest import ingest_artifact
from empiricist.ledger.models import Artifact, EvidenceRow, Status, Verdict
from empiricist.store import Store
from empiricist.verifiers.base import module_source_hash
from empiricist.verifiers.enum_fusion import EnumFusionVerifier
from empiricist.verifiers.goldens import suite_hash
from empiricist.verifiers.registry import Registry, verify_agreed
from empiricist.verifiers.stab_fusion import StabFusionVerifier

# Adcock's connected LC-orbit counts (matching test_p5_canonical.py's
# ADCOCK_CUMULATIVE / test_p5_tablebase.py's ADCOCK_TOTALS): the independent,
# literature-anchored ground truth `ingest_dataset` checks per-n row counts
# against -- deliberately NOT derived from anything computed this session,
# so a self-consistent-but-wrong dataset can't fool the check.
ADCOCK_TOTALS = {3: 1, 4: 2, 5: 4, 6: 11, 7: 26, 8: 101, 9: 440}


def _sorted_edges(gs: GraphState) -> list[list[int]]:
    return sorted(sorted(e) for e in gs.edges)


def _serialize_construction(c: Construction) -> dict[str, Any]:
    steps = []
    for s in c.steps:
        if isinstance(s, LocalComplement):
            steps.append({"op": "lc", "v": s.v})
        else:
            steps.append({"op": "fuse", "a": s.a, "b": s.b})
    return {
        "resources": c.resources,
        "steps": steps,
        "target_n": c.target.n,
        "target_edges": _sorted_edges(c.target),
    }


def _deserialize_construction(blob: dict[str, Any]) -> Construction:
    steps: list[FusionOp | LocalComplement] = []
    for s in blob["steps"]:
        if s["op"] == "lc":
            steps.append(LocalComplement(v=s["v"]))
        elif s["op"] == "fuse":
            steps.append(FusionOp(a=s["a"], b=s["b"]))
        else:
            raise ValueError(f"unknown construction step op: {s['op']!r}")
    target = GraphState(n=blob["target_n"], edges=[tuple(e) for e in blob["target_edges"]])
    return Construction(resources=blob["resources"], steps=tuple(steps), target=target)


def build_dataset(tier0: Tier0Result, tier1: Tier1Result) -> dict[str, Any]:
    """Assemble the canonical dataset dict: one row per connected orbit for
    every n in 3..tier0.n_max, tiered as:

    - "tier0": F = n - 3 exactly (Tier-0 all-merge reachability, L3).
    - "tier1": F = n exactly (Tier-1's one-intra-fusion resolution, L2+L4);
      only possible for n <= tier1.n_max.
    - "open": F unknown; `lower_bound` is n+3 if Tier-1 exhaustively searched
      this n and did not resolve it, else n (Tier-0's L2 floor only).

    Requires `tier0` to have MATERIALIZED unreachable-orbit representatives
    for every n <= tier0.n_max (`Tier0Result.unreachable_representatives`,
    which `tier0_search` only fills in for n <= 7) -- open rows need an
    actual representative graph, not just a count. Raises ValueError if
    `tier0.n_max` exceeds that materialized range.
    """
    for n in range(3, tier0.n_max + 1):
        n_unreachable = tier0.unreachable_count.get(n, 0)
        n_materialized = len(tier0.unreachable_representatives.get(n, []))
        if n_materialized != n_unreachable:
            raise ValueError(
                f"build_dataset: tier0.unreachable_representatives is not materialized for "
                f"n={n} ({n_unreachable} unreachable orbits, {n_materialized} representatives) "
                "-- Tier0Result only materializes these for n <= 7; pass a tier0 result with "
                "n_max <= 7 to build a full dataset."
            )

    rows: list[dict[str, Any]] = []
    per_n_totals: dict[str, int] = {}

    for n in range(3, tier0.n_max + 1):
        per_n_totals[str(n)] = tier0.total_orbit_count[n]
        enum_n = enumerate_connected_orbits(n)

        tier1_orbits = tier1.newly_resolved.get(n, []) if n <= tier1.n_max else []
        tier1_ids = {o.orbit_id for o in tier1_orbits}

        for orbit in tier0.reachable.get(n, []):
            root_hex = enum_n.orbit_root(orbit.representative_cert).hex()
            construction = tier0.witness(orbit.representative_cert)
            rows.append(
                {
                    "n": n,
                    "orbit_id": root_hex,
                    "representative_edges": _sorted_edges(orbit.representative),
                    "F": orbit.depth,
                    "lower_bound": orbit.depth,
                    "exact": True,
                    "tier": "tier0",
                    "witness": _serialize_construction(construction),
                }
            )

        for orbit in tier1_orbits:
            construction = tier1.witness(orbit)
            rows.append(
                {
                    "n": n,
                    "orbit_id": orbit.orbit_id,
                    "representative_edges": _sorted_edges(orbit.representative),
                    "F": orbit.f_value,
                    "lower_bound": orbit.f_value,
                    "exact": True,
                    "tier": "tier1",
                    "witness": _serialize_construction(construction),
                }
            )

        tier1_ran = n <= tier1.n_max
        open_lower_bound = n + 3 if tier1_ran else n
        for rep in tier0.unreachable_representatives.get(n, []):
            root_hex = enum_n.orbit_root(iso_certificate(rep)).hex()
            if root_hex in tier1_ids:
                continue  # already emitted above as a tier1 row
            rows.append(
                {
                    "n": n,
                    "orbit_id": root_hex,
                    "representative_edges": _sorted_edges(rep),
                    "F": None,
                    "lower_bound": open_lower_bound,
                    "exact": False,
                    "tier": "open",
                    "witness": None,
                }
            )

        n_rows = [r for r in rows if r["n"] == n]
        assert len({r["orbit_id"] for r in n_rows}) == len(n_rows) == tier0.total_orbit_count[n], (
            f"build_dataset: n={n} produced {len(n_rows)} rows "
            f"({len({r['orbit_id'] for r in n_rows})} distinct ids) but the independent "
            f"enumeration says {tier0.total_orbit_count[n]} connected orbits exist"
        )

    rows.sort(key=lambda r: (r["n"], r["tier"], r["orbit_id"]))

    return {
        "schema_version": 1,
        "n_max": tier0.n_max,
        "tier1_n_max": tier1.n_max,
        "per_n_totals": per_n_totals,
        "rows": rows,
    }


def to_canonical_json(dataset: dict[str, Any]) -> bytes:
    """Canonical content bytes for the dataset artifact: sorted keys, compact
    separators -- deterministic across processes so the blake3 CAS digest is
    stable for identical content."""
    return json.dumps(dataset, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _validate_dataset(dataset: dict[str, Any], registry: Registry) -> dict[str, Any]:
    """Raise ValueError on any invariant violation; return a per-n summary
    dict for the ingestion evidence row on success. Runs to completion
    (or raises) BEFORE `ingest_dataset` touches the ledger or the store."""
    rows = dataset.get("rows")
    if not rows:
        raise ValueError("dataset has no rows")
    per_n_totals = dataset.get("per_n_totals")
    if per_n_totals is None:
        raise ValueError("dataset missing per_n_totals")

    by_n: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_n.setdefault(row["n"], []).append(row)

    per_n_summary: dict[int, dict[str, int]] = {}
    for n, n_rows in sorted(by_n.items()):
        if n not in ADCOCK_TOTALS:
            raise ValueError(f"n={n}: no Adcock ground truth available -- cannot validate")

        for row in n_rows:
            f_value = row["F"]
            if row["exact"]:
                if f_value is None:
                    raise ValueError(f"n={n} orbit={row['orbit_id']}: exact=True but F is None")
                if f_value % 3 != (n - 3) % 3:
                    raise ValueError(
                        f"n={n} orbit={row['orbit_id']}: F={f_value} violates the mod-3 "
                        f"ladder invariant (F must be === {n - 3} (mod 3))"
                    )
                if row["tier"] == "tier0" and f_value != n - 3:
                    raise ValueError(
                        f"n={n} orbit={row['orbit_id']}: tier0 row claims F={f_value}, "
                        f"expected exactly N-3={n - 3}"
                    )
                elif row["tier"] == "tier1" and f_value != n:
                    raise ValueError(
                        f"n={n} orbit={row['orbit_id']}: tier1 row claims F={f_value}, "
                        f"expected exactly N={n}"
                    )
                elif row["tier"] not in ("tier0", "tier1"):
                    raise ValueError(
                        f"n={n} orbit={row['orbit_id']}: exact=True with unknown tier "
                        f"{row['tier']!r}"
                    )
            else:
                if f_value is not None:
                    raise ValueError(f"n={n} orbit={row['orbit_id']}: exact=False but F is set")
                if row["tier"] != "open":
                    raise ValueError(
                        f"n={n} orbit={row['orbit_id']}: exact=False but tier={row['tier']!r}"
                    )

        # per-n totals == Adcock (ground truth, not re-derived from a live search).
        if len(n_rows) != ADCOCK_TOTALS[n]:
            raise ValueError(
                f"n={n}: dataset has {len(n_rows)} rows, Adcock says {ADCOCK_TOTALS[n]} "
                "connected orbits -- row count mismatch"
            )
        claimed_total = per_n_totals.get(str(n))
        if claimed_total != ADCOCK_TOTALS[n]:
            raise ValueError(
                f"n={n}: dataset's own per_n_totals claims {claimed_total}, "
                f"Adcock says {ADCOCK_TOTALS[n]}"
            )

        # reachable-counts consistency: the rows must PARTITION the n orbits
        # -- no duplicate or missing orbit_id.
        ids = [row["orbit_id"] for row in n_rows]
        if len(set(ids)) != len(ids):
            raise ValueError(f"n={n}: duplicate orbit_id(s) among dataset rows")

        per_n_summary[n] = {
            "total": len(n_rows),
            "tier0": sum(1 for r in n_rows if r["tier"] == "tier0"),
            "tier1": sum(1 for r in n_rows if r["tier"] == "tier1"),
            "open": sum(1 for r in n_rows if r["tier"] == "open"),
        }

    # Witness re-verification: EVERY exact row, no sampling.
    exact_rows_verified = 0
    for row in rows:
        if not row["exact"]:
            continue
        construction = _deserialize_construction(row["witness"])
        if construction.fusion_count != row["F"]:
            raise ValueError(
                f"n={row['n']} orbit={row['orbit_id']}: witness fusion_count="
                f"{construction.fusion_count} != claimed F={row['F']}"
            )
        target_edges = _sorted_edges(construction.target)
        if construction.target.n != row["n"] or target_edges != row["representative_edges"]:
            raise ValueError(
                f"n={row['n']} orbit={row['orbit_id']}: witness target does not match "
                "the row's claimed representative"
            )
        result = verify_agreed(registry, construction)
        if result.verdict != Verdict.PASS:
            raise ValueError(
                f"n={row['n']} orbit={row['orbit_id']}: witness FAILED verify_agreed "
                f"({result.verdict.value}): {result.details}"
            )
        exact_rows_verified += 1

    return {"per_n": per_n_summary, "exact_rows_verified": exact_rows_verified}


def ingest_dataset(
    ledger: Ledger, store: Store, dataset: dict[str, Any], registry: Registry
) -> Artifact:
    """Verify `dataset` in full (every exact row's witness via
    `verify_agreed`, the mod-3 ladder invariant, per-n totals against Adcock,
    and row-partition consistency), then ingest it into `store` + `ledger`
    at `Status.VERIFIED_N` with `coverage='exhaustive'`, and record an
    evidence row (verdict PASS) documenting what was checked.

    RAISES ValueError on any violation -- no artifact and no evidence row
    are ever created for a dataset that fails validation."""
    summary = _validate_dataset(dataset, registry)

    content = to_canonical_json(dataset)
    n_max = dataset["n_max"]
    art = ingest_artifact(
        ledger,
        store,
        content=content,
        kind="dataset",
        problem="P5",
        title=f"GHZ3 min-fusion tablebase: F(G) for connected orbits, n=3..{n_max}",
        status=Status.VERIFIED_N,
        status_n=n_max,
        coverage="exhaustive",
    )

    ev = EvidenceRow(
        artifact_id=art.id,
        verifier="p5_tablebase_dataset_ingest",
        verifier_version="1.0",
        binary_hash=module_source_hash(sys.modules[__name__]),
        verdict=Verdict.PASS,
        details={
            "per_n": {str(n): counts for n, counts in summary["per_n"].items()},
            "exact_rows_verified": summary["exact_rows_verified"],
            "witness_verifiers": [StabFusionVerifier.name, EnumFusionVerifier.name],
            "golden_suite_hash": suite_hash(),
        },
    )
    ledger.record_evidence(ev)
    return art

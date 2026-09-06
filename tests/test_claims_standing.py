"""Standing derivation and propagation (M22a Task 3)."""
from __future__ import annotations

import pytest

from empiricist.claims.model import ClaimFile, ClaimSchemaError, EvidenceEntry
from empiricist.claims.standing import (
    ClaimGraphError,
    Finding,
    Receipt,
    compute_standing,
    dependency_graph,
    find_cycle,
    load_receipts,
    save_receipt,
    topological_order,
)


def _claim(cid, deps=(), supersedes=(), level="CERTIFIED", receipts=()):
    return ClaimFile(
        id=cid, problem="P", formulation_version="v1", kind="statement", statement=cid,
        level=level, updated="2026-09-06", depends_on=list(deps), supersedes=list(supersedes),
        receipts=list(receipts),
        evidence=[EvidenceEntry(path=f"ev/{cid}.json", verifier="v", version="1",
                                verdict="PASS", stamped="2026-09-06T00:00:00Z")],
    )


def _receipt(rid, cid, blocking=False, closes=None, created="2026-09-06"):
    return Receipt(
        id=rid, claim_id=cid, reviewer="human", statement_sha256="0" * 64,
        findings=[Finding(dimension="evidence_support", severity="blocking" if blocking else "note",
                          text="x")],
        verdict="BLOCK" if blocking else "PASS", closes=closes, created=created,
    )


def test_graph_cycle_and_unknown_dependency():
    claims = {"a": _claim("a", deps=["b"]), "b": _claim("b", deps=["a"])}
    g = dependency_graph(claims)
    assert find_cycle(g) in (["a", "b", "a"], ["b", "a", "b"])
    with pytest.raises(ClaimGraphError, match="cycle"):
        topological_order(g)
    with pytest.raises(ClaimGraphError, match="unknown claim"):
        dependency_graph({"a": _claim("a", deps=["ghost"])})
    with pytest.raises(ClaimGraphError, match="supersedes unknown"):
        dependency_graph({"a": _claim("a", supersedes=["ghost"])})
    assert find_cycle(dependency_graph({"a": _claim("a"), "b": _claim("b", deps=["a"])})) is None


def test_each_rule_alone_and_precedence():
    claims = {
        "base": _claim("base"),
        "mid": _claim("mid", deps=["base"]),
        "top": _claim("top", deps=["mid"]),
        "old": _claim("old"),
        "new": _claim("new", supersedes=["old"]),
        "ref": _claim("ref", level="REFUTED"),
        "onref": _claim("onref", deps=["ref"]),
    }
    st = compute_standing(claims, {})
    assert st == {"base": "CURRENT", "mid": "CURRENT", "top": "CURRENT", "old": "SUPERSEDED",
                  "new": "CURRENT", "ref": "CURRENT", "onref": "STALE"}
    # a lock mismatch two levels down propagates forward
    st = compute_standing(claims, {"base": ["changed:ev/base.json"]})
    assert st["base"] == "STALE" and st["mid"] == "STALE" and st["top"] == "STALE"
    assert st["new"] == "CURRENT"
    # registry newer -> STALE
    st = compute_standing(claims, {}, registry_newer=lambda e: True)
    assert all(v in ("STALE", "SUPERSEDED") for v in st.values())
    # SUPERSEDED beats STALE and CHALLENGED; CHALLENGED beats STALE
    st = compute_standing(claims, {"old": ["changed:ev/old.json"]})
    assert st["old"] == "SUPERSEDED"
    r = _receipt("r", "old", blocking=True)
    assert compute_standing(claims, {}, {"r": r})["old"] == "SUPERSEDED"
    r = _receipt("r", "base", blocking=True)
    st = compute_standing(claims, {"base": ["changed:ev/base.json"]}, {"r": r})
    assert st["base"] == "CHALLENGED" and st["mid"] == "STALE"


def test_propagation_does_not_depend_on_id_order():
    # the edge runs against alphabetical order, plus a diamond
    claims = {"a": _claim("a", deps=["z"]), "z": _claim("z"),
              "d": _claim("d", deps=["l", "r"]), "l": _claim("l", deps=["z"]),
              "r": _claim("r")}
    st = compute_standing(claims, {"z": ["changed:ev/z.json"]})
    assert st == {"z": "STALE", "a": "STALE", "l": "STALE", "r": "CURRENT", "d": "STALE"}


def test_challenged_until_closed(tmp_path):
    claims = {"a": _claim("a", receipts=["r1"]), "b": _claim("b", deps=["a"])}
    r1 = _receipt("r1", "a", blocking=True)
    st = compute_standing(claims, {}, {"r1": r1})
    assert st["a"] == "CHALLENGED" and st["b"] == "STALE"  # a dependent is not CURRENT
    r2 = _receipt("r2", "a", closes="r1")
    st = compute_standing(claims, {}, {"r1": r1, "r2": r2})
    assert st == {"a": "CURRENT", "b": "CURRENT"}
    # a receipt cannot close itself, close across claims, or predate what it closes
    with pytest.raises(ValueError, match="close itself"):
        _receipt("r9", "a", blocking=True, closes="r9")
    other = _receipt("rb", "b", closes="r1")
    assert compute_standing(claims, {}, {"r1": r1, "rb": other})["a"] == "CHALLENGED"
    early = _receipt("r0", "a", closes="r1", created="2026-01-01")
    assert compute_standing(claims, {}, {"r1": r1, "r0": early})["a"] == "CHALLENGED"
    # a receipt merely LISTED on the claim but written for another claim is ignored
    stray = _receipt("r1", "zzz", blocking=True)
    assert compute_standing(claims, {}, {"r1": stray})["a"] == "CURRENT"
    save_receipt(tmp_path, r1)
    save_receipt(tmp_path, r2)
    loaded = load_receipts(tmp_path)
    assert set(loaded) == {"r1", "r2"} and loaded["r1"].blocking
    (tmp_path / "receipts" / "r3.json").write_text("{}")
    with pytest.raises(ClaimSchemaError, match="malformed receipt"):
        load_receipts(tmp_path)

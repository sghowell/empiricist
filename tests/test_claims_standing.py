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
                                verdict="PASS", stamped="t")],
    )


def _receipt(rid, cid, blocking=False, closes=None):
    return Receipt(
        id=rid, claim_id=cid, reviewer="human", statement_sha256="0" * 64,
        findings=[Finding(dimension="evidence_support", severity="blocking" if blocking else "note",
                          text="x")],
        verdict="BLOCK" if blocking else "PASS", closes=closes, created="2026-09-06",
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
    # SUPERSEDED beats STALE
    st = compute_standing(claims, {"old": ["changed:ev/old.json"]})
    assert st["old"] == "SUPERSEDED"


def test_challenged_until_closed(tmp_path):
    claims = {"a": _claim("a", receipts=["r1"]), "b": _claim("b", deps=["a"])}
    r1 = _receipt("r1", "a", blocking=True)
    st = compute_standing(claims, {}, {"r1": r1})
    assert st["a"] == "CHALLENGED" and st["b"] == "CURRENT"  # challenge does not propagate as STALE
    r2 = _receipt("r2", "a", closes="r1")
    st = compute_standing(claims, {}, {"r1": r1, "r2": r2})
    assert st["a"] == "CURRENT"
    save_receipt(tmp_path, r1)
    save_receipt(tmp_path, r2)
    loaded = load_receipts(tmp_path)
    assert set(loaded) == {"r1", "r2"} and loaded["r1"].blocking
    (tmp_path / "receipts" / "r3.json").write_text("{}")
    with pytest.raises(ClaimSchemaError, match="malformed receipt"):
        load_receipts(tmp_path)

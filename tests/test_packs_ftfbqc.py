"""The ftfbqc pack manifest: v1 evidence adapters over the P3/P5 verifiers (M24a Task 3)."""
from __future__ import annotations

import json

import pytest

from empiricist.certificates.goldens import load_k0_golden
from empiricist.certificates.verifier import SOSCertificateVerifier, certificate_to_json
from empiricist.claims.check import check
from empiricist.claims.promote import formulate, promote, statement_sha256
from empiricist.claims.standing import Finding, Receipt, save_receipt
from empiricist.ledger.models import Verdict
from empiricist.packs import certify_pack_verifier, load_pack, pack_identity, resolve_pack_verifier
from empiricist.verifiers.builtin import identity_for
from empiricist.verifiers.registry import AGREED_VERSION, agreed_binary_hash

NAMES = ("sos_certificate", "p3_exact_witness", "stab_fusion", "enum_fusion", "verify_agreed",
         "p3_moment_bound", "p3_k0_min_zero")
# p3_moment_bound's PASS goldens at (k, m) = (1, 5) and (1, 6) are exact expansions of ~30 s
# and ~50 s: certified in its own slow test below, not in the fast loop.
FAST_NAMES = tuple(n for n in NAMES if n != "p3_moment_bound")


def test_manifest_loads_and_identities_are_the_v0_ones():
    m = load_pack("ftfbqc")
    assert m is not None and set(m.verifiers) == set(NAMES) and m.problems["P5"] == "p5-ghz3-v1"
    sos = SOSCertificateVerifier()
    assert pack_identity("sos_certificate") == (sos.version, sos.binary_hash)
    assert pack_identity("verify_agreed") == (AGREED_VERSION, agreed_binary_hash())
    assert identity_for("sos_certificate") == pack_identity("sos_certificate")


def test_every_ftfbqc_verifier_certifies_and_judges_its_goldens(tmp_path):
    (tmp_path / "claims").mkdir()
    for name in FAST_NAMES:
        v = resolve_pack_verifier(tmp_path, name)
        cases = v.golden_suite()
        assert cases and {c.expected for c in cases} >= {Verdict.PASS, Verdict.FAIL}, name
        for c in cases:
            assert v.verify_bytes(c.payload).verdict is c.expected, (name, c.label)
        stamp, problems = certify_pack_verifier(tmp_path, name)
        assert problems == [] and stamp is not None and stamp.pack == "ftfbqc", name
    sos = resolve_pack_verifier(tmp_path, "sos_certificate")
    assert sos.verify_bytes(b"{").verdict is Verdict.FAIL
    # a predicate verifier that can REFUTE never turns a malformed file into a FAIL
    mz = resolve_pack_verifier(tmp_path, "p3_k0_min_zero")
    assert mz.verify_bytes(b"{").verdict is Verdict.ERROR


@pytest.mark.slow
def test_the_moment_bound_verifier_certifies_and_judges_its_goldens(tmp_path):
    (tmp_path / "claims").mkdir()
    v = resolve_pack_verifier(tmp_path, "p3_moment_bound")
    cases = v.golden_suite()
    assert {c.expected for c in cases} == {Verdict.PASS, Verdict.FAIL}
    for c in cases:
        assert v.verify_bytes(c.payload).verdict is c.expected, c.label
    stamp, problems = certify_pack_verifier(tmp_path, "p3_moment_bound")
    assert problems == [] and stamp is not None and stamp.pack == "ftfbqc"
    assert v.verify_bytes(b"{").verdict is Verdict.FAIL


def test_the_moment_bound_verifier_fails_fast_on_cheap_gates(tmp_path):
    v = resolve_pack_verifier(tmp_path, "p3_moment_bound")
    by_label = {c.label: c for c in v.golden_suite()}
    for label in ("moment-k0-m4-half", "moment-k1-m5-bound-too-low", "moment-k1-m6-bound-too-low",
                  "moment-k0-m4-corrupt-lemma", "moment-k1-m5-foreign-lemma",
                  "moment-k2-m8-unsupported"):
        c = by_label[label]
        assert v.verify_bytes(c.payload).verdict is c.expected, label


def test_promote_a_claim_to_certified_on_the_sos_pack_verifier(tmp_path):
    repo = tmp_path
    (repo / "certs").mkdir()
    (repo / "certs" / "k0.json").write_text(json.dumps(certificate_to_json(load_k0_golden())))
    certify_pack_verifier(repo, "sos_certificate")
    stmt = "the standard-assignment objective is at most 1/2 for every U in U(4)"
    formulate(repo, claim_id="P3.k0", problem="P3", formulation_version="v1", kind="statement",
              statement=stmt)
    c = promote(repo, claim_id="P3.k0", level="CONJECTURED", verifier="sos_certificate",
                evidence_path="certs/k0.json")
    assert c.level == "CONJECTURED" and c.evidence[0].verifier == "sos_certificate"
    save_receipt(repo, Receipt(
        id="P3.k0.20260907.human", claim_id="P3.k0", reviewer="human",
        statement_sha256=statement_sha256(stmt), verdict="PASS", created="2026-09-07",
        target_level="CERTIFIED",
        findings=[Finding(dimension="evidence_support", severity="note", text="replays")],
    ))
    c = promote(repo, claim_id="P3.k0", level="CERTIFIED", verifier="sos_certificate",
                evidence_path="certs/k0.json", receipt_id="P3.k0.20260907.human")
    assert c.level == "CERTIFIED"
    rep = check(repo)
    assert rep.ok, rep.issues

"""`reverify` for certificate artifacts: SOS certificates and exact witnesses (M23a Task 4)."""
from __future__ import annotations

import math

from empiricist.certificates.goldens import certify_sos, load_k0_golden
from empiricist.certificates.ingest import ingest_p3_certificate
from empiricist.certificates.reverify import reverify_certificate_artifacts
from empiricist.certificates.verifier import SOSCertificateVerifier, certificate_to_json
from empiricist.domain.p3.exact_ingest import ingest_exact_witness, witness_json_from_scheme_json
from empiricist.ledger.audit import audit_ledger
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Status, Verdict
from empiricist.store import Store
from empiricist.verifiers.base import VerifierResult
from empiricist.verifiers.p3_exact import P3ExactVerifier
from empiricist.verifiers.p3_exact_goldens import certify_p3_exact

_BS = math.pi / 4


def _grice_json() -> dict:
    r = 1 / math.sqrt(2)
    bs = [(0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
    return {
        "n_modes": 8,
        "n_ancilla_photons": 2,
        "ancilla": [
            {"pattern": [1, 0, 1, 0], "re": r, "im": 0.0},
            {"pattern": [0, 1, 0, 1], "re": r, "im": 0.0},
        ],
        "mesh": [{"kind": "bs", "i": i, "j": j, "theta": _BS, "phi": 0.0} for i, j in bs],
    }


GRICE_CLAIM = {"phi+": "1/2", "phi-": "1/2", "psi+": "1", "psi-": "1"}


def _env(tmp_path):
    lg, st = Ledger(tmp_path / "ledger.db"), Store(tmp_path / "store")
    certify_sos(lg, SOSCertificateVerifier())
    certify_p3_exact(lg, P3ExactVerifier())
    return lg, st


def _sos_artifact(lg, st):
    return ingest_p3_certificate(
        lg, st, certificate_json=certificate_to_json(load_k0_golden()),
        target="k0_standard_assignment_p_avg", title="k0 cert",
    )


def test_reverify_sos_certificate_records_a_pass_under_the_live_identity(tmp_path, monkeypatch):
    lg, st = _env(tmp_path)
    art = _sos_artifact(lg, st)
    # an edited checker: the live hash moves while the old stamp stays
    monkeypatch.setattr(SOSCertificateVerifier, "binary_hash", property(lambda self: "cd" * 32))
    rep = reverify_certificate_artifacts(lg, st)
    assert rep.certified_now and rep.ok
    assert [(o.artifact_id, o.verdict) for o in rep.outcomes] == [(art.id, "PASS")]
    rows = lg.evidence_for(art.id)
    assert len(rows) == 2 and rows[-1].binary_hash == "cd" * 32
    assert rows[-1].verdict is Verdict.PASS and rows[-1].claim_id == rows[0].claim_id
    assert lg.get_artifact(art.id).status is Status.CERTIFIED
    assert audit_ledger(lg, st).ok
    rep2 = reverify_certificate_artifacts(lg, st)
    assert rep2.ok and not rep2.certified_now   # the live identity is now stamped
    lg.close()


def test_reverify_exact_witness_reruns_from_the_stored_payload(tmp_path, monkeypatch):
    lg, st = _env(tmp_path)
    art = ingest_exact_witness(
        lg, st, witness_json=witness_json_from_scheme_json(_grice_json()),
        claimed_success=GRICE_CLAIM, require_all_identified=True, title="Grice",
    )
    monkeypatch.setattr(P3ExactVerifier, "binary_hash", property(lambda self: "ef" * 32))
    rep = reverify_certificate_artifacts(lg, st)
    assert rep.ok and rep.certified_now
    rows = lg.evidence_for(art.id)
    assert len(rows) == 2 and rows[-1].verifier == "p3_exact_witness"
    assert rows[-1].binary_hash == "ef" * 32 and rows[-1].verdict is Verdict.PASS
    assert len(lg.claims_for(art.id)) == 1
    lg.close()


def test_reverify_non_pass_records_evidence_only_and_keeps_status(tmp_path, monkeypatch):
    lg, st = _env(tmp_path)
    art = _sos_artifact(lg, st)
    monkeypatch.setattr(
        SOSCertificateVerifier, "verify",
        lambda self, cert: VerifierResult(verdict=Verdict.FAIL, details={"failure": "psd"}),
    )
    rep = reverify_certificate_artifacts(lg, st)
    assert not rep.ok and rep.outcomes[0].verdict == "FAIL" and "psd" in rep.outcomes[0].detail
    rows = lg.evidence_for(art.id)
    assert rows[-1].verdict is Verdict.FAIL and rows[-1].details["reverify"] is True
    assert lg.get_artifact(art.id).status is Status.CERTIFIED
    lg.close()


def test_reverify_dry_run_and_missing_ids(tmp_path):
    lg, st = _env(tmp_path)
    art = _sos_artifact(lg, st)
    rep = reverify_certificate_artifacts(lg, st, dry_run=True)
    assert rep.dry_run and [o.verdict for o in rep.outcomes] == ["SKIPPED"]
    assert len(lg.evidence_for(art.id)) == 1
    rep = reverify_certificate_artifacts(lg, st, artifact_ids=["nope"])
    assert [o.verdict for o in rep.outcomes] == ["MISSING"]
    lg.close()

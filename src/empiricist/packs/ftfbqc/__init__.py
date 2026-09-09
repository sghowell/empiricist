"""The `ftfbqc` pack: today's P3 and P5 verifiers behind one manifest (charter section 5).

The code still lives in `empiricist.certificates`, `empiricist.verifiers` and
`empiricist.domain`; this manifest is the boundary the claim ledger sees. The physical move
of the domain code under this package is deferred (recorded in the M24a plan).
"""
from __future__ import annotations

from empiricist.packs import PackManifest
from empiricist.packs.ftfbqc.adapters import (
    AgreedFusionAdapter,
    EnumFusionAdapter,
    ExactWitnessAdapter,
    SOSCertificateAdapter,
    StabFusionAdapter,
)

MANIFEST = PackManifest(
    name="ftfbqc",
    version="0.1",
    verifiers={
        "sos_certificate": SOSCertificateAdapter,
        "p3_exact_witness": ExactWitnessAdapter,
        "stab_fusion": StabFusionAdapter,
        "enum_fusion": EnumFusionAdapter,
        "verify_agreed": AgreedFusionAdapter,
    },
    problems={"P3": "p3-certificates-v1", "P5": "p5-ghz3-v1"},
)

__all__ = ["MANIFEST"]

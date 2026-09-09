"""The `zx` pack: Problem 6 (ZX rewriting -- proof complexity and confluence).

Diagrams (`diagram`), their standard interpretation for small sizes (`semantics`), the
Clifford and Clifford+T rewrite rules (`rules`), matching and rewriting (`rewrite`),
derivation replay (`derivation`), critical-pair joinability (`critical_pairs`),
termination certificates (`termination`), rule soundness against the semantic oracle
(`soundness`) and bounded completeness with the zero class recognised rather than
normalised (`completeness`; formulation `p6-zx-v2`), behind six certified pack
verifiers (`verifiers`): `zx_derivation`, `zx_semantic_equal`, `zx_critical_pairs`,
`zx_termination`, `zx_rule_sound`, `zx_completeness`. No optional dependencies: the
pack loads wherever core does.
"""
from __future__ import annotations

from empiricist.packs import PackManifest
from empiricist.packs.zx.verifiers import VERIFIERS

MANIFEST = PackManifest(
    name="zx",
    version="0.2",
    verifiers=dict(VERIFIERS),
    problems={"P6": "p6-zx-v2"},
)

__all__ = ["MANIFEST"]

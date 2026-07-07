"""The Verifier protocol + its result type (spec §7).

A Verifier is anything that can `verify()` a construction and report a
PASS/FAIL/ERROR verdict with supporting details. It is identified by
(name, version, binary_hash): binary_hash is the blake3 digest of the
verifier module's OWN source concatenated with its wrapped engine module's
source (see `module_source_hash`), so editing either -- even a comment change
-- mints a new identity and silently drops any certification stamp earned by
the old one (registry.py enforces this; base.py just computes the digest).

Verifiers must never raise on an engine failure: `verify()` catches engine
exceptions and reports Verdict.ERROR with the message in `details["error"]`,
so a buggy engine becomes evidence in the ledger rather than a crashed run.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Protocol, runtime_checkable

from blake3 import blake3

from empiricist.ledger.models import Verdict


def module_source_hash(*modules: ModuleType) -> str:
    """blake3 hex digest of the concatenated source of `modules`, in order.

    Used as a Verifier's `binary_hash`: pass the verifier's own module plus
    the engine module it wraps. Any edit to either source changes the digest.
    """
    hasher = blake3()
    for mod in modules:
        hasher.update(inspect.getsource(mod).encode("utf-8"))
    return hasher.hexdigest()


@dataclass(frozen=True)
class VerifierResult:
    """The outcome of one `Verifier.verify()` call. `details` is copied on
    construction (same discipline as the ledger's EvidenceRow) so a caller
    mutating their own dict afterward can't retroactively corrupt the result.
    """

    verdict: Verdict
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", dict(self.details))


@runtime_checkable
class Verifier(Protocol):
    """The shape every verifier (stab_fusion, enum_fusion, ...) implements.

    `name`/`version` identify the verifier's lineage; `binary_hash` pins its
    exact code (own module + wrapped engine module); `applicable(kind)`
    answers whether this verifier can judge an artifact of that `kind`
    (e.g. "construction"); `verify(construction)` runs it and returns a
    VerifierResult -- never raises on an engine failure (see module docstring).
    """

    name: str
    version: str

    @property
    def binary_hash(self) -> str: ...

    def applicable(self, kind: str) -> bool: ...

    def verify(self, construction: Any) -> VerifierResult: ...

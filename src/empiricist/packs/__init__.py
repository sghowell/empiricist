"""Packs (charter section 5): one domain's verifiers and golden suites behind one manifest.

A pack is the module `empiricist.packs.<name>` exposing `MANIFEST: PackManifest`. Core never
imports a pack statically; the claim ledger resolves a verifier by name -- a research
repository's own command-verifier declaration first (`claims/verifiers/<name>.yaml`),
an installed pack second -- and certifies it against the golden suite the pack ships.
Pack discovery is by fixed name (`PACK_NAMES`); there is no plugin system. A pack whose
optional dependencies are not installed loads as absent, never as an error.

A pack verifier judges v1 evidence: the bytes of a committed evidence file. Its identity
(name, version, binary_hash) follows the same rule as every verifier -- the hash covers the
verifier's own source and the engine modules it wraps -- and its golden suite is a list of
(payload, expected verdict) cases hashed into the stamp, so a changed suite invalidates
every stamp earned against the old one.
"""
from __future__ import annotations

import hashlib
import importlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from empiricist.claims.model import validate_repo_relative
from empiricist.claims.registry import VerifierStamp, stamp
from empiricist.ledger.models import Verdict
from empiricist.verifiers.base import VerifierResult

PACK_NAMES: tuple[str, ...] = ("ftfbqc", "cosmology", "zx")
log = logging.getLogger(__name__)


class PackError(Exception):
    """A manifest problem: two installed packs declare the same verifier name."""


@dataclass(frozen=True)
class GoldenCase:
    label: str
    payload: bytes
    expected: Verdict


@runtime_checkable
class PackVerifier(Protocol):
    name: str
    version: str

    @property
    def binary_hash(self) -> str: ...

    def verify_bytes(self, payload: bytes) -> VerifierResult: ...

    def run(self, evidence_rel: str) -> VerifierResult: ...

    def golden_suite(self) -> list[GoldenCase]: ...


@dataclass(frozen=True)
class PackManifest:
    name: str
    version: str
    verifiers: dict[str, Callable[[Path], PackVerifier]]
    problems: dict[str, str] = field(default_factory=dict)


class BytesFileVerifier:
    """Helper base for pack verifiers: `run(evidence_rel)` reads the committed evidence
    file under the repository root and hands its bytes to `verify_bytes`; an unreadable
    or out-of-repository path is an ERROR verdict, never an exception."""

    def __init__(self, repo: Path | str) -> None:
        self._repo = Path(repo)

    def run(self, evidence_rel: str) -> VerifierResult:
        try:
            rel = validate_repo_relative(evidence_rel)
            payload = (self._repo / rel).read_bytes()
        except (OSError, ValueError) as exc:
            return VerifierResult(
                verdict=Verdict.ERROR, details={"error": f"cannot read {evidence_rel}: {exc}"}
            )
        try:
            return self.verify_bytes(payload)
        except Exception as exc:  # noqa: BLE001 - a verifier is total: faults are ERROR verdicts
            return VerifierResult(
                verdict=Verdict.ERROR, details={"error": f"{type(exc).__name__}: {exc}"}
            )


def load_pack(name: str) -> PackManifest | None:
    """The manifest of `empiricist.packs.<name>`, or None when the name is unknown or the
    pack cannot be imported here (missing optional dependencies)."""
    if name not in PACK_NAMES:
        return None
    try:
        mod = importlib.import_module(f"empiricist.packs.{name}")
    except ImportError as exc:
        log.info("pack %s is not installed here: %s", name, exc)
        return None
    manifest = getattr(mod, "MANIFEST", None)
    if not isinstance(manifest, PackManifest):
        log.warning("pack %s exposes no MANIFEST", name)
        return None
    return manifest


def installed_packs() -> dict[str, PackManifest]:
    out: dict[str, PackManifest] = {}
    for name in PACK_NAMES:
        m = load_pack(name)
        if m is not None:
            out[name] = m
    return out


def _owners(name: str) -> list[tuple[str, PackManifest]]:
    return [(pn, m) for pn, m in installed_packs().items() if name in m.verifiers]


def pack_of(name: str) -> str | None:
    """The installed pack declaring verifier `name`, or None."""
    owners = _owners(name)
    if len(owners) > 1:
        raise PackError(
            f"verifier {name!r} is declared by several packs: "
            + ", ".join(sorted(pn for pn, _ in owners))
        )
    return owners[0][0] if owners else None


def resolve_pack_verifier(repo: Path | str, name: str) -> PackVerifier | None:
    owners = _owners(name)
    if not owners:
        return None
    if len(owners) > 1:
        raise PackError(
            f"verifier {name!r} is declared by several packs: "
            + ", ".join(sorted(pn for pn, _ in owners))
        )
    return owners[0][1].verifiers[name](Path(repo))


def pack_identity(name: str) -> tuple[str, str] | None:
    """(version, binary_hash) of the live pack verifier `name`, or None when no installed
    pack declares it or its identity cannot be computed."""
    try:
        v = resolve_pack_verifier(Path("."), name)
        if v is None:
            return None
        return str(v.version), str(v.binary_hash)
    except PackError:
        raise
    except Exception:  # noqa: BLE001 - an uncomputable identity is unknown, not drift
        return None


def golden_suite_hash(cases: list[GoldenCase]) -> str:
    """sha256 over (label, sha256(payload), expected) in suite order."""
    h = hashlib.sha256()
    for c in cases:
        h.update(f"{c.label}\0".encode())
        h.update(hashlib.sha256(c.payload).hexdigest().encode("ascii"))
        h.update(f"\0{c.expected.value}\n".encode())
    return h.hexdigest()


def certify_pack_verifier(
    repo: Path | str, name: str, *, allow_downgrade: bool = False
) -> tuple[VerifierStamp | None, list[str]]:
    """Run the pack verifier's golden suite; stamp the repository registry iff every case
    yields exactly its expected verdict (ERROR never satisfies a case). Returns
    (stamp or None, problems)."""
    repo = Path(repo)
    v = resolve_pack_verifier(repo, name)
    if v is None:
        return None, [f"no installed pack declares a verifier named {name!r}"]
    cases = v.golden_suite()
    if not cases:
        return None, [f"{name}: the pack ships no golden suite for it"]
    problems: list[str] = []
    for c in cases:
        try:
            r = v.verify_bytes(c.payload)
        except Exception as exc:  # noqa: BLE001 - report, never crash a certification
            problems.append(f"golden {c.label}: raised {type(exc).__name__}: {exc}")
            continue
        if r.verdict is not c.expected:
            why = r.details.get("detail") or r.details.get("error") or ""
            must = "must FAIL" if c.expected is Verdict.FAIL else f"must {c.expected.value}"
            problems.append(f"golden {c.label}: {r.verdict.value} ({must}) {why}".strip())
    if problems:
        return None, problems
    try:
        s = stamp(
            repo, name=v.name, version=v.version, binary_hash=v.binary_hash,
            golden_suite_hash=golden_suite_hash(cases), pack=pack_of(name),
            allow_downgrade=allow_downgrade,
        )
    except ValueError as exc:
        return None, [str(exc)]
    return s, []


__all__ = [
    "PACK_NAMES", "BytesFileVerifier", "GoldenCase", "PackError", "PackManifest",
    "PackVerifier", "certify_pack_verifier", "golden_suite_hash", "installed_packs",
    "load_pack", "pack_identity", "pack_of", "resolve_pack_verifier",
]

"""The pack's verifier table: which vendored checker each `cosmo_*` verifier replays, which
packages that replay imports (all hashed into the identity) and its goldens.

Two families so far:

- the P8(a) chain (`p8a` ... `p8a_remainder`, seven checkers, one per claim P8-A.1..A.7):
  each checker pins and replays its predecessor, so the replay of `p8a_remainder` runs the
  whole chain and its identity hashes every package in it;
- the P8(b) base chain (`p8`): the S0 anchor (P8-0), the derived action (P8-1) and the
  complete chain of six certificates through `verify_all` (P8-1, P8-2.C/D/CD, P8-2.reg,
  P8-3), through the contract adapters in `adapters/`.

Names carry the `cosmo_` prefix so they never shadow the research repository's own
declarations (`p8a`, `p8a_radiation`, ...).
"""
from __future__ import annotations

import functools
import importlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from empiricist.ledger.models import Verdict
from empiricist.packs import GoldenCase, PackVerifier
from empiricist.packs.cosmology.replay import ReplayVerifier
from empiricist.packs.cosmology.vendored import (
    CHECKERS,
    PACK_DIR,
    package_modules,
    vendored_package,
)

GOLDENS = PACK_DIR / "goldens"
ADAPTERS = "empiricist.packs.cosmology.adapters"

P8 = "problems/P8"
P8A = f"{P8}/a"
_P8A_ROOTS: tuple[tuple[str, str, str], ...] = (
    # (package, checker root relative to the research repository, pinned certificate)
    ("p8a", P8A, "focusing.json"),
    ("p8a_radiation", f"{P8A}/applicability", "radiation-qsei.json"),
    ("p8a_reference", f"{P8A}/applicability/reference", "radiation-reference.json"),
    ("p8a_asymptotics", f"{P8A}/applicability/reference/asymptotics", "radiation-asymptotics.json"),
    ("p8a_backreaction", f"{P8A}/applicability/reference/asymptotics/backreaction",
     "radiation-backreaction.json"),
    ("p8a_response", f"{P8A}/applicability/reference/asymptotics/backreaction/response",
     "radiation-response.json"),
    ("p8a_remainder",
     f"{P8A}/applicability/reference/asymptotics/backreaction/response/remainder",
     "radiation-remainder.json"),
)


@dataclass(frozen=True)
class Spec:
    name: str
    version: str
    checker: str                            # dotted module exposing the checker contract
    packages: tuple[tuple[str, str], ...]   # (top-level name, src dir under CHECKERS), import order
    passing: tuple[str, ...]                # pinned certificates under CHECKERS (PASS goldens)
    failing: tuple[str, ...]                # mutated certificates under GOLDENS (FAIL goldens)


def _p8a_spec(index: int) -> Spec:
    pkg, root, cert = _P8A_ROOTS[index]
    chain = tuple((p, f"{r}/src") for p, r, _ in _P8A_ROOTS[: index + 1])
    fixture = "fail-mutated-status.json" if pkg == "p8a_remainder" else "fail-mutated.json"
    return Spec(
        name=f"cosmo_{pkg}", version="1", checker=f"{pkg}.verify", packages=chain,
        passing=(f"{root}/certificates/{cert}",), failing=(f"cosmo_{pkg}/{fixture}",),
    )


_P8_BASE = (("p8", f"{P8}/src"),)
_P8_CERTS = f"{P8}/certificates"

SPECS: tuple[Spec, ...] = (
    *(_p8a_spec(i) for i in range(len(_P8A_ROOTS))),
    Spec(name="cosmo_p8_s0", version="1", checker=f"{ADAPTERS}.p8_s0", packages=_P8_BASE,
         passing=(f"{_P8_CERTS}/s0-identities.json",),
         failing=("cosmo_p8_s0/fail-mutated.json",)),
    Spec(name="cosmo_p8_s1", version="1", checker=f"{ADAPTERS}.p8_s1", packages=_P8_BASE,
         passing=(f"{_P8_CERTS}/s1-derived-action.json",),
         failing=("cosmo_p8_s1/fail-mutated.json",)),
    Spec(name="cosmo_p8_chain", version="1", checker=f"{ADAPTERS}.p8_chain", packages=_P8_BASE,
         passing=tuple(f"{_P8_CERTS}/{c}" for c in (
             "s1-derived-action.json", "a25-regression.json", "witness-C.json",
             "witness-D.json", "witness-CD_matter.json", "classification.json")),
         failing=("cosmo_p8_chain/fail-mutated.json",)),
)


def build(spec: Spec, repo: Path | str) -> ReplayVerifier:
    packages = [vendored_package(name, CHECKERS / src) for name, src in spec.packages]
    checker = importlib.import_module(spec.checker)
    engines = [m for p in packages for m in package_modules(p) if m is not checker]
    goldens = [
        GoldenCase(f"{Path(rel).name}: pinned certificate", (CHECKERS / rel).read_bytes(),
                   Verdict.PASS)
        for rel in spec.passing
    ] + [
        GoldenCase(f"{rel}: mutated certificate", (GOLDENS / rel).read_bytes(), Verdict.FAIL)
        for rel in spec.failing
    ]
    return ReplayVerifier(
        repo, name=spec.name, version=spec.version, checker_module=checker,
        engine_modules=engines, goldens=goldens,
    )


VERIFIERS: dict[str, Callable[[Path], PackVerifier]] = {
    spec.name: functools.partial(build, spec) for spec in SPECS
}

__all__ = ["GOLDENS", "SPECS", "VERIFIERS", "Spec", "build"]

"""The generic replay verifier over a death_and_gravity checker (M24b Task 1).

A checker is a module exposing `REPORT` (the pinned certificate path), `build_report()`
(an exact, read-only replay) and `validate_report(expected, actual)` (raises ValueError,
KeyError, TypeError or AssertionError on any difference) -- the contract every
`<package>.verify` module in death_and_gravity follows and the one its own command-verifier
adapter (`tools/empiricist_check.py`) runs. `ReplayVerifier` judges v1 evidence -- the
bytes of a committed certificate -- by that contract:

- PASS iff the replay reproduces the certificate exactly;
- FAIL when the checker reports a difference, or refuses to build a report at all (a failed
  exact identity, a changed pinned prior certificate): the adapter's exit 3, the checker's
  own verdict;
- ERROR for anything else: the evidence is not a JSON document, or the checker crashed.
  ERROR never satisfies a golden case and never earns a level.

The verifier is total: `verify_bytes` does not raise. Its identity is `source_hash` over
this module, the checker module and every engine module it was declared with -- the blake3
digest of their source files' bytes, in order, the same rule as core's
`module_source_hash` (which reads sources through `inspect.getsource` and cannot hash an
empty `__init__.py`, which vendored checker packages have) -- so an edit anywhere in the
vendored checker code mints a new identity and drops its stamp.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from blake3 import blake3

from empiricist.ledger.models import Verdict
from empiricist.packs import BytesFileVerifier, GoldenCase
from empiricist.verifiers.base import VerifierResult

#: What a checker raises to say "this certificate is not reproduced" (its adapter maps
#: exactly these to exit 3). Anything else is a fault.
CHECKER_FAILURES: tuple[type[BaseException], ...] = (
    ValueError, KeyError, TypeError, AssertionError,
)

_UNBUILT = object()


def source_hash(*modules: Any) -> str:
    """blake3 hex digest of the concatenated source-file bytes of `modules`, in order."""
    hasher = blake3()
    for mod in modules:
        origin = getattr(mod, "__file__", None)
        if not origin:
            raise ValueError(f"module {mod!r} has no source file to hash")
        hasher.update(Path(origin).read_bytes())
    return hasher.hexdigest()


class ReplayVerifier(BytesFileVerifier):
    def __init__(
        self,
        repo: Path | str,
        *,
        name: str,
        version: str,
        checker_module: Any,
        engine_modules: Iterable[Any] = (),
        goldens: Iterable[GoldenCase] = (),
    ) -> None:
        super().__init__(repo)
        self.name = name
        self.version = version
        self._checker = checker_module
        self._engines = tuple(engine_modules)
        self._goldens = list(goldens)
        self._report: Any = _UNBUILT

    @property
    def binary_hash(self) -> str:
        return source_hash(sys.modules[__name__], self._checker, *self._engines)

    @property
    def checker_name(self) -> str:
        return str(getattr(self._checker, "__name__", type(self._checker).__name__))

    def _replay(self) -> Any:
        """The checker's replay, built once per verifier instance: it is deterministic and
        read-only, and one certification runs every golden case against it. A replay that
        raises is not cached (the next call replays again)."""
        if self._report is _UNBUILT:
            self._report = self._checker.build_report()
        return self._report

    def verify_bytes(self, payload: bytes) -> VerifierResult:
        base = {"checker": self.checker_name,
                "certificate_sha256": hashlib.sha256(payload).hexdigest()}
        try:
            expected = json.loads(payload)
        except ValueError as exc:
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={**base, "error": f"evidence is not a JSON certificate: {exc}"},
            )
        try:
            actual = self._replay()
            self._checker.validate_report(expected, actual)
        except CHECKER_FAILURES as exc:
            return VerifierResult(
                verdict=Verdict.FAIL, details={**base, "detail": f"{type(exc).__name__}: {exc}"}
            )
        except Exception as exc:  # noqa: BLE001 - a verifier is total: faults are ERROR verdicts
            return VerifierResult(
                verdict=Verdict.ERROR,
                details={**base, "error": f"replay failed: {type(exc).__name__}: {exc}"},
            )
        return VerifierResult(
            verdict=Verdict.PASS,
            details={**base, "detail": "certificate reproduced exactly by read-only replay"},
        )

    def golden_suite(self) -> list[GoldenCase]:
        return list(self._goldens)


__all__ = ["CHECKER_FAILURES", "ReplayVerifier", "source_hash"]

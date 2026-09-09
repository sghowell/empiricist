"""Live identities of the verifiers this package ships, for `claims check`.

A research repository's registry (`claims/verifiers.json`) stamps the identity each
verifier held when its evidence was certified. Command verifiers are compared to their
declaration on disk; the built-in verifier (Lean, core per charter section 5) is compared
to the identity the installed package computes; pack verifiers are compared through the
pack that ships them (`identity_for`). An identity this build cannot compute (no Lean
project on disk, an import error) is "unknown", never drift.
"""
from __future__ import annotations

from collections.abc import Callable


def _lean():
    from empiricist.verifiers.lean import LeanVerifier

    return LeanVerifier()


# Lean is core (charter section 5); every other verifier's live identity comes from the
# pack that ships it (`identity_for` asks the packs first).
_FACTORIES: dict[str, Callable[[], object]] = {"lean": _lean}


def builtin_identity(name: str) -> tuple[str, str] | None:
    """(version, binary_hash) of the live built-in verifier `name`, or None when the name
    is not a built-in or its identity cannot be computed here."""
    factory = _FACTORIES.get(name)
    if factory is None:
        return None
    try:
        v = factory()
        return str(v.version), str(v.binary_hash)
    except Exception:  # noqa: BLE001 - an uncomputable identity is unknown, not drift
        return None


def identity_for(name: str) -> tuple[str, str] | None:
    """(version, binary_hash) of the live verifier `name`: an installed pack's verifier
    first (charter section 5), a built-in second, None when neither knows the name."""
    from empiricist.packs import pack_identity

    live = pack_identity(name)
    return live if live is not None else builtin_identity(name)

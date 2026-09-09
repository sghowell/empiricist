"""The `cosmology` pack (charter section 5, M24b): death_and_gravity's certificate replay
checkers as certified pack verifiers.

Each verifier wraps one of the research repository's read-only checkers (vendored verbatim
under `checkers/death_and_gravity/`; see `SOURCES.md`) in the generic `ReplayVerifier`:
the evidence is a committed certificate, the verdict is whether an exact replay reproduces
it. Verifier names carry the `cosmo_` prefix so they never shadow the research repository's
own command-verifier declarations (`p8a`, `p8a_radiation`, ...), which stay as they are.

Importing this module requires the optional `cosmology` dependency group (sympy,
python-flint); without it the import raises ImportError and `load_pack("cosmology")`
reads as "not installed".
"""
from __future__ import annotations

import flint  # noqa: F401 - optional dependency: ImportError here means the pack is absent
import sympy  # noqa: F401

from empiricist.packs import PackManifest

#: The frozen problem document the research repository works against
#: (`docs/problems/open-problems-theoretical-cosmology-2026.tex` at tag `problems-v1.1`).
PROBLEMS = {"P8": "problems-v1.1"}

MANIFEST = PackManifest(name="cosmology", version="0.1", verifiers={}, problems=PROBLEMS)

__all__ = ["MANIFEST", "PROBLEMS"]

"""Import plumbing for the checker packages this pack vendors from death_and_gravity.

The research repository's checkers are top-level packages (`p8`, `p8a`, `p8a_radiation`,
...) that import each other by those names and locate their pinned certificates and
hashed sources relative to their own `__file__`. They are vendored verbatim under
`checkers/death_and_gravity/` (the layout of the research repository, so every relative
path they compute resolves to the vendored copy), and a meta-path finder serves those
names ahead of `sys.path`: the code that runs is the code the verifier identity hashes,
whatever `PYTHONPATH` says.
"""
from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import sys
from pathlib import Path
from types import ModuleType

PACK_DIR = Path(__file__).resolve().parent
CHECKERS = PACK_DIR / "checkers" / "death_and_gravity"


class VendoredFinder(importlib.abc.MetaPathFinder):
    """Serves registered top-level package names from their vendored `src` directories.
    Submodules are found by the package's own `__path__`, which already points into the
    vendored tree."""

    def __init__(self) -> None:
        self._roots: dict[str, Path] = {}

    def register(self, name: str, src_dir: Path) -> None:
        known = self._roots.get(name)
        if known is not None and known != src_dir:
            raise ImportError(f"vendored package {name!r} is already served from {known}")
        self._roots[name] = src_dir

    def find_spec(self, fullname, path=None, target=None):  # noqa: ARG002 - protocol
        if "." in fullname:
            return None
        src = self._roots.get(fullname)
        if src is None:
            return None
        return importlib.machinery.PathFinder.find_spec(fullname, [str(src)])


_FINDER = VendoredFinder()
if not any(isinstance(f, VendoredFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _FINDER)


def vendored_package(name: str, src_dir: Path | str) -> ModuleType:
    """Import top-level package `name` from `src_dir` through the finder and return it.
    Refuses (loudly: this is a programming-environment fault, not a missing dependency)
    a module of that name that was already imported from somewhere else."""
    src_dir = Path(src_dir).resolve()
    _FINDER.register(name, src_dir)
    mod = importlib.import_module(name)
    origin = getattr(mod, "__file__", None)
    if origin is None or not Path(origin).resolve().is_relative_to(src_dir):
        raise RuntimeError(
            f"package {name!r} resolved to {origin}, not the vendored copy under {src_dir}; "
            "it was imported from elsewhere before the cosmology pack registered it"
        )
    return mod


def package_modules(pkg: ModuleType) -> list[ModuleType]:
    """Every module of vendored package `pkg` (its `*.py` files, sorted by name), imported."""
    root = Path(pkg.__file__).parent
    out = []
    for f in sorted(root.glob("*.py")):
        sub = pkg.__name__ if f.stem == "__init__" else f"{pkg.__name__}.{f.stem}"
        out.append(importlib.import_module(sub))
    return out


__all__ = ["CHECKERS", "PACK_DIR", "VendoredFinder", "package_modules", "vendored_package"]

"""Vendor death_and_gravity's checker trees into this pack, verbatim, and record it.

    python -m empiricist.packs.cosmology.vendor --from ~/dev/research/death_and_gravity \
        --commit <sha of the research commit the working tree is at>

For every checker root in `ROOTS` the files its replay reads are copied unchanged, at the
same relative paths, under `checkers/death_and_gravity/`: `src/**/*.py`, `tests/*.py`,
`*.md`, `notes/*.md` (all hashed into the certificates as `source_sha256`) and
`certificates/*.json` (the pinned certificates: PASS goldens and pinned priors). `uv.lock`
is copied too: the P8(b) classification certificate pins its sha256. The research
repository's own FAIL fixtures are copied to `goldens/<verifier>/`, and FAIL goldens are
minted for the checkers it declares no command verifier for (one certified value
changed). The manifest section of `SOURCES.md` is rewritten with every file's sha256.

This is a maintenance tool, not part of any verifier: re-running it after the research
repository changes is the only sanctioned way to change vendored code, and any change it
makes mints new verifier identities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

from empiricist.packs.cosmology.vendored import CHECKERS, PACK_DIR

GOLDENS = PACK_DIR / "goldens"
SOURCES_MD = PACK_DIR / "SOURCES.md"
MANIFEST_HEADING = "## Vendored files"

P8 = "problems/P8"
P8A = f"{P8}/a"
#: Checker roots (directories holding `src/`, `tests/`, `notes/`, `certificates/`, `*.md`).
ROOTS: tuple[str, ...] = (
    P8,
    P8A,
    f"{P8A}/applicability",
    f"{P8A}/applicability/reference",
    f"{P8A}/applicability/reference/asymptotics",
    f"{P8A}/applicability/reference/asymptotics/backreaction",
    f"{P8A}/applicability/reference/asymptotics/backreaction/response",
    f"{P8A}/applicability/reference/asymptotics/backreaction/response/remainder",
)
PATTERNS: tuple[str, ...] = (
    "src/**/*.py", "tests/*.py", "*.md", "notes/*.md", "certificates/*.json",
)
EXTRA_FILES: tuple[str, ...] = ("uv.lock",)

#: verifier -> the research repository's own FAIL fixture for that checker
RESEARCH_FIXTURES: dict[str, str] = {
    "cosmo_p8a": "claims/fixtures/p8a/fail-mutated.json",
    "cosmo_p8a_radiation": "claims/fixtures/p8a_radiation/fail-mutated.json",
    "cosmo_p8a_reference": "claims/fixtures/p8a_reference/fail-mutated.json",
    "cosmo_p8a_asymptotics": "claims/fixtures/p8a_asymptotics/fail-mutated.json",
    "cosmo_p8a_backreaction": "claims/fixtures/p8a_backreaction/fail-mutated.json",
    "cosmo_p8a_response": "claims/fixtures/p8a_response/fail-mutated.json",
    "cosmo_p8a_remainder": "claims/fixtures/p8a_remainder/fail-mutated-status.json",
}

#: verifier -> (certificate, key path, mutated value): FAIL goldens minted here for the
#: P8(b) base chain, whose checkers the research repository declares no verifier for.
MINTED: dict[str, tuple[str, tuple[str, ...], object]] = {
    "cosmo_p8_s0": (f"{P8}/certificates/s0-identities.json", ("benchmark_Hdot0_pinned",), "1/376"),
    "cosmo_p8_s1": (f"{P8}/certificates/s1-derived-action.json",
                    ("exact_residuals", "ADM", "__first__"), "1"),
    "cosmo_p8_chain": (f"{P8}/certificates/classification.json", ("counts", "M0", "E"), 11),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _files(origin: Path) -> list[str]:
    out: set[str] = set()
    for root in ROOTS:
        base = origin / root
        if not base.is_dir():
            raise SystemExit(f"vendor: {base} is not a directory")
        for pattern in PATTERNS:
            for f in base.glob(pattern):
                if f.is_file() and "__pycache__" not in f.parts:
                    out.add(str(f.relative_to(origin)))
    out.update(EXTRA_FILES)
    return sorted(out)


def _mutate(certificate: dict, keys: tuple[str, ...], value: object) -> dict:
    node = certificate
    for k in keys[:-1]:
        node = node[k]
    last = keys[-1]
    if last == "__first__":
        last = sorted(node)[0]
    if node[last] == value:
        raise SystemExit(f"vendor: mutation {keys} would not change {value!r}")
    node[last] = value
    return certificate


ORIGIN_NAME = "~/dev/research/death_and_gravity (branch empiricist-claims-import)"


def vendor(origin: Path, commit: str, origin_name: str = ORIGIN_NAME) -> list[str]:
    origin = origin.resolve()
    files = _files(origin)
    if CHECKERS.exists():
        shutil.rmtree(CHECKERS)
    for rel in files:
        dst = CHECKERS / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origin / rel, dst)
    if GOLDENS.exists():
        shutil.rmtree(GOLDENS)
    golden_lines: list[str] = []
    for name, rel in sorted(RESEARCH_FIXTURES.items()):
        dst = GOLDENS / name / Path(rel).name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origin / rel, dst)
        golden_lines.append(f"- `goldens/{name}/{dst.name}` <- `{rel}` (sha256 {sha256(dst)})")
    for name, (cert, keys, value) in sorted(MINTED.items()):
        data = json.loads((CHECKERS / cert).read_text(encoding="utf-8"))
        data = _mutate(data, keys, value)
        dst = GOLDENS / name / "fail-mutated.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        golden_lines.append(
            f"- `goldens/{name}/fail-mutated.json`: `{cert}` with `{'/'.join(keys)}` set to "
            f"`{value!r}` (sha256 {sha256(dst)})"
        )
    lines = [
        MANIFEST_HEADING, "",
        f"Origin: `{origin_name}` at commit `{commit}`; copied by `vendor.py` into "
        f"`checkers/death_and_gravity/` ({len(files)} files).", "",
        "### FAIL goldens", "", *golden_lines, "",
        "### Files (path, sha256)", "",
        *(f"- `{rel}` {sha256(CHECKERS / rel)}" for rel in files), "",
    ]
    text = SOURCES_MD.read_text(encoding="utf-8")
    head, sep, _ = text.partition(MANIFEST_HEADING)
    if not sep:
        raise SystemExit(f"vendor: {SOURCES_MD} has no '{MANIFEST_HEADING}' section")
    SOURCES_MD.write_text(head + "\n".join(lines), encoding="utf-8")
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--from", dest="origin", required=True, type=Path,
                        help="the death_and_gravity working tree to copy from")
    parser.add_argument("--commit", required=True, help="the commit that working tree is at")
    parser.add_argument("--origin-name", default=ORIGIN_NAME,
                        help="how SOURCES.md names the origin (not the local checkout path)")
    args = parser.parse_args(argv)
    files = vendor(args.origin, args.commit, args.origin_name)
    print(f"vendor: {len(files)} files under {CHECKERS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

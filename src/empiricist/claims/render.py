"""`CLAIMS.md`: rendered from claim files, never hand-edited (charter section 3)."""
from __future__ import annotations

from pathlib import Path

from empiricist.claims.model import ClaimFile, Standing

CLAIMS_MD = "CLAIMS.md"
RENDERED_MARKER = "# Claims ledger\n\nRendered by `empiricist claims report`"
_HEADER = (
    RENDERED_MARKER + " from `claims/*.yaml`; do not hand-edit. One row "
    "per claim; a claim's level changes only together with an evidence entry or a receipt; "
    "REFUTED is terminal. Levels: HEURISTIC, CONJECTURED, VERIFIED_N, CERTIFIED, FORMALIZED, "
    "REFUTED; \"legacy X, unverified\" marks a level imported from an earlier table that "
    "`promote` has not yet re-earned. Standing: CURRENT, STALE, CHALLENGED, SUPERSEDED "
    "(derived by `empiricist claims check`).\n\n"
    "| id | problem | statement | level | standing | evidence | updated |\n"
    "|---|---|---|---|---|---|---|\n"
)


def is_rendered(text: str) -> bool:
    """True when `text` is this module's own output (and so safe to overwrite)."""
    return text.startswith(RENDERED_MARKER)


def _cell(text: str) -> str:
    return " ".join(text.replace("|", "\\|").split())


def _level_cell(c: ClaimFile) -> str:
    level = c.level
    if c.level == "VERIFIED_N" and c.n is not None:
        level += f" (n={c.n}{', ' + c.coverage if c.coverage else ''})"
    if c.substatus:
        level += f" [{c.substatus}]"
    if c.legacy_pending:
        level += f" (legacy {c.legacy_level}, unverified)"
    return level


def _evidence_cell(c: ClaimFile) -> str:
    seen: list[str] = []
    for e in c.evidence:
        if e.verdict == "IMPORTED":
            tag = f"{e.path} (imported)"
        else:
            tag = f"{e.path} ({e.verifier} {e.version} {e.verdict})"
        if tag not in seen:
            seen.append(tag)
    return "; ".join(seen) if seen else "—"


def render_claims_md(claims: dict[str, ClaimFile], standings: dict[str, Standing]) -> str:
    rows = []
    for cid in sorted(claims):
        c = claims[cid]
        rows.append(
            f"| {_cell(c.id)} | {_cell(c.problem)} | {_cell(c.statement)} | "
            f"{_cell(_level_cell(c))} | {standings.get(cid, c.standing)} | "
            f"{_cell(_evidence_cell(c))} | {_cell(c.updated)} |"
        )
    return _HEADER + "\n".join(rows) + ("\n" if rows else "")


def claims_md_path(repo: Path | str) -> Path:
    return Path(repo) / CLAIMS_MD


def write_claims_md(
    repo: Path | str,
    claims: dict[str, ClaimFile],
    standings: dict[str, Standing],
    *,
    force: bool = False,
) -> Path | None:
    """Write the render. A `CLAIMS.md` that is NOT rendered output (a hand-written legacy
    table, the importer's own input) is left alone and None is returned unless
    `force=True`: replacing it is a one-time, explicit migration step."""
    p = claims_md_path(repo)
    if p.is_file() and not force and not is_rendered(p.read_text(encoding="utf-8")):
        return None
    p.write_text(render_claims_md(claims, standings), encoding="utf-8")
    return p

"""`CLAIMS.md`: rendered from claim files, never hand-edited (charter section 3)."""
from __future__ import annotations

from pathlib import Path

from empiricist.claims.model import ClaimFile, Standing

CLAIMS_MD = "CLAIMS.md"
_HEADER = (
    "# Claims ledger\n\n"
    "Rendered by `empiricist claims report` from `claims/*.yaml`; do not hand-edit. One row "
    "per claim; a claim's level changes only together with an evidence entry or a receipt; "
    "REFUTED is terminal. Levels: HEURISTIC, CONJECTURED, VERIFIED_N, CERTIFIED, FORMALIZED, "
    "REFUTED. Standing: CURRENT, STALE, CHALLENGED, SUPERSEDED (derived by `empiricist claims "
    "check`).\n\n"
    "| id | problem | statement | level | standing | evidence | updated |\n"
    "|---|---|---|---|---|---|---|\n"
)


def _cell(text: str) -> str:
    return " ".join(text.replace("|", "\\|").split())


def _level_cell(c: ClaimFile) -> str:
    level = c.level
    if c.level == "VERIFIED_N" and c.n is not None:
        level += f" (n={c.n}{', ' + c.coverage if c.coverage else ''})"
    if c.substatus:
        level += f" [{c.substatus}]"
    return level


def _evidence_cell(c: ClaimFile) -> str:
    seen: list[str] = []
    for e in c.evidence:
        tag = f"{e.path} ({e.verifier} {e.version} {e.verdict})"
        if tag not in seen:
            seen.append(tag)
    return "; ".join(seen) if seen else "—"


def render_claims_md(claims: dict[str, ClaimFile], standings: dict[str, Standing]) -> str:
    rows = []
    for cid in sorted(claims):
        c = claims[cid]
        rows.append(
            f"| {_cell(c.id)} | {_cell(c.problem)} | {_cell(c.statement)} | {_level_cell(c)} | "
            f"{standings.get(cid, c.standing)} | {_cell(_evidence_cell(c))} | {c.updated} |"
        )
    return _HEADER + "\n".join(rows) + ("\n" if rows else "")


def claims_md_path(repo: Path | str) -> Path:
    return Path(repo) / CLAIMS_MD


def write_claims_md(
    repo: Path | str, claims: dict[str, ClaimFile], standings: dict[str, Standing]
) -> Path:
    p = claims_md_path(repo)
    p.write_text(render_claims_md(claims, standings), encoding="utf-8")
    return p

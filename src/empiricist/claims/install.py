"""`install-skill`: put the interactive workflow into a research repository (charter
section 4, "a skill pack shipped here and installed into the research repository").

Installs `.claude/skills/empiricist-claims/SKILL.md` (always refreshed: the skill is the
harness's), `tools/empiricist_check.py` (the generic checker adapter; kept if the
repository already has one, unless `force`), and a `.empiricist/` line in `.gitignore`
(model-run provenance is local). Idempotent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

SKILL_REL = Path(".claude") / "skills" / "empiricist-claims" / "SKILL.md"
ADAPTER_REL = Path("tools") / "empiricist_check.py"
GITIGNORE_LINE = ".empiricist/"


@dataclass
class InstallReport:
    written: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    gitignore_updated: bool = False


def skill_files() -> dict[str, str]:
    pkg = resources.files("empiricist.claims.skill")
    return {
        "SKILL.md": (pkg / "SKILL.md").read_text(encoding="utf-8"),
        "adapter_template.py": (pkg / "adapter_template.py").read_text(encoding="utf-8"),
    }


def _write_if_changed(path: Path, text: str) -> bool:
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def install_skill(repo: Path | str, *, force: bool = False) -> InstallReport:
    repo = Path(repo)
    files = skill_files()
    report = InstallReport()
    if _write_if_changed(repo / SKILL_REL, files["SKILL.md"]):
        report.written.append(str(SKILL_REL))
    else:
        report.kept.append(str(SKILL_REL))
    adapter = repo / ADAPTER_REL
    if adapter.is_file() and not force:
        report.kept.append(str(ADAPTER_REL))
    elif _write_if_changed(adapter, files["adapter_template.py"]):
        report.written.append(str(ADAPTER_REL))
    else:
        report.kept.append(str(ADAPTER_REL))
    gi = repo / ".gitignore"
    lines = gi.read_text(encoding="utf-8").splitlines() if gi.is_file() else []
    if GITIGNORE_LINE not in [ln.strip() for ln in lines]:
        text = ("\n".join(lines) + "\n" if lines else "") + GITIGNORE_LINE + "\n"
        gi.write_text(text, encoding="utf-8")
        report.gitignore_updated = True
    return report

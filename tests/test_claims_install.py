"""Skill pack installer (M22c Task 4)."""
from __future__ import annotations

from empiricist.claims.install import ADAPTER_REL, SKILL_REL, install_skill, skill_files
from empiricist.cli import main


def test_install_is_idempotent_and_keeps_a_local_adapter(tmp_path):
    rep = install_skill(tmp_path)
    assert rep.written == [str(SKILL_REL), str(ADAPTER_REL)] and rep.gitignore_updated
    skill = (tmp_path / SKILL_REL).read_text()
    assert skill.startswith("---\nname: empiricist-claims\n") and "claims promote" in skill
    assert (tmp_path / ADAPTER_REL).read_text() == skill_files()["adapter_template.py"]
    assert (tmp_path / ".gitignore").read_text() == ".empiricist/\n"
    rep2 = install_skill(tmp_path)
    assert rep2.written == [] and not rep2.gitignore_updated
    assert sorted(rep2.kept) == sorted([str(SKILL_REL), str(ADAPTER_REL)])
    # a repository's own adapter survives unless forced
    (tmp_path / ADAPTER_REL).write_text("# mine\n")
    (tmp_path / ".gitignore").write_text(".venv/\n.empiricist/\n")
    rep3 = install_skill(tmp_path)
    assert (tmp_path / ADAPTER_REL).read_text() == "# mine\n" and str(ADAPTER_REL) in rep3.kept
    assert (tmp_path / ".gitignore").read_text() == ".venv/\n.empiricist/\n"
    rep4 = install_skill(tmp_path, force=True)
    assert rep4.written == [str(ADAPTER_REL)]
    assert (tmp_path / ADAPTER_REL).read_text() == skill_files()["adapter_template.py"]


def test_cli_install_skill(tmp_path, capsys):
    assert main(["claims", "install-skill", "--repo", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "wrote .claude/skills/empiricist-claims/SKILL.md" in out
    assert "added .empiricist/ to .gitignore" in out
